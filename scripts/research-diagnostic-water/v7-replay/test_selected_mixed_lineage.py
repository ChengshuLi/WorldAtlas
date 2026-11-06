import json,tempfile,unittest
from pathlib import Path
import selected_mixed_lineage as m

class Fixture:
 def __init__(self,root):
  self.root=Path(root);self.out=self.root/'out';self.out.mkdir();self.rev={'id':'v2-land-mainland-boundary-draft-1','status':'draft','entity_revision':'entity'};self.grid={'width':4,'height':2}
  def file(name,content):
   p=self.root/name;p.write_bytes(content);return {'path':str(p),'sha256':m.sha(p)}
  def obj(name,x):return file(name,json.dumps(x,sort_keys=True).encode())
  self.obj=obj;self.file=file
  br=file('baseline.rows',b'base rows');bu=file('baseline.runs',b'base runs');pr=file('physical.rows',b'physical rows');pu=file('physical.runs',b'physical runs');cr=file('component.rows',b'component rows');cu=file('component.runs',b'component runs')
  self.phys={'rows_sha256':pr['sha256'],'runs_sha256':pu['sha256']};metric={'algorithm':'wgs84_ellipsoidal_geodesic_inverse','semi_major_axis_m':'6378137','inverse_flattening':'298.257223563','execution_status':'selected_for_research','decision_revision':self.rev['id'],'policy_id':'wgs84','version':'1'};bs=obj('base.json',{'decision_revision':self.rev,'distance_policies':[metric],'land_baseline_policy':{'distance_policy_id':'wgs84','distance_policy_version':'1','endpoints':'physical_land_cell_centers','execution_status':'selected_for_research'}});self.bs=bs
  physr=obj('physical.json',{'status':'candidate-only','grid':self.grid,'output_sha256':{'rows.u32le':pr['sha256'],'runs.u32le':pu['sha256']}})
  baseline=obj('stage2.json',{'schema':'stage2-source-geodesic-report-v1','status':'stage2-research-complete','publishable':False,'distance_policy':metric,'decision_snapshot_sha256':bs['sha256'],'decision_revision':'v2-land-mainland-boundary-draft-1','entity_revision':'entity','output_rows_sha256':br['sha256'],'output_runs_sha256':bu['sha256'],'inputs_sha256':{'physical_rows':pr['sha256'],'physical_runs':pu['sha256'],'physical_report':physr['sha256'],'component_rows':cr['sha256'],'component_runs':cu['sha256']},'grid':self.grid})
  s={'snapshot':bs,'report':baseline,'rows':br,'runs':bu,'physical_rows':pr,'physical_runs':pu,'physical_report':physr}
  pins={'baseline_report_sha256':baseline['sha256'],'baseline_rows_sha256':br['sha256'],'baseline_runs_sha256':bu['sha256'],'baseline_decision_snapshot_sha256':bs['sha256'],'physical_rows_sha256':pr['sha256'],'physical_runs_sha256':pu['sha256'],'component_rows_sha256':cr['sha256'],'component_runs_sha256':cu['sha256']}
  pol={'baseline_revision':'v2-land-mainland-boundary-draft-1','execution_status':'selected_for_research',**pins};snap=obj('region.json',{'decision_revision':{'id':'v7-list1-wgs84-draft-170','status':'draft','entity_revision':'entity'},'entity_revision':{'id':'entity','status':'draft'},'list1_policy':pol});req=obj('point.json',{'snapshot':snap,'physical_rows':pr,'physical_runs':pu,'component_rows':cr,'component_runs':cu,'grid':self.grid})
  approval=obj('approval.json',{'validator_sha256':'b'*64});self.cfg={'stage2_approval':approval,'schema':'stage3-selected-mixed-request-v1','output':str(self.out),'stage2':s,'point_request':req,'policy_pins':pins,'regional':{'request':{'profiling_standin':False,'pending_inventory_complete':True}},'code':{'driver':'a'*64,'validator':'b'*64}}
  self.snap=snap;self.cfgspec=obj('request.json',self.cfg);self.loc=obj('out/water-lineage.json',{'schema':'water-selected-mixed-lineage-v1','request':self.cfgspec,'snapshot_origin':{'kind':'direct','source_snapshot':snap}})
  rows=file('out/rows.u32le',b'land rows');runs=file('out/runs.u32le',b'land runs');self.land={'resolved_rows':Path(rows['path']),'resolved_runs':Path(runs['path']),'rows_sha256':rows['sha256'],'runs_sha256':runs['sha256']}
  self.report={'schema':'stage3-selected-mixed-land-report-v1','status':'research-awaiting-review','publishable':False,'request_sha256':self.cfgspec['sha256'],'decision_snapshot_sha256':snap['sha256'],'regional_island_rule':{'status':'research-awaiting-review','provenance':{'profiling_standin':False,'pending_inventory_complete':True,'decision_snapshot_sha256':snap['sha256']}},'baseline_validation':{'schema':'stage2-candidate-validation-v1','status':'diagnostic-candidate-bound','report_sha256':baseline['sha256'],'decision_revision':'v2-land-mainland-boundary-draft-1','entity_revision':'entity','output_rows_sha256':br['sha256'],'output_runs_sha256':bu['sha256'],'physical_rows_sha256':pr['sha256'],'physical_runs_sha256':pu['sha256'],'grid':self.grid},'point_resolution':{'schema':'source-point-component-report-v1','status':'research-only-not-a-build','snapshot_sha256':snap['sha256'],'revision':'v7-list1-wgs84-draft-170','entity_revision':'entity','input_sha256':{'physical_rows':pr['sha256'],'physical_runs':pu['sha256'],'component_rows':cr['sha256'],'component_runs':cu['sha256']}},'policy':{'revision':'v7-list1-wgs84-draft-170','entity_revision':'entity','baseline_revision':'v2-land-mainland-boundary-draft-1','policy':pol},'code_sha256':self.cfg['code'],'writer':{'schema':'stage3-land-writer-result-v1','status':'pending-caller-validation','grid':self.grid,'output_rows_sha256':rows['sha256'],'output_runs_sha256':runs['sha256']}}
  self.rp=self.out/'report.json';self.physr=physr
 def check(self):return m.validate(self.report,self.rp,self.phys,self.land,self.bs['sha256'],self.rev,self.root,self.physr['sha256'])
 def config_update(self):
  self.cfgspec=self.obj('request.json',self.cfg);self.obj('out/water-lineage.json',{'schema':'water-selected-mixed-lineage-v1','request':self.cfgspec,'snapshot_origin':{'kind':'direct','source_snapshot':self.snap}});self.report['request_sha256']=self.cfgspec['sha256']
 def diagnostic(self):
  launcher=self.file('seed_worker.py',b'launcher');derived=self.obj('derived.json',{'code_sha256':{'seed-producer/seed_worker.py':launcher['sha256']}});self.cfg['stage2']['derived_manifest']=derived
  spec=self.cfg['stage2']['report'];stage2=json.loads(Path(spec['path']).read_text());stage2.update(status='stage2-provisional-only',provisional_only=True,config_sha256='d'*64,orchestration={'provisional_only':True,'derived_manifest':derived});stage2['inputs_sha256']['seed_report']='f'*64;spec=self.obj('stage2.json',stage2);self.cfg['stage2']['report']=spec
  self.cfg.update(schema='stage3-provisional-diagnostic-request-v1',diagnostic_only=True,publishable=False);self.cfg['stage2_recovery_evidence']=self.obj('repair.json',{'schema':'stage2-seed-code-handoff-repair-v1','status':'launcher-remains-bound-by-derived-manifest','corrected_core_config_sha256':'d'*64,'derived_manifest_sha256':derived['sha256'],'seed_report_sha256':'f'*64,'launcher':launcher});self.cfg['regional']['request'].update(profiling_standin=True,pending_inventory_complete=False);self.cfg['policy_pins']['baseline_report_sha256']=spec['sha256']
  sp=self.report['policy']['policy'];pins=self.cfg['policy_pins'];self.report.update(schema='stage3-provisional-diagnostic-land-report-v1',status='provisional-profiling-only-not-publishable',publishable=False,provisional_only=True)
  self.report['baseline_validation'].update(status='provisional-diagnostic-candidate-bound',report_sha256=spec['sha256'],original_report_status='stage2-provisional-only',provisional_only=True,publishable=False)
  self.report['regional_island_rule'].update(status='research-profiling-standin');self.report['regional_island_rule']['provenance']['profiling_standin']=True;self.report['regional_island_rule']['provenance']['pending_inventory_complete']=False
  self.report['policy']['diagnostic_binding']={'actual_baseline_pins':dict(pins),'original_policy_baseline_revision':sp['baseline_revision'],'original_policy_pins':{k:sp.get(k) for k in pins}}
  self.report['diagnostic_provenance']={'stage2_recovery_evidence':self.cfg['stage2_recovery_evidence'],'actual_baseline_pins':dict(pins),'list1_policy_original':sp,'stage2':self.cfg['stage2'],'stage2_report_schema':'stage2-source-geodesic-report-v1','stage2_report_status':'stage2-provisional-only','stage2_provisional_only':True,'stage2_publishable':False,'list1_snapshot':self.snap,'profiling_standin':True,'pending_inventory_complete':False,'stage2_snapshot_source':'local-derived-from-neon-export','list1_snapshot_source':'neon-export'}
  self.config_update();self.obj('out/water-lineage.json',{'schema':'water-selected-mixed-lineage-v1','request':self.cfgspec,'mode':'explicit-provisional-diagnostic','snapshot_origin':{'kind':'direct','source_snapshot':self.snap}})
