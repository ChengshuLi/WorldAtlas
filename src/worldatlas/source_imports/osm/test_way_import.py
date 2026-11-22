"""OSM way imports, editable recipes and atomic saves."""

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

from worldatlas.shared.r2 import R2Client
from worldatlas.source_imports.osm.ways import assemble
from worldatlas.source_imports.run_import import run_import


def source_fixture(way_id, start_node, points):
    """Encode a small OSM API response with one way and all its nodes.

    Args:
        way_id: ID of the archived way.
        start_node: First of the consecutive node IDs.
        points: Longitude and latitude pairs in way order.

    Returns:
        Bytes of the JSON response.
    """
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
    """Exercise the way importer with a real database and local R2 responses."""

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
            (2, 1, [(0, 0), (0.4, 0.6), (2, 2)]),
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
        self.recipe = dict(way_source_ids=["osm-test-1"], feature_id="border")
        self.store(self.recipe)
        self.storage = Mock()
        self.storage.get_object.side_effect = lambda **kw: {
            "Body": io.BytesIO(self.responses[kw["Key"]])
        }

    def store(self, arguments, recipe_id="__osm_recipe"):
        """Insert or update a test way-chain recipe.

        Args:
            arguments: Constructor arguments to save.
            recipe_id: ID of the recipe to save.
        """
        self.database.execute(
            "INSERT INTO atlas.construction_records(id,method,arguments,basis) "
            "VALUES (%s,'osm_way_chain',%s,'Test construction description') "
            "ON CONFLICT(id) DO UPDATE SET arguments=EXCLUDED.arguments",
            (recipe_id, Jsonb(arguments)),
        )

    def build(self, recipe_id="__osm_recipe"):
        """Import the saved recipe through the production entry point.

        Args:
            recipe_id: ID of the recipe to import.

        Returns:
            The way importer's result, including its vertex count.
        """
        return run_import(
            lambda: nullcontext(self.database),
            recipe_id,
            storage=R2Client(self.storage),
            work_dir=self.directory,
        )

    def boundary(self, feature_id="border"):
        """Read a saved boundary and its owner.

        Args:
            feature_id: ID of the boundary to read.

        Returns:
            A pair of geometry and construction ID, or None if absent.
        """
        return self.database.execute(
            "SELECT geometry,construction_id FROM atlas.source_features WHERE id=%s",
            (feature_id,),
        ).fetchone()

    def links(self):
        """Return the main test recipe's source links in source ID order."""
        return self.database.execute(
            "SELECT source_id FROM atlas.construction_sources WHERE construction_id='__osm_recipe' ORDER BY source_id"
        ).fetchall()

    def test_repeat_import_reuses_the_cached_way(self):
        first = self.build()
        self.assertEqual(first, {"feature_id": "border", "vertices": 2})
        before = self.boundary()
        self.assertEqual(before[0]["coordinates"], [[0.0, 0.0], [1.0, 1.0]])
        self.assertEqual(self.build(), first)
        self.assertEqual(self.boundary(), before)
        self.assertEqual(self.storage.get_object.call_count, 1)

    def test_changed_vertex_count_preserves_other_features(self):
        self.build()
        self.store(
            dict(way_source_ids=["osm-test-3"], feature_id="other-border"),
            "__other_osm_recipe",
        )
        self.build("__other_osm_recipe")
        other_boundary = self.boundary("other-border")
        self.assertIsNotNone(other_boundary)

        self.recipe.update(way_source_ids=["osm-test-2"])
        self.store(self.recipe)
        self.assertEqual(self.build(), {"feature_id": "border", "vertices": 3})
        self.assertEqual(
            self.boundary(),
            (
                {"type": "LineString", "coordinates": [[0, 0], [0.4, 0.6], [2, 2]]},
                "__osm_recipe",
            ),
        )
        self.assertEqual(self.boundary("other-border"), other_boundary)
        self.assertEqual(self.links(), [("osm-test-2",)])

    def test_chain_uses_both_cataloged_responses_in_endpoint_order(self):
        self.recipe.update(way_source_ids=["osm-test-3", "osm-test-1"])
        self.store(self.recipe)
        self.build()
        self.assertEqual(self.boundary()[0]["coordinates"], [[0, 0], [1, 1], [2, 2]])
        self.assertEqual(self.links(), [("osm-test-1",), ("osm-test-3",)])
        self.assertEqual(self.storage.get_object.call_count, 2)

    def test_evidence_source_is_linked_without_downloading_it(self):
        self.recipe.update(evidence_source_ids=["osm-test-2"])
        self.store(self.recipe)
        self.build()
        self.assertEqual(self.links(), [("osm-test-1",), ("osm-test-2",)])
        self.storage.get_object.assert_called_once_with(Bucket="test", Key="1.json")

    def test_recipe_edit_during_calculation_does_not_save_stale_geometry(self):
        self.build()
        before = self.boundary()

        def calculate(*args):
            self.database.execute(
                "UPDATE atlas.construction_records SET arguments=arguments || '{\"way_source_ids\":[\"osm-test-2\"]}' "
                "WHERE id='__osm_recipe'"
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

    def test_basis_edit_during_calculation_allows_the_save(self):
        def retrieve(*, Bucket, Key):
            self.database.execute(
                "UPDATE atlas.construction_records SET basis='New explanation' WHERE id='__osm_recipe'"
            )
            return {"Body": io.BytesIO(self.responses[Key])}

        self.storage.get_object.side_effect = retrieve
        self.assertEqual(self.build()["feature_id"], "border")
        self.assertEqual(self.boundary()[0]["coordinates"], [[0.0, 0.0], [1.0, 1.0]])
        self.assertEqual(self.database.execute(
            "SELECT basis FROM atlas.construction_records WHERE id='__osm_recipe'"
        ).fetchone(), ("New explanation",))

    def test_corrupt_replacement_source_leaves_previous_boundary_intact(self):
        self.build()
        before = self.boundary()
        self.recipe.update(way_source_ids=["osm-test-2"])
        self.store(self.recipe)
        # Keep the byte count unchanged so the test exercises checksum verification.
        self.responses["2.json"] = self.responses["2.json"].replace(b"0.4", b"0.5")
        with self.assertRaisesRegex(ValueError, "size or hash"):
            self.build()
        self.assertEqual(self.boundary(), before)
        self.assertEqual(self.links(), [("osm-test-2",)])


if __name__ == "__main__":
    unittest.main()
