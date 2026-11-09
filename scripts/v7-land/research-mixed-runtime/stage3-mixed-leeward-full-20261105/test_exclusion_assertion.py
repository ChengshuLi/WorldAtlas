import copy
import unittest

import polygon_policy


class AssertionTests(unittest.TestCase):
 def setUp(self):
  witness = {'lon': '27.9', 'lat': '36.1'}
  anchor = {'node_id': '2', 'node_version': '3', 'way_id': '4',
            'expected_tags': {'name': 'Harbor', 'amenity': 'ferry_terminal'},
            'geometry_sha256': 'c' * 64}

  def source(source_id, uri):
   raw = {'source_id': source_id, 'version': 'v', 'sha256': 'a' * 64,
          'r2_bucket': 'bucket', 'r2_key': source_id, 'size_bytes': 10}
   asset = {**raw, 'kind': 'raw', 'source_uri': uri, 'provider': 'provider',
            'license_name': 'license', 'license_uri': 'https://example.com/license',
            'attribution': 'provider', 'provenance': {'representation': 'provider_original'}}
   return raw, asset

  def feature(feature_id, source_id, source_feature_id, evidence):
   return {'feature_id': feature_id, 'source_id': source_id, 'source_version': 'v',
           'source_feature_id': source_feature_id, 'geometry_sha256': 'b' * 64,
           'evidence': evidence}

  def affiliation(affiliation_id, method, feature_id, selector):
   return {'affiliation_id': affiliation_id, 'decision_revision': 'r', 'scope': 'land',
           'relationship': 'affiliation', 'entity_id': 3, 'method': method,
           'feature_id': feature_id, 'evidence': {'execution_status': 'selected_for_research',
                                                  'selector': selector}}

  raw, asset = source('polygon', 'https://example.com/source')
  osm_raw, osm_asset = source('osm', 'https://api.openstreetmap.org/api/0.6/relation/5/full')
  polygon = feature('polygon', 'polygon', 'p', {'selector_property': 'id'})
  anchored_ring = feature('anchor-ring', 'osm', '5', {
      'source_format': 'osm-xml', 'relation_version': '1',
      'geometry_hash_method': 'binary64-sorted-compact-geojson-v1'})
  selector = {'additional_feature_ids': [], 'include_witnesses': [], 'exclude_witnesses': []}
  self.reference = affiliation('anchor', 'osm_archipelago_anchored_rings_intersection_v1', 'anchor-ring', {
      **selector, 'relation_version': '1', 'extractor_version': 'osm-anchored-outer-rings-v1',
      'expected_identity_tags': {'name': 'Archipelago', 'place': 'archipelago'}, 'anchors': [anchor]})
  self.a = affiliation('polygon', 'component_intersection_v1', 'polygon',
                       {**selector, 'exclude_witnesses': [copy.deepcopy(witness)]})
  self.a['evidence']['exclusion_witness_evidence'] = {
      'source_affiliation_id': 'anchor', 'relation_id': '5', 'anchor_node_id': anchor['node_id'],
      'anchor_node_version': anchor['node_version'], 'outer_way_id': anchor['way_id'],
      'ring_geometry_sha256': anchor['geometry_sha256'], 'method': 'PointOnSurface',
      'proof_sha256': 'd' * 64, 'limitation': 'Fixed coordinate', 'witness': witness}
  self.snapshot = {
      'source': 'neon-export', 'schema': 'worldatlas-geography-decision-draft-evidence-v1',
      'decision_revision': {'id': 'r', 'status': 'draft'}, 'sources': [raw, osm_raw],
      'source_lineage_assets': [asset, osm_asset], 'source_lineage_dependencies': [],
      'features': [polygon, anchored_ring], 'affiliations': [self.a, self.reference]}
  self.ids = {'polygon', 'anchor'}

 def adapt(self):return polygon_policy.adapt(self.snapshot,self.ids)
 def test_valid_assertion_is_labelled_and_preserved(self):
  d=next(x for x in self.adapt()['decisions'] if x['affiliation_id']==self.a['affiliation_id']);a=d['exclusion_witness_assertion'];self.assertEqual(a['kind'],'selected_assertion_not_recomputed');self.assertEqual(a['witness'],self.a['evidence']['selector']['exclude_witnesses'][0])
 def test_wrong_coordinate_rejected(self):
  self.a['evidence']['exclusion_witness_evidence']['witness']['lat']='1'
  with self.assertRaisesRegex(ValueError,'assertion witness'):self.adapt()
 def test_wrong_ring_rejected(self):
  self.a['evidence']['exclusion_witness_evidence']['ring_geometry_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'anchor mismatch'):self.adapt()
 def test_wrong_affiliation_revision_rejected(self):
  self.reference['decision_revision']='old'
  with self.assertRaisesRegex(ValueError,'invalid (polygon|selected anchor) affiliation'):self.adapt()
 def test_missing_field_rejected(self):
  del self.a['evidence']['exclusion_witness_evidence']['proof_sha256']
  with self.assertRaisesRegex(ValueError,'invalid exclusion witness assertion'):self.adapt()
 def test_reference_must_be_selected(self):
  self.ids.remove('anchor')
  with self.assertRaisesRegex(ValueError,'invalid selected anchor affiliation'):self.adapt()
if __name__=='__main__':unittest.main()
