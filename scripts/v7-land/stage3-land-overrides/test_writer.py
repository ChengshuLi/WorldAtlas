import json,struct,tempfile,unittest
from unittest.mock import patch
from pathlib import Path
from writer import write_streams
U=struct.Struct('<I');P=struct.Struct('<II');T=struct.Struct('<III')
def save(p,fmt,values):p.write_bytes(b''.join(fmt.pack(*x) if isinstance(x,tuple) else fmt.pack(x) for x in values));return p
class WriterTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.base=Path(self.t.name);self.src=self.base/'src';self.src.mkdir();self.o=self.base/'out';self.grid={'width':10,'height':2,'west':-180,'north':90,'step':36}
  self.pr=save(self.src/'pr',U,[0,3,4]);self.pv=save(self.src/'pv',P,[(2,1),(8,17),(10,1),(10,1)]);self.cr=save(self.src/'cr',U,[0,2,2]);self.cv=save(self.src/'cv',T,[(2,5,10),(5,8,11)]);self.br=save(self.src/'br',U,[0,3,4]);self.bv=save(self.src/'bv',P,[(2,0),(8,18),(10,0),(10,0)])
 def runv(self,claims=None,regions=None,mainlands=None):
  return write_streams(grid=self.grid,physical_rows=self.pr,physical_runs=self.pv,component_rows=self.cr,component_runs=self.cv,baseline_rows=self.br,baseline_runs=self.bv,component_claims=claims or {},mainland_roots=mainlands or {99},region_rows=regions or (lambda y:[]),output=self.o,guard=lambda:None,disk_reserve_bytes=2*1024**3)
 def test_component_output_and_trace(self):
  c={'affiliation_id':'a','entry_ids':['entry'],'code':19};r=self.runv({10:[c]});self.assertEqual(r['changed_cells'],3);self.assertEqual(r['change_spans'],1);rows=list(struct.iter_unpack('<I',(self.o/'rows.u32le').read_bytes()));runs=list(struct.iter_unpack('<II',(self.o/'runs.u32le').read_bytes()));self.assertEqual([x[0] for x in rows],[0,4,5]);self.assertEqual(runs,[(2,0),(5,19),(8,18),(10,0),(10,0)]);self.assertEqual(json.loads((self.o/'changes.jsonl').read_text())['entry_ids'],['entry']);self.assertFalse((self.o/'report.json').exists())
 def test_region_mixed_decisions(self):
  a={'affiliation_id':'a','entry_ids':['a-entry'],'code':19};b={'affiliation_id':'b','entry_ids':['b-entry'],'code':19};r=self.runv({10:[a]},lambda y:[{'claim':b,'roots':{10},'spans':[(3,5)]}] if y==0 else []);self.assertEqual(r['changed_cells'],3);self.assertEqual(r['affiliation_statistics']['b']['changed_cells'],2);self.assertEqual(r['change_spans'],2)
 def test_conflict_never_has_completion_marker(self):
  a={'affiliation_id':'a','entry_ids':['a-entry'],'code':19};b={'affiliation_id':'b','entry_ids':['b-entry'],'code':20}
  with self.assertRaisesRegex(ValueError,'conflicting'):self.runv({10:[a]},lambda y:[{'claim':b,'roots':{10},'spans':[(3,5)]}] if y==0 else [])
  self.assertFalse((self.o/'report.json').exists())
 def test_mainland_component_claim_rejected(self):
  with self.assertRaisesRegex(ValueError,'targets mainland'):self.runv({10:[{'affiliation_id':'a','entry_ids':['e'],'code':19}]},mainlands={10})
 def test_mainland_region_claim_rejected(self):
  claim={'affiliation_id':'a','entry_ids':['e'],'code':19}
  with self.assertRaisesRegex(ValueError,'region claim targets mainland'):self.runv(regions=lambda y:[{'claim':claim,'roots':{10},'spans':[(2,3)]}],mainlands={10})
  self.assertFalse((self.o/'report.json').exists())
 def test_trace_bytes_checked_against_reserve(self):
  claim={'affiliation_id':'a'*(2<<20),'entry_ids':['e'],'code':19};reserve=2*1024**3
  class Usage:
   free=reserve+(1536<<10)
  with patch('writer.shutil.disk_usage',return_value=Usage()):
   with self.assertRaisesRegex(ValueError,'disk reserve'):self.runv({10:[claim]})
  self.assertFalse((self.o/'report.json').exists())
 def test_output_inside_input_rejected(self):
  self.o=self.src/'inside'
  with self.assertRaisesRegex(ValueError,'overlaps'):self.runv()
 def test_trailing_runs_rejected(self):
  with self.pv.open('ab') as f:f.write(P.pack(10,1))
  with self.assertRaisesRegex(ValueError,'trailing'):self.runv()
if __name__=='__main__':unittest.main()
