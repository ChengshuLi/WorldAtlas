"""Synthetic in-memory planner fixtures only."""
import copy, unittest
import test_direct_core as fixtures
from partial_plan import plan

class PartialPlanTest(unittest.TestCase):
 def fixture(self):
  snapshot,witness,pins,grid=fixtures.DirectCoreTest().fixture()
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
