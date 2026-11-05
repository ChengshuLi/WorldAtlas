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
        filled,nxt=flow_graph(z,valid,from_origin(0,1,.001,.001));self.assertEqual(filled[2,2],5);self.assertGreaterEqual(nxt[2,2],0)

if __name__=='__main__':unittest.main()
