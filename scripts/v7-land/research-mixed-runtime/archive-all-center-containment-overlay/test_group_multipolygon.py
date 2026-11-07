import hashlib,json,unittest
import polygon_policy
from test_polygon_resolution import ResolveTests
class MultiPolygonContainment(ResolveTests):
 def setgeom(self,g):
  self.file.write_text(json.dumps({'type':'FeatureCollection','features':[{'type':'Feature','properties':{'id':'f'},'geometry':g}]}));h=hashlib.sha256(self.file.read_bytes()).hexdigest()
  for z in (self.snap['sources'][0],self.snap['source_lineage_assets'][0],self.sources[0]):z['sha256']=h;z['size_bytes']=self.file.stat().st_size
  self.snap['features'][0]['geometry_sha256']=hashlib.sha256(json.dumps(g,sort_keys=True,separators=(',',':')).encode()).hexdigest();self.snap['affiliations'][0]['method']='component_containment_v1';self.policy=polygon_policy.adapt(self.snap,{'a'})
 def test_disjoint_parts_aggregate_before_whole_root_check(self):
  g={'type':'MultiPolygon','coordinates':[[[[-100,55],[-80,55],[-80,89],[-100,89],[-100,55]]],[[[-60,55],[-5,55],[-5,89],[-60,89],[-60,55]]]]};self.setgeom(g);claim=self.runv()['claims'][0];self.assertEqual(claim['component_ids'],[10]);self.assertEqual(claim['containment']['selected_cells'],3);self.assertEqual(claim['intersection']['multipolygon_part_count'],2);self.assertEqual(claim['intersection']['per_feature_root_inside_cells'],[{'10':3}])
 def test_overlapping_parts_rejected(self):
  g={'type':'MultiPolygon','coordinates':[[[[-100,55],[-50,55],[-50,89],[-100,89],[-100,55]]],[[[-80,55],[-20,55],[-20,89],[-80,89],[-80,55]]]]};self.setgeom(g)
  with self.assertRaisesRegex(ValueError,'invalid multipolygon'):self.runv()
 def test_partial_root_not_selected(self):
  g={'type':'MultiPolygon','coordinates':[[[[-100,55],[-80,55],[-80,89],[-100,89],[-100,55]]],[[[-20,55],[-10,55],[-10,89],[-20,89],[-20,55]]]]};self.setgeom(g)
  with self.assertRaisesRegex(ValueError,'no wholly covered components'):self.runv()
 def test_grid_center_on_part_boundary_is_rejected(self):
  g={'type':'MultiPolygon','coordinates':[[[[-90,55],[-75,55],[-75,89],[-90,89],[-90,55]]],[[[-70,55],[-5,55],[-5,89],[-70,89],[-70,55]]]]};self.setgeom(g)
  with self.assertRaisesRegex(ValueError,'boundary crosses grid cell center'):self.runv()
 def test_point_touching_parts_do_not_double_count(self):
  g={'type':'MultiPolygon','coordinates':[[[[-110,72],[-90,55],[-72,72],[-90,89],[-110,72]]],[[[-72,72],[-36,55],[0,72],[-36,89],[-72,72]]]]};self.setgeom(g);claim=self.runv()['claims'][0];self.assertEqual(claim['component_ids'],[10]);self.assertEqual(claim['intersection']['per_feature_root_inside_cells'],[{'10':3}])
 def test_hole_prevents_whole_component_selection(self):
  g={'type':'MultiPolygon','coordinates':[[[[-100,55],[-80,55],[-80,89],[-100,89],[-100,55]]],[[[-70,55],[-5,55],[-5,89],[-70,89],[-70,55]],[[-60,65],[-48,65],[-48,79],[-60,79],[-60,65]]]]};self.setgeom(g)
  with self.assertRaisesRegex(ValueError,'no wholly covered components'):self.runv()
 def test_empty_part_retains_nonempty_selection(self):
  g={'type':'MultiPolygon','coordinates':[[[[-100,55],[-5,55],[-5,89],[-100,89],[-100,55]]],[[[100,55],[110,55],[110,89],[100,89],[100,55]]]]};self.setgeom(g)
  claim=self.runv()['claims'][0];self.assertEqual(claim['component_ids'],[10]);self.assertEqual(claim['intersection']['multipolygon_part_count'],2)
if __name__=='__main__':unittest.main()
