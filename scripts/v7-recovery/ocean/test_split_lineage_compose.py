import json,struct,tempfile,unittest
from pathlib import Path
import split_lineage_compose as s

def write_json(p,d):p.write_text(json.dumps(d));return p

def binary(p,fmt,records):
 with p.open('wb') as f:
  for r in records:f.write(struct.pack(fmt,*r))
 return p

class SplitComposeTest(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();root=Path(self.temp.name);self.inp=root/'inputs';self.inp.mkdir();self.out=root/'out';self.paths={}
  def add(key,p):self.paths[key]=p;return p
  bindings=[{'entity_id':1,'code':17,'physical_class':'land'},{'entity_id':7,'code':7,'physical_class':'water'}]
  base={'decision_revision':{'id':'base','entity_revision':'e'},'entity_revision':{'id':'e'},'category_bindings':bindings};snap={'source':'neon-export','schema':'worldatlas-geography-decision-draft-evidence-v1','decision_revision':{'id':'new','status':'draft','entity_revision':'e','evidence':{}},'entity_revision':{'id':'e','status':'draft'},'category_bindings':bindings}
  add('prefill_snapshot',write_json(self.inp/'base.json',base));snap['decision_revision']['evidence']['base_local_snapshot_sha256']=s.ocean.sha(self.paths['prefill_snapshot']);add('ocean_snapshot',write_json(self.inp/'ocean.json',snap))
  add('baseline_rows',binary(self.inp/'base-rows','<I',[(0,),(4,),(8,),(12,),(16,)]))
  base_runs=[(2,7),(4,8),(6,9),(8,10)]*4;add('baseline_runs',binary(self.inp/'base-runs','<II',base_runs))
  add('prefill_plan',write_json(self.inp/'prefill-plan.json',{'decision_snapshot_sha256':s.ocean.sha(self.paths['prefill_snapshot']),'decision_revision':'base','entity_revision':'e','grid':{'width':8,'height':4},'rle_inputs':{'physical':{'rows_sha256':'1'*64,'runs_sha256':'2'*64,'physical_mask_sha256':'3'*64,'report_sha256':'7'*64}}}))
  add('prefill_audit',write_json(self.inp/'prefill-audit.json',{'schema':'worldatlas-v7-prefill-class-rle-audit-v1','status':'staged-not-published','prior_ocean_water_labels_read':'none','source_plan_sha256':s.ocean.sha(self.paths['prefill_plan']),'decision_snapshot_sha256':s.ocean.sha(self.paths['prefill_snapshot']),'decision_revision':'base','entity_revision':'e','physical_mask_sha256':'3'*64,'output':{'rows_sha256':'4'*64,'runs_sha256':'5'*64}}))
  add('ocean_candidate_build',write_json(self.inp/'candidate.json',{'schema':'worldatlas-direct-candidate-build-v1','status':'unverified-research-not-published','decision_snapshot_sha256':s.ocean.sha(self.paths['ocean_snapshot']),'decision_revision':'new','entity_revision':'e','physical_rows_sha256':'1'*64,'physical_runs_sha256':'2'*64,'physical_mask_sha256':'3'*64,'physical_report_sha256':'7'*64,'grid':{'width':8,'height':4}}))
  common={'physical_rows_sha256':'1'*64,'physical_runs_sha256':'2'*64,'physical_mask_sha256':'3'*64,'prefill_rows_sha256':'4'*64,'prefill_runs_sha256':'5'*64,'prefill_audit_sha256':s.ocean.sha(self.paths['prefill_audit']),'entity_revision':'e','legacy_ocean_label_inheritance':False}
  for label in ('old','new'):
   p=self.inp/label;p.mkdir();add(label+'_barrier',(p/'barrier'));self.paths[label+'_barrier'].write_bytes(b'')
   rows=[(0,),(4,),(8,),(12,),(16,)];spans=[(0,2,7),(2,4,8),(4,6,9),(6,8,10)]*4
   if label=='new':rows=[(0,),(5,),(9,),(13,),(17,)];spans=[(0,1,10),(1,2,7),(2,4,8),(4,6,9),(6,8,10)]+spans[4:]
   add(label+'_ocean_rows',binary(p/'ocean_rows.u64le','<Q',rows));add(label+'_ocean_spans',binary(p/'ocean_assignment_spans.u32le','<III',spans))
   add(label+'_unseeded_rows',binary(p/'unseeded_rows.u64le','<Q',[(0,)]*5));add(label+'_unseeded_spans',(p/'unseeded_component_spans.u32le'));self.paths[label+'_unseeded_spans'].write_bytes(b'')
   inp={**common,'decision_snapshot_sha256':s.ocean.sha(self.paths['prefill_snapshot' if label=='old' else 'ocean_snapshot']),'decision_revision':'base' if label=='old' else 'new','source_cut_edges_sha256':s.ocean.sha(self.paths[label+'_barrier'])}
   if label=='new':
    exec_code={k:'a'*64 for k in ('adapter','ocean_runner','partition_core','rle_inputs','exclusive_outputs')}
    inp.update(prefill_decision_snapshot_sha256=s.ocean.sha(self.paths['prefill_snapshot']),prefill_plan_sha256=s.ocean.sha(self.paths['prefill_plan']),candidate_build_sha256=s.ocean.sha(self.paths['ocean_candidate_build']),lineage_mode='separately-pinned-prefill-and-ocean-research-decisions',split_execution_code_sha256=exec_code,candidate_code_sha256={name+'.py':exec_code[key] for name,key in [('ocean_fill_runner','ocean_runner'),('partition_core','partition_core'),('rle_inputs','rle_inputs'),('exclusive_outputs','exclusive_outputs')]})
   doc={'schema':'fresh-ocean-run-partition-v1','grid':{'W':8,'H':4},'inputs':inp,'eligible_water_cells':32,'unseeded_cell_count':0,'seed_cells':{},'components':[]}
   add(label+'_partition',write_json(p/'manifest.json',doc))
   tile=p/'tile.jsonl';offsets=[v[0] for v in rows]
   with tile.open('w') as f:
    for y in range(4):f.write(json.dumps({'row':y,'spans':[{'start':v[0],'end':v[1],'code':v[2]} for v in spans[offsets[y]:offsets[y+1]]]})+'\n')
   layer={'schema':'worldatlas-full-water-assignment-tiles-v1','coverage':{'complete':True},'source':inp,'tiles':[{'core_rows':[0,4],'span_file':{'path':'tile.jsonl','sha256':s.ocean.sha(tile)}}]}
   add(label+'_layer_manifest',write_json(p/'ocean-layer-manifest.json',layer))
   summary={'status':'unverified-candidate-not-published','snapshot_sha256':inp['decision_snapshot_sha256'],'barrier_sha256':inp['source_cut_edges_sha256'],'layer_manifest_sha256':s.ocean.sha(self.paths[label+'_layer_manifest'])}
   add(label+'_summary',write_json(p/'run-summary.json',summary))
  closed={'pending_cells':0,'coverage':{'complete':True},'source':{'decision_snapshot_sha256':s.ocean.sha(self.paths['prefill_snapshot']),'decision_revision':'base','entity_revision':'e','legacy_ocean_label_inheritance':False,'physical_rows_sha256':common['physical_rows_sha256'],'physical_runs_sha256':common['physical_runs_sha256'],'prefill_audit_sha256':common['prefill_audit_sha256'],'partition_manifest_sha256':s.ocean.sha(self.paths['old_partition']),'barrier_edges_sha256':s.ocean.sha(self.paths['old_barrier']),'prefill_rows_sha256':common['prefill_rows_sha256'],'prefill_runs_sha256':common['prefill_runs_sha256'],'component_rows_sha256':s.ocean.sha(self.paths['old_unseeded_rows']),'component_spans_sha256':s.ocean.sha(self.paths['old_unseeded_spans'])}}
  add('closed_manifest',write_json(self.inp/'closed.json',closed))
  plan={'decision_snapshot_sha256':s.ocean.sha(self.paths['prefill_snapshot']),'decision_revision':'base','prefill':{'plan_sha256':s.ocean.sha(self.paths['prefill_plan']),'audit_sha256':s.ocean.sha(self.paths['prefill_audit'])},'research_provenance':{'partition_manifest_sha256':s.ocean.sha(self.paths['old_partition'])},'water_layers':[{'layer_id':'ocean','manifest_sha256':s.ocean.sha(self.paths['old_layer_manifest'])},{'layer_id':'enclosed-water','manifest_sha256':s.ocean.sha(self.paths['closed_manifest'])}]}
  add('baseline_plan',write_json(self.inp/'plan.json',plan))
  report={'schema':'worldatlas-direct-final-audit-v1','status':'unverified-research-not-published','publishable':False,'decision_snapshot_sha256':s.ocean.sha(self.paths['prefill_snapshot']),'decision_revision':'base','entity_revision':'e','prefill_audit_sha256':common['prefill_audit_sha256'],'final_plan_sha256':s.ocean.sha(self.paths['baseline_plan']),'output':{'rows_sha256':s.ocean.sha(self.paths['baseline_rows']),'runs_sha256':s.ocean.sha(self.paths['baseline_runs'] )},'counts':{'7':8,'8':8,'9':8,'10':8}}
  add('baseline_report',write_json(self.inp/'report.json',report));self.config=self.inp/'config.json';self.save_config()
 def tearDown(self):self.temp.cleanup()
 def save_config(self):write_json(self.config,{'schema':'worldatlas-split-ocean-final-config-v1','inputs':{k:{'path':str(v),'sha256':s.ocean.sha(v)} for k,v in self.paths.items()}})
 def test_complete_split_composition(self):
  r=s.compose(self.config,self.out);self.assertEqual(r['changed_cells'],1);self.assertEqual(r['pair_counts'],{'7->10':1});self.assertEqual(r['counts']['7'],7);self.assertEqual(r['counts']['10'],9)
 def test_tampered_tile_rejected(self):
  (self.inp/'new/tile.jsonl').write_text('{}\n')
  with self.assertRaisesRegex(ValueError,'tile hash'):s.compose(self.config,self.out)
 def test_changed_seed_rejected(self):
  p=self.paths['new_partition'];d=json.loads(p.read_text());d['seed_cells']={'7':{'x':0,'y':0}};write_json(p,d);self.save_config()
  with self.assertRaisesRegex(ValueError,'seeds'):s.compose(self.config,self.out)
 def test_partition_spans_must_match_layer(self):
  p=self.paths['new_ocean_spans'];data=bytearray(p.read_bytes());data[8:12]=(7).to_bytes(4,'little');p.write_bytes(data);self.save_config()
  with self.assertRaisesRegex(ValueError,'partition spans differ'):s.compose(self.config,self.out)
 def test_ocean_summary_binding_rejected(self):
  p=self.paths['new_summary'];d=json.loads(p.read_text());d['barrier_sha256']='0'*64;write_json(p,d);self.save_config()
  with self.assertRaisesRegex(ValueError,'summary'):s.compose(self.config,self.out)
 def test_closed_layer_must_bind_original_partition(self):
  p=self.paths['closed_manifest'];d=json.loads(p.read_text());d['source']['partition_manifest_sha256']='0'*64;write_json(p,d)
  plan=self.paths['baseline_plan'];x=json.loads(plan.read_text());x['water_layers'][1]['manifest_sha256']=s.ocean.sha(p);write_json(plan,x)
  report=self.paths['baseline_report'];x=json.loads(report.read_text());x['final_plan_sha256']=s.ocean.sha(plan);write_json(report,x);self.save_config()
  with self.assertRaisesRegex(ValueError,'closed layer'):s.compose(self.config,self.out)
 def set_unseeded_fixture(self,new_end=1,new_contacts=0,old_end=1,old_contacts=0):
  for label,root,end,contacts in [('old',11,old_end,old_contacts),('new',22,new_end,new_contacts)]:
   binary(self.paths[label+'_unseeded_rows'],'<Q',[(0,),(1,),(1,),(1,),(1,)])
   binary(self.paths[label+'_unseeded_spans'],'<III',[(0,end,root)])
   p=self.paths[label+'_partition'];d=json.loads(p.read_text());d['unseeded_cell_count']=old_end;d['components']=[{'component_root':root,'source_barrier_contact_edge_count':contacts,'ocean_code':None,'cell_count':old_end}];write_json(p,d)
  p=self.paths['closed_manifest'];d=json.loads(p.read_text());d['source']['partition_manifest_sha256']=s.ocean.sha(self.paths['old_partition']);d['source']['component_rows_sha256']=s.ocean.sha(self.paths['old_unseeded_rows']);d['source']['component_spans_sha256']=s.ocean.sha(self.paths['old_unseeded_spans']);write_json(p,d)
  p=self.paths['baseline_plan'];d=json.loads(p.read_text());d['research_provenance']['partition_manifest_sha256']=s.ocean.sha(self.paths['old_partition']);d['water_layers'][1]['manifest_sha256']=s.ocean.sha(self.paths['closed_manifest']);write_json(p,d)
  p=self.paths['baseline_report'];d=json.loads(p.read_text());d['final_plan_sha256']=s.ocean.sha(self.paths['baseline_plan']);write_json(p,d);self.save_config()
 def test_unseeded_footprint_change_rejected(self):
  self.set_unseeded_fixture(new_end=2)
  with self.assertRaisesRegex(ValueError,'unseeded footprint'):s.compose(self.config,self.out)
 def test_equal_positive_summary_cut_contacts_rejected(self):
  self.set_unseeded_fixture(new_contacts=1,old_contacts=1)
  with self.assertRaisesRegex(ValueError,'source-cut contacts'):s.compose(self.config,self.out)
 def test_unseeded_cut_contact_change_rejected(self):
  self.set_unseeded_fixture(new_contacts=1)
  with self.assertRaisesRegex(ValueError,'source-cut contacts'):s.compose(self.config,self.out)
 def add_internal_barrier(self,label):
  binary(self.paths[label+'_barrier'],'<III',[(0,0,0)])
  p=self.paths[label+'_partition'];d=json.loads(p.read_text());d['inputs']['source_cut_edges_sha256']=s.ocean.sha(self.paths[label+'_barrier']);write_json(p,d)
  p=self.paths[label+'_layer_manifest'];d=json.loads(p.read_text());d['source']['source_cut_edges_sha256']=s.ocean.sha(self.paths[label+'_barrier']);write_json(p,d)
  p=self.paths[label+'_summary'];d=json.loads(p.read_text());d['barrier_sha256']=s.ocean.sha(self.paths[label+'_barrier']);d['layer_manifest_sha256']=s.ocean.sha(self.paths[label+'_layer_manifest']);write_json(p,d)
  if label=='old':
   p=self.paths['closed_manifest'];d=json.loads(p.read_text());d['source']['partition_manifest_sha256']=s.ocean.sha(self.paths['old_partition']);d['source']['barrier_edges_sha256']=s.ocean.sha(self.paths['old_barrier']);write_json(p,d)
   p=self.paths['baseline_plan'];d=json.loads(p.read_text());d['research_provenance']['partition_manifest_sha256']=s.ocean.sha(self.paths['old_partition']);d['water_layers'][0]['manifest_sha256']=s.ocean.sha(self.paths['old_layer_manifest']);d['water_layers'][1]['manifest_sha256']=s.ocean.sha(self.paths['closed_manifest']);write_json(p,d)
   p=self.paths['baseline_report'];d=json.loads(p.read_text());d['final_plan_sha256']=s.ocean.sha(self.paths['baseline_plan']);write_json(p,d)
  self.save_config()
 def test_internal_cut_rejected_even_if_partition_summary_omits_it(self):
  self.set_unseeded_fixture(new_end=2,old_end=2);self.add_internal_barrier('new')
  with self.assertRaisesRegex(ValueError,'conservative unseeded source-cut'):s.compose(self.config,self.out)
 def test_internal_cut_on_both_sides_cannot_reuse_complete_closed_layer(self):
  self.set_unseeded_fixture(new_end=2,old_end=2);self.add_internal_barrier('old');self.add_internal_barrier('new')
  with self.assertRaisesRegex(ValueError,'conservative unseeded source-cut'):s.compose(self.config,self.out)
 def test_zero_length_first_baseline_run_rejected(self):
  p=self.paths['baseline_runs'];raw=bytearray(p.read_bytes());raw[:4]=(0).to_bytes(4,'little');p.write_bytes(raw)
  p=self.paths['baseline_report'];d=json.loads(p.read_text());d['output']['runs_sha256']=s.ocean.sha(self.paths['baseline_runs']);write_json(p,d);self.save_config()
  with self.assertRaisesRegex(ValueError,'invalid baseline row'):s.compose(self.config,self.out)
 def test_ocean_layer_source_must_equal_complete_partition_input(self):
  p=self.paths['new_layer_manifest'];d=json.loads(p.read_text());d['source']['unexpected']='tampered';write_json(p,d)
  p=self.paths['new_summary'];d=json.loads(p.read_text());d['layer_manifest_sha256']=s.ocean.sha(self.paths['new_layer_manifest']);write_json(p,d);self.save_config()
  with self.assertRaisesRegex(ValueError,'ocean layer source binding'):s.compose(self.config,self.out)
 def test_split_helper_hash_mismatch_rejected(self):
  p=self.paths['new_partition'];d=json.loads(p.read_text());d['inputs']['split_execution_code_sha256']['ocean_runner']='b'*64;write_json(p,d)
  p=self.paths['new_layer_manifest'];d=json.loads(p.read_text());d['source']['split_execution_code_sha256']['ocean_runner']='b'*64;write_json(p,d)
  p=self.paths['new_summary'];d=json.loads(p.read_text());d['layer_manifest_sha256']=s.ocean.sha(self.paths['new_layer_manifest']);write_json(p,d);self.save_config()
  with self.assertRaisesRegex(ValueError,'split execution lineage'):s.compose(self.config,self.out)
 def test_duplicate_unseeded_component_root_rejected(self):
  self.set_unseeded_fixture();p=self.paths['new_partition'];d=json.loads(p.read_text());d['components'].append(dict(d['components'][0]));write_json(p,d);self.save_config()
  with self.assertRaisesRegex(ValueError,'component metadata'):s.compose(self.config,self.out)
 def test_unseeded_component_cell_count_mismatch_rejected(self):
  self.set_unseeded_fixture();p=self.paths['new_partition'];d=json.loads(p.read_text());d['components'][0]['cell_count']=99;write_json(p,d);self.save_config()
  with self.assertRaisesRegex(ValueError,'component metadata'):s.compose(self.config,self.out)
 def test_changed_input_hash_rejected(self):
  self.paths['baseline_rows'].write_bytes(b'changed')
  with self.assertRaisesRegex(ValueError,'input hash'):s.compose(self.config,self.out)
if __name__=='__main__':unittest.main()
