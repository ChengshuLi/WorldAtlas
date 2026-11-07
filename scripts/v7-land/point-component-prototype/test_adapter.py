# Synthetic fixtures only; no project geographic records.
import copy,unittest
import adapter

def fixture():
 sources=[{'source_id':'point','version':'v1','sha256':'1'*64,'r2_bucket':'b','r2_key':'p','size_bytes':10},{'source_id':'identity','version':'v1','sha256':'2'*64,'r2_bucket':'b','r2_key':'i','size_bytes':20}]
 assets=[dict(x,source_uri='https://example.org/'+x['source_id'],attribution='author',license_name='test',license_uri='https://example.org/license',provider='provider',title='title',kind='raw',provenance={'representation':'provider_original'}) for x in sources]
 return {'schema':'worldatlas-geography-decision-draft-evidence-v1','source':'neon-export','decision_revision':{'id':'r','entity_revision':'e','status':'draft'},'entity_revision':{'id':'e','status':'draft'},'sources':sources,'source_lineage_assets':assets,'source_lineage_dependencies':[],'features':[{'feature_id':'f','source_id':'point','source_version':'v1','source_feature_id':'3','geometry_sha256':'3'*64}],'affiliations':[{'affiliation_id':'a','method':'source_point_component_v1','scope':'land','relationship':'affiliation','rationale':'reviewed rationale','feature_id':'f','entity_id':42,'evidence':{'execution_status':'selected_for_research','selector':{'island_identity':'Example','point_name':'Place','id_property':'id'}}}],'affiliation_source_refs':[{'affiliation_id':'a','role':'identity_evidence','source_id':'identity','source_version':'v1'}],'entities':[{'id':42,'name':'Example continent'}],'category_bindings':[{'entity_id':42,'physical_class':'land','code':18}]}
