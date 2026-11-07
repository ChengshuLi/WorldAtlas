import copy,unittest
from unittest import mock
import contracts as c
import test_contracts

class ReproofTests(unittest.TestCase):
 def setUp(self):
  fixture=test_contracts.CrosswalkTests();fixture.setUp();self.__dict__.update(fixture.__dict__);self.check=fixture.check.__func__.__get__(self);self.snapshot['source']='local-derived-from-neon-export';self.old='a'*64;self.pins=self.seed['input_sha256'];self.pins['prior_physical_report']=self.old
  self.snapshot['land_baseline_policy']['physical_report_sha256']=self.old
  prov=self.snapshot['routes'][0]['provenance'];prov['physical_report_sha256']=self.old;prov['contract_sha256']='b'*64;prov['checker_sha256']='c'*64
  self.seed['provisional_physical_equivalence']={'prior_report_sha256':self.old,'current_report_sha256':self.pins['physical_report'],'rows_sha256':self.pins['physical_rows'],'runs_sha256':self.pins['physical_runs'],'historical_route_provenance':{'q':copy.deepcopy(prov)},'fresh_reproof_route_ids':['q'],'status':'equivalent-streams-fresh-proofs-provisional-only'}
  self.prior={'status':'candidate-only','grid':self.grid,'physical_output_sha256':{'rows.u32le':self.pins['physical_rows'],'runs.u32le':self.pins['physical_runs']}}
 def check_new(self):
  with mock.patch.object(c,'local_or_neon_source',return_value=True):ok=c.provisional_reproof(self.snapshot,self.seed,self.pins,self.prior,self.grid)
  return c.validate_selected_seed_decisions(self.snapshot,self.seed,self.groups,self.codes,self.metric,provisional_equivalence=ok)
 def test_exact_equivalence_requires_opt_in_and_new_proof(self):
  with self.assertRaises(ValueError):self.check()
  self.assertTrue(self.check_new())
  self.seed['region_traces'][0]['input_trace'][1]['closure_proof']['checker_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'checker'):self.check_new()
 def test_prior_physical_or_provenance_tamper_fails(self):
  for obj,key in [(self.prior['physical_output_sha256'],'rows.u32le'),(self.seed['provisional_physical_equivalence'],'prior_report_sha256'),(self.seed['provisional_physical_equivalence']['historical_route_provenance']['q'],'physical_runs_sha256')]:
   orig=obj[key];obj[key]='f'*64
   with self.assertRaises(ValueError):self.check_new()
   obj[key]=orig
 def test_accepted_snapshot_cannot_use_equivalence(self):
  self.snapshot['source']='neon-export'
  with self.assertRaises(ValueError):self.check_new()
if __name__=='__main__':unittest.main()
