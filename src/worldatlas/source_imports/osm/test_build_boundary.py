"""OSM archive imports, editable recipes, atomic saves and concurrent region validation."""

from contextlib import nullcontext
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
import zipfile
import psycopg
from psycopg.types.json import Jsonb
from worldatlas.source_imports.run_import import run_import
from worldatlas.source_imports.osm.build_boundary import save_boundary


def source_fixture(endpoint=(1, 1), *, coordinates=None):
    points = coordinates if coordinates is not None else [(0, 0), endpoint]
    elements = [
        {"type": "node", "id": i, "lon": x, "lat": y}
        for i, (x, y) in enumerate(points, 1)
    ]
    elements.append({"type": "way", "id": 3, "nodes": list(range(1, len(points) + 1))})
    response = json.dumps({"elements": elements}).encode()
    manifest = {
        "start_node": 1,
        "ways": [
            {"id": 3, "file": "3.json", "sha256": hashlib.sha256(response).hexdigest()}
        ],
    }
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        archive.writestr("3.json", response)
    raw = output.getvalue()
    return raw, {
        "source_id": "osm-test",
        "version": "1",
        "r2_bucket": "test",
        "r2_key": "source.zip",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
    }


@unittest.skipUnless(
    os.environ.get("WORLDATLAS_TEST_DATABASE_URL"), "requires disposable PostgreSQL"
)
class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.database = psycopg.connect(os.environ["WORLDATLAS_TEST_DATABASE_URL"])
        self.addCleanup(self.database.close)
        self.addCleanup(self.database.rollback)
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name)
        self.responses = {}
        for label, endpoint in [("1", (1, 1)), ("2", (2, 2))]:
            raw, source = source_fixture(endpoint)
            ident = "osm-test-" + label
            self.responses[label + ".zip"] = raw
            self.database.execute(
                "INSERT INTO atlas.source_assets "
                "(source_id,title,provider,source_uri,license_name,license_uri,attribution,r2_bucket,r2_key,sha256,size_bytes) "
                "VALUES (%s,'Test','Test','test:source','Test','test:license','Test','test',%s,%s,%s)",
                (ident, label + ".zip", source["sha256"], source["size_bytes"]),
            )
        self.source = dict(source_id="osm-test-1")
        self.recipe = dict(
            method="osm_way_chain",
            source_id="osm-test-1",
            boundary_id="border",
            basis="Test construction description",
            recipe_id="__osm_recipe",
        )
        self.store()
        self.storage = Mock()
        self.storage.get_object.side_effect = lambda **kw: {
            "Body": io.BytesIO(self.responses[kw["Key"]])
        }

    def store(self):
        self.database.execute(
            "INSERT INTO atlas.construction_records VALUES (%s,%s) ON CONFLICT(source_id) DO UPDATE SET document=EXCLUDED.document",
            (
                "__osm_recipe",
                Jsonb({k: v for k, v in self.recipe.items() if k != "recipe_id"}),
            ),
        )

    def build(self, expected=None):
        return run_import(
            lambda: nullcontext(self.database),
            "__osm_recipe",
            storage=self.storage,
            work_dir=self.directory,
            expected_geometry_sha256=expected,
        )

    def boundary(self):
        return self.database.execute(
            "SELECT geometry,geometry_sha256,provenance,construction_id FROM atlas.decision_mainland_boundaries WHERE boundary_id='border'"
        ).fetchone()

    def links(self):
        return self.database.execute(
            "SELECT source_id,relationship FROM atlas.decision_mainland_boundary_sources WHERE boundary_id='border' ORDER BY source_id"
        ).fetchall()

    def test_build_repeat_and_edit_recipe(self):
        first = self.build()
        self.assertEqual(self.build(), first)
        self.assertEqual(self.storage.get_object.call_count, 1)
        self.database.execute(
            'UPDATE atlas.decision_mainland_boundaries SET provenance=provenance || \'{"note":"keep"}\''
        )
        self.recipe.update(source_id="osm-test-2", basis="New source")
        self.store()
        self.build()
        self.assertEqual(self.boundary()[0]["coordinates"], [[0.0, 0.0], [2.0, 2.0]])
        self.assertEqual(self.boundary()[2]["note"], "keep")
        self.assertEqual(self.links(), [("osm-test-2", "construction_input")])

    def test_expected_geometry_mismatch_preserves_existing_boundary(self):
        self.build()
        before = self.boundary()
        with self.assertRaisesRegex(ValueError, "expected geometry"):
            self.build(expected="0" * 64)
        self.assertEqual(self.boundary(), before)

    def test_recipe_edit_during_calculation_does_not_save_stale_geometry(self):
        from unittest.mock import patch
        from worldatlas.source_imports.osm.ways import assemble_archive

        self.build()
        before = self.boundary()

        def calculate(*args):
            self.database.execute(
                "UPDATE atlas.construction_records SET document=document || '{\"basis\":\"Edited concurrently\"}' WHERE source_id='__osm_recipe'"
            )
            return assemble_archive(*args)

        with patch(
            "worldatlas.source_imports.osm.build_boundary.assemble_archive",
            side_effect=calculate,
        ):
            with self.assertRaisesRegex(
                ValueError, "construction changed during calculation"
            ):
                self.build()
        self.assertEqual(self.boundary(), before)

    def test_corrupt_source_does_not_write(self):
        self.responses["1.zip"] = b"corrupt"
        with self.assertRaisesRegex(ValueError, "size or hash"):
            self.build()
        self.assertIsNone(self.boundary())

    def test_missing_source_rolls_back_boundary_and_links(self):
        self.build()
        before = self.boundary()
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            save_boundary(
                self.database,
                {"type": "LineString", "coordinates": [[0, 0], [2, 2]]},
                dict(source_id="missing"),
                self.recipe,
            )
        self.assertEqual(self.boundary(), before)
        self.assertEqual(self.links(), [("osm-test-1", "construction_input")])

    def test_working_export_contains_saved_boundary_coordinates(self):
        from worldatlas.map_build.inputs.selection import read_selection

        self.build()
        self.database.commit()
        try:
            with psycopg.connect(os.environ["WORLDATLAS_TEST_DATABASE_URL"]) as db:
                selected = read_selection(db)
            line = next(
                b
                for b in selected["geography"]["mainland_boundaries"]
                if b["boundary_id"] == "border"
            )
            self.assertEqual(line["geometry"], self.boundary()[0])
        finally:
            self.database.rollback()
            with self.database.transaction():
                self.database.execute(
                    "DELETE FROM atlas.decision_mainland_boundary_sources"
                )
                self.database.execute("DELETE FROM atlas.decision_mainland_boundaries")
                self.database.execute("DELETE FROM atlas.construction_records")
                self.database.execute("DELETE FROM atlas.source_assets")

    def region_fixture(self):
        self.build()
        save_boundary(
            self.database,
            {"type": "LineString", "coordinates": [[1.0, 1.0], [1.0, 0.0], [0.0, 0.0]]},
            self.source,
            dict(self.recipe, boundary_id="return"),
        )
        self.database.execute(
            "INSERT INTO atlas.decision_mainland_seed_regions VALUES ('region','[]')"
        )
        self.database.execute(
            "INSERT INTO atlas.decision_mainland_region_segments VALUES "
            "('region',0,'boundary','border',NULL,false),"
            "('region',1,'boundary','return',NULL,false)"
        )

    def region_sections(self):
        return self.database.execute(
            "SELECT * FROM atlas.decision_mainland_region_segments ORDER BY ordinal"
        ).fetchall()

    def test_changed_vertex_count_needs_no_region_reference_updates(self):
        self.region_fixture()
        sections = self.region_sections()
        geometry = {
            "type": "LineString",
            "coordinates": [[0.0, 0.0], [0.4, 0.6], [1.0, 1.0]],
        }
        save_boundary(self.database, geometry, self.source, self.recipe)
        self.assertEqual(self.boundary()[0], geometry)
        self.assertEqual(self.region_sections(), sections)

    def test_broken_region_join_rolls_back_boundary_and_source_links(self):
        self.region_fixture()
        before, sections = self.boundary(), self.region_sections()
        with self.assertRaisesRegex(ValueError, "does not join"):
            save_boundary(
                self.database,
                {
                    "type": "LineString",
                    "coordinates": [[0.0, 0.0], [0.4, 0.6], [2.0, 2.0]],
                },
                self.source,
                self.recipe,
            )
        self.assertEqual(self.boundary(), before)
        self.assertEqual(self.links(), [("osm-test-1", "construction_input")])
        self.assertEqual(self.region_sections(), sections)

    def test_simple_boundary_crossing_another_region_section_rolls_back(self):
        from shapely.geometry import LineString, Polygon

        self.region_fixture()
        before, sections = self.boundary(), self.region_sections()
        coordinates = [[0.0, 0.0], [2.0, 0.5], [1.0, 1.0]]
        self.assertTrue(LineString(coordinates).is_simple)
        self.assertFalse(Polygon([*coordinates, [1.0, 0.0], [0.0, 0.0]]).is_valid)
        with self.assertRaisesRegex(ValueError, "invalid region polygon"):
            save_boundary(
                self.database,
                {"type": "LineString", "coordinates": coordinates},
                self.source,
                self.recipe,
            )
        self.assertEqual(self.boundary(), before)
        self.assertEqual(self.links(), [("osm-test-1", "construction_input")])
        self.assertEqual(self.region_sections(), sections)

    def test_parallel_boundary_updates_validate_the_latest_committed_region(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Event
        import time

        import psycopg

        self.region_fixture()
        self.database.commit()

        def cleanup():
            self.database.rollback()
            with self.database.transaction():
                for table in (
                    "decision_mainland_region_segments",
                    "decision_mainland_seed_regions",
                    "decision_mainland_boundary_sources",
                    "decision_mainland_boundaries",
                ):
                    self.database.execute("DELETE FROM atlas." + table)
                self.database.execute(
                    "DELETE FROM atlas.construction_records WHERE source_id='__osm_recipe'"
                )
                self.database.execute(
                    "DELETE FROM atlas.source_assets WHERE source_id LIKE 'osm-test-%'"
                )

        self.addCleanup(cleanup)
        paused, release = Event(), Event()

        class PauseBeforeValidation:
            def __init__(self, database):
                self.database = database

            def transaction(self):
                return self.database.transaction()

            def execute(self, sql, parameters):
                if sql.startswith("SELECT s.reverse,coalesce"):
                    paused.set()
                    if not release.wait(5):
                        raise AssertionError("test did not release the first writer")
                return self.database.execute(sql, parameters)

        first = {
            "type": "LineString",
            "coordinates": [[0.0, 0.0], [0.4, 0.6], [1.0, 1.0]],
        }
        second = {
            "type": "LineString",
            "coordinates": [[1.0, 1.0], [1.2, -0.2], [0.0, 0.0]],
        }

        def write(database, geometry, boundary_id):
            return save_boundary(
                database,
                geometry,
                self.source,
                dict(self.recipe, boundary_id=boundary_id),
            )

        url = os.environ["WORLDATLAS_TEST_DATABASE_URL"]
        with (
            psycopg.connect(url) as a,
            psycopg.connect(url) as b,
            psycopg.connect(url, autocommit=True) as observer,
            ThreadPoolExecutor(2) as workers,
        ):
            try:
                first_result = workers.submit(
                    write, PauseBeforeValidation(a), first, "border"
                )
                self.assertTrue(paused.wait(5))
                second_result = workers.submit(write, b, second, "return")
                deadline = time.monotonic() + 5
                while not second_result.done():
                    blockers = observer.execute(
                        "SELECT pg_blocking_pids(%s)", (b.info.backend_pid,)
                    ).fetchone()[0]
                    if a.info.backend_pid in blockers:
                        break
                    if time.monotonic() >= deadline:
                        self.fail(
                            "second writer neither completed nor waited for the first writer"
                        )
                    release.wait(0.01)
            finally:
                release.set()
            first_result.result(timeout=5)
            second_result.result(timeout=5)

        from shapely.geometry import Polygon

        saved = dict(
            self.database.execute(
                "SELECT boundary_id,geometry FROM atlas.decision_mainland_boundaries "
            ).fetchall()
        )
        self.assertEqual(saved, {"border": first, "return": second})
        self.assertTrue(
            Polygon(
                [*saved["border"]["coordinates"], *saved["return"]["coordinates"][1:]]
            ).is_valid
        )
