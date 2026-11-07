import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
from osgeo import gdal
import rasterize_land as b

class RasterizeLandTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory(); self.d=Path(self.t.name); self.inputs=self.d/'inputs'; self.inputs.mkdir()
        self.p=self.inputs/'land.geojson'
        self.p.write_text(json.dumps({'type':'FeatureCollection','features':[{'type':'Feature','properties':{},'geometry':{'type':'Polygon','coordinates':[[[-180,90],[-45,90],[-45,0],[-180,0],[-180,90]]]}}]}))
        self.cfg={'schema':'land-raster-candidate-v1','grid':{'width':8,'height':4,'west':-180,'north':90,'step':45},'selection_notes':'synthetic','strip_rows':1,'minimum_free_bytes':0,
                  'land':[{'dataset':str(self.p),'where':None,'files':[{'path':str(self.p),'sha256':b.sha(self.p)}]}]}
        self.config=self.inputs/'config.json'; self.config.write_text(json.dumps(self.cfg))
    def tearDown(self): self.t.cleanup()
    def test_polygon_and_strip_invariance(self):
        a=self.d/'a';b.run(self.config,a); expected=np.zeros((4,8),dtype=np.uint8);expected[:2,:3]=1
        np.testing.assert_array_equal(gdal.Open(str(a/'land.tif')).ReadAsArray(),expected)
        report=json.loads((a/'report.json').read_text());self.assertEqual(report['land_cells'],6);self.assertEqual(report['feature_counts'],[1])
        self.cfg['strip_rows']=4;self.config.write_text(json.dumps(self.cfg));out=self.d/'all-rows';b.run(self.config,out)
        np.testing.assert_array_equal(gdal.Open(str(out/'land.tif')).ReadAsArray(),expected)
    def test_rejects_bad_digest_and_output_collision(self):
        self.cfg['land'][0]['files'][0]['sha256']='0'*64;self.config.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError,'digest mismatch'):b.run(self.config,self.d/'bad')
        self.assertFalse((self.d/'bad').exists())
        self.cfg['land'][0]['files'][0]['sha256']=b.sha(self.p);self.config.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError,'outside input'):b.run(self.config,self.inputs/'bad')
        (self.d/'exists').mkdir()
        with self.assertRaises(FileExistsError):b.run(self.config,self.d/'exists')
    def test_rejects_invalid_geometry(self):
        self.p.write_text(json.dumps({'type':'FeatureCollection','features':[{'type':'Feature','properties':{},'geometry':{'type':'Polygon','coordinates':[[[-180,90],[-45,0],[-45,90],[-180,0],[-180,90]]]}}]}))
        self.cfg['land'][0]['files'][0]['sha256']=b.sha(self.p);self.config.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError,'invalid geometry'):b.run(self.config,self.d/'bad')
        self.assertFalse((self.d/'bad').exists())
if __name__=='__main__':unittest.main()
