import os
import tempfile
import unittest
import numpy as np
import rasterio
from rasterio.transform import from_origin
from local_flow_screen import run

class FlowScreenTest(unittest.TestCase):
    def test_opposing_samples_converge_on_synthetic_valley(self):
        with tempfile.TemporaryDirectory() as d:
            rows, cols=np.indices((100,100))
            # Downhill to the central eastward valley and then the east edge.
            z=(100-cols + 2*np.abs(rows-50)).astype('float32')
            meta=dict(driver='GTiff',width=100,height=100,count=1,crs='EPSG:4326',transform=from_origin(0,0.02,0.0002,0.0002))
            ds=os.path.join(d,'dsm.tif'); mask=os.path.join(d,'mask.tif')
            with rasterio.open(ds,'w',dtype='float32',**meta) as f: f.write(z,1)
            with rasterio.open(mask,'w',dtype='uint8',**meta) as f: f.write(np.zeros((100,100),dtype='uint8'),1)
            out=run(ds,mask,(0,0,0.02,0.02),100,(0.004,0.01),(0.016,0.01),'EPSG:3857')
            self.assertEqual(out['excluded'],0)
            self.assertEqual(out['same_outlet'],19)
            bent=run(ds,mask,(0,0,0.02,0.02),100,(0.004,0.01),(0.016,0.01),'EPSG:3857',[(0.004,0.01),(0.01,0.011),(0.016,0.01)])
            self.assertEqual(bent['excluded'],0)
            with self.assertRaises(ValueError):run(ds,mask,(0,0,0.02,0.02),100,(0.004,0.01),(0.016,0.01),'EPSG:3857',[(0,0),(0.016,0.01)])

    def test_two_valley_diagnostic_finds_transition(self):
        with tempfile.TemporaryDirectory() as d:
            rows,cols=np.indices((100,100));z=(100-cols+2*np.minimum(np.abs(rows-25),np.abs(rows-75))).astype('float32')
            meta=dict(driver='GTiff',width=100,height=100,count=1,crs='EPSG:4326',transform=from_origin(0,0.02,0.0002,0.0002))
            ds=os.path.join(d,'dsm.tif');mask=os.path.join(d,'mask.tif')
            with rasterio.open(ds,'w',dtype='float32',**meta) as f:f.write(z,1)
            with rasterio.open(mask,'w',dtype='uint8',**meta) as f:f.write(np.zeros((100,100),dtype='uint8'),1)
            out=run(ds,mask,(0,0,.02,.02),100,(.004,.01),(.016,.01),'EPSG:3857',diagnostic=(.01,.01),basin_outlets=[(.0199,.0149),(.0199,.0049)])
            self.assertIn(out['diagnostic']['root_class'],(1,2))
            self.assertGreater(min(out['diagnostic']['class_cell_counts']),0)
            self.assertLess(out['diagnostic']['nearest_transition_center_m'],100)

if __name__ == '__main__': unittest.main()
