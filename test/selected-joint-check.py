"""Selected map repairs run native checks; raw polygon changes keep their detector."""
import builtins
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest
from contextlib import ExitStack, contextmanager
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('joint_geography_controls', ROOT / 'scripts/run-geographic-check.py')
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)
BASE, NEXT = '1' * 40, '2' * 40


def raw(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()


def native(**extra):
    return {'method': 'selected-native-owner-conservation-v1', 'status': 'no-new-native-loss',
            'candidate_code_executed': False, 'intervals': [], 'lost_or_reassigned_cells': 0, **extra}


@contextmanager
def no_polygons():
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == 'shapely' or name.startswith('shapely.'):
            raise AssertionError('selected runner imported Shapely')
        return original_import(name, *args, **kwargs)

    with mock.patch.object(builtins, '__import__', side_effect=guarded_import), \
         mock.patch.object(G.importlib.util, 'spec_from_file_location', side_effect=AssertionError('selected runner loaded polygon detector')):
        yield


class JointRouting(unittest.TestCase):
    def issued(self, **extra):
        return {'version': 1, 'kind': 'trusted-selected-joint-comparison-v1', 'candidate_code_executed': False, **extra}

    def test_only_explicit_unavailable_custody_selects_cold_native_fallback(self):
        value = self.issued(mode='legacy-cold-required', reuse_unavailable={'cold': 'candidate', 'reason': 'changed base'})
        with no_polygons(), mock.patch.object(G.subprocess, 'check_output', return_value=raw(value)) as launch:
            self.assertEqual(G.selected_joint(ROOT, BASE, NEXT), value)
        self.assertEqual(launch.call_count, 1)
        self.assertEqual(launch.call_args.args[0][1], '--expose-gc')
        self.assertTrue(launch.call_args.args[0][2].endswith('/selected-joint-entry.mjs'))
        del value['reuse_unavailable']
        with mock.patch.object(G.subprocess, 'check_output', return_value=raw(value)):
            with self.assertRaisesRegex(ValueError, 'fallback omitted'):
                G.selected_joint(ROOT, BASE, NEXT)

    def test_native_failure_returns_without_additional_comparison(self):
        value = self.issued(mode='authenticated-checkpoint-append-v1',
                            native=native(status='native-regressions-found', intervals=[{'row': 1}], lost_or_reassigned_cells=1))
        with no_polygons(), mock.patch.object(G.subprocess, 'check_output', return_value=raw(value)) as child:
            self.assertEqual(G.selected_joint(ROOT, BASE, NEXT), value)
        self.assertEqual(child.call_count, 1)

    def test_joint_success_returns_direct_native_checkpoint_without_polygon_receipts(self):
        value = self.issued(mode='authenticated-checkpoint-append-v1', native=native(),
                            derived_checkpoint={'validation_stage': 'native-passed', 'accepted_checkpoint': False})
        with no_polygons(), mock.patch.object(G.subprocess, 'check_output', return_value=raw(value)) as child:
            result = G.selected_joint(ROOT, BASE, NEXT)
        self.assertEqual(result, value)
        self.assertEqual(child.call_count, 1)
        self.assertNotIn('continuous', result)
        self.assertNotIn('continuous_result', result)

    def test_joint_invalid_or_foreign_acknowledgements_fail_closed(self):
        valid = self.issued(mode='authenticated-checkpoint-append-v1', native=native())
        cases = [{**valid, 'kind': 'foreign'}, {**valid, 'candidate_code_executed': True},
                 {**valid, 'mode': 'invented'}, {**valid, 'native': None},
                 {**valid, 'native': native(status='not-applicable')},
                 {**valid, 'native': native(candidate_code_executed=True)},
                 {**valid, 'native': native(method='foreign')},
                 {**valid, 'native': native(lost_or_reassigned_cells=1)},
                 {**valid, 'native': native(intervals=[{'row': 1}])}]
        for value in cases:
            with self.subTest(value=value), mock.patch.object(G.subprocess, 'check_output', return_value=raw(value)):
                with self.assertRaises(ValueError):
                    G.selected_joint(ROOT, BASE, NEXT)

    def test_joint_launcher_keeps_code_and_both_data_commits_distinct(self):
        value = self.issued(mode='authenticated-checkpoint-append-v1', native=native())
        with mock.patch.object(G.subprocess, 'check_output', return_value=raw(value)) as child:
            G.selected_joint(ROOT, BASE, NEXT, trusted=NEXT)
        self.assertEqual(child.call_args.args[0][3:7], [str(ROOT), NEXT, BASE, NEXT])


class InspectRouting(unittest.TestCase):
    @contextmanager
    def fixture(self):
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(G, 'verify_trusted_checkout', return_value='fixture'))
            stack.enter_context(mock.patch.object(G, 'inventory', return_value=[]))
            stack.enter_context(mock.patch.object(G, 'unchanged_selected_inputs', return_value=None))
            stack.enter_context(mock.patch.object(G, 'git', return_value=b'present'))
            yield

    def test_warm_and_cold_selected_routes_never_import_or_launch_continuous_polygons(self):
        for cold in [False, True]:
            calls = []
            result = native()

            def joint(*args, **kwargs):
                calls.append('joint')
                if cold:
                    return {'mode': 'legacy-cold-required', 'reuse_unavailable': {'cold': 'candidate', 'reason': 'not accepted'}}
                return {'mode': 'authenticated-checkpoint-append-v1', 'native': result}

            def child(command, **kwargs):
                self.assertTrue(command[1].endswith('/check-effective-geographic-regression.mjs'))
                self.assertEqual(command[2:5], [str(ROOT), BASE, NEXT])
                calls.append('native')
                return raw(result)

            with self.subTest(cold=cold), self.fixture(), no_polygons(), \
                 mock.patch.object(G, 'selected_joint', side_effect=joint), \
                 mock.patch.object(G, 'prefetch_declared_inputs', side_effect=lambda *args: calls.append('prefetch')), \
                 mock.patch.object(G.subprocess, 'check_output', side_effect=child):
                report = G.inspect(ROOT, BASE, NEXT, prefetch=True)
            self.assertFalse(any(name == 'shapely' or name.startswith('shapely.') for name in sys.modules))
            self.assertEqual(calls, ['joint', 'prefetch', 'native'] if cold else ['joint'])
            self.assertEqual(report['selected_native_report'], result)
            self.assertEqual(report['status'], 'no-new-native-loss')
            self.assertEqual(report['regressions'], 0)
            self.assertEqual(report['validation_scope'], 'selected-native-map-cells')
            self.assertNotIn('selected_continuous_report', report)
            self.assertNotIn('differential_report', report)

    def test_software_inspect_runs_cold_native_with_distinct_data_and_no_checkpoint_reuse(self):
        result = native()
        with self.fixture(), no_polygons(), \
             mock.patch.object(G, 'verify_trusted_checkout', return_value='fixture') as verify, \
             mock.patch.object(G, 'unchanged_selected_inputs', side_effect=AssertionError('software shortcut')), \
             mock.patch.object(G, 'selected_joint', side_effect=AssertionError('software checkpoint reuse')), \
             mock.patch.object(G.subprocess, 'check_output', return_value=raw(result)) as child:
            report = G.inspect(ROOT, BASE, NEXT, code_commit=NEXT, checkpoint_destination=ROOT)
        verify.assert_called_once_with(ROOT, NEXT)
        self.assertEqual(child.call_args.args[0][-3:-1], [BASE, NEXT])
        self.assertEqual(child.call_count, 1)
        self.assertEqual(report['trusted_code_commit'], NEXT)
        self.assertTrue(report['candidate_code_executed'])
        self.assertEqual(report['selected_native_report'], result)
        self.assertNotIn('selected_continuous_report', report)
        self.assertNotIn('checkpoint', report)

    def test_warm_and_cold_invalid_native_results_fail_closed(self):
        for cold in [False, True]:
            for alter in [lambda v: v.pop('method'), lambda v: v.update(method='foreign'),
                          lambda v: v.update(candidate_code_executed=True), lambda v: v.pop('status'),
                          lambda v: v.update(status='no-new-regression'), lambda v: v.pop('lost_or_reassigned_cells'),
                          lambda v: v.update(lost_or_reassigned_cells=1), lambda v: v.pop('intervals'),
                          lambda v: v.update(intervals=[{'row': 1}])]:
                value = native(); alter(value)
                joint = {'mode': 'legacy-cold-required'} if cold else {'mode': 'authenticated-checkpoint-append-v1', 'native': value}
                with self.subTest(cold=cold, value=value), self.fixture(), no_polygons(), \
                     mock.patch.object(G, 'selected_joint', return_value=joint), \
                     mock.patch.object(G.subprocess, 'check_output', return_value=raw(value)):
                    with self.assertRaisesRegex(ValueError, 'completed native result|contradicts conservation'):
                        G.inspect(ROOT, BASE, NEXT)

    def test_native_loss_is_reported_without_polygon_adjudication_or_checkpoint(self):
        value = native(status='native-regressions-found', intervals=[{'row': 1}], lost_or_reassigned_cells=1)
        with self.fixture(), no_polygons(), \
             mock.patch.object(G, 'selected_joint', return_value={'mode': 'authenticated-checkpoint-append-v1', 'native': value}), \
             mock.patch.object(G.subprocess, 'check_output', side_effect=AssertionError('duplicate comparison')):
            report = G.inspect(ROOT, BASE, NEXT)
        self.assertEqual(report['status'], 'native-regressions-found')
        self.assertEqual(report['regressions'], 1)
        self.assertNotIn('selected_continuous_report', report)
        self.assertNotIn('checkpoint', report)
        self.assertNotIn('adjudication', report)

    def test_nonselected_changed_geography_still_loads_and_runs_raw_polygon_detector(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = pathlib.Path(temporary)
            (repo / 'scripts').mkdir()
            (repo / 'scripts/check-geographic-regression.py').write_text(
                "def inspect(repo, baseline, candidate):\n"
                "    assert baseline == '1' * 40 and candidate == '2' * 40\n"
                "    return {'status': 'regressions-found', 'regressions': 2, 'raw_detector_executed': True}\n")
            with self.fixture(), mock.patch.object(G, 'inventory', side_effect=[['before'], ['after']]), \
                 mock.patch.object(G, 'git', return_value=b''), \
                 mock.patch.object(G, 'selected_joint', side_effect=AssertionError('nonselected checkpoint route')), \
                 mock.patch.object(G.subprocess, 'check_output', side_effect=AssertionError('nonselected native route')):
                report = G.inspect(repo, BASE, NEXT)
        self.assertEqual(report['status'], 'regressions-found')
        self.assertEqual(report['regressions'], 2)
        self.assertTrue(report['differential_report']['raw_detector_executed'])
        self.assertNotIn('selected_native_report', report)


if __name__ == '__main__':
    unittest.main()
