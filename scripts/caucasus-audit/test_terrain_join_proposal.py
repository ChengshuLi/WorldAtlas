import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import numpy as np
import rasterio
from rasterio.transform import from_origin

SCRIPT=Path(__file__).with_name('terrain_join_proposal.py')

class JoinProposalTest(unittest.TestCase):
    def test_synthetic_flat_surface_generates_six_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); affine=from_origin(0,1,1/3600,1/3600)
            def point(row,col):
                return list(rasterio.transform.xy(affine,row,col))
            profile={'driver':'GTiff','width':100,'height':100,'count':1,
                     'dtype':'int16','crs':'EPSG:4326','transform':affine,'nodata':-9999}
            for name,fill in [('dsm',100),('mask',0),('stack',1)]:
                with rasterio.open(root/(name+'.tif'),'w',**profile) as out:
                    out.write(np.full((100,100),fill,dtype='int16'),1)
            for name,coordinates in [('selected',[point(20,54),point(80,54)]),
                                     ('candidate',[point(50,50),point(52,49)])]:
                (root/(name+'.json')).write_text(json.dumps({'type':'LineString','coordinates':coordinates}))
            command=[sys.executable,str(SCRIPT),'--selected',str(root/'selected.json'),
                     '--candidate',str(root/'candidate.json'),'--dsm',str(root/'dsm.tif'),
                     '--mask',str(root/'mask.tif'),'--stack',str(root/'stack.tif'),
                     '--epsg','32631','--radius-pixels','10','--output-dir',str(root/'out')]
            result=subprocess.run(command,capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(len(list((root/'out').glob('*.json'))),6)
            for file in (root/'out').glob('*.json'):
                geometry=json.loads(file.read_text())
                self.assertEqual(geometry['type'],'LineString')
                self.assertGreaterEqual(len(geometry['coordinates']),2)

if __name__=='__main__':unittest.main()
