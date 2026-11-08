from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from benchmark_shore_index_build import run
import benchmark_shore_index_build as benchmark
import test_benchmark_water_shore_index as fixtures


class ConstructorPairTests(unittest.TestCase):
    def test_complete_pair_exact_in_both_orders(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);request=fixtures.GlobalShoreQATests().fixture(root)
            for first in (False,True):
                result=run(request,root/str(first),rows_per_batch=2,candidate_first=first)
                self.assertEqual(result['status'],'all-index-offset-start-end-category-bytes-identical')
                self.assertEqual(set(result['arrays']),{'offsets','starts','ends','codes'})
                self.assertGreater(result['coastal_cells'],0)
    def test_changed_buffer_prevents_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);request=fixtures.GlobalShoreQATests().fixture(root)
            original=benchmark.BatchedCoastalShoreIndex
            def wrong(*args,**kwargs):
                result=original(*args,**kwargs);result.starts[0]+=1;return result
            with patch.object(benchmark,'BatchedCoastalShoreIndex',wrong):
                with self.assertRaisesRegex(ValueError,'buffer differs'):run(request,root/'out')
            self.assertFalse((root/'out/report.json').exists())


if __name__=='__main__':unittest.main()
