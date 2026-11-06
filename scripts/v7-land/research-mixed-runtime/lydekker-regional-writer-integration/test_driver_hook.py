import hashlib,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import driver_hook

def pin(p):return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
class HookTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();d=Path(self.tmp.name)
  for n,v in [('policy',{'evidence':{'decision_snapshot_sha256':'a'*64}}),('line',{}),('pending',[])]:
   p=d/(n+'.json');p.write_text(json.dumps(v));setattr(self,n,p)
  self.cfg={'policy':pin(self.policy),'policy_canonical_sha256':'b'*64,'line':pin(self.line),'pending':pin(self.pending),'pending_inventory_complete':False,'profiling_standin':True,'sources':{},'code':{}}
 def tearDown(self):self.tmp.cleanup()
 def test_incomplete_pending_requires_profiling(self):
  self.cfg['profiling_standin']=False
  with self.assertRaisesRegex(ValueError,'profiling'):driver_hook.prepare(self.cfg,{}, {},[],{}, {},set(),None,lambda:None,snapshot_sha256='a'*64)
 def test_snapshot_mismatch_precedes_module_loading(self):
  with patch.object(driver_hook,'modules_from_pins') as m:
   with self.assertRaisesRegex(ValueError,'snapshot'):driver_hook.prepare(self.cfg,{}, {},[],{}, {},set(),None,lambda:None,snapshot_sha256='c'*64)
   m.assert_not_called()
 def test_changed_pinned_input_fails(self):
  self.line.write_text('{"changed":true}')
  with self.assertRaisesRegex(ValueError,'pin mismatch'):driver_hook.prepare(self.cfg,{}, {},[],{}, {},set(),None,lambda:None,snapshot_sha256='a'*64)
 def test_prepares_same_run_reports_and_wrap(self):
  reports=[{'from':'actual driver'}];seen={};none=lambda *a,**k:None
  def resolve(*a,**k):
   seen['reports']=a[3];seen['snapshot_sha256']=k['snapshot_sha256'];seen['pending']=k['pending_claims']
   return {'regional_result':{'review':{3:'source_group_pending_review'}},'writer_bridge':{'component_claims':{2:[{'code':18}]},'blocked_region_roots':[3,9],'regional_proposal_trace':{2:{'basis':'whole_component_line_side'}},'synthetic_affiliation_id':'rule'}}
  modules={'regional_workflow':NS(research=none,buffered_bounds=none),'regional_rule':NS(verified_line=none),'component_scan':NS(scan=none,collect_runs=none,component_at=none),'source_groups':NS(resolve_feature_windows=none),'regional_group_convention':NS(apply_groups=none),'replay_adapter':NS(resolve_with_mixed_replay=none),'satellite_geodesic':NS(apply_satellites=none),'land_archive_source':NS(extract=none),'polygon_intersection':NS(intersect=none),'run_pair':NS(run_pair=none),'live_driver':NS(resolve_live=resolve),'adapter':NS(protected_region_rows=none)}
  with patch.object(driver_hook,'modules_from_pins',return_value=modules):
   out=driver_hook.prepare(self.cfg,{}, {},reports,{}, {},{9},None,lambda:None,snapshot_sha256='a'*64)
   self.assertIs(seen['reports'],reports);self.assertEqual(seen['snapshot_sha256'],'a'*64);self.assertEqual(seen['pending'],[]);self.assertEqual(out['blocked_region_roots'],[3,9]);self.assertTrue(out['provenance']['profiling_standin']);out['verify']()
   self.pending.write_text('[{}]')
   with self.assertRaisesRegex(ValueError,'changed during run'):out['verify']()
if __name__=='__main__':unittest.main()
