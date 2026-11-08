import unittest
from unittest.mock import patch

import compare_land_replays as compare
import test_replay_land_sweep as fixture


class CompleteLandPairTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture.ReplayTest('test_complete_coverage_without_processes')
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)

    def test_complete_independent_search_writer_pair_uses_python_apis(self):
        with patch('subprocess.Popen',side_effect=AssertionError('no process')),patch('ctypes.CDLL',side_effect=AssertionError('no bridge')),patch('ural_delta.compile_rule',return_value=None):
            result=compare.compare(self.fixture.stage,self.fixture.root/'pair')
        self.assertEqual(result['status'],'complete-land-replays-all-decisions-bytes-and-reports-identical')
        self.assertEqual(result['results']['reference']['result']['preflight_engine'],'legacy-python-row')
        self.assertEqual(result['results']['candidate']['result']['preflight_engine'],'numpy-row-batch')
        self.assertEqual(result['results']['candidate']['result']['preflight_batch_rows'],128)

    def test_writer_pair_keeps_current_numeric_coverage_on_both_sides(self):
        with patch('subprocess.Popen',side_effect=AssertionError('no process')),patch('ctypes.CDLL',side_effect=AssertionError('no bridge')),patch('ural_delta.compile_rule',return_value=None):
            result=compare.compare(self.fixture.stage,self.fixture.root/'writers',compare_writer=True)
        reference=result['results']['reference']['result'];candidate=result['results']['candidate']['result']
        self.assertEqual(reference['preflight_engine'],candidate['preflight_engine'])
        self.assertEqual(reference['preflight_engine'],'numpy-row-batch')
        self.assertEqual(reference['writer_engine'],'legacy');self.assertEqual(candidate['writer_engine'],'numeric')