class AdapterTests(unittest.TestCase):
 def setUp(self):self.d=fixture()
 def test_valid(self):
  out=adapter.adapt(self.d);self.assertEqual(out['source'],'derived-from-neon-export');self.assertEqual(out['decisions'][0]['affiliation_id'],'a');self.assertEqual(out['target_entities'][0]['code'],18);self.assertEqual(len(out['sources']),2)
 def test_revision_mismatch(self):
  self.d['entity_revision']['id']='other'
  with self.assertRaisesRegex(ValueError,'revision mismatch'):adapter.adapt(self.d)
 def test_missing_ref(self):
  self.d['affiliation_source_refs']=[]
  with self.assertRaisesRegex(ValueError,'identity source missing'):adapter.adapt(self.d)
 def test_duplicate_ref(self):
  self.d['affiliation_source_refs']*=2
  with self.assertRaisesRegex(ValueError,'duplicate'):adapter.adapt(self.d)
 def test_wrong_ref_role(self):
  self.d['affiliation_source_refs'][0]['role']='other'
  with self.assertRaisesRegex(ValueError,'unsupported source role'):adapter.adapt(self.d)
 def test_unselected(self):
  self.d['affiliations'][0]['evidence']['execution_status']='pending'
  with self.assertRaisesRegex(ValueError,'unselected'):adapter.adapt(self.d)
 def test_missing_selector(self):
  del self.d['affiliations'][0]['evidence']['selector']['island_identity']
  with self.assertRaisesRegex(ValueError,'selector'):adapter.adapt(self.d)
 def test_feature_missing(self):
  self.d['features']=[]
  with self.assertRaisesRegex(ValueError,'point feature missing'):adapter.adapt(self.d)
 def test_duplicate_feature(self):
  self.d['features']*=2
  with self.assertRaisesRegex(ValueError,'duplicate identity'):adapter.adapt(self.d)
 def test_sources_identical(self):
  self.d['affiliation_source_refs'][0]['source_id']='point'
  with self.assertRaisesRegex(ValueError,'identical'):adapter.adapt(self.d)
 def test_catalog_key_mismatch(self):
  self.d['source_lineage_assets'][0]['r2_key']='different'
  with self.assertRaisesRegex(ValueError,'custody mismatch'):adapter.adapt(self.d)
 def test_bad_target(self):
  self.d['category_bindings'][0]['code']=1
  with self.assertRaisesRegex(ValueError,'invalid point target'):adapter.adapt(self.d)
 def test_source_without_license(self):
  del self.d['source_lineage_assets'][0]['license_name']
  with self.assertRaisesRegex(ValueError,'license missing'):adapter.adapt(self.d)
 def test_orphan_ref(self):
  self.d['affiliation_source_refs'][0]['affiliation_id']='none'
  with self.assertRaisesRegex(ValueError,'orphan'):adapter.adapt(self.d)
 def test_mixed_method_refs_allowed(self):
  self.d['affiliations'].append({'affiliation_id':'polygon','method':'component_intersection_v1'})
  self.assertEqual(len(adapter.adapt(self.d)['decisions']),1)
 def test_mixed_method_duplicate_refs_rejected(self):
  self.d['affiliations'].append({'affiliation_id':'polygon','method':'component_intersection_v1'});ref={'affiliation_id':'polygon','role':'boundary_source','source_id':'identity','source_version':'v1'};self.d['affiliation_source_refs'].extend([ref,ref])
  with self.assertRaisesRegex(ValueError,'unsupported source role'):adapter.adapt(self.d)
 def test_extra_selector_rejected(self):
  self.d['affiliations'][0]['evidence']['selector']['extra']='x'
  with self.assertRaisesRegex(ValueError,'unsupported keys'):adapter.adapt(self.d)
 def test_derived_source_rejected(self):
  self.d['source_lineage_assets'][0]['kind']='derived';self.d['source_lineage_assets'][0]['provenance']={'representation':'derived'}
  with self.assertRaisesRegex(ValueError,'provider-original raw'):adapter.adapt(self.d)
 def test_raw_source_with_parent_rejected(self):
  self.d['source_lineage_dependencies']=[{'source_id':'point','version':'v1','parent_source_id':'original','parent_version':'v1'}]
  with self.assertRaisesRegex(ValueError,'raw source may not'):adapter.adapt(self.d)
 def test_source_size_mismatch(self):
  self.d['source_lineage_assets'][0]['size_bytes']=99
  with self.assertRaisesRegex(ValueError,'size or license'):adapter.adapt(self.d)
 def named_fixture(self):
  a=self.d['affiliations'][0];a['method']='source_point_named_region_component_v1';a['evidence']['selector'].update({'identity_id_property':'NE_ID','identity_name_property':'NAME','identity_class_property':'FEATURECLA','identity_class_value':'Island'})
  self.d['features'].append({'feature_id':'identity-feature','source_id':'identity','source_version':'v1','source_feature_id':'8','geometry_sha256':'4'*64});self.d['affiliation_source_refs']=[];self.d['affiliation_feature_refs']=[{'affiliation_id':'a','role':'identity_polygon','feature_id':'identity-feature'}]
 def test_named_identity_valid(self):
  self.named_fixture();out=adapter.adapt(self.d);self.assertEqual(out['decisions'][0]['identity_source_feature_id'],'8');self.assertEqual(out['decisions'][0]['method'],'source_point_named_region_component_v1')
 def test_named_identity_wrong_role(self):
  self.named_fixture();self.d['affiliation_feature_refs'][0]['role']='wrong'
  with self.assertRaisesRegex(ValueError,'unsupported feature reference'):adapter.adapt(self.d)
 def test_named_identity_duplicate_ref(self):
  self.named_fixture();self.d['affiliation_feature_refs']*=2
  with self.assertRaisesRegex(ValueError,'duplicate'):adapter.adapt(self.d)
 def test_named_identity_missing_feature(self):
  self.named_fixture();self.d['affiliation_feature_refs']=[]
  with self.assertRaisesRegex(ValueError,'identity polygon feature missing'):adapter.adapt(self.d)
 def test_no_points(self):
  self.d['affiliations']=[];self.d['affiliation_source_refs']=[]
  with self.assertRaisesRegex(ValueError,'no selected point'):adapter.adapt(self.d)
if __name__=='__main__':unittest.main()
