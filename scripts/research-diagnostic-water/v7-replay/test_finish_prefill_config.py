import json,tempfile,unittest
from unittest.mock import patch
from pathlib import Path
import finish_prefill_config as f
class Tests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.r=Path(self.t.name);self.i=self.r/'i';self.c=self.r/'c';self.mask=self.r/'mask';self.mask.write_bytes(b'mask');self.report=self.r/'report';self.report.write_text(json.dumps({'output_sha256':{'physical-dry.tif':f.sha(self.mask)}}));self.inv={'rle_inputs':{'physical':{'physical_mask_path':str(self.mask),'physical_mask_sha256':f.sha(self.mask),'report_path':str(self.report),'report_sha256':f.sha(self.report)}},'schema':'worldatlas-prefill-input-inventory-v1','status':'coastal-band-pending-not-runnable','publishable':False,'coastal_band':None,'basins':[{}]*92,'snapshot_sha256':'p'};self.coast={'schema':'worldatlas-full-water-assignment-tiles-v1','coverage':{'complete':True},'source':{'policy_sha256':'p'}};self.write()
 def write(self):self.i.write_text(json.dumps(self.inv));self.c.write_text(json.dumps(self.coast))
 def test_success_and_exclusive_output(self):
  r=f.make(self.i,f.sha(self.i),self.c,f.sha(self.c),self.r/'out');self.assertEqual(r['status'],'pending-full-prefill-validation')
  with self.assertRaises(FileExistsError):f.make(self.i,f.sha(self.i),self.c,f.sha(self.c),self.r/'out')
 def test_incomplete_or_mismatched_coast_rejected(self):
  self.coast['coverage']['complete']=False;self.write()
  with self.assertRaisesRegex(ValueError,'incomplete'):f.make(self.i,f.sha(self.i),self.c,f.sha(self.c),self.r/'out')
  self.coast['coverage']['complete']=True;self.coast['source']['policy_sha256']='bad';self.write()
  with self.assertRaisesRegex(ValueError,'wrong-policy'):f.make(self.i,f.sha(self.i),self.c,f.sha(self.c),self.r/'out')
 def test_input_mutation_rejected(self):
  old=f.read
  def changing(p,h):
   data=old(p,h)
   if Path(p)==self.c:self.i.write_text('{}')
   return data
  with patch.object(f,'read',side_effect=changing):
   with self.assertRaisesRegex(ValueError,'changed before output'):f.make(self.i,f.sha(self.i),self.c,f.sha(self.c),self.r/'out')
 def test_mask_mismatch_rejected(self):
  self.mask.write_bytes(b'changed')
  with self.assertRaisesRegex(ValueError,'physical mask lineage'):f.make(self.i,f.sha(self.i),self.c,f.sha(self.c),self.r/'out')
 def test_pin_mismatch_rejected(self):
  with self.assertRaisesRegex(ValueError,'pinned input'):f.make(self.i,'x',self.c,f.sha(self.c),self.r/'out')
if __name__=='__main__':unittest.main()
