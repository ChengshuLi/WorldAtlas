import unittest
import numpy as np
from rasterio.transform import from_origin
from seeded_flow_basins import flow_graph,trace_to_seeds

class SeededTests(unittest.TestCase):
    def test_two_seed_directions_and_invalid(self):
        valid=np.ones((2,3),bool);valid[1,2]=False
        nxt=np.array([[1,-1,1],[0,3,-2]])
        seeds=np.zeros((2,3),dtype='uint8');seeds[0,1]=1;seeds[1,0]=2
        labels,_=trace_to_seeds(nxt,valid,seeds)
        self.assertEqual(labels.tolist(),[[1,1,1],[2,2,0]])
    def test_cycle_unresolved(self):
        labels,stats=trace_to_seeds(np.array([[1,0]]),np.ones((1,2),bool),np.zeros((1,2),dtype='uint8'))
        self.assertEqual(labels.tolist(),[[3,3]]);self.assertEqual(stats['cycle'],1)
    def test_invalid_seed_rejected(self):
        with self.assertRaises(ValueError):trace_to_seeds(np.array([[-1]]),np.array([[False]]),np.array([[1]]))
    def test_wgs84_surface_fills_and_routes(self):
        z=np.full((5,5),5.0);z[2,2]=0;valid=np.ones_like(z,dtype=bool)
        filled,nxt=flow_graph(z,valid,from_origin(0,1,.001,.001),'EPSG:4326');self.assertEqual(filled[2,2],5);self.assertGreaterEqual(nxt[2,2],0)
    def test_projected_grid_rejected(self):
        z=np.ones((3,3));valid=np.ones((3,3),bool)
        with self.assertRaisesRegex(ValueError,'EPSG:4326'):
            flow_graph(z,valid,from_origin(400000,5000000,30,30),'EPSG:32637')
    def test_nonfinite_and_out_of_bounds_transform_rejected(self):
        z=np.ones((3,3));valid=np.ones((3,3),bool)
        with self.assertRaises(ValueError):flow_graph(z,valid,from_origin(float('nan'),1,.001,.001),'EPSG:4326')
        with self.assertRaises(ValueError):flow_graph(z,valid,from_origin(400,1,.001,.001),'EPSG:4326')
    def test_missing_crs_rejected(self):
        with self.assertRaisesRegex(ValueError,'EPSG:4326'):
            flow_graph(np.ones((3,3)),np.ones((3,3),bool),from_origin(0,1,.001,.001),None)

if __name__=='__main__':unittest.main()
