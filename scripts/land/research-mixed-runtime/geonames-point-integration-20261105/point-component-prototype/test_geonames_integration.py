import hashlib,io,unittest,zipfile
from pathlib import Path
import resolve
from test_resolve import ResolverTests,put
class GeoNamesIntegration(ResolverTests):
 def fixture(self):
  d,_=self.use_named_export();row='\t'.join(['123','Test place','Test place','','22.5','-112.5','T','ISL','ZZ','','','','','','0','','','Pacific/Test','2020-01-01'])+'\n';b=io.BytesIO()
  with zipfile.ZipFile(b,'w',compression=zipfile.ZIP_DEFLATED) as z:z.writestr('ZZ.txt',row)
  pin=put(self.p/'source.zip',b.getvalue());self.req['source_files'][0].update(pin)
  for x in d['sources']+d['source_lineage_assets']:
   if x['source_id']=='p':x['sha256']=pin['sha256'];x['size_bytes']=Path(pin['path']).stat().st_size
  asset=next(x for x in d['source_lineage_assets'] if x['source_id']=='p');asset['source_uri']='https://download.geonames.org/export/dump/ZZ.zip';asset['provider']='GeoNames'
  d['features'][0]['source_feature_id']='123';a=d['affiliations'][0];a['method']='geonames_zip_island_named_region_component_v1';a['evidence']['selector'].update({'id_property':'geonameid','country_code':'ZZ','extractor_version':'geonames-island-point-extraction-v1'})
  self.req['snapshot']=put(self.p/'combined.json',d);self.req['geonames_extractor_sha256']=resolve.digest(Path(resolve.__file__).with_name('geonames_extract.py'));return d
 def test_end_to_end(self):
  self.fixture();r=resolve.resolve(self.req);c=r['claims'][0];self.assertEqual(c['component_id'],7);self.assertEqual(c['source_crs_scope'],'geonames_wgs84_record');self.assertEqual(c['geonames_extraction']['record_id'],'123');self.assertTrue(c['identity_check']['strict_contains']);self.assertEqual(r['geonames_extractor_sha256'],self.req['geonames_extractor_sha256'])
 def test_bad_extractor_pin(self):
  self.fixture();self.req['geonames_extractor_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'GeoNames extractor code pin'):resolve.resolve(self.req)
 def test_bad_provider(self):
  d=self.fixture();next(x for x in d['source_lineage_assets'] if x['source_id']=='p')['source_uri']='https://example.org/ZZ.zip';self.req['snapshot']=put(self.p/'combined.json',d)
  with self.assertRaisesRegex(ValueError,'GeoNames original source'):resolve.resolve(self.req)
 def test_bad_country(self):
  d=self.fixture();d['affiliations'][0]['evidence']['selector']['country_code']='ZZZ';self.req['snapshot']=put(self.p/'combined.json',d)
  with self.assertRaisesRegex(ValueError,'unsupported GeoNames'):resolve.resolve(self.req)
 def test_wrong_name(self):
  d=self.fixture();d['affiliations'][0]['evidence']['selector']['point_name']='Different';self.req['snapshot']=put(self.p/'combined.json',d)
  with self.assertRaisesRegex(ValueError,'island identity mismatch'):resolve.resolve(self.req)
if __name__=='__main__':unittest.main()
