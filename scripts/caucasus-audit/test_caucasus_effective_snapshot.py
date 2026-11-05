import copy
import unittest

from caucasus_effective_snapshot import BOUNDARY, derive, geomhash
from caucasus_seed_gate import assembled_region_hash


class EffectiveSnapshotTest(unittest.TestCase):
    def setUp(self):
        line = {'type': 'LineString', 'coordinates': [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]]}
        boundary = {'boundary_id': BOUNDARY, 'geometry': line, 'geometry_sha256': geomhash(line),
                    'provenance': {'source_assembly_v1': {'recipe_sha256': 'a' * 64}}}
        route = {'route_id': 'r', 'geometry': {'type': 'LineString', 'coordinates': [[1, 1], [0, 1], [0, 0]]}}
        region = {'region_id': 'europe', 'segments': [{'kind': 'boundary', 'id': BOUNDARY, 'start': 0, 'end': 3, 'reverse': False},
                  {'kind': 'route', 'id': 'r', 'start': 0, 'end': 3, 'reverse': False}]}
        region['geometry_sha256'] = assembled_region_hash(region, {('boundary', BOUNDARY): boundary, ('route', 'r'): route})
        self.snapshot = {'mainland_boundaries': [boundary], 'routes': [route], 'seed_regions': [region]}
        self.derived = {'type': 'LineString', 'coordinates': [[0.0, 0.0], [1.01, 0.0], [1.0, 1.0]]}
        self.gate = {'schema': 'caucasus-source-seed-gate-v1', 'snapshot_sha256': 'b' * 64,
                     'selected_geometry_sha256': geomhash(line), 'recipe_sha256': 'a' * 64,
                     'assembly': {'geometry_sha256': geomhash(self.derived)}}

    def test_updates_only_effective_copy_and_region_hash(self):
        saved = copy.deepcopy(self.snapshot)
        effective, report = derive(self.snapshot, self.derived, self.gate, 'b' * 64)
        self.assertEqual(self.snapshot, saved)
        self.assertEqual(effective['mainland_boundaries'][0]['geometry'], self.derived)
        self.assertNotEqual(effective['seed_regions'][0]['geometry_sha256'], saved['seed_regions'][0]['geometry_sha256'])
        self.assertEqual(len(report['regions']), 1)

    def test_endpoint_change_is_rejected(self):
        self.derived['coordinates'][0] = [-1.0, 0.0]
        self.gate['assembly']['geometry_sha256'] = geomhash(self.derived)
        with self.assertRaisesRegex(ValueError, 'endpoint'):
            derive(self.snapshot, self.derived, self.gate, 'b' * 64)

    def test_stale_selected_region_is_rejected(self):
        self.snapshot['seed_regions'][0]['geometry_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'region digest'):
            derive(self.snapshot, self.derived, self.gate, 'b' * 64)

    def test_duplicate_region_id_is_rejected(self):
        self.snapshot['seed_regions'].append(copy.deepcopy(self.snapshot['seed_regions'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate region'):
            derive(self.snapshot, self.derived, self.gate, 'b' * 64)


if __name__ == '__main__':
    unittest.main()
