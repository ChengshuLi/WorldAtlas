"""Large valid documents remain accepted; hashes still detect changes."""
import hashlib,json,tempfile,unittest
from pathlib import Path
import verify_physical_lineage as v
class LineageDocumentTests(unittest.TestCase):
 def test_large_report_and_readback_are_not_rejected_for_size(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'document';p.write_bytes(b'{"v":1}'+b' '*(4*1024*1024+1));pin={'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
   self.assertEqual(v.read_pin(pin,lambda:None)[0],{'v':1});self.assertEqual(v.read_overture_readback(pin,lambda:None),{'v':1})
   p.write_bytes(b'{"v":2}')
   with self.assertRaisesRegex(ValueError,'hash mismatch'):v.read_pin(pin,lambda:None)
 def test_validator_does_not_impose_document_size_ceiling(self):
  import ast,validate_stage2_candidate as c
  tree=ast.parse(Path(c.__file__).read_text());calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='bounded_bytes']
  self.assertEqual(calls,[])
if __name__=='__main__':unittest.main()
