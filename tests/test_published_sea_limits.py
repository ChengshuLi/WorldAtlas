import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from refine_published_sea_limits import ocean_connected_overhang
import numpy as np
from rasterio.features import rasterize
from rasterio.transform import from_origin
from shapely.geometry import Polygon,MultiPolygon,GeometryCollection,mapping,box
from shapely.ops import unary_union

class PublishedSeaLimitsTests(unittest.TestCase):
    def test_enclosed_source_difference_is_preserved(self):
        self.assertEqual(ocean_connected_overhang({11,12,13,66},{11},10),{11,12,13})
    def test_longitude_wrap_connects(self):
        self.assertEqual(ocean_connected_overhang({20,29,28},{20},10),{20,29,28})
    def test_corner_contact_does_not_connect(self):
        self.assertEqual(ocean_connected_overhang({11,22},{11},10),{11})
    def test_no_ocean_seed_changes_nothing(self):
        self.assertEqual(ocean_connected_overhang({11,12},set(),10),set())
    def test_collection_raster_is_exact_union(self):
        ring=Polygon([(0,0),(4,0),(4,4),(0,4)],holes=[[(1,1),(3,1),(3,3),(1,3)]])
        parts=[MultiPolygon([ring]),box(1,1,2,3)]
        def draw(g):return rasterize([(mapping(g),1)],out_shape=(4,4),transform=from_origin(0,4,1,1),dtype='uint8')
        np.testing.assert_array_equal(draw(GeometryCollection(parts)),draw(unary_union(parts)))
    def test_strip_clipping_preserves_center_sampling(self):
        g=Polygon([(-2,-2),(7,-1),(8,9),(1,8)],holes=[[(2,2),(5,2),(5,5),(2,5)]])
        tf=from_origin(0,8,1,1)
        expected=rasterize([(mapping(g),1)],out_shape=(8,8),transform=tf,dtype='uint8')
        strips=[]
        for y in range(0,8,2):
            clipped=g.intersection(box(0,6-y,8,8-y))
            strips.append(rasterize([(mapping(clipped),1)],out_shape=(2,8),transform=from_origin(0,8-y,1,1),dtype='uint8'))
        np.testing.assert_array_equal(np.vstack(strips),expected)
if __name__=='__main__':unittest.main()
