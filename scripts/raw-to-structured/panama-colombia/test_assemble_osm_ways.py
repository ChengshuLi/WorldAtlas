import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from assemble_osm_ways import assemble


class AssemblyTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.manifest = {'start_node': 1, 'ways': []}

    def tearDown(self):
        self.temp.cleanup()

    def way(self, way_id, refs, nodes):
        elements = [{'type': 'node', 'id': n, 'lon': x, 'lat': y} for n, x, y in nodes]
        elements.append({'type': 'way', 'id': way_id, 'nodes': refs})
        raw = json.dumps({'elements': elements}).encode()
        name = f'{way_id}.json'
        (self.directory / name).write_bytes(raw)
        self.manifest['ways'].append({'id': way_id, 'file': name, 'sha256': hashlib.sha256(raw).hexdigest()})

    def test_join_and_reverse(self):
        self.way(11, [2, 1], [(1, 0, 0), (2, 1, 1)])
        self.way(12, [2, 3], [(2, 1, 1), (3, 2, 2)])
        self.assertEqual(assemble(self.manifest, self.directory)['coordinates'], [[0., 0.], [1., 1.], [2., 2.]])

    def test_reject_tampering(self):
        self.way(11, [1, 2], [(1, 0, 0), (2, 1, 1)])
        (self.directory / '11.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            assemble(self.manifest, self.directory)

    def test_reject_conflicting_node(self):
        self.way(11, [1, 2], [(1, 0, 0), (2, 1, 1)])
        self.way(12, [2, 3], [(2, 1, 2), (3, 2, 2)])
        with self.assertRaisesRegex(ValueError, 'conflicting'):
            assemble(self.manifest, self.directory)

    def test_reject_branched_chain(self):
        self.way(11, [1, 2], [(1, 0, 0), (2, 1, 1)])
        self.way(12, [2, 3], [(2, 1, 1), (3, 2, 2)])
        self.way(13, [2, 4], [(2, 1, 1), (4, 3, 3)])
        with self.assertRaisesRegex(ValueError, 'unbranched'):
            assemble(self.manifest, self.directory)


if __name__ == '__main__':
    unittest.main()
