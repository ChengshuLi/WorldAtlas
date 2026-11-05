import hashlib,json,struct,tempfile,unittest
from unittest import mock
import os
from pathlib import Path
import run_diagnostic

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ints(p,v):p.write_bytes(struct.pack('<'+'I'*len(v),*v))
class CLITests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.p=Path(self.t.name);self.i=self.p/'inputs';self.i.mkdir();(self.p/'out').mkdir()
  for name in run_diagnostic.NAMES:(self.i/name).write_bytes(b'dummy')
  ints(self.i/'component_rows',[0,2,4,5]);ints(self.i/'component_runs',[0,2,9,7,8,1,2,4,9,4,6,2,7,8,1]);ints(self.i/'representatives',[0,0,0,0,17,0,0,1,4,18]);(self.i/'tile_manifest').write_text('0 0 2 3 '+('0'*64)+'\n')
  self.grid=dict(width=8,height=3,step=45,west=-180,north=90)
  snapshot=dict(schema='worldatlas-geography-decision-draft-evidence-v1',source='neon-export',decision_revision=dict(id='d',entity_revision='e',status='draft'),entity_revision=dict(id='e',status='draft'),distance_policies=[dict(policy_id='worldatlas-wgs84-geodesic',version='1',decision_revision='d',execution_status='selected_for_research',algorithm='wgs84_ellipsoidal_geodesic_inverse',units='metres',semi_major_axis_m='6378137',inverse_flattening='298.257223563')],category_bindings=[dict(code=17,physical_class='land'),dict(code=18,physical_class='land')]);(self.i/'decision_snapshot').write_text(json.dumps(snapshot))
  hashes={k:sha(self.i/k) for k in ('physical_rows','physical_runs','component_rows','component_runs')}
  report=dict(schema='mainland-witness-resolution-v1',status='selected-research-identity-claims-not-mainland-proof',publishable=False,grid=self.grid,input_sha256=hashes,snapshot_sha256=sha(self.i/'decision_snapshot'),component_manifest_sha256=sha(self.i/'component_manifest'),decision_revision='d',entity_revision='e',groups=[dict(group_id='g',role='mainland',target_entity_ids=['asia'],component_id_current_generation_only=9)])
  (self.i/'resolution_report').write_text(json.dumps(report))
  self.config=dict(schema='source-only-hints-diagnostic-request-v1',grid=self.grid,codes=[17,18],inputs={k:{'path':str(self.i/k),'sha256':sha(self.i/k)} for k in run_diagnostic.NAMES},decision_revision='d',entity_revision='e',policy_id='worldatlas-wgs84-geodesic',policy_version='1',minimum_memory_kib=1,minimum_free_bytes=1)
  self.req=self.i/'request';self.req.write_text(json.dumps(self.config))
 def tearDown(self):self.t.cleanup()
 def test_complete_and_no_overwrite(self):
  out=self.p/'out'/'a';r=run_diagnostic.run(self.req,out)
  self.assertEqual(r['root_count'],2);self.assertEqual(r['status'],'diagnostic-not-independently-authenticated');self.assertEqual((out/'roots.u32le').read_bytes(),struct.pack('<II',1,2));self.assertEqual((out/'hints.u8').read_bytes(),bytes([17,18]));self.assertTrue((out/'report.json').is_file())
  with self.assertRaisesRegex(ValueError,'fresh'):run_diagnostic.run(self.req,out)
 def test_changed_input_fails_before_output(self):
  (self.i/'component_runs').write_bytes(b'corrupt');out=self.p/'out'/'b'
  with self.assertRaisesRegex(ValueError,'hash mismatch'):run_diagnostic.run(self.req,out)
  self.assertFalse(out.exists())
 def test_unselected_policy_fails_closed(self):
  p=self.i/'decision_snapshot';snap=json.loads(p.read_text());snap['distance_policies'][0]['execution_status']='proposed_not_selected';p.write_text(json.dumps(snap));self.config['inputs']['decision_snapshot']['sha256']=sha(p)
  q=self.i/'resolution_report';r=json.loads(q.read_text());r['snapshot_sha256']=sha(p);q.write_text(json.dumps(r));self.config['inputs']['resolution_report']['sha256']=sha(q);self.req.write_text(json.dumps(self.config))
  with self.assertRaisesRegex(ValueError,'selected WGS84'):run_diagnostic.run(self.req,self.p/'out'/'bad-policy')
 def test_link_uncertainty_is_explicit(self):
  out=self.p/'out'/'uncertain';real=os.link
  def link_then_error(a,b):real(a,b);raise OSError('simulated uncertain link')
  with mock.patch.object(run_diagnostic.os,'link',side_effect=link_then_error):
   with self.assertRaisesRegex(RuntimeError,'may exist'):run_diagnostic.run(self.req,out)
  self.assertTrue((out/'report.json').exists())
 def test_foreign_policy_revision_rejected(self):
  p=self.i/'decision_snapshot';snap=json.loads(p.read_text());snap['distance_policies'][0]['decision_revision']='foreign';p.write_text(json.dumps(snap));self.config['inputs']['decision_snapshot']['sha256']=sha(p)
  q=self.i/'resolution_report';r=json.loads(q.read_text());r['snapshot_sha256']=sha(p);q.write_text(json.dumps(r));self.config['inputs']['resolution_report']['sha256']=sha(q);self.req.write_text(json.dumps(self.config))
  with self.assertRaisesRegex(ValueError,'policy revision'):run_diagnostic.run(self.req,self.p/'out'/'bad-revision')
 def test_memory_guard_fails_before_output(self):
  self.config['minimum_memory_kib']=10**15;self.req.write_text(json.dumps(self.config));out=self.p/'out'/'c'
  with self.assertRaisesRegex(RuntimeError,'resource floor'):run_diagnostic.run(self.req,out)
  self.assertFalse(out.exists())
if __name__=='__main__':unittest.main()
