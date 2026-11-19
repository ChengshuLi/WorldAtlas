import json
import tempfile
import unittest
from pathlib import Path

from worldatlas.source_imports.osm.ways import assemble


class AssemblyTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.paths = []

    def tearDown(self):
        self.temp.cleanup()

    def way(self, way_id, refs, nodes):
        elements = [{'type': 'node', 'id': n, 'lon': x, 'lat': y} for n, x, y in nodes]
        elements.append({'type': 'way', 'id': way_id, 'nodes': refs})
        path = self.directory / f'{way_id}.json'
        path.write_text(json.dumps({'elements': elements}))
        self.paths.append(path)

    def test_join_and_reverse(self):
        self.way(11, [2, 1], [(1, 0, 0), (2, 1, 1)])
        self.way(12, [2, 3], [(2, 1, 1), (3, 2, 2)])
        self.assertEqual(assemble(self.paths[::-1])['coordinates'], [[0., 0.], [1., 1.], [2., 2.]])
        self.assertEqual(assemble(self.paths[::-1]), assemble(self.paths))

    def test_reject_multiple_ways_in_one_response(self):
        self.way(11, [1, 2], [(1, 0, 0), (2, 1, 1)])
        payload = json.loads(self.paths[0].read_text())
        payload['elements'].append({'type': 'way', 'id': 12, 'nodes': [1, 2]})
        self.paths[0].write_text(json.dumps(payload))
        with self.assertRaisesRegex(ValueError, 'exactly one OSM way'):
            assemble(self.paths)

    def test_reject_duplicate_way(self):
        self.way(11, [1, 2], [(1, 0, 0), (2, 1, 1)])
        with self.assertRaisesRegex(ValueError, 'duplicate OSM way'):
            assemble(self.paths * 2)

    def test_reject_conflicting_node(self):
        self.way(11, [1, 2], [(1, 0, 0), (2, 1, 1)])
        self.way(12, [2, 3], [(2, 1, 2), (3, 2, 2)])
        with self.assertRaisesRegex(ValueError, 'conflicting'):
            assemble(self.paths)

    def test_reject_branched_chain(self):
        self.way(11, [1, 2], [(1, 0, 0), (2, 1, 1)])
        self.way(12, [2, 3], [(2, 1, 1), (3, 2, 2)])
        self.way(13, [2, 4], [(2, 1, 1), (4, 3, 3)])
        with self.assertRaisesRegex(ValueError, 'unbranched'):
            assemble(self.paths)

    def test_reject_disconnected_cycle(self):
        self.way(11, [1, 2], [(1, 0, 0), (2, 1, 1)])
        self.way(12, [3, 4, 5, 3], [(3, 2, 2), (4, 3, 3), (5, 4, 4)])
        with self.assertRaisesRegex(ValueError, 'one open, unbranched chain'):
            assemble(self.paths)

    def test_reject_closed_chain(self):
        self.way(11, [1, 2, 3, 1], [(1, 0, 0), (2, 1, 0), (3, 0, 1)])
        with self.assertRaisesRegex(ValueError, 'one open, unbranched chain'):
            assemble(self.paths)

    def test_starts_with_the_lower_endpoint_id(self):
        self.way(11, [5, 1, 3], [(5, 0, 0), (1, 1, 1), (3, 2, 2)])
        self.assertEqual(assemble(self.paths)['coordinates'], [[2, 2], [1, 1], [0, 0]])

    def test_reject_missing_node(self):
        self.way(11, [1, 2], [(1, 0, 0)])
        with self.assertRaisesRegex(ValueError, 'missing node'):
            assemble(self.paths)

    def test_reject_invalid_coordinates(self):
        for longitude, latitude in [(float('nan'), 0), (181, 0), (0, 91), (True, 0)]:
            with self.subTest(longitude=longitude, latitude=latitude):
                self.paths.clear()
                self.way(11, [1, 2], [(1, 0, 0), (2, longitude, latitude)])
                with self.assertRaisesRegex(ValueError, 'invalid node coordinates'):
                    assemble(self.paths)

    def test_reject_revisited_node(self):
        self.way(11, [1, 2, 3, 2, 4], [(1, 0, 0), (2, 1, 1), (3, 2, 2), (4, 3, 3)])
        with self.assertRaisesRegex(ValueError, 'self-intersection'):
            assemble(self.paths)

    def test_reject_duplicate_adjacent_coordinates(self):
        self.way(11, [1, 2], [(1, 0, 0), (2, 0, 0)])
        with self.assertRaisesRegex(ValueError, 'duplicate adjacent coordinates'):
            assemble(self.paths)

    def test_reject_geometric_crossing_with_distinct_node_ids(self):
        self.way(11, [1, 2, 3, 4], [(1, 0, 0), (2, 2, 2), (3, 0, 2), (4, 2, 0)])
        with self.assertRaisesRegex(ValueError, 'self-intersection'):
            assemble(self.paths)

    def test_reject_coincident_endpoints_with_distinct_ids(self):
        self.way(11, [1, 2], [(1, 0, 0), (2, 1, 1)])
        self.way(12, [3, 4], [(3, 1, 1), (4, 2, 2)])
        with self.assertRaisesRegex(ValueError, 'distinct OSM endpoints share coordinates'):
            assemble(self.paths)

    def test_reject_unsplit_longitude_discontinuity(self):
        self.way(11, [1, 2], [(1, 179, 0), (2, -179, 1)])
        with self.assertRaisesRegex(ValueError, 'antimeridian'):
            assemble(self.paths)


if __name__ == '__main__':
    unittest.main()
