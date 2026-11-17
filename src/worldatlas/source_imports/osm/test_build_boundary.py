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
from worldatlas.source_imports.features.geometry import save_features
from worldatlas.source_imports.atlas_sources.catalog import catalog_source


def save_boundary(database, geometry, source, recipe):
    with database.transaction():
        catalog_source(database, source["source_id"])
        return save_features(
            database,
            [
                dict(
                    feature_id=recipe["feature_id"],
                    source_feature_id=recipe["source_feature_id"],
                    geometry=geometry,
                )
            ],
            recipe,
        )


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
                "(id,title,provider,source_uri,license_name,license_uri,attribution,r2_bucket,r2_key,sha256,size_bytes) "
                "VALUES (%s,'Test','Test','test:source','Test','test:license','Test','test',%s,%s,%s)",
                (ident, label + ".zip", source["sha256"], source["size_bytes"]),
            )
        self.source = dict(source_id="osm-test-1")
        self.recipe = dict(
            method="osm_way_chain",
            source_id="osm-test-1",
            feature_id="border",
            source_feature_id="manifest.json",
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
            "INSERT INTO atlas.construction_records VALUES (%s,%s) ON CONFLICT(id) DO UPDATE SET document=EXCLUDED.document",
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
            "SELECT geometry,construction_id FROM atlas.source_features WHERE id='border'"
        ).fetchone()

    def links(self):
        return self.database.execute(
            "SELECT source_id FROM atlas.construction_sources WHERE construction_id='__osm_recipe' ORDER BY source_id"
        ).fetchall()

    def test_build_repeat_and_edit_recipe(self):
        first = self.build()
        self.assertEqual(self.build(), first)
        self.assertEqual(self.storage.get_object.call_count, 1)
        self.recipe.update(source_id="osm-test-2", basis="New source")
        self.store()
        self.build()
        self.assertEqual(self.boundary()[0]["coordinates"], [[0.0, 0.0], [2.0, 2.0]])
        self.assertEqual(self.boundary()[1:], ("__osm_recipe",))
        self.assertEqual(self.links(), [("osm-test-2",)])

    def test_chain_feature_preserves_source_vertices_and_builds_extensions_once(self):
        self.recipe = dict(
            method="osm_way_chain",
            source_id="osm-test-1",
            feature_id="complete-boundary",
            source_feature_id="manifest.json",
            basis="Preserve source chain and add selected geodesic extensions",
            before=[[-1, 0]],
            after=[[2, 1]],
            max_step_metres=100000,
            evidence_source_ids=["osm-test-2"],
        )
        self.store()
        first = self.build()
        self.assertEqual(self.build(), first)
        geometry = self.database.execute(
            "SELECT geometry FROM atlas.source_features WHERE id='complete-boundary'"
        ).fetchone()[0]
        self.assertEqual(self.build(expected=first["sha256"]), first)
        points = geometry["coordinates"]
        self.assertEqual(points[0], [-1, 0])
        self.assertEqual(points[-1], [2, 1])
        start = points.index([0, 0])
        self.assertEqual(points[start : start + 2], [[0, 0], [1, 1]])
        refs = self.database.execute(
            "SELECT source_id FROM atlas.construction_sources WHERE construction_id='__osm_recipe' ORDER BY source_id"
        ).fetchall()
        self.assertEqual(refs, [("osm-test-1",), ("osm-test-2",)])
        self.assertEqual(self.storage.get_object.call_count, 1)
        self.recipe["before"] = [[0, 0]]
        self.store()
        with self.assertRaises(ValueError):
            self.build()
        self.assertEqual(
            self.database.execute(
                "SELECT geometry FROM atlas.source_features WHERE id='complete-boundary'"
            ).fetchone()[0],
            geometry,
        )

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
                "UPDATE atlas.construction_records SET document=document || '{\"basis\":\"Edited concurrently\"}' WHERE id='__osm_recipe'"
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
        with self.assertRaisesRegex(ValueError, "missing from the Neon catalog"):
            save_boundary(
                self.database,
                {"type": "LineString", "coordinates": [[0, 0], [2, 2]]},
                dict(source_id="missing"),
                self.recipe,
            )
        self.assertEqual(self.boundary(), before)
        self.assertEqual(self.links(), [("osm-test-1",)])

    def test_changed_vertex_count_preserves_other_features(self):
        self.build()
        geometry = {"type": "LineString", "coordinates": [[0, 0], [0.4, 0.6], [1, 1]]}
        save_boundary(self.database, geometry, self.source, self.recipe)
        self.assertEqual(self.boundary()[0], geometry)


if __name__ == "__main__":
    unittest.main()
