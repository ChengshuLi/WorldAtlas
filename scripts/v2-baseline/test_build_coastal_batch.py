import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import build_coastal_batch as batch
import coastal_band as band
from test_coastal_band import make_rle,pin

class CoastalBatchTest(unittest.TestCase):
 def fixture(self,root,bad=False):
  for name in ('physical','land','config','direct-config'):(root/name).mkdir()
  g={'width':4,'height':2,'west':-180,'north':90,'step':90};pr,pu=make_rle(root/'physical',4,2,[(0,0,17)],False);cells=[(0,0,17)]+([(1,1,3)] if bad else []);lr,lu=make_rle(root/'land',4,2,cells,True)
  report=root/'land'/'report.json';report.write_text(json.dumps({'schema':'simple-v2-land-report-v1','status':'research-not-published','grid':g,'inputs':{'physical_rows':pr,'physical_runs':pu},'output_rows_sha256':lr['sha256'],'output_runs_sha256':lu['sha256']}))
  cfg={'schema':'simple-v2-coastal-batch-v1','grid':g,'physical_rows':pr,'physical_runs':pu,'land_rows':lr,'land_runs':lu,'land_report':pin(report),'tile_width':2,'tile_height':2,'pad_degrees':180,'minimum_free_bytes':0,'workers':1};path=root/'config'/'batch.json';path.write_text(json.dumps(cfg));return path,cfg
 def test_serial_parallel_and_independent_tile_parity(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);path,cfg=self.fixture(root)
   with patch.object(band,'pin',wraps=band.pin) as pins:serial=batch.build(path,root/'serial');self.assertEqual(pins.call_count,10)
   cfg['workers']=2;path.write_text(json.dumps(cfg));parallel=batch.build(path,root/'parallel');self.assertEqual(serial['tile_count'],2);self.assertTrue(serial['tile_cores_cover_grid'])
   for i,box in enumerate(([0,2,0,2],[2,4,0,2])):
    c={'schema':'simple-v2-coastal-band-v1','grid':cfg['grid'],**{k:cfg[k] for k in ('physical_rows','physical_runs','land_rows','land_runs','land_report')},'core':box,'pad_degrees':180,'minimum_free_bytes':0};cp=root/'direct-config'/f'{i}.json';cp.write_text(json.dumps(c));direct=root/f'direct{i}';band.build(cp,direct)
    self.assertEqual((direct/'coastal-spans.jsonl.gz').read_bytes(),(root/'serial'/'tiles'/f'{i:06d}'/'coastal-spans.jsonl.gz').read_bytes());self.assertEqual((direct/'coastal-spans.jsonl.gz').read_bytes(),(root/'parallel'/'tiles'/f'{i:06d}'/'coastal-spans.jsonl.gz').read_bytes())
 def test_invalid_tile_never_writes_batch_report(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);path,_=self.fixture(root,True)
   with self.assertRaisesRegex(ValueError,'land/physical values mismatch'):batch.build(path,root/'out')
   self.assertFalse((root/'out'/'report.json').exists())
 def test_invalid_resource_or_untrusted_shared_spec_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);path,cfg=self.fixture(root);cfg['minimum_free_bytes']=1<<60;path.write_text(json.dumps(cfg))
   with self.assertRaisesRegex(ValueError,'free disk'):batch.build(path,root/'out')
   self.assertFalse((root/'out').exists());cfg['minimum_free_bytes']=0;path.write_text(json.dumps(cfg))
   tc={'schema':'simple-v2-coastal-band-v1','grid':cfg['grid'],**{k:cfg[k] for k in ('physical_rows','physical_runs','land_rows','land_runs','land_report')},'core':[0,2,0,2],'pad_degrees':180,'minimum_free_bytes':0};cp=root/'direct-config'/'tile.json';cp.write_text(json.dumps(tc))
   with self.assertRaisesRegex(ValueError,'batch input specifications differ'):band.build(cp,root/'direct',_verified_inputs={})
if __name__=='__main__':unittest.main()
