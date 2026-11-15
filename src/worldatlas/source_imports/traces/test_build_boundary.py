"""Editable trace recipes update working geometry without changing earlier snapshots."""

from contextlib import nullcontext
import hashlib
import json
import os
import unittest
import psycopg
from psycopg.types.json import Jsonb
from worldatlas.source_imports.run_import import run_import


@unittest.skipUnless(
    os.environ.get("WORLDATLAS_TEST_DATABASE_URL"), "requires disposable PostgreSQL"
)
class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.db = psycopg.connect(os.environ["WORLDATLAS_TEST_DATABASE_URL"])
        self.addCleanup(self.db.close)
        self.addCleanup(self.db.rollback)
        self.db.execute(
            "INSERT INTO atlas.source_assets(id,title,provider,source_uri,license_name,license_uri,attribution,r2_bucket,r2_key,sha256,size_bytes) VALUES ('raw','Test','Test','test:source','Test','test:license','Test','test','figure.pdf',%s,10)",
            ("a" * 64,),
        )
        self.recipe = dict(
            method="geodesic_trace",
            source_id="raw",
            feature_id="line",
            source_feature_id="Figure 1",
            basis="Chosen points",
            points=[[10.0, 1.0], [9.0, 0.0], [8.0, -1.0]],
            max_step_metres=1000,
        )
        self.store()

    def store(self):
        self.db.execute(
            "INSERT INTO atlas.construction_records VALUES ('trace',%s) ON CONFLICT(id) DO UPDATE SET document=EXCLUDED.document",
            (Jsonb(self.recipe),),
        )

    def build(self):
        return run_import(
            lambda: nullcontext(self.db), "trace"
        )

    def row(self):
        return self.db.execute(
            "SELECT geometry,source_feature_id,construction_id FROM atlas.source_features WHERE id='line'"
        ).fetchone()

    def test_repeat_and_edit_preserve_links_and_old_coordinate_copy(self):
        first = self.build()
        before = self.row()
        self.assertEqual(self.build(), first)
        self.db.execute("INSERT INTO atlas.geographic_entities(id,name,level) VALUES (81,'First','continent'),(42,'Second','continent')")
        self.db.execute("INSERT INTO atlas.geographic_partitions(id,feature_id,bounds_lon_lat,side_a_entity_id,side_a_witness,side_b_entity_id,side_b_witness,rationale) VALUES ('rule','line',ARRAY[0,-10,20,10],81,ARRAY[1,1],42,ARRAY[19,1],'Selected divide')")
        self.recipe["points"] = [[12.0, 1.0], [11.0, 0.0], [10.0, -1.0]]
        self.store()
        self.build()
        self.assertEqual(before[0]["coordinates"][0], [10.0, 1.0])
        self.assertEqual(self.row()[0]["coordinates"][0], [12.0, 1.0])
        self.assertEqual(self.row()[2], "trace")
        self.assertEqual(self.db.execute("SELECT feature_id FROM atlas.geographic_partitions").fetchone()[0], "line")

    def test_bad_source_preserves_previous_geometry(self):
        self.build()
        before = self.row()
        self.recipe["source_id"] = "missing"
        with self.assertRaises(psycopg.errors.ForeignKeyViolation), self.db.transaction():
            self.store()
        self.assertEqual(self.row(), before)

    def test_invalid_points_preserve_previous_geometry(self):
        self.build()
        before = self.row()
        self.recipe["points"] = [[0, 0], [0, 0]]
        self.store()
        with self.assertRaises(ValueError):
            self.build()
        self.assertEqual(self.row(), before)

    def test_signed_zero_hash_matches_stored_json(self):
        self.recipe["points"] = [[10.0, -0.0], [9.0, -1.0]]
        self.store()
        result = self.build()
        raw = json.dumps(
            self.row()[0], sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), result["sha256"])

    def test_description_does_not_change_geometry(self):
        first = self.build()
        self.recipe["source_location"] = "Figure caption"
        self.store()
        self.assertEqual(self.build(), first)
