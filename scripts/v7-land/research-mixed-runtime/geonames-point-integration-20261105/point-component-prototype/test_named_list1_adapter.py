import copy,unittest
import adapter
from test_adapter import fixture
class NamedList1Adapter(unittest.TestCase):
 def setUp(self):
  self.s=fixture();s=self.s;s.update(schema='worldatlas-geography-decision-draft-evidence-v3',polygon_corroboration_refs=[],ecoregion_source_refs=[],unsupported_affiliation_source_ref_table_present=False,unsupported_point_methods_present=False,affiliation_source_refs=[],affiliation_feature_refs=[]);a=s['affiliations'][0];a['method']='geonames_zip_named_list1_component_v1';a['evidence']['selector']={'island_identity':'Synthetic Island','point_name':'Synthetic Island','id_property':'geonameid','country_code':'ZZ','extractor_version':'geonames-island-point-extraction-v1','list1_entry_id':'entry','old_item_id':'old'};s['features'][0]['source_feature_id']='123';asset=s['source_lineage_assets'][0];asset.update(provider='GeoNames',source_uri='https://download.geonames.org/export/dump/ZZ.zip');s['list1_entries']=[{'entry_id':'entry','decision_revision':'r','execution_status':'selected_for_research','affiliation_ids':['a'],'old_list1_refs':[{'old_item_id':'old','reference':'List 1 · Example continent · Reason 1 · Item x'}]}];self.a=a;self.sel=a['evidence']['selector'];self.e=s['list1_entries'][0]
 def test_valid(self):
  d=adapter.adapt(self.s)['decisions'][0];self.assertEqual((d['list1_entry_id'],d['old_item_id']),('entry','old'));self.assertIsNone(d['identity_source_id'])
 def bad(self):
  with self.assertRaises(ValueError):adapter.adapt(self.s)
 def test_wrong_entry(self):self.sel['list1_entry_id']='bad';self.bad()
 def test_wrong_old_item(self):self.sel['old_item_id']='bad';self.bad()
 def test_missing_link(self):self.e['affiliation_ids']=[];self.bad()
 def test_duplicate_entry(self):self.s['list1_entries'].append(copy.deepcopy(self.e));self.bad()
 def test_wrong_revision(self):self.e['decision_revision']='bad';self.bad()
 def test_unselected_entry(self):self.e['execution_status']='pending';self.bad()
 def test_wrong_continent(self):self.e['old_list1_refs'][0]['reference']='List 1 · Other · Reason 1 · Item x';self.bad()
 def test_wrong_name(self):self.sel['island_identity']='Other';self.bad()
 def test_wrong_country(self):self.sel['country_code']='US';self.bad()
 def test_wrong_provider(self):self.s['source_lineage_assets'][0]['provider']='Other';self.bad()
 def test_extra_selector(self):self.sel['extra']='bad';self.bad()
if __name__=='__main__':unittest.main()
