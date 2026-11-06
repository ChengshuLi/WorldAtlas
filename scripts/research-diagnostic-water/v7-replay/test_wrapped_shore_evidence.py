import json,tempfile,unittest
from pathlib import Path
import wrapped_shore_evidence as e
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.msha='a'*64;self.tile='b'*64;self.mask='c'*64;self.m={'source':{'decision_id':'seavox-24119','policy_sha256':'p','physical_rows_sha256':'r','physical_runs_sha256':'u'},'nearest_assignment_audit':{'shore_method':e.WRAPPED},'tiles':[{'span_file':{'sha256':self.tile}}],'rasterization':{'source_mask_sha256':self.mask},'physical_water_cells':2,'span_count':1,'row_count':1};t={'cells':2,'spans':1,'rows':1};self.comp={'schema':'worldatlas-bering-full-rerun-comparison-v1','status':'complete-research-not-published','all_rows_and_spans_equal':True,'reference_manifest_sha256':e.REFERENCE,'candidate_manifest_sha256':self.msha,'candidate_span_sha256':self.tile,'reference_span_sha256':self.tile,'candidate_totals':t,'reference_totals':t,'counts':{'different_rows':0}};self.proof={'schema':'worldatlas-bering-independent-raster-coverage-proof-v1','status':'raster-to-span-match','manifest_sha256':self.msha,'verifier_sha256':e.VERIFIER,'policy_sha256':'p','physical_rows_sha256':'r','physical_runs_sha256':'u','result':{'status':'raster-to-span-match','cells':2,'spans':1,'assignment_sha256':self.tile,'raster_sha256':self.mask}};self.write()
 def write(self):
  self.spec={}
  for key,obj in [('comparison',self.comp),('coverage',self.proof)]:
   p=self.root/(key+'.json');p.write_text(json.dumps(obj));self.spec[key]={'path':p.name,'sha256':e.sha(p)}
 def check(self):e.validate(self.m,self.msha,self.spec,self.root,self.root)
 def test_valid_and_original(self):self.check();self.m['nearest_assignment_audit']['shore_method']=e.ORIGINAL;e.validate(self.m,self.msha,None,self.root,self.root)
 def test_missing_or_changed_evidence_rejected(self):
  with self.assertRaisesRegex(ValueError,'missing wrapped evidence'):e.validate(self.m,self.msha,None,self.root,self.root)
  (self.root/'comparison.json').write_text('{}')
  with self.assertRaisesRegex(ValueError,'pin mismatch'):self.check()
 def test_comparison_and_coverage_must_bind(self):
  self.comp['candidate_manifest_sha256']='wrong';self.write()
  with self.assertRaisesRegex(ValueError,'comparison mismatch'):self.check()
  self.comp['candidate_manifest_sha256']=self.msha;self.proof['result']['raster_sha256']='wrong';self.write()
  with self.assertRaisesRegex(ValueError,'coverage mismatch'):self.check()
 def test_reference_must_be_verified_baseline(self):
  self.comp['reference_manifest_sha256']=self.msha;self.write()
  with self.assertRaisesRegex(ValueError,'comparison mismatch'):self.check()
 def test_original_method_cannot_hide_wrapped_optimization(self):
  self.m['nearest_assignment_audit']={'shore_method':e.ORIGINAL,'wrapped_narrow_cells':2}
  with self.assertRaisesRegex(ValueError,'wrapped optimization metadata'):self.check()
 def test_unapproved_basin_rejected(self):
  self.m['source']['decision_id']='other'
  with self.assertRaisesRegex(ValueError,'unsupported wrapped method'):self.check()
if __name__=='__main__':unittest.main()
