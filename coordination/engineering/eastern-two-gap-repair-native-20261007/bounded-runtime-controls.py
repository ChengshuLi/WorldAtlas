#!/usr/bin/env python3
import gzip,importlib.util,pathlib,tempfile,unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[3]
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
bounded=module('bounded',pathlib.Path(__file__).with_name('bounded-ownership-runtime.py'))
stock=module('stock',ROOT/'scripts/prepare-ownership-runtime.py')
class Tests(unittest.TestCase):
 def test_actual_complete_stock_range_positive(self):
  old=stock.bucket_ranges(-3000,2025);new=bounded.refined_ranges(stock.bucket_ranges,-3000,2025)
  self.assertEqual(len(old),51);self.assertEqual(len(new),54)
  self.assertEqual([r for r in old if r[0] not in [1801,1901]],[r for r in new if r not in bounded.REPLACEMENTS[1801]+bounded.REPLACEMENTS[1901]])
  self.assertEqual(new[0][0],-3000);self.assertEqual(new[-1][1],2025)
 def test_wrong_original_end_rejected(self):
  with self.assertRaisesRegex(ValueError,'Unexpected original oversized'):
   bounded.refined_ranges(lambda a,b:[(x,y+1 if x==1801 else y) for x,y in stock.bucket_ranges(a,b)],-3000,2025)
 def test_missing_original_range_rejected(self):
  with self.assertRaisesRegex(ValueError,'complete stock range'):
   bounded.refined_ranges(lambda a,b:stock.bucket_ranges(a,b)[:-1],-3000,2025)
 def test_option_commit_never_calls_git(self):
  with patch.object(bounded.subprocess,'check_output') as call:
   with self.assertRaisesRegex(ValueError,'before Git'):bounded.authenticate('--output=forged',__file__)
   call.assert_not_called()
 def test_decoded_cap_with_small_encoded_body(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=pathlib.Path(tmp)/'large.gz';p.write_bytes(gzip.compress(b'0'*(bounded.LIMIT+1),mtime=0))
   self.assertLess(p.stat().st_size,bounded.LIMIT)
   with self.assertRaisesRegex(ValueError,'decoded body'):bounded.bounded_pin(p)
 def test_complete_bounded_body_positive(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=pathlib.Path(tmp)/'small.gz';p.write_bytes(gzip.compress(b'complete original',mtime=0));pin=bounded.bounded_pin(p)
   self.assertEqual(pin['decoded_bytes'],17);self.assertEqual(pin['decoded_sha256'],bounded.digest(b'complete original'))
if __name__=='__main__':unittest.main()
