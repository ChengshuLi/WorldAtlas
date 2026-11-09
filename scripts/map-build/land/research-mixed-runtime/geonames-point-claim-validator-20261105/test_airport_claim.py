import copy,unittest
from test_geonames_claim import GeoNamesClaims
from point_claim_validator import claims_for
METHOD='geonames_zip_airport_named_region_component_v1'
class AirportClaims(GeoNamesClaims):
 def setUp(self):
  super().setUp();self.sel.update(extractor_version='geonames-airport-point-extraction-v1',point_name='Synthetic Airport',island_identity='Broad Archipelago',airport_island_name='Synthetic Island',island_evidence_source_id='official',island_evidence_source_version='v1',island_evidence_citation='page 2');self.snap['affiliations'][0]['method']=METHOD
  self.claim['method']=METHOD;self.claim['geonames_extraction'].update(schema='geonames-airport-point-extraction-v1',name='Synthetic Airport',feature_class='S',feature_code='AIRP')
  self.snap['source_lineage_assets'].append({'source_id':'official','version':'v1','sha256':'z'*64})
  self.claim['identity_source']={'source_id':'region','version':'v1'}
  self.snap['list1_entry_evidence_sources']=[{'decision_revision':'r','entry_id':'entry','role':'geographic_membership_evidence','source_id':'official','source_version':'v1','citation_section':'page 2','interpretation':'Synthetic Airport is on Synthetic Island.'}]
 def test_airport_valid(self):self.assertIn(10,claims_for(self.comp,self.snap,self.res))
 def test_requires_evidence_link(self):
  bad=copy.deepcopy(self.snap);bad['list1_entry_evidence_sources']=[]
  with self.assertRaisesRegex(ValueError,'airport island evidence'):claims_for(self.comp,bad,self.res)
 def test_requires_explicit_island_assertion(self):
  bad=copy.deepcopy(self.snap);bad['list1_entry_evidence_sources'][0]['interpretation']='Synthetic Airport is in the broad archipelago.'
  with self.assertRaisesRegex(ValueError,'island identity assertion'):claims_for(self.comp,bad,self.res)
 def test_rejects_airport_masquerading_as_island(self):
  bad=copy.deepcopy(self.res);bad['claims'][0]['geonames_extraction'].update(feature_class='T',feature_code='ISL')
  with self.assertRaisesRegex(ValueError,'airport extraction'):claims_for(self.comp,self.snap,bad)
 def test_rejects_identical_evidence_source(self):
  bad=copy.deepcopy(self.snap);sel=bad['affiliations'][0]['evidence']['selector'];sel.update(island_evidence_source_id='s',island_evidence_source_version='v');bad['list1_entry_evidence_sources'][0].update(source_id='s',source_version='v')
  with self.assertRaisesRegex(ValueError,'airport island evidence'):claims_for(self.comp,bad,self.res)
 def test_missing_evidence_asset_rejected(self):
  bad=copy.deepcopy(self.snap);bad['source_lineage_assets']=[x for x in bad['source_lineage_assets'] if x['source_id']!='official']
  with self.assertRaisesRegex(ValueError,'evidence asset'):claims_for(self.comp,bad,self.res)
 def test_evidence_must_not_be_broad_label(self):
  bad=copy.deepcopy(self.res);bad['claims'][0]['identity_source']={'source_id':'official','version':'v1'}
  with self.assertRaisesRegex(ValueError,'not independent'):claims_for(self.comp,self.snap,bad)
 def test_empty_island_name_rejected(self):
  bad=copy.deepcopy(self.snap);bad['affiliations'][0]['evidence']['selector']['airport_island_name']=''
  with self.assertRaisesRegex(ValueError,'identity assertion'):claims_for(self.comp,bad,self.res)
if __name__=='__main__':unittest.main()
