#!/usr/bin/env python3
import unittest
import build_closed_water_assignments_final_selfadj_classindex_exclusive_progress_20261103T0815Z as cwa
from build_closed_water_assignments_final_selfadj_classindex_exclusive_progress_20261103T0815Z import candidate_method, intervals_cover

class FakeRLE:
    def __init__(self, rows): self.rows=rows
    def row(self,y): return self.rows[y]

def encode(values):
    out=[];last=values[0]
    for i,v in enumerate(values[1:],1):
        if v!=last:out.append((i,last));last=v
    out.append((len(values),last));return out

class ClosedWaterAssignmentTests(unittest.TestCase):
    def setUp(self): self.old_w,self.old_h=cwa.W,cwa.H;cwa.W,cwa.H=5,3
    def tearDown(self): cwa.W,cwa.H=self.old_w,self.old_h
    def test_partial_zero_superset(self):
        self.assertTrue(intervals_cover([(0,3),(5,10)],[(1,3),(6,8)]))
        self.assertFalse(intervals_cover([(0,3),(6,10)],[(1,3),(5,8)]))
    def test_assignment_policies(self):
        self.assertEqual(candidate_method([2]),'direct-single-final-shore-class')
        self.assertEqual(candidate_method([1,3,1]),'nearest-final-assigned-shore')
        self.assertEqual(candidate_method([2],unknown_zero_edges=4),'pending-unknown-code-0-boundary')
        self.assertEqual(candidate_method([2],source_cut_edges=1),'retain-ocean-parent-source-cut-review')
        self.assertEqual(candidate_method([2],crop_edge=True),'open-at-grid-crop-review')
    def test_three_cell_component_internal_zeros_excluded(self):
        raster=FakeRLE([encode([1,0,0,2,2]),encode([1,0,3,2,2]),encode([4,4,4,2,2])])
        got=cwa.edge_counts_for_components({7:[(0,1,3),(1,1,2)]},raster)[7]
        self.assertEqual(got['unknown_zero_edges'],0)
        self.assertEqual(got['codes'],{1:2,2:1,3:2,4:1})
    def test_dateline_wrap_excludes_same_component_but_keeps_external_zero(self):
        raster=FakeRLE([encode([3,3,3,3,3]),encode([0,1,2,3,0]),encode([0,1,1,3,0])])
        got=cwa.edge_counts_for_components({7:[(1,0,1),(1,4,5)]},raster)[7]
        self.assertEqual(got['unknown_zero_edges'],2)
        self.assertEqual(got['codes'],{1:1,3:3})
    def test_zero_boundary_of_distinct_component_stays_unknown(self):
        raster=FakeRLE([encode([1,0,0,2,2]),encode([1,0,0,2,2]),encode([1,1,1,2,2])])
        got=cwa.edge_counts_for_components({7:[(1,1,3)],8:[(0,1,3)]},raster)[7]
        self.assertEqual(got['unknown_zero_edges'],2)
        self.assertEqual(got['codes'],{1:3,2:1})

if __name__=='__main__':unittest.main(verbosity=2)
