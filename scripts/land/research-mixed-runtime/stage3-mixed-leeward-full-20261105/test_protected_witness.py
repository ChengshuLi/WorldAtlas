import copy,unittest
import mixed_claims as m
class ProtectedWitnessTests(unittest.TestCase):
 def setUp(self):
  self.snapshot={'affiliations':[{'affiliation_id':'west','scope':'land','method':'component_intersection_v1','entity_id':2,'evidence':{'protected_witness_group_ids':['sentinel-new-guinea']}}]};self.compiled={'affiliation_ids':['west']}
  self.base={'decision_revision':{'id':'base'},'entity_revision':{'id':'entities'},'mainland_witness_groups':[{'group_id':'sentinel-new-guinea','decision_revision':'base','execution_status':'selected_for_research','role':'sentinel','target_entity_ids':[],'witness_ids':['w']}],'mainland_witnesses':[{'witness_id':'w','decision_revision':'base','execution_status':'selected_for_research','point_feature_id':'pt','identity_feature_id':'geo'}]}
  self.request={'baseline_snapshot_sha256':'a'*64,'component_manifest_sha256':'b'*64,'input_sha256':{'physical_rows':'c'*64,'physical_runs':'d'*64,'component_rows':'e'*64,'component_runs':'f'*64},'grid':{'width':8,'height':4}}
  self.report={'schema':'mainland-witness-resolution-v1','status':'selected-research-identity-claims-not-mainland-proof','snapshot_sha256':'a'*64,'decision_revision':'base','entity_revision':'entities','component_manifest_sha256':'b'*64,'input_sha256':self.request['input_sha256'].copy(),'grid':self.request['grid'].copy(),'groups':[{'group_id':'sentinel-new-guinea','role':'sentinel','target_entity_ids':[],'component_id_current_generation_only':77}],'witnesses':[{'witness_id':'w','group_id':'sentinel-new-guinea','point_feature_id':'pt','identity_feature_id':'geo'}]}
  self.stage2={'resolution_report_sha256':'9'*64};self.poly={'claims':[{'affiliation_id':'west','entity_id':2,'method':'component_intersection_v1','component_ids':[7,8]}]}
 def run_guard(self):return m.verify_protected(m.protected_requirements(self.snapshot,self.compiled),self.snapshot,self.base,self.stage2,self.request,self.report,'9'*64,self.poly)
 def test_clear_and_no_persisted_root(self):self.assertEqual(self.run_guard(),[{'affiliation_id':'west','target_entity_id':2,'witness_group_id':'sentinel-new-guinea','status':'clear'}])
 def test_protected_hit_fails(self):
  self.poly['claims'][0]['component_ids'].append(77)
  with self.assertRaisesRegex(ValueError,'protected witness component hit'):self.run_guard()
 def test_wrong_target_fails(self):
  self.poly['claims'][0]['entity_id']=6
  with self.assertRaisesRegex(ValueError,'target mismatch'):self.run_guard()
 def test_unknown_group_fails(self):
  self.snapshot['affiliations'][0]['evidence']['protected_witness_group_ids']=['unknown']
  with self.assertRaisesRegex(ValueError,'unknown or unsupported'):self.run_guard()
 def test_duplicate_requirement_fails(self):
  self.snapshot['affiliations'][0]['evidence']['protected_witness_group_ids']=['sentinel-new-guinea']*2
  with self.assertRaisesRegex(ValueError,'invalid protected witness'):self.run_guard()
 def test_missing_or_changed_source_witness_fails(self):
  self.report['witnesses'][0]['point_feature_id']='other'
  with self.assertRaisesRegex(ValueError,'source identity mismatch'):self.run_guard()
 def test_stale_component_fails(self):
  self.report['input_sha256']['component_runs']='z'*64
  with self.assertRaisesRegex(ValueError,'physical or component mismatch'):self.run_guard()
 def test_stale_stage2_binding_fails(self):
  self.stage2['resolution_report_sha256']='8'*64
  with self.assertRaisesRegex(ValueError,'not bound'):self.run_guard()
 def test_duplicate_group_fails(self):
  self.report['groups'].append(copy.deepcopy(self.report['groups'][0]))
  with self.assertRaisesRegex(ValueError,'duplicate or malformed'):self.run_guard()
 def test_unselected_group_fails(self):
  self.base['mainland_witness_groups'][0]['execution_status']='draft'
  with self.assertRaisesRegex(ValueError,'unknown or unsupported'):self.run_guard()
 def test_unsupported_method_fails(self):
  self.snapshot['affiliations'][0]['method']='source_point_component_v1'
  with self.assertRaisesRegex(ValueError,'unsupported protected affiliation'):self.run_guard()
 def test_missing_claim_fails(self):
  self.poly['claims']=[]
  with self.assertRaisesRegex(ValueError,'target mismatch'):self.run_guard()
 def test_no_requirement_preserves_existing(self):
  self.snapshot['affiliations'][0]['evidence']={};self.assertEqual(self.run_guard(),[])
if __name__=='__main__':unittest.main()
