import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import build_coastal_batch as builder
import compare_coastal_batch as comparison
import coastal_band as band
import test_build_coastal_batch as fixture_module
from test_build_land import pin

class ComparisonBatchTest(unittest.TestCase):
 def fixture(self,root):
  helper=fixture_module.CoastalBatchTest('runTest');path,cfg=helper.fixture(root);candidate=root/'candidate';builder.build(path,candidate)
  for name in ('reference','comparison-config'):(root/name).mkdir()
  rows=root/'reference'/'rows';runs=root/'reference'/'runs';np.asarray([0,2,3],dtype='<u4').tofile(rows);np.asarray([(1,17),(4,7),(4,7)],dtype='<u4').tofile(runs)
  c={'schema':'simple-v2-coastal-comparison-batch-v1','candidate_batch':pin(candidate/'report.json'),'reference_rows':pin(rows),'reference_runs':pin(runs),'workers':1,'minimum_free_bytes':0};p=root/'comparison-config'/'config.json';p.write_text(json.dumps(c));return p,c,cfg
 def test_serial_parallel_and_shared_pin_counts(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);path,cfg,candidate=self.fixture(root);physical=candidate['physical_rows']['path']
   original=band.pin;seen=[]
   def count(spec):seen.append(spec['path']);return original(spec)
   with patch.object(band,'pin',side_effect=count):serial=comparison.build(path,root/'serial')
   self.assertEqual(seen.count(physical),4);self.assertEqual(serial['comparison_count'],2);self.assertEqual(serial['candidate_band_cells'],0)
   cfg['workers']=2;path.write_text(json.dumps(cfg));parallel=comparison.build(path,root/'parallel');self.assertEqual(serial['counts'],parallel['counts'])
 def test_reference_and_space_failure_leave_no_output(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);path,cfg,_=self.fixture(root);cfg['reference_rows']['sha256']='0'*64;path.write_text(json.dumps(cfg))
   with self.assertRaisesRegex(ValueError,'hash mismatch'):comparison.build(path,root/'out')
   self.assertFalse((root/'out').exists())
   cfg['reference_rows']=pin(root/'reference'/'rows');cfg['minimum_free_bytes']=1<<60;path.write_text(json.dumps(cfg))
   with self.assertRaisesRegex(ValueError,'free disk'):comparison.build(path,root/'out')
   self.assertFalse((root/'out').exists())
if __name__=='__main__':unittest.main()
