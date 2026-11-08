import unittest
from unittest.mock import patch

import compare_land_preflights as compare
import test_replay_land_sweep as fixture


class NumericPreflightPairTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture.ReplayTest('test_complete_coverage_without_processes')
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)

    def test_complete_pair_uses_python_apis_and_retains_default(self):
        for reverse in (False,True):
            with self.subTest(reverse=reverse),patch('subprocess.Popen',side_effect=AssertionError('no process')),patch('ctypes.CDLL',side_effect=AssertionError('no bridge')):
                result=compare.compare(self.fixture.stage,self.fixture.root/str(reverse),candidate_first=reverse,batch_rows=128 if reverse else 1)
            self.assertEqual(result['status'],'complete-preflight-reports-identical')
            self.assertEqual(result['results']['candidate']['coverage']['land_cells'],7)

    def test_corrupt_source_rejected_without_completion(self):
        (self.fixture.stage/'fresh-components-runs').write_bytes(b'corrupt')
        out=self.fixture.root/'bad'
        with self.assertRaisesRegex(ValueError,'hash mismatch'):compare.compare(self.fixture.stage,out)
        self.assertFalse(out.exists())
