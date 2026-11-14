"""Working feature imports preserve relationships and save each calculation atomically."""

from contextlib import nullcontext
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

import psycopg
from psycopg.types.json import Jsonb
from worldatlas.source_imports.run_import import run_import, selected_constructions
from worldatlas.source_imports.features.geometry import save_features, geometry_hash


@unittest.skipUnless(
    os.environ.get("WORLDATLAS_TEST_DATABASE_URL"), "requires disposable PostgreSQL"
)
class StorageTests(unittest.TestCase):
    def setUp(self):
        self.database = psycopg.connect(os.environ["WORLDATLAS_TEST_DATABASE_URL"])
        self.addCleanup(self.database.close)
        self.addCleanup(self.database.rollback)
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.work = Path(temp.name)
        self.storage = Mock()
        self.raw = json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"id": "a"},
                        "geometry": {"type": "Point", "coordinates": [10, 20]},
                    }
                ],
            }
        ).encode()
        self.add_source("raw", self.raw, "source.geojson")
        self.storage.get_object.side_effect = lambda **_: {"Body": io.BytesIO(self.raw)}
        self.recipe = dict(
            method="selected_vector_features",
            source_id="raw",
            basis="Selected source point",
            id_field="id",
            selections=[dict(feature_id="point-a", source_feature_id="a")],
        )
        self.store()

    def add_source(self, ident, raw, key):
        self.database.execute(
            "INSERT INTO atlas.source_assets "
            "(source_id,title,provider,source_uri,license_name,license_uri,attribution,r2_bucket,r2_key,sha256,size_bytes) "
            "VALUES (%s,'Test','Test','test:source','Test','test:license','Test','test',%s,%s,%s)",
            (ident, key, hashlib.sha256(raw).hexdigest(), len(raw)),
        )

    def store(self):
        self.database.execute(
            "INSERT INTO atlas.construction_records VALUES (%s,%s) "
            "ON CONFLICT(source_id) DO UPDATE SET document=EXCLUDED.document",
            ("__features", Jsonb(self.recipe)),
        )

    def build(self):
        return run_import(
            lambda: nullcontext(self.database),
            "__features",
            storage=self.storage,
            work_dir=self.work,
        )

    def rows(self):
        return self.database.execute(
            "SELECT feature_id,geometry,geometry_sha256,evidence,construction_id "
            "FROM atlas.decision_features ORDER BY feature_id"
        ).fetchall()

    def test_repeat_and_recipe_edit_preserve_notes_links_and_other_records(self):
        first = self.build()
        self.database.execute(
            'UPDATE atlas.decision_features SET evidence=evidence || \'{"note":"keep"}\''
        )
        self.database.execute(
            "INSERT INTO atlas.decision_basins VALUES ('basin','point-a','test','{}','{}')"
        )
        self.recipe["basis"] = "Updated explanation"
        self.store()
        self.build()
        after = self.rows()[0]
        self.assertEqual(after[3]["note"], "keep")
        self.assertEqual(after[3]["basis"], "Updated explanation")
        self.assertEqual(after[4], "__features")
        self.assertEqual(self.build()["geometry_sha256"], first["geometry_sha256"])
        self.assertEqual(self.storage.get_object.call_count, 1)
        self.assertEqual(selected_constructions(self.database), ["__features"])
        self.assertEqual(
            self.database.execute(
                "SELECT count(*) FROM atlas.decision_basins"
            ).fetchone()[0],
            1,
        )

    def test_missing_source_rolls_back_the_complete_feature_batch(self):
        self.build()
        before = self.rows()
        features = [
            dict(
                feature_id="point-a",
                source_id="raw",
                source_feature_id="a",
                geometry={"type": "Point", "coordinates": [11, 21]},
            ),
            dict(
                feature_id="point-b",
                source_id="missing",
                source_feature_id="b",
                geometry={"type": "Point", "coordinates": [12, 22]},
            ),
        ]
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            save_features(
                self.database, features, dict(self.recipe, recipe_id="__features")
            )
        self.assertEqual(self.rows(), before)

    def test_table_import_and_identity_failure(self):
        self.raw = b"id,name,lon,lat\na,First,-20.25,11.5\n"
        self.add_source("table", self.raw, "source.csv")
        self.recipe.update(
            method="selected_table_points",
            source_id="table",
            longitude_field="lon",
            latitude_field="lat",
            coordinate_reference="OGC:CRS84",
        )
        self.recipe["selections"][0]["expected_properties"] = {"name": "First"}
        self.store()
        self.build()
        before = self.rows()
        self.assertEqual(before[0][1]["coordinates"], [-20.25, 11.5])
        self.recipe["selections"][0]["expected_properties"]["name"] = "Wrong"
        self.store()
        with self.assertRaisesRegex(ValueError, "identity"):
            self.build()
        self.assertEqual(self.rows(), before)

    def test_signed_zero_and_native_coordinate_storage(self):
        for ident, reference, coordinates in [
            ("zero", "OGC:CRS84", [-0.0, 1e-24]),
            ("native", "EPSG:3857", [1000, 2000]),
        ]:
            geometry = {"type": "Point", "coordinates": coordinates}
            save_features(
                self.database,
                [
                    dict(
                        feature_id=ident,
                        source_id="raw",
                        source_feature_id="a",
                        coordinate_reference=reference,
                        geometry=geometry,
                    )
                ],
                dict(self.recipe, recipe_id="__features"),
            )
        for _, geometry, digest, _, _ in self.rows():
            self.assertEqual(geometry_hash(geometry), digest)
        zero = next(r for r in self.rows() if r[0] == "zero")
        self.assertEqual(json.dumps(zero[1]["coordinates"]), "[0.0, 1e-24]")
