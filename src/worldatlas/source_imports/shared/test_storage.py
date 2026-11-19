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
from worldatlas.source_imports.shared.storage import _write_features, geometry_bytes, geometry_hash
from worldatlas.source_imports.run_import import run_import


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
            source_id="raw",
            basis="Selected source point",
            id_field="id",
            selections=[dict(feature_id="point-a", source_feature_id="a")],
        )
        self.store()

    def add_source(self, ident, raw, key):
        self.database.execute(
            "INSERT INTO atlas.source_assets "
            "(id,title,provider,source_uri,license_name,license_uri,attribution,r2_bucket,r2_key,sha256,size_bytes) "
            "VALUES (%s,'Test','Test','test:source','Test','test:license','Test','test',%s,%s,%s)",
            (ident, key, hashlib.sha256(raw).hexdigest(), len(raw)),
        )

    def store(self):
        self.database.execute(
            "INSERT INTO atlas.construction_records(id,method,arguments) VALUES (%s,'selected_vector_features',%s) "
            "ON CONFLICT(id) DO UPDATE SET arguments=EXCLUDED.arguments",
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
            "SELECT id,geometry,construction_id FROM atlas.source_features ORDER BY id"
        ).fetchall()

    def test_repeat_and_recipe_edit_preserve_links_and_other_records(self):
        first = self.build()
        self.database.execute(
            "INSERT INTO atlas.geographic_levels VALUES ('world',NULL)"
        )
        self.database.execute(
            "INSERT INTO atlas.geographic_entities(id,name,level_id,physical_class) VALUES (0,'World','world','mixed')"
        )
        self.database.execute(
            "INSERT INTO atlas.geographic_rules VALUES ('related',0,'nearest_land','land','component',true,'Reference')"
        )
        self.database.execute(
            "INSERT INTO atlas.geographic_rule_features VALUES ('related','point-a','distance_reference')"
        )
        self.recipe.update(basis="Updated explanation", member=None, layer=None)
        self.store()
        self.build()
        after = self.rows()[0]
        self.assertEqual(after[2], "__features")
        self.assertEqual(self.build()["geometry_sha256"], first["geometry_sha256"])
        self.assertEqual(self.storage.get_object.call_count, 1)
        self.assertEqual(
            self.database.execute(
                "SELECT count(*) FROM atlas.geographic_rule_features"
            ).fetchone()[0],
            1,
        )

    def test_missing_construction_rolls_back_the_complete_feature_batch(self):
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
            _write_features(self.database, features, construction_id="missing")
        self.assertEqual(self.rows(), before)

    def test_signed_zero_preserves_longitude_latitude_coordinates(self):
        geometry = {"type": "Point", "coordinates": [-0.0, 1e-24]}
        _write_features(
            self.database,
            [
                dict(
                    feature_id="zero",
                    source_id="raw",
                    source_feature_id="a",
                    geometry=geometry,
                )
            ],
            construction_id="__features",
        )
        self.assertEqual(json.dumps(self.rows()[0][1]["coordinates"]), "[0.0, 1e-24]")

    def test_conflicting_feature_owner_rolls_back_an_earlier_insert(self):
        self.build()
        before = self.rows()
        recipe = dict(self.recipe, selections=[
            dict(feature_id="point-b", source_feature_id="a"),
            dict(feature_id="point-a", source_feature_id="a"),
        ])
        self.database.execute(
            "INSERT INTO atlas.construction_records VALUES ('__other','selected_vector_features',%s)",
            (Jsonb(recipe),),
        )
        with self.assertRaisesRegex(ValueError, "feature ID already belongs to another construction"):
            run_import(lambda: nullcontext(self.database), "__other", storage=self.storage,
                       work_dir=self.work)
        self.assertEqual(self.rows(), before)


class GeometryChecksumTests(unittest.TestCase):
    def test_nested_signed_zero_uses_storage_form_without_mutating_or_rounding(self):
        point = [-0.0, 1e-24]
        for kind, coordinates in (
            ("Point", point),
            ("MultiPoint", [point]),
            ("LineString", [point, [1, 2]]),
            ("MultiLineString", [[point, [1, 2]]]),
            ("Polygon", [[point, [1, 0], [1, 2], point]]),
            ("MultiPolygon", [[[point, [1, 0], [1, 2], point]]]),
        ):
            with self.subTest(kind=kind):
                geometry = dict(type=kind, coordinates=coordinates)
                original = json.dumps(geometry)
                expected = json.loads(original.replace("-0.0", "0.0"))
                expected_bytes = json.dumps(
                    expected, sort_keys=True, separators=(",", ":")
                ).encode()
                self.assertEqual(geometry_bytes(geometry), expected_bytes)
                self.assertEqual(
                    geometry_hash(geometry), hashlib.sha256(expected_bytes).hexdigest()
                )
                self.assertEqual(json.dumps(geometry), original)
        self.assertNotEqual(
            geometry_hash(dict(type="Point", coordinates=[0, 1])),
            geometry_hash(dict(type="Point", coordinates=[0.0, 1])),
        )
