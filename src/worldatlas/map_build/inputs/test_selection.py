import json
import os
from pathlib import Path
import tempfile
import unittest
from copy import deepcopy

import psycopg
from psycopg.types.json import Jsonb

from worldatlas.map_build.inputs.selection import (
    entity_colors,
    canonical_bytes,
    read_selection,
    read_saved,
    validate_bindings,
)


class BindingTests(unittest.TestCase):
    def setUp(self):
        bindings = [
            dict(code=301, entity_id=81, physical_class="land"),
            dict(code=999, entity_id=42, physical_class="land"),
            dict(code=4321, entity_id=81, physical_class="water"),
        ]
        self.selection = dict(
            schema="worldatlas-input-selection-v1",
            domains={
                name: dict(category_bindings=deepcopy(bindings))
                for name in ("mainland", "regional", "water", "ocean")
            },
        )
        self.selection["domains"]["water"].update(features=[], basins=[])

    def test_reordered_rows_and_different_registry_names_keep_the_same_meanings(self):
        for name, domain in self.selection["domains"].items():
            domain["entity_revision"] = {"id": name}
            domain["category_bindings"].reverse()
        validate_bindings(self.selection["domains"])

    def test_saved_replay_preserves_legacy_document_metadata(self):
        selected = dict(
            self.selection,
            documents=[
                dict(
                    source_id="saved-construction",
                    version="1",
                    document_text=' {"a": 1}\n',
                    sha256="a" * 64,
                    size_bytes=10,
                )
            ],
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "selection.json"
            path.write_text(json.dumps(selected))
            self.assertEqual(read_saved(path), selected)

    def test_replay_rejects_swapped_entity_meanings_in_every_stage(self):
        for name in self.selection["domains"]:
            with self.subTest(stage=name), tempfile.TemporaryDirectory() as directory:
                selected = deepcopy(self.selection)
                bindings = selected["domains"][name]["category_bindings"]
                bindings[0]["entity_id"], bindings[1]["entity_id"] = (
                    bindings[1]["entity_id"],
                    bindings[0]["entity_id"],
                )
                path = Path(directory) / "selection.json"
                path.write_text(json.dumps(selected))
                with self.assertRaisesRegex(ValueError, "category bindings differ"):
                    read_saved(path)

    def test_physical_classes_and_missing_rows_are_part_of_the_mapping(self):
        for change in ("class", "missing"):
            with self.subTest(change=change):
                selected = deepcopy(self.selection)
                bindings = selected["domains"]["regional"]["category_bindings"]
                if change == "class":
                    bindings[1]["physical_class"] = "water"
                else:
                    bindings.pop()
                with self.assertRaisesRegex(ValueError, "category bindings differ"):
                    validate_bindings(selected["domains"])

    def test_duplicate_codes_or_entity_classes_cannot_hide_a_disagreement(self):
        for duplicate in (
            dict(code=301, entity_id=42, physical_class="water"),
            dict(code=123, entity_id=81, physical_class="land"),
        ):
            with self.subTest(binding=duplicate):
                selected = deepcopy(self.selection)
                selected["domains"]["regional"]["category_bindings"].append(duplicate)
                with self.assertRaisesRegex(ValueError, "duplicate category bindings"):
                    validate_bindings(selected["domains"])


@unittest.skipUnless(
    os.environ.get("WORLDATLAS_TEST_DATABASE_URL"), "requires disposable PostgreSQL"
)
class SelectionTests(unittest.TestCase):
    def setUp(self):

        self.url = os.environ["WORLDATLAS_TEST_DATABASE_URL"]
        self.writer = psycopg.connect(self.url, autocommit=True)
        self.addCleanup(self.writer.close)
        self.addCleanup(self.remove)
        self.writer.execute(
            "INSERT INTO atlas.geographic_entities(id,name,level,color_rgb) VALUES (970000001,'Selected entity','continent','#123456')"
        )
        self.writer.execute(
            "INSERT INTO atlas.map_category_bindings VALUES (17,970000001,'land')"
        )
        self.writer.execute(
            "INSERT INTO atlas.source_assets(source_id,title,provider,source_uri,license_name,license_uri,attribution,r2_bucket,r2_key,sha256,size_bytes) VALUES ('__selected_raw','Test','Test','test:source','Test','test:license','Test','test','source.geojson',%s,1)",
            ("a" * 64,),
        )
        self.geometry = {"type": "Point", "coordinates": [10.0, 20.0]}
        self.writer.execute(
            "INSERT INTO atlas.construction_records VALUES ('__selected_recipe',%s)",
            (
                Jsonb(
                    dict(
                        method="selected_vector_features",
                        source_id="__selected_raw",
                        basis="First",
                        id_field="id",
                        selections=[
                            dict(
                                feature_id="__selected_point",
                                source_feature_id="provider",
                            )
                        ],
                    )
                ),
            ),
        )
        self.writer.execute(
            "INSERT INTO atlas.source_features VALUES ('__selected_point','__selected_raw','provider',%s,'__selected_recipe')",
            (Jsonb(self.geometry),),
        )

        self.writer.execute(
            "INSERT INTO atlas.geographic_assignments VALUES ('__selected_assignment',970000001,'A geographic decision',%s)",
            (Jsonb(dict(relation="point_component", feature_id="__selected_point")),),
        )
        self.writer.execute(
            "INSERT INTO atlas.geographic_assignment_sources VALUES ('__selected_assignment','__selected_raw','Section 1','A supporting citation')"
        )

    def remove(self):
        self.writer.execute(
            "DELETE FROM atlas.geographic_assignment_sources WHERE assignment_id='__selected_assignment'"
        )
        self.writer.execute(
            "DELETE FROM atlas.geographic_assignments WHERE assignment_id='__selected_assignment'"
        )
        self.writer.execute(
            "DELETE FROM atlas.source_features WHERE feature_id='__selected_point'"
        )
        self.writer.execute(
            "DELETE FROM atlas.construction_records WHERE source_id='__selected_recipe'"
        )
        self.writer.execute(
            "DELETE FROM atlas.source_assets WHERE source_id='__selected_raw'"
        )
        self.writer.execute(
            "DELETE FROM atlas.map_category_bindings WHERE entity_id=970000001"
        )
        self.writer.execute("DELETE FROM atlas.geographic_entities WHERE id=970000001")

    def read(self, **options):
        with psycopg.connect(self.url) as db:
            result = read_selection(db, **options)
            self.assertEqual(
                db.info.transaction_status, psycopg.pq.TransactionStatus.IDLE
            )
            return result

    def test_freezes_coordinates_catalog_bindings_and_colors(self):
        selected = self.read()
        self.assertEqual(selected["schema"], "worldatlas-input-selection-v3")
        self.assertNotIn("revisions", selected)
        self.assertEqual(
            selected["geography"]["features"][0]["geometry"], self.geometry
        )
        self.assertEqual(selected["raw_sources"][0]["sha256"], "a" * 64)
        self.assertEqual(
            entity_colors(selected), [dict(entity_id=970000001, color_rgb="#123456")]
        )

    def test_freezes_assignments_and_citations_without_case_or_evidence_copies(self):
        selected = self.read()["geography"]
        self.assertNotIn("affiliations", selected)
        self.assertNotIn("cases", selected)
        self.assertNotIn("case_sources", selected)
        self.assertEqual(
            selected["assignments"],
            [
                dict(
                    assignment_id="__selected_assignment",
                    entity_id=970000001,
                    rationale="A geographic decision",
                    selection=dict(
                        relation="point_component", feature_id="__selected_point"
                    ),
                )
            ],
        )
        self.assertEqual(
            selected["assignment_sources"][0]["source_id"], "__selected_raw"
        )

    def test_later_working_edit_does_not_change_saved_inputs(self):
        first = self.read()

        changed = {"type": "Point", "coordinates": [11.0, 21.0]}
        self.writer.execute(
            "UPDATE atlas.source_features SET geometry=%s WHERE feature_id=%s",
            (Jsonb(changed), "__selected_point"),
        )
        second = self.read()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "selection.json"
            path.write_bytes(canonical_bytes(first))
            restored = read_saved(path)
        self.assertEqual(
            restored["geography"]["features"][0]["geometry"], self.geometry
        )
        self.assertEqual(second["geography"]["features"][0]["geometry"], changed)

    def test_construction_edits_are_copied_into_each_build(self):
        first = self.read()
        self.writer.execute(
            "UPDATE atlas.construction_records SET document=document || '{\"basis\":\"Second\"}' WHERE source_id='__selected_recipe'"
        )
        second = self.read()
        self.assertEqual(first["construction_records"][0]["document"]["basis"], "First")
        self.assertEqual(
            second["construction_records"][0]["document"]["basis"], "Second"
        )

    def test_missing_explicit_inputs_fail(self):
        for options in (dict(raw_sources=["missing"]), dict(constructions=["missing"])):
            with (
                self.subTest(options=options),
                self.assertRaisesRegex(ValueError, "missing"),
            ):
                self.read(**options)

    def test_concurrent_edits_do_not_mix_database_snapshots(self):
        with psycopg.connect(self.url) as db:
            outer = self

            class ConcurrentEdit:
                def transaction(self):
                    return db.transaction()

                def cursor(self, **kw):
                    return db.cursor(**kw)

                def execute(self, query, params=None):
                    result = db.execute(query, params)
                    if query.startswith("SELECT to_jsonb(a)"):
                        outer.writer.execute(
                            "UPDATE atlas.geographic_entities SET color_rgb='#654321' WHERE id=970000001"
                        )
                    return result

            first = read_selection(ConcurrentEdit())
        self.assertEqual(entity_colors(first)[0]["color_rgb"], "#123456")
        self.assertEqual(entity_colors(self.read())[0]["color_rgb"], "#654321")


@unittest.skipUnless(
    os.environ.get("WORLDATLAS_TEST_DATABASE_URL"), "requires disposable PostgreSQL"
)
class HierarchyConcurrencyTests(unittest.TestCase):
    def test_parent_change_and_child_insert_cannot_commit_an_invalid_hierarchy(self):
        from concurrent.futures import ThreadPoolExecutor
        import threading
        import time

        url = os.environ["WORLDATLAS_TEST_DATABASE_URL"]
        ids = [970100001, 970100002, 970100003]
        with psycopg.connect(url, autocommit=True) as setup:
            setup.execute(
                "INSERT INTO atlas.geographic_entities(id,name,level) VALUES (%s,'First','continent'),(%s,'Second','continent')",
                ids[:2],
            )
        try:
            with (
                psycopg.connect(url) as parent,
                psycopg.connect(url) as child,
                psycopg.connect(url, autocommit=True) as observer,
                ThreadPoolExecutor(1) as workers,
            ):
                parent.execute(
                    "UPDATE atlas.geographic_entities SET level='subcontinent',parent_id=%s WHERE id=%s",
                    (ids[1], ids[0]),
                )
                parent.execute("SET CONSTRAINTS ALL IMMEDIATE")

                def add_child():
                    child.execute(
                        "INSERT INTO atlas.geographic_entities(id,name,level,parent_id) VALUES (%s,'Child','subcontinent',%s)",
                        (ids[2], ids[0]),
                    )
                    child.commit()

                result = workers.submit(add_child)
                deadline = time.monotonic() + 5
                while not result.done():
                    blockers = observer.execute(
                        "SELECT pg_blocking_pids(%s)", (child.info.backend_pid,)
                    ).fetchone()[0]
                    if parent.info.backend_pid in blockers:
                        break
                    if time.monotonic() >= deadline:
                        parent.rollback()
                        self.fail(
                            "child insertion did not resolve or wait for the parent edit"
                        )
                    threading.Event().wait(0.01)
                parent.commit()
                with self.assertRaisesRegex(
                    psycopg.errors.RaiseException, "invalid parent level"
                ):
                    result.result(timeout=5)
        finally:
            with psycopg.connect(url) as cleanup:
                cleanup.execute(
                    "DELETE FROM atlas.geographic_entities WHERE id=ANY(%s)", (ids,)
                )
