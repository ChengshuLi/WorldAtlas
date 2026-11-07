import os,tempfile,unittest
import numpy as np
import rasterio
from rasterio.transform import from_origin
from dem_crop import crop,digest

class CropTest(unittest.TestCase):
    def test_exact_crop_and_checksum_guard(self):
        with tempfile.TemporaryDirectory() as d:
            src=os.path.join(d,'source.tif');out=os.path.join(d,'out.tif')
            with rasterio.open(src,'w',driver='GTiff',width=4,height=4,count=1,dtype='float32',crs='EPSG:3857',transform=from_origin(0,4,1,1),nodata=-9999) as f:f.write(np.arange(16,dtype='float32').reshape(4,4),1)
            with self.assertRaises(ValueError):crop([(src,'0'*64)],(1,1,3,3),1,'EPSG:3857','nearest',out)
            report=crop([(src,digest(src))],(1,1,3,3),1,'EPSG:3857','nearest',out)
            with rasterio.open(out) as f:np.testing.assert_array_equal(f.read(1),[[5,6],[9,10]])
            self.assertEqual(report['valid_fraction'],1)

if __name__=='__main__':unittest.main()
