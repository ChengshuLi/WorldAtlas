import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from panama_seed_source import BOUNDARY, SOURCE, bind


class PanamaBindingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.archive = Path(self.tmp.name) / 'source.zip'
        nodes = [{'type': 'node', 'id': 1, 'lon': 0, 'lat': 0},
                 {'type': 'node', 'id': 2, 'lon': 1, 'lat': 1},
                 {'type': 'way', 'id': 3, 'nodes': [1, 2]}]
        raw = json.dumps({'elements': nodes}).encode()
        manifest = {'start_node': 1, 'ways': [{'id': 3, 'file': '3.json', 'sha256': hashlib.sha256(raw).hexdigest()}]}
        with zipfile.ZipFile(self.archive, 'w') as z:
            z.writestr('manifest.json', json.dumps(manifest))
            z.writestr('3.json', raw)
        self.digest = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        geometry = {'type': 'LineString', 'coordinates': [[0., 0.], [1., 1.]]}
        ghash = hashlib.sha256(json.dumps(geometry, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        self.record = {'geometry': geometry, 'geometry_sha256': ghash,
                       'qualified_source_refs': [{'source_id': SOURCE[0], 'version': SOURCE[1]}]}
        self.records = {('boundary', BOUNDARY): self.record}
        self.catalog = {SOURCE: {'kind': 'raw', 'sha256': self.digest, 'size_bytes': self.archive.stat().st_size}}
        self.pin = {'path': str(self.archive), 'sha256': self.digest}

    def tearDown(self):
        self.tmp.cleanup()

    def test_bind_reconstructs_selected_geometry(self):
        result, trace = bind(self.records, self.catalog, self.pin)
        self.assertEqual(result[('boundary', BOUNDARY)]['geometry'], self.record['geometry'])
        self.assertEqual(trace['archive_sha256'], self.digest)
        self.assertEqual(trace['vertices'], 2)

    def test_missing_pin_and_source_link_fail(self):
        with self.assertRaisesRegex(ValueError, 'requires a pinned'):
            bind(self.records, self.catalog, None)
        self.record['qualified_source_refs'] = []
        with self.assertRaisesRegex(ValueError, 'lacks Panama source link'):
            bind(self.records, self.catalog, self.pin)

    def test_wrong_catalog_and_geometry_fail(self):
        self.catalog[SOURCE]['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'source catalog'):
            bind(self.records, self.catalog, self.pin)
        self.catalog[SOURCE]['sha256'] = self.digest
        self.record['geometry_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'selected boundary'):
            bind(self.records, self.catalog, self.pin)

    def test_no_panama_leaves_other_boundaries_alone(self):
        self.assertEqual(bind({}, {}, None), ({}, None))
        with self.assertRaisesRegex(ValueError, 'without selected boundary'):
            bind({}, {}, self.pin)


if __name__ == '__main__':
    unittest.main()
