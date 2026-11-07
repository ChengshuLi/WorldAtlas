import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import compare_grids as c

class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.root=Path(self.t.name)
        self.old=self.root/'reference';self.new=self.root/'candidate';self.old.mkdir();self.new.mkdir()
        self.write(self.old,[[[2,7],[4,18]],[[4,1]]]);self.write(self.new,[[[2,7],[4,18]],[[4,1]]])
    def write(self,d,rows):
        offsets=[0];runs=[]
        for rr in rows:runs.extend(rr);offsets.append(len(runs))
        (d/'rows.u32le').write_bytes(np.asarray(offsets,dtype='<u4').tobytes());(d/'runs.u32le').write_bytes(np.asarray(runs,dtype='<u4').tobytes())
    def run_comparison(self,**kw):
        return c.compare(self.new,self.old,4,2,kw.get('pins',{n:c.sha(self.old/n) for n in c.NAMES}),self.root/'comparison.json')
    def test_identical_and_exclusive_report(self):
        report=self.run_comparison();self.assertEqual(report['cells_compared'],8);self.assertEqual(report['changed_cells'],0);self.assertTrue(report['byte_identical']);self.assertGreaterEqual(report['processing_elapsed_seconds'],0)
        with self.assertRaises(FileExistsError):self.run_comparison()
    def test_different_segmentation_same_cells(self):
        self.write(self.new,[[[1,7],[2,7],[4,18]],[[2,1],[4,1]]])
        report=self.run_comparison();self.assertEqual(report['status'],'same-cells');self.assertFalse(report['byte_identical'])
    def test_exact_changed_cell_counts(self):
        self.write(self.new,[[[1,7],[2,8],[4,18]],[[2,2],[4,1]]])
        report=self.run_comparison();self.assertEqual(report['changed_cells'],3);self.assertEqual(report['pair_counts'],{'1->2':2,'7->8':1})
    def test_reference_pin_mismatch(self):
        with self.assertRaisesRegex(ValueError,'hash mismatch'):self.run_comparison(pins={n:'0'*64 for n in c.NAMES})
        self.assertFalse((self.root/'comparison.json').exists())
    def test_malformed_identical_grids_are_not_accepted(self):
        self.write(self.old,[[[0,7],[4,18]],[[4,1]]]);self.write(self.new,[[[0,7],[4,18]],[[4,1]]])
        with self.assertRaisesRegex(ValueError,'endpoints'):self.run_comparison()
    def test_invalid_offsets_and_dimensions(self):
        (self.new/'rows.u32le').write_bytes(np.asarray([0,0,3],dtype='<u4').tobytes())
        with self.assertRaisesRegex(ValueError,'offsets'):self.run_comparison()
        with self.assertRaisesRegex(ValueError,'dimensions'):c.compare(self.new,self.old,True,2,{},self.root/'report')
    def test_input_change_before_report_fails(self):
        original=c.combined
        def changing(d):
            result=original(d)
            if d==self.new:(self.new/'runs.u32le').write_bytes(b'changed')
            return result
        with patch.object(c,'combined',side_effect=changing), self.assertRaisesRegex(ValueError,'changed before'):self.run_comparison()
        self.assertFalse((self.root/'comparison.json').exists())

if __name__=='__main__':unittest.main()
