import gzip,hashlib,os,tempfile,unittest
import numpy as np
from delta_side_screen import screen,read_grid

class SideScreenTest(unittest.TestCase):
    def test_reports_both_wrong_sides(self):
        rows=np.array([0,2,4,8,10,12],dtype='uint32')
        pairs=[(5,19),(10,18),(5,19),(10,18),(1,18),(5,19),(9,18),(10,19),(5,19),(10,18),(5,19),(10,18)]
        runs=np.array(pairs,dtype='uint32').ravel()
        summary,found=screen(rows,runs,[(0,85),(0,-85)],(-179,-70,179,70),(-100,0),(100,0),'EPSG:3857',10,5,36)
        self.assertEqual(summary['summary']['asia_labeled_europe']['count'],1)
        self.assertEqual(summary['summary']['europe_labeled_asia']['count'],1)
        self.assertEqual(summary['unassigned_land_centers'],0)
        self.assertEqual(found['asia_labeled_europe'][0]['x'],9)
        self.assertEqual(found['europe_labeled_asia'][0]['x'],0)

    def test_raw_and_gzip_grid_hashes(self):
        with tempfile.TemporaryDirectory() as d:
            b=np.array([1,2,3],dtype='<u4').tobytes();h=hashlib.sha256(b).hexdigest()
            raw=os.path.join(d,'rows.u32le');gz=raw+'.gz'
            with open(raw,'wb') as f:f.write(b)
            with gzip.open(gz,'wb') as f:f.write(b)
            np.testing.assert_array_equal(read_grid(raw,h),read_grid(gz,h))
            with self.assertRaises(ValueError):read_grid(raw,'0'*64)

if __name__=='__main__': unittest.main()
