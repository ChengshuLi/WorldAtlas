import unittest
from unittest.mock import patch

from compare_land_sweeps import compare
import test_replay_land_sweep as fixture
from replay_land_sweep import replay, STAGE2


class ComparisonTest(unittest.TestCase):
    def setUp(self):
        fixture.ReplayTest.setUp(self)

    def test_complete_pair_uses_source_checkpoint_without_processes(self):
        with patch('ural_delta.compile_rule',return_value=None),patch('subprocess.Popen',side_effect=AssertionError('process launch')):
            source=self.root/'source';replay(self.stage,source,search=True)
            result=compare(self.stage,source,STAGE2,self.root/'pair')
        self.assertEqual(result['status'],'all-complete-old-new-land-bytes-and-reports-identical')
        self.assertEqual(set(result['results']),{'reference','candidate'})
        self.assertEqual(result['results']['candidate']['writer']['land_cells'],7)

    def test_changed_assignment_file_cannot_be_used_as_fresh_decisions(self):
        with patch('ural_delta.compile_rule',return_value=None):
            source=self.root/'source';replay(self.stage,source,search=True)
        (source/'codes.u8').write_bytes(bytes([18]))
        with self.assertRaisesRegex(ValueError,'source-bound assignments differ'):
            compare(self.stage,source,STAGE2,self.root/'pair')
        self.assertFalse((self.root/'pair').exists())


if __name__=='__main__':unittest.main()
