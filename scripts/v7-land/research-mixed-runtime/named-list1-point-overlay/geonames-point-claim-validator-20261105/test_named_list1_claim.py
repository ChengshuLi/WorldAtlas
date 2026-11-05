import copy,unittest
from test_geonames_claim import GeoNamesClaims
from point_claim_validator import claims_for
METHOD='geonames_zip_named_list1_component_v1'
class NamedList1Claims(GeoNamesClaims):
 def setUp(self):
  super().setUp();self.snap['affiliations'][0]['method']=METHOD;self.claim['method']=METHOD;self.claim['entity_name']='Europe';self.sel.update({'island_identity':'Synthetic Island','list1_entry_id':'entry','old_item_id':'old'});self.snap['entities']=[{'id':3,'name':'Europe'}];self.snap['list1_entries']=[{'entry_id':'entry','decision_revision':'r','execution_status':'selected_for_research','affiliation_ids':['a'],'old_list1_refs':[{'old_item_id':'old','reference':'List 1 · Europe · Reason 1 · Item x'}]}];self.claim['identity_check']={'method':'selected_named_list1_entry','list1_entry_id':'entry','old_item_id':'old'}
 def test_tampered_list1_rejected(self):
  for field in ('list1_entry_id','old_item_id'):
   bad=copy.deepcopy(self.res);bad['claims'][0]['identity_check'][field]='bad'
   with self.subTest(field=field),self.assertRaises(ValueError):claims_for(self.comp,self.snap,bad)
 def test_wrong_continent_rejected(self):
  bad=copy.deepcopy(self.snap);bad['list1_entries'][0]['old_list1_refs'][0]['reference']='List 1 · Asia · Reason 1 · Item x'
  with self.assertRaises(ValueError):claims_for(self.comp,bad,self.res)
 def test_missing_link_rejected(self):
  bad=copy.deepcopy(self.comp);bad['affiliation_entry_links']['a']=[]
  with self.assertRaises(ValueError):claims_for(bad,self.snap,self.res)
if __name__=='__main__':unittest.main()
