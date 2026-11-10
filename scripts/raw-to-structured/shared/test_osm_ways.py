import hashlib
import json
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path

from shared.osm_ways import assemble, assemble_archive


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

    def test_reject_disconnected_cycle(self):
        self.way(11, [1, 2], [(1, 0, 0), (2, 1, 1)])
        self.way(12, [3, 4, 5, 3], [(3, 2, 2), (4, 3, 3), (5, 4, 4)])
        with self.assertRaisesRegex(ValueError, 'disconnected'):
            assemble(self.manifest, self.directory)

    def test_reject_start_inside_chain(self):
        self.way(11, [1, 2, 3], [(1, 0, 0), (2, 1, 1), (3, 2, 2)])
        self.manifest['start_node'] = 2
        with self.assertRaisesRegex(ValueError, 'start node'):
            assemble(self.manifest, self.directory)

    def test_reject_missing_node(self):
        self.way(11, [1, 2], [(1, 0, 0)])
        with self.assertRaisesRegex(ValueError, 'missing node'):
            assemble(self.manifest, self.directory)

    def test_reject_invalid_coordinates(self):
        for longitude, latitude in [(float('nan'), 0), (181, 0), (0, 91), (True, 0)]:
            with self.subTest(longitude=longitude, latitude=latitude):
                self.manifest['ways'] = []
                self.way(11, [1, 2], [(1, 0, 0), (2, longitude, latitude)])
                with self.assertRaisesRegex(ValueError, 'invalid node coordinates'):
                    assemble(self.manifest, self.directory)

    def test_reject_revisited_node(self):
        self.way(11, [1, 2, 3, 2, 4], [(1, 0, 0), (2, 1, 1), (3, 2, 2), (4, 3, 3)])
        with self.assertRaisesRegex(ValueError, 'revisits a node'):
            assemble(self.manifest, self.directory)

    def test_reject_duplicate_adjacent_coordinates(self):
        self.way(11, [1, 2], [(1, 0, 0), (2, 0, 0)])
        with self.assertRaisesRegex(ValueError, 'duplicate adjacent coordinates'):
            assemble(self.manifest, self.directory)


class ArchiveTest(unittest.TestCase):
    def reject_archive(self, entries, message):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / 'bad.zip'
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
                with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
                    for name, data in entries:
                        z.writestr(name, data)
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, message):
                assemble_archive(archive, digest)

    def test_rejects_path_traversal(self):
        self.reject_archive([('../escape', b'x')], 'unsafe archive names')

    def test_rejects_duplicate_names(self):
        self.reject_archive([('same', b'a'), ('same', b'b')], 'duplicate or unsafe')

    def test_rejects_unlisted_member(self):
        self.reject_archive([('manifest.json', b'{"ways": []}'), ('extra.json', b'{}')],
                            'manifest does not match')

    def test_selected_geometry_and_pin(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / 'source.zip'
            elements = [{'type': 'node', 'id': 1, 'lon': 0, 'lat': 0},
                        {'type': 'node', 'id': 2, 'lon': 1, 'lat': 1},
                        {'type': 'way', 'id': 3, 'nodes': [1, 2]}]
            source = json.dumps({'elements': elements}).encode()
            manifest = {'start_node': 1, 'ways': [{'id': 3, 'file': '3.json', 'sha256': hashlib.sha256(source).hexdigest()}]}
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('manifest.json', json.dumps(manifest))
                z.writestr('3.json', source)
            archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
            geom = {'type': 'LineString', 'coordinates': [[0., 0.], [1., 1.]]}
            geom_hash = hashlib.sha256(json.dumps(geom, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            self.assertEqual(assemble_archive(archive, archive_hash), geom)
            self.assertEqual(assemble_archive(archive, archive_hash,
                                             expected_geometry_sha256=geom_hash), geom)
            with self.assertRaisesRegex(ValueError, 'source archive'):
                assemble_archive(archive, '0' * 64)
            with self.assertRaisesRegex(ValueError, 'expected geometry'):
                assemble_archive(archive, archive_hash, expected_geometry_sha256='0' * 64)


if __name__ == '__main__':
    unittest.main()

