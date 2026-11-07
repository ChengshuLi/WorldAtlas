import hashlib,os,tempfile,unittest,zipfile
import shapefile
from classify_outlet_basins import run

class BasinTest(unittest.TestCase):
    def test_point_matches_basin_and_terminal(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=os.path.join(tmp,'basins');w=shapefile.Writer(base,shapeType=shapefile.POLYGON)
            for name in ('HYBAS_ID','MAIN_BAS','NEXT_SINK','NEXT_DOWN'):w.field(name,'N',10,0)
            w.poly([[(0,0),(0,1),(1,1),(1,0),(0,0)]]);w.record(42,42,42,0);w.close()
            path=os.path.join(tmp,'a.zip')
            with zipfile.ZipFile(path,'w') as z:
                for ext in ('shp','shx','dbf'):z.write(base+'.'+ext,'basins.'+ext)
            with open(path,'rb') as f:sha=hashlib.sha256(f.read()).hexdigest()
            r=run(path,sha,[(.5,.5),(2,2)])
            self.assertEqual(r['points'][0]['hits'][0]['main_bas'],42)
            self.assertEqual(r['points'][1]['hits'],[])
            self.assertEqual(r['terminal_records'][0]['next_down'],0)

if __name__=='__main__':unittest.main()
