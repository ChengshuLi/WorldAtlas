import hashlib,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import driver_hook

def pin(p):return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
class HookTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();d=Path(self.tmp.name)
  self.mixed_path=d/'mixed.py';self.mixed_path.write_text('mixed fixture')
  self.mixed=NS(__file__=str(self.mixed_path))
  for n,v in [('policy',{'evidence':{'decision_snapshot_sha256':'a'*64,'mixed_claims_sha256':pin(self.mixed_path)['sha256']}}),('line',{}),('pending',[])]:
   p=d/(n+'.json');p.write_text(json.dumps(v));setattr(self,n,p)
  self.cfg={'policy':pin(self.policy),'policy_canonical_sha256':'b'*64,'line':pin(self.line),'pending':pin(self.pending),'pending_inventory_complete':False,'profiling_standin':True,'sources':{},'code':{}}
 def tearDown(self):self.tmp.cleanup()
 def test_incomplete_pending_requires_profiling(self):
  self.cfg['profiling_standin']=False
  with self.assertRaisesRegex(ValueError,'profiling'):driver_hook.prepare(self.cfg,{}, {},[],{}, {},set(),None,snapshot_sha256='a'*64)
 def test_snapshot_mismatch_precedes_module_loading(self):
  with patch.object(driver_hook,'modules_from_pins') as m:
   with self.assertRaisesRegex(ValueError,'snapshot'):driver_hook.prepare(self.cfg,{}, {},[],{}, {},set(),None,snapshot_sha256='c'*64)
   m.assert_not_called()
 def test_real_driver_import_uses_exact_loaded_module_pins(self):
  import subprocess,sys
  root=Path(__file__).resolve().parent.parent
  script="""
import hashlib,importlib.util,json,sys
from pathlib import Path
R=Path(sys.argv[1]);D=R/'lydekker-regional-writer-integration';W=R/'lydekker-regional-rule';T=R/'stage3-mixed-leeward-full-20261105';P=R.parents[1]/'v7-recovery/land/stage2-geodesic-20261104'
sys.path[:0]=[str(T),str(D)];sp=importlib.util.spec_from_file_location('real_mixed_driver',T/'apply_selected_mixed.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
import driver_hook
paths={n:W/(n+'.py') for n in ('regional_rule','component_scan','replay_adapter','geonames_anchors','satellite_geodesic','regional_workflow','regional_group_convention')};paths.update({n:D/(n+'.py') for n in ('source_groups','adapter','live_driver')});paths.update({n:P/(n+'.py') for n in ('point_prototype','run_pair')});paths.update({n:T/(n+'.py') for n in ('land_archive_source','polygon_intersection')});pins={n:{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for n,p in paths.items()};policy={'evidence':{'runtime_code_sha256':{n+'.py':pins[n]['sha256'] for n in ('regional_rule','component_scan','replay_adapter','geonames_anchors','satellite_geodesic','regional_workflow','regional_group_convention')},'wgs84_run_pair_sha256':pins['run_pair']['sha256'],'point_prototype_sha256':pins['point_prototype']['sha256']}};mods=driver_hook.modules_from_pins(pins,policy);assert Path(mods['polygon_intersection'].__file__).resolve()==(T/'polygon_intersection.py').resolve()
"""
  run=subprocess.run([sys.executable,'-c',script,str(root)],text=True,capture_output=True)
  self.assertEqual(run.returncode,0,run.stderr)
 def test_mixed_code_mismatch_fails(self):
  self.mixed_path.write_text('tampered')
  with self.assertRaisesRegex(ValueError,'mixed claims code mismatch'):driver_hook.prepare(self.cfg,{}, {},[],{}, {},set(),self.mixed,snapshot_sha256='a'*64)
 def test_changed_pinned_input_fails(self):
  self.line.write_text('{"changed":true}')
  with self.assertRaisesRegex(ValueError,'pin mismatch'):driver_hook.prepare(self.cfg,{}, {},[],{}, {},set(),None,snapshot_sha256='a'*64)
 def test_prepares_same_run_reports_and_wrap(self):
  reports=[{'from':'actual driver'}];seen={};none=lambda *a,**k:None
  def resolve(*a,**k):
   seen['reports']=a[3];seen['snapshot_sha256']=k['snapshot_sha256'];seen['pending']=k['pending_claims']
   return {'regional_result':{'review':{3:'source_group_pending_review'}},'writer_bridge':{'component_claims':{2:[{'code':18}]},'blocked_region_roots':[3,9],'regional_proposal_trace':{2:{'basis':'whole_component_line_side'}},'synthetic_affiliation_id':'rule'}}
  modules={'regional_workflow':NS(research=none,buffered_bounds=none),'regional_rule':NS(verified_line=none),'component_scan':NS(scan=none,collect_runs=none,component_at=none),'source_groups':NS(resolve_feature_windows=none),'regional_group_convention':NS(apply_groups=none),'replay_adapter':NS(resolve_with_mixed_replay=none),'satellite_geodesic':NS(apply_satellites=none),'land_archive_source':NS(extract=none),'polygon_intersection':NS(intersect=none),'run_pair':NS(run_pair=none),'live_driver':NS(resolve_live=resolve),'adapter':NS(protected_region_rows=none)}
  with patch.object(driver_hook,'modules_from_pins',return_value=modules):
   out=driver_hook.prepare(self.cfg,{}, {},reports,{}, {},{9},self.mixed,snapshot_sha256='a'*64)
   self.assertIs(seen['reports'],reports);self.assertEqual(seen['snapshot_sha256'],'a'*64);self.assertEqual(seen['pending'],[]);self.assertEqual(out['blocked_region_roots'],[3,9]);self.assertTrue(out['provenance']['profiling_standin']);out['verify']()
   self.pending.write_text('[{}]')
   with self.assertRaisesRegex(ValueError,'changed during run'):out['verify']()
