import gzip,hashlib,os,tempfile,unittest
import numpy as np
from delta_side_screen import screen,read_grid

class SideScreenTest(unittest.TestCase):
    def test_reports_both_wrong_sides(self):
        width,height=3600,1800;rows=[0];pairs=[]
        for y in range(height):
            pairs.extend([(1799,19),(1800,18),(1801,19),(width,18)] if y==899 else [(1800,19),(width,18)])
            rows.append(len(pairs))
        rows=np.array(rows,dtype='uint32')
        runs=np.array(pairs,dtype='uint32').ravel()
        summary,found=screen(rows,runs,[(0,.3),(0,-.3)],(-.2,-.2,.2,.2),(-.15,0),(.15,0),'EPSG:3857',width,height,.1)
        self.assertEqual(summary['summary']['asia_labeled_europe']['count'],1)
        self.assertEqual(summary['summary']['europe_labeled_asia']['count'],1)
        self.assertEqual(summary['unassigned_land_centers'],0)
        self.assertEqual(found['asia_labeled_europe'][0]['x'],1800)
        self.assertEqual(found['europe_labeled_asia'][0]['x'],1799)
        self.assertTrue(summary['summary']['asia_labeled_europe']['threshold_counts_are_numerical_estimates'])

    def test_raw_and_gzip_grid_hashes(self):
        with tempfile.TemporaryDirectory() as d:
            b=np.array([1,2,3],dtype='<u4').tobytes();h=hashlib.sha256(b).hexdigest()
            raw=os.path.join(d,'rows.u32le');gz=raw+'.gz'
            with open(raw,'wb') as f:f.write(b)
            with gzip.open(gz,'wb') as f:f.write(b)
            np.testing.assert_array_equal(read_grid(raw,h),read_grid(gz,h))
            with self.assertRaises(ValueError):read_grid(raw,'0'*64)

if __name__=='__main__': unittest.main()

