"""OSM way imports, editable recipes and atomic saves."""

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
from worldatlas.source_imports.shared.storage import _write_features
from worldatlas.source_assets.catalog import catalog_sources


def save_boundary(database, geometry, source, recipe):
    with database.transaction():
        catalog_sources(database, [source["source_id"]])
        _write_features(
            database,
            [
                dict(
                    feature_id=recipe["feature_id"],
                    geometry=geometry,
                )
            ],
            construction_id=recipe["recipe_id"],
        )


def source_fixture(way_id, start_node, points):
    elements = [
        {"type": "node", "id": i, "lon": x, "lat": y}
        for i, (x, y) in enumerate(points, start_node)
    ]
    elements.append({"type": "way", "id": way_id, "nodes": list(range(start_node, start_node + len(points)))})
    return json.dumps({"elements": elements}).encode()


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
        for way_id, start, points in (
            (1, 1, [(0, 0), (1, 1)]),
            (2, 1, [(0, 0), (2, 2)]),
            (3, 2, [(1, 1), (2, 2)]),
        ):
            raw = source_fixture(way_id, start, points)
            ident = f"osm-test-{way_id}"
            key = f"{way_id}.json"
            self.responses[key] = raw
            self.database.execute(
                "INSERT INTO atlas.source_assets "
                "(id,title,provider,source_uri,license_name,license_uri,attribution,r2_bucket,r2_key,sha256,size_bytes) "
                "VALUES (%s,'Test','Test','test:source','Test','test:license','Test','test',%s,%s,%s)",
                (ident, key, hashlib.sha256(raw).hexdigest(), len(raw)),
            )
        self.source = dict(source_id="osm-test-1")
        self.recipe = dict(
            way_source_ids=["osm-test-1"],
            start_node_id=1,
            feature_id="border",
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
            "INSERT INTO atlas.construction_records(id,method,arguments) VALUES (%s,'osm_way_chain',%s) "
            "ON CONFLICT(id) DO UPDATE SET arguments=EXCLUDED.arguments",
            (
                "__osm_recipe",
                Jsonb({k: v for k, v in self.recipe.items() if k != "recipe_id"}),
            ),
        )

    def build(self):
        return run_import(
            lambda: nullcontext(self.database),
            "__osm_recipe",
            storage=self.storage,
            work_dir=self.directory,
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
        self.assertEqual(first, {"feature_id": "border", "vertices": 2})
        before = self.boundary()
        self.assertEqual(before[0]["coordinates"], [[0.0, 0.0], [1.0, 1.0]])
        self.assertEqual(self.build(), first)
        self.assertEqual(self.boundary(), before)
        self.assertEqual(self.storage.get_object.call_count, 1)
        self.recipe.update(way_source_ids=["osm-test-2"], basis="New source")
        self.store()
        self.build()
        self.assertEqual(self.boundary()[0]["coordinates"], [[0.0, 0.0], [2.0, 2.0]])
        self.assertEqual(self.boundary()[1:], ("__osm_recipe",))
        self.assertEqual(self.links(), [("osm-test-2",)])

    def test_chain_uses_both_cataloged_responses_in_endpoint_order(self):
        self.recipe.update(way_source_ids=["osm-test-3", "osm-test-1"])
        self.store()
        self.build()
        self.assertEqual(self.boundary()[0]["coordinates"], [[0, 0], [1, 1], [2, 2]])
        self.assertEqual(self.links(), [("osm-test-1",), ("osm-test-3",)])
        self.assertEqual(self.storage.get_object.call_count, 2)

    def test_evidence_source_is_linked_without_downloading_it(self):
        self.recipe.update(evidence_source_ids=["osm-test-2"])
        self.store()
        self.build()
        self.assertEqual(self.links(), [("osm-test-1",), ("osm-test-2",)])
        self.storage.get_object.assert_called_once_with(Bucket="test", Key="1.json")

    def test_recipe_edit_during_calculation_does_not_save_stale_geometry(self):
        from unittest.mock import patch
        from worldatlas.source_imports.osm.ways import assemble

        self.build()
        before = self.boundary()

        def calculate(*args):
            self.database.execute(
                "UPDATE atlas.construction_records SET arguments=arguments || '{\"basis\":\"Edited concurrently\"}' WHERE id='__osm_recipe'"
            )
            return assemble(*args)

        with patch(
            "worldatlas.source_imports.osm.ways.assemble",
            side_effect=calculate,
        ):
            with self.assertRaisesRegex(
                ValueError, "construction changed during calculation"
            ):
                self.build()
        self.assertEqual(self.boundary(), before)

    def test_corrupt_source_does_not_write(self):
        self.responses["1.json"] = b"corrupt"
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
