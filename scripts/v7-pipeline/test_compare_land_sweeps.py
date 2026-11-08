import unittest
import sys
import types
from unittest.mock import patch

from compare_land_sweeps import compare
import compare_land_sweeps as comparator
import ural_delta
import test_replay_land_sweep as fixture
from replay_land_sweep import replay, STAGE2


class ComparisonTest(unittest.TestCase):
    def setUp(self):
        fixture.ReplayTest.setUp(self)

    def test_complete_pair_uses_source_checkpoint_without_processes(self):
        with patch('ural_delta.compile_rule',return_value=None),patch.object(comparator,'rule_module',return_value=ural_delta),patch('subprocess.Popen',side_effect=AssertionError('process launch')):
            source=self.root/'source';replay(self.stage,source,search=True)
            result=compare(self.stage,source,STAGE2,self.root/'pair')
        self.assertEqual(result['status'],'all-complete-old-new-land-bytes-and-reports-identical')
        self.assertEqual(set(result['results']),{'reference','candidate'})
        self.assertEqual(result['results']['candidate']['writer']['land_cells'],7)

    def test_wrong_cached_sweep_module_is_not_executed(self):
        with patch('ural_delta.compile_rule',return_value=None):
            source=self.root/'source';replay(self.stage,source,search=True)
        wrong=types.ModuleType('write_land_stream');wrong.__file__='/wrong/write_land_stream.py'
        wrong.write_land_stream=lambda *a,**k: (_ for _ in ()).throw(AssertionError('cached wrong writer executed'))
        with patch.dict(sys.modules,{'write_land_stream':wrong}),patch('ural_delta.compile_rule',return_value=None),patch.object(comparator,'rule_module',return_value=ural_delta):
            result=compare(self.stage,source,STAGE2,self.root/'pair')
            self.assertIs(sys.modules['write_land_stream'],wrong)
        self.assertEqual(result['status'],'all-complete-old-new-land-bytes-and-reports-identical')

    def test_changed_source_is_rejected_before_execution(self):
        path=self.root/'unloaded.py';path.write_text("raise AssertionError('must not execute')\n")
        with self.assertRaisesRegex(ValueError,'source changed before loading'):
            comparator.source_module('_unloaded_land_test',path,'0'*64)

    def test_data_helper_from_another_checkout_is_rejected(self):
        with patch.object(comparator.engine,'__file__','/wrong/engine.py'):
            with self.assertRaisesRegex(ImportError,'outside selected source'):
                compare(self.stage,self.root,STAGE2,self.root/'pair')
        self.assertFalse((self.root/'pair').exists())

    def test_changed_assignment_file_cannot_be_used_as_fresh_decisions(self):
        with patch('ural_delta.compile_rule',return_value=None):
            source=self.root/'source';replay(self.stage,source,search=True)
        (source/'codes.u8').write_bytes(bytes([18]))
        with self.assertRaisesRegex(ValueError,'source-bound assignments differ'):
            compare(self.stage,source,STAGE2,self.root/'pair')
        self.assertFalse((self.root/'pair').exists())


if __name__=='__main__':unittest.main()
