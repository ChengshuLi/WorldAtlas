import copy,unittest
from pathlib import Path
import resolve,adapter
from test_resolve import ResolverTests,put,packed
from test_raw_city_integration import RawCityIntegrationTests

class OSMIntegrationTests(ResolverTests):
 def osm_fixture(self):
  d,identity=self.use_named_export();xml=b'<osm version="0.6"><node id="123" version="2" visible="true" lat="22.5" lon="-112.5"><tag k="name" v="Test place"/><tag k="place" v="town"/></node></osm>';p=put(self.p/'point.json',xml);self.req['source_files'][0].update(p)
  for row in d['sources']+d['source_lineage_assets']:
   if row['source_id']=='p':row['sha256']=p['sha256'];row['size_bytes']=Path(p['path']).stat().st_size
  for row in d['source_lineage_assets']:
   if row['source_id']=='p':row['source_uri']='https://api.openstreetmap.org/api/0.6/node/123/2';row['provider']='OpenStreetMap contributors'
  d['features'][0]['source_feature_id']='123';a=d['affiliations'][0];a['method']='osm_api_node_named_region_component_v1';a['evidence']['selector'].update({'id_property':'id','node_version':'2','place_tag':'town','source_crs':'OGC:CRS84','extractor_version':'osm-api-node-point-selection-v1'})
  self.req['snapshot']=put(self.p/'combined.json',d);self.req['osm_node_extractor_sha256']=resolve.digest(Path(resolve.__file__).with_name('osm_node_extract.py'));return d,xml
 def test_osm_end_to_end(self):
  self.osm_fixture();out=resolve.resolve(self.req);c=out['claims'][0];self.assertEqual(c['component_id'],7);self.assertTrue(c['identity_check']['strict_contains']);self.assertEqual(c['source_crs_scope'],'osm_api_0_6_standard');self.assertEqual(c['osm_node_extraction']['node_version'],'2');self.assertEqual(out['osm_node_extractor_sha256'],self.req['osm_node_extractor_sha256'])
 def test_code_pin(self):
  self.osm_fixture();self.req['osm_node_extractor_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'OSM node extractor code pin'):resolve.resolve(self.req)
 def test_wrong_source_uri(self):
  d,_=self.osm_fixture();next(x for x in d['source_lineage_assets'] if x['source_id']=='p')['source_uri']='https://example.org/api/0.6/node/123/2';self.req['snapshot']=put(self.p/'combined.json',d)
  with self.assertRaisesRegex(ValueError,'official OSM node URL'):resolve.resolve(self.req)
 def test_wrong_node_version(self):
  d,_=self.osm_fixture();d['affiliations'][0]['evidence']['selector']['node_version']='3';next(x for x in d['source_lineage_assets'] if x['source_id']=='p')['source_uri']='https://api.openstreetmap.org/api/0.6/node/123/3';self.req['snapshot']=put(self.p/'combined.json',d)
  with self.assertRaisesRegex(ValueError,'version or visibility'):resolve.resolve(self.req)
 def test_wrong_expected_tags(self):
  d,_=self.osm_fixture();d['affiliations'][0]['evidence']['selector']['place_tag']='village';self.req['snapshot']=put(self.p/'combined.json',d)
  with self.assertRaisesRegex(ValueError,'node tags mismatch'):resolve.resolve(self.req)
 def test_invalid_selector_and_identity(self):
  for field,value in [('id_property','node'),('source_crs','EPSG:3857'),('extractor_version','v2'),('node_version','01')]:
   d,_=self.osm_fixture();d['affiliations'][0]['evidence']['selector'][field]=value;self.req['snapshot']=put(self.p/'combined.json',d)
   with self.assertRaisesRegex(ValueError,'unsupported OSM node selector'):resolve.resolve(self.req)
  d,_=self.osm_fixture();d['affiliation_feature_refs']=[];self.req['snapshot']=put(self.p/'combined.json',d)
  with self.assertRaisesRegex(ValueError,'identity polygon feature missing'):resolve.resolve(self.req)
 def test_mixed_osm_polygon_coexist(self):
  import sys
  sys.path.insert(0,str(Path(resolve.__file__).resolve().parents[2]/'stage3-land-overrides-20261104'));import polygon_policy
  d,_=self.osm_fixture();src={'source_id':'poly','version':'1','sha256':'a'*64,'r2_bucket':'bucket','r2_key':'poly','size_bytes':10};asset=dict(src,source_uri='https://example.org/poly',attribution='provider',license_name='test',license_uri='https://example.org/license',provider='provider',title='poly',kind='raw',provenance={'representation':'provider_original'})
  d['sources'].append(src);d['source_lineage_assets'].append(asset)
  for name in ('poly-main','poly-extra'):d['features'].append({'feature_id':name,'source_id':'poly','source_version':'1','source_feature_id':name,'geometry_sha256':'b'*64,'evidence':{'selector_property':'id'}})
  d['affiliations'].append({'affiliation_id':'poly-rule','decision_revision':'draft-1','method':'component_intersection_v1','scope':'land','relationship':'affiliation','entity_id':42,'feature_id':'poly-main','evidence':{'execution_status':'selected_for_research','selector':{'additional_feature_ids':['poly-extra'],'include_witnesses':[],'exclude_witnesses':[]}}});d['polygon_affiliation_feature_refs']=[{'affiliation_id':'poly-rule','role':'additional_polygon','feature_id':'poly-extra'}]
  points=adapter.adapt(d);polygons=polygon_policy.adapt(d,{'poly-rule'});self.assertEqual(len(points['decisions']),1);self.assertEqual(len(polygons['decisions']),1)
 def test_three_point_methods_end_to_end(self):
  d,_=RawCityIntegrationTests.raw_fixture(self);geom={'type':'Polygon','coordinates':[[[-150,0],[-10,0],[-10,45],[-150,45],[-150,0]]]};identity={'type':'FeatureCollection','features':[{'type':'Feature','properties':{'NE_ID':8,'NAME':'TEST ISLAND','FEATURECLA':'Island'},'geometry':geom}]};ip=put(self.p/'identity.txt',identity);self.req['source_files'][1].update(ip)
  for asset in d['sources']+d['source_lineage_assets']:
   if asset['source_id']=='i':asset['sha256']=ip['sha256'];asset['size_bytes']=Path(ip['path']).stat().st_size
  next(f for f in d['features'] if f['feature_id']=='identity-feature')['geometry_sha256']=resolve.geometry_sha(geom)
  def add_source(key,path,payload,uri,provider='provider'):
   p=put(self.p/path,payload);src={'source_id':key,'version':'1','sha256':p['sha256'],'r2_bucket':'bucket','r2_key':key,'size_bytes':Path(p['path']).stat().st_size};asset=dict(src,source_uri=uri,attribution='provider',license_name='test',license_uri='https://example.org/license',provider=provider,title=key,kind='raw',provenance={'representation':'provider_original'});d['sources'].append(src);d['source_lineage_assets'].append(asset);self.req['source_files'].append(dict(source_id=key,version='1',**p))
  gp={'type':'Point','coordinates':[-67.5,22.5]};add_source('q','geo.json',{'type':'FeatureCollection','features':[{'type':'Feature','properties':{'id':'b','name':'Second'},'geometry':gp}]},'https://example.org/q');op={'type':'Point','coordinates':[-22.5,22.5]};add_source('o','node.xml',b'<osm version="0.6"><node id="123" version="2" visible="true" lat="22.5" lon="-22.5"><tag k="name" v="Third"/><tag k="place" v="town"/></node></osm>','https://api.openstreetmap.org/api/0.6/node/123/2','OpenStreetMap contributors')
  for aid,key,feature_id,source_id,point,method,name in [('b','b','f2','q',gp,'source_point_named_region_component_v1','Second'),('c','123','f3','o',op,'osm_api_node_named_region_component_v1','Third')]:
   d['features'].append({'feature_id':feature_id,'source_id':source_id,'source_version':'1','source_feature_id':key,'geometry_sha256':resolve.geometry_sha(point)});a=copy.deepcopy(d['affiliations'][0]);a.update(affiliation_id=aid,method=method,feature_id=feature_id);sel=a['evidence']['selector'];sel['point_name']=name
   for k in ('name_property','longitude_property','latitude_property','source_crs_assertion','extractor_version','coordinate_guideline_excerpt'):del sel[k]
   if method=='osm_api_node_named_region_component_v1':sel.update(id_property='id',node_version='2',place_tag='town',source_crs='OGC:CRS84',extractor_version='osm-api-node-point-selection-v1')
   d['affiliations'].append(a);d['affiliation_feature_refs'].append({'affiliation_id':aid,'role':'identity_polygon','feature_id':'identity-feature'})
  cr=put(self.p/'cr',packed('<I',[(0,),(3,),(6,),(9,),(12,)]));cs=put(self.p/'cs',packed('<III',[(1,2,7),(2,3,8),(3,4,9)]*4));self.req['component_rows']=cr;self.req['component_runs']=cs;self.manifest['pins']['component_rows']=cr;self.manifest['pins']['component_runs']=cs;self.req['component_manifest']=put(self.p/'manifest',self.manifest);self.req['snapshot']=put(self.p/'combined.json',d);self.req['osm_node_extractor_sha256']=resolve.digest(Path(resolve.__file__).with_name('osm_node_extract.py'))
  out=resolve.resolve(self.req);self.assertEqual({(c['affiliation_id'],c['component_id']) for c in out['claims']},{('a',7),('b',8),('c',9)});self.assertEqual({c['source_crs_scope'] for c in out['claims']},{'collection_feature_geometry','raw_record_coordinate_assertion','osm_api_0_6_standard'})
if __name__=='__main__':unittest.main()
