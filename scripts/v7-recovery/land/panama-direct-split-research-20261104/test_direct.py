import tempfile,unittest
from pathlib import Path
import numpy as np
from direct import TripleRows,partition,rasterize_barriers,reject_center_hits,reject_invalid_line,reject_terminal_near_land,resolve_fragments,select_witnesses,verify_witness_assignments
from compare import nearest_side
class DirectTests(unittest.TestCase):
 def test_witness_seed_must_be_on_selected_land(self):
  ws=[{'lon':0,'lat':0,'inside':True},{'lon':1,'lat':0,'inside':True},{'lon':2,'lat':0,'inside':False}]
  seeds,checks,oriented=select_witnesses(ws,lambda w:(w['lon'],w['lat']),lambda x,y:x!=0,lambda lon,lat:1 if lon==0 else -1 if lon==2 else 0)
  self.assertEqual(seeds,{20:(1,0),21:(2,0)});self.assertEqual(checks,{20:[(1,0)],21:[(2,0)]});self.assertEqual(oriented,{20:1,21:1})
  with self.assertRaisesRegex(ValueError,'missing eligible'):select_witnesses(ws,lambda w:(w['lon'],w['lat']),lambda x,y:x==2,lambda lon,lat:1 if lon<2 else -1)
  with self.assertRaisesRegex(ValueError,'conflicting witness'):select_witnesses(ws,lambda w:(w['lon'],w['lat']),lambda x,y:True,lambda lon,lat:-1)
  with self.assertRaisesRegex(ValueError,'unambiguous orientation'):select_witnesses(ws,lambda w:(w['lon'],w['lat']),lambda x,y:True,lambda lon,lat:0)
 def test_every_eligible_witness_is_checked(self):
  with tempfile.TemporaryDirectory() as td:
   r=Path(td)/'rows';v=Path(td)/'spans';np.array([0,2],dtype='<u4').tofile(r);np.array([[0,2,20],[2,4,21]],dtype='<u4').tofile(v)
   stream=TripleRows(r,v,1);verify_witness_assignments(stream,{20:[(0,0),(1,0)],21:[(2,0)]})
   with self.assertRaisesRegex(ValueError,'witness assignment'):verify_witness_assignments(stream,{20:[(2,0)],21:[]})
   stream.close()
 def test_bounded_triple_rows_and_invalid_streams(self):
  with tempfile.TemporaryDirectory() as td:
   r=Path(td)/'rows';v=Path(td)/'spans'
   np.array([0,2,2,3],dtype='<u4').tofile(r)
   np.array([[1,2,3],[3,4,5],[5,7,8]],dtype='<u4').tofile(v)
   stream=TripleRows(r,v,3)
   self.assertEqual(stream.row(0).tolist(),[[1,2,3],[3,4,5]])
   self.assertEqual(stream.row(1).tolist(),[])
   self.assertEqual(stream.row(2).tolist(),[[5,7,8]])
   with self.assertRaisesRegex(ValueError,'out of range'):stream.row(3)
   stream.close()
   v.write_bytes(v.read_bytes()[:-1])
   with self.assertRaisesRegex(ValueError,'stream size'):TripleRows(r,v,3)
   np.array([0,2,1,3],dtype='<u4').tofile(r)
   with self.assertRaisesRegex(ValueError,'row offsets'):TripleRows(r,v,3)
 def test_fresh_line_splits_land_without_ocean_closure(self):
  with tempfile.TemporaryDirectory() as td:
   out=Path(td)/'graph';cuts=rasterize_barriers([[(2,0),(2,4)]],5,4)
   result=partition(lambda y:[(1,3)],5,4,cuts,{20:(1,1),21:(2,1)},out)
   self.assertEqual(result['cells_by_code'],{20:4,21:4});self.assertEqual(result['residual_cells'],0)
   self.assertEqual(np.fromfile(out/'partition-spans.u32le',dtype='<u4').reshape(-1,3).tolist(),[[1,2,20],[2,3,21]]*4)
 def test_crossing_or_wrapped_lines_rejected(self):
  for line in ([[0,0],[2,2],[0,2],[2,0]],[[179,0],[-179,0]],[[1,1],[1,1]]):
   with self.subTest(line=line),self.assertRaises(ValueError):reject_invalid_line(line)
  reject_invalid_line([[0,0],[1,1],[2,0]])
 def test_grid_center_hits_rejected(self):
  for path in ([[-1,0],[3,4]],[[1.5,0],[1.5,4]],[[0,2.5],[4,2.5]]):
   with self.subTest(path=path),self.assertRaisesRegex(ValueError,'cell center'):reject_center_hits(path,5,5)
  reject_center_hits([[2,0],[2,4]],5,5)
 def test_terminals_near_land_fail_closed(self):
  eligible=lambda x,y:(x,y)==(1,1)
  reject_terminal_near_land([[0,0],[5,5]],6,6,eligible)
  with self.assertRaisesRegex(ValueError,'endpoint too close'):
   reject_terminal_near_land([[1.5,1.5],[5,5]],6,6,eligible)
  with self.assertRaisesRegex(ValueError,'endpoint too close'):
   reject_terminal_near_land([[0,0],[2.5,1.5]],6,6,eligible)
 def test_fragment_codes_are_caller_supplied(self):
  cuts=rasterize_barriers([[(2,0),(2,4)]],5,4)
  self.assertEqual(resolve_fragments({1:[(1,1)],2:[(2,1)]},cuts,[[2,4],[2,0]],0,4,1,5,4,lambda x,y:True,side_codes=(31,32)),{1:32,2:31})
 def test_fragment_sides_and_disconnected_fail(self):
  cuts=rasterize_barriers([[(2,0),(2,4)]],5,4);line=[[2,4],[2,0]]
  self.assertEqual(resolve_fragments({7:[(1,1)],8:[(2,1)]},cuts,line,0,4,1,5,4,lambda x,y:True),{7:21,8:20})
  with self.assertRaisesRegex(ValueError,'does not touch'):resolve_fragments({9:[(0,0)]},cuts,line,0,4,1,5,4,lambda x,y:True)
  with self.assertRaisesRegex(ValueError,'does not touch'):resolve_fragments({9:[(1,1)]},cuts,line,0,4,1,5,4,lambda x,y:False)
  with self.assertRaisesRegex(ValueError,'conflicting line sides'):resolve_fragments({9:[(1,1),(2,1)]},cuts,line,0,4,1,5,4,lambda x,y:True)
  with self.assertRaisesRegex(ValueError,'duplicate'):resolve_fragments({7:[(1,1)],8:[(1,1)]},cuts,line,0,4,1,5,4,lambda x,y:True)
 def test_fragment_resource_cap(self):
  cuts=rasterize_barriers([[(2,0),(2,4)]],5,4)
  with self.assertRaisesRegex(ValueError,'resource cap'):resolve_fragments({1:[(1,0),(1,1)]},cuts,[[2,4],[2,0]],0,4,1,5,4,lambda x,y:True,max_cells=1)
 def test_fragment_endpoint_is_unresolved(self):
  from partition_core import CutEdges
  cuts=CutEdges();cuts.add_h(0,1)
  with self.assertRaisesRegex(ValueError,'ambiguous residual side'):resolve_fragments({1:[(1,0)]},cuts,[[2,3],[2,1]],0,4,1,5,4,lambda x,y:True)
 def test_horizontal_line_orients_both_sides(self):
  cuts=rasterize_barriers([[(0,2),(4,2)]],5,4)
  self.assertEqual(resolve_fragments({1:[(1,1)],2:[(1,2)]},cuts,[[0,2],[4,2]],0,4,1,5,4,lambda x,y:True),{1:20,2:21})
 def test_bent_line(self):
  from partition_core import CutEdges
  cuts=CutEdges();cuts.add_v(2,3)
  result=resolve_fragments({1:[(3,2)]},cuts,[[1,4],[1,1],[4,1]],0,4,1,5,5,lambda x,y:True)
  self.assertEqual(result[1],20)
 def test_fragment_opposed_nearest_segments_unresolved(self):
  from partition_core import CutEdges
  cuts=CutEdges();cuts.add_h(0,0)
  with self.assertRaisesRegex(ValueError,'ambiguous residual side'):resolve_fragments({1:[(0,0)]},cuts,[[-1,-1],[-1,1],[3,2],[1,-1],[1,1]],-.5,.5,1,5,5,lambda x,y:True)
 def test_cut_center_and_endpoint_fail_closed(self):
  line=[[0,0],[0,10]]
  self.assertEqual(nearest_side(0,5,line)[0],0);self.assertEqual(nearest_side(1,11,line)[0],0)
if __name__=='__main__':unittest.main()
