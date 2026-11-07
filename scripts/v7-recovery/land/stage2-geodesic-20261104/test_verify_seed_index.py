import tempfile,subprocess,struct,pathlib,unittest
HERE=pathlib.Path(__file__).resolve().parent
class Verify(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmpbin=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmpbin.cleanup);cls.bin=str(pathlib.Path(cls.tmpbin.name)/'verifier');subprocess.run(['g++','-O2','-std=c++17','-Wall','-Wextra','-Werror',str(HERE/'verify_seed_index.cpp'),'-lcrypto','-o',cls.bin],check=True)
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.d=pathlib.Path(self.tmp.name);self.tiles=self.d/'tiles';self.tiles.mkdir();rows=[[(2,0),(6,18),(16,0)],[(4,17),(12,0),(16,20)]]+[[(16,0)] for _ in range(6)];offs=[0];run=[];parts={}
  for y,seq in enumerate(rows):
   a=0
   for b,code in seq:
    run.append((b,code))
    if code:
     x=a
     while x<b:
      z=min(b,(x//4+1)*4);p=(y//4,x//4);parts.setdefault(p,[]).append((y,x,z,code));x=z
    a=b
   offs.append(len(run))
  (self.d/'rows').write_bytes(b''.join(struct.pack('<I',x) for x in offs));(self.d/'runs').write_bytes(b''.join(struct.pack('<II',*x) for x in run))
  for (y,x),z in parts.items():(self.tiles/f'{y:05}-{x:05}.bin').write_bytes(b''.join(struct.pack('<IIII',*v) for v in z))
 def tearDown(self):self.tmp.cleanup()
 def runv(self,*extra):
  return subprocess.run([self.bin,str(self.d/'rows'),str(self.d/'runs'),str(self.tiles),'16','8','4',*extra],capture_output=True,text=True)
 def test_valid(self):
  r=self.runv();self.assertEqual(r.returncode,0,r.stderr);self.assertIn('"status":"verified"',r.stdout)
 def test_corruption(self):
  f=next(self.tiles.glob('*.bin'));z=bytearray(f.read_bytes());z[-1]^=1;f.write_bytes(z);r=self.runv();self.assertNotEqual(r.returncode,0);self.assertIn('mismatch',r.stderr)
 def test_missing(self):
  next(self.tiles.glob('*.bin')).unlink();self.assertNotEqual(self.runv().returncode,0)
 def test_extra(self):
  (self.tiles/'00001-00002.bin').write_bytes(b'1234');self.assertNotEqual(self.runv().returncode,0)
 def test_obsolete_memory_argument_is_rejected_as_usage(self):
  r=self.runv('999999999999');self.assertNotEqual(r.returncode,0);self.assertIn('usage:',r.stderr)
if __name__=='__main__':unittest.main()
