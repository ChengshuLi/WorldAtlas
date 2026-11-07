import builtins,errno,hashlib,json,struct,subprocess,tempfile,unittest
from pathlib import Path
from unittest import mock
import build_seed_tiles as t

def pin(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def packed(fmt,rows):return b''.join(struct.pack(fmt,*x) for x in rows)

class TileTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.bin=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.bin.cleanup);cls.verifier=Path(cls.bin.name)/'verify';subprocess.run(['g++','-O2','-std=c++17','-Wall','-Wextra','-Werror',str(Path(t.__file__).with_name('verify_seed_index.cpp')),'-lcrypto','-o',str(cls.verifier)],check=True)
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.inp=self.root/'input';self.inp.mkdir();self.rows=self.inp/'rows';self.runs=self.inp/'runs'
  data=[[(2,0),(7,17),(8,0)],[(1,18),(5,0),(8,19)],[(8,0)],[(4,20),(8,21)]];off=[0];flat=[]
  for row in data:flat+=row;off.append(len(flat))
  self.rows.write_bytes(packed('<I',[(v,) for v in off]));self.runs.write_bytes(packed('<II',flat));self.out=self.root/'tiles'
 def runbuild(self):return t.build(self.rows,self.runs,pin(self.rows),pin(self.runs),8,4,self.out,tile_size=4,disk_floor_bytes=0)
 def test_tiles_match_independent_verifier(self):
  report=self.runbuild();self.assertEqual(report['tile_count'],2);self.assertEqual(report['manifest_sha256'],pin(self.out/'manifest.txt'))
  p=subprocess.run([str(self.verifier),str(self.rows),str(self.runs),str(self.out),'8','4','4'],capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(json.loads(p.stdout)['status'],'verified')
 def test_descriptor_exhaustion_reopens_tiles_and_preserves_verification(self):
  real_open=builtins.open;injected=[]
  def open_once(path,mode='r',*args,**kwargs):
   if Path(path).name=='00000-00001.bin' and mode=='xb' and not injected:
    injected.append(True);raise OSError(errno.EMFILE,'simulated descriptor exhaustion')
   return real_open(path,mode,*args,**kwargs)
  with mock.patch('builtins.open',side_effect=open_once):report=self.runbuild()
  self.assertEqual(report['tile_count'],2);self.assertTrue(injected)
  p=subprocess.run([str(self.verifier),str(self.rows),str(self.runs),str(self.out),'8','4','4'],capture_output=True,text=True)
  self.assertEqual(p.returncode,0,p.stderr)
 def test_reopen_tamper_fails_readback(self):
  real_open=builtins.open;injected=[];tampered=[]
  def open_tamper(path,mode='r',*args,**kwargs):
   if Path(path).name=='00000-00001.bin' and mode=='xb' and not injected:
    injected.append(True);raise OSError(errno.EMFILE,'simulated descriptor exhaustion')
   if Path(path).name=='00000-00000.bin' and mode=='ab' and not tampered:
    tampered.append(True)
    with real_open(path,'ab') as f:f.write(b'bad')
   return real_open(path,mode,*args,**kwargs)
  with mock.patch('builtins.open',side_effect=open_tamper):
   with self.assertRaisesRegex(ValueError,'tile readback mismatch'):self.runbuild()
  self.assertTrue(tampered);self.assertFalse((self.out/'report.json').exists())
 def test_verifier_rejects_noncanonical_tile_name(self):
  self.runbuild();(self.out/'0-0.bin').write_bytes(b'extra')
  p=subprocess.run([str(self.verifier),str(self.rows),str(self.runs),str(self.out),'8','4','4'],capture_output=True,text=True)
  self.assertNotEqual(p.returncode,0);self.assertIn('noncanonical tile filename',p.stderr)
 def test_large_tile_grid_is_not_rejected_before_input_validation(self):
  with self.assertRaisesRegex(ValueError,'seed input hash mismatch'):
   t.build(self.rows,self.runs,'0'*64,pin(self.runs),1000001,1000001,self.out,tile_size=1,disk_floor_bytes=0)
  self.assertFalse(self.out.exists())
 def test_six_digit_tile_index_verifies(self):
  self.rows.write_bytes(packed('<I',[(0,),(2,)]));self.runs.write_bytes(packed('<II',[(100001,0),(100002,17)]))
  report=t.build(self.rows,self.runs,pin(self.rows),pin(self.runs),100002,1,self.out,tile_size=1,disk_floor_bytes=0)
  self.assertEqual(report['tile_count'],1);self.assertTrue((self.out/'00000-100001.bin').exists())
  p=subprocess.run([str(self.verifier),str(self.rows),str(self.runs),str(self.out),'100002','1','1'],capture_output=True,text=True)
  self.assertEqual(p.returncode,0,p.stderr)
 def test_maximum_u32_tile_size_verifies_without_overflow(self):
  report=t.build(self.rows,self.runs,pin(self.rows),pin(self.runs),8,4,self.out,tile_size=0xffffffff,disk_floor_bytes=0)
  self.assertEqual(report['tile_count'],1)
  p=subprocess.run([str(self.verifier),str(self.rows),str(self.runs),str(self.out),'8','4',str(0xffffffff)],capture_output=True,text=True)
  self.assertEqual(p.returncode,0,p.stderr)
 def test_tile_size_outside_u32_is_rejected(self):
  with self.assertRaisesRegex(ValueError,'controls'):
   t.build(self.rows,self.runs,pin(self.rows),pin(self.runs),8,4,self.out,tile_size=0x100000000,disk_floor_bytes=0)
  self.assertFalse(self.out.exists())
 def test_verifier_rejects_non_u32_dimensions(self):
  self.runbuild()
  for size in ('4294967296','-18446744073709551615','4x'):
   p=subprocess.run([str(self.verifier),str(self.rows),str(self.runs),str(self.out),'8','4',size],capture_output=True,text=True)
   self.assertNotEqual(p.returncode,0);self.assertIn('bad dimensions',p.stderr)
 def test_input_tamper_and_no_overwrite(self):
  with self.assertRaisesRegex(ValueError,'hash mismatch'):t.build(self.rows,self.runs,'0'*64,pin(self.runs),8,4,self.out,tile_size=4,disk_floor_bytes=0)
  self.assertFalse(self.out.exists());self.runbuild()
  with self.assertRaisesRegex(ValueError,'already exists'):self.runbuild()
 def test_invalid_seed_fails_without_completion(self):
  raw=bytearray(self.runs.read_bytes());raw[4:8]=(99).to_bytes(4,'little');self.runs.write_bytes(raw)
  with self.assertRaisesRegex(ValueError,'invalid seed'):self.runbuild()
  self.assertFalse((self.out/'report.json').exists())
 def test_disk_guard(self):
  with self.assertRaisesRegex(RuntimeError,'disk guard'):t.build(self.rows,self.runs,pin(self.rows),pin(self.runs),8,4,self.out,tile_size=4,disk_floor_bytes=2**63)
  self.assertFalse(self.out.exists())
 def test_parent_sync_failure_uncertain(self):
  with mock.patch.object(t,'sync_dir',side_effect=OSError('fault')):
   with self.assertRaisesRegex(RuntimeError,'directory may exist'):self.runbuild()
  self.assertTrue(self.out.is_dir());self.assertFalse((self.out/'report.json').exists())
 def test_marker_link_failure_and_post_link_sync_uncertain(self):
  with mock.patch.object(t.os,'link',side_effect=OSError('fault')):
   with self.assertRaises(OSError):self.runbuild()
  self.assertFalse((self.out/'report.json').exists())
  import shutil
  shutil.rmtree(self.out)
  original=t.sync_dir;calls=[]
  def sync(path):
   calls.append(path)
   if len(calls)==2:raise OSError('fault')
   return original(path)
  with mock.patch.object(t,'sync_dir',side_effect=sync):
   with self.assertRaisesRegex(RuntimeError,'marker may exist'):self.runbuild()
  self.assertTrue((self.out/'report.json').exists())

if __name__=='__main__':unittest.main()
