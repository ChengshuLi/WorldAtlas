import unittest
from unittest.mock import patch

import compare_land_writers as compare
import replay_land_sweep
import test_replay_land_sweep as fixture


class NumericWriterPairTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture.ReplayTest('test_complete_coverage_without_processes')
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.replay=self.fixture.root/'source'
        with patch('ural_delta.compile_rule',return_value=None):replay_land_sweep.replay(self.fixture.stage,self.replay,search=True)

    def test_complete_in_process_pair(self):
        with patch('subprocess.Popen',side_effect=AssertionError('no process')),patch('ctypes.CDLL',side_effect=AssertionError('no bridge')):
            # Both modules bind the same actual rule compiler; the fixture has
            # no Ural policy, so use its normal no-override test convention.
            selected=compare.modules
            def no_delta(pins):
                rule,reference,candidate=selected(pins);rule.compile_rule=lambda *args:None
                return rule,reference,candidate
            with patch.object(compare,'modules',side_effect=no_delta):
                result=compare.compare(self.fixture.stage,self.replay,self.fixture.root/'pair')
        self.assertEqual(result['status'],'complete-land-writer-bytes-and-reports-identical')

    def test_changed_assignments_fail_before_output(self):
        (self.replay/'codes.u8').write_bytes(bytes([18]));out=self.fixture.root/'bad'
        with self.assertRaisesRegex(ValueError,'assignments differ'):compare.compare(self.fixture.stage,self.replay,out)
        self.assertFalse(out.exists())
