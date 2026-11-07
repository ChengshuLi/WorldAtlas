import os,struct,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from full_coverage_policy import select_all_centers, build_coverage_index
U=struct.Struct('<I');P=struct.Struct('<II');T=struct.Struct('<III')
class Tests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);p=Path(self.t.name)
  def write(n,fmt,rows):
   x=p/n;x.write_bytes(b''.join(fmt.pack(*(v if isinstance(v,tuple) else (v,))) for v in rows));return x
  self.args=[write('pr',U,[0,3,4]),write('pv',P,[(2,1),(8,17),(10,1),(10,1)]),write('cr',U,[0,2,2]),write('cv',T,[(2,5,10),(5,8,11)])];self.grid={'width':10,'height':2};self.guard=lambda:None
 def run_it(self,d):return select_all_centers(d,self.grid,*self.args,self.guard)
 def test_contained_and_partial(self):
  ids,t=self.run_it({'10':3,'11':2});self.assertEqual(ids,[10]);self.assertEqual((t['selected_cells'],t['excluded_partial_count'],t['excluded_partial_cells']),(3,1,3))
 def test_indexed_results_match_existing_selector(self):
  index=build_coverage_index(self.grid,*self.args,self.guard)
  for d in ({'10':3,'11':2},{'10':3},{'11':3}):
   with self.subTest(counts=d):self.assertEqual(select_all_centers(d,self.grid,*self.args,self.guard,coverage_index=index),self.run_it(d))
  for d in ({'10':4},{'10':0},{'010':1},{'999':1},{'10':True},{'10':1}):
   with self.subTest(invalid=d):
    with self.assertRaises(ValueError):select_all_centers(d,self.grid,*self.args,self.guard,coverage_index=index)
 def test_index_fails_closed_on_generation_change(self):
  index=build_coverage_index(self.grid,*self.args,self.guard)
  self.args[3].write_bytes(T.pack(2,4,10)+T.pack(5,8,11))
  with self.assertRaisesRegex(ValueError,'generation mismatch'):select_all_centers({'10':3},self.grid,*self.args,self.guard,coverage_index=index)
 def test_index_rejects_invalid_physical_component_coverage(self):
  self.args[3].write_bytes(T.pack(2,4,10)+T.pack(5,8,11))
  with self.assertRaises(ValueError):build_coverage_index(self.grid,*self.args,self.guard)
 def test_invalid_counts(self):
  for d in ({'10':4},{'10':0},{'010':1},{'999':1},{'10':True}):
   with self.subTest(d=d),self.assertRaises(ValueError):self.run_it(d)
 def test_component_mismatch(self):
  self.args[3].write_bytes(T.pack(2,4,10)+T.pack(5,8,11))
  with self.assertRaises(ValueError):self.run_it({'10':2})
 def test_empty_selection(self):
  with self.assertRaises(ValueError):self.run_it({'10':1})
if __name__=='__main__':unittest.main()