class TestMixed(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.f=Fixture(self.tmp.name)
 def test_explicit_diagnostic_retains_real_statuses(self):
  self.f.diagnostic();r=self.f.check();self.assertEqual(r['status'],'diagnostic-provisional-lineage-bound');self.assertEqual(r['baseline_status'],'stage2-provisional-only');self.assertEqual(r['regional_status'],'research-profiling-standin');self.assertIs(r['publishable'],False);self.assertIs(r['pending_inventory_complete'],False)
 def test_diagnostic_opt_in_required(self):
  self.f.diagnostic();self.f.obj('out/water-lineage.json',{'schema':'water-selected-mixed-lineage-v1','request':self.f.cfgspec,'snapshot_origin':{'kind':'direct','source_snapshot':self.f.snap}})
  with self.assertRaisesRegex(ValueError,'opt-in'):self.f.check()
 def test_regional_provenance_inventory_cannot_be_erased(self):
  self.f.diagnostic();self.f.report['regional_island_rule']['provenance']['pending_inventory_complete']=True
  with self.assertRaisesRegex(ValueError,'profiling flags'):self.f.check()
 def test_diagnostic_incomplete_inventory_cannot_be_erased(self):
  self.f.diagnostic();self.f.report['diagnostic_provenance']['pending_inventory_complete']=True
  with self.assertRaisesRegex(ValueError,'provenance'):self.f.check()
 def test_derived_manifest_tamper_rejected(self):
  self.f.diagnostic();Path(self.f.cfg['stage2']['derived_manifest']['path']).write_text('{}')
  with self.assertRaisesRegex(ValueError,'hash mismatch'):self.f.check()
 def test_launcher_tamper_rejected(self):
  self.f.diagnostic();Path(json.loads(Path(self.f.cfg['stage2_recovery_evidence']['path']).read_text())['launcher']['path']).write_text('tamper')
  with self.assertRaisesRegex(ValueError,'hash mismatch'):self.f.check()
 def test_recovery_evidence_tamper_rejected(self):
  self.f.diagnostic();Path(self.f.cfg['stage2_recovery_evidence']['path']).write_text('{}')
  with self.assertRaisesRegex(ValueError,'hash mismatch'):self.f.check()
 def test_diagnostic_baseline_pin_spoof_rejected(self):
  self.f.diagnostic();self.f.report['policy']['diagnostic_binding']['actual_baseline_pins']['baseline_runs_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'provenance'):self.f.check()
 def test_status_preserved(self):
  result=self.f.check();self.assertEqual(result['producer_status'],'research-awaiting-review');self.assertEqual(result['writer_status'],'pending-caller-validation')
 def test_provisional_stage2_rejected(self):
  spec=self.f.cfg['stage2']['report']; obj=json.loads(Path(spec['path']).read_text());obj['provisional_only']=True;updated=self.f.obj('stage2.json',obj);self.f.cfg['stage2']['report']=updated;self.f.config_update()
  with self.assertRaisesRegex(ValueError,'completed Stage 2'):self.f.check()
 def test_regional_revision_mismatch(self):
  self.f.report['policy']['revision']='v2-land-mainland-boundary-draft-1'
  with self.assertRaisesRegex(ValueError,'regional policy revision'):self.f.check()
 def test_profile_cannot_masquerade_as_final(self):
  self.f.cfg['regional']['request']['profiling_standin']=True;self.f.config_update()
  with self.assertRaisesRegex(ValueError,'profiling'):self.f.check()
 def test_incomplete_inventory_rejected(self):
  self.f.cfg['regional']['request']['pending_inventory_complete']=False;self.f.config_update()
  with self.assertRaisesRegex(ValueError,'profiling'):self.f.check()
 def test_local_derived_origin(self):
  source=json.loads(Path(self.f.snap['path']).read_text());source['list1_policy']['baseline_revision']='older';source['list1_policy']['baseline_rows_sha256']='0'*64;sp=self.f.obj('neon-source.json',source)
  self.f.obj('out/water-lineage.json',{'schema':'water-selected-mixed-lineage-v1','request':self.f.cfgspec,'snapshot_origin':{'kind':'local-derived-baseline-pin-refresh-v1','source_snapshot':sp}})
  self.assertEqual(self.f.check()['regional_snapshot_origin'],'local-derived-baseline-pin-refresh-v1')
  source['extra_unrelated_change']=True;sp=self.f.obj('neon-source.json',source);self.f.obj('out/water-lineage.json',{'schema':'water-selected-mixed-lineage-v1','request':self.f.cfgspec,'snapshot_origin':{'kind':'local-derived-baseline-pin-refresh-v1','source_snapshot':sp}})
  with self.assertRaisesRegex(ValueError,'outside baseline'):self.f.check()
 def test_spherical_stage2_rejected(self):
  spec=self.f.cfg['stage2']['report']; obj=json.loads(Path(spec['path']).read_text());obj['distance_policy']['algorithm']='spherical';updated=self.f.obj('stage2.json',obj);self.f.cfg['stage2']['report']=updated;self.f.config_update()
  with self.assertRaisesRegex(ValueError,'WGS84'):self.f.check()
 def test_base_snapshot_tamper(self):
  Path(self.f.bs['path']).write_text('{}')
  with self.assertRaisesRegex(ValueError,'hash mismatch'):self.f.check()
 def test_regional_snapshot_hash_mismatch(self):
  self.f.report['decision_snapshot_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'regional snapshot'):self.f.check()
 def test_output_tamper(self):
  self.f.land['resolved_rows'].write_bytes(b'wrong')
  with self.assertRaisesRegex(ValueError,'land output hash'):self.f.check()
 def test_component_generation_mismatch(self):
  spec=self.f.cfg['stage2']['report'];obj=json.loads(Path(spec['path']).read_text());obj['inputs_sha256']['component_rows']='0'*64;updated=self.f.obj('stage2.json',obj);self.f.cfg['stage2']['report']=updated;self.f.config_update();self.f.report['baseline_validation']['report_sha256']=updated['sha256']
  with self.assertRaisesRegex(ValueError,'component generation'):self.f.check()
 def test_physical_report_mismatch(self):
  with self.assertRaisesRegex(ValueError,'physical report'):m.validate(self.f.report,self.f.rp,self.f.phys,self.f.land,self.f.bs['sha256'],self.f.rev,self.f.root,'0'*64)
 def test_forged_baseline_status(self):
  self.f.report['baseline_validation']['status']='selected'
  with self.assertRaisesRegex(ValueError,'baseline validation'):self.f.check()
 def test_code_pin_mismatch(self):
  self.f.report['code_sha256']['driver']='b'*64
  with self.assertRaisesRegex(ValueError,'code pin'):self.f.check()
 def test_producer_status_rejected(self):
  self.f.report['status']='complete'
  with self.assertRaisesRegex(ValueError,'completed research'):self.f.check()
 def test_stage2_report_mutation(self):
  Path(self.f.cfg['stage2']['report']['path']).write_text('{}')
  with self.assertRaisesRegex(ValueError,'hash mismatch'):self.f.check()
 def test_wrong_revision(self):
  self.f.rev['id']='wrong'
  with self.assertRaisesRegex(ValueError,'revision'):self.f.check()
if __name__=='__main__':unittest.main()
