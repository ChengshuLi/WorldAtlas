import unittest
from pathlib import Path
import resolve,adapter
from test_osm_integration import OSMIntegrationTests
from test_resolve import put
class GroupIntegrationTests(OSMIntegrationTests):
 def group_fixture(self):
  d,_=self.osm_fixture();xml=b'<osm version="0.6"><node id="123" version="2" visible="true" lat="22.5" lon="-112.5"><tag k="name" v="Test island"/><tag k="place" v="island"/></node></osm>';point=put(self.p/'point.json',xml);self.req['source_files'][0].update(point)
  geom={'type':'Polygon','coordinates':[[[-150,0],[-80,0],[-80,45],[-150,45],[-150,0]]]};identity={'type':'FeatureCollection','features':[{'type':'Feature','properties':{'NE_ID':8,'NAME':'TEST GROUP','FEATURECLA':'Island group'},'geometry':geom}]};ip=put(self.p/'identity.txt',identity);self.req['source_files'][1].update(ip)
  for row in d['sources']+d['source_lineage_assets']:
   pin=point if row['source_id']=='p' else ip;row['sha256']=pin['sha256'];row['size_bytes']=Path(pin['path']).stat().st_size
  a=d['affiliations'][0];a['method']='osm_api_island_node_group_component_v1';s=a['evidence']['selector'];s.pop('island_identity');s.pop('point_name');s.update(island_name='Test island',group_identity='Test group',identity_scope='island_group',identity_class_value='Island group',place_tag='island')
  self.req['snapshot']=put(self.p/'combined.json',d);return d
 def test_group_end_to_end(self):
  self.group_fixture();r=resolve.resolve(self.req);c=r['claims'][0];self.assertEqual(c['component_id'],7);self.assertEqual(c['island_identity'],'Test island');self.assertEqual(c['group_identity'],'Test group');self.assertEqual(c['identity_scope'],'island_group');self.assertEqual(c['identity_check']['identity_feature_name'],'TEST GROUP');self.assertEqual(c['osm_node_extraction']['verified_tags'],{'name':'Test island','place':'island'});self.assertTrue(c['identity_check']['strict_contains'])
 def test_v3_group_source_resolution(self):
  d=self.group_fixture();d['schema']='worldatlas-geography-decision-draft-evidence-v3';d['polygon_corroboration_refs']=[];d['ecoregion_source_refs']=[];d['unsupported_affiliation_source_ref_table_present']=False;d['unsupported_point_methods_present']=False;self.req['snapshot']=put(self.p/'combined.json',d);r=resolve.resolve(self.req);self.assertEqual(r['claims'][0]['component_id'],7)
 def test_v2_group_source_resolution(self):
  d=self.group_fixture();d['schema']='worldatlas-geography-decision-draft-evidence-v2';d['polygon_corroboration_refs']=[];self.req['snapshot']=put(self.p/'combined.json',d);r=resolve.resolve(self.req);self.assertEqual(r['claims'][0]['component_id'],7)
  del d['polygon_corroboration_refs'];self.req['snapshot']=put(self.p/'combined.json',d)
  with self.assertRaisesRegex(ValueError,'corroboration refs'):resolve.resolve(self.req)
 def test_scope_class_place_fail_closed(self):
  for k,v in [('identity_scope','island'),('identity_class_value','Island'),('place_tag','town')]:
   d=self.group_fixture();d['affiliations'][0]['evidence']['selector'][k]=v;self.req['snapshot']=put(self.p/'combined.json',d)
   with self.assertRaisesRegex(ValueError,'invalid island group scope or class'):resolve.resolve(self.req)
 def test_wrong_group_fails(self):
  d=self.group_fixture();d['affiliations'][0]['evidence']['selector']['group_identity']='Other group';self.req['snapshot']=put(self.p/'combined.json',d)
  with self.assertRaises(ValueError):resolve.resolve(self.req)
 def test_wrong_island_node_fails(self):
  d=self.group_fixture();d['affiliations'][0]['evidence']['selector']['island_name']='Another island';self.req['snapshot']=put(self.p/'combined.json',d)
  with self.assertRaisesRegex(ValueError,'node tags mismatch'):resolve.resolve(self.req)
 def test_no_unbounded_satellites(self):
  self.group_fixture();r=resolve.resolve(self.req);self.assertEqual(len(r['claims']),1);self.assertEqual(r['claims'][0]['component_id'],7);self.assertNotIn('component_ids',r['claims'][0])
 def test_group_and_polygon_fk_coexist(self):
  import sys
  sys.path.insert(0,str(Path(resolve.__file__).resolve().parents[2]/'stage3-land-overrides-20261104'));import polygon_policy
  d=self.group_fixture();src={'source_id':'poly','version':'1','sha256':'a'*64,'r2_bucket':'bucket','r2_key':'poly','size_bytes':10};asset=dict(src,source_uri='https://example.org/poly',attribution='provider',license_name='test',license_uri='https://example.org/license',provider='provider',title='poly',kind='raw',provenance={'representation':'provider_original'});d['sources'].append(src);d['source_lineage_assets'].append(asset)
  for name in ('poly-main','poly-extra'):d['features'].append({'feature_id':name,'source_id':'poly','source_version':'1','source_feature_id':name,'geometry_sha256':'b'*64,'evidence':{'selector_property':'id'}})
  d['affiliations'].append({'affiliation_id':'poly-rule','decision_revision':'draft-1','method':'component_intersection_v1','scope':'land','relationship':'affiliation','entity_id':42,'feature_id':'poly-main','evidence':{'execution_status':'selected_for_research','selector':{'additional_feature_ids':['poly-extra'],'include_witnesses':[],'exclude_witnesses':[]}}});d['polygon_affiliation_feature_refs']=[{'affiliation_id':'poly-rule','role':'additional_polygon','feature_id':'poly-extra'}]
  self.assertEqual(adapter.adapt(d)['decisions'][0]['method'],'osm_api_island_node_group_component_v1');self.assertEqual(len(polygon_policy.adapt(d,{'poly-rule'})['decisions']),1)
  d['polygon_affiliation_feature_refs'][0]['feature_id']='missing'
  with self.assertRaisesRegex(ValueError,'orphan'):polygon_policy.adapt(d,{'poly-rule'})
if __name__=='__main__':unittest.main()
