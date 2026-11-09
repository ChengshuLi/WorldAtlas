import unittest
import prepare_final_plan as p
class Tests(unittest.TestCase):
 def setUp(self):
  self.plan={'schema':'worldatlas-full-grid-composition-plan-v1','decision_snapshot_sha256':'s','decision_revision':'d','entity_revision':'e'};self.audit={'schema':'worldatlas-prefill-class-rle-audit-v1','status':'staged-not-published','land_lineage':{'status':'diagnostic-provisional-lineage-bound'},'output':{'rows_sha256':'r','runs_sha256':'u'},'residual_eligible_water_cells':10};self.source={'prefill_rows_sha256':'r','prefill_runs_sha256':'u','decision_snapshot_sha256':'s','decision_revision':'d','entity_revision':'e'};self.o={'schema':'worldatlas-full-water-assignment-tiles-v1','status':'completed_unverified_candidate_not_published','coverage':{'complete':True},'source':dict(self.source),'_verified_manifest_sha256':'o'};self.summary={'status':'unverified-candidate-not-published','snapshot_sha256':'s','layer_manifest_sha256':'o','assigned_cells_total':7,'unseeded_cell_count':3};self.c={'schema':'worldatlas-full-water-assignment-tiles-v1','status':'completed_unverified_candidate_not_published','coverage':{'complete':True},'source':{**self.source,'partition_manifest_sha256':'p','component_rows_sha256':'x','component_spans_sha256':'y'},'pending_cells':0,'assigned_cells':3,'span_count':2,'_verified_manifest_sha256':'c','tiles':[{'span_file':{'sha256':'a'}}]};self.partition={'unseeded_span_count':2,'unseeded_cell_count':3,'inputs':{'prefill_rows_sha256':'r','prefill_runs_sha256':'u'}};self.coverage={'schema':'worldatlas-independent-enclosed-union-check-v1','status':'passed','check_script_sha256':'084976f54bc2c16df03fa7a9939d2465f680ae8dd16aef9de0c7832a9047d06f','grid':{'width':131072,'height':54614},'input_spans':2,'output_spans':2,'input_sha256':{'partition_manifest':'p','closed_manifest':'c','assignments':'a','unseeded_rows':'x','unseeded_spans':'y'},'assigned_cells':3,'unseeded_cells':3}
 def check(self):return p.validate(self.plan,self.audit,self.o,self.summary,self.c,self.partition,'p')
 def test_success(self):self.check()
 def test_incomplete(self):
  self.c['pending_cells']=1
  with self.assertRaisesRegex(ValueError,'conservation'):self.check()
 def test_wrong_partition(self):
  self.c['source']['partition_manifest_sha256']='wrong'
  with self.assertRaisesRegex(ValueError,'conservation'):self.check()
 def test_wrong_prefill_or_ocean(self):
  self.c['source']['prefill_runs_sha256']='bad'
  with self.assertRaisesRegex(ValueError,'lineage mismatch'):self.check()
  self.c['source']['prefill_runs_sha256']='u';self.summary['layer_manifest_sha256']='bad'
  with self.assertRaisesRegex(ValueError,'summary mismatch'):self.check()
 def test_residual_conservation(self):
  self.audit['residual_eligible_water_cells']=11
  with self.assertRaisesRegex(ValueError,'conservation'):self.check()
if __name__=='__main__':unittest.main()
