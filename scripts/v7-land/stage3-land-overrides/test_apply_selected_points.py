import unittest
from apply_selected_points import claims_for
class TestPointBinding(unittest.TestCase):
 def setUp(self):
  self.comp={'revision':'r','entity_revision':'e','affiliation_ids':['a'],'affiliation_entry_links':{'a':['x']}}
  self.snap={'affiliations':[{'affiliation_id':'a','entity_id':3,'method':'source_point_named_region_component_v1'}],'category_bindings':[{'entity_id':3,'code':19,'physical_class':'land'}]}
  self.res={'schema':'source-point-component-report-v1','status':'research-only-not-a-build','revision':'r','entity_revision':'e','claims':[{'affiliation_id':'a','entity_id':3,'entity_code':19,'component_id':10,'method':'source_point_named_region_component_v1'}]}
 def test_bound(self):self.assertEqual(claims_for(self.comp,self.snap,self.res)[10][0]['entry_ids'],['x'])
 def test_target_tamper(self):
  self.res['claims'][0]['entity_code']=20
  with self.assertRaisesRegex(ValueError,'mismatch'):claims_for(self.comp,self.snap,self.res)
 def test_missing_claim(self):
  self.res['claims']=[]
  with self.assertRaisesRegex(ValueError,'count'):claims_for(self.comp,self.snap,self.res)
if __name__=='__main__':unittest.main()
