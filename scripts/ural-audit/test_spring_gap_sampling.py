import unittest
import numpy as np
from affine import Affine
from spring_gap_sampling import sampled_gap,closest_sampled_pair,G


class Identity:
    def transform(self,x,y):return x,y


class SpringGapSamplingTest(unittest.TestCase):
    def test_ninth_chord_candidate_can_be_nearest_geodesically(self):
        from pyproj import Transformer
        points=[(4.653210991,-4.952086531),(-7.02052525,-4.687746212),(-7.500812622,-4.620942023),(4.146730717,-4.994861691),(-7.109798602,-4.676093217),(-1.088518416,-5.147954049),(4.074044418,-5.001225927),(-12.067788207,-3.75868194),(-14.068948616806175,-3.248401475069858)]
        ecef=Transformer.from_crs(4979,4978,always_xy=True);q=np.array(ecef.transform(0,40,0));p=np.array([ecef.transform(x,y,0) for x,y in points]);chords=np.linalg.norm(p-q,axis=1)
        self.assertEqual(int(np.sum(chords<chords[-1])),8)
        d,i,j=closest_sampled_pair(points,[(0,40)])
        self.assertEqual((i,j),(0,8));self.assertAlmostEqual(d,G.inv(0,40,*points[8])[2],places=6)
    def test_matches_brute_force_with_wrap_and_ties(self):
        rng=np.random.default_rng(42);selected=np.column_stack((rng.uniform(-180,180,21),rng.uniform(-85,85,21))).tolist();interface=np.column_stack((rng.uniform(-180,180,13),rng.uniform(-85,85,13))).tolist()
        selected += [(179.999,0),(179.999,0)];interface += [(-179.999,0)]
        expected=min((G.inv(*q,*p)[2],i,j) for i,q in enumerate(interface) for j,p in enumerate(selected))
        got=closest_sampled_pair(selected,interface);self.assertEqual(got[1:],expected[1:]);self.assertAlmostEqual(got[0],expected[0],places=7)
        with self.assertRaises(ValueError):closest_sampled_pair([(0,91)],[(0,0)])
    def test_sampled_gap_and_wgs84_distance(self):
        labels=np.array([[1,2],[1,2]],dtype=np.uint8)
        t=Affine(.001,0,0,0,-.001,.002)
        result=sampled_gap(labels,t,Identity(),[(.003,0),(.003,.002)],[-.01,-.01,.01,.01],15)
        actual=G.inv(*result['retained_point'],*result['interface_point'])[2]
        self.assertAlmostEqual(result['sampled_gap_wgs84_m'],actual,places=8)
        self.assertGreater(actual,220);self.assertLess(actual,225)


if __name__=='__main__':unittest.main()

