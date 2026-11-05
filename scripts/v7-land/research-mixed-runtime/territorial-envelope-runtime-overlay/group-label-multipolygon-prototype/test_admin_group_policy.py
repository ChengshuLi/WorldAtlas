import hashlib,json
from pathlib import Path
from test_polygon_resolution import ResolveTests
import polygon_policy
class AdminGroupTests(ResolveTests):
 def prepare(self):
  raw='''<osm><node id="1" lon="-105" lat="55"/><node id="2" lon="40" lat="55"/><node id="3" lon="40" lat="89"/><node id="4" lon="-105" lat="89"/><node id="5" lon="0" lat="70"/><way id="10"><nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="1"/></way><relation id="20" version="4"><member type="way" ref="10" role="outer"/><member type="node" ref="5" role="label"/><tag k="type" v="boundary"/><tag k="boundary" v="administrative"/><tag k="admin_level" v="2"/><tag k="ISO3166-1:alpha2" v="XY"/><tag k="name:en" v="Example"/></relation></osm>''';self.file.write_text(raw);h=hashlib.sha256(self.file.read_bytes()).hexdigest()
  for x in (self.snap['sources'][0],self.snap['source_lineage_assets'][0],self.sources[0]):x['sha256']=h;x['size_bytes']=self.file.stat().st_size
  self.snap['source_lineage_assets'][0].update(source_uri='https://api.openstreetmap.org/api/0.6/relation/20/full',provider='OpenStreetMap contributors',license_name='ODbL 1.0',attribution='© OpenStreetMap contributors')
  geom={'type':'MultiPolygon','coordinates':[[[[-105.,55.],[40.,55.],[40.,89.],[-105.,89.],[-105.,55.]]]]};self.snap['features'][0].update(source_feature_id='20',geometry_sha256=hashlib.sha256(json.dumps(geom,sort_keys=True,separators=(',',':')).encode()).hexdigest(),evidence={'source_format':'osm-xml','relation_version':'4','geometry_hash_method':'binary64-sorted-compact-geojson-v1'})
  g={'type':'Polygon','coordinates':[[[-105,55],[4,55],[4,89],[-105,89],[-105,55]]]};props={'id':'group','NAME':'Example group','FEATURECLA':'Island group','REGION':'Europe'};f=self.file.parent/'group.json';f.write_text(json.dumps({'type':'FeatureCollection','features':[{'type':'Feature','properties':props,'geometry':g}]}));pin={'source_id':'group-source','version':'v','sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'r2_bucket':'bucket','r2_key':'group','size_bytes':f.stat().st_size};self.snap['sources'].append(pin);self.snap['source_lineage_assets'].append({**pin,'kind':'raw','provenance':{'representation':'provider_original'},'source_uri':'https://example.com','attribution':'Natural Earth','license_name':'public domain','license_uri':'https://example.com/license','provider':'Natural Earth contributors'});self.sources.append({**pin,'path':str(f)});self.snap['features'].append({'feature_id':'group','source_id':'group-source','source_version':'v','source_feature_id':'group','geometry_sha256':hashlib.sha256(json.dumps(g,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'evidence':{'selector_property':'id','expected_properties':{'NAME':'Example group','FEATURECLA':'Island group','REGION':'Europe'}}});self.snap['entities']=[{'id':3,'name':'Europe','level':'continent'}];self.snap['polygon_affiliation_feature_refs']=[{'affiliation_id':'a','role':'additional_polygon','feature_id':'group'}]
  a=self.snap['affiliations'][0];a['method']='osm_admin_group_containment_v1';a['evidence']['selector']={'additional_feature_ids':['group'],'include_witnesses':[],'exclude_witnesses':[],'relation_version':'4','extractor_version':'osm-admin-envelope-v1','expected_identity_tags':{'name:en':'Example','ISO3166-1:alpha2':'XY','boundary':'administrative','admin_level':'2'}};self.policy=polygon_policy.adapt(self.snap,{'a'})
 def test_two_source_intersection(self):
  self.prepare();c=self.runv()['claims'][0];self.assertEqual(c['component_ids'],[10]);self.assertEqual(c['containment']['policy'],'all-centers-within-both-sources-v1')
 def test_wrong_but_nonempty_name_or_iso_fails(self):
  for key,val in [('name:en','Wrong'),('ISO3166-1:alpha2','ZZ')]:
   self.setUp();self.prepare();self.snap['affiliations'][0]['evidence']['selector']['expected_identity_tags'][key]=val;self.policy=polygon_policy.adapt(self.snap,{'a'})
   with self.assertRaisesRegex(ValueError,'identity tags mismatch'):self.runv()
 def test_wrong_group_region_fails_closed(self):
  self.prepare();self.snap['features'][1]['evidence']['expected_properties']['REGION']='Asia'
  with self.assertRaises(ValueError):polygon_policy.adapt(self.snap,{'a'})
 def test_wrong_relation_version_and_id_fail(self):
  self.prepare();self.snap['affiliations'][0]['evidence']['selector']['relation_version']='5';self.snap['features'][0]['evidence']['relation_version']='5';self.policy=polygon_policy.adapt(self.snap,{'a'})
  with self.assertRaises(ValueError):self.runv()
  self.setUp();self.prepare();self.snap['features'][0]['source_feature_id']='21'
  with self.assertRaises(ValueError):polygon_policy.adapt(self.snap,{'a'})
 def test_wrong_but_nonempty_group_name_fails_at_source(self):
  self.prepare();self.snap['features'][1]['evidence']['expected_properties']['NAME']='Wrong group';self.policy=polygon_policy.adapt(self.snap,{'a'})
  with self.assertRaisesRegex(ValueError,'identity properties mismatch'):self.runv()
 def set_group_bounds(self,west,east):
  f=self.file.parent/'group.json';d=json.loads(f.read_text());middle=(west+east)/2;g={'type':'Polygon','coordinates':[[[west,55],[middle,55],[east,55],[east,89],[middle,89],[west,89],[west,55]]]};d['features'][0]['geometry']=g;f.write_text(json.dumps(d));h=hashlib.sha256(f.read_bytes()).hexdigest()
  for item in (self.snap['sources'][1],self.snap['source_lineage_assets'][1],self.sources[1]):item['sha256']=h;item['size_bytes']=f.stat().st_size
  self.snap['features'][1]['geometry_sha256']=hashlib.sha256(json.dumps(g,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 def test_country_partial_group_full_excludes_partial(self):
  self.prepare();self.set_group_bounds(-105,120);self.policy=polygon_policy.adapt(self.snap,{'a'});c=self.runv()['claims'][0];self.assertEqual(c['component_ids'],[10]);self.assertIn(11,[x['component_id_evidence_only'] for x in c['containment']['administrative']['excluded_partial_components']]);self.assertEqual(c['containment']['geographic_group']['excluded_partial_count'],0)
 def test_two_fully_covered_disjoint_sets_fail(self):
  self.prepare();self.set_group_bounds(4,120);raw=self.file.read_text().replace('lon="40"','lon="4"');self.file.write_text(raw);h=hashlib.sha256(self.file.read_bytes()).hexdigest()
  for item in (self.snap['sources'][0],self.snap['source_lineage_assets'][0],self.sources[0]):item['sha256']=h;item['size_bytes']=self.file.stat().st_size
  g={'type':'MultiPolygon','coordinates':[[[[-105.,55.],[4.,55.],[4.,89.],[-105.,89.],[-105.,55.]]]]};self.snap['features'][0]['geometry_sha256']=hashlib.sha256(json.dumps(g,sort_keys=True,separators=(',',':')).encode()).hexdigest();self.policy=polygon_policy.adapt(self.snap,{'a'})
  with self.assertRaisesRegex(ValueError,'empty two-source containment'):self.runv()
 def test_country_full_group_partial_excludes_partial(self):
  self.prepare();self.set_group_bounds(-105,40);raw=self.file.read_text().replace('lon="40"','lon="120"').replace('<way id="10">','<node id="98" lon="0" lat="55"/><node id="99" lon="0" lat="89"/><way id="10">').replace('<nd ref="1"/><nd ref="2"/>','<nd ref="1"/><nd ref="98"/><nd ref="2"/>').replace('<nd ref="3"/><nd ref="4"/>','<nd ref="3"/><nd ref="99"/><nd ref="4"/>');self.file.write_text(raw);h=hashlib.sha256(self.file.read_bytes()).hexdigest()
  for item in (self.snap['sources'][0],self.snap['source_lineage_assets'][0],self.sources[0]):item['sha256']=h;item['size_bytes']=self.file.stat().st_size
  g={'type':'MultiPolygon','coordinates':[[[[-105.,55.],[0.,55.],[120.,55.],[120.,89.],[0.,89.],[-105.,89.],[-105.,55.]]]]};self.snap['features'][0]['geometry_sha256']=hashlib.sha256(json.dumps(g,sort_keys=True,separators=(',',':')).encode()).hexdigest();self.policy=polygon_policy.adapt(self.snap,{'a'});c=self.runv()['claims'][0];self.assertEqual(c['component_ids'],[10]);self.assertEqual(c['containment']['administrative']['excluded_partial_count'],0);self.assertIn(11,[x['component_id_evidence_only'] for x in c['containment']['geographic_group']['excluded_partial_components']])
class AdminOutputExtentTests(ResolveTests):
 def test_dual_extent_tamper_fails(self):
  from apply_selected_mixed import validate_admin_group_extent
  method='osm_admin_group_containment_v1';valid=[{'inside_cells':3,'outside_cells':0},{'inside_cells':3,'outside_cells':0}];validate_admin_group_extent(method,valid,3)
  for per in [valid[:1],[valid[0],{'inside_cells':2,'outside_cells':1}],[valid[0],{'inside_cells':0,'outside_cells':0}]]:
   with self.assertRaisesRegex(ValueError,'dual-source whole-component extent mismatch'):validate_admin_group_extent(method,per,3)
class AdminTerritoryLevel3Tests(AdminGroupTests):
 def prepare_level3(self, nested=True):
  self.prepare();raw=self.file.read_text().replace('<relation id="20"',('<relation id="21" version="1"/>' if nested else '')+'<relation id="20"').replace('<member type="node" ref="5" role="label"/>','<member type="node" ref="5" role="label"/><member type="relation" ref="21" role="land_area"/>').replace('<tag k="admin_level" v="2"/>','<tag k="admin_level" v="3"/><tag k="border_type" v="territorial"/>');self.file.write_text(raw);h=hashlib.sha256(self.file.read_bytes()).hexdigest()
  for item in (self.snap['sources'][0],self.snap['source_lineage_assets'][0],self.sources[0]):item['sha256']=h;item['size_bytes']=self.file.stat().st_size
  tags=self.snap['affiliations'][0]['evidence']['selector']['expected_identity_tags'];tags['admin_level']='3';tags['border_type']='territorial';self.policy=polygon_policy.adapt(self.snap,{'a'})
 def test_level3_territorial_full_resolution(self):
  self.prepare_level3();c=self.runv()['claims'][0];self.assertEqual(c['component_ids'],[10]);self.assertEqual(c['entity_code'],19)
 def test_level3_wrong_border_tag_fails(self):
  self.prepare_level3();tags=self.snap['affiliations'][0]['evidence']['selector']['expected_identity_tags'];tags['border_type']='maritime'
  with self.assertRaisesRegex(ValueError,'invalid administrative group selector'):polygon_policy.adapt(self.snap,{'a'})
 def test_level3_missing_land_area_member_fails(self):
  self.prepare_level3(nested=False)
  with self.assertRaisesRegex(ValueError,'missing metadata member'):self.runv()
 def test_level2_land_area_fails(self):
  self.prepare_level3();raw=self.file.read_text().replace('<tag k="admin_level" v="3"/>','<tag k="admin_level" v="2"/>');self.file.write_text(raw);h=hashlib.sha256(self.file.read_bytes()).hexdigest()
  for item in (self.snap['sources'][0],self.snap['source_lineage_assets'][0],self.sources[0]):item['sha256']=h;item['size_bytes']=self.file.stat().st_size
  tags=self.snap['affiliations'][0]['evidence']['selector']['expected_identity_tags'];tags['admin_level']='2';tags.pop('border_type');self.policy=polygon_policy.adapt(self.snap,{'a'})
  with self.assertRaisesRegex(ValueError,'unsupported geometric or metadata member'):self.runv()
 def test_wrong_nonempty_level3_identity_fails(self):
  self.prepare_level3();tags=self.snap['affiliations'][0]['evidence']['selector']['expected_identity_tags'];tags['ISO3166-1:alpha2']='ZZ';self.policy=polygon_policy.adapt(self.snap,{'a'})
  with self.assertRaisesRegex(ValueError,'identity tags mismatch'):self.runv()

 def test_direct_extractor_rejects_nonterritorial_level3_without_land_area(self):
  import importlib.util
  self.prepare_level3();raw=self.file.read_text().replace('<tag k="border_type" v="territorial"/>','').replace('<member type="relation" ref="21" role="land_area"/>','');self.file.write_text(raw);digest=hashlib.sha256(self.file.read_bytes()).hexdigest();path=Path(__file__).resolve().parent.parent/'osm-relation-adapter-20261104/osm_admin_envelope_v1.py';spec=importlib.util.spec_from_file_location('direct_admin_test',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  with self.assertRaisesRegex(ValueError,'named country administrative boundary required'):module.read_graph(self.file,20,4,expected_source_sha256=digest)
