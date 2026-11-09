"""Synthetic outer-driver wiring. Source bridge/adapter are mocked here."""
import hashlib,json,unittest
from pathlib import Path
from unittest.mock import patch
from test_mixed_driver import js
from test_corroboration_outer import CorroborationOuter
import apply_selected_mixed as driver
class BeringOuterTests(CorroborationOuter):
 def setup_bering(self,target=3,root=11,protected_requirement=False):
  reqpath=Path(self.cfg['point_request']['path']);req=json.loads(reqpath.read_text());sp=Path(req['snapshot']['path']);snap=json.loads(sp.read_text());snap['schema']='worldatlas-geography-decision-draft-evidence-v3';snap['unsupported_affiliation_source_ref_table_present']=False;snap['unsupported_point_methods_present']=False;snap['affiliation_source_refs']=[];snap.setdefault('polygon_corroboration_refs',[]);snap['ecoregion_source_refs']=[];snap['affiliations'].append({'affiliation_id':'bering','decision_revision':'r','scope':'land','relationship':'affiliation','method':'label_contained_ecoregion_contact_v1','entity_id':target,'evidence':{'execution_status':'selected_for_research'}});snap['list1_entries'].append({'entry_id':'eb','title':'Bering','reason':'test','old_list1_refs':[],'execution_status':'selected_for_research','decision_revision':'r','affiliation_ids':['bering']});snap['list1_policy']['entry_ids'].append('eb');snap['list1_policy']['affiliation_ids'].append('bering')
  if protected_requirement:snap['affiliations'][1]['evidence']['protected_witness_group_ids']=['sentinel']
  stage=self.cfg['stage2'];rpath=Path(stage['report']['path']);report=json.loads(rpath.read_text());witness=js(self.src/'protected.json',{});derived=js(self.src/'derived.json',{'artifacts':{'resolution_report':witness}});stage['derived_manifest']=derived;report['resolution_report_sha256']=witness['sha256'];stage['report']=js(rpath,report);self.cfg['policy_pins']['baseline_report_sha256']=stage['report']['sha256'];snap['list1_policy']['baseline_report_sha256']=stage['report']['sha256'];req['snapshot']=js(sp,snap);self.point['snapshot_sha256']=req['snapshot']['sha256'];self.cfg['point_request']=js(reqpath,req);self.cfg['bering_source_files']=[]
  import pyproj
  db=(Path(pyproj.datadir.get_data_dir())/'proj.db').resolve();self.cfg['bering_proj_db']={'path':str(db),'sha256':hashlib.sha256(db.read_bytes()).hexdigest()};code=17+target
  v={'root':root,'cells':3,'label_inside':3,'inside':2,'outside':1,'boundary':0,'untested':0};self.bering={'schema':'source-label-ecoregion-component-report-v1','status':'research-only-not-a-build','revision':'r','entity_revision':'e','claims':[{'affiliation_id':'bering','entity_id':target,'entity_code':code,'method':'label_contained_ecoregion_contact_v1','component_ids':[root]}],'details':[{'affiliation_id':'bering','resolution':{'root_counts':[v]}}]}
 def run_bering(self):
  with patch.dict('os.environ',{'PROJ_NETWORK':'OFF'}),patch.object(driver.bering_adapter,'adapt',return_value={'decisions':[]}),patch.object(driver.bering_bridge,'protected_roots',return_value={99}),patch.object(driver.bering_bridge,'resolve',return_value=self.bering):return self.runv()
 def test_v3_same_target_trace(self):
  self.setup_bering();self.run_bering();r=json.loads((self.b/'out/report.json').read_text());self.assertEqual(r['bering_component_extents']['bering']['11']['ecoregion_outside_cells'],1);self.assertEqual(r['writer']['affiliation_statistics']['bering']['applied_cells'],3)
 def test_v3_bering_and_sulcis_corroboration_coexist(self):
  self.setup_corroboration();self.setup_bering();self.run_bering();r=json.loads((self.b/'out/report.json').read_text());self.assertEqual(r['administrative_corroboration']['affiliations'][0]['rows'][0]['covered_centers'],3);self.assertEqual(r['bering_component_extents']['bering']['11']['ecoregion_outside_cells'],1)
 def test_v3_real_adapter_and_sulcis_outer(self):
  import importlib.util,sys
  sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'bering-two-source-adapter-20261104'))
  self.setup_corroboration();self.setup_bering();path=Path(__file__).resolve().parent.parent/'bering-two-source-adapter-20261104/test_adapter_v3.py';spec=importlib.util.spec_from_file_location('v3_adapter_fixture',path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);fixture=mod.Tests('runTest');fixture.setUp();src=fixture.s
  reqpath=Path(self.cfg['point_request']['path']);req=json.loads(reqpath.read_text());sp=Path(req['snapshot']['path']);snap=json.loads(sp.read_text());snap['sources'].extend(src['sources']);snap['source_lineage_assets'].extend(src['source_lineage_assets']);snap['features'].extend(src['features']);snap['affiliations'][-1]['feature_id']='label-feature';snap['affiliations'][-1]['evidence']['selector']=src['affiliations'][0]['evidence']['selector'];ref=dict(src['ecoregion_source_refs'][0]);ref['affiliation_id']='bering';snap['ecoregion_source_refs']=[ref];req['snapshot']=js(sp,snap);self.point['snapshot_sha256']=req['snapshot']['sha256'];self.cfg['point_request']=js(reqpath,req)
  with patch.dict('os.environ',{'PROJ_NETWORK':'OFF'}),patch.object(driver.bering_bridge,'protected_roots',return_value={99}),patch.object(driver.bering_bridge,'resolve',return_value=self.bering):self.runv()
  r=json.loads((self.b/'out/report.json').read_text());self.assertEqual(r['administrative_corroboration']['affiliations'][0]['rows'][0]['covered_centers'],3);self.assertEqual(r['bering_resolution']['claims'][0]['component_ids'],[11])
 def test_v3_rejects_bad_label_coverage_and_online_proj(self):
  self.setup_bering();self.bering['details'][0]['resolution']['root_counts'][0]['label_inside']=2
  with self.assertRaisesRegex(ValueError,'Bering extent'):self.run_bering()
  self.setUp();self.setup_bering()
  with patch.dict('os.environ',{'PROJ_NETWORK':'ON'}),patch.object(driver.bering_adapter,'adapt',return_value={'decisions':[]}),patch.object(driver.bering_bridge,'protected_roots',return_value={99}),patch.object(driver.bering_bridge,'resolve',return_value=self.bering):
   with self.assertRaisesRegex(ValueError,'PROJ network must be disabled'):self.runv()
 def test_v3_different_target_and_mainland_fail(self):
  self.setup_bering(target=2)
  with self.assertRaisesRegex(ValueError,'conflicting'):self.run_bering()
  self.setUp();self.setup_bering(root=99)
  with self.assertRaisesRegex(ValueError,'mainland'):self.run_bering()
 def test_existing_protected_verification_not_skipped(self):
  self.setup_bering(protected_requirement=True)
  with patch.object(driver.mixed_claims,'verify_protected',return_value=[{'status':'checked'}]) as check:self.run_bering();check.assert_called_once()
  r=json.loads((self.b/'out/report.json').read_text());self.assertEqual(r['protected_witness_checks'],[{'status':'checked'}])
if __name__=='__main__':unittest.main()
