import hashlib,unittest
from polygon_loader import extract
from polygon_policy import adapt
from test_polygon_loader import LoaderTests
from test_polygon_policy import TestPolygonPolicy
class LabelLoaderTests(LoaderTests):
 def test_label_exact_identity_and_v4_rejection(self):
  self.xml=self.xml.replace('<way id="7">','<node id="99" version="1" lon="0.5" lat="0.5"><tag k="note" v="label"/></node><way id="7">').replace('<tag k="type" v="multipolygon"/>','<member type="node" ref="99" role="label"/><tag k="type" v="multipolygon"/><tag k="name" v="Group"/><tag k="place" v="archipelago"/>');self.p.write_text(self.xml);self.pin.update(size_bytes=self.p.stat().st_size,sha256=hashlib.sha256(self.p.read_bytes()).hexdigest());self.f.update(source_class='archipelago',extractor_version='osm-multipolygon-outer-label-v1',expected_identity_tags={'name':'Group','place':'archipelago'},label_node_id='99',label_node_version='1',expected_label_tags={'note':'label'})
  _,trace=extract(self.f,self.pin,lambda:None);self.assertEqual(trace['excluded_non_geometric_label_node_id'],'99');self.assertEqual(trace['verified_label_tags'],{'note':'label'})
  for k,v in [('label_node_id','98'),('label_node_version','2'),('expected_label_tags',{'note':'wrong'}),('expected_identity_tags',{'name':'Bad','place':'archipelago'})]:
   old=self.f[k];self.f[k]=v
   with self.assertRaises(ValueError):extract(self.f,self.pin,lambda:None)
   self.f[k]=old
  self.f['extractor_version']='osm-multipolygon-outer-v4'
  with self.assertRaises(ValueError):extract(self.f,self.pin,lambda:None)

class LabelPolicyTests(TestPolygonPolicy):
 def test_label_method_specific_contract(self):
  a=self.s['affiliations'][0];a['method']='osm_archipelago_component_intersection_v1';a['evidence']['selector']={'additional_feature_ids':[],'include_witnesses':[],'exclude_witnesses':[],'relation_version':'4','extractor_version':'osm-multipolygon-outer-label-v1','expected_identity_tags':{'name':'Group','place':'archipelago'},'label_node_id':'99','label_node_version':'1','expected_label_tags':{'note':'label'}};self.s['polygon_affiliation_feature_refs']=[];f=self.s['features'][0];f['source_feature_id']='9';f['evidence']={'source_format':'osm-xml','relation_version':'4','geometry_hash_method':'binary64-sorted-compact-geojson-v1'};self.s['source_lineage_assets'][0]['source_uri']='https://api.openstreetmap.org/api/0.6/relation/9/full'
  feat=adapt(self.s,{'a'})['decisions'][0]['features'][0];self.assertEqual(feat['label_node_id'],'99');self.assertEqual(feat['expected_label_tags'],{'note':'label'})
  for k,v in [('label_node_id','0'),('label_node_version','0'),('expected_label_tags',{})]:
   old=a['evidence']['selector'][k];a['evidence']['selector'][k]=v
   with self.assertRaises(ValueError):adapt(self.s,{'a'})
   a['evidence']['selector'][k]=old
  a['method']='osm_relation_component_intersection_v1'
  with self.assertRaises(ValueError):adapt(self.s,{'a'})
