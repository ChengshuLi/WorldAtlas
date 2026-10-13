"""Actual continuous readback/polygon controls and the minimal joint routing seam."""
import copy
import gzip
import hashlib
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result
G = module('joint_geography_controls', 'scripts/run-geographic-check.py')
D = module('joint_strict_detector', 'scripts/check-geographic-regression.py')
BASE, NEXT = '1' * 40, '2' * 40

def raw(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()
def digest(value):
    return hashlib.sha256(raw(value)).hexdigest()
def feature(identity, left, right):
    return {'type': 'Feature', 'id': identity, 'properties': {'id': identity, 'parent_id': 'P'},
            'geometry': {'type': 'Polygon', 'coordinates': [[[left, 0], [right, 0], [right, 1], [left, 1], [left, 0]]]}}

class ContinuousReadback(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = pathlib.Path(self.temp.name)
        self.features = {'A': feature('A', 0, 1), 'B': feature('B', 2, 3)}
        self.addition = {'component_id': 'new', 'target_id': 'A', 'pixelIndex': 1,
                         'base_geometry_sha256': digest(self.features['A']['geometry']),
                         'geometry': feature('piece', 1.2, 1.5)['geometry']}
        self.operands = {'version': 1, 'kind': 'complete-selected-continuous-operands-v1',
                         'plan': {'required_ids': ['A', 'B'], 'changed_ids': ['A'], 'pairs': [['A', 'B']],
                                  'source_bindings': {'baseline': {'vintage': BASE}, 'candidate': {'vintage': NEXT}}},
                         'baseline': self.features, 'candidate': copy.deepcopy(self.features),
                         'effective_additions': {'baseline': [], 'candidate': [self.addition]}}
        self.facts = {'executing_commit': BASE, 'baseline_commit': BASE, 'candidate_commit': NEXT,
                      'candidate_code_executed': False,
                      'inverse': [{'vintage': vintage, 'id': identity, 'geometry_sha256': digest(f['geometry'])}
                                  for vintage in ['baseline', 'candidate'] for identity, f in self.features.items()]}
        self.allowance = mock.patch.object(G.subprocess, 'check_output', return_value=raw({'phaseBytes': 1024 ** 3}))
        self.allowance.start()
    def tearDown(self):
        self.allowance.stop()
        self.temp.cleanup()
    def publish(self):
        decoded, facts = raw(self.operands), raw(self.facts)
        encoded = gzip.compress(decoded, mtime=0)
        pin = lambda name, body: {'path': name, 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}
        publication = {'version': 1, 'complete': True, 'kind': 'trusted-selected-continuous-comparison-v1',
                       'operands': {**pin('operands.json.gz', encoded), 'decoded_bytes': len(decoded), 'decoded_sha256': hashlib.sha256(decoded).hexdigest()},
                       'facts': pin('facts.json', facts)}
        for name, body in [('operands.json.gz', encoded), ('facts.json', facts), ('publication.json', raw(publication))]:
            (self.directory / name).write_bytes(body)
            (self.directory / name).chmod(0o644)
        return {'version': 1, 'kind': publication['kind'], 'publication': publication, 'complete_owners': 2,
                'changed_ids': self.operands['plan']['changed_ids'], 'candidate_code_executed': False}
    def consume(self, issued):
        return G.consume_selected_continuous(ROOT, BASE, NEXT, D, self.directory, issued)
    def test_literal_addition_runs_the_original_full_polygon_predicates(self):
        result = self.consume(self.publish())
        self.assertEqual(result['status'], 'no-new-regression')
        self.assertEqual(result['regressions'], 0)
        self.assertEqual(result['original_strict_polygon_result']['changed_location_ids'], ['A'])
    def test_overlap_with_an_unchanged_neighbor_is_not_filtered(self):
        self.addition['geometry'] = feature('piece', 2.25, 2.75)['geometry']
        result = self.consume(self.publish())
        self.assertEqual(result['status'], 'regressions-found')
        self.assertGreater(result['regressions'], 0)
        self.assertEqual(result['original_strict_polygon_result']['findings']['features'][0]['properties']['location_ids'], ['A', 'B'])
    def test_two_changed_owners_are_compared_to_each_other(self):
        self.addition['geometry'] = feature('piece', 1.25, 1.75)['geometry']
        second = {**self.addition, 'component_id': 'second', 'target_id': 'B', 'pixelIndex': 2,
                  'base_geometry_sha256': digest(self.features['B']['geometry'])}
        self.operands['effective_additions']['candidate'].append(second)
        self.operands['plan']['changed_ids'] = ['A', 'B']
        result = self.consume(self.publish())
        self.assertGreater(result['regressions'], 0)
    def test_polygon_loss_is_preserved(self):
        self.operands['effective_additions']['candidate'] = []
        self.operands['candidate']['A'] = feature('A', 0, 0.5)
        for row in self.facts['inverse']:
            if row['vintage'] == 'candidate' and row['id'] == 'A':
                row['geometry_sha256'] = digest(self.operands['candidate']['A']['geometry'])
        result = self.consume(self.publish())
        self.assertGreater(result['regressions'], 0)
    def test_wrong_changed_scope_fails_against_actual_polygon_result(self):
        self.operands['plan']['changed_ids'] = ['B']
        with self.assertRaisesRegex(ValueError, 'changed-ID closure differs'):
            self.consume(self.publish())
    def test_omitted_operand_and_inverse_records_fail_before_comparison(self):
        del self.operands['candidate']['B']
        with self.assertRaisesRegex(ValueError, 'closure omitted'):
            self.consume(self.publish())
        self.operands['candidate']['B'] = self.features['B']
        self.facts['inverse'].pop()
        with self.assertRaisesRegex(ValueError, 'inverse scope differs'):
            self.consume(self.publish())
    def test_tampered_body_and_symlink_are_not_a_successful_publication(self):
        issued = self.publish()
        target = self.directory / 'operands.json.gz'
        target.write_bytes(target.read_bytes()[:-1] + b'x')
        with self.assertRaisesRegex(ValueError, 'differs from issued trusted child'):
            self.consume(issued)
        self.publish()
        target.rename(self.directory / 'sentinel.gz')
        target.symlink_to(self.directory / 'sentinel.gz')
        with self.assertRaisesRegex(ValueError, 'Nonordinary whole'):
            self.consume(issued)
    def test_foreign_execution_vintage_is_rejected(self):
        self.facts['executing_commit'] = NEXT
        with self.assertRaisesRegex(ValueError, 'Foreign selected execution'):
            self.consume(self.publish())

class JointRouting(unittest.TestCase):
    def issued(self, **extra):
        return {'version': 1, 'kind': 'trusted-selected-joint-comparison-v1', 'candidate_code_executed': False, **extra}
    def test_only_explicit_unavailable_custody_selects_legacy_fallback(self):
        value = self.issued(mode='legacy-cold-required', reuse_unavailable={'cold': 'candidate', 'reason': 'changed base'})
        with mock.patch.object(G.subprocess, 'check_output', return_value=raw(value)) as launch, \
             mock.patch.object(G, 'consume_selected_continuous', side_effect=AssertionError('unavailable proof consumed')):
            self.assertEqual(G.selected_joint(ROOT, BASE, NEXT, D), value)
        self.assertEqual(launch.call_count, 1)
        self.assertEqual(launch.call_args.args[0][1], '--expose-gc')
        del value['reuse_unavailable']
        with mock.patch.object(G.subprocess, 'check_output', return_value=raw(value)):
            with self.assertRaisesRegex(ValueError, 'fallback omitted'):
                G.selected_joint(ROOT, BASE, NEXT, D)
    def test_native_failure_does_not_consume_continuous_or_report_success(self):
        value = self.issued(mode='authenticated-checkpoint-append-v1', native={'status': 'native-regressions-found', 'candidate_code_executed': False, 'intervals': [{'row': 1}]}, continuous=None)
        with mock.patch.object(G.subprocess, 'check_output', return_value=raw(value)), \
             mock.patch.object(G, 'consume_selected_continuous', side_effect=AssertionError('continuous called')):
            self.assertEqual(G.selected_joint(ROOT, BASE, NEXT, D), value)
    def test_joint_success_uses_the_same_complete_readback_function(self):
        value = self.issued(mode='authenticated-checkpoint-append-v1', native={'status': 'no-new-native-loss', 'candidate_code_executed': False}, continuous={'actual': 'issued acknowledgement'})
        strict = {'status': 'no-new-regression', 'regressions': 0}
        with mock.patch.object(G.subprocess, 'check_output', return_value=raw(value)), \
             mock.patch.object(G, 'consume_selected_continuous', return_value=strict) as consume:
            self.assertEqual(G.selected_joint(ROOT, BASE, NEXT, D)['continuous_result'], strict)
            self.assertEqual(consume.call_args.args[-1], value['continuous'])
    def test_actual_inspect_route_does_not_launch_old_native_or_continuous(self):
        native = {'status': 'no-new-native-loss', 'candidate_code_executed': False}
        continuous = {'status': 'no-new-regression', 'regressions': 0}
        with mock.patch.object(G, 'verify_trusted_checkout', return_value='fixture'), \
             mock.patch.object(G, 'inventory', return_value=[]), \
             mock.patch.object(G, 'unchanged_selected_inputs', return_value=None), \
             mock.patch.object(G, 'git', return_value=b'present'), \
             mock.patch.object(G, 'selected_joint', return_value={'mode': 'authenticated-checkpoint-append-v1', 'native': native, 'continuous_result': continuous}), \
             mock.patch.object(G.subprocess, 'check_output', side_effect=AssertionError('duplicate native child')), \
             mock.patch.object(G, 'selected_continuous', side_effect=AssertionError('duplicate continuous child')):
            result = G.inspect(ROOT, BASE, NEXT)
        self.assertIs(result['selected_native_report'], native)
        self.assertIs(result['selected_continuous_report'], continuous)

    def test_software_inspect_runs_cold_native_and_continuous_with_distinct_data(self):
        native = {'status': 'no-new-native-loss', 'candidate_code_executed': False}
        continuous = {'status': 'no-new-regression', 'regressions': 0}
        with mock.patch.object(G, 'verify_trusted_checkout', return_value='fixture') as verify, \
             mock.patch.object(G, 'inventory', return_value=[]), \
             mock.patch.object(G, 'unchanged_selected_inputs', side_effect=AssertionError('software shortcut')), \
             mock.patch.object(G, 'git', return_value=b'present'), \
             mock.patch.object(G, 'selected_joint', side_effect=AssertionError('software checkpoint reuse')), \
             mock.patch.object(G.subprocess, 'check_output', return_value=raw(native)) as child, \
             mock.patch.object(G, 'selected_continuous', return_value=continuous) as cold:
            result = G.inspect(ROOT, BASE, NEXT, code_commit=NEXT, checkpoint_destination=ROOT)
        verify.assert_called_once_with(ROOT, NEXT)
        self.assertEqual(child.call_args.args[0][-3:-1], [BASE, NEXT])
        self.assertEqual(cold.call_args.args[1:3], (BASE, NEXT))
        self.assertEqual(cold.call_args.kwargs, {'trusted': NEXT})
        self.assertEqual(result['trusted_code_commit'], NEXT)
        self.assertTrue(result['candidate_code_executed'])
        self.assertEqual(result['selected_native_report'], native)
        self.assertIs(result['selected_continuous_report'], continuous)
        self.assertNotIn('checkpoint', result)

    def test_cold_launcher_separates_code_from_both_data_commits(self):
        issued = {'protocol': 'unchanged-child'}
        with mock.patch.object(G.subprocess, 'check_output', return_value=raw(issued)) as child, \
             mock.patch.object(G, 'consume_selected_continuous', return_value={}) as consume:
            G.selected_continuous(ROOT, BASE, NEXT, D, trusted=NEXT)
        args = child.call_args.args[0]
        self.assertEqual(args[4:8], [str(ROOT), NEXT, BASE, NEXT])
        self.assertEqual(consume.call_args.kwargs, {'trusted': NEXT})

if __name__ == '__main__':
    unittest.main()
