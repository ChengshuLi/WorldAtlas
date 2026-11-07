import struct,tempfile,unittest
from pathlib import Path
import full_coverage_policy as cp
U=struct.Struct('<I');P=struct.Struct('<II');T=struct.Struct('<III')
def save(p,fmt,x):p.write_bytes(b''.join(fmt.pack(*v) for v in x));return p
class CoverageIndexTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);p=Path(self.tmp.name)
  self.paths=[save(p/'pr',U,[(0,),(3,),(4,)]),save(p/'pv',P,[(2,1),(8,17),(10,1),(10,1)]),save(p/'cr',U,[(0,),(2,),(2,)]),save(p/'cv',T,[(2,5,10),(5,8,11)])]
  self.grid={'width':10,'height':2,'west':-180,'north':90,'step':36}
 def test_indexed_selector_parity(self):
  counts={'10':3,'11':3};idx=cp.build_coverage_index(self.grid,*self.paths)
  self.assertEqual(cp.select_all_centers(counts,self.grid,*self.paths),cp.select_all_centers(counts,self.grid,*self.paths,coverage_index=idx))
 def test_changed_generation_rejected(self):
  idx=cp.build_coverage_index(self.grid,*self.paths);self.paths[3].write_bytes(T.pack(2,5,11)+T.pack(5,8,10))
  with self.assertRaisesRegex(ValueError,'generation mismatch'):cp.indexed_totals(idx,{10},self.grid,*self.paths)
 def test_physical_component_mismatch_rejected(self):
  save(self.paths[2],U,[(0,),(2,),(2,)]);save(self.paths[3],T,[(2,4,10),(5,8,11)])
  with self.assertRaisesRegex(ValueError,'component/physical mismatch'):cp.build_coverage_index(self.grid,*self.paths)
 def test_forged_index_rejected(self):
  with self.assertRaisesRegex(ValueError,'must be built'):cp.CoverageIndex((10,2,()),{10:999})
  idx=cp.build_coverage_index(self.grid,*self.paths)
  forged=object.__new__(cp.CoverageIndex)
  with self.assertRaisesRegex(ValueError,'invalid coverage index'):cp.indexed_totals(forged,{10},self.grid,*self.paths)
if __name__=='__main__':unittest.main()
