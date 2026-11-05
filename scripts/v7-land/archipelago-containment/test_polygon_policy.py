import copy,unittest
from polygon_policy import adapt
class TestPolygonPolicy(unittest.TestCase):
 def setUp(self):
  src={'source_id':'raw','version':'v','sha256':'a'*64,'r2_bucket':'bucket','r2_key':'key','size_bytes':10}
  asset={**src,'kind':'raw','provenance':{'representation':'provider_original'},'source_uri':'https://example.com/source','attribution':'provider','license_name':'license','license_uri':'https://example.com/license','provider':'p'}
  def feature(i):return {'feature_id':i,'source_id':'raw','source_version':'v','source_feature_id':i,'geometry_sha256':'b'*64,'evidence':{'selector_property':'id'}}
  self.s={'source':'neon-export','schema':'worldatlas-geography-decision-draft-evidence-v1','decision_revision':{'id':'r','status':'draft'},'sources':[src],'source_lineage_assets':[asset],'source_lineage_dependencies':[],'features':[feature('p'),feature('q')],'affiliations':[{'affiliation_id':'a','decision_revision':'r','scope':'land','relationship':'affiliation','method':'component_intersection_v1','entity_id':3,'feature_id':'p','evidence':{'execution_status':'selected_for_research','selector':{'additional_feature_ids':['q'],'include_witnesses':[{'lon':'1','lat':'2'}],'exclude_witnesses':[]}}}],'polygon_affiliation_feature_refs':[{'affiliation_id':'a','role':'additional_polygon','feature_id':'q'}]}
 def test_v3_rejects_unsupported_source_flags(self):
  self.s.update(schema='worldatlas-geography-decision-draft-evidence-v3',polygon_corroboration_refs=[],ecoregion_source_refs=[],unsupported_affiliation_source_ref_table_present=False,unsupported_point_methods_present=False,affiliation_source_refs=[]);adapt(self.s,{'a'})
  for key in ('unsupported_affiliation_source_ref_table_present','unsupported_point_methods_present'):
   self.s[key]=True
   with self.assertRaisesRegex(ValueError,'unsupported affiliation-source table status'):adapt(self.s,{'a'})
   self.s[key]=False
 def test_versioned_corroboration_schema(self):
  self.s['affiliations'][0]['evidence']['polygon_corroboration_mode']='administrative_geometry_v1'
  with self.assertRaisesRegex(ValueError,'schema or corroboration refs'):adapt(self.s,{'a'})
  self.s['schema']='worldatlas-geography-decision-draft-evidence-v2'
  with self.assertRaisesRegex(ValueError,'schema or corroboration refs'):adapt(self.s,{'a'})
  self.s['polygon_corroboration_refs']=[];adapt(self.s,{'a'})
 def test_selected(self):
  v=adapt(self.s,{'a'});self.assertEqual(len(v['decisions'][0]['features']),2);self.assertEqual(v['status'],'requires-source-resolution')
 def test_fk_missing(self):
  self.s['polygon_affiliation_feature_refs']=[]
  with self.assertRaisesRegex(ValueError,'FK/selector'):adapt(self.s,{'a'})
 def test_orphan(self):
  self.s['polygon_affiliation_feature_refs'][0]['affiliation_id']='other'
  with self.assertRaisesRegex(ValueError,'orphan'):adapt(self.s,{'a'})
 def test_derived_source(self):
  self.s['source_lineage_dependencies']=[{'source_id':'raw','version':'v'}]
  with self.assertRaisesRegex(ValueError,'derived'):adapt(self.s,{'a'})
 def test_preserved_eea_query_is_truthfully_supported(self):
  a=self.s['source_lineage_assets'][0];a.update(provider='European Environment Agency',source_uri='https://bio.discomap.eea.europa.eu/arcgis/rest/query',provenance={'source_kind':'preserved direct GeoJSON query response, not full EEA dataset','r2_readback':'verified'})
  self.assertEqual(adapt(self.s,{'a'})['source_pins'][0]['validated_representation'],'preserved_official_eea_query_response')
  a['source_uri']='https://other.example/query'
  with self.assertRaisesRegex(ValueError,'provenance'):adapt(self.s,{'a'})
 def test_bad_witness(self):
  self.s['affiliations'][0]['evidence']['selector']['include_witnesses']=[{'lon':'NaN','lat':'0'}]
  with self.assertRaisesRegex(ValueError,'outside'):adapt(self.s,{'a'})
 def test_stale_revision(self):
  self.s['affiliations'][0]['decision_revision']='old'
  with self.assertRaisesRegex(ValueError,'invalid polygon affiliation'):adapt(self.s,{'a'})
 def test_osm_relation_source(self):
  a=self.s['affiliations'][0];a['method']='osm_relation_component_intersection_v1';a['evidence']['selector']={'additional_feature_ids':[],'include_witnesses':[],'exclude_witnesses':[],'relation_version':'53','extractor_version':'osm-multipolygon-outer-v2'};self.s['polygon_affiliation_feature_refs']=[];f=self.s['features'][0];f['source_feature_id']='4263184';f['evidence']={'source_format':'osm-xml','relation_version':'53','geometry_hash_method':'binary64-sorted-compact-geojson-v1'}
  result=adapt(self.s,{'a'});self.assertEqual(result['decisions'][0]['features'][0]['relation_version'],'53')
  f['evidence']['relation_version']='52'
  with self.assertRaisesRegex(ValueError,'OSM feature/source mismatch'):adapt(self.s,{'a'})
 def test_v3_island_identity_required(self):
  a=self.s['affiliations'][0];a['method']='osm_relation_component_intersection_v1';a['evidence']['selector']={'additional_feature_ids':[],'include_witnesses':[],'exclude_witnesses':[],'relation_version':'53','extractor_version':'osm-multipolygon-outer-v3','expected_identity_tags':{'name':'Lombok','place':'island'}};self.s['polygon_affiliation_feature_refs']=[];f=self.s['features'][0];f['source_feature_id']='4263184';f['evidence']={'source_format':'osm-xml','relation_version':'53','geometry_hash_method':'binary64-sorted-compact-geojson-v1'}
  self.assertEqual(adapt(self.s,{'a'})['decisions'][0]['features'][0]['expected_identity_tags']['name'],'Lombok');a['evidence']['selector']['expected_identity_tags']['place']='town'
  with self.assertRaisesRegex(ValueError,'invalid expected island identity'):adapt(self.s,{'a'})
 def test_v4_alias_supported_and_v3_forbids_alias(self):
  a=self.s['affiliations'][0];a['method']='osm_relation_component_intersection_v1';a['evidence']['selector']={'additional_feature_ids':[],'include_witnesses':[],'exclude_witnesses':[],'relation_version':'53','extractor_version':'osm-multipolygon-outer-v4','expected_identity_tags':{'name':'Pulau Kekeh','alt_name':'Pulau Kekik','place':'island'}};self.s['polygon_affiliation_feature_refs']=[];f=self.s['features'][0];f['source_feature_id']='4263184';f['evidence']={'source_format':'osm-xml','relation_version':'53','geometry_hash_method':'binary64-sorted-compact-geojson-v1'}
  self.assertEqual(adapt(self.s,{'a'})['decisions'][0]['features'][0]['expected_identity_tags']['alt_name'],'Pulau Kekik');a['evidence']['selector']['extractor_version']='osm-multipolygon-outer-v3'
  with self.assertRaisesRegex(ValueError,'invalid expected island identity'):adapt(self.s,{'a'})
 def test_unspecified_reuse_is_explicit_not_fabricated(self):
  a=self.s['source_lineage_assets'][0];a['license_name']='Unspecified';a['license_uri']=None;a['provenance']['reuse_terms']='unspecified';result=adapt(self.s,{'a'});self.assertIsNone(result['source_pins'][0]['license_uri']);del a['provenance']['reuse_terms']
  with self.assertRaisesRegex(ValueError,'unspecified reuse terms'):adapt(self.s,{'a'})
 def test_unspecified_nonempty_uri_requires_nonlicense_role(self):
  a=self.s['source_lineage_assets'][0];a['license_name']='Reuse terms unspecified; user directed proceeding';a['provenance']['reuse_terms']='not established; no redistribution license is asserted';a['license_uri']='https://example.com/docs'
  with self.assertRaisesRegex(ValueError,'documentation role'):adapt(self.s,{'a'})
  a['provenance']['terms_uri_role']='Service documentation, not an asserted redistribution license.';result=adapt(self.s,{'a'});self.assertEqual(result['source_pins'][0]['license_uri_role'],a['provenance']['terms_uri_role'])
 def test_unspecified_rejects_contradictory_terms(self):
  a=self.s['source_lineage_assets'][0];a['license_name']='Unspecified';a['license_uri']=None;a['provenance']['reuse_terms']='approved for redistribution'
  with self.assertRaisesRegex(ValueError,'unspecified reuse terms'):adapt(self.s,{'a'})
 def test_source_provenance_and_decision_limitations_preserved(self):
  a=self.s['affiliations'][0];a['evidence']['limitations']=['Only current source is known'];src=self.s['source_lineage_assets'][0];src['provenance'].update(source_query_identity='ID only in URI',historical_v7_equivalence='not established',origin='direct response');r=adapt(self.s,{'a'});self.assertEqual(r['decisions'][0]['decision_limitations'],['Only current source is known']);self.assertEqual(r['source_pins'][0]['source_query_identity'],'ID only in URI');self.assertEqual(r['source_pins'][0]['historical_v7_equivalence'],'not established');a['evidence']['limitations']=['ok',None]
  with self.assertRaisesRegex(ValueError,'invalid decision limitations'):adapt(self.s,{'a'})
 def test_anchored_archipelago_policy_and_fail_closed(self):
  a=self.s['affiliations'][0];a['method']='osm_archipelago_anchored_rings_intersection_v1';anchor={'node_id':'2','node_version':'3','way_id':'10','expected_tags':{'name:en':'ExampleAnchor','amenity':'ferry_terminal'},'geometry_sha256':'c'*64};a['evidence']['selector']={'additional_feature_ids':[],'include_witnesses':[],'exclude_witnesses':[],'relation_version':'13','extractor_version':'osm-anchored-outer-rings-v1','expected_identity_tags':{'name':'ExampleArchipelago','place':'archipelago'},'anchors':[anchor]};self.s['polygon_affiliation_feature_refs']=[];f=self.s['features'][0];f['source_feature_id']='20';f['evidence']={'source_format':'osm-xml','relation_version':'13','geometry_hash_method':'binary64-sorted-compact-geojson-v1'};self.s['source_lineage_assets'][0]['source_uri']='https://api.openstreetmap.org/api/0.6/relation/20/full';r=adapt(self.s,{'a'});self.assertEqual(r['decisions'][0]['features'][0]['anchors'],[anchor]);a['evidence']['selector']['anchors'].append(copy.deepcopy(anchor))
  with self.assertRaisesRegex(ValueError,'duplicate anchor'):adapt(self.s,{'a'})
  a['evidence']['selector']['anchors']=[anchor];self.s['source_lineage_assets'][0]['source_uri']='https://example.com/source'
  with self.assertRaisesRegex(ValueError,'official source URI'):adapt(self.s,{'a'})
  self.s['source_lineage_assets'][0]['source_uri']='https://api.openstreetmap.org/api/0.6/relation/20/full';anchor['expected_tags']={'name:en':'ExampleAnchor'}
  with self.assertRaisesRegex(ValueError,'invalid anchor tags'):adapt(self.s,{'a'})
if __name__=='__main__':unittest.main()
