import gzip,hashlib,json,tempfile,unittest
from pathlib import Path
import assemble_coastal_tiles as a
from test_coastal_core import snap


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

class AssemblyTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.s=snap();self.entries=[]
  for i,(x0,x1) in enumerate(((0,2),(2,4))):
   d=self.root/str(i);d.mkdir();f=d/'tile.gz'
   with gzip.open(f,'wt') as g:g.write(json.dumps({'row':0,'spans':[{'start':x0,'end':x0+1,'code':1,'rule_id':'r','member_id':'m'}]})+'\n')
   m={'schema':'worldatlas-coastal-tile-candidate-v1','status':'partial-unverified-research-not-published',
      'grid':{'width':4,'height':2,'angular_step_deg':90.0},'policy_id':'test-coast','policy_definition':self.s['policies'][0]['definition'],
      'decision_snapshot_sha256':'a'*64,'decision_revision':'draft','entity_revision':'entities','core_cols':[x0,x1],'core_rows':[0,2],
      'inputs':{k:'b'*64 for k in ('physical_rows_sha256','physical_runs_sha256','physical_report_sha256','land_rows_sha256','land_runs_sha256','land_report_sha256')},'algorithm_sha256':'c'*64,'core_sha256':'d'*64,'shore_sha256':'e'*64,'geometry_sha256':'f'*64,
      'assigned_cells':1,'span_count':1,'span_file':{'path':'tile.gz','sha256':sha(f)}}
   path=d/'manifest.json';path.write_text(json.dumps(m));self.entries.append({'manifest_path':f'{i}/manifest.json','manifest_sha256':sha(path)})
 def tearDown(self):self.tmp.cleanup()
 def write(self,i,modify):
  p=self.root/str(i)/'manifest.json';m=json.loads(p.read_text());modify(m);p.write_text(json.dumps(m));self.entries[i]['manifest_sha256']=sha(p)
 def call(self):return a.assemble(self.s,'a'*64,self.entries,self.root,self.root/'layer.json',4,2,allow_selected_research=True)
 def test_full_coverage(self):
  m=self.call();self.assertEqual(m['assigned_cells'],2);self.assertEqual(len(m['tiles']),2);self.assertTrue(m['coverage']['complete'])
 def test_gap_or_overlap(self):
  self.write(1,lambda m:m.update(core_cols=[3,4]))
  with self.assertRaisesRegex(ValueError,'invalid tile span|coverage gap'):self.call()
  self.write(1,lambda m:m.update(core_cols=[1,4]))
  with self.assertRaisesRegex(ValueError,'overlap'):self.call()
 def test_mixed_lineage_and_tampering(self):
  self.write(1,lambda m:m['inputs'].update(land_rows_sha256='1'*64))
  with self.assertRaisesRegex(ValueError,'mixed'):self.call()
  self.write(1,lambda m:m['inputs'].update(land_rows_sha256='b'*64))
  with (self.root/'0/tile.gz').open('ab') as f:f.write(b'x')
  with self.assertRaises((ValueError,OSError,EOFError)):self.call()
 def test_unselected_fails_even_with_optin(self):
  self.s['policies'][0]['evidence']['execution_status']='research_only_not_selected'
  with self.assertRaisesRegex(ValueError,'selected draft'):self.call()

if __name__=='__main__':unittest.main()
