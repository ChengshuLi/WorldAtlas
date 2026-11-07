import unittest
from pathlib import Path
from test_geonames_integration import GeoNamesIntegration
from test_resolve import put
import resolve
class NamedList1Integration(GeoNamesIntegration):
 def fixture(self):
  d=super().fixture();a=d['affiliations'][0];a['method']='geonames_zip_named_list1_component_v1';a['evidence']['selector']={'island_identity':'Test place','point_name':'Test place','id_property':'geonameid','country_code':'ZZ','extractor_version':'geonames-island-point-extraction-v1','list1_entry_id':'entry','old_item_id':'old'};d['affiliation_feature_refs']=[];self.req['source_files']=[x for x in self.req['source_files'] if x['source_id']=='p'];d['list1_entries']=[{'entry_id':'entry','decision_revision':d['decision_revision']['id'],'execution_status':'selected_for_research','affiliation_ids':[a['affiliation_id']],'old_list1_refs':[{'old_item_id':'old','reference':'List 1 · '+d['entities'][0]['name']+' · Reason 1 · Item x'}]}];self.req['snapshot']=put(self.p/'combined.json',d);return d
 def test_end_to_end(self):
  self.fixture();r=resolve.resolve(self.req);c=r['claims'][0];self.assertEqual(c['component_id'],7);self.assertEqual(c['source_crs_scope'],'geonames_wgs84_record');self.assertEqual(c['identity_check']['old_item_id'],'old');self.assertIsNone(c['identity_source'])
 def test_wrong_name(self):
  d=self.fixture();d['affiliations'][0]['evidence']['selector']['point_name']='Different';self.req['snapshot']=put(self.p/'combined.json',d)
  with self.assertRaisesRegex(ValueError,'List 1 entry link or island identity'):resolve.resolve(self.req)
 def test_missing_entry(self):
  d=self.fixture();d['list1_entries']=[];self.req['snapshot']=put(self.p/'combined.json',d)
  with self.assertRaisesRegex(ValueError,'List 1'):resolve.resolve(self.req)
if __name__=='__main__':unittest.main()
