import tempfile,pathlib,unittest,numpy as np
import engine
class Fake:
 def certify_runs(self,y,a,b,u,h,t):return y!=2
class Traversal(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);p=pathlib.Path(self.t.name);self.r=p/'runs';self.o=p/'rows';np.asarray([[0,3,10],[5,9,1],[0,2,11],[4,10,10],[0,3,12]],dtype='<u4').tofile(self.r);np.asarray([0,2,3,4,5],dtype='<u4').tofile(self.o);self.co=engine.offsets(self.o,4,5);self.roots=np.array([10,11,12],dtype='u4');self.seed=np.array([1],dtype='u4')
 def test_first_points(self):
  y,x=engine.first_points(self.r,self.co,self.roots,self.seed,16);self.assertEqual(y.tolist(),[0,1,3]);self.assertEqual(x.tolist(),[0,0,0])
 def test_all_runs_and_resume(self):
  a=np.zeros(3,dtype=bool);engine.certificate_pass(self.r,self.co,self.roots,self.seed,Fake(),[1,1,1],[17,18,19],a,chunk=2,block_records=2);self.assertEqual(a.tolist(),[True,False,False])
  b=np.zeros(3,dtype=bool);engine.certificate_pass(self.r,self.co,self.roots,self.seed,Fake(),[1,1,1],[17,18,19],b,cursor=2,chunk=2,block_records=2);self.assertEqual(b.tolist(),[True,False,False])
 def test_unknown_component(self):
  with self.assertRaisesRegex(ValueError,'unknown'):engine.first_points(self.r,self.co,np.array([10,11],dtype='u4'),self.seed,16)
 def test_prefix_counts(self):
  self.assertEqual(engine.prefix_query_count(self.r,self.roots,self.seed,2,chunk=2),2)
  self.assertEqual(engine.prefix_query_count(self.r,self.roots,self.seed,5,chunk=2,amb=[True,False,False]),5)
 def test_truncated(self):
  with open(self.r,'ab') as f:f.write(b'x')
  with self.assertRaisesRegex(ValueError,'stream'):list(engine.blocks(self.r))
 def test_split(self):
  a=np.array([[0,8,10]],dtype='u4');got=list(engine.expanded(a,0,np.array([0,1],dtype='u4'),np.array([10],dtype='u4'),self.seed,chunk=2));self.assertEqual(got[0][1].tolist(),[0,2,4,6]);self.assertEqual(got[0][2].tolist(),[2,4,6,8])
if __name__=='__main__':unittest.main()

class FakeExact:
 def nearest_run(self,y,a,b,u,t):return ({18:1.0} if y==2 else {17:5.0}),{}
class Fallback(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);p=pathlib.Path(self.t.name);self.r=p/'runs';self.o=p/'rows';np.asarray([[0,3,10],[5,9,1],[0,2,11],[4,10,10],[0,3,12]],dtype='<u4').tofile(self.r);np.asarray([0,2,3,4,5],dtype='<u4').tofile(self.o);self.co=engine.offsets(self.o,4,5);self.roots=np.array([10,11,12],dtype='u4');self.seed=np.array([1],dtype='u4')
 def test_last_run_changes_component(self):
  a=np.array([True,False,False]);b=np.full((3,6),np.inf);b[:,0]=10
  engine.exact_pass(self.r,self.co,self.roots,self.seed,FakeExact(),[17,17,17],a,b,chunk=2,block_records=2)
  out,t=engine.finalize([17,17,17],a,b);self.assertEqual(out.tolist(),[18,17,17]);self.assertEqual(t,[])
 def test_tie_lowest_code(self):
  b=np.full((1,6),np.inf);b[0,1]=1;b[0,2]=1
  out,t=engine.finalize([19],[True],b);self.assertEqual(out.tolist(),[18]);self.assertEqual(t[0]['codes'],[18,19])
 def test_near_tolerance_fails(self):
  b=np.full((1,6),np.inf);b[0,0]=1;b[0,1]=1.00001
  with self.assertRaisesRegex(ValueError,'numerical boundary'):engine.finalize([17],[True],b)
