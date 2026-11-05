"""Bounded compatibility check using the hash-pinned Panama v2 candidate.

Set PANAMA_DIRECT_DIR to the candidate's unpacked source directory. This uses
synthetic lines and an OSM fixture; it does not run GDAL or a closure checker.
"""
import copy
import hashlib
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from caucasus_effective_snapshot import derive, geomhash
import test_caucasus_effective_snapshot as caucasus_fixture

PINS = {'assemble_osm_ways.py': 'b1edf136b05109dcfb080158f58dffe9f910c6c30b3a654721478453b64270e2',
        'osm_source_handoff.py': 'ef6bc620e447f38be3524bcebeba6b1fe309ab2a4ea7f507ccf38c3ef4d30add',
        'panama_seed_source.py': 'f6edea70f22993241acbffcfd1d02eefaf7a9e60b00925e8afdfb5963b781655'}


@unittest.skipUnless(os.getenv('PANAMA_DIRECT_DIR'), 'pinned Panama v2 candidate path not supplied')
class PanamaCaucasusCompatibilityTest(unittest.TestCase):
    def test_both_source_bindings_preserve_original_snapshot(self):
        root = Path(os.environ['PANAMA_DIRECT_DIR']).resolve(strict=True)
        for name, expected in PINS.items():
            self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), expected)
        names = ('panama_seed_source', 'osm_source_handoff', 'assemble_osm_ways')
        self.assertTrue(all(name not in sys.modules for name in names))
        sys.path.insert(0, str(root))
        try:
            import panama_seed_source as panama
            fixture = caucasus_fixture.EffectiveSnapshotTest('test_updates_only_effective_copy_and_region_hash')
            fixture.setUp()
            panama_line = {'type': 'LineString', 'coordinates': [[2.0, 2.0], [3.0, 3.0]]}
            record = {'boundary_id': panama.BOUNDARY, 'geometry': panama_line,
                      'geometry_sha256': geomhash(panama_line),
                      'qualified_source_refs': [{'source_id': panama.SOURCE[0], 'version': panama.SOURCE[1]}]}
            fixture.snapshot['mainland_boundaries'].append(record)
            original = copy.deepcopy(fixture.snapshot)
            effective, trace = derive(fixture.snapshot, fixture.derived, fixture.gate, 'b' * 64)
            self.assertEqual(fixture.snapshot, original)
            self.assertEqual(effective['mainland_boundaries'][1], record)
            self.assertEqual(trace['original_snapshot_sha256'], 'b' * 64)
            nodes = [{'type': 'node', 'id': 1, 'lon': 2, 'lat': 2},
                     {'type': 'node', 'id': 2, 'lon': 3, 'lat': 3},
                     {'type': 'way', 'id': 3, 'nodes': [1, 2]}]
            raw = json.dumps({'elements': nodes}).encode()
            manifest = {'start_node': 1, 'ways': [{'id': 3, 'file': '3.json',
                         'sha256': hashlib.sha256(raw).hexdigest()}]}
            with tempfile.TemporaryDirectory() as directory:
                archive = Path(directory) / 'panama.zip'
                with zipfile.ZipFile(archive, 'w') as z:
                    z.writestr('manifest.json', json.dumps(manifest))
                    z.writestr('3.json', raw)
                digest = hashlib.sha256(archive.read_bytes()).hexdigest()
                catalog = {panama.SOURCE: {'kind': 'raw', 'sha256': digest, 'size_bytes': archive.stat().st_size}}
                records = {('boundary', r['boundary_id']): r for r in effective['mainland_boundaries']}
                result, panama_trace = panama.bind(records, catalog, {'path': str(archive), 'sha256': digest})
                self.assertEqual(result[('boundary', panama.BOUNDARY)]['geometry'], panama_line)
                self.assertEqual(panama_trace['geometry_sha256'], record['geometry_sha256'])
                self.assertEqual(result[('boundary', fixture.snapshot['mainland_boundaries'][0]['boundary_id'])]['geometry'], fixture.derived)
                self.assertEqual(fixture.snapshot, original)
                result[('boundary', panama.BOUNDARY)]['geometry_sha256'] = '0' * 64
                with self.assertRaisesRegex(ValueError, 'selected boundary'):
                    panama.bind(result, catalog, {'path': str(archive), 'sha256': digest})
        finally:
            sys.path.remove(str(root))
            for name in names:
                sys.modules.pop(name, None)


if __name__ == '__main__':
    unittest.main()
