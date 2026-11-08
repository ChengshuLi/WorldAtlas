import copy, unittest
import split_lineage_ocean as s

class SplitLineageTest(unittest.TestCase):
 def setUp(self):
  self.h={k:format(i+1,'064x') for i,k in enumerate(('ocean_snapshot','prefill_snapshot','plan','physical_rows','physical_runs','prefill_rows','prefill_runs','candidate','audit'))}
  self.mask='f'*64;self.report='e'*64
  bindings=[{'entity_id':1,'code':17,'physical_class':'land'},{'entity_id':7,'code':7,'physical_class':'water'}]
  self.base={'decision_revision':{'id':'base','entity_revision':'e'},'entity_revision':{'id':'e'},'category_bindings':bindings}
  self.ocean={'source':'neon-export','schema':'worldatlas-geography-decision-draft-evidence-v1','decision_revision':{'id':'ocean','status':'draft','entity_revision':'e','evidence':{'base_local_snapshot_sha256':self.h['prefill_snapshot']}},'entity_revision':{'id':'e','status':'draft'},'category_bindings':copy.deepcopy(bindings)}
  self.plan={'grid':{'width':8,'height':4},'decision_snapshot_sha256':self.h['prefill_snapshot'],'decision_revision':'base','entity_revision':'e','rle_inputs':{'physical':{'rows_sha256':self.h['physical_rows'],'runs_sha256':self.h['physical_runs'],'physical_mask_sha256':self.mask,'report_sha256':self.report}}}
  self.audit={'schema':'worldatlas-v7-prefill-class-rle-audit-v1','status':'staged-not-published','prior_ocean_water_labels_read':'none','source_plan_sha256':self.h['plan'],'decision_snapshot_sha256':self.h['prefill_snapshot'],'decision_revision':'base','entity_revision':'e','physical_mask_sha256':self.mask,'output':{'rows_sha256':self.h['prefill_rows'],'runs_sha256':self.h['prefill_runs']}}
  self.candidate={'schema':'worldatlas-direct-candidate-build-v1','status':'unverified-research-not-published','decision_snapshot_sha256':self.h['ocean_snapshot'],'decision_revision':'ocean','entity_revision':'e','physical_rows_sha256':self.h['physical_rows'],'physical_runs_sha256':self.h['physical_runs'],'physical_mask_sha256':self.mask,'physical_report_sha256':self.report,'grid':{'width':8,'height':4}}
 def check(self):
  return s.validate(self.ocean,self.base,self.h['prefill_snapshot'],self.plan,self.audit,self.candidate,self.h)
 def test_final_recheck_detects_change_after_summary_callback(self):
  import json,sys,tempfile
  from pathlib import Path
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);pf=root/'prefill';pf.mkdir()
   for name in ('physical-rows','physical-runs'):(root/name).write_bytes(name.encode())
   for name in ('rows','runs'):(pf/name).write_bytes(name.encode())
   base=root/'base.json';base.write_text(json.dumps(self.base));self.h['prefill_snapshot']=s.ocean.sha(base)
   self.ocean['decision_revision']['evidence']['base_local_snapshot_sha256']=self.h['prefill_snapshot'];op=root/'ocean.json';op.write_text(json.dumps(self.ocean));self.h['ocean_snapshot']=s.ocean.sha(op)
   self.h.update(physical_rows=s.ocean.sha(root/'physical-rows'),physical_runs=s.ocean.sha(root/'physical-runs'),prefill_rows=s.ocean.sha(pf/'rows'),prefill_runs=s.ocean.sha(pf/'runs'))
   self.plan['decision_snapshot_sha256']=self.h['prefill_snapshot'];self.plan['rle_inputs']['physical'].update(rows_sha256=self.h['physical_rows'],runs_sha256=self.h['physical_runs'])
   plan=root/'plan.json';plan.write_text(json.dumps(self.plan));self.h['plan']=s.ocean.sha(plan)
   self.audit.update(source_plan_sha256=self.h['plan'],decision_snapshot_sha256=self.h['prefill_snapshot']);self.audit['output'].update(rows_path='rows',runs_path='runs',rows_sha256=self.h['prefill_rows'],runs_sha256=self.h['prefill_runs'])
   audit=pf/'prefill-audit.json';audit.write_text(json.dumps(self.audit))
   self.candidate.update(decision_snapshot_sha256=self.h['ocean_snapshot'],physical_rows_sha256=self.h['physical_rows'],physical_runs_sha256=self.h['physical_runs']);candidate=root/'candidate.json';candidate.write_text(json.dumps(self.candidate))
   argv=['split','--ocean-snapshot',str(op),'--ocean-snapshot-sha256',self.h['ocean_snapshot'],'--prefill-snapshot',str(base),'--prefill-snapshot-sha256',self.h['prefill_snapshot'],'--prefill-plan',str(plan),'--prefill-dir',str(pf),'--physical-rows',str(root/'physical-rows'),'--physical-runs',str(root/'physical-runs'),'--candidate-build',str(candidate),'--candidate-build-sha256',s.ocean.sha(candidate),'--out',str(root/'out'),'--allow-unverified-snapshots','--allow-draft-snapshot']
   def fake_run(*args,**kw):
    kw['pre_finalize']();kw['pre_summary']();out=root/'out';out.mkdir();(out/'run-summary.json').write_text('{}');audit.write_text(audit.read_text()+' ')
   with patch.object(sys,'argv',argv),patch.object(s.ocean,'run',side_effect=fake_run):
    with self.assertRaisesRegex(ValueError,'input changed during ocean fill'):s.main()
   self.assertFalse((root/'out/run-summary.json').exists());self.assertTrue((root/'out/run-summary-invalid.json').exists())
 def test_split_lineage_passes(self):self.assertEqual(self.check(),(8,4))
 def test_wrong_source_snapshot_rejected(self):
  self.ocean['decision_revision']['evidence']['base_local_snapshot_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'lineage'):self.check()
 def test_regenerated_prefill_requires_pinned_equivalent_reference(self):
  expected='f'*64
  self.ocean['decision_revision']['evidence']['base_local_snapshot_sha256']=expected
  self.base.update(routes=[],local_overlay_provenance={'overlay_sha256':'current','overlay_path':'/local/overlay'})
  reference=copy.deepcopy(self.base)
  reference['local_overlay_provenance'].update(overlay_sha256='historical',overlay_path='/original/overlay')
  self.h['prefill_reference']='e'*64
  def check():
   return s.validate(self.ocean,self.base,self.h['prefill_snapshot'],self.plan,self.audit,self.candidate,self.h,reference)
  with self.assertRaisesRegex(ValueError,'lineage'):check()
  self.h['prefill_reference']=expected
  self.assertEqual(check(),(8,4))
  reference['decision_revision']['id']='different'
  with self.assertRaisesRegex(ValueError,'lineage'):check()
 def test_registry_mismatch_rejected(self):
  self.ocean['category_bindings'][0]['code']=18
  with self.assertRaisesRegex(ValueError,'registry'):self.check()
 def test_wrong_prefill_audit_rejected(self):
  self.audit['source_plan_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'prefill audit'):self.check()
 def test_inherited_ocean_labels_rejected(self):
  self.audit['prior_ocean_water_labels_read']='yes'
  with self.assertRaisesRegex(ValueError,'prefill audit'):self.check()
 def test_wrong_physical_mask_rejected(self):
  self.candidate['physical_mask_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'candidate'):self.check()
 def test_wrong_candidate_snapshot_rejected(self):
  self.candidate['decision_snapshot_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'candidate'):self.check()
 def test_non_draft_rejected(self):
  self.ocean['decision_revision']['status']='accepted'
  with self.assertRaisesRegex(ValueError,'draft'):self.check()
 def test_bad_prefill_grid_rejected(self):
  self.plan['grid']['height']=5
  with self.assertRaisesRegex(ValueError,'candidate'):self.check()
if __name__=='__main__':unittest.main()
