import copy,unittest
from point_claim_validator import claims_for
METHOD='geonames_zip_island_named_region_component_v1'
class GeoNamesClaims(unittest.TestCase):
 def setUp(self):
  self.comp={'revision':'r','entity_revision':'e','affiliation_ids':['a'],'affiliation_entry_links':{'a':['entry']}}
  self.sel={'extractor_version':'geonames-island-point-extraction-v1','id_property':'geonameid','point_name':'Synthetic Island','country_code':'XY'}
  self.feature={'feature_id':'f','source_id':'s','source_version':'v','source_feature_id':'123','geometry_sha256':'g'*64}
  self.snap={'affiliations':[{'affiliation_id':'a','entity_id':3,'method':METHOD,'feature_id':'f','evidence':{'selector':self.sel}}],'category_bindings':[{'entity_id':3,'code':19,'physical_class':'land'}],'features':[self.feature],'source_lineage_assets':[{'source_id':'s','version':'v','sha256':'h'*64}]}
  self.claim={'affiliation_id':'a','entity_id':3,'entity_code':19,'component_id':10,'method':METHOD,'point_source':{'source_id':'s','version':'v','sha256':'h'*64},'geonames_extraction':{'schema':'geonames-island-point-extraction-v1','source_sha256':'h'*64,'record_id':'123','name':'Synthetic Island','feature_class':'T','feature_code':'ISL','country_code':'XY','geometry_sha256':'g'*64,'source_crs':'OGC:CRS84'},'source_crs_scope':'geonames_wgs84_record','identity_check':{'strict_contains':True}}
  self.res={'schema':'source-point-component-report-v1','status':'research-only-not-a-build','revision':'r','entity_revision':'e','claims':[self.claim]}
 def test_valid(self):self.assertEqual(claims_for(self.comp,self.snap,self.res)[10][0]['entry_ids'],['entry'])
 def test_extraction_tampering_rejected(self):
  for key in ['schema','source_sha256','record_id','name','feature_class','feature_code','country_code','geometry_sha256','source_crs']:
   bad=copy.deepcopy(self.res);bad['claims'][0]['geonames_extraction'][key]='bad'
   with self.subTest(key=key),self.assertRaises(ValueError):claims_for(self.comp,self.snap,bad)
 def test_bad_identity_and_crs_rejected(self):
  for field in ('identity_check','source_crs_scope','point_source'):
   bad=copy.deepcopy(self.res);bad['claims'][0][field]={} if field!='source_crs_scope' else 'bad'
   with self.subTest(field=field),self.assertRaises(ValueError):claims_for(self.comp,self.snap,bad)
 def test_wrong_selector_rejected(self):
  for key in ('country_code','extractor_version','id_property','point_name'):
   bad=copy.deepcopy(self.snap);bad['affiliations'][0]['evidence']['selector'][key]='bad'
   with self.subTest(key=key),self.assertRaises(ValueError):claims_for(self.comp,bad,self.res)
if __name__=='__main__':unittest.main()
