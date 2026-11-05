import hashlib,os,tempfile,unittest,zipfile
import numpy as np,rasterio,shapefile
from rasterio.transform import from_origin
from pyproj import Transformer
from terrain_basin_screen import screen

class TerrainScreenTest(unittest.TestCase):
    def test_two_basin_synthetic_surface(self):
        with tempfile.TemporaryDirectory() as d:
            dem=os.path.join(d,'dem.tif');rr,cc=np.indices((100,100));z=(100-cc+2*np.minimum(abs(rr-25),abs(rr-75))).astype('float32')
            z[50,50]=-9999
            with rasterio.open(dem,'w',driver='GTiff',width=100,height=100,count=1,dtype='float32',crs='EPSG:3857',transform=from_origin(0,1000,10,10),nodata=-9999) as f:f.write(z,1)
            base=os.path.join(d,'b');w=shapefile.Writer(base,shapeType=shapefile.POLYGON);w.field('MAIN_BAS','N',10,0)
            togeo=Transformer.from_crs(3857,4326,always_xy=True).transform
            for y0,y1,r in [(0,500,10),(500,1000,20)]:
                pts=[togeo(x,y) for x,y in [(0,y0),(0,y1),(1000,y1),(1000,y0),(0,y0)]];w.poly([pts]);w.record(r)
            w.close();archive=os.path.join(d,'basins.zip')
            with zipfile.ZipFile(archive,'w') as q:
                for ext in ('.shp','.shx','.dbf'):q.write(base+ext,os.path.basename(base)+ext)
            def sha(p):
                with open(p,'rb') as f:return hashlib.sha256(f.read()).hexdigest()
            line=[togeo(100,500),togeo(900,500)]
            out=screen(dem,sha(dem),[(archive,sha(archive),base+'.shp')],line,[10],[20],[100],200)
            self.assertEqual(out['valid_cells'],9999)
            self.assertEqual(out['outlets']['conflict'],0)
            self.assertEqual(out['label_cell_counts']['unknown_valid'],0)
            self.assertEqual(sum(out['offset_pair_counts']['100'].values()),out['stations'])
            self.assertTrue(any(k in out['offset_pair_counts']['100'] for k in ('1-2','2-1')))

if __name__=='__main__':unittest.main()

