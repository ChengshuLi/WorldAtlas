import importlib.util,math,sys,unittest
from pathlib import Path
from osgeo import ogr
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT/'scripts/v7-replay'),str(ROOT/'scripts/v2-baseline')]
PATHS=[ROOT/'scripts/v2-baseline/build_seed.py',ROOT/'scripts/v2-baseline/build_regions.py',ROOT/'scripts/v7-land/mainland-seed-l2/rasterizer/build_seed.py',ROOT/'scripts/v7-recovery/land/neon-mainland-regions-20261104/rasterizer/build_seed.py']
class NumericalBoundaryGuard(unittest.TestCase):
 def test_coordinate_box_rejects_boundary_and_near_boundary(self):
  geom=ogr.CreateGeometryFromWkt('POLYGON ((0 0, 2 0, 2 2, 0 2, 0 0))')
  for i,p in enumerate(PATHS):
   spec=importlib.util.spec_from_file_location('witness_guard_'+str(i),p);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
   for point,expected in [((1,0),True),((1,5e-13),True),((1,2e-12),False),((1,1),False)]:
    with self.subTest(path=str(p),point=point):self.assertEqual(mod.witness_boundary_ambiguous(geom,*point),expected)
   with self.assertRaises(ValueError):mod.witness_boundary_ambiguous(geom,float('nan'),0)
 def test_high_longitude_threshold_is_conservative(self):
  geom=ogr.CreateGeometryFromWkt('POLYGON ((179 0, 180 0, 180 2, 179 2, 179 0))')
  for i,p in enumerate(PATHS):
   spec=importlib.util.spec_from_file_location('high_guard_'+str(i),p);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
   self.assertTrue(mod.witness_boundary_ambiguous(geom,math.nextafter(180-1e-12,math.inf),1))
   self.assertFalse(mod.witness_boundary_ambiguous(geom,180-2e-12,1))
 def test_diagonal_square_is_more_conservative_than_old_disk(self):
  geom=ogr.CreateGeometryFromWkt('POLYGON ((0 0, 2 2, 0 2, 0 0))')
  spec=importlib.util.spec_from_file_location('guard',PATHS[0]);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
  self.assertGreater(1.5/math.sqrt(2),1.0)  # abstract old epsilon-disk geometry
  self.assertTrue(mod.witness_boundary_ambiguous(geom,1,1+1.5e-12))
if __name__=='__main__':unittest.main()
