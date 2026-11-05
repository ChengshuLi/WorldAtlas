import hashlib,json,tempfile,unittest
from pathlib import Path
from polygon_loader import extract
class LoaderTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.p=Path(self.t.name)/'raw.osm';self.xml='<osm><node id="1" lon="0" lat="0"/><node id="2" lon="1" lat="0"/><node id="3" lon="1" lat="1"/><way id="7"><nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="1"/></way><relation id="9" version="4"><member type="way" ref="7" role="outer"/><tag k="type" v="multipolygon"/></relation></osm>';self.p.write_text(self.xml);g={'type':'MultiPolygon','coordinates':[[[[0.0,0.0],[1.0,0.0],[1.0,1.0],[0.0,0.0]]]]};h=hashlib.sha256(json.dumps(g,sort_keys=True,separators=(',',':')).encode()).hexdigest();self.f={'source_format':'osm-xml','extractor_version':'osm-multipolygon-outer-v2','source_feature_id':'9','relation_version':'4','geometry_sha256':h};self.pin={'path':str(self.p),'sha256':hashlib.sha256(self.p.read_bytes()).hexdigest(),'size_bytes':self.p.stat().st_size}
 def test_osm(self):self.assertEqual(extract(self.f,self.pin,lambda:None)[1]['outer_ring_count'],1)
 def test_version_mismatch(self):
  self.f['relation_version']='5'
  with self.assertRaisesRegex(ValueError,'version mismatch'):extract(self.f,self.pin,lambda:None)
 def test_v3_validates_identity_tags(self):
  xml=self.xml.replace('<tag k="type" v="multipolygon"/>','<tag k="type" v="multipolygon"/><tag k="name" v="Test island"/><tag k="place" v="island"/>');self.p.write_text(xml);self.pin['size_bytes']=self.p.stat().st_size;self.pin['sha256']=hashlib.sha256(self.p.read_bytes()).hexdigest();self.f.update(extractor_version='osm-multipolygon-outer-v3',expected_identity_tags={'name':'Test island','place':'island'})
  self.assertEqual(extract(self.f,self.pin,lambda:None)[1]['verified_identity_tags']['name'],'Test island');self.f['expected_identity_tags']['name']='Wrong'
  with self.assertRaisesRegex(ValueError,'identity tags mismatch'):extract(self.f,self.pin,lambda:None)
 def test_v4_checks_exact_alias_and_v3_rejects_it(self):
  xml=self.xml.replace('<tag k="type" v="multipolygon"/>','<tag k="type" v="multipolygon"/><tag k="name" v="ExampleIslandA"/><tag k="alt_name" v="ExampleIslandB"/><tag k="place" v="island"/>');self.p.write_text(xml);self.pin['size_bytes']=self.p.stat().st_size;self.pin['sha256']=hashlib.sha256(self.p.read_bytes()).hexdigest();self.f.update(extractor_version='osm-multipolygon-outer-v4',expected_identity_tags={'name':'ExampleIslandA','alt_name':'ExampleIslandB','place':'island'})
  self.assertEqual(extract(self.f,self.pin,lambda:None)[1]['verified_identity_tags']['alt_name'],'ExampleIslandB');self.f['expected_identity_tags']['alt_name']='Wrong'
  with self.assertRaisesRegex(ValueError,'identity tags mismatch'):extract(self.f,self.pin,lambda:None)
  self.f['extractor_version']='osm-multipolygon-outer-v3';self.f['expected_identity_tags']['alt_name']='ExampleIslandB'
  with self.assertRaisesRegex(ValueError,'identity tags mismatch'):extract(self.f,self.pin,lambda:None)
 def test_source_hash(self):
  self.pin['sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'hash mismatch'):extract(self.f,self.pin,lambda:None)
 def test_size_limit(self):
  self.pin['size_bytes']=1
  with self.assertRaisesRegex(ValueError,'size mismatch'):extract(self.f,self.pin,lambda:None)
 def test_anchored_ring_loader(self):
  raw='<osm><node id="1" version="1" visible="true" lon="0" lat="0"/><node id="2" version="3" visible="true" lon="1" lat="0"><tag k="name:en" v="ExampleAnchor"/><tag k="amenity" v="ferry_terminal"/></node><node id="3" version="1" visible="true" lon="1" lat="1"/><node id="4" version="1" visible="true" lon="0" lat="1"/><way id="10"><nd ref="1"/><nd ref="2"/><nd ref="3"/></way><way id="11"><nd ref="3"/><nd ref="4"/><nd ref="1"/></way><relation id="20" version="4"><member type="way" ref="10" role="outer"/><member type="way" ref="11" role="outer"/><tag k="type" v="multipolygon"/><tag k="place" v="archipelago"/><tag k="name" v="Demo"/></relation></osm>';self.p.write_text(raw);self.pin['sha256']=hashlib.sha256(self.p.read_bytes()).hexdigest();self.pin['size_bytes']=self.p.stat().st_size;ring=[[0.0,0.0],[1.0,0.0],[1.0,1.0],[0.0,1.0],[0.0,0.0]];gh=lambda g:hashlib.sha256(json.dumps(g,sort_keys=True,separators=(',',':')).encode()).hexdigest();anchor={'node_id':'2','node_version':'3','way_id':'10','expected_tags':{'name:en':'ExampleAnchor','amenity':'ferry_terminal'},'geometry_sha256':gh({'type':'Polygon','coordinates':[ring]})};self.f={'source_format':'osm-xml','source_class':'archipelago','extractor_version':'osm-anchored-outer-rings-v1','source_feature_id':'20','relation_version':'4','geometry_sha256':gh({'type':'MultiPolygon','coordinates':[[ring]]}),'expected_relation_tags':{'name':'Demo','place':'archipelago'},'anchors':[anchor]};g,t=extract(self.f,self.pin,lambda:None);self.assertEqual(g['type'],'MultiPolygon');self.assertEqual(t['selected_anchor_traces'][0]['anchor_node_id'],'2');anchor['way_id']='11'
  with self.assertRaises(ValueError):extract(self.f,self.pin,lambda:None)
if __name__=='__main__':unittest.main()
