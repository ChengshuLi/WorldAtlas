import unittest
from test_geonames_integration import GeoNamesIntegration
from test_resolve import put
import resolve
class NamedIslandIntegration(GeoNamesIntegration):
 def test_source_backed_decision_without_old_review(self):
  d=self.fixture()
  a=d['affiliations'][0]
  a['method']='geonames_zip_named_island_component_v1'
  a['evidence']['selector']={
   'island_identity':'Test place','point_name':'Test place','id_property':'geonameid',
   'country_code':'ZZ','extractor_version':'geonames-island-point-extraction-v1',
   'decision_entry_id':'entry',
  }
  d['affiliation_feature_refs']=[]
  self.req['source_files']=[x for x in self.req['source_files'] if x['source_id']=='p']
  d['list1_entries']=[{'entry_id':'entry','decision_revision':d['decision_revision']['id'],
                      'execution_status':'selected_for_research','affiliation_ids':[a['affiliation_id']]}]
  evidence=next(row for row in d['source_lineage_assets'] if row['source_id']!='p')
  d['list1_entry_evidence_sources']=[{
   'entry_id':'entry','decision_revision':d['decision_revision']['id'],
   'role':'geographic_membership_evidence','source_id':evidence['source_id'],
   'source_version':evidence['version'],
  }]
  self.req['snapshot']=put(self.p/'combined.json',d)
  claim=resolve.resolve(self.req)['claims'][0]
  self.assertEqual(claim['component_id'],7)
  self.assertEqual(claim['identity_check'],{
   'method':'selected_named_island_decision','decision_entry_id':'entry',
  })
  d['list1_entry_evidence_sources']=[]
  self.req['snapshot']=put(self.p/'combined.json',d)
  with self.assertRaisesRegex(ValueError,'geographic evidence missing'):
   resolve.resolve(self.req)

if __name__=='__main__':unittest.main()
