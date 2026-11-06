import copy,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import bering_bridge,mixed_claims
class Tests(unittest.TestCase):
 def setUp(self):
  self.base={'decision_revision':{'id':'r'},'entity_revision':{'id':'e'},'mainland_witness_groups':[{'group_id':'g','decision_revision':'r','execution_status':'selected_for_research','role':'sentinel','target_entity_ids':[],'witness_ids':['w']}],'mainland_witnesses':[{'witness_id':'w','decision_revision':'r','execution_status':'selected_for_research','point_feature_id':'p','identity_feature_id':'i'}]};self.req={'baseline_snapshot_sha256':'a','component_manifest_sha256':'b','input_sha256':{'x':'c'},'grid':{'width':8}};self.res={'schema':'mainland-witness-resolution-v1','status':'selected-research-identity-claims-not-mainland-proof','snapshot_sha256':'a','decision_revision':'r','entity_revision':'e','component_manifest_sha256':'b','input_sha256':{'x':'c'},'grid':{'width':8},'groups':[{'group_id':'g','role':'sentinel','target_entity_ids':[],'component_id_current_generation_only':77}],'witnesses':[{'witness_id':'w','group_id':'g','point_feature_id':'p','identity_feature_id':'i'}]};self.stage={'resolution_report_sha256':'d','physical_coverage':{'seed_roots':[99]}}
 def test_protected_and_tamper(self):
  self.assertEqual(bering_bridge.protected_roots(self.base,self.stage,self.req,self.res,'d'),{77,99})
  cases=[lambda:self.res['groups'][0].update(component_id_current_generation_only=0xffffffff),lambda:self.res['groups'][0].update(role='mainland'),lambda:self.res['witnesses'][0].update(identity_feature_id='wrong'),lambda:self.base['mainland_witnesses'][0].update(group_id='wrong'),lambda:self.res.update(component_manifest_sha256='wrong'),lambda:self.stage['physical_coverage'].update(seed_roots=[])]
  for mutate in cases:
   self.setUp();mutate()
   with self.assertRaises(ValueError):bering_bridge.protected_roots(self.base,self.stage,self.req,self.res,'d')
 def test_mixed_conflict_and_same_target(self):
  snap={'affiliations':[{'affiliation_id':'a','method':'label_contained_ecoregion_contact_v1','entity_id':1},{'affiliation_id':'b','method':'component_intersection_v1','entity_id':1}],'category_bindings':[{'physical_class':'land','entity_id':1,'code':20}]};compiled={'affiliation_ids':['a','b'],'revision':'r','entity_revision':'e','affiliation_entry_links':{'a':['x'],'b':['y']}};base={'status':'research-only-not-a-build','revision':'r','entity_revision':'e'};reports=[{**base,'schema':'source-label-ecoregion-component-report-v1','claims':[{'affiliation_id':'a','entity_id':1,'entity_code':20,'method':'label_contained_ecoregion_contact_v1','component_ids':[5]}]},{**base,'schema':'source-polygon-component-report-v1','claims':[{'affiliation_id':'b','entity_id':1,'entity_code':20,'method':'component_intersection_v1','component_ids':[5]}]}];out=mixed_claims.combine(compiled,snap,reports,{99});self.assertEqual(len(out[5]),2)
  with self.assertRaisesRegex(ValueError,'mainland'):mixed_claims.combine(compiled,snap,reports,{5})
  snap['affiliations'][1]['entity_id']=2;snap['category_bindings'].append({'physical_class':'land','entity_id':2,'code':19});reports[1]['claims'][0].update(entity_id=2,entity_code=19)
  with self.assertRaisesRegex(ValueError,'conflicting'):mixed_claims.combine(compiled,snap,reports,{99})
if __name__=='__main__':unittest.main()

class RealBeringHandoffTests(unittest.TestCase):
 def test_adapter_bridge_and_real_resolver(self):
  import importlib.util,sys,json,hashlib,struct
  from pathlib import Path
  root=Path(__file__).resolve().parent.parent;d=root/'bering-two-source-adapter-20261104';sys.path.insert(0,str(d))
  def load(n,p):
   spec=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
  fixturemod=load('bering_test_fixture',d/'test_resolver.py');fixture=fixturemod.Tests('runTest');fixture.setUp();self.addCleanup(fixture.doCleanups)
  adaptermod=load('bering_adapter_fixture',d/'test_adapter_v3.py');af=adaptermod.Tests('runTest');af.setUp();snap=af.s
  label=fixture.inputs['label'];epa=fixture.inputs['ecoregion'];
  for s in snap['sources']:
   data=label if s['source_id']=='label' else epa;s.update(sha256=data['sha256'],size_bytes=data['size_bytes'])
  for a in snap['source_lineage_assets']:
   data=label if a['source_id']=='label' else epa;a.update(sha256=data['sha256'],size_bytes=data['size_bytes'])
  f=snap['features'][0];f['source_feature_id']='42';f['geometry_sha256']=hashlib.sha256(json.dumps(fixture.geom,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest();ref=snap['ecoregion_source_refs'][0];ref['contract'].update(layer='epa',selector_property='CODE',name_property='NAME',expected_feature_count=1)
  policy=__import__('bering_adapter').adapt(snap,af.p,{'a'});files=[{'source_id':k,'version':'v',**(label if k=='label' else epa)} for k in ('label','epa')]
  def binary(name,fmt,rows):
   p=fixture.r/name;p.write_bytes(b''.join(struct.pack(fmt,*v) for v in rows));fixture.inputs[name]=fixturemod.pin(p)
  binary('physical_rows','<I',[(0,),(2,),(3,),(4,),(5,)]);binary('physical_runs','<II',[(2,17),(8,1),(8,1),(8,1),(8,1)]);binary('component_rows','<I',[(0,),(2,),(2,),(2,),(2,)]);binary('component_runs','<III',[(0,1,1),(1,2,2)])
  source=load('real_source',root/'stage3-mixed-leeward-full-20261105/polygon_source.py');import bering_profiler,bering_intersection
  inputs={k:{'path':v['path'],'sha256':v['sha256']} for k,v in fixture.inputs.items() if k not in ('label','ecoregion')};res=bering_bridge.resolve(policy,snap,files,inputs,fixture.grid,{2},bering_profiler.profile,source.extract,bering_intersection)
  self.assertEqual(res['claims'][0]['component_ids'],[1]);self.assertIn(2,res['details'][0]['resolution']['protected_roots_excluded']);self.assertEqual(res['details'][0]['resolution']['root_counts'][0]['inside'],1)

class SourcePathTests(unittest.TestCase):
 def test_shared_identity_and_collisions(self):
  import apply_selected_mixed as driver
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'source';p.write_bytes(b'x');v={'source_id':'ne','version':'v','path':str(p),'sha256':'a'*64,'size_bytes':1}
   driver.verify_bering_source_paths([v],[dict(v)],[])
   bad=dict(v,source_id='other')
   with self.assertRaisesRegex(ValueError,'identity conflict'):driver.verify_bering_source_paths([v],[bad],[])
   with self.assertRaisesRegex(ValueError,'duplicate Bering'):driver.verify_bering_source_paths([v,v],[],[])
   with self.assertRaisesRegex(ValueError,'corroboration sources overlap'):driver.verify_bering_source_paths([v],[],[v])
