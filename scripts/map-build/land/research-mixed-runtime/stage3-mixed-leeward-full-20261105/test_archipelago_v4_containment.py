import hashlib,json,unittest
from test_polygon_resolution import ResolveTests
import polygon_policy
class V4Containment(ResolveTests):
 def prepare(self,extra_member='',place='archipelago'):
  raw=f'<osm><node id="1" lon="-105" lat="55"/><node id="2" lon="40" lat="55"/><node id="3" lon="40" lat="89"/><node id="4" lon="-105" lat="89"/><way id="10"><nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="1"/></way><relation id="20" version="4"><member type="way" ref="10" role="outer"/>{extra_member}<tag k="type" v="multipolygon"/><tag k="place" v="{place}"/><tag k="name" v="Demo"/></relation></osm>';self.file.write_text(raw);h=hashlib.sha256(self.file.read_bytes()).hexdigest()
  for z in (self.snap['sources'][0],self.snap['source_lineage_assets'][0],self.sources[0]):z['sha256']=h;z['size_bytes']=self.file.stat().st_size
  self.snap['source_lineage_assets'][0]['source_uri']='https://api.openstreetmap.org/api/0.6/relation/20/full';g={'type':'MultiPolygon','coordinates':[[[[-105.,55.],[40.,55.],[40.,89.],[-105.,89.],[-105.,55.]]]]};self.snap['features'][0].update(source_feature_id='20',geometry_sha256=hashlib.sha256(json.dumps(g,sort_keys=True,separators=(',',':')).encode()).hexdigest(),evidence={'source_format':'osm-xml','relation_version':'4','geometry_hash_method':'binary64-sorted-compact-geojson-v1'});a=self.snap['affiliations'][0];a['method']='osm_archipelago_component_containment_v1';a['evidence']['selector']={'additional_feature_ids':[],'include_witnesses':[],'exclude_witnesses':[],'relation_version':'4','extractor_version':'osm-multipolygon-outer-v4','expected_identity_tags':{'name':'Demo','place':'archipelago'}};self.policy=polygon_policy.adapt(self.snap,{'a'})
 def test_v4_named_group_full_and_partial(self):
  self.prepare();c=self.runv()['claims'][0];self.assertEqual(c['component_ids'],[10]);self.assertEqual(c['containment']['excluded_partial_components'],[{'component_id_evidence_only':11,'inside_cells':1,'whole_cells':3}])
 def test_v4_rejects_unknown_node_member(self):
  self.prepare('<member type="node" ref="99" role="label"/>')
  with self.assertRaises(ValueError):self.runv()
 def test_v4_rejects_name_mismatch(self):
  self.prepare();self.snap['affiliations'][0]['evidence']['selector']['expected_identity_tags']['name']='Wrong';self.policy=polygon_policy.adapt(self.snap,{'a'})
  with self.assertRaises(ValueError):self.runv()
 def test_v4_rejects_witness(self):
  self.prepare();self.snap['affiliations'][0]['evidence']['selector']['include_witnesses']=[{'lon':'0','lat':'0'}]
  with self.assertRaises(ValueError):polygon_policy.adapt(self.snap,{'a'})
if __name__=='__main__':unittest.main()
