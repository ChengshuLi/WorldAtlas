"""Reverse macro membership without changing identities, geometry or historic claims."""
import copy,importlib.util,pathlib,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('restoration',ROOT/'scripts/restore-reviewed-geography.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class ReverseTests(unittest.TestCase):
 def setUp(self):
  units={};parent=None
  for tier in reversed(m.helper.TIERS[1:]):units[tier]={'id':tier,'name':tier,'level':tier,'parent_id':parent};parent=tier
  self.before_units=units;self.before_features=[{'type':'Feature','properties':{'id':'L','name':'Name','parent_id':'province','metadata':{'source':'kept'}},'geometry':{'type':'Polygon','coordinates':[[[0,0],[1,0],[1,1],[0,1],[0,0]]]}}]
  self.after_units=copy.deepcopy(units);self.after_units['province']['name']='New province reference';self.after_units['new']={'id':'new','level':'province','name':'New cluster','parent_id':'area'}
  self.after_features=copy.deepcopy(self.before_features);self.after_features[0]['properties']['parent_id']='new';self.after_features[0]['properties']['metadata']['macro']='modern reference'
  row={'location_id':'L','before_properties':copy.deepcopy(self.before_features[0]['properties']),'after_properties':copy.deepcopy(self.after_features[0]['properties']),'geometry_sha256':m.digest(self.before_features[0]['geometry'])}
  self.receipt={'before_sha256':m.digest([self.before_units,self.before_features]),'after_sha256':m.digest([self.after_units,self.after_features]),'before_units':list(self.before_units.values()),'changed_location_properties':[row],'unchanged_geometry_ids':['L'],'unchanged_geometry_sha256':m.digest([['L',self.before_features[0]['geometry']]])}
 def test_complete_reverse_and_original_input_immutability(self):
  original=copy.deepcopy(self.after_features);features,units=m.reverse_macro(self.after_features,self.after_units,self.receipt)
  self.assertEqual(features,self.before_features);self.assertEqual(units,self.before_units);self.assertEqual(self.after_features,original);self.assertEqual(features[0]['geometry'],original[0]['geometry'])
 def test_geometry_changes_rejected(self):
  self.after_features[0]['geometry']['coordinates'][0][1][0]=2
  with self.assertRaisesRegex(ValueError,'content differs'):m.reverse_macro(self.after_features,self.after_units,self.receipt)
 def test_metadata_changes_cannot_silently_pass_footprint_guards(self):
  self.after_features[0]['properties']['metadata']['source']='changed'
  with self.assertRaisesRegex(ValueError,'content differs'):m.reverse_macro(self.after_features,self.after_units,self.receipt)
 def test_invalid_archived_parent_chain_rejected(self):
  self.receipt['before_units'][0]['parent_id']='broken';units={u['id']:u for u in self.receipt['before_units']};self.receipt['before_sha256']=m.digest([units,self.before_features])
  with self.assertRaisesRegex(ValueError,'Continent|Incomplete'):m.reverse_macro(self.after_features,self.after_units,self.receipt)
 def test_changed_receipt_properties_rejected(self):
  self.receipt['changed_location_properties'][0]['after_properties']['name']='other'
  with self.assertRaisesRegex(ValueError,'evidence differs'):m.reverse_macro(self.after_features,self.after_units,self.receipt)
 def test_raw_newline_convention_is_explicit(self):
  value={'name':'São Tomé'};self.assertEqual(m.encoded(value,True),m.encoded(value)+b'\n');self.assertNotEqual(m.hashbytes(m.encoded(value)),m.hashbytes(m.encoded(value,True)))

if __name__=='__main__':unittest.main()
