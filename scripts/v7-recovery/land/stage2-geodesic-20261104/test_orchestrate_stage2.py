import json,subprocess,sys,tempfile,unittest
from unittest import mock
from pathlib import Path
import orchestrate_stage2 as o

class OrchestrationTests(unittest.TestCase):
 def fixture(self,root):
  p=Path(root);ind=p/'inputs';ind.mkdir();pins={}
  for key in o.BASE_INPUTS:
   f=ind/(key+'.txt');f.write_text(key);pins[key]=o.pin(f,lambda:None)
  cfg={'schema':'stage2-fresh-orchestration-v1','grid':{'width':8,'height':4,'west':-180,'north':90,'step':45},'inputs':pins,'policy_id':'wgs','policy_version':'1','controls':{'minimum_free_bytes':1,'chunk_columns':16,'checkpoint_seconds':1,'numerical_guard_metres':1000,'block_records':100},'seed_controls':{'strip_rows':1}}
  cp=ind/'config.json';cp.write_text(json.dumps(cfg));return p,cp,cfg
 def test_seed_launcher_is_identity_pinned_but_not_in_producer_report(self):
  import ast
  source=(o.HERE/'seed-producer'/'seed_producer.py').read_text();tree=ast.parse(source)
  decl=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CODE' for t in n.targets))
  self.assertEqual(set(ast.literal_eval(decl.value)),set(o.SEED_REPORT_NAMES))
  self.assertIn('seed_worker.py',o.SEED_NAMES);self.assertNotIn('seed_worker.py',o.SEED_REPORT_NAMES)
  self.assertIn('seed-producer/seed_worker.py',o.code_hashes(lambda:None))
 def test_rejected_historical_input(self):
  with tempfile.TemporaryDirectory() as d:
   p,cp,cfg=self.fixture(d);cfg['inputs']['old_checkpoint']={'path':'/tmp/old','sha256':'0'*64};cp.write_text(json.dumps(cfg))
   with self.assertRaisesRegex(ValueError,'historical input'):o.load_config(cp)
 def test_unreviewed_freeze_stops_before_work(self):
  with tempfile.TemporaryDirectory() as d:
   p,cp,cfg=self.fixture(d)
   with mock.patch.object(o,'SEED_FREEZE_CURRENT',True),mock.patch.object(o,'REVIEWED_SEED_FREEZE',{}):
    with self.assertRaisesRegex(ValueError,'reviewed seed producer'):o.run(cp,p/'work',p/'output')
   self.assertFalse((p/'work').exists());self.assertFalse((p/'output').exists())
 def test_provisional_only_requires_distinct_marked_paths(self):
  with tempfile.TemporaryDirectory() as d:
   p,cp,cfg=self.fixture(d)
   with self.assertRaisesRegex(ValueError,r'separate \*-provisional-only'):
    o.run(cp,p/'work',p/'output',provisional_only=True)
   self.assertFalse((p/'work').exists());self.assertFalse((p/'output').exists())
 def test_freeze_must_bind_invoked_seed_worker_entrypoint(self):
  with tempfile.TemporaryDirectory() as d:
   p,cp,cfg=self.fixture(d);code=o.code_hashes(lambda:None)
   incomplete={n:code['seed-producer/'+n] for n in o.SEED_NAMES if n!='seed_worker.py'}
   with mock.patch.object(o,'SEED_FREEZE_CURRENT',True),mock.patch.object(o,'REVIEWED_SEED_FREEZE',incomplete):
    with self.assertRaisesRegex(ValueError,'reviewed seed producer'):o.run(cp,p/'work',p/'output')
   self.assertFalse((p/'work').exists());self.assertFalse((p/'output').exists())
 def test_unimplemented_crosswalk_stops_before_work(self):
  with tempfile.TemporaryDirectory() as d:
   p,cp,cfg=self.fixture(d)
   current={n:o.code_hashes(lambda:None)['seed-producer/'+n] for n in o.SEED_NAMES}
   with mock.patch.object(o,'SEED_FREEZE_CURRENT',True),mock.patch.object(o,'REVIEWED_SEED_FREEZE',current),mock.patch.object(o,'SELECTED_POLICY_CROSSWALK_READY',False):
    with self.assertRaisesRegex(ValueError,'crosswalk not yet implemented'):o.run(cp,p/'work',p/'output')
   self.assertFalse((p/'work').exists())
 def test_direct_core_build_binds_generated_artifacts_and_resume(self):
  import hashlib
  with tempfile.TemporaryDirectory() as d:
   p,cp,cfg=self.fixture(d);work=p/'work';work.mkdir()
   for x in ('derived','core-requests','requests','resolution','seed-work-parent/output','tiles-parent/tiles','hints-parent/hints','reps','lineage'):(work/x).mkdir(parents=True,exist_ok=True)
   tiles=work/'tiles-parent'/'tiles';snap={'schema':'worldatlas-geography-decision-draft-evidence-v1','source':'neon-export','decision_revision':{'id':'d','entity_revision':'e','status':'draft'},'entity_revision':{'id':'e','status':'draft'},'distance_policies':[{'policy_id':'wgs','version':'1','decision_revision':'d','execution_status':'selected_for_research','algorithm':'wgs84_ellipsoidal_geodesic_inverse','units':'metres','semi_major_axis_m':'6378137','inverse_flattening':'298.257223563'}],'entities':[{'id':i,'name':str(i),'level':'continent'} for i in range(6)],'category_bindings':[{'entity_id':i,'code':i+17,'physical_class':'land'} for i in range(6)]}
   sp=Path(cfg['inputs']['decision_snapshot']['path']);sp.write_text(json.dumps(snap));cfg['inputs']['decision_snapshot']=o.pin(sp,lambda:None);cp.write_text(json.dumps(cfg));raw=cp.read_bytes();code=o.code_hashes(lambda:None)
   paths={'resolution_report':work/'resolution/report.json','seed_rows':work/'seed-work-parent/output/rows.u32le','seed_runs':work/'seed-work-parent/output/runs.u32le','seed_report':work/'seed-work-parent/output/report.json','hint_roots':work/'hints-parent/hints/roots.u32le','hint_codes':work/'hints-parent/hints/hints.u8','hint_report':work/'hints-parent/hints/report.json','tile_manifest':work/'tiles-parent/tiles/manifest.txt','representatives':work/'reps/representatives.u32le'}
   for name,f in paths.items():f.write_text(name)
   artifacts={name:o.pin(f,lambda:None) for name,f in paths.items()}
   c=cfg['controls'];si={dst:cfg['inputs'][src] for dst,src in (('snapshot','decision_snapshot'),('physical_rows','physical_rows'),('physical_runs','physical_runs'),('physical_report','physical_report'),('component_rows','component_rows'),('component_runs','component_runs'),('component_manifest','component_manifest'),('closure_checker','closure_checker'),('terminal_checker','terminal_checker'),('closure_contract','closure_contract'),('seed_builder','seed_builder'),('seed_kernel','seed_kernel'))};si['resolution']=artifacts['resolution_report']
   sr={'schema':'worldatlas-stage2-seed-request-v1','grid':cfg['grid'],'inputs':si,'controls':{'disk_reserve_bytes':c['minimum_free_bytes'],**cfg['seed_controls']}};sh=o.write_json(work/'requests/seed.json',sr)
   hi={k:cfg['inputs'][k] for k in ('physical_rows','physical_runs','component_rows','component_runs','decision_snapshot','component_manifest')};hi.update({k:artifacts[k] for k in ('seed_rows','seed_runs','resolution_report','representatives','tile_manifest')})
   hr={'schema':'source-only-hints-diagnostic-request-v1','grid':cfg['grid'],'codes':list(range(17,23)),'inputs':hi,'decision_revision':'d','entity_revision':'e','policy_id':'wgs','policy_version':'1','minimum_free_bytes':c['minimum_free_bytes']};hh=o.write_json(work/'requests/hints.json',hr)
   paths['seed_report'].write_text(json.dumps({'request_sha256':sh,'input_sha256':{k:v['sha256'] for k,v in si.items()}}));paths['hint_report'].write_text(json.dumps({'request_sha256':hh}));artifacts.update({k:o.pin(paths[k],lambda:None) for k in ('seed_report','hint_report')})
   lineage={'schema':'stage1-reported-lineage-validation-v1','status':'reported-lineage-verified-not-rerasterized'};o.write_json(work/'lineage/report.json',lineage)
   marker={'schema':'stage2-fresh-derived-v1','outer_config_sha256':hashlib.sha256(raw).hexdigest(),'orchestrator_sha256':code['orchestrate_stage2.py'],'code_sha256':code,'artifacts':artifacts,'tile_directory':str(tiles),'seed_tile_verification':{'status':'verified'},'seed_request_sha256':sh,'hint_request_sha256':hh,'physical_lineage_report':o.pin(work/'lineage/report.json',lambda:None),'provisional_only':False};o.write_json(work/'derived/manifest.json',marker)
   with mock.patch.object(o.verify_physical_lineage,'validate_combined',return_value=lineage),mock.patch.object(o.build_stage2,'build',return_value={'ok':True}) as build:
    self.assertEqual(o.finish_from_marker(cfg,raw,work,p/'out',code,lambda:None,False),{'ok':True})
    core=json.loads((work/'core-requests/config.json').read_bytes());self.assertEqual(core['inputs']['seed_rows'],artifacts['seed_rows']);self.assertEqual(core['orchestration']['outer_config_sha256'],hashlib.sha256(raw).hexdigest())
    self.assertEqual(set(core['seed_code_files']),set(o.SEED_REPORT_NAMES)|{'rasterizer','rasterizer_kernel'});self.assertIn('seed-producer/seed_worker.py',marker['code_sha256'])
    o.finish_from_marker(cfg,raw,work,p/'out',code,lambda:None,True);self.assertFalse(build.call_args.kwargs['resume'])
    (work/'core').mkdir();o.finish_from_marker(cfg,raw,work,p/'out',code,lambda:None,True);self.assertTrue(build.call_args.kwargs['resume'])
    paths['seed_rows'].write_text('tampered')
    with self.assertRaisesRegex(ValueError,'input hash mismatch'):o.finish_from_marker(cfg,raw,work,p/'out',code,lambda:None,True)
    paths['seed_rows'].write_text('seed_rows');(work/'requests/seed.json').write_text('{}')
    with self.assertRaisesRegex(ValueError,'request hash mismatch'):o.finish_from_marker(cfg,raw,work,p/'out',code,lambda:None,True)
    marker['artifacts']['seed_rows']=o.pin(Path(cfg['inputs']['physical_rows']['path']),lambda:None);(work/'derived/manifest.json').unlink();o.write_json(work/'derived/manifest.json',marker)
    with self.assertRaisesRegex(ValueError,'not fresh work output'):o.finish_from_marker(cfg,raw,work,p/'out',code,lambda:None,True)
 def test_direct_cli_reaches_config_validation_without_guardian(self):
  cmd=[sys.executable,str(Path(o.__file__)), '/nonexistent/config', '/nonexistent/work', '/nonexistent/output']
  proc=subprocess.run(cmd,capture_output=True,text=True)
  self.assertNotEqual(proc.returncode,0);self.assertNotIn('guardian',proc.stderr)
  self.assertNotIn('require_guardian',Path(o.__file__).read_text())
 def test_seed_worker_accepts_oversize_request_through_json_validation(self):
  with tempfile.TemporaryDirectory() as d:
   request=Path(d)/'request';request.write_bytes(b'{}'+b' '*((1<<20)+1));worker=Path(o.__file__).parent/'seed-producer/seed_worker.py'
   result=subprocess.run([sys.executable,str(worker),str(request),str(Path(d)/'work'),str(Path(d)/'out')],capture_output=True,text=True)
   self.assertNotEqual(result.returncode,0);self.assertIn('controls',result.stderr);self.assertNotIn('exceeds bound',result.stderr);self.assertFalse((Path(d)/'out').exists())
 def test_json_sync_failure_is_uncertain(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'marker.json'
   with mock.patch.object(o.os,'fsync',side_effect=OSError('fault')):
    with self.assertRaisesRegex(RuntimeError,'may exist; durability uncertain'):o.write_json(path,{'x':1})
   self.assertTrue(path.exists())
 def test_partial_core_without_checkpoint_fails_closed(self):
  with tempfile.TemporaryDirectory() as d:
   work=Path(d);o.build_stage2.validate_resume_checkpoint(work,False)
   with self.assertRaisesRegex(ValueError,'no checkpoint'):o.build_stage2.validate_resume_checkpoint(work,True)
   (work/'checkpoint.npz').write_bytes(b'fixture');o.build_stage2.validate_resume_checkpoint(work,True)
 def test_unsupported_controls(self):
  with tempfile.TemporaryDirectory() as d:
   p,cp,cfg=self.fixture(d);cfg['seed_controls']['strip_rows']=65;cp.write_text(json.dumps(cfg))
   with self.assertRaisesRegex(ValueError,'seed controls'):o.load_config(cp)
if __name__=='__main__':unittest.main()
