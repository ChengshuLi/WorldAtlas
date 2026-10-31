import gzip,json,tempfile,unittest,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_grid import NativeGrid

class NativeGridTests(unittest.TestCase):
 def test_exclusive_ends_and_land_bit(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'proposal.json').write_text(json.dumps({'width':131072,'height':1,'step':360/131072}))
   (p/'rows.u32.gz').write_bytes(gzip.compress(np.array([0,3],dtype='<u4').tobytes()))
   (p/'runs.u32.gz').write_bytes(gzip.compress(np.array([[2,8],[65536,2],[131072,22]],dtype='<u4').tobytes()))
   g=NativeGrid(p)
   for x,v in [(0,8),(1,8),(2,2),(65535,2),(65536,22),(131071,22)]:
    self.assertEqual(g.at(x,0),v);self.assertEqual(int(g.row(0)[x]),v)
   self.assertFalse(g.is_land(2));self.assertFalse(g.is_land(8));self.assertTrue(g.is_land(22))
   with self.assertRaises(IndexError):g.at(131072,0)
if __name__=='__main__':unittest.main()
