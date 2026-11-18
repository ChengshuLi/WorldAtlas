"""Freeze one coherent dependency selection and validate its executable contracts."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest

import psycopg
from psycopg.types.json import Jsonb

from worldatlas.map_build.inputs.selection import (
    canonical_bytes,
    read_saved,
    read_selection,
    validate_bindings,
)
from worldatlas.map_build.test_support import selection


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.frozen = selection()
        self.geography = self.frozen["geography"]
        self.geography["entities"].append(
            dict(
                id=2,
                name="Asia",
                parent_id=0,
                level_id="continent",
                physical_class="mixed",
                color_rgb="#123456",
            )
        )
        self.geography["category_bindings"] = [
            dict(code=18, entity_id=2, physical_class="land"),
            dict(code=2, entity_id=2, physical_class="water"),
        ]

    def test_duplicate_code_or_entity_class_and_missing_entity_fail(self):
        for bad in (
            dict(code=18, entity_id=2, physical_class="water"),
            dict(code=4, entity_id=2, physical_class="land"),
            dict(code=4, entity_id=999, physical_class="land"),
        ):
            geography = deepcopy(self.geography)
            geography["category_bindings"].append(bad)
            with self.assertRaisesRegex(ValueError, "category binding"):
                validate_bindings(geography)

    def test_saved_values_are_read_without_querying_neon(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "selection.json"
            path.write_bytes(canonical_bytes(self.frozen))
            self.assertEqual(read_saved(path), self.frozen)
            self.frozen["schema"] = "worldatlas-input-selection-v1"
            path.write_text(json.dumps(self.frozen))
            with self.assertRaisesRegex(ValueError, "captured implementation"):
                read_saved(path)


@unittest.skipUnless(
    os.environ.get("WORLDATLAS_TEST_DATABASE_URL"), "requires disposable PostgreSQL"
)
class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.url = os.environ["WORLDATLAS_TEST_DATABASE_URL"]
        self.writer = psycopg.connect(self.url, autocommit=True)
        self.addCleanup(self.writer.close)
        self.addCleanup(self.remove)
        self.geometry = dict(type="Point", coordinates=[10.0, 20.0])
        self.recipe = dict(
            source_id="__selection_raw",
            basis="First",
            id_field="id",
            selections=[
                dict(feature_id="__selection_point", source_feature_id="provider")
            ],
        )
        with self.writer.transaction():
            self.writer.execute(
                "INSERT INTO atlas.geographic_levels VALUES ('world',NULL),('continent','world')"
            )
            self.writer.execute(
                "INSERT INTO atlas.geographic_entities(id,name,level_id,parent_id,physical_class,color_rgb) VALUES (0,'World','world',NULL,'mixed',NULL),(2,'Asia','continent',0,'mixed','#123456')"
            )
            self.writer.execute(
                "INSERT INTO atlas.source_assets(id,title,provider,source_uri,license_name,license_uri,attribution,r2_bucket,r2_key,sha256,size_bytes) VALUES ('__selection_raw','First','Test','test:raw','Test','test:license','Test','test','selected',%s,1)",
                ("a" * 64,),
            )
            self.writer.execute(
                "INSERT INTO atlas.construction_records(id,method,arguments) "
                "VALUES ('__selection_recipe','selected_vector_features',%s)",
                (Jsonb(self.recipe),),
            )
            self.writer.execute(
                "INSERT INTO atlas.source_features VALUES ('__selection_point',%s,'__selection_recipe')",
                (Jsonb(self.geometry),),
            )
            self.writer.execute(
                "INSERT INTO atlas.geographic_rules VALUES ('__selection_rule',0,'assign_area','land','component',false,'Geographic decision')"
            )
            self.writer.execute(
                "INSERT INTO atlas.geographic_rule_features VALUES ('__selection_rule','__selection_point','scope_component')"
            )
            self.writer.execute(
                "INSERT INTO atlas.geographic_rule_targets VALUES ('__selection_target','__selection_rule',2,NULL)"
            )
            self.writer.execute(
                "INSERT INTO atlas.geographic_rule_sources VALUES ('__selection_rule','__selection_raw','Section 1','Supporting geographic interpretation')"
            )

    def remove(self):
        with self.writer.transaction():
            self.writer.execute(
                "DELETE FROM atlas.geographic_rules WHERE id='__selection_rule'"
            )
            self.writer.execute(
                "DELETE FROM atlas.source_features WHERE id='__selection_point'"
            )
            self.writer.execute(
                "DELETE FROM atlas.construction_records WHERE id='__selection_recipe'"
            )
            self.writer.execute(
                "DELETE FROM atlas.source_assets WHERE id='__selection_raw'"
            )
            self.writer.execute(
                "DELETE FROM atlas.map_category_bindings WHERE entity_id=2"
            )
            self.writer.execute(
                "DELETE FROM atlas.geographic_entities WHERE id IN (0,2)"
            )
            self.writer.execute(
                "DELETE FROM atlas.geographic_levels WHERE id IN ('world','continent')"
            )

    def read(self, **kwargs):
        with psycopg.connect(self.url) as database:
            result = read_selection(database, **kwargs)
            self.assertEqual(
                database.info.transaction_status, psycopg.pq.TransactionStatus.IDLE
            )
            return result

    def test_geometry_construction_raw_metadata_and_links_are_frozen(self):
        frozen = self.read()
        geography = frozen["geography"]
        self.assertEqual(geography["features"][0]["geometry"], self.geometry)
        self.assertEqual(
            frozen["construction_records"],
            [dict(id="__selection_recipe", method="selected_vector_features", arguments=self.recipe)],
        )
        self.assertEqual(frozen["raw_sources"][0]["sha256"], "a" * 64)
        self.assertEqual(geography["rule_sources"][0]["source_id"], "__selection_raw")
        self.assertEqual(
            {(b["entity_id"], b["physical_class"]) for b in geography["category_bindings"]},
            {(2, "land"), (2, "water")},
        )
        first = canonical_bytes(frozen)
        self.writer.execute(
            'UPDATE atlas.source_features SET geometry=\' {"type":"Point","coordinates":[11,21]}\' WHERE id=\'__selection_point\''
        )
        self.assertEqual(canonical_bytes(frozen), first)
        self.assertEqual(
            self.read()["geography"]["features"][0]["geometry"]["coordinates"], [11, 21]
        )

    def test_repeatable_read_never_mixes_concurrent_edits(self):
        writer = self.writer

        class Interleave:
            def __init__(self, database):
                self.database = database
                self.changed = False

            def __getattr__(self, name):
                return getattr(self.database, name)

            def execute(self, query, *args):
                cursor = self.database.execute(query, *args)
                if "WITH selected_rules" in query and not self.changed:
                    self.changed = True
                    with writer.transaction():
                        writer.execute(
                            'UPDATE atlas.source_features SET geometry=\'{"type":"Point","coordinates":[11,21]}\' WHERE id=\'__selection_point\''
                        )
                        writer.execute(
                            "UPDATE atlas.source_assets SET title='Second' WHERE id='__selection_raw'"
                        )
                        writer.execute(
                            "UPDATE atlas.construction_records SET arguments=arguments||'{\"basis\":\"Second\"}' WHERE id='__selection_recipe'"
                        )
                return cursor

        with psycopg.connect(self.url) as database:
            frozen = read_selection(Interleave(database))
        self.assertEqual(frozen["geography"]["features"][0]["geometry"], self.geometry)
        self.assertEqual(frozen["raw_sources"][0]["title"], "First")
        self.assertEqual(
            frozen["construction_records"][0]["arguments"]["basis"], "First"
        )
        self.assertEqual(
            self.read()["construction_records"][0]["arguments"]["basis"], "Second"
        )

    def test_requested_missing_raw_source_fails(self):
        with self.assertRaisesRegex(ValueError, "missing"):
            self.read(raw_sources=["absent"])


@unittest.skipUnless(
    os.environ.get("WORLDATLAS_TEST_DATABASE_URL"), "requires disposable PostgreSQL"
)
class HierarchyConcurrencyTests(unittest.TestCase):
    def test_parent_edit_and_child_insert_cannot_commit_an_incompatible_family(self):
        url = os.environ["WORLDATLAS_TEST_DATABASE_URL"]
        started = threading.Event()
        with psycopg.connect(url, autocommit=True) as setup:
            with setup.transaction():
                setup.execute(
                    "INSERT INTO atlas.geographic_levels VALUES ('world',NULL),('continent','world')"
                )
                setup.execute(
                    "INSERT INTO atlas.geographic_entities(id,name,level_id,physical_class) VALUES (0,'World','world','mixed')"
                )
            try:
                with psycopg.connect(url) as parent:
                    parent.execute(
                        "UPDATE atlas.geographic_entities SET physical_class='land' WHERE id=0"
                    )

                    def insert():
                        try:
                            with psycopg.connect(url) as child:
                                child.execute(
                                    "INSERT INTO atlas.geographic_entities(id,name,level_id,parent_id,physical_class) VALUES (7,'Atlantic','continent',0,'water')"
                                )
                                started.set()
                            return "committed"
                        except psycopg.errors.RaiseException:
                            return "rejected"

                    with ThreadPoolExecutor(max_workers=1) as pool:
                        future = pool.submit(insert)
                        self.assertTrue(started.wait(5))
                        parent.commit()
                        self.assertEqual(future.result(timeout=5), "rejected")
            finally:
                with setup.transaction():
                    setup.execute(
                        "DELETE FROM atlas.geographic_entities WHERE id IN (0,7)"
                    )
                    setup.execute(
                        "DELETE FROM atlas.geographic_levels WHERE id IN ('world','continent')"
                    )
