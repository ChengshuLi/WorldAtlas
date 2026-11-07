import tempfile,pathlib,unittest,numpy as np
from baseline_runner import run
from certificate import CertificateIndex
from test_exact_index import Exact
class Runner(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.d=pathlib.Path(self.temp.name);self.cr=self.d/'runs';self.rows=self.d/'rows';self.seeds=[(3,1,17),(3,6,18),(3,12,19),(3,18,20),(3,24,21),(3,30,22)];self.w=36
  # component order by row, each selected root may occupy several runs
  rows=[[] for _ in range(18)];rows[3]=[(1,2,1),(6,7,2),(12,13,3),(18,19,4),(24,25,4),(30,31,4)];rows[4]=[(1,3,10),(7,8,11)];rows[5]=[(5,6,10)]
  off=[0];z=[]
  for row in rows:z.extend(row);off.append(len(z))
  np.asarray(z,dtype='<u4').tofile(self.cr);np.asarray(off,dtype='<u4').tofile(self.rows);self.co=np.asarray(off,dtype='<u4');self.roots=np.array([10,11],dtype='u4');self.hints=np.array([20,17],dtype='u1');self.seedroots=np.array([1,2,3,4],dtype='u4');maker=Exact();tmp,self.exact,self.cert=maker.make(self.seeds,self.w);self.addCleanup(tmp.cleanup);self.cp=self.d/'state';self.identity={'test':'v1'}
 def runit(self,resume=False,guard=lambda:None):return run(self.cr,self.co,self.roots,self.hints,self.seedroots,self.w,self.cert,self.exact,self.cp,self.identity,resume=resume,chunk=4,checkpoint_seconds=0,block_records=2,guard=guard)
 def test_complete_matches_bruteforce(self):
  out=self.runit();expect=[next(iter(Exact().oracle([(4,1,3),(5,5,6)],self.seeds,36,.00001))),next(iter(Exact().oracle([(4,7,8)],self.seeds,36,.00001)))];self.assertEqual(out['codes'].tolist(),expect);self.assertEqual(len(out['codes']),2)
 def test_resume_after_complete(self):
  a=self.runit();b=self.runit(True);self.assertEqual(a['codes'].tolist(),b['codes'].tolist())
 def test_interrupt_then_resume(self):
  n=[0]
  def fail():
   n[0]+=1
   if n[0]>9 and self.cp.exists():raise RuntimeError('simulated interrupt')
  with self.assertRaisesRegex(RuntimeError,'interrupt'):self.runit(guard=fail)
  self.assertTrue(self.cp.exists());a=self.runit(True);self.assertEqual(len(a['codes']),2)
 def test_identity_mismatch(self):
  self.runit();self.identity={'test':'v2'}
  with self.assertRaisesRegex(ValueError,'identity'):self.runit(True)
if __name__=='__main__':unittest.main()
