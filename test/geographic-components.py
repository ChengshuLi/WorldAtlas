"""Connectivity controls independently construct expected shapes and exclusions."""
import pathlib
import gzip
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest

from shapely.geometry import Polygon, box, mapping, shape

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from geographic_components import components
from evidence.immutable import canonical_json, descriptor, deterministic_gzip, sha256

spec = importlib.util.spec_from_file_location('refine_components', ROOT / 'scripts/refine-geographic-components.py')
refine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(refine)


def feature(identity, geometry, area=1):
    return {'type': 'Feature', 'id': identity, 'geometry': mapping(geometry),
            'properties': {'area_m2': area, 'nearby_locations': []}}


class ComponentControls(unittest.TestCase):
    def test_cross_tile_edges_reconstruct_whole(self):
        records, contacts = components([feature('a', box(4, 0, 5, 1)), feature('b', box(5, 0, 6, 1))])
        self.assertEqual(len(records), 1)
        self.assertTrue(shape(records[0]['geometry']).equals(box(4, 0, 6, 1)))
        self.assertEqual(contacts[0]['kind'], 'shared-edge')

    def test_point_contact_is_ambiguous_not_joined(self):
        records, contacts = components([feature('a', box(0, 0, 1, 1)), feature('b', box(1, 1, 2, 2))])
        self.assertEqual(len(records), 2)
        self.assertEqual(contacts[0]['kind'], 'point-only-ambiguous')

    def test_point_contact_can_have_an_independent_edge_path(self):
        records, contacts = components([feature('a', box(0, 0, 1, 1)),
                                        feature('b', box(1, 1, 2, 2)), feature('c', box(0, 1, 1, 2))])
        self.assertEqual(len(records), 1)
        point = [c for c in contacts if c['kind'] == 'point-only-ambiguous']
        self.assertEqual(len(point), 1)
        self.assertEqual(point[0]['components'][0], point[0]['components'][1])

    def test_subpixel_gap_is_not_snapped(self):
        records, contacts = components([feature('a', box(0, 0, 1, 1)),
                                        feature('b', box(1 + 1e-12, 0, 2, 1))])
        self.assertEqual(len(records), 2)
        self.assertEqual(contacts, [])

    def test_hole_and_small_island_remain_separate(self):
        ring = Polygon([(0, 0), (4, 0), (4, 4), (0, 4)],
                       [[(1, 1), (3, 1), (3, 3), (1, 3)]])
        island = box(2, 2, 2.000001, 2.000001)
        records, contacts = components([feature('a', ring), feature('b', island)])
        self.assertEqual(len(records), 2)
        self.assertEqual(contacts, [])
        self.assertTrue(any(shape(r['geometry']).equals(ring) for r in records))

    def test_dateline_edge_joins_without_world_spanning_shape(self):
        records, contacts = components([feature('a', box(179, 0, 180, 1)),
                                        feature('b', box(-180, 0, -179, 1))])
        self.assertEqual(len(records), 1)
        self.assertEqual(shape(records[0]['geometry']).area, 2)
        self.assertTrue(records[0]['properties']['dateline_connected'])
        self.assertTrue(contacts[0]['dateline'])

    def test_dateline_point_is_not_joined(self):
        records, contacts = components([feature('a', box(179, 0, 180, 1)),
                                        feature('b', box(-180, 1, -179, 2))])
        self.assertEqual(len(records), 2)
        self.assertEqual(contacts[0]['kind'], 'point-only-ambiguous')

    def test_overlap_flag_prevents_unique_area_claim(self):
        records, contacts = components([feature('a', box(0, 0, 2, 2)), feature('b', box(1, 1, 3, 3))])
        self.assertEqual(len(records), 1)
        self.assertTrue(records[0]['properties']['positive_area_input_overlap'])
        self.assertEqual(contacts[0]['kind'], 'positive-area-input-overlap')

    def test_blocked_tile_and_unknown_area_survive(self):
        records, _ = components([feature('a', box(0, 0, 1, 1), None)], [{'bounds': [1, 0, 2, 1]}])
        p = records[0]['properties']
        self.assertTrue(p['touches_blocked_tile'])
        self.assertEqual(p['unmeasured_fragment_ids'], ['a'])
        self.assertIsNone(p['administrative_assignment'])
        self.assertEqual(p['water_status'], 'unverified')

    def test_wrapped_blocked_tile_contacts_in_both_directions(self):
        for geometry, blocked in [(box(-180, 0, -179, 1), [179, 0, 180, 1]),
                                  (box(179, 0, 180, 1), [-180, 0, -179, 1])]:
            records, _ = components([feature('a', geometry)], [{'bounds': blocked}])
            self.assertTrue(records[0]['properties']['touches_blocked_tile'])

    def test_wrapped_blocked_point_contact_retains_uncertainty(self):
        for geometry, blocked in [(box(-180, 0, -179, 1), [179, 1, 180, 2]),
                                  (box(179, 0, 180, 1), [-180, 1, -179, 2])]:
            records, _ = components([feature('a', geometry)], [{'bounds': blocked}])
            self.assertTrue(records[0]['properties']['touches_blocked_tile'])

    def test_wrapped_nearby_blocked_tile_does_not_invent_contact(self):
        for geometry, blocked in [(box(-180, 0, -179, 1), [179, 0, 180 - 1e-12, 1]),
                                  (box(179, 0, 180, 1), [-180 + 1e-12, 0, -179, 1])]:
            records, _ = components([feature('a', geometry)], [{'bounds': blocked}])
            self.assertFalse(records[0]['properties']['touches_blocked_tile'])

    def test_permutation_and_two_runs_are_identical(self):
        inputs = [feature('b', box(1, 0, 2, 1)), feature('a', box(0, 0, 1, 1))]
        self.assertEqual(canonical_json(components(inputs)), canonical_json(components(list(reversed(inputs)))))
        self.assertEqual(canonical_json(components(inputs)), canonical_json(components(inputs)))

    def test_changed_original_identity_changes_component_binding(self):
        a = feature('a', box(0, 0, 1, 1))
        old, _ = components([a])
        a['properties']['source'] = 'changed'
        new, _ = components([a])
        self.assertNotEqual(old[0]['id'], new[0]['id'])

    def test_duplicate_invalid_and_outside_domain_fail(self):
        a = feature('a', box(0, 0, 1, 1))
        for inputs in [[a, a], [feature('x', Polygon([(0, 0), (1, 1), (0, 1), (1, 0)]))],
                       [feature('x', box(180, 0, 181, 1))]]:
            with self.assertRaises(ValueError):
                components(inputs)


