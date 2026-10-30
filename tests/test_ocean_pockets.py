import unittest
import numpy as np
from clean_ocean_pockets import clean_ocean_pockets

class Pockets(unittest.TestCase):
    def test_fill_enclosed_ocean_keep_real_island(self):
        g=np.full((30,30),9,dtype='uint8');g[5:25,5:25]=2;g[10:12,10:12]=9;g[1,1]=3
        audit=clean_ocean_pockets(g)
        self.assertEqual(len(audit),1);self.assertEqual(g[10,10],2);self.assertEqual(g[1,1],3);self.assertEqual(g[0,0],9)
    def test_no_fill_open_bay(self):
        g=np.full((20,20),9,dtype='uint8');g[4:16,4:16]=2;g[8:10,8:20]=9
        self.assertEqual(clean_ocean_pockets(g),[])
    def test_small_shared_seam(self):
        g=np.full((20,20),9,dtype='uint8');g[3:17,3:10]=2;g[3:17,10:17]=6;g[9,9:11]=9
        audit=clean_ocean_pockets(g)
        self.assertEqual(audit[0]['method'],'nearest_continent_at_small_shared_seam');self.assertEqual(g[9,9],2);self.assertEqual(g[9,10],6)
    def test_date_line_wrap(self):
        g=np.full((12,12),2,dtype='uint8');g[3:9,:2]=9;g[3:9,-2:]=9
        self.assertEqual(clean_ocean_pockets(g),[])

if __name__=='__main__':unittest.main()
