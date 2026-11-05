import unittest
import numpy as np
from priority_flood import priority_flood,trace

class PriorityFloodTest(unittest.TestCase):
    def test_closed_pit_fills_and_flat_routes_to_crop_edge(self):
        z=np.full((5,5),5.0);z[2,2]=0
        valid=np.ones_like(z,dtype=bool)
        filled,parent=priority_flood(z,valid)
        self.assertEqual(filled[2,2],5)
        path,status=trace(filled,valid,parent,(2,2),1,1)
        self.assertEqual(status,'crop_edge')
        self.assertEqual(len(path),len(set(path)))
        self.assertTrue(all(filled[a]>=filled[b] for a,b in zip(path,path[1:])))

    def test_invalid_neighbor_is_an_artificial_outlet(self):
        z=np.ones((5,5));valid=np.ones((5,5),dtype=bool);valid[2,2]=False
        filled,parent=priority_flood(z,valid)
        self.assertEqual(trace(filled,valid,parent,(2,1),1,1),([(2,1)],'invalid_neighbor'))
        self.assertEqual(trace(filled,valid,parent,(2,2),1,1),([],'invalid_start'))

    def test_invalid_inputs_fail_closed(self):
        with self.assertRaises(ValueError):priority_flood(np.ones((2,2)),np.zeros((2,2),dtype=bool))
        with self.assertRaises(ValueError):trace(np.ones((2,2)),np.ones((2,2)),np.ones((2,2)),(0,0),0,1)

if __name__=='__main__':unittest.main()
