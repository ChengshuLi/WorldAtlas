from pathlib import Path
import tempfile
import unittest

from shapely.geometry import MultiPolygon, Polygon, shape

from worldatlas.source_imports.osm.features import read_features


class OsmFeatureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "source.osm"
        coordinates = {
            1: (0, 0),
            2: (10, 0),
            3: (10, 10),
            4: (0, 10),
            5: (2, 2),
            6: (3, 2),
            7: (3, 3),
            8: (2, 3),
            20: (20, 0),
            21: (30, 0),
            22: (30, 10),
            23: (20, 10),
            40: (32, 12),
        }
        nodes = [
            f'<node id="{i}" version="1" lon="{lon}" lat="{lat}">'
            '<tag k="name" v="Selected"/></node>'
            for i, (lon, lat) in coordinates.items()
        ]
        ways = []
        for ident, refs in {
            10: [1, 2, 3],
            20: [4, 3],
            30: [4, 1],
            40: [20, 21, 22, 23, 20],
            50: [5, 6, 7, 8, 5],
        }.items():
            ways.append(
                f'<way id="{ident}" version="2">'
                + "".join(f'<nd ref="{n}"/>' for n in refs)
                + "</way>"
            )
        members = "".join(
            f'<member type="way" ref="{i}" role="{role}"/>'
            for i, role in [
                (10, "outer"),
                (20, "outer"),
                (30, "outer"),
                (40, "outer"),
                (50, "inner"),
            ]
        )
        relation = (
            '<relation id="100" version="3">'
            + members
            + '<member type="node" ref="1" role="label"/>'
            '<tag k="type" v="multipolygon"/><tag k="name" v="Selected"/></relation>'
        )
        self.path.write_text(
            '<osm version="0.6">' + "".join(nodes + ways) + relation + "</osm>"
        )
        self.selection = dict(
            feature_id="islands",
            source_feature_id="100",
            object_type="relation",
            expected_tags={"name": "Selected"},
        )

    def read(self, selection=None):
        return read_features(self.path, [selection or self.selection])[0]

    def test_unordered_and_reversed_way_members_join_with_holes_preserved(self):
        result = self.read()
        self.assertEqual(result["geometry"]["type"], "MultiPolygon")
        area = shape(result["geometry"])
        expected = MultiPolygon([
            Polygon(
                [(0, 0), (10, 0), (10, 10), (0, 10)],
                holes=[[(2, 2), (3, 2), (3, 3), (2, 3)]],
            ),
            Polygon([(20, 0), (30, 0), (30, 10), (20, 10)]),
        ])
        self.assertTrue(area.equals(expected))

    def test_label_reference_does_not_require_node_coordinates(self):
        expected = self.read()
        self.path.write_text(
            self.path.read_text().replace('ref="1" role="label"', 'ref="999" role="label"')
        )
        self.assertEqual(self.read(), expected)

    def test_mixed_selections_keep_recipe_order(self):
        selections = [
            self.selection,
            dict(feature_id="way", source_feature_id=40, object_type="way"),
            dict(feature_id="label", source_feature_id=40, object_type="node"),
        ]
        results = read_features(self.path, selections)
        self.assertEqual([item["feature_id"] for item in results],
                         ["islands", "way", "label"])
        self.assertEqual(results[2]["geometry"], {"type": "Point", "coordinates": [32, 12]})

    def test_rejects_the_same_osm_object_under_two_feature_ids(self):
        duplicate = dict(self.selection, feature_id="duplicate", source_feature_id=100)
        with self.assertRaisesRegex(ValueError, "relation 100 is selected more than once"):
            read_features(self.path, [self.selection, duplicate])

    def test_nodes_and_closed_ways(self):
        node = dict(
            feature_id="point",
            source_feature_id="1",
            object_type="node",
        )
        self.assertEqual(
            self.read(node)["geometry"], {"type": "Point", "coordinates": [0.0, 0.0]}
        )
        way = dict(
            feature_id="closed",
            source_feature_id="40",
            object_type="way",
        )
        self.assertEqual(len(self.read(way)["geometry"]["coordinates"]), 1)
        way["source_feature_id"] = "10"
        with self.assertRaisesRegex(ValueError, "is open"):
            self.read(way)

    def test_missing_objects_and_tag_mismatches_fail(self):
        for update, message in [
            ({"source_feature_id": "999"}, "missing"),
            ({"expected_tags": {"name": "Other"}}, "identity"),
        ]:
            with (
                self.subTest(update=update),
                self.assertRaisesRegex(ValueError, message),
            ):
                self.read(dict(self.selection, **update))

    def test_unrecognized_member_roles_fail(self):
        self.path.write_text(self.path.read_text().replace('role="label"', 'role="unknown"'))
        with self.assertRaisesRegex(ValueError, "member role"):
            self.read()

    def test_incomplete_or_crossing_outer_rings_fail(self):
        original = self.path.read_text()
        for old, new in (
            ('<nd ref="22"/>', '<nd ref="999"/>'),
            ('type="way" ref="40" role="outer"', 'type="way" ref="999" role="outer"'),
            ('<nd ref="21"/><nd ref="22"/>', '<nd ref="22"/><nd ref="21"/>'),
        ):
            self.path.write_text(original.replace(old, new))
            with self.subTest(change=new), self.assertRaises(ValueError):
                self.read()


if __name__ == "__main__":
    unittest.main()
