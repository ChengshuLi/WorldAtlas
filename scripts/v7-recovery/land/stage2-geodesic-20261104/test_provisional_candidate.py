"""Exercise real candidate validator with tiny synthetic provisional artifacts.

The local-snapshot digest admission and physical lineage are stubbed because
production deliberately accepts only one immutable actual local snapshot and
its much larger real provenance chain. All report, snapshot, Ural, code and
artifact checks and file hashing are otherwise exercised by the real validator.
"""
import copy,json,unittest
from unittest import mock
import test_validate_stage2_candidate as fixtures
import validate_stage2_candidate as validator
class ProvisionalCandidateTests(unittest.TestCase):
 pin=fixtures.CandidateTests.pin
 write=fixtures.CandidateTests.write
 def setUp(self):
  fixtures.CandidateTests.setUp(self)
  snapshot=json.loads((self.d/'snapshot').read_bytes());snapshot['source']='local-derived-from-neon-export';self.write('snapshot',snapshot)
  self.report.update(status='stage2-provisional-only',provisional_only=True,decision_snapshot_sha256=self.pins['snapshot']['sha256'])
  self.report['orchestration']['provisional_only']=True
  derived=json.loads((self.d/'derived_manifest').read_bytes());derived['provisional_only']=True;self.write('derived_manifest',derived)
  self.report['orchestration']['derived_manifest']=self.pins['derived_manifest'];self.write('report',self.report)
  p=mock.patch.object(validator.contracts,'local_or_neon_source',return_value=True);p.start();self.addCleanup(p.stop)
 def test_large_valid_report_is_not_rejected_for_size(self):
  with (self.d/'report').open('ab') as f:f.write(b' '*(16*1024*1024+1))
  self.pin('report')
  self.assertEqual(validator.validate(self.pins,self.code,provisional_diagnostic=True)['status'],'provisional-diagnostic-candidate-bound')
 def test_shared_contract_rejects_local_without_explicit_diagnostic(self):
  with self.assertRaisesRegex(ValueError,'draft Neon export required'):
   validator.contracts.snap_policy({'schema':'worldatlas-geography-decision-draft-evidence-v1','source':'local-derived-from-neon-export'},'r','e','p','v')
 def test_provisional_accepted_and_normal_rejected(self):
  out=validator.validate(self.pins,self.code,provisional_diagnostic=True)
  self.assertEqual(out['status'],'provisional-diagnostic-candidate-bound');self.assertEqual(out['original_report_status'],'stage2-provisional-only');self.assertTrue(out['provisional_only']);self.assertFalse(out['publishable'])
  with self.assertRaises(ValueError):validator.validate(self.pins,self.code)
 def test_report_flags_and_status_must_be_explicit(self):
  original=copy.deepcopy(self.report)
  for key,value in [('provisional_only',False),('provisional_only',None),('publishable',True),('publishable',None),('status','stage2-research-complete')]:
   self.report=copy.deepcopy(original)
   if value is None:self.report.pop(key)
   else:self.report[key]=value
   self.write('report',self.report)
   with self.subTest(key=key,value=value),self.assertRaises(ValueError):validator.validate(self.pins,self.code,provisional_diagnostic=True)
 def test_nonlocal_source_rejected(self):
  snapshot=json.loads((self.d/'snapshot').read_bytes());snapshot['source']='neon-export';self.write('snapshot',snapshot);self.report['decision_snapshot_sha256']=self.pins['snapshot']['sha256'];self.write('report',self.report)
  with self.assertRaises(ValueError):validator.validate(self.pins,self.code,provisional_diagnostic=True)
 def test_orchestration_and_derived_flags_rejected(self):
  original=copy.deepcopy(self.report)
  for value in (False,None):
   self.report=copy.deepcopy(original)
   if value is None:self.report['orchestration'].pop('provisional_only')
   else:self.report['orchestration']['provisional_only']=value
   self.write('report',self.report)
   with self.subTest(orchestration=value),self.assertRaises(ValueError):validator.validate(self.pins,self.code,provisional_diagnostic=True)
  self.report=copy.deepcopy(original);derived=json.loads((self.d/'derived_manifest').read_bytes())
  for value in (False,None):
   d=copy.deepcopy(derived)
   if value is None:d.pop('provisional_only')
   else:d['provisional_only']=value
   self.write('derived_manifest',d);self.report['orchestration']['derived_manifest']=self.pins['derived_manifest'];self.write('report',self.report)
   with self.subTest(derived=value),self.assertRaises(ValueError):validator.validate(self.pins,self.code,provisional_diagnostic=True)
# Run only the new tests; inherited CandidateTests assume a non-provisional fixture.
if __name__=='__main__':
 suite=unittest.TestSuite(ProvisionalCandidateTests(n) for n in ('test_provisional_accepted_and_normal_rejected','test_report_flags_and_status_must_be_explicit','test_nonlocal_source_rejected','test_orchestration_and_derived_flags_rejected'));unittest.TextTestRunner(verbosity=2).run(suite)
