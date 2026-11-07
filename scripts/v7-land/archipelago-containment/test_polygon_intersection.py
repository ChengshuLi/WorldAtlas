import struct,tempfile,unittest
from pathlib import Path
from polygon_intersection import intersect,reject_boundary_centers
U=struct.Struct('<I');P=struct.Struct('<II');T=struct.Struct('<III')
def save(p,fmt,x):p.write_bytes(b''.join(fmt.pack(*v) if isinstance(v,tuple) else fmt.pack(v) for v in x));return p
class IntersectionTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);b=Path(self.t.name);self.pr=save(b/'pr',U,[0,3,4]);self.pv=save(b/'pv',P,[(2,1),(8,17),(10,1),(10,1)]);self.cr=save(b/'cr',U,[0,2,2]);self.cv=save(b/'cv',T,[(2,5,10),(5,8,11)]);self.grid={'width':10,'height':2,'west':-180,'north':90,'step':36};self.g={'type':'Polygon','coordinates':[[[-105,55],[-40,55],[-40,89],[-105,89],[-105,55]]]}
 def runv(self,inc=[],exc=[]):return intersect([self.g],self.grid,self.pr,self.pv,self.cr,self.cv,inc,exc,lambda:None)
 def test_intersection(self):
  roots,report=self.runv();self.assertEqual(roots,[10]);self.assertEqual(report['per_feature_root_inside_cells'],[{'10':2}])
 def test_include_and_exclude(self):self.assertEqual(self.runv([{'lon':'54','lat':'72'}],[{'lon':'-90','lat':'72'}])[0],[11])
 def test_exclude_not_hit(self):
  with self.assertRaisesRegex(ValueError,'inclusion/exclusion'):self.runv(exc=[{'lon':'54','lat':'72'}])
 def test_witness_on_boundary(self):
  with self.assertRaisesRegex(ValueError,'grid boundary'):self.runv(inc=[{'lon':'0','lat':'72'}])
 def test_bad_component_coverage(self):
  save(self.cv,T,[(2,4,10),(5,8,11)])
  with self.assertRaisesRegex(ValueError,'component/physical'):self.runv()
 def test_boundary_on_center_rejected(self):
  self.g['coordinates'][0][0]=[-90,72];self.g['coordinates'][0][-1]=[-90,72]
  with self.assertRaisesRegex(ValueError,'cell center'):self.runv()
 def test_non_dyadic_grid_rejected(self):
  self.grid['width']=7;self.grid['step']=360/7
  with self.assertRaisesRegex(ValueError,'non-dyadic'):reject_boundary_centers(self.g,self.grid,lambda:None)
if __name__=='__main__':unittest.main()
