import unittest
import numpy as np
import closed_water_core as c
from test_helpers import rle
from test_coastal_core import snap


def policy_snapshot():
 s=snap();tie=s['policies'][0]['definition']['tie_rules']
 s['policies']=[{'id':'test-closed','kind':'closed_water_assignment','evidence':{'execution_status':'selected_for_research'},'definition':{
  'method':'closed_water_component_v1','boundary_participants':'adjacent_final_water_or_assigned_land',
  'distance':'spherical_segment','earth_radius_metres':'6371008.8','latitude_grid_edge_contacts':'report_only',
  'multiple_participants':'nearest_assigned_land_shore','no_participants':'report_only','one_participant':'direct_fill',
  'source_cut_contacts':'retain_ocean_parent_source_cut_review','tie_rules':tie,'unresolved_zero_neighbors':'report_only',
  'shore_geometry':'physical_land_water_grid_edges'}}]
 return s


class ClosedTest(unittest.TestCase):
 def setup_case(self):
  p=np.full((5,12),17,dtype=np.uint32);q=np.full((5,12),17,dtype=np.uint32)
  p[2,4:6]=1;q[2,4:6]=0
  _,pairs,t=c.policy(policy_snapshot(),allow_selected_research=True)
  return p,q,pairs,t
 def test_direct_boundary_and_source_cut(self):
  p,q,pairs,_=self.setup_case();components,r=c.adjacency({2:[(4,6,7)]},rle(p),rle(q),12,5,pairs)
  self.assertEqual(components[7],[(2,4,6)]);self.assertEqual(r[7]['codes'],{1:6})
  self.assertEqual(c.component_method(r[7],0),'direct-single-boundary-continent')
  self.assertEqual(c.component_method(r[7],1),'pending-source-cut-contact')
 def test_mixed_boundary_and_unknown_zero(self):
  p,q,pairs,_=self.setup_case();q[1,4]=18
  _,r=c.adjacency({2:[(4,6,7)]},rle(p),rle(q),12,5,pairs)
  self.assertEqual(set(r[7]['codes']),{1,2});self.assertEqual(c.component_method(r[7],0),'nearest-participant-shore')
  p[2,6]=1;q[2,6]=0
  _,r=c.adjacency({2:[(4,6,7)]},rle(p),rle(q),12,5,pairs)
  self.assertEqual(r[7]['unknown_zero_edges'],1);self.assertEqual(c.component_method(r[7],0),'pending-unknown-zero-boundary')
 def test_seeded_ocean_neighbor_remains_unresolved_prefill_zero(self):
  # Ocean partition can later label x6 as seeded ocean, but prefill remains 0.
  # This classifier never imports that ocean label or assigns the neighbor.
  p,q,pairs,_=self.setup_case();p[2,6]=1;q[2,6]=0
  _,summary=c.adjacency({2:[(4,6,7)]},rle(p),rle(q),12,5,pairs)
  self.assertEqual(summary[7]['unknown_zero_edges'],1)
  self.assertEqual(c.component_method(summary[7],0),'pending-unknown-zero-boundary')
 def test_crop_and_wrap(self):
  p,q,pairs,_=self.setup_case();p[0,0]=1;q[0,0]=0
  _,r=c.adjacency({0:[(0,1,9)]},rle(p),rle(q),12,5,pairs)
  self.assertTrue(r[9]['crop_edge']);self.assertEqual(c.component_method(r[9],0),'pending-grid-crop-edge')
  p[3,0]=p[3,11]=1;q[3,0]=q[3,11]=0
  _,r=c.adjacency({3:[(0,1,9),(11,12,9)]},rle(p),rle(q),12,5,pairs)
  self.assertEqual(r[9]['unknown_zero_edges'],0)
 def test_invalid_components_and_prefill(self):
  p,q,pairs,_=self.setup_case()
  with self.assertRaisesRegex(ValueError,'overlapping'):c.adjacency({2:[(4,6,7),(5,7,8)]},rle(p),rle(q),12,5,pairs)
  q[2,4]=7
  with self.assertRaisesRegex(ValueError,'physical/prefill'):c.adjacency({2:[(4,6,7)]},rle(p),rle(q),12,5,pairs)
 def test_internal_cut_same_component_and_invalid_edges(self):
  # Upstream partition may report zero when both sides reconnect as one root.
  by={2:[(4,6,7)]};self.assertEqual(c.cut_contacts(by,[(0,2,4)],12,5),{7:1})
  self.assertEqual(c.cut_contacts({2:[(0,1,7),(11,12,7)]},[(2,2,0)],12,5),{7:1})
  with self.assertRaisesRegex(ValueError,'unique and sorted'):c.cut_contacts(by,[(0,2,4),(0,2,4)],12,5)
  with self.assertRaisesRegex(ValueError,'outside grid'):c.cut_contacts(by,[(1,4,4)],12,5)
 def test_policy_fails_closed(self):
  with self.assertRaisesRegex(ValueError,'opt-in'):c.policy(policy_snapshot())
  s=policy_snapshot();s['policies']=[]
  with self.assertRaisesRegex(ValueError,'policy'):c.policy(s,allow_selected_research=True)
  s=policy_snapshot();s['policies'][0]['definition']['unresolved_zero_neighbors']='direct_fill'
  with self.assertRaisesRegex(ValueError,'safety'):c.policy(s,allow_selected_research=True)

if __name__=='__main__':unittest.main()
