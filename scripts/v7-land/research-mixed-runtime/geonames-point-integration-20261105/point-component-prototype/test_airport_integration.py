import hashlib,io,unittest,zipfile
from pathlib import Path
import resolve
from test_resolve import ResolverTests,put
class AirportIntegration(ResolverTests):
 def fixture(self):
  d,_=self.use_named_export();row='\t'.join(['123','Test Airport','Test Airport','','22.5','-112.5','S','AIRP','ZZ','','','','','','0','','','Pacific/Test','2020-01-01'])+'\n';b=io.BytesIO()
  with zipfile.ZipFile(b,'w',compression=zipfile.ZIP_DEFLATED) as z:z.writestr('ZZ.txt',row)
  pin=put(self.p/'source.zip',b.getvalue());self.req['source_files'][0].update(pin)
  for x in d['sources']+d['source_lineage_assets']:
   if x['source_id']=='p':x['sha256']=pin['sha256'];x['size_bytes']=Path(pin['path']).stat().st_size
  asset=next(x for x in d['source_lineage_assets'] if x['source_id']=='p');asset['source_uri']='https://download.geonames.org/export/dump/ZZ.zip';asset['provider']='GeoNames'
  d['features'][0]['source_feature_id']='123';a=d['affiliations'][0];a['method']='geonames_zip_airport_named_region_component_v1';a['evidence']['selector'].update({'id_property':'geonameid','point_name':'Test Airport','country_code':'ZZ','extractor_version':'geonames-airport-point-extraction-v1','airport_island_name':'Synthetic Island','island_evidence_source_id':'official','island_evidence_source_version':'v1','island_evidence_citation':'page 2'})
  self.req['snapshot']=put(self.p/'combined.json',d);self.req['geonames_airport_extractor_sha256']=resolve.digest(Path(resolve.__file__).with_name('geonames_airport_extract.py'));return d
 def test_airport_end_to_end(self):
  self.fixture();r=resolve.resolve(self.req);c=r['claims'][0];self.assertEqual(c['component_id'],7);self.assertEqual(c['geonames_extraction']['record_id'],'123');self.assertEqual(c['geonames_extraction']['feature_code'],'AIRP');self.assertTrue(c['identity_check']['strict_contains']);self.assertEqual(r['geonames_airport_extractor_sha256'],self.req['geonames_airport_extractor_sha256'])
 def test_bad_pin_rejected(self):
  self.fixture();self.req['geonames_airport_extractor_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'airport extractor code pin'):resolve.resolve(self.req)
 def test_missing_evidence_selector_rejected(self):
  d=self.fixture();del d['affiliations'][0]['evidence']['selector']['island_evidence_source_id'];self.req['snapshot']=put(self.p/'combined.json',d)
  with self.assertRaisesRegex(ValueError,'selector missing'):resolve.resolve(self.req)
if __name__=='__main__':unittest.main()
