import unittest
from spring_join_profile import station_points,GEOD


class SpringJoinProfileTest(unittest.TestCase):
    def test_geodesic_offsets_and_stationing(self):
        length,center,left,right=station_points((59.4,54.7),(59.41,54.71),19,100)
        self.assertGreater(length,1000)
        self.assertEqual(len(center),19)
        for c,l,r in zip(center,left,right):
            self.assertAlmostEqual(GEOD.inv(*c,*l)[2],100,places=5)
            self.assertAlmostEqual(GEOD.inv(*c,*r)[2],100,places=5)
        self.assertAlmostEqual(GEOD.inv(59.4,54.7,*center[0])[2],length/20,places=5)


if __name__=='__main__':unittest.main()
