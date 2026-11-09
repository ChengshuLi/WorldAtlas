import unittest,numpy as np
from test_write_land_stream import WriterTest
from preflight import validate
class Preflight(WriterTest):
 def runv(self):
  a,b=self.pair('c',self.comp);c,d=self.pair('p',self.phys);e,f=self.pair('s',self.seed)
  return validate(8,2,a,b,c,d,e,f,np.array(self.roots,dtype='u4'),[1,2,3,4],required_codes=[17,18,19])
 def test_valid_preflight(self):self.assertEqual(self.runv()['land_cells'],13)
 def test_physical_gap(self):
  self.phys[0]=[(3,17),(5,1),(7,17),(8,1)]
  with self.assertRaisesRegex(ValueError,'physical/component'):self.runv()
 def test_unknown_root(self):
  self.roots=[10,12]
  with self.assertRaisesRegex(ValueError,'unknown nonseed'):self.runv()
 def test_seed_mismatch(self):
  self.seed[0]=[(2,17),(4,0),(8,0)]
  with self.assertRaisesRegex(ValueError,'seed root gap'):self.runv()
if __name__=='__main__':unittest.main()

class RulePopulation(Preflight):
 def rule_inputs(self):
  return ([{'component_id_current_generation_only':1,'inside_code':17,'outside_code':17,'region_id':None},
           {'component_id_current_generation_only':2,'inside_code':17,'outside_code':18,'region_id':'split'},
           {'component_id_current_generation_only':3,'inside_code':19,'outside_code':19,'region_id':None},
           {'component_id_current_generation_only':4,'inside_code':19,'outside_code':19,'region_id':None}],
          {'1':{'inside_cells':2,'outside_cells':0},'2':{'inside_cells':1,'outside_cells':1},'3':{'inside_cells':2,'outside_cells':0},'4':{'inside_cells':2,'outside_cells':0}},
          {'17':3,'18':1,'19':4})
 def checked(self,rules,pop,counts):
  a,b=self.pair('c',self.comp);c,d=self.pair('p',self.phys);e,f=self.pair('s',self.seed)
  return validate(8,2,a,b,c,d,e,f,np.array(self.roots,dtype='u4'),[1,2,3,4],required_codes=[17,18,19],seed_rules=rules,expected_rule_population=pop,expected_category_counts=counts)
 def test_rule_population_matches_independent_sweep(self):
  r,p,c=self.rule_inputs();self.assertEqual(self.checked(r,p,c)['seed_category_cells'],c)
 def test_rule_population_tamper_fails(self):
  r,p,c=self.rule_inputs();p['2']['outside_cells']=2
  with self.assertRaisesRegex(ValueError,'rule population'):self.checked(r,p,c)
 def test_seed_category_outside_selected_rule_fails(self):
  r,p,c=self.rule_inputs();r[1]['outside_code']=20
  with self.assertRaisesRegex(ValueError,'split-component seed category'):self.checked(r,p,c)
 def test_equal_codes_with_region_fails(self):
  r,p,c=self.rule_inputs();r[0]['region_id']='unsupported'
  with self.assertRaisesRegex(ValueError,'split-component seed category'):self.checked(r,p,c)

 def test_extra_reported_root_fails(self):
  r,p,c=self.rule_inputs();p['999']={'inside_cells':1,'outside_cells':0}
  with self.assertRaisesRegex(ValueError,'population root mismatch'):self.checked(r,p,c)
