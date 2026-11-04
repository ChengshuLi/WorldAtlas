import gzip,json,tempfile,unittest
from pathlib import Path
import numpy as np
import build_coastal_tile as b
from test_coastal_core import snap
from test_helpers import rle

class TileTest(unittest.TestCase):
 def fixture(self):
  p=np.ones((180,360),dtype=np.uint32);l=np.zeros_like(p)
  p[89,4]=p[89,6]=17;l[89,4]=17;l[89,6]=18
  snapshot=snap();snapshot['decision_revision']={'id':'draft','status':'draft','entity_revision':'entities'}
  return snapshot,rle(p),rle(l)
 def test_generate_single_core_and_preserve_inputs(self):
  s,p,l=self.fixture();before=[x.copy() for x in (*p,*l)]
  with tempfile.TemporaryDirectory() as d:
   out=Path(d)/'tile';m=b.run(s,'a'*64,p,l,out,360,180,[3,9,89,90],180,{'test':'pin'},chunk=2,allow_selected_research=True)
   with gzip.open(out/'coastal-assignments.jsonl.gz','rt') as f:r=json.loads(f.readline())
   self.assertEqual([(z['start'],z['end'],z['code']) for z in r['spans']],[(3,4,1),(5,6,2),(7,8,2)])
   self.assertEqual(m['assigned_cells'],3);self.assertEqual(m['physical_water_cells'],4)
   self.assertIn('partial',m['status']);self.assertEqual(m['core_cols'],[3,9])
   with self.assertRaises(FileExistsError):b.run(s,'a'*64,p,l,out,360,180,[3,9,89,90],180,{},chunk=2,allow_selected_research=True)
  for arr,old in zip((*p,*l),before):np.testing.assert_array_equal(arr,old)
 def test_input_mutation_fails_without_complete_manifest(self):
  s,p,l=self.fixture()
  with tempfile.TemporaryDirectory() as d:
   out=Path(d)/'out'
   def verify():raise ValueError('input changed')
   with self.assertRaisesRegex(ValueError,'input changed'):b.run(s,'a'*64,p,l,out,360,180,[3,9,89,90],180,{},verify_inputs=verify,allow_selected_research=True)
   self.assertFalse((out/'manifest.json').exists())
 def test_raw_physical_report_pin_required(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);rows=root/'rows';runs=root/'runs';rows.write_bytes(b'rows');runs.write_bytes(b'runs');report_path=root/'report.json'
   pin={'path':'source','sha256':'a'*64};physical={'rows_sha256':b.sha(rows),'runs_sha256':b.sha(runs)}
   report={'status':'candidate-only','grid':{'width':4,'height':2,'west':-180,'north':90,'step':90},
           'physical_output_sha256':{'rows.u32le':b.sha(rows),'runs.u32le':b.sha(runs)},
           'source_manifest':pin,'land_config':pin,'water_config':pin,'stage_reports':{}}
   report_path.write_text(json.dumps(report))
   self.assertEqual(b.validate_physical_report(report_path,b.sha(report_path),physical,4,2),'raw-pipeline-report')
   report['source_manifest']={};report_path.write_text(json.dumps(report))
   with self.assertRaisesRegex(ValueError,'source pins'):b.validate_physical_report(report_path,b.sha(report_path),physical,4,2)
 def test_shore_segment_limit(self):
  s,p,l=self.fixture()
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaisesRegex(ValueError,'segment limit'):b.run(s,'a'*64,p,l,Path(d)/'out',360,180,[3,9,89,90],180,{},allow_selected_research=True,max_shore_segments=1)
 def test_missing_policy_or_bad_core_fails(self):
  s,p,l=self.fixture();s['policies']=[]
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaisesRegex(ValueError,'policy'):b.run(s,'a'*64,p,l,Path(d)/'out',360,180,[3,9,89,90],180,{},allow_selected_research=True)
   with self.assertRaisesRegex(ValueError,'invalid coastal tile'):b.run(s,'a'*64,p,l,Path(d)/'out',360,180,[3,9,90,89],180,{},allow_selected_research=True)

if __name__=='__main__':unittest.main()
