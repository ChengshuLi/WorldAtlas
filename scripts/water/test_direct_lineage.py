import json,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
import direct_lineage as d

class LineageTest(unittest.TestCase):
 def test_streaming_land_uses_shared_validator_and_physical_report_pin(self):
  calls=[];stub=types.ModuleType('build_prefill_plan');stub.validate_land_report=lambda *args,**kwargs:calls.append((args,kwargs))
  with tempfile.TemporaryDirectory() as t,patch.dict(sys.modules,{'build_prefill_plan':stub}):
   p=Path(t)/'land.json';p.write_text(json.dumps({'schema':'single-generation-direct-land-report-v1','physical_report_sha256':'a'*64}))
   d.validate_direct_land(p,d.sha(p),{}, {},'b'*64,{'id':'d'},t,'a'*64)
   self.assertEqual(len(calls),1);self.assertEqual(calls[0][1]['input_root'],Path(t).resolve())
   with self.assertRaisesRegex(ValueError,'different physical report'):d.validate_direct_land(p,d.sha(p),{}, {},'b'*64,{'id':'d'},t,'c'*64)
   with self.assertRaisesRegex(ValueError,'hash mismatch'):d.validate_direct_land(p,'0'*64,{}, {},'b'*64,{'id':'d'},t,'a'*64)
 def test_compose_report_source_pins_and_grid(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'physical.json';pin={'path':'source','sha256':'a'*64};grid={'width':4,'height':2,'west':-180,'north':90,'step':90}
   report={'status':'candidate-only','grid':grid,'configuration_sha256':'b'*64,'inputs':{'land':pin,'water':pin},
           'output_sha256':{'rows.u32le':'c'*64,'runs.u32le':'d'*64}}
   p.write_text(json.dumps(report));physical={'rows_sha256':'c'*64,'runs_sha256':'d'*64}
   self.assertEqual(d.validate_physical_report(p,d.sha(p),physical,4,2),'compose-report')
   report['grid']['width']=5;p.write_text(json.dumps(report))
   with self.assertRaisesRegex(ValueError,'candidate grid'):d.validate_physical_report(p,d.sha(p),physical,4,2)

if __name__=='__main__':unittest.main()
