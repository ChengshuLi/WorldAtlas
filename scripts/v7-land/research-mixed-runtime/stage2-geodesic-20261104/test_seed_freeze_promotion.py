"""Tests for the proposed code-only freeze; no scientific or data approval."""
import unittest
import orchestrate_stage2 as m

class FreezeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.good=m.code_hashes(lambda:None)
 def test_assembled_candidate(self):m.require_reviewed_seed(self.good)
 def test_every_producer_tamper_fails(self):
  for name in m.SEED_NAMES:
   code=dict(self.good);code['seed-producer/'+name]='0'*64
   with self.subTest(name=name),self.assertRaisesRegex(ValueError,'producer freeze'):m.require_reviewed_seed(code)
 def test_worker_tamper_fails(self):
  code=dict(self.good);code['seed-producer/seed_worker.py']='0'*64
  with self.assertRaisesRegex(ValueError,'worker mismatch'):m.require_reviewed_seed(code)
 def test_missing_worker_fails(self):
  code=dict(self.good);del code['seed-producer/seed_worker.py']
  with self.assertRaisesRegex(ValueError,'worker mismatch'):m.require_reviewed_seed(code)
 def test_gate_false_fails(self):
  old=m.SEED_FREEZE_CURRENT;m.SEED_FREEZE_CURRENT=False
  try:
   with self.assertRaisesRegex(ValueError,'producer freeze'):m.require_reviewed_seed(self.good)
  finally:m.SEED_FREEZE_CURRENT=old
if __name__=='__main__':unittest.main()
