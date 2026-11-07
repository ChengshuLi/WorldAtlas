import copy
import unittest
from pyproj import Geod
from geodesic_spring_join import build

OSM=b'''<osm><node id="1" lon="59.4185198" lat="54.7035941"/><relation id="214415" version="122"><member type="node" ref="1" role="spring"/></relation></osm>'''
class JoinTest(unittest.TestCase):
 def setUp(self):
  self.g={'type':'LineString','coordinates':[[59.419,54.7034],[59.41871378709666,54.703513984728765],[59.4185198,54.7035941],[59.4184,54.7036]]}
 def test_join_preserves_line_and_follows_geodesic(self):
  out,report=build(self.g,OSM);self.assertEqual(report['segments'],16);self.assertEqual(out['coordinates'][:2],self.g['coordinates'][:2]);self.assertEqual(out['coordinates'][-2:],self.g['coordinates'][-2:]);p=out['coordinates'][1:18];g=Geod(ellps='WGS84');steps=[g.inv(*a,*b)[2] for a,b in zip(p,p[1:])];self.assertTrue(all(d<1 for d in steps));self.assertAlmostEqual(sum(steps),report['length_wgs84_m'],places=7)
 def test_reject_wrong_spring(self):
  with self.assertRaises(ValueError):build(self.g,OSM.replace(b'role="spring"',b'role="mouth"'))
 def test_reject_wrong_join(self):
  g=copy.deepcopy(self.g);g['coordinates'][1]=[59.42,54.70]
  with self.assertRaises(ValueError):build(g,OSM)
if __name__=='__main__':unittest.main()
