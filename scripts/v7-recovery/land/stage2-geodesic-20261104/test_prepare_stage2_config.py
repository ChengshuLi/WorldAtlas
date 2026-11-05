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
   controls={'minimum_memory_kib':1,'minimum_free_bytes':1,'chunk_columns':16,'checkpoint_seconds':1,'tile_cache_bytes':1024,'numerical_guard_metres':1000,'block_records':100};sc={'timeout_seconds':30,'strip_rows':1,'max_group_rss_kib':262144};g={'width':8,'height':4,'west':-180,'north':90,'step':45};out=dest/'config.json'
   r=p.create(out,inputs,g,'wgs','1',controls,sc,262144);self.assertEqual(r['schema'],'stage2-fresh-config-receipt-v1');_,cfg=o.load_config(out);self.assertEqual(set(cfg['inputs']),o.BASE_INPUTS)
   with self.assertRaisesRegex(ValueError,'new file'):p.create(out,inputs,g,'wgs','1',controls,sc,262144)
   huge={**g,'width':1000001,'step':360/1000001}
   with self.assertRaisesRegex(ValueError,'invalid global grid'):p.create(dest/'huge.json',inputs,huge,'wgs','1',controls,sc,262144)
   inputs['old_checkpoint']=str(source/'physical_rows')
   with self.assertRaisesRegex(ValueError,'exact fresh input'):p.create(dest/'other.json',inputs,g,'wgs','1',controls,sc,262144)
if __name__=='__main__':unittest.main()
