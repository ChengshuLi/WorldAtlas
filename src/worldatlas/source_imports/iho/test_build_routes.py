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
from worldatlas.source_imports.iho.build_routes import save_routes
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
            "INSERT INTO atlas.source_assets(source_id,title,provider,source_uri,license_name,license_uri,attribution,r2_bucket,r2_key,sha256,size_bytes) VALUES (%s,'Test','Test','test:source','Test','test:license','Test','test','source.zip',%s,%s)",
            (self.source["source_id"], self.digest, len(raw)),
        )
        self.store()
        self.storage = Mock()
        self.storage.get_object.side_effect = lambda **kw: {"Body": io.BytesIO(raw)}

    def store(self):
        self.database.execute(
            "INSERT INTO atlas.construction_records VALUES ('routes',%s) ON CONFLICT(source_id) DO UPDATE SET document=EXCLUDED.document",
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
        return [
            self.database.execute(
                "SELECT * FROM atlas." + name + " ORDER BY 1,2"
            ).fetchall()
            for name in (
                "decision_endpoints",
                "decision_routes",
                "decision_route_points",
            )
        ]

    def test_build_and_cached_repeat(self):
        result = self.build()
        before = self.rows()
        self.assertEqual(self.build(), result)
        self.assertEqual(self.rows(), before)
        self.assertEqual(self.storage.get_object.call_count, 1)
        self.assertEqual(
            self.database.execute(
                "SELECT longitude::text,latitude::text FROM atlas.decision_endpoints WHERE endpoint_id='route-a-endpoint-0'"
            ).fetchone(),
            ("40", "30"),
        )

    def test_recipe_edit_preserves_unrelated_notes_and_links(self):
        self.build()
        self.database.execute(
            'UPDATE atlas.decision_endpoints SET evidence=evidence || \'{"note":"keep","selector":"old"}\''
        )
        self.recipe["routes"][0]["endpoint_names"][0] = "Renamed"
        self.store()
        self.build()
        name, evidence = self.database.execute(
            "SELECT name,evidence FROM atlas.decision_endpoints WHERE endpoint_id='route-a-endpoint-0'"
        ).fetchone()
        self.assertEqual(name, "Renamed")
        self.assertEqual(evidence["note"], "keep")
        self.assertNotIn("selector", evidence)

    def test_link_failure_rolls_back_the_entire_import(self):
        self.build()
        before = self.rows()
        result = extract_routes(self.path, self.digest, self.recipe)
        result["endpoints"][0]["name"] = "Must roll back"
        result["routes"][1]["points"][1]["endpoint_id"] = "missing"
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            save_routes(
                self.database,
                result,
                self.source,
                dict(self.recipe, recipe_id="routes"),
            )
        self.assertEqual(self.rows(), before)

    def test_corrupt_archive_does_not_save(self):
        self.storage.get_object.side_effect = lambda **kw: {"Body": io.BytesIO(b"bad")}
        with self.assertRaisesRegex(ValueError, "size or hash"):
            self.build()
        self.assertEqual(self.rows(), [[], [], []])
