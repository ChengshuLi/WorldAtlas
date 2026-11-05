import unittest
import numpy as np
from affine import Affine
from pyproj import Geod
from spring_connector_graph import graph_route


class Identity:
    def transform(self,x,y): return x,y


class SpringConnectorGraphTest(unittest.TestCase):
    def test_connected_interface_uses_geodesic_lengths(self):
        labels=np.array([[1,2],[1,2]],dtype=np.uint8)
        transform=Affine(.001,0,0,0,-.001,.002)
        result=graph_route(labels,transform,Identity(),(.001,.002),(.001,0))
        self.assertEqual(result['component_count'],1)
        self.assertAlmostEqual(result['start_join_m'],0)
        self.assertAlmostEqual(result['end_join_m'],0)
        expected=Geod(ellps='WGS84').inv(.001,.002,.001,0)[2]
        self.assertAlmostEqual(result['divide_length_m'],expected,places=5)

    def test_unknown_cells_do_not_create_an_interface(self):
        with self.assertRaisesRegex(ValueError,'no shared interface'):
            graph_route(np.array([[1,0,2]],dtype=np.uint8),Affine.identity(),Identity(),(0,0),(1,0))


if __name__=='__main__':unittest.main()
