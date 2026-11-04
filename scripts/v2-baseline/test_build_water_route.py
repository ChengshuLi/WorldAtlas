import json,tempfile,unittest
from pathlib import Path
import numpy as np
import build_water_route as route
from test_build_land import rle

class WaterRouteTest(unittest.TestCase):
 def fixture(self,root,blocked=False):
  (root/'physical').mkdir();(root/'config').mkdir();grid={'width':36,'height':18,'west':-180,'north':90,'step':10};values=np.ones((18,36),dtype=np.uint32);values[:4,2]=17
  if blocked:values[4,2]=17
  rows,runs=rle(values,root/'physical');cfg={'schema':'simple-v2-water-route-v1','grid':grid,'physical_rows':rows,'physical_runs':runs,'bounds':[0,6,0,5],'start':[0,0],'end':[4,0],'minimum_free_bytes':0,'max_window_cells':30};path=root/'config'/'route.json';path.write_text(json.dumps(cfg));return path,cfg
 def test_water_route_and_provenance(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);cfg,_=self.fixture(root);out=root/'out';report=route.build(cfg,out);p=np.fromfile(out/'route.u32le',dtype='<u4');self.assertEqual((int(p[0]),int(p[-1])),(0,4));self.assertGreater(len(p),5)
   xy=[(int(x)%6,int(x)//6) for x in p];self.assertTrue(all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(xy,xy[1:])));self.assertEqual(report['route']['sha256'],route.sha(out/'route.u32le'))
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
