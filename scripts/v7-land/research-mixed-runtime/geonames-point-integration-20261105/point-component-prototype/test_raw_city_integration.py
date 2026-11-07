import copy,unittest
from pathlib import Path
import resolve,adapter
from test_resolve import ResolverTests,put,packed

class RawCityIntegrationTests(ResolverTests):
 def raw_fixture(self):
  self.req['source_files']=self.req['source_files'][:2]
  d,identity=self.use_named_export();raw=[{'id':'a','name':'Test place','longitude':'-112.5','latitude':'22.5'}];p=put(self.p/'point.json',raw);self.req['source_files'][0].update(p)
  for row in d['sources']+d['source_lineage_assets']:
   if row['source_id']=='p':row['sha256']=p['sha256'];row['size_bytes']=Path(p['path']).stat().st_size
  guideline=put(self.p/'guideline.md',b'Coordinate rule: WGS84 decimal degrees format.')
  gs={'source_id':'g','version':'1','sha256':guideline['sha256'],'r2_bucket':'bucket','r2_key':'g','size_bytes':Path(guideline['path']).stat().st_size};ga=dict(gs,source_uri='https://github.com/example/cities/blob/'+'a'*40+'/guideline.md',attribution='provider',license_name='test',license_uri='https://example.org/license',provider='provider',title='guideline',kind='raw',provenance={'representation':'provider_original'})
  d['sources'].append(gs);d['source_lineage_assets'].append(ga);self.req['source_files'].append(dict(source_id='g',version='1',**guideline));d['affiliation_source_refs']=[{'affiliation_id':'a','role':'coordinate_guideline','source_id':'g','source_version':'1'}]
  for asset in d['source_lineage_assets']:
   if asset['source_id']=='p':asset['source_uri']='https://github.com/example/cities/blob/'+'a'*40+'/cities.json'
  a=d['affiliations'][0];a['method']='raw_json_city_named_region_component_v1';a['evidence']['selector'].update({'name_property':'name','longitude_property':'longitude','latitude_property':'latitude','source_crs_assertion':'OGC:CRS84','extractor_version':'raw-json-city-point-selection-v1','coordinate_guideline_excerpt':'WGS84 decimal degrees format'})
  self.req['snapshot']=put(self.p/'combined.json',d);self.req['raw_city_extractor_sha256']=resolve.digest(Path(resolve.__file__).with_name('raw_city_extract.py'));return d,raw
 def test_raw_city_end_to_end(self):
  self.raw_fixture();out=resolve.resolve(self.req);c=out['claims'][0]
  self.assertEqual(c['component_id'],7);self.assertEqual(c['entity_code'],18);self.assertTrue(c['identity_check']['strict_contains']);self.assertEqual(c['source_crs_scope'],'raw_record_coordinate_assertion');self.assertEqual(c['raw_city_extraction']['source_crs_assertion'],'OGC:CRS84');self.assertEqual(c['coordinate_guideline_evidence']['matches'],1);self.assertEqual(out['raw_city_extractor_sha256'],self.req['raw_city_extractor_sha256'])
 def test_raw_city_code_pin_mismatch(self):
  self.raw_fixture();self.req['raw_city_extractor_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'raw city extractor code pin'):resolve.resolve(self.req)
 def test_raw_city_version_and_crs_rejected(self):
  for key,val in [('extractor_version','unknown'),('source_crs_assertion','EPSG:3857')]:
   d,raw=self.raw_fixture();d['affiliations'][0]['evidence']['selector'][key]=val;self.req['snapshot']=put(self.p/'combined.json',d)
   with self.assertRaisesRegex(ValueError,'unsupported raw city extractor or CRS'):resolve.resolve(self.req)
 def test_raw_city_duplicate_records_rejected(self):
  d,raw=self.raw_fixture();p=put(self.p/'point.json',raw*2);self.req['source_files'][0].update(p)
  for row in d['sources']+d['source_lineage_assets']:
   if row['source_id']=='p':row['sha256']=p['sha256'];row['size_bytes']=Path(p['path']).stat().st_size
  self.req['snapshot']=put(self.p/'combined.json',d)
  with self.assertRaisesRegex(ValueError,'uniquely'):resolve.resolve(self.req)
 def test_raw_city_forged_name_or_geometry_rejected(self):
  d,raw=self.raw_fixture();d['affiliations'][0]['evidence']['selector']['point_name']='Wrong';self.req['snapshot']=put(self.p/'combined.json',d)
  with self.assertRaisesRegex(ValueError,'name mismatch'):resolve.resolve(self.req)
  d,raw=self.raw_fixture();d['features'][0]['geometry_sha256']='0'*64;self.req['snapshot']=put(self.p/'combined.json',d)
  with self.assertRaisesRegex(ValueError,'geometry hash mismatch'):resolve.resolve(self.req)
 def test_missing_guideline_and_forged_excerpt_rejected(self):
  d,raw=self.raw_fixture();d['affiliation_source_refs']=[];self.req['snapshot']=put(self.p/'combined.json',d)
  with self.assertRaisesRegex(ValueError,'guideline missing'):resolve.resolve(self.req)
  d,raw=self.raw_fixture();d['affiliations'][0]['evidence']['selector']['coordinate_guideline_excerpt']='not present';self.req['snapshot']=put(self.p/'combined.json',d)
  with self.assertRaisesRegex(ValueError,'excerpt must occur exactly once'):resolve.resolve(self.req)
 def test_wrong_repo_or_role_rejected(self):
  d,raw=self.raw_fixture();next(x for x in d['source_lineage_assets'] if x['source_id']=='g')['source_uri']='https://github.com/other/cities/blob/'+'a'*40+'/guide.md';self.req['snapshot']=put(self.p/'combined.json',d)
  with self.assertRaisesRegex(ValueError,'share provider repository and commit'):resolve.resolve(self.req)
  d,raw=self.raw_fixture();d['affiliation_source_refs'][0]['role']='arbitrary';self.req['snapshot']=put(self.p/'combined.json',d)
  with self.assertRaisesRegex(ValueError,'unsupported source role'):resolve.resolve(self.req)
 def test_mixed_named_and_raw_adapter(self):
  d,raw=self.raw_fixture();second=copy.deepcopy(d['affiliations'][0]);second['affiliation_id']='b';second['method']='source_point_named_region_component_v1';sel=second['evidence']['selector']
  for k in ('name_property','longitude_property','latitude_property','source_crs_assertion','extractor_version','coordinate_guideline_excerpt'):del sel[k]
  d['affiliations'].append(second);d['affiliation_feature_refs'].append({'affiliation_id':'b','role':'identity_polygon','feature_id':'identity-feature'})
  out=adapter.adapt(d);self.assertEqual({x['method'] for x in out['decisions']},{'raw_json_city_named_region_component_v1','source_point_named_region_component_v1'})
 def test_mixed_methods_end_to_end(self):
  d,raw=self.raw_fixture();identity={'type':'FeatureCollection','features':[{'type':'Feature','properties':{'NE_ID':8,'NAME':'TEST ISLAND','FEATURECLA':'Island'},'geometry':{'type':'Polygon','coordinates':[[[-150,0],[-50,0],[-50,45],[-150,45],[-150,0]]]}}]};ip=put(self.p/'identity.txt',identity);self.req['source_files'][1].update(ip)
  for asset in d['sources']+d['source_lineage_assets']:
   if asset['source_id']=='i':asset['sha256']=ip['sha256'];asset['size_bytes']=Path(ip['path']).stat().st_size
  next(f for f in d['features'] if f['feature_id']=='identity-feature')['geometry_sha256']=resolve.geometry_sha(identity['features'][0]['geometry'])
  qgeom={'type':'Point','coordinates':[-67.5,22.5]};q=put(self.p/'second-point.json',{'type':'FeatureCollection','features':[{'type':'Feature','properties':{'id':'b','name':'Second place'},'geometry':qgeom}]})
  qs={'source_id':'q','version':'1','sha256':q['sha256'],'r2_bucket':'bucket','r2_key':'q','size_bytes':Path(q['path']).stat().st_size};qa=dict(qs,source_uri='https://example.org/q',attribution='provider',license_name='test',license_uri='https://example.org/license',provider='provider',title='point',kind='raw',provenance={'representation':'provider_original'})
  d['sources'].append(qs);d['source_lineage_assets'].append(qa);self.req['source_files'].append(dict(source_id='q',version='1',**q));d['features'].append({'feature_id':'f2','source_id':'q','source_version':'1','source_feature_id':'b','geometry_sha256':resolve.geometry_sha(qgeom)})
  second=copy.deepcopy(d['affiliations'][0]);second.update({'affiliation_id':'b','method':'source_point_named_region_component_v1','feature_id':'f2'});sel=second['evidence']['selector'];sel['point_name']='Second place'
  for k in ('name_property','longitude_property','latitude_property','source_crs_assertion','extractor_version','coordinate_guideline_excerpt'):del sel[k]
  d['affiliations'].append(second);d['affiliation_feature_refs'].append({'affiliation_id':'b','role':'identity_polygon','feature_id':'identity-feature'})
  cr=put(self.p/'cr',packed('<I',[(0,),(2,),(4,),(6,),(8,)]));cs=put(self.p/'cs',packed('<III',[(1,2,7),(2,4,8)]*4));self.req['component_rows']=cr;self.req['component_runs']=cs;self.manifest['pins']['component_rows']=cr;self.manifest['pins']['component_runs']=cs;self.req['component_manifest']=put(self.p/'manifest',self.manifest);self.req['snapshot']=put(self.p/'combined.json',d)
  out=resolve.resolve(self.req);self.assertEqual({(c['affiliation_id'],c['component_id']) for c in out['claims']},{('a',7),('b',8)});self.assertEqual({c['source_crs_scope'] for c in out['claims']},{'collection_feature_geometry','raw_record_coordinate_assertion'})
 def test_polygon_fk_coexists_with_point_guideline(self):
  import sys
  sys.path.insert(0,str(Path(resolve.__file__).resolve().parents[2]/'stage3-land-overrides-20261104'))
  import polygon_policy
  d,raw=self.raw_fixture();src={'source_id':'poly','version':'1','sha256':'a'*64,'r2_bucket':'bucket','r2_key':'poly','size_bytes':10};asset=dict(src,source_uri='https://example.org/poly',attribution='provider',license_name='test',license_uri='https://example.org/license',provider='provider',title='poly',kind='raw',provenance={'representation':'provider_original'})
  d['sources'].append(src);d['source_lineage_assets'].append(asset)
  for name in ('poly-main','poly-extra'):d['features'].append({'feature_id':name,'source_id':'poly','source_version':'1','source_feature_id':name,'geometry_sha256':'b'*64,'evidence':{'selector_property':'id'}})
  d['affiliations'].append({'affiliation_id':'poly-rule','decision_revision':'draft-1','method':'component_intersection_v1','scope':'land','relationship':'affiliation','entity_id':42,'feature_id':'poly-main','evidence':{'execution_status':'selected_for_research','selector':{'additional_feature_ids':['poly-extra'],'include_witnesses':[],'exclude_witnesses':[]}}});d['polygon_affiliation_feature_refs']=[{'affiliation_id':'poly-rule','role':'additional_polygon','feature_id':'poly-extra'}]
  points=adapter.adapt(d);polygons=polygon_policy.adapt(d,{'poly-rule'});self.assertEqual(len(points['decisions']),1);self.assertEqual(len(polygons['decisions']),1);self.assertEqual({s['source_id'] for s in points['sources']},{'p','i','g'});self.assertEqual({s['source_id'] for s in polygons['source_pins']},{'poly'})
  d['polygon_affiliation_feature_refs'][0]['feature_id']='missing'
  with self.assertRaisesRegex(ValueError,'orphan'):polygon_policy.adapt(d,{'poly-rule'})
if __name__=='__main__':unittest.main()
