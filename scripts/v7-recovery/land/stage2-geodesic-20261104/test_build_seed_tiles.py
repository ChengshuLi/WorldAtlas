import hashlib,json,struct,subprocess,tempfile,unittest
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
 def runbuild(self):return t.build(self.rows,self.runs,pin(self.rows),pin(self.runs),8,4,self.out,tile_size=4,memory_floor_kib=0,disk_floor_bytes=0)
 def test_tiles_match_independent_verifier(self):
  report=self.runbuild();self.assertEqual(report['tile_count'],2);self.assertEqual(report['manifest_sha256'],pin(self.out/'manifest.txt'))
  p=subprocess.run([str(self.verifier),str(self.rows),str(self.runs),str(self.out),'8','4','4','0'],capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(json.loads(p.stdout)['status'],'verified')
 def test_input_tamper_and_no_overwrite(self):
  with self.assertRaisesRegex(ValueError,'hash mismatch'):t.build(self.rows,self.runs,'0'*64,pin(self.runs),8,4,self.out,tile_size=4,memory_floor_kib=0,disk_floor_bytes=0)
  self.assertFalse(self.out.exists());self.runbuild()
  with self.assertRaisesRegex(ValueError,'already exists'):self.runbuild()
 def test_invalid_seed_fails_without_completion(self):
  raw=bytearray(self.runs.read_bytes());raw[4:8]=(99).to_bytes(4,'little');self.runs.write_bytes(raw)
  with self.assertRaisesRegex(ValueError,'invalid seed'):self.runbuild()
  self.assertFalse((self.out/'report.json').exists())
 def test_memory_and_disk_guards(self):
  with self.assertRaisesRegex(RuntimeError,'memory guard'):t.build(self.rows,self.runs,pin(self.rows),pin(self.runs),8,4,self.out,tile_size=4,memory_floor_kib=2**63,disk_floor_bytes=0)
  self.assertFalse(self.out.exists())
  with self.assertRaisesRegex(RuntimeError,'disk guard'):t.build(self.rows,self.runs,pin(self.rows),pin(self.runs),8,4,self.out,tile_size=4,memory_floor_kib=0,disk_floor_bytes=2**63)
  self.assertFalse(self.out.exists())

 def test_metadata_budget(self):
  with mock.patch('checkpoints.memory_available_kib',return_value=16384+128+8-1):
   with self.assertRaisesRegex(RuntimeError,'metadata headroom'):self.runbuild()
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
