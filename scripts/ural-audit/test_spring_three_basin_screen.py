import unittest
import numpy as np
from pyproj import Geod, Transformer
from spring_three_basin_screen import nearest_transitions


class SpringThreeBasinTest(unittest.TestCase):
    def test_each_root_pair_and_unknown_cell(self):
        labels=np.array([[1,2,3],[1,0,3]],dtype=np.uint8)
        inv=Transformer.from_crs(3857,4326,always_xy=True);geod=Geod(ellps='WGS84')
        result=nearest_transitions(labels,[11,22,33],0,20,10,5,15,inv)
        self.assertEqual(set(result),{'11:22','22:33'})
        self.assertEqual(result['11:22']['point_lonlat'],list(inv.transform(10,15)))
        for key,x in [('11:22',10),('22:33',20)]:
            self.assertAlmostEqual(result[key]['distance_m'],geod.inv(*inv.transform(5,15),*inv.transform(x,15))[2],delta=1e-8)

    def test_high_latitude_geodesic_ranking(self):
        # Longitude distance contracts strongly with latitude; projected x/y
        # Euclidean ranking can therefore choose a different transition.
        class Scaled:
            def transform(self,x,y): return np.asarray(x)*.01,np.asarray(y)*.01+80
        labels=np.array([[0,0,0,0,0],[0,0,0,1,2],[0,1,0,1,0],[0,2,0,0,0]],dtype=np.uint8)
        result=nearest_transitions(labels,[1,2],0,40,10,10,20,Scaled())['1:2']
        self.assertTrue(np.isfinite(result['distance_m']))
        lon,lat=result['point_lonlat']; expected=Geod(ellps='WGS84').inv(.1,80.2,lon,lat)[2]
        self.assertAlmostEqual(result['distance_m'],expected,delta=1e-8)
        # The eastward transition wins geodesically; the southern transition
        # would win if projected x/y Euclidean distances were used instead.
        np.testing.assert_allclose((lon,lat),(.4,80.25))


if __name__=='__main__': unittest.main()

