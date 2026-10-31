import json,unittest
from pathlib import Path
from shapely.geometry import shape,Point
ROOT=Path(__file__).resolve().parents[1]
class AsiaOceaniaReferences(unittest.TestCase):
 def setUp(self):
  self.ref=json.loads((ROOT/'data/references/asia-oceania-reference.geojson').read_text());self.geoms={f['properties']['name']:shape(f['geometry']) for f in self.ref['features']}
 def test_valid_sea_geometries(self):
  self.assertTrue(all(g.is_valid for g in self.geoms.values()))
 def test_philippine_open_water(self):
  self.assertIn('Philippine Sea',self.ref['open_waters']);self.assertNotIn('Philippine Sea',self.geoms)
 def test_timor_western_headlands(self):
  g=self.geoms['Timor Sea'];self.assertLess(g.boundary.distance(Point(126+55/60,-(13+47/60))),1e-10);self.assertLess(g.boundary.distance(Point(122+51/60,-(10+56/60+30/3600))),1e-10)
 def test_named_island_groups(self):
  groups={e['name']:e['group'] for e in self.ref['land_groups']};self.assertEqual(groups['Tanimbar Islands'],2);self.assertEqual(groups['Kei and Tayandu Islands'],2);self.assertEqual(groups['Raja Ampat, including Kofiau, Gag and Waigeo satellites'],6)
if __name__=='__main__':unittest.main()
