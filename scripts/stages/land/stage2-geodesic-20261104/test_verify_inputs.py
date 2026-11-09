import tempfile,pathlib,unittest,hashlib
import numpy as np
from verify_inputs import verify_representatives
class Inputs(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.d=pathlib.Path(self.tmp.name);self.raw=np.asarray([[1,0,2,17],[1,2,4,18]],dtype='<u4').tobytes();(self.d/'00000-00000.bin').write_bytes(self.raw);self.p=self.d/'manifest';self.p.write_text('0 0 2 3 '+hashlib.sha256(self.raw).hexdigest()+'\n');self.r=np.asarray([[0,0,1,0,17],[0,0,1,3,18]],dtype='<u4')
 def v(self):return verify_representatives(self.d,self.p,self.r,8,4,4)
 def test_good(self):self.assertEqual(self.v()[0][:4],(0,0,[17,18],2))
 def test_oversized_tile(self):
  (self.d/'00000-00000.bin').write_bytes(self.raw+b'x')
  with self.assertRaisesRegex(ValueError,'size mismatch'):self.v()
 def test_long_valid_manifest_line_is_not_resource_capped(self):
  self.p.write_bytes(self.p.read_bytes().rstrip()+b' '*(8*1024*1024+1)+b'\n')
  self.assertEqual(self.v()[0][:4],(0,0,[17,18],2))
 def test_invalid_manifest_line_still_rejected(self):
  self.p.write_bytes(b'x'*257+b'\n')
  with self.assertRaisesRegex(ValueError,'bad manifest'):self.v()
 def test_manifest_count_exceeds_tile(self):
  self.p.write_text('0 0 17 1 '+'0'*64+'\n')
  with self.assertRaisesRegex(ValueError,'invalid/duplicate tile manifest'):self.v()
 def test_bad_witness(self):
  self.r[0,3]=3
  with self.assertRaisesRegex(ValueError,'not an actual'):self.v()
 def test_bad_tile_hash(self):
  (self.d/'00000-00000.bin').write_bytes(b'x'*len(self.raw))
  with self.assertRaisesRegex(ValueError,'hash mismatch'):self.v()
 def test_missing_category(self):
  self.r=self.r[:1]
  with self.assertRaisesRegex(ValueError,'lacks a representative'):self.v()
 def test_missing_tile(self):
  self.p.write_text(self.p.read_text()+'0 1 1 1 '+'0'*64+'\n')
  with self.assertRaisesRegex(ValueError,'tile lacks'):self.v()
if __name__=='__main__':unittest.main()
