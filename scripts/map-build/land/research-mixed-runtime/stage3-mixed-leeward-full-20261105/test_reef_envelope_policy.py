import hashlib,json
from test_polygon_resolution import ResolveTests
import polygon_policy
class ReefPolicyTests(ResolveTests):
 def prepare(self):
  raw='''<osm><node id="1" lon="-105" lat="55"/><node id="2" lon="40" lat="55"/><node id="3" lon="40" lat="89"/><node id="4" lon="-105" lat="89"/><node id="5" lon="-10" lat="60"/><node id="6" lon="-5" lat="60"/><node id="7" lon="-5" lat="65"/><node id="8" lon="-10" lat="65"/><way id="10"><nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="1"/></way><way id="11"><nd ref="5"/><nd ref="6"/><nd ref="7"/><nd ref="8"/><nd ref="5"/></way><relation id="20" version="4"><member type="way" ref="10" role="outer"/><member type="way" ref="11" role="inner"/><tag k="type" v="multipolygon"/><tag k="natural" v="reef"/><tag k="name" v="Demo"/></relation></osm>''';self.file.write_text(raw);h=hashlib.sha256(self.file.read_bytes()).hexdigest()
  for x in (self.snap['sources'][0],self.snap['source_lineage_assets'][0],self.sources[0]):x['sha256']=h;x['size_bytes']=self.file.stat().st_size
  self.snap['source_lineage_assets'][0].update(source_uri='https://api.openstreetmap.org/api/0.6/relation/20/full',provider='OpenStreetMap contributors',license_name='ODbL 1.0',attribution='© OpenStreetMap contributors')
  g={'type':'MultiPolygon','coordinates':[[[[-105.,55.],[40.,55.],[40.,89.],[-105.,89.],[-105.,55.]]]]};self.snap['features'][0].update(source_feature_id='20',geometry_sha256=hashlib.sha256(json.dumps(g,sort_keys=True,separators=(',',':')).encode()).hexdigest(),evidence={'source_format':'osm-xml','relation_version':'4','geometry_hash_method':'binary64-sorted-compact-geojson-v1'})
  a=self.snap['affiliations'][0];a['method']='osm_reef_envelope_component_containment_v1';a['evidence']['selector']={'additional_feature_ids':[],'include_witnesses':[],'exclude_witnesses':[],'relation_version':'4','extractor_version':'osm-reef-envelope-v1','expected_identity_tags':{'name':'Demo','natural':'reef'}};self.policy=polygon_policy.adapt(self.snap,{'a'})
 def test_reef_full_and_partial(self):
  self.prepare();c=self.runv()['claims'][0];self.assertEqual(c['component_ids'],[10]);self.assertEqual(c['containment']['excluded_partial_components'],[{'component_id_evidence_only':11,'inside_cells':1,'whole_cells':3}])
 def test_wrong_identity_fails(self):
  self.prepare();self.snap['affiliations'][0]['evidence']['selector']['expected_identity_tags']['name']='Wrong';self.policy=polygon_policy.adapt(self.snap,{'a'})
  with self.assertRaises(ValueError):self.runv()
 def test_wrong_provider_url_fails(self):
  self.prepare();self.snap['source_lineage_assets'][0]['source_uri']='https://example.com/relation/20'
  with self.assertRaises(ValueError):polygon_policy.adapt(self.snap,{'a'})
 def test_missing_reef_tag_fails(self):
  self.prepare();del self.snap['affiliations'][0]['evidence']['selector']['expected_identity_tags']['natural']
  with self.assertRaises(ValueError):polygon_policy.adapt(self.snap,{'a'})