class ActualDriverBlockTests(unittest.TestCase):
 def test_real_driver_hook_block_wraps_actual_overlay(self):
  import importlib.util,os,textwrap
  from adapter import protected_region_rows
  path=os.environ.get('OVERLAY_PATH')
  if not path:self.skipTest('actual writer overlay unavailable')
  spec=importlib.util.spec_from_file_location('driver_hook_overlay',path);overlay=importlib.util.module_from_spec(spec);spec.loader.exec_module(overlay)
  src=(Path(__file__).parent.parent/'stage3-mixed-leeward-full-20261105/apply_selected_mixed.py').read_text()
  block=src[src.index(' regional=None;regional_paths=[];region_rows=lambda y:[]'):src.index(' if requirements:',src.index(' regional=None;regional_paths=[];region_rows=lambda y:[]'))]
  seen={}
  def prepare(cfg,compiled,snapshot,reports,grid,inputs,mainland,mixed,*,snapshot_sha256):
   seen['reports']=reports;seen['snapshot']=snapshot_sha256
   return {'component_claims':{2:[{'affiliation_id':'rule','entry_ids':['rule'],'code':18}]},'blocked_region_roots':[3,9],'wrap_region_rows':protected_region_rows,'provenance':{'decision_snapshot_sha256':'a'*64},'input_paths':[]}
  ctx={'cfg':{'regional':{'hook':{},'request':{}}},'pinned':lambda spec:Path(__file__),'loadmodule':lambda name,path:NS(prepare=prepare),'compiled':{},'snapshot':{},'reports':[{'fresh':True}],'report':{'grid':{},'physical_coverage':{'seed_roots':[9]}},'req':{**{k:{} for k in ('physical_rows','physical_runs','component_rows','component_runs')},'snapshot':{'sha256':'a'*64}},'mixed_claims':None,'need':driver_hook.need,'Path':Path}
  exec(compile(textwrap.dedent(block),'actual-driver-hook-block','exec'),ctx)
  self.assertIs(seen['reports'],ctx['reports']);self.assertEqual(seen['snapshot'],'a'*64)
  # Replace only the raw callback, then apply the exact wrapper selected by the driver.
  raw=lambda y:[{'claim':{'affiliation_id':'other','entry_ids':['entry'],'code':22},'roots':{3,9},'spans':[(0,4)]}]
  regions=ctx['regional']['wrap_region_rows'](raw,ctx['regional']['blocked_region_roots'])(0);stats={}
  row=overlay.overlay_row(4,[(0,4,17)],[(4,18)],[(0,1,1),(1,2,2),(2,3,3),(3,4,9)],ctx['claims'],regions,stats,lambda *v:None)
  self.assertEqual(row,[(4,18)]);self.assertNotIn('other',stats)
  self.assertIn('component_claims=claims,mainland_roots=',src);self.assertIn('region_rows=region_rows,output=out',src)
if __name__=='__main__':unittest.main()
