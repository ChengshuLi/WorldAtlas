import json,unittest
from unittest import mock
import test_provisional_candidate as f
import validate_stage2_candidate as v
class FreshTests(unittest.TestCase):
 pin=f.ProvisionalCandidateTests.pin;write=f.ProvisionalCandidateTests.write;setUp=f.ProvisionalCandidateTests.setUp
 def prepare(self):
  snapshot=json.loads((self.d/'snapshot').read_bytes());old='a'*64
  self.write('prior_physical_report',{'status':'candidate-only','grid':self.report['grid'],'physical_output_sha256':{'rows.u32le':self.pins['physical_rows']['sha256'],'runs.u32le':self.pins['physical_runs']['sha256']}})
  old=self.pins['prior_physical_report']['sha256'];snapshot['land_baseline_policy']['physical_report_sha256']=old;self.write('snapshot',snapshot)
  self.report['decision_snapshot_sha256']=self.pins['snapshot']['sha256'];self.report['land_baseline_policy']=snapshot['land_baseline_policy'];self.report['inputs_sha256']['prior_physical_report']=old
  derived=json.loads((self.d/'derived_manifest').read_bytes())
  for name in ('seed_report','resolution_report'):
   self.write(name,{});derived['artifacts'][name]=self.pins.pop(name);self.report['inputs_sha256'][name]=derived['artifacts'][name]['sha256'];self.report[name+'_sha256']=derived['artifacts'][name]['sha256']
  self.write('derived_manifest',derived);self.report['orchestration']['derived_manifest']=self.pins['derived_manifest'];self.write('report',self.report)
 def test_fresh_path_checks_reproof_and_rejects_normal_mode(self):
  self.prepare()
  with mock.patch.object(v.contracts,'provisional_reproof',return_value=True) as proof,mock.patch.object(v.contracts,'resolution_roots',return_value={}),mock.patch.object(v.contracts,'validate_selected_seed_decisions') as cross:
   self.assertEqual(v.validate(self.pins,self.code,provisional_diagnostic=True)['status'],'provisional-diagnostic-candidate-bound');proof.assert_called_once();cross.assert_called_once()
  with self.assertRaises(ValueError):v.validate(self.pins,self.code)
 def test_missing_or_changed_prior_fails(self):
  self.prepare();self.pins.pop('prior_physical_report')
  with self.assertRaisesRegex(ValueError,'prior physical report'):v.validate(self.pins,self.code,provisional_diagnostic=True)
if __name__=='__main__':unittest.main()
