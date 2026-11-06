import json,tempfile,unittest
from pathlib import Path
import numpy as np
import build_water_route as route
from fixture_land import rle

class WaterRouteTest(unittest.TestCase):
 def fixture(self,root,blocked=False):
  (root/'physical').mkdir();(root/'config').mkdir();grid={'width':36,'height':18,'west':-180,'north':90,'step':10};values=np.ones((18,36),dtype=np.uint32);values[:4,2]=17
  if blocked:values[4,2]=17
  rows,runs=rle(values,root/'physical');cfg={'schema':'simple-v2-water-route-v2','grid':grid,'physical_rows':rows,'physical_runs':runs,'bounds':[0,6,0,5],'start':[0,0],'end':[4,0],'minimum_free_bytes':0,'max_window_cells':30};path=root/'config'/'route.json';path.write_text(json.dumps(cfg));return path,cfg
 def test_water_route_and_provenance(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);cfg,_=self.fixture(root);out=root/'out';report=route.build(cfg,out);p=np.fromfile(out/'route.u32le',dtype='<u4');self.assertEqual((int(p[0]),int(p[-1])),(0,4));self.assertGreater(len(p),5)
   xy=[(int(x)%6,int(x)//6) for x in p];self.assertTrue(all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(xy,xy[1:])));self.assertEqual(report['route']['sha256'],route.sha(out/'route.u32le'))
 def test_wgs84_weighted_route_prefers_shorter_high_latitude_cells(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'physical').mkdir();(root/'config').mkdir()
   grid={'width':36,'height':18,'west':-180,'north':90,'step':10}
   values=np.ones((18,36),dtype=np.uint32)
   for x,y in ((0,1),(0,4),(0,5),(1,2),(2,0),(2,5),(3,2),(5,0),(5,3)):values[y,x]=17
   rows,runs=rle(values,root/'physical')
   cfg={'schema':'simple-v2-water-route-v2','grid':grid,'physical_rows':rows,'physical_runs':runs,'bounds':[0,6,0,6],'start':[3,1],'end':[3,4],'minimum_free_bytes':0}
   path=root/'config'/'route.json';path.write_text(json.dumps(cfg));out=root/'out';report=route.build(path,out)
   ids=np.fromfile(out/'route.u32le',dtype='<u4');coords=[(int(x)%6,int(x)//6) for x in ids]
   self.assertEqual(coords,[(3,1),(2,1),(2,2),(2,3),(3,3),(3,4)])
   self.assertIn('WGS84',report['route']['metric']);self.assertGreater(report['route']['distance_m'],0)
   def center(x,y):return (-180+(x+.5)*10,90-(y+.5)*10)
   expected=sum(route.shore.GEOD.inv(*center(x1,y1),*center(x2,y2))[2] for (x1,y1),(x2,y2) in zip(coords,coords[1:]))
   self.assertLessEqual(abs(report['route']['distance_m']-expected),len(coords)*0.6e-6)
 def test_equal_cost_paths_choose_lowest_predecessor_id(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'physical').mkdir();(root/'config').mkdir()
   grid={'width':4,'height':2,'west':-180,'north':90,'step':90}
   rows,runs=rle(np.ones((2,4),dtype=np.uint32),root/'physical')
   cfg={'schema':'simple-v2-water-route-v2','grid':grid,'physical_rows':rows,'physical_runs':runs,'bounds':[0,2,0,2],'start':[0,0],'end':[1,1],'minimum_free_bytes':0}
   path=root/'config'/'route.json';path.write_text(json.dumps(cfg));out=root/'out';route.build(path,out)
   ids=np.fromfile(out/'route.u32le',dtype='<u4')
   self.assertEqual(ids.tolist(),[0,1,3])
 def test_no_path_and_no_completion_report(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);cfg,_=self.fixture(root,True)
   with self.assertRaisesRegex(ValueError,'no water path'):route.build(cfg,root/'out')
   self.assertFalse((root/'out/report.json').exists())
 def test_resource_and_hash_fail_before_output(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);path,cfg=self.fixture(root);cfg['minimum_free_bytes']=1<<60;path.write_text(json.dumps(cfg))
   with self.assertRaisesRegex(ValueError,'free disk'):route.build(path,root/'out')
   self.assertFalse((root/'out').exists());cfg['minimum_free_bytes']=0;cfg['physical_rows']['sha256']='0'*64;path.write_text(json.dumps(cfg))
   with self.assertRaisesRegex(ValueError,'hash mismatch'):route.build(path,root/'out')
   self.assertFalse((root/'out').exists())
if __name__=='__main__':unittest.main()
