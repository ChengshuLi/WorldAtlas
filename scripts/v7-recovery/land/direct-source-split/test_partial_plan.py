"""Synthetic in-memory planner fixtures only."""
import copy, hashlib, json, unittest
from partial_plan import plan

class PartialPlanTest(unittest.TestCase):
 def fixture(self):
  line={'type':'LineString','coordinates':[[0.0,-2.0],[0.0,2.0]]}
  h=hashlib.sha256(json.dumps(line,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
  snapshot={'source':'neon-export','decision_revision':{'id':'d','status':'draft','entity_revision':'e'},'entity_revision':{'id':'e','status':'draft'},
   'mainland_component_rules':[{'rule_id':'r','region_id':'z','group_id':'g','inside_entity_id':1,'outside_entity_id':2,'execution_status':'selected_for_research','decision_revision':'d'}],
   'seed_regions':[{'region_id':'z','execution_status':'selected_for_research','decision_revision':'d','segments':[{'kind':'boundary','id':'b','start':0,'end':2,'reverse':False}],'witnesses':[{'lon':-1,'lat':0,'inside':True},{'lon':1,'lat':0,'inside':False}]}],
   'mainland_boundaries':[{'boundary_id':'b','execution_status':'selected_for_research','decision_revision':'d','method':'stored_linestring_v1','coordinate_reference':'OGC:CRS84','geometry_hash_method':'binary64-sorted-compact-geojson-v1','geometry_sha256':h,'geometry':line}],
   'category_bindings':[{'entity_id':1,'physical_class':'land','code':31},{'entity_id':2,'physical_class':'land','code':32}]}
  grid={'width':4,'height':4,'west':-2,'north':2,'step':1};pins={'component_rows':'a'*64,'component_runs':'b'*64}
  witness={'schema':'mainland-witness-resolution-v1','status':'selected-research-identity-claims-not-mainland-proof','snapshot_sha256':'c'*64,'decision_revision':'d','entity_revision':'e','grid':grid,'input_sha256':pins,'groups':[{'group_id':'g','role':'mainland','component_id_current_generation_only':7,'target_entity_ids':[1,2]}]}
  source={'source_id':'source','version':'test','sha256':'a'*64,'r2_bucket':'test-bucket','r2_key':'synthetic','size_bytes':1}
  snapshot.update({'schema':'worldatlas-geography-decision-draft-evidence-v1','serialization':'worldatlas-canonical-json-v1','sources':[source],
    'source_lineage_assets':[{**source,'kind':'raw','provider':'test','source_uri':'synthetic:test','provenance':{'representation':'provider_original','origin':'synthetic'}}],
    'source_lineage_dependencies':[]})
  snapshot['mainland_boundaries'][0]['provenance']={'source_refs':[{'source_id':'source','version':'test'}],'lineage_status':'incomplete'}
  pins['component_rows']='a'*64
  snapshot['land_baseline_policy']={'region_ids':['z','other'],'boundary_ids':['b','q'],'route_ids':['target-closure'],'mainland_rule_ids':['r','r2']}
  snapshot['seed_regions'][0]['segments'].append({'kind':'route','id':'target-closure','start':0,'end':2,'reverse':False})
  snapshot['seed_regions'].append({'region_id':'other','segments':[{'kind':'boundary','id':'q','start':0,'end':2,'reverse':False}]})
  snapshot['mainland_boundaries'].append({'boundary_id':'q'})
  rules=[{'rule_id':'r','region_id':'z','component_id_current_generation_only':7,'inside_code':31,'outside_code':32}, {'rule_id':'r2','region_id':'other','component_id_current_generation_only':8,'inside_code':33,'outside_code':34}]
  return snapshot,witness,pins,grid,rules
 def execute(self,s,w,p,g,rules):
  def compile_rules(snapshot,witness,sha,ids):self.assertEqual(ids,['z','other']);return rules
  def boundary_records(view):
   self.assertEqual(view['land_baseline_policy']['region_ids'],['other']);self.assertEqual(view['land_baseline_policy']['boundary_ids'],['q']);self.assertEqual(view['land_baseline_policy']['route_ids'],[]);return 'd','e',{'q':'record'},{}
  def selected_regions(view,*_):return [{'region_id':x['region_id']} for x in view['seed_regions']],{'q':'record'}
  return plan(s,w,'c'*64,p,g,'r','b',compile_rules,boundary_records,selected_regions)
 def test_plan_omits_only_target_and_keeps_original_unchanged(self):
  s,w,p,g,rules=self.fixture();original=copy.deepcopy(s);result=self.execute(s,w,p,g,rules)
  self.assertEqual(result['status'],'research-plan-not-a-build');self.assertEqual([x['rule_id'] for x in result['remaining_rules']],['r2']);self.assertEqual(s,original)
 def test_rejects_shared_region_or_wrong_component(self):
  s,w,p,g,rules=self.fixture();rules[1]['region_id']='z'
  with self.assertRaisesRegex(ValueError,'shared or missing'):self.execute(s,w,p,g,rules)
  s,w,p,g,rules=self.fixture();rules[0]['component_id_current_generation_only']=9
  with self.assertRaisesRegex(ValueError,'differs from selected'):self.execute(s,w,p,g,rules)
 def test_rejects_unselected_retained_geometry(self):
  s,w,p,g,rules=self.fixture();s['land_baseline_policy']['boundary_ids'].remove('q')
  with self.assertRaisesRegex(ValueError,'not selected'):self.execute(s,w,p,g,rules)
if __name__=='__main__':unittest.main()