class ImmutableControls(unittest.TestCase):
    def setUp(self):
        (ROOT / '.cache').mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / '.cache')
        self.repo = pathlib.Path(self.temp.name)
        refine.ROOT = self.repo

        def git(*args):
            return subprocess.check_output(['git', '-C', str(self.repo), *args], stderr=subprocess.PIPE).decode().strip()
        self.git = git
        git('init', '-q')
        git('config', 'user.name', 'Test Fixture')
        git('config', 'user.email', 'test@example.invalid')
        original = b'original bytes\n'
        (self.repo / 'input.json').write_bytes(original)
        git('add', '.')
        git('commit', '-qm', 'original input')
        evaluation = git('rev-parse', 'HEAD')
        features = [feature('a', box(0, 0, 1, 1)), feature('b', box(1, 0, 2, 1), None)]
        raw = canonical_json({'type': 'FeatureCollection', 'features': features})
        encoded = deterministic_gzip(raw)
        (self.repo / 'fragments.json.gz').write_bytes(encoded)
        pin = descriptor('fragments.json.gz', encoded)
        pin.update(uncompressed_bytes=len(raw), uncompressed_sha256=sha256(raw))
        report = {'version': 'worldatlas-geographic-gap-audit-v1', 'baseline_commit': evaluation,
                  'inputs': [descriptor('input.json', original)], 'outputs': [pin],
                  'water_reference': {'input_commit': evaluation,
                                      'input_files': [descriptor('input.json', original)]},
                  'candidate_fragments': 2, 'tiles_blocked': [{'bounds': [2, 0, 3, 1]}],
                  'tiles_scanned': 1, 'measurement_errors': [{'tile': 'b', 'fragment': ''}],
                  'bounds': [-180, -60, 180, 85], 'limits': ['Test source only']}
        # Production null IDs use tile:fragment. Use that native shape here too.
        features[1]['id'] = '2:3'
        raw = canonical_json({'type': 'FeatureCollection', 'features': features})
        encoded = deterministic_gzip(raw)
        (self.repo / 'fragments.json.gz').write_bytes(encoded)
        report['outputs'] = [{**descriptor('fragments.json.gz', encoded),
                              'uncompressed_bytes': len(raw), 'uncompressed_sha256': sha256(raw)}]
        report['measurement_errors'] = [{'tile': 2, 'fragment': 3}]
        self.report = canonical_json(report)
        (self.repo / 'report.json').write_bytes(self.report)
        git('add', '.')
        git('commit', '-qm', 'retained audit')
        self.commit = git('rev-parse', 'HEAD')

    def tearDown(self):
        refine.ROOT = ROOT
        self.temp.cleanup()

    def run_refine(self, out='result'):
        return refine.refine(self.commit, 'report.json', len(self.report), sha256(self.report), out)

    def test_immutable_inputs_and_two_runs(self):
        # A mutated checkout cannot replace the committed bytes.
        (self.repo / 'fragments.json.gz').write_bytes(b'not original')
        first, second = self.run_refine('one'), self.run_refine('two')
        self.assertEqual(first['fragment_count'], 2)
        self.assertEqual(first['component_count'], 1)
        self.assertEqual(first['unmeasured_fragment_ids'], ['2:3'])
        self.assertEqual(first['tiles_blocked'], [{'bounds': [2, 0, 3, 1]}])
        self.assertTrue(all(r['same_bytes'] for r in first['current_input_compatibility']))
        self.assertEqual([r['sha256'] for r in first['outputs']], [r['sha256'] for r in second['outputs']])

    def test_whole_report_hash_is_required(self):
        with self.assertRaisesRegex(ValueError, 'hash/size mismatch'):
            refine.refine(self.commit, 'report.json', len(self.report), '0' * 64, 'wrong')
        self.assertFalse((self.repo / 'wrong').exists())

    def test_existing_result_is_never_replaced(self):
        self.run_refine()
        before = (self.repo / 'result/report.json').read_bytes()
        with self.assertRaises(ValueError):
            self.run_refine()
        self.assertEqual(before, (self.repo / 'result/report.json').read_bytes())

    def test_current_compatibility_is_not_relabeling(self):
        (self.repo / 'input.json').write_bytes(b'new actual input\n')
        self.git('add', 'input.json')
        self.git('commit', '-qm', 'later input')
        self.commit = self.git('rev-parse', 'HEAD')
        result = self.run_refine()
        self.assertFalse(result['current_input_compatibility'][0]['same_bytes'])
        self.assertNotEqual(result['original_evaluation_commit'], result['input_commit'])

    def test_bounded_decompression(self):
        previous = refine.MAX_FILE_BYTES
        try:
            refine.MAX_FILE_BYTES = 10
            with self.assertRaises(ValueError):
                refine.decoded(gzip.compress(b'x' * 11))
        finally:
            refine.MAX_FILE_BYTES = previous


if __name__ == '__main__':
    unittest.main()
