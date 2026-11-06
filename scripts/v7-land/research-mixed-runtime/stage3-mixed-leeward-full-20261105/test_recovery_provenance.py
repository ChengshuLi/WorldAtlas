import copy, unittest
from apply_selected_mixed import verify_recovery_evidence
class RecoveryTests(unittest.TestCase):
 def setUp(self):
  self.recovery={'schema':'stage2-seed-code-handoff-repair-v1','status':'launcher-remains-bound-by-derived-manifest','derived_manifest_sha256':'a'*64,'corrected_core_config_sha256':'b'*64,'seed_report_sha256':'c'*64,'launcher':{'sha256':'d'*64}}
  self.report={'config_sha256':'b'*64,'seed_report_sha256':'c'*64};self.derived={'code_sha256':{'seed-producer/seed_worker.py':'d'*64}}
 def runv(self):verify_recovery_evidence(self.recovery,self.report,self.derived,'a'*64)
 def test_valid(self):self.runv()
 def test_mismatched_evidence_fails(self):
  for key in ('schema','status','derived_manifest_sha256','corrected_core_config_sha256','seed_report_sha256'):
   original=self.recovery[key];self.recovery[key]='0'*64
   with self.subTest(key=key),self.assertRaises(ValueError):self.runv()
   self.recovery[key]=original
  self.recovery['launcher']['sha256']='0'*64
  with self.assertRaises(ValueError):self.runv()
 def test_mismatched_report_and_manifest_fail(self):
  for obj,key in ((self.report,'config_sha256'),(self.report,'seed_report_sha256'),(self.derived['code_sha256'],'seed-producer/seed_worker.py')):
   original=obj[key];obj[key]='0'*64
   with self.subTest(key=key),self.assertRaises(ValueError):self.runv()
   obj[key]=original
 def test_mutually_missing_digests_fail(self):
  for a,ka,b,kb in ((self.recovery,'corrected_core_config_sha256',self.report,'config_sha256'),(self.recovery,'seed_report_sha256',self.report,'seed_report_sha256'),(self.recovery['launcher'],'sha256',self.derived['code_sha256'],'seed-producer/seed_worker.py')):
   av=a.pop(ka);bv=b.pop(kb)
   with self.subTest(key=ka),self.assertRaises(ValueError):self.runv()
   a[ka]=av;b[kb]=bv
  self.recovery['derived_manifest_sha256']='A'*64
  with self.assertRaises(ValueError):self.runv()
if __name__=='__main__':unittest.main()
