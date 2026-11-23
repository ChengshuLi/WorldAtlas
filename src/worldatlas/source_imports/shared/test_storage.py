"""Working feature imports preserve relationships and save each calculation atomically."""

from contextlib import nullcontext
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import psycopg
from psycopg.types.json import Jsonb
from worldatlas.source_imports.shared.runtime import Runtime
from worldatlas.source_imports.shared.storage import save_features
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
        self.enterContext(patch("boto3.client", return_value=self.storage))
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
            "INSERT INTO atlas.construction_records(id,method,arguments,basis) "
            "VALUES (%s,'selected_vector_features',%s,'Selected source point') "
            "ON CONFLICT(id) DO UPDATE SET arguments=EXCLUDED.arguments",
            ("__features", Jsonb(self.recipe)),
        )

    def build(self):
        return run_import(
            lambda: nullcontext(self.database),
            "__features",
            work_dir=self.work,
        )

    def rows(self):
        return self.database.execute(
            "SELECT id,geometry,construction_id FROM atlas.source_features ORDER BY id"
        ).fetchall()

    def test_repeat_and_recipe_edit_preserve_links_and_other_records(self):
        self.assertEqual(self.build()["feature_ids"], ["point-a"])
        before = self.rows()
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
        self.recipe.update(member=None, layer=None)
        self.store()
        self.build()
        self.assertEqual(self.rows(), before)
        self.assertEqual(self.storage.get_object.call_count, 1)
        self.assertEqual(
            self.database.execute(
                "SELECT count(*) FROM atlas.geographic_rule_features"
            ).fetchone()[0],
            1,
        )

    def save(self, features):
        runtime = Runtime(
            connect=lambda: nullcontext(self.database),
            recipe_id="__features",
            method="selected_vector_features",
            arguments=self.recipe,
        )
        return save_features(runtime, features)

    def test_save_preserves_small_coordinates_and_unselected_features(self):
        self.build()
        geometry = {"type": "Point", "coordinates": [-0.0, 1e-24]}
        self.assertEqual(
            self.save([dict(feature_id="zero", geometry=geometry)]), ["zero"]
        )
        self.assertEqual(
            self.rows(),
            [
                ("point-a", {"type": "Point", "coordinates": [10, 20]}, "__features"),
                ("zero", geometry, "__features"),
            ],
        )

    def test_duplicate_and_blank_ids_leave_existing_geometry_intact(self):
        self.build()
        before = self.rows()
        feature = dict(
            feature_id="point-a", geometry={"type": "Point", "coordinates": [11, 21]}
        )
        for batch in ([], [feature, feature], [dict(feature, feature_id="  ")]):
            with self.assertRaisesRegex(
                ValueError, "feature IDs must be nonempty and unique"
            ):
                self.save(batch)
        self.assertEqual(self.rows(), before)

    def test_conflicting_feature_owner_rolls_back_an_earlier_insert(self):
        self.build()
        before = self.rows()
        recipe = dict(self.recipe, selections=[
            dict(feature_id="point-b", source_feature_id="a"),
            dict(feature_id="point-a", source_feature_id="a"),
        ])
        self.database.execute(
            "INSERT INTO atlas.construction_records(id,method,arguments,basis) "
            "VALUES ('__other','selected_vector_features',%s,'Select the fixture point')",
            (Jsonb(recipe),),
        )
        with self.assertRaisesRegex(ValueError, "feature ID already belongs to another construction"):
            run_import(lambda: nullcontext(self.database), "__other",
                       work_dir=self.work)
        self.assertEqual(self.rows(), before)
