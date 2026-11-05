import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from osm_source_handoff import verified_geometry


class HandoffTest(unittest.TestCase):
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
            self.assertEqual(verified_geometry(archive, archive_hash, geom_hash), geom)
            with self.assertRaisesRegex(ValueError, 'source archive'):
                verified_geometry(archive, '0' * 64, geom_hash)
            with self.assertRaisesRegex(ValueError, 'selected boundary'):
                verified_geometry(archive, archive_hash, '0' * 64)


if __name__ == '__main__':
    unittest.main()
