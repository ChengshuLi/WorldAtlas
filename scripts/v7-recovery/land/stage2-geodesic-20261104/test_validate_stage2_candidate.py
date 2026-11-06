import copy,hashlib,json,tempfile,unittest
from unittest import mock
from pathlib import Path
import validate_stage2_candidate as v
import build_stage2,orchestrate_stage2
class CandidateTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.d=Path(self.t.name);self.pins={}
  for k in ('rows','runs','physical_rows','physical_runs','physical_lineage_request'):(self.d/k).write_bytes(k.encode());self.pin(k)
  grid={'width':8,'height':4,'west':-180,'north':90,'step':45};metric={'policy_id':'wgs','version':'1','decision_revision':'d','execution_status':'selected_for_research','algorithm':'wgs84_ellipsoidal_geodesic_inverse','units':'metres','semi_major_axis_m':'6378137','inverse_flattening':'298.257223563'};policy={'policy_id':'p','version':'1','decision_revision':'d','execution_status':'selected_for_research','distance_policy_id':'wgs','distance_policy_version':'1','tie_tolerance_metres':'0.00001','island_overrides':'none','connectivity':'four_neighbor_longitude_wrapped','aggregation':'minimum_over_component_and_mainland_cells','endpoints':'physical_land_cell_centers','tie':'lowest_category_code','grid':grid,'physical_rows_sha256':self.pins['physical_rows']['sha256'],'physical_runs_sha256':self.pins['physical_runs']['sha256'],'physical_report_sha256':'PLACEHOLDER'};self.code={k:format(i+1,'064x') for i,k in enumerate(('orchestrator','core','watchdog','guardian'))}
  snapshot={'schema':'worldatlas-geography-decision-draft-evidence-v1','source':'neon-export','decision_revision':{'id':'d','entity_revision':'e','status':'draft'},'entity_revision':{'id':'e','status':'draft'},'entities':[{'id':i,'name':'c'+str(i),'level':'continent'} for i in range(6)],'category_bindings':[{'entity_id':i,'code':i+17,'physical_class':'land'} for i in range(6)],'distance_policies':[metric],'land_baseline_policy':policy};self.write('snapshot',snapshot)
  self.write('physical_report',{'status':'candidate-only','grid':grid,'output_sha256':{'rows.u32le':self.pins['physical_rows']['sha256'],'runs.u32le':self.pins['physical_runs']['sha256']}})
  policy['physical_report_sha256']=self.pins['physical_report']['sha256'];snapshot['land_baseline_policy']=policy;self.write('snapshot',snapshot)
  self.code.update({'core_files':{k:('0'*64 if k!='build_stage2.py' else self.code['core']) for k in build_stage2.CODE_NAMES},'dependency_files':{'seed_code_files':{k:'1'*64 for k in set(orchestrate_stage2.SEED_NAMES)|{'rasterizer','rasterizer_kernel'}},'resolution_code_files':{k:'2'*64 for k in ('resolver','helper','named_identity','identity_watch')},'hint_code_files':{k:'3'*64 for k in ('hints.py','run_diagnostic.py')}},'orchestration_files':{k:('4'*64 if k!='orchestrate_stage2.py' else self.code['orchestrator']) for k in {'orchestrate_stage2.py','representatives.py','build_seed_tiles.py','seed-producer/seed_worker.py'}|{'seed-producer/'+x for x in orchestrate_stage2.SEED_NAMES}|{'hint-producer/'+x for x in orchestrate_stage2.HINT_NAMES}|set(build_stage2.CODE_NAMES)}})
  self.code['orchestration_files'].update(self.code['core_files'])
  self.code['orchestration_files'].update({'seed-producer/'+k:v for k,v in self.code['dependency_files']['seed_code_files'].items() if k in orchestrate_stage2.SEED_NAMES})
  self.code['orchestration_files'].update({'hint-producer/'+k:v for k,v in self.code['dependency_files']['hint_code_files'].items()})
  resolver={'resolver':'v7-land/mainland-witness-prototype/resolve_mainland.py','helper':'v7-land/point-component-prototype/resolve.py','named_identity':'v7-land/named-identity-prototype/named_identity.py','identity_watch':'v7-land/named-identity-prototype/identity_watch.py'}
  for k,path in resolver.items():self.code['core_files'][path]=self.code['dependency_files']['resolution_code_files'][k];self.code['orchestration_files'][path]=self.code['dependency_files']['resolution_code_files'][k]
  self.write('outer_config',{'schema':'stage2-fresh-orchestration-v1','controls':{'minimum_free_bytes':1}})
  self.artifacts={k:{'path':'/unused/'+k,'sha256':format(i+20,'064x')} for i,k in enumerate(('resolution_report','seed_rows','seed_runs','seed_report','hint_roots','hint_codes','hint_report','hint_monitor','tile_manifest','representatives'))}
  self.lineage={'schema':'stage1-lineage-and-selection-validation-v1','status':'selected-sources-match-reported-lineage'};self.write('physical_lineage_report',self.lineage)
  patcher=mock.patch.object(v.verify_physical_lineage,'validate_combined',return_value=self.lineage);patcher.start();self.addCleanup(patcher.stop)
  self.write('derived_manifest',{'physical_lineage_report':self.pins['physical_lineage_report'],'schema':'stage2-fresh-derived-v1','outer_config_sha256':self.pins['outer_config']['sha256'],'orchestrator_sha256':self.code['orchestrator'],'code_sha256':self.code['orchestration_files'],'artifacts':self.artifacts})
  self.report={'schema':'stage2-source-geodesic-report-v1','status':'stage2-research-awaiting-monitor','publishable':False,'monitor_required':True,'output_rows_sha256':self.pins['rows']['sha256'],'output_runs_sha256':self.pins['runs']['sha256'],'physical_lineage_report_sha256':self.pins['physical_lineage_report']['sha256'],'physical_lineage_status':'selected-sources-match-reported-lineage','decision_snapshot_sha256':self.pins['snapshot']['sha256'],'inputs_sha256':{**{k:self.pins[k]['sha256'] for k in ('physical_rows','physical_runs','physical_report','physical_lineage_request')},**{k:x['sha256'] for k,x in self.artifacts.items()}},**{k+'_sha256':self.artifacts[k]['sha256'] for k in ('resolution_report','seed_report','hint_report','hint_monitor')},'grid':grid,'decision_revision':'d','entity_revision':'e','distance_policy':metric,'land_baseline_policy':policy,'categories':{str(17+i):'c'+str(i) for i in range(6)},'code_sha256':self.code['core_files'],'dependency_sha256':self.code['dependency_files'],'orchestration':{'outer_config_sha256':self.pins['outer_config']['sha256'],'orchestrator_sha256':self.code['orchestrator'],'derived_manifest':self.pins['derived_manifest'],'physical_lineage_report':self.pins['physical_lineage_report']}};self.write('report',self.report)
  self.monitor={'schema':'stage2-geodesic-watchdog-v1','status':'sampled-complete','report_sha256':self.pins['report']['sha256'],'config_sha256':self.pins['outer_config']['sha256'],'driver_sha256':self.code['orchestrator'],**{k+'_sha256':self.code[k] for k in ('core','watchdog','guardian')},'samples':5,'peak_process_group_rss_kib':20,'sample_interval_seconds':.05};self.write('monitor',self.monitor)
 def pin(self,k):p=self.d/k;self.pins[k]={'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
 def write(self,k,obj):(self.d/k).write_text(json.dumps(obj));self.pin(k)
 def test_valid_and_stale_monitor(self):
  self.assertEqual(v.validate(self.pins,self.code)['status'],'diagnostic-candidate-bound');self.monitor['report_sha256']='0'*64;self.write('monitor',self.monitor)
  with self.assertRaisesRegex(ValueError,'monitor/report'):v.validate(self.pins,self.code)
 def test_refuses_changed_physical_mask(self):
  (self.d/'physical_rows').write_text('tampered')
  with self.assertRaisesRegex(ValueError,'hash mismatch'):v.validate(self.pins,self.code)
 def test_rejects_forged_selected_policy(self):
  self.report['land_baseline_policy']={**self.report['land_baseline_policy'],'execution_status':'unselected'};self.write('report',self.report)
  with self.assertRaisesRegex(ValueError,'selected policy'):v.validate(self.pins,self.code)
 def test_monitor_samples_are_required(self):
  self.monitor['samples']=0;self.write('monitor',self.monitor)
  with self.assertRaisesRegex(ValueError,'resource monitor incomplete'):v.validate(self.pins,self.code)
 def test_incomplete_or_inconsistent_code_closure_fails(self):
  bad=copy.deepcopy(self.code);bad['core_files'].pop('certificate.py')
  with self.assertRaisesRegex(ValueError,'incomplete approved code closure'):v.validate(self.pins,bad)
  bad=copy.deepcopy(self.code);bad['orchestration_files']['certificate.py']='f'*64
  with self.assertRaisesRegex(ValueError,'code closure inconsistent'):v.validate(self.pins,bad)
 def test_simple_policy_semantics_required(self):
  snapshot=json.loads((self.d/'snapshot').read_bytes());snapshot['land_baseline_policy'].pop('connectivity');self.write('snapshot',snapshot)
  self.report['decision_snapshot_sha256']=self.pins['snapshot']['sha256'];self.report['land_baseline_policy']=snapshot['land_baseline_policy'];self.write('report',self.report)
  with self.assertRaisesRegex(ValueError,'land policy mismatch: connectivity'):v.validate(self.pins,self.code)
 def test_derived_artifact_and_sample_interval_tampering(self):
  derived=json.loads((self.d/'derived_manifest').read_bytes());derived['artifacts']['seed_rows']['sha256']='f'*64;self.write('derived_manifest',derived);self.report['orchestration']['derived_manifest']=self.pins['derived_manifest'];self.write('report',self.report)
  with self.assertRaisesRegex(ValueError,'derived artifact/report mismatch'):v.validate(self.pins,self.code)
  derived['artifacts']['seed_rows']['sha256']=self.artifacts['seed_rows']['sha256'];self.write('derived_manifest',derived);self.report['orchestration']['derived_manifest']=self.pins['derived_manifest'];self.write('report',self.report);self.monitor['report_sha256']=self.pins['report']['sha256'];self.monitor['sample_interval_seconds']=.2;self.write('monitor',self.monitor)
  with self.assertRaisesRegex(ValueError,'resource monitor incomplete'):v.validate(self.pins,self.code)
if __name__=='__main__':unittest.main()
