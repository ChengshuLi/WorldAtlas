import unittest
import numpy as np
GT=(-.015,.01,0,.015,0,-.01)
from trace_downhill import trace, filter_surface, trace_record

class TraceTests(unittest.TestCase):
    def test_downhill_and_pit(self):
        z = np.array([[9,9,9,9,9], [9,8,7,6,9], [9,9,9,9,9]])
        path,status = trace(z, np.ones_like(z, bool), (1,1), GT)
        self.assertEqual(path, [(1,1),(1,2),(1,3)])
        self.assertEqual(status, 'pit_or_flat')

    def test_mask_stops_before_forcing_direction(self):
        z = np.array([[9,9,9], [9,8,1], [9,9,9]])
        valid = np.ones_like(z, bool); valid[0,1] = False
        path,status = trace(z,valid,(1,1),GT)
        self.assertEqual((path,status), ([(1,1)],'invalid_neighbor'))

    def test_flats_are_optional_and_bounded(self):
        z = np.array([[9,9,9,9,9,9], [9,7,7,7,6,9], [9,9,9,9,9,9]])
        valid = np.ones_like(z, bool)
        self.assertEqual(trace(z,valid,(1,1),GT,flat_limit=0)[1], 'pit_or_flat')
        self.assertEqual(trace(z,valid,(1,1),GT,flat_limit=2)[1], 'large_flat')
        path,status = trace(z,valid,(1,1),GT,flat_limit=3)
        self.assertEqual(path, [(1,1),(1,2),(1,3),(1,4)])
        self.assertEqual(status,'pit_or_flat')

    def test_median_filter_qualifies_all_neighbors(self):
        z = np.ones((7,7),dtype=int); z[3,3] = 100
        valid = np.ones_like(z,bool); valid[1,1] = False
        filtered, screened = filter_surface(z,valid,3)
        self.assertEqual(filtered[3,3],1)
        self.assertFalse(screened[2,2])
        self.assertTrue(screened[4,4])
        self.assertFalse(screened[0,4])
        with self.assertRaises(ValueError): filter_surface(z,valid,2)

    def test_ellipsoidal_neighbor_distance_changes_slope_ranking(self):
        z=np.full((3,3),3000,dtype=int);z[1,1]=2000;z[0,1]=1005;z[1,2]=1000
        path,status=trace(z,np.ones_like(z,bool),(1,1),GT)
        self.assertEqual(path[:2],[(1,1),(0,1)])

    def test_output_uses_validated_top_level_section(self):
        result=trace_record({'distance_m':500,'center':[1,1]},7,{}, {})
        self.assertEqual(result['section'],7)
        self.assertEqual(result['distance_method'],'wgs84-ellipsoidal-geodesic-v1')

    def test_invalid_start(self):
        z=np.ones((3,3),int);valid=np.ones((3,3),bool);valid[1,1]=False
        self.assertEqual(trace(z,valid,(1,1),GT),([], 'invalid_start'))

if __name__ == '__main__': unittest.main()
