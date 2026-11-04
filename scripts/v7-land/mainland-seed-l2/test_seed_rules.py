import unittest
from seed_rules import compile_rules
class Rules(unittest.TestCase):
 def setUp(self):
  self.s={'source':'neon-export','schema':'worldatlas-geography-decision-draft-evidence-v1','decision_revision':{'id':'r','status':'draft','entity_revision':'e'},'entity_revision':{'id':'e','status':'draft'},'land_baseline_policy':{'decision_revision':'r','execution_status':'selected_for_research','island_overrides':'none','mainland_rule_ids':['a','b','c','d'],'region_ids':['eur','amer']},'entities':[{'id':i,'level':'continent'} for i in range(1,7)],'category_bindings':[{'entity_id':i,'code':i+16,'physical_class':'land'} for i in range(1,7)],'mainland_component_rules':[]}
  groups=[]
  for rid,gid,root,reg,inside,outside in [('a','g1',10,'eur',1,2),('b','g2',20,'amer',3,4),('c','g3',30,None,5,5),('d','g4',40,None,6,6)]:
   self.s['mainland_component_rules'].append({'rule_id':rid,'decision_revision':'r','execution_status':'selected_for_research','group_id':gid,'region_id':reg,'inside_entity_id':inside,'outside_entity_id':outside});groups.append({'group_id':gid,'role':'mainland','component_id_current_generation_only':root,'target_entity_ids':sorted({inside,outside})})
  self.r={'schema':'mainland-witness-resolution-v1','status':'selected-research-identity-claims-not-mainland-proof','snapshot_sha256':'a'*64,'decision_revision':'r','entity_revision':'e','groups':groups}
 def runv(self):return compile_rules(self.s,self.r,'a'*64,['eur','amer'])
 def test_selected_rules_use_current_roots(self):
  x=self.runv();self.assertEqual([v['component_id_current_generation_only'] for v in x],[10,20,30,40]);self.assertEqual((x[0]['inside_code'],x[0]['outside_code']),(17,18))
 def test_old_override_forbidden(self):
  self.s['land_baseline_policy']['island_overrides']='enabled'
  with self.assertRaisesRegex(ValueError,'simple baseline'):self.runv()
 def test_stale_snapshot_rejected(self):
  self.r['snapshot_sha256']='b'*64
  with self.assertRaisesRegex(ValueError,'resolution mismatch'):self.runv()
 def test_wrong_entity_level_rejected(self):
  self.s['entities'][0]['level']='island'
  with self.assertRaisesRegex(ValueError,'continent category'):self.runv()
 def test_sentinel_root_rejected(self):
  self.r['groups'][0]['component_id_current_generation_only']=0xffffffff
  with self.assertRaisesRegex(ValueError,'mainland group/root'):self.runv()
 def test_unconsumed_mainland_group_rejected(self):
  self.r['groups'].append({'group_id':'extra','role':'mainland','component_id_current_generation_only':99,'target_entity_ids':[1]})
  with self.assertRaisesRegex(ValueError,'unconsumed selected mainland'):self.runv()
 def test_incomplete_category_coverage_rejected(self):
  self.s['mainland_component_rules'][3]['inside_entity_id']=5;self.s['mainland_component_rules'][3]['outside_entity_id']=5;self.r['groups'][3]['target_entity_ids']=[5]
  with self.assertRaisesRegex(ValueError,'category coverage'):self.runv()
 def test_duplicate_root_rejected(self):
  self.r['groups'][1]['component_id_current_generation_only']=10
  with self.assertRaisesRegex(ValueError,'duplicate mainland'):self.runv()
 def test_conflicting_target_rejected(self):
  self.s['mainland_component_rules'][0]['inside_entity_id']=3
  with self.assertRaisesRegex(ValueError,'target mismatch'):self.runv()
 def test_unselected_region_rejected(self):
  self.s['mainland_component_rules'][0]['region_id']='other'
  with self.assertRaisesRegex(ValueError,'unselected or unnecessary region'):self.runv()
if __name__=='__main__':unittest.main()
