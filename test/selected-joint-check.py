"""Selected map repairs run native checks; raw polygon changes keep their detector."""
import builtins
import importlib.util
import io
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


    def test_native_failure_returns_without_additional_comparison(self):
        value = self.issued(mode='accepted-final-map-comparison-v1',
                            native=native(status='native-regressions-found', intervals=[{'row': 1}], lost_or_reassigned_cells=1))
        with no_polygons(), mock.patch.object(G.subprocess, 'check_output', return_value=raw(value)) as child:
            self.assertEqual(G.selected_joint(ROOT, BASE, NEXT), value)
        self.assertEqual(child.call_count, 1)

    def test_joint_success_returns_direct_native_checkpoint_without_polygon_receipts(self):
        value = self.issued(mode='accepted-final-map-comparison-v1', native=native(),
                            derived_checkpoint={'validation_stage': 'native-passed', 'accepted_checkpoint': False})
        stream = io.StringIO()
        with no_polygons(), mock.patch.object(G.sys, 'stderr', stream), \
             mock.patch.object(G.subprocess, 'check_output', return_value=raw(value)) as child:
            result = G.selected_joint(ROOT, BASE, NEXT)
        self.assertEqual(result, value)
        self.assertEqual(stream.getvalue(), '')
        self.assertEqual(child.call_count, 1)
        self.assertNotIn('continuous', result)
        self.assertNotIn('continuous_result', result)

    def test_final_map_result_needs_no_retained_checkpoint_product(self):
        value = self.issued(mode='accepted-final-map-comparison-v1', native=native(), derived_checkpoint=None)
        with mock.patch.object(G.subprocess, 'check_output', return_value=raw(value)):
            result = G.selected_joint(ROOT, BASE, NEXT)
        self.assertEqual(result, value)
        self.assertNotIn('checkpoint', result)

    def test_joint_invalid_or_foreign_acknowledgements_fail_closed(self):
        valid = self.issued(mode='accepted-final-map-comparison-v1', native=native())
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
        value = self.issued(mode='accepted-final-map-comparison-v1', native=native())
        with mock.patch.object(G.subprocess, 'check_output', return_value=raw(value)) as child:
            G.selected_joint(ROOT, BASE, NEXT, trusted=NEXT)
        self.assertEqual(child.call_args.args[0][2:6], [str(ROOT), NEXT, BASE, NEXT])


class InspectRouting(unittest.TestCase):
    @contextmanager
    def fixture(self):
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(G, 'verify_trusted_checkout', return_value='fixture'))
            stack.enter_context(mock.patch.object(G, 'inventory', return_value=[]))
            stack.enter_context(mock.patch.object(G, 'git', return_value=b'present'))
            stack.enter_context(mock.patch.object(G, 'read', return_value=raw({'version': 1})))
            yield





    def test_final_software_fetch_skips_legacy_prefetch_and_keeps_real_native_result_checks(self):
        for invalid in [False, True]:
            result = native(candidate_code_executed=True, candidate_selection={'version': 2, 'kind': 'selected-final-native-bank-v2'})
            if invalid:
                result['lost_or_reassigned_cells'] = 1
            with self.subTest(invalid=invalid), self.fixture(), no_polygons(), \
                 mock.patch.object(G, 'read', return_value=raw({'version': 2})), \
                 mock.patch.object(G, 'selected_joint', side_effect=AssertionError('software checkpoint reuse')), \
                 mock.patch.object(G, 'prefetch_declared_inputs', side_effect=AssertionError('final-bank legacy prefetch')), \
                 mock.patch.object(G.subprocess, 'check_output', return_value=raw(result)) as child:
                if invalid:
                    with self.assertRaisesRegex(ValueError, 'contradicts conservation'):
                        G.inspect(ROOT, BASE, NEXT, code_commit=NEXT, prefetch=True)
                else:
                    report = G.inspect(ROOT, BASE, NEXT, code_commit=NEXT, prefetch=True)
                    self.assertTrue(report['candidate_code_executed'])
                    self.assertEqual(report['selected_native_report'], result)
                    self.assertNotIn('checkpoint', report)
                self.assertEqual(child.call_count, 1)

    def test_warm_and_cold_invalid_native_results_fail_closed(self):
        for cold in [False]:
            for alter in [lambda v: v.pop('method'), lambda v: v.update(method='foreign'),
                          lambda v: v.update(candidate_code_executed=True), lambda v: v.pop('status'),
                          lambda v: v.update(status='no-new-regression'), lambda v: v.pop('lost_or_reassigned_cells'),
                          lambda v: v.update(lost_or_reassigned_cells=1), lambda v: v.pop('intervals'),
                          lambda v: v.update(intervals=[{'row': 1}])]:
                value = native(); alter(value)
                joint = {'mode': 'legacy-cold-required'} if cold else {'mode': 'accepted-final-map-comparison-v1', 'native': value}
                with self.subTest(cold=cold, value=value), self.fixture(), no_polygons(), \
                     mock.patch.object(G, 'selected_joint', return_value=joint), \
                     mock.patch.object(G.subprocess, 'check_output', return_value=raw(value)):
                    with self.assertRaisesRegex(ValueError, 'completed native result|contradicts conservation'):
                        G.inspect(ROOT, BASE, NEXT)

    def test_native_loss_is_reported_without_polygon_adjudication_or_checkpoint(self):
        value = native(status='native-regressions-found', intervals=[{'row': 1}], lost_or_reassigned_cells=1)
        with self.fixture(), no_polygons(), \
             mock.patch.object(G, 'selected_joint', return_value={'mode': 'accepted-final-map-comparison-v1', 'native': value}), \
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
