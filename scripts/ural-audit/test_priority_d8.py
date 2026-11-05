import unittest
import numpy as np
from priority_d8 import drainage, neighbor_distances
from pyproj import Geod, Transformer

class Grid:
    a=30.;b=0.;c=400000.;d=0.;e=-30.;f=6500000.

class DrainageTest(unittest.TestCase):
    def test_gradient_and_void_barrier(self):
        r,c=np.indices((9,9));z=(20-c+2*np.abs(r-4)).astype(float);valid=np.ones((9,9),dtype=bool);valid[2,2]=False
        roots,flood,flow=drainage(z,valid,Grid(),'EPSG:32640')
        self.assertEqual(roots[2,2],-2)
        self.assertEqual(roots[4,4],4*9+8)
        self.assertEqual(roots[3,3],roots[5,3])
        self.assertTrue(np.isinf(flood[2,2]))

    def test_cached_edges_match_wgs84_and_mask(self):
        valid=np.ones((3,4),dtype=bool);valid[1,2]=False;t=Grid()
        edges=neighbor_distances(valid,t,'EPSG:32640',chunk_rows=1)
        inv=Transformer.from_crs(32640,4326,always_xy=True);geod=Geod(ellps='WGS84')
        def center(r,c):return inv.transform(t.c+(c+.5)*t.a,t.f+(r+.5)*t.e)
        self.assertAlmostEqual(edges[0,0,0],geod.inv(*center(0,0),*center(0,1))[2],delta=1e-8)
        self.assertAlmostEqual(edges[2,0,0],geod.inv(*center(0,0),*center(1,1))[2],delta=1e-8)
        self.assertAlmostEqual(edges[3,0,1],geod.inv(*center(0,1),*center(1,0))[2],delta=1e-8)
        self.assertEqual(edges[3,0,3],0)
        self.assertEqual(edges[1,0,2],0)

    def test_reject_unprojected(self):
        with self.assertRaises(ValueError):neighbor_distances(np.ones((3,4),bool),Grid(),'EPSG:4326')
    def test_all_eight_neighbor_directions(self):
        for dr in (-1,0,1):
            for dc in (-1,0,1):
                if not (dr or dc):continue
                z=np.full((3,3),99.);z[1,1]=100.;z[1+dr,1+dc]=90.
                roots,_,flow=drainage(z,np.ones((3,3),bool),Grid(),'EPSG:32640')
                self.assertEqual(flow[1,1],(1+dr)*3+1+dc,(dr,dc))
                self.assertEqual(roots[1,1],(1+dr)*3+1+dc,(dr,dc))
    def test_invalid_elevations_and_indices(self):
        z=np.ones((3,3));z[1,1]=np.nan
        with self.assertRaises(ValueError):drainage(z,np.ones((3,3),bool),Grid(),'EPSG:32640')
        huge=np.lib.stride_tricks.as_strided(np.zeros(1,dtype=bool),shape=(46341,46341),strides=(0,0))
        with self.assertRaises(ValueError):neighbor_distances(huge,Grid(),'EPSG:32640')
        class Bad(Grid):a=float('nan')
        with self.assertRaises(ValueError):neighbor_distances(np.zeros((3,3),bool),Bad(),'EPSG:32640')
    def test_isolated_valid_cell_does_not_gain_outlet(self):
        valid=np.zeros((3,3),bool);valid[1,1]=True
        roots,_,_=drainage(np.ones((3,3)),valid,Grid(),'EPSG:32640')
        self.assertEqual(roots[1,1],-2)
    def test_high_latitude_grid(self):
        class Polar(Grid):c=500000.;f=8700000.
        e=neighbor_distances(np.ones((3,3),bool),Polar(),'EPSG:32640')
        self.assertTrue(np.all(e[0,:,:-1]>0));self.assertTrue(np.all(e[1,:-1,:]>0))

if __name__=='__main__':unittest.main()

