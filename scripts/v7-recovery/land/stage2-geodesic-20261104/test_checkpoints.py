import tempfile,pathlib,unittest,subprocess,sys,numpy as np
import checkpoints as c
class Checkpoints(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.p=pathlib.Path(self.t.name)/'state';self.i={'input':'abc','code':'def'};self.a={'roots':np.array([2,5],dtype='u4'),'hints':np.array([18,20],dtype='u1'),'upper':np.array([100.,200.]),'amb':np.array([False,True]),'best':np.array([[np.inf,100,np.inf,np.inf,np.inf,np.inf],[np.inf,np.inf,np.inf,200,np.inf,np.inf]])}
 def test_roundtrip(self):
  c.write(self.p,self.i,'cert',12,9,self.a,0,0);m,a=c.read(self.p,self.i,self.a['roots']);self.assertEqual((m['phase'],m['cursor'],m['queries']),('cert',12,9));self.assertTrue(np.array_equal(a['amb'],self.a['amb']))
 def test_oversized_checkpoint(self):
  self.p.write_bytes(b'x'*(3<<20))
  with self.assertRaisesRegex(ValueError,'size limit'):c.read(self.p,self.i,self.a['roots'])
 def test_wrong_identity(self):
  c.write(self.p,self.i,'cert',12,9,self.a,0,0)
  with self.assertRaisesRegex(ValueError,'identity'):c.read(self.p,{'input':'different'},self.a['roots'])
 def test_wrong_roots(self):
  c.write(self.p,self.i,'cert',12,9,self.a,0,0)
  with self.assertRaisesRegex(ValueError,'state'):c.read(self.p,self.i,np.array([2,6],dtype='u4'))
 def test_disk_guard(self):
  with self.assertRaisesRegex(RuntimeError,'disk guard'):c.write(self.p,self.i,'cert',12,9,self.a,0,1<<60)
  self.assertFalse(self.p.exists())
 def test_memory_guard(self):
  with self.assertRaisesRegex(RuntimeError,'memory guard'):c.write(self.p,self.i,'cert',12,9,self.a,10**15,0)
 def test_exclusive_lock(self):
  with c.exclusive_lock(self.p):
   cmd='import sys; import checkpoints as c;\nwith c.exclusive_lock(sys.argv[1]): pass'
   r=subprocess.run([sys.executable,'-c',cmd,str(self.p)],capture_output=True,text=True)
   self.assertNotEqual(r.returncode,0);self.assertIn('locked by another process',r.stderr)
  with c.exclusive_lock(self.p):pass
 def test_bad_state(self):
  self.a['hints'][0]=3;c.write(self.p,self.i,'cert',12,9,self.a,0,0)
  with self.assertRaisesRegex(ValueError,'state'):c.read(self.p,self.i,self.a['roots'])
if __name__=='__main__':unittest.main()
