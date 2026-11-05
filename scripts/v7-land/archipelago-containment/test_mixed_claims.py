import unittest
from mixed_claims import combine
class MixedTests(unittest.TestCase):
 def setUp(self):
  self.c={'revision':'r','entity_revision':'e','affiliation_ids':['a','b'],'affiliation_entry_links':{'a':['x'],'b':['y']}};self.s={'affiliations':[{'affiliation_id':'a','entity_id':3,'method':'source_point_named_region_component_v1'},{'affiliation_id':'b','entity_id':3,'method':'component_intersection_v1'}],'category_bindings':[{'entity_id':3,'code':19,'physical_class':'land'}]};base={'status':'research-only-not-a-build','revision':'r','entity_revision':'e'};self.r=[{**base,'schema':'source-point-component-report-v1','claims':[{'affiliation_id':'a','method':'source_point_named_region_component_v1','entity_id':3,'entity_code':19,'component_id':10}]},{**base,'schema':'source-polygon-component-report-v1','claims':[{'affiliation_id':'b','method':'component_intersection_v1','entity_id':3,'entity_code':19,'component_ids':[10,11]}]}]
 def test_osm_point_with_polygon(self):
  self.s['affiliations'][0]['method']='osm_api_node_named_region_component_v1';self.r[0]['claims'][0]['method']='osm_api_node_named_region_component_v1'
  self.assertEqual({x['affiliation_id'] for x in combine(self.c,self.s,self.r,{99})[10]},{'a','b'})
 def test_group_point_with_polygon(self):
  self.s['affiliations'][0]['method']='osm_api_island_node_group_component_v1';self.r[0]['claims'][0]['method']='osm_api_island_node_group_component_v1'
  self.assertEqual({x['affiliation_id'] for x in combine(self.c,self.s,self.r,{99})[10]},{'a','b'})
 def test_same_target_overlap_preserves_all_ids(self):self.assertEqual({x['affiliation_id'] for x in combine(self.c,self.s,self.r,{99})[10]},{'a','b'})
 def test_mainland_rejected(self):
  with self.assertRaisesRegex(ValueError,'mainland'):combine(self.c,self.s,self.r,{11})
 def test_missing_decision_rejected(self):
  with self.assertRaisesRegex(ValueError,'not resolved'):combine(self.c,self.s,self.r[:1],{99})
 def test_conflict_rejected(self):
  self.s['category_bindings'].append({'entity_id':4,'code':20,'physical_class':'land'});self.s['affiliations'][1]['entity_id']=4;self.r[1]['claims'][0].update(entity_id=4,entity_code=20)
  with self.assertRaisesRegex(ValueError,'conflicting'):combine(self.c,self.s,self.r,{99})
if __name__=='__main__':unittest.main()
