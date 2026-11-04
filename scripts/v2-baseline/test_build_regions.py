import json,tempfile,unittest
from pathlib import Path
import numpy as np
import build_regions,build_water_route
from test_build_land import pin,rle

class RegionTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.inputs=self.root/'inputs';self.inputs.mkdir();self.grid={'width':36,'height':18,'west':-180,'north':90,'step':10}
  self.cfg={'schema':'simple-v2-regions-v1','grid':self.grid,'regions':[{'id':'test','segments':[{'kind':'points','coordinates':[[-10,-10],[10,-10],[10,10],[-10,10],[-10,-10]]}],'witnesses':[{'lon':0,'lat':0,'inside':True},{'lon':15,'lat':0,'inside':False}]}],'evidence':[],'minimum_free_bytes':0};self.path=self.inputs/'config.json';self.save()
 def tearDown(self):self.tmp.cleanup()
 def save(self):self.path.write_text(json.dumps(self.cfg))
 def test_explicit_polygon_and_pins(self):
  out=self.root/'out';r=build_regions.build(self.path,out);geo=json.loads((out/'test.geojson').read_text());self.assertEqual(geo['features'][0]['geometry']['type'],'Polygon');self.assertEqual(r['outputs'][0]['sha256'],pin(out/'test.geojson')['sha256'])
 def test_feature_and_explicit_connectors(self):
  line=self.inputs/'source.geojson';line.write_text(json.dumps({'type':'FeatureCollection','features':[{'type':'Feature','properties':{'id':'cut'},'geometry':{'type':'LineString','coordinates':[[-10,-10],[10,-10]]}}]}))
  self.cfg['regions'][0]['segments']=[{'kind':'feature','file':pin(line),'id_property':'id','id_value':'cut','reverse':False},{'kind':'points','coordinates':[[10,-10],[10,10],[-10,10],[-10,-10]]}];self.save();self.assertEqual(build_regions.build(self.path,self.root/'out')['status'],'unreviewed-research-not-published')
 def test_unjoined_witness_and_hash_fail(self):
  self.cfg['regions'][0]['segments']=[{'kind':'points','coordinates':[[-10,-10],[10,-10]]},{'kind':'points','coordinates':[[11,-10],[10,10],[-10,10],[-10,-10]]}];self.save()
  with self.assertRaisesRegex(ValueError,'do not join'):build_regions.build(self.path,self.root/'out')
  self.cfg['regions'][0]['segments']=[{'kind':'points','coordinates':[[-10,-10],[10,-10],[10,10],[-10,10],[-10,-10]]}];self.cfg['regions'][0]['witnesses'][0]['inside']=False;self.save()
  with self.assertRaisesRegex(ValueError,'witness fails'):build_regions.build(self.path,self.root/'out')
  self.cfg['regions'][0]['witnesses']=[];self.cfg['evidence']=[{'path':str(self.path),'sha256':'0'*64}];self.save()
  with self.assertRaisesRegex(ValueError,'hash mismatch'):build_regions.build(self.path,self.root/'out')
 def test_water_route_segment_is_rechecked(self):
  physical=self.root/'physical';physical.mkdir();rows,runs=rle(np.ones((18,36),dtype=np.uint32),physical);rc={'schema':'simple-v2-water-route-v1','grid':self.grid,'physical_rows':rows,'physical_runs':runs,'bounds':[0,8,0,8],'start':[2,5],'end':[4,5],'minimum_free_bytes':0};rpath=self.inputs/'route-config.json';rpath.write_text(json.dumps(rc));route_out=self.root/'route';build_water_route.build(rpath,route_out)
  self.cfg['regions'][0]={'id':'route-region','segments':[{'kind':'water-route','report':pin(route_out/'report.json'),'reverse':False},{'kind':'points','coordinates':[[-135,35],[-135,25],[-155,25],[-155,35]]}],'witnesses':[{'lon':-145,'lat':30,'inside':True}]};self.save();out=self.root/'out';self.assertEqual(build_regions.build(self.path,out)['status'],'unreviewed-research-not-published')
  with open(route_out/'route.u32le','ab') as f:f.write(b'\0\0\0\0')
  with self.assertRaisesRegex(ValueError,'hash mismatch'):build_regions.build(self.path,self.root/'bad')
 def test_route_cannot_cross_changed_physical_land(self):
  physical=self.root/'physical';physical.mkdir();values=np.ones((18,36),dtype=np.uint32);rows,runs=rle(values,physical);rc={'schema':'simple-v2-water-route-v1','grid':self.grid,'physical_rows':rows,'physical_runs':runs,'bounds':[0,8,0,8],'start':[2,5],'end':[4,5],'minimum_free_bytes':0};rp=self.inputs/'route-config.json';rp.write_text(json.dumps(rc));route_out=self.root/'route';build_water_route.build(rp,route_out)
  values[5,3]=17;rows,runs=rle(values,physical);report=route_out/'report.json';doc=json.loads(report.read_text());doc['physical_rows']=rows;doc['physical_runs']=runs;report.write_text(json.dumps(doc))
  self.cfg['regions'][0]={'id':'route','segments':[{'kind':'water-route','report':pin(report),'reverse':False},{'kind':'points','coordinates':[[-135,35],[-135,25],[-155,25],[-155,35]]}],'witnesses':[]};self.save()
  with self.assertRaisesRegex(ValueError,'crosses land'):build_regions.build(self.path,self.root/'bad')
  self.assertFalse((self.root/'bad').exists())
 def test_resource_guard_before_output(self):
  self.cfg['minimum_free_bytes']=1<<60;self.save()
  with self.assertRaisesRegex(ValueError,'free disk'):build_regions.build(self.path,self.root/'out')
  self.assertFalse((self.root/'out').exists())
if __name__=='__main__':unittest.main()
