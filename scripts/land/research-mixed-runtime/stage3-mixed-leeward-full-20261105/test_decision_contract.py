import copy,unittest
from decision_contract import compile_policy
class ContractTests(unittest.TestCase):
 def setUp(self):
  self.pins={k:(str(i)*64) for i,k in enumerate(('baseline_report_sha256','baseline_rows_sha256','baseline_runs_sha256','baseline_decision_snapshot_sha256','physical_rows_sha256','physical_runs_sha256','component_rows_sha256','component_runs_sha256'),1)}
  cats=['Africa','Asia','Europe','North America','South America','Oceania'];entities=[{'id':i,'level':'continent','name':n} for i,n in enumerate(cats,1)];bindings=[{'entity_id':i,'code':i+16,'physical_class':'land'} for i in range(1,7)]
  self.base={'schema':'worldatlas-geography-decision-draft-evidence-v1','source':'neon-export','decision_revision':{'id':'base','status':'draft','entity_revision':'entities'},'entity_revision':{'id':'entities','status':'draft'},'entities':entities,'category_bindings':bindings}
  self.report={'schema':'stage2-source-geodesic-report-v1','status':'stage2-research-complete','decision_revision':'base','entity_revision':'entities','decision_snapshot_sha256':self.pins['baseline_decision_snapshot_sha256'],'output_rows_sha256':self.pins['baseline_rows_sha256'],'output_runs_sha256':self.pins['baseline_runs_sha256'],'inputs_sha256':{k:self.pins[k+'_sha256'] for k in ('physical_rows','physical_runs','component_rows','component_runs')},'categories':{str(i+17):n for i,n in enumerate(cats)}}
  self.s={'schema':'worldatlas-geography-decision-draft-evidence-v1','source':'neon-export','decision_revision':{'id':'new','status':'draft','entity_revision':'entities'},'entity_revision':{'id':'entities','status':'draft'},'entities':copy.deepcopy(entities),'category_bindings':copy.deepcopy(bindings),'affiliations':[{'affiliation_id':'a','decision_revision':'new','scope':'land','entity_id':2,'relationship':'affiliation','method':'point','evidence':{'execution_status':'selected_for_research'}}],'list1_entries':[{'entry_id':'e','decision_revision':'new','title':'Island','reason':'Source decision','old_list1_refs':['old'], 'execution_status':'selected_for_research','affiliation_ids':['a']}],'list1_policy':{'decision_revision':'new','baseline_revision':'base','execution_status':'selected_for_research','entry_ids':['e'],'affiliation_ids':['a'],'conflict_policy':'error_on_different_target','unclaimed_policy':'preserve_baseline','physical_water_policy':'preserve_unassigned',**self.pins}}
 def runv(self):return compile_policy(self.s,self.base,self.report,self.pins,{'point','polygon'})
 def test_v3_requires_both_explicit_reference_sets(self):
  self.s['schema']='worldatlas-geography-decision-draft-evidence-v3';self.s['unsupported_affiliation_source_ref_table_present']=False;self.s['unsupported_point_methods_present']=False;self.s['affiliation_source_refs']=[];self.s['polygon_corroboration_refs']=[];self.s['ecoregion_source_refs']=[];self.runv()
  self.s['unsupported_affiliation_source_ref_table_present']=True
  with self.assertRaisesRegex(ValueError,'unsupported affiliation-source table status'):self.runv()
  self.s['unsupported_affiliation_source_ref_table_present']=False;self.s['unsupported_point_methods_present']=False;self.s['affiliation_source_refs']=[];del self.s['ecoregion_source_refs']
  with self.assertRaisesRegex(ValueError,'ecoregion export schema'):self.runv()
  self.s['schema']='worldatlas-geography-decision-draft-evidence-v2';self.s['ecoregion_source_refs']=[]
  with self.assertRaisesRegex(ValueError,'ecoregion export schema'):self.runv()
 def test_versioned_corroboration_schema(self):
  self.s['affiliations'][0]['evidence']['polygon_corroboration_mode']='administrative_geometry_v1'
  with self.assertRaisesRegex(ValueError,'schema or corroboration refs'):self.runv()
  self.s['schema']='worldatlas-geography-decision-draft-evidence-v2'
  with self.assertRaisesRegex(ValueError,'schema or corroboration refs'):self.runv()
  self.s['polygon_corroboration_refs']=[];self.runv()
 def test_selected(self):self.assertEqual(self.runv()['affiliation_entry_links'],{'a':['e']})
 def test_convention_note_consumed(self):
  note={'identity_source_region':'Oceania','selected_affiliation':'Asia','basis':'Old list convention'};self.s['affiliations'][0]['evidence']['source_convention_note']=note;self.assertEqual(self.runv()['affiliation_convention_notes']['a'],note)
  note['selected_affiliation']='Europe'
  with self.assertRaisesRegex(ValueError,'convention note'):self.runv()
 def test_many_entries_one_affiliation(self):
  e=copy.deepcopy(self.s['list1_entries'][0]);e['entry_id']='e2';self.s['list1_entries'].append(e);self.s['list1_policy']['entry_ids'].append('e2');self.assertEqual(self.runv()['affiliation_entry_links']['a'],['e','e2'])
 def test_orphan_entry_rejected(self):
  self.s['list1_entries'][0]['affiliation_ids']=[]
  with self.assertRaisesRegex(ValueError,'orphan'):self.runv()
 def test_unlinked_affiliation_rejected(self):
  a=copy.deepcopy(self.s['affiliations'][0]);a['affiliation_id']='b';self.s['affiliations'].append(a);self.s['list1_policy']['affiliation_ids'].append('b')
  with self.assertRaisesRegex(ValueError,'unlinked'):self.runv()
 def test_unconsumed_selected_affiliation_rejected(self):
  a=copy.deepcopy(self.s['affiliations'][0]);a['affiliation_id']='b';self.s['affiliations'].append(a)
  with self.assertRaisesRegex(ValueError,'differ from policy'):self.runv()
 def test_unsupported_method_rejected(self):
  self.s['affiliations'][0]['method']='unknown'
  with self.assertRaisesRegex(ValueError,'unsupported'):self.runv()
 def test_stale_revision_rejected(self):
  self.s['affiliations'][0]['decision_revision']='stale'
  with self.assertRaisesRegex(ValueError,'stale'):self.runv()
 def test_nonland_target_rejected(self):
  self.s['affiliations'][0]['entity_id']=99
  with self.assertRaisesRegex(ValueError,'non-continent'):self.runv()
 def test_wrong_baseline_rejected(self):
  self.s['list1_policy']['baseline_runs_sha256']='f'*64
  with self.assertRaisesRegex(ValueError,'policy'):self.runv()
 def test_category_change_rejected(self):
  self.s['entities'][0]['name']='Other'
  with self.assertRaisesRegex(ValueError,'category mismatch'):self.runv()
 def test_water_assignment_policy_rejected(self):
  self.s['list1_policy']['physical_water_policy']='assign'
  with self.assertRaisesRegex(ValueError,'policy'):self.runv()
 def test_provisional_binding_preserves_original_and_is_explicit(self):
  self.base['source']='local-derived-from-neon-export';self.report.update(status='stage2-provisional-only',provisional_only=True,publishable=False)
  self.s['list1_policy']['baseline_revision']='old-baseline';self.s['list1_policy']['baseline_runs_sha256']='f'*64
  old=copy.deepcopy(self.s);old_report=copy.deepcopy(self.report)
  with self.assertRaises(ValueError):self.runv()
  out=compile_policy(self.s,self.base,self.report,self.pins,{'point','polygon'},provisional_diagnostic=True)
  self.assertEqual(self.s,old);self.assertEqual(self.report,old_report);self.assertEqual(out['policy'],old['list1_policy']);self.assertEqual(out['diagnostic_binding']['original_policy_pins']['baseline_runs_sha256'],'f'*64);self.assertEqual(out['diagnostic_binding']['actual_baseline_pins'],self.pins)
  for key,value in [('status','stage2-research-complete'),('provisional_only',False),('publishable',True)]:
   self.report[key]=value
   with self.assertRaises(ValueError):compile_policy(self.s,self.base,self.report,self.pins,{'point','polygon'},provisional_diagnostic=True)
   self.report=copy.deepcopy(old_report)
  self.report['output_runs_sha256']='f'*64
  with self.assertRaises(ValueError):compile_policy(self.s,self.base,self.report,self.pins,{'point','polygon'},provisional_diagnostic=True)
 def test_diagnostic_retains_conflict_policy_and_selection_guards(self):
  self.base['source']='local-derived-from-neon-export';self.report.update(status='stage2-provisional-only',provisional_only=True,publishable=False)
  self.s['list1_policy']['conflict_policy']='last_wins'
  with self.assertRaisesRegex(ValueError,'policy'):compile_policy(self.s,self.base,self.report,self.pins,{'point','polygon'},provisional_diagnostic=True)
  self.s['list1_policy']['conflict_policy']='error_on_different_target';self.s['list1_entries'][0]['affiliation_ids']=[]
  with self.assertRaisesRegex(ValueError,'orphan'):compile_policy(self.s,self.base,self.report,self.pins,{'point','polygon'},provisional_diagnostic=True)
if __name__=='__main__':unittest.main()
