import json,tempfile,unittest
from pathlib import Path
import orchestrate_stage2 as o
import prepare_stage2_config as p
class ConfigTests(unittest.TestCase):
 def test_pins_only_fresh_inputs_and_refuses_overwrite(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);source=root/'input';source.mkdir();dest=root/'config';dest.mkdir();inputs={}
   for k in o.BASE_INPUTS:
    f=source/k;f.write_text(k);inputs[k]=str(f)
   controls={'minimum_free_bytes':1,'chunk_columns':16,'checkpoint_seconds':1,'numerical_guard_metres':1000,'block_records':100};sc={'strip_rows':1};g={'width':8,'height':4,'west':-180,'north':90,'step':45};out=dest/'config.json'
   r=p.create(out,inputs,g,'wgs','1',controls,sc);self.assertEqual(r['schema'],'stage2-fresh-config-receipt-v1');_,cfg=o.load_config(out);self.assertEqual(set(cfg['inputs']),o.BASE_INPUTS)
   with self.assertRaisesRegex(ValueError,'new file'):p.create(out,inputs,g,'wgs','1',controls,sc)
   huge={**g,'width':1000001,'step':360/1000001}
   with self.assertRaisesRegex(ValueError,'invalid global grid'):p.create(dest/'huge.json',inputs,huge,'wgs','1',controls,sc)
   inputs['old_checkpoint']=str(source/'physical_rows')
   with self.assertRaisesRegex(ValueError,'exact fresh input'):p.create(dest/'other.json',inputs,g,'wgs','1',controls,sc)
 def test_prior_report_requires_explicit_provisional_mode(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);source=root/'input';source.mkdir();dest=root/'config';dest.mkdir();inputs={}
   for k in o.BASE_INPUTS|{'prior_physical_report'}:
    f=source/k;f.write_text(k);inputs[k]=str(f)
   controls={'minimum_free_bytes':1,'chunk_columns':16,'checkpoint_seconds':1,'numerical_guard_metres':1000,'block_records':100};sc={'strip_rows':1};g={'width':8,'height':4,'west':-180,'north':90,'step':45}
   with self.assertRaisesRegex(ValueError,'exact fresh input'):p.create(dest/'no.json',inputs,g,'wgs','1',controls,sc)
   p.create(dest/'yes.json',inputs,g,'wgs','1',controls,sc,provisional_only=True)
   self.assertIn('prior_physical_report',o.load_config(dest/'yes.json')[1]['inputs'])
if __name__=='__main__':unittest.main()
