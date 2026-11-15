"""IHO route imports retain exact endpoints and commit linked records together."""

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
from worldatlas.source_imports.run_import import run_import
from worldatlas.source_imports.features.geometry import save_features
from worldatlas.source_imports.iho.s130 import extract_routes
from worldatlas.source_imports.iho.test_s130 import fixture


@unittest.skipUnless(
    os.environ.get("WORLDATLAS_TEST_DATABASE_URL"), "requires disposable PostgreSQL"
)
class BuildTests(unittest.TestCase):
    def setUp(self):
        self.database = psycopg.connect(os.environ["WORLDATLAS_TEST_DATABASE_URL"])
        self.addCleanup(self.database.close)
        self.addCleanup(self.database.rollback)
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.work = Path(temp.name)
        self.path, self.digest, self.recipe = fixture(self.work)
        self.recipe.pop("source_version", None)
        self.source = dict(source_id=self.recipe["source_id"], sha256=self.digest)
        raw = self.path.read_bytes()
        self.database.execute(
            "INSERT INTO atlas.source_assets(id,title,provider,source_uri,license_name,license_uri,attribution,r2_bucket,r2_key,sha256,size_bytes) VALUES (%s,'Test','Test','test:source','Test','test:license','Test','test','source.zip',%s,%s)",
            (self.source["source_id"], self.digest, len(raw)),
        )
        self.store()
        self.storage = Mock()
        self.storage.get_object.side_effect = lambda **kw: {"Body": io.BytesIO(raw)}

    def store(self):
        self.database.execute(
            "INSERT INTO atlas.construction_records VALUES ('routes',%s) ON CONFLICT(id) DO UPDATE SET document=EXCLUDED.document",
            (Jsonb(self.recipe),),
        )

    def build(self):
        return run_import(
            lambda: nullcontext(self.database),
            "routes",
            storage=self.storage,
            work_dir=self.work / "downloads",
        )

    def rows(self):
        return self.database.execute('SELECT * FROM atlas.source_features ORDER BY id').fetchall()

    def test_build_and_cached_repeat(self):
        result=self.build()
        before=self.rows()
        self.assertEqual(self.build(),result)
        self.assertEqual(self.rows(),before)
        self.assertEqual(self.storage.get_object.call_count,1)
        geometry=self.database.execute("SELECT geometry FROM atlas.source_features WHERE id='route-a'").fetchone()[0]
        self.assertEqual(geometry['coordinates'][0],[40,30])
        self.assertIn([30,20],geometry['coordinates'])

    def test_recipe_edit_preserves_partition_reference(self):
        self.build()
        self.database.execute("INSERT INTO atlas.geographic_entities(id,name,level) VALUES (81,'A','continent'),(42,'B','continent')")
        self.database.execute("INSERT INTO atlas.geographic_partitions(id,method,feature_id,side_a_entity_id,side_b_entity_id,rationale) VALUES ('p','ocean_barrier','route-a',81,42,'Selected source divider')")
        self.recipe['basis']='Updated description'
        self.store()
        self.build()
        self.assertEqual(self.database.execute("SELECT feature_id FROM atlas.geographic_partitions WHERE id='p'").fetchone()[0],'route-a')

    def test_link_failure_rolls_back_the_entire_import(self):
        self.build()
        before=self.rows()
        features=extract_routes(self.path,self.digest,self.recipe)
        features[0]['source_feature_id']='must roll back'
        features[1]['source_feature_id']=None
        with self.assertRaises(psycopg.errors.NotNullViolation):
            save_features(self.database,features,dict(recipe_id='routes'))
        self.assertEqual(self.rows(),before)

    def test_corrupt_archive_does_not_save(self):
        self.storage.get_object.side_effect = lambda **kw: {"Body": io.BytesIO(b"bad")}
        with self.assertRaisesRegex(ValueError, "size or hash"):
            self.build()
        self.assertEqual(self.rows(), [])
