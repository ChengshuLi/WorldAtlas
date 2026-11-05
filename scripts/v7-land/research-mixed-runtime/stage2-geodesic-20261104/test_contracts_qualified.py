import copy,unittest
import contracts as c

class ContractsTests(unittest.TestCase):
 def setUp(self):
  self.rev='d';self.ent='e';self.grid={'width':8,'height':4,'west':-180,'north':90,'step':45}
  self.metric={'policy_id':'wgs','version':'1','decision_revision':'d','execution_status':'selected_for_research','algorithm':'wgs84_ellipsoidal_geodesic_inverse','units':'metres','semi_major_axis_m':'6378137','inverse_flattening':'298.257223563'}
  self.snapshot={'schema':'worldatlas-geography-decision-draft-evidence-v1','source':'neon-export','decision_revision':{'id':'d','entity_revision':'e','status':'draft'},'entity_revision':{'id':'e','status':'draft'},'distance_policies':[self.metric], 'entities':[{'id':i,'name':'c'+str(i),'level':'continent'} for i in range(6)],'category_bindings':[{'entity_id':i,'code':17+i,'physical_class':'land'} for i in range(6)]}
  names=('physical_rows','physical_runs','component_rows','component_runs','component_manifest','component_source','component_builder_binary','physical_report','seed_rows','seed_runs','resolution_report','decision_snapshot','hint_roots','hint_codes','hint_report','representatives','tile_manifest');self.pins={k:str(i).zfill(64) for i,k in enumerate(names)}
  self.groups=[{'group_id':'g','role':'mainland','target_entity_ids':[0,1],'component_id_current_generation_only':7},{'group_id':'s','role':'sentinel','target_entity_ids':[],'component_id_current_generation_only':9}]
  self.res={'schema':'mainland-witness-resolution-v1','status':'selected-research-identity-claims-not-mainland-proof','publishable':False,'grid':self.grid,'decision_revision':'d','entity_revision':'e','snapshot_sha256':self.pins['decision_snapshot'],'component_manifest_sha256':self.pins['component_manifest'],'input_sha256':{x:self.pins[x] for x in ('physical_rows','physical_runs','component_rows','component_runs')},'groups':self.groups}
  self.man={'schema':'single-generation-component-manifest-v1','status':'complete-research','grid':self.grid,'pins':{x:{'sha256':self.pins[x]} for x in ('physical_rows','physical_runs','component_rows','component_runs')},'component_source_sha256':self.pins['component_source'],'builder_binary_sha256':self.pins['component_builder_binary'],'builder_binary':{'sha256':self.pins['component_builder_binary']},'physical_report':{'sha256':self.pins['physical_report']},'compiler_version':'c','builder_output':'ok'}
  self.seed={'schema':'worldatlas-stage2-mainland-seed-report-v1','status':'diagnostic-seed-pending-independent-provenance','publishable':False,'grid':self.grid,'decision_snapshot_sha256':self.pins['decision_snapshot'],'resolution_report_sha256':self.pins['resolution_report'],'decision_revision':'d','entity_revision':'e',**{x+'_sha256':self.pins[x] for x in ('physical_rows','physical_runs','component_rows','component_runs','seed_rows','seed_runs')},'component_manifest_sha256':self.pins['component_manifest'],'physical_report_sha256':self.pins['physical_report'],'physical_code_contract':{'water':1,'land':17},'seed_roots':[7],'code_sha256':{'seed.py':'a'*64},'seed_rules':[{'rule_id':'r','group_id':'g','component_id_current_generation_only':7,'region_id':'z','inside_entity_id':0,'outside_entity_id':1,'inside_code':17,'outside_code':18}],'region_traces':[{'revision_id':'d','region_id':'z','geometry_sha256':'f'*64,'input_trace':[{'route_id':'x'}],'method':'v1'}]}
  self.hints={'schema':'source-only-hints-diagnostic-report-v1','status':'diagnostic-not-independently-authenticated','publishable':False,'grid':self.grid,'decision_revision':'d','entity_revision':'e','distance_policy':self.metric,'seed_roots':[7],'inputs_sha256':{k:self.pins[k] for k in ('physical_rows','physical_runs','component_rows','component_runs','seed_rows','seed_runs','representatives','tile_manifest','resolution_report','decision_snapshot','component_manifest')},'roots_sha256':self.pins['hint_roots'],'hints_sha256':self.pins['hint_codes'],'root_count':3,'code_sha256':{'hints.py':'b'*64,'run_diagnostic.py':'c'*64}}
  self.monitor={'schema':'source-only-hints-watchdog-v1','status':'sampled-complete','diagnostic_report_sha256':self.pins['hint_report'],'watchdog_sha256':'d'*64,'samples':10,'minimum_available_kib':100,'minimum_memory_kib':90,'peak_child_rss_kib':20,'maximum_child_rss_kib':40}
 def test_selected_seed_crosswalk_rejects_incomplete_policy(self):
  with self.assertRaisesRegex(ValueError,'missing selected simple land policy'):c.validate_selected_seed_decisions(self.snapshot,self.seed,{}, {},self.metric)
 def test_policy_tolerance_decimal_and_invalid(self):
  self.assertEqual(c.policy_tolerance_metres({'tie_tolerance_metres':'0.00001'}),.00001)
  for x in (None,True,'NaN','Infinity','-0.1','1e9999','1e-9999'):
   with self.assertRaisesRegex(ValueError,'tie tolerance'):c.policy_tolerance_metres({'tie_tolerance_metres':x})
 def test_valid_chain(self):
  metric,codes,entity=c.snap_policy(self.snapshot,'d','e','wgs','1');groups=c.resolution_roots(self.res,self.grid,self.pins,'d','e');c.component_manifest(self.man,self.grid,self.pins);roots=c.seed_report(self.seed,self.grid,self.pins,'d','e',groups,entity,{'seed.py':'a'*64});n=c.hints_report(self.hints,self.monitor,self.grid,self.pins,'d','e',metric,roots,{'hints.py':'b'*64,'run_diagnostic.py':'c'*64},'d'*64);self.assertEqual((roots,n),([7],3))
 def test_snapshot_rejects_nonselected_and_wrong_metric(self):
  self.metric['execution_status']='proposed_not_selected'
  with self.assertRaisesRegex(ValueError,'selected distance'):c.snap_policy(self.snapshot,'d','e','wgs','1')
  self.metric['execution_status']='selected_for_research';self.metric['inverse_flattening']='300'
  with self.assertRaisesRegex(ValueError,'unsupported geodesic'):c.snap_policy(self.snapshot,'d','e','wgs','1')
 def test_rejected_or_stale_roots_fail(self):
  self.res['input_sha256']['component_runs']='f'*64
  with self.assertRaisesRegex(ValueError,'stale resolution'):c.resolution_roots(self.res,self.grid,self.pins,'d','e')
  self.res['input_sha256']['component_runs']=self.pins['component_runs'];self.groups[1]['component_id_current_generation_only']=7
  with self.assertRaisesRegex(ValueError,'invalid group root'):c.resolution_roots(self.res,self.grid,self.pins,'d','e')
 def test_seed_old_or_mismatched_fails(self):
  groups=c.resolution_roots(self.res,self.grid,self.pins,'d','e');self.seed['schema']='simple-v2-land-report-v1'
  with self.assertRaisesRegex(ValueError,'stage-2 seed'):c.seed_report(self.seed,self.grid,self.pins,'d','e',groups,{0:17,1:18},{'seed.py':'a'*64})
  self.seed['schema']='worldatlas-stage2-mainland-seed-report-v1';self.seed['seed_rules'][0]['outside_code']=19
  with self.assertRaisesRegex(ValueError,'entity/code'):c.seed_report(self.seed,self.grid,self.pins,'d','e',groups,{0:17,1:18},{'seed.py':'a'*64})
 def test_seed_grid_mismatch_rejected(self):
  groups=c.resolution_roots(self.res,self.grid,self.pins,'d','e');self.seed['grid']={**self.grid,'width':16}
  with self.assertRaisesRegex(ValueError,'matching grid'):c.seed_report(self.seed,self.grid,self.pins,'d','e',groups,{0:17,1:18},{'seed.py':'a'*64})
 def test_hints_not_final_and_watchdog_required(self):
  self.hints['inputs_sha256']['seed_rows']='f'*64
  with self.assertRaisesRegex(ValueError,'stale hint input'):c.hints_report(self.hints,self.monitor,self.grid,self.pins,'d','e',self.metric,[7],{'hints.py':'b'*64,'run_diagnostic.py':'c'*64},'d'*64)
  self.hints['inputs_sha256']['seed_rows']=self.pins['seed_rows'];self.monitor['samples']=0
  with self.assertRaisesRegex(ValueError,'watchdog'):c.hints_report(self.hints,self.monitor,self.grid,self.pins,'d','e',self.metric,[7],{'hints.py':'b'*64,'run_diagnostic.py':'c'*64},'d'*64)

class CrosswalkTests(unittest.TestCase):
 def setUp(self):
  ContractsTests.setUp(self)
  import hashlib,json
  def gh(p):return hashlib.sha256(json.dumps({'type':'LineString','coordinates':p},sort_keys=True,separators=(',',':')).encode()).hexdigest()
  line=[[-1.0,0.0],[1.0,0.0]];route=[[1.0,0.0],[0.0,1.0],[-1.0,0.0]];lg=gh(line);rg=gh(route);polygon_hash=hashlib.sha256(json.dumps({'type':'Polygon','coordinates':[[*line,*route[1:]]]},sort_keys=True,separators=(',',':')).encode()).hexdigest();self.groups={};rules=[];result=[]
  for i,(a,b,region) in enumerate([(0,1,'z'),(2,2,None),(3,3,None),(4,4,None),(5,5,None)]):
   gid='g'+str(i);rid='r'+str(i);root=10+i;self.groups[gid]={'group_id':gid,'role':'mainland','target_entity_ids':sorted({a,b}),'component_id_current_generation_only':root};rules.append({'rule_id':rid,'decision_revision':'d','execution_status':'selected_for_research','group_id':gid,'region_id':region,'inside_entity_id':a,'outside_entity_id':b});result.append({'rule_id':rid,'group_id':gid,'component_id_current_generation_only':root,'region_id':region,'inside_entity_id':a,'outside_entity_id':b,'inside_code':17+a,'outside_code':17+b})
  pins={x:format(i+1,'064x') for i,x in enumerate(('physical_rows','physical_runs','physical_report','closure_contract','closure_checker','terminal_checker'))}
  proof={'schema':'physical-water-closure-proof-v1','status':'valid','geometry_sha256':rg,'physical_rows_sha256':pins['physical_rows'],'physical_runs_sha256':pins['physical_runs'],'physical_report_sha256':pins['physical_report'],'contract_sha256':pins['closure_contract'],'checker_sha256':pins['closure_checker']}
  common={'decision_revision':'d','execution_status':'selected_for_research','coordinate_reference':'OGC:CRS84','geometry_hash_method':'binary64-sorted-compact-geojson-v1'}
  boundary={'boundary_id':'b',**common,'method':'stored_linestring_v1','geometry':{'type':'LineString','coordinates':line},'geometry_sha256':lg,'provenance':{'source_refs':[{'source_id':'s','version':'1'}],'source_relationships':[{'source_id':'s','version':'1','relationship':'construction_input'}],'lineage_status':'incomplete'}};rte={'route_id':'q',**common,'route_type':'stored_linestring_v1','role':'water_closure','closure_method':'physical_water_closure_v1','geometry':{'type':'LineString','coordinates':route},'geometry_sha256':rg}
  segs=[{'kind':'boundary','id':'b','start':0,'end':2,'reverse':False},{'kind':'route','id':'q','start':0,'end':3,'reverse':False}];self.snapshot.update({'mainland_component_rules':rules,'mainland_boundaries':[boundary],'routes':[rte],'seed_regions':[{'region_id':'z','decision_revision':'d','execution_status':'selected_for_research','geometry_hash_method':'binary64-sorted-compact-geojson-v1','geometry_sha256':polygon_hash,'segments':segs}],'sources':[{'source_id':'s','version':'1','sha256':'a'*64,'r2_bucket':'raw','r2_key':'s','size_bytes':100}],'source_lineage_assets':[{'source_id':'s','version':'1','sha256':'a'*64,'r2_bucket':'raw','r2_key':'s','size_bytes':100,'kind':'raw','provider':'provider','source_uri':'https://example.org','provenance':{'representation':'provider_original','origin':'provider'}}],'source_lineage_dependencies':[]})
  self.snapshot['land_baseline_policy']={'policy_id':'l','version':'1','decision_revision':'d','execution_status':'selected_for_research','distance_policy_id':'wgs','distance_policy_version':'1','connectivity':'four_neighbor_longitude_wrapped','aggregation':'minimum_over_component_and_mainland_cells','endpoints':'physical_land_cell_centers','tie':'lowest_category_code','tie_tolerance_metres':'0.00001','island_overrides':'none','grid':self.grid,'physical_rows_sha256':pins['physical_rows'],'physical_runs_sha256':pins['physical_runs'],'physical_report_sha256':pins['physical_report'],'mainland_rule_ids':[r['rule_id'] for r in rules],'region_ids':['z'],'boundary_ids':['b'],'route_ids':['q']}
  prov={'lineage_status':'incomplete','source_refs':[{'source_id':'s','version':'1'}],**{k+'_sha256':pins[k] for k in ('physical_rows','physical_runs','physical_report')},'contract_sha256':pins['closure_contract'],'checker_sha256':pins['closure_checker']};self.snapshot['routes'][0]['provenance']=prov;self.snapshot['stage1_source_inputs']=[{'source_id':'s','source_version':'1','decision_revision':'d','execution_status':'selected_for_research'}]
  traces=[{**segs[0],'geometry_sha256':lg,'lineage_status':'incomplete','source_citations':[{'source_id':'s','version':'1','relationship':'construction_input','role':'construction_input','sha256':'a'*64,'bucket':'raw','key':'s'}],'closure_proof':None,'route_provenance':None},{**segs[1],'geometry_sha256':rg,'lineage_status':'incomplete','route_provenance':prov,'source_citations':[{'source_id':'s','version':'1','sha256':'a'*64,'bucket':'raw','key':'s','origin':'provider'}],'closure_proof':proof}]
  self.seed={'grid':self.grid,'physical_rows_sha256':pins['physical_rows'],'physical_runs_sha256':pins['physical_runs'],'physical_report_sha256':pins['physical_report'],'seed_rules':result,'input_sha256':pins,'region_traces':[{'region_id':'z','revision_id':'d','geometry_sha256':polygon_hash,'input_trace':traces}]};self.codes={i:17+i for i in range(6)}
 def check(self):return c.validate_selected_seed_decisions(self.snapshot,self.seed,self.groups,self.codes,self.metric)
 def test_full_crosswalk_and_tampers(self):
  self.assertEqual(self.check(),self.snapshot['land_baseline_policy'])
  for obj,key,bad in [(self.snapshot['land_baseline_policy'],'distance_policy_version','forged'),(self.seed['seed_rules'][0],'inside_code',22),(self.seed['region_traces'][0]['input_trace'][0],'geometry_sha256','0'*64),(self.seed['region_traces'][0]['input_trace'][1]['closure_proof'],'checker_sha256','0'*64),(self.snapshot['source_lineage_assets'][0],'kind','derived'),(self.snapshot['land_baseline_policy'],'connectivity','unwrapped')]:
   old=obj[key];obj[key]=bad
   with self.assertRaises(ValueError):self.check()
   obj[key]=old
 def test_boundary_cannot_claim_route_provenance(self):
  self.seed['region_traces'][0]['input_trace'][0]['route_provenance']={'forged':True}
  with self.assertRaisesRegex(ValueError,'invalid boundary provenance'):self.check()
 def test_qualified_support_is_not_construction(self):
  b=self.snapshot['mainland_boundaries'][0];t=self.seed['region_traces'][0]['input_trace'][0]['source_citations'][0];relation='local_geographic_comparison_not_terrain_or_construction_proof';b['provenance']['source_relationships'][0]['relationship']=relation;t['relationship']=relation;t['role']='supporting_research_evidence';self.assertTrue(self.check())
  t['role']='construction_input'
  with self.assertRaisesRegex(ValueError,'boundary citations mismatch'):self.check()
 def test_source_relationships_missing_unknown_or_incomplete_fail(self):
  b=self.snapshot['mainland_boundaries'][0]['provenance'];b['source_relationships'][0]['relationship']='unreviewed'
  with self.assertRaisesRegex(ValueError,'unsupported'):self.check()
  b['source_relationships'][0]['relationship']='local_geographic_comparison_not_terrain_or_construction_proof';b['lineage_status']='complete';self.seed['region_traces'][0]['input_trace'][0]['lineage_status']='complete'
  with self.assertRaisesRegex(ValueError,'boundary lineage'):self.check()
 def test_empty_physical_source_set_fails(self):
  self.snapshot['stage1_source_inputs']=[];self.snapshot['routes'][0]['provenance']['source_refs']=[]
  with self.assertRaisesRegex(ValueError,'route source selection'):self.check()
 def test_zero_physical_asset_size_fails(self):
  src=dict(self.snapshot['sources'][0]);asset=copy.deepcopy(self.snapshot['source_lineage_assets'][0]);src.update(source_id='route-asset',size_bytes=0);asset.update(source_id='route-asset',size_bytes=0);self.snapshot['sources'].append(src);self.snapshot['source_lineage_assets'].append(asset)
  self.snapshot['stage1_source_inputs']=[{'source_id':'route-asset','source_version':'1','decision_revision':'d','execution_status':'selected_for_research'}];self.snapshot['routes'][0]['provenance']['source_refs']=[{'source_id':'route-asset','version':'1'}]
  with self.assertRaisesRegex(ValueError,'invalid route source custody'):self.check()
 def test_jointly_forged_route_physical_pins_fail(self):
  pins=self.seed['input_sha256'];route=self.snapshot['routes'][0]['provenance'];proof=self.seed['region_traces'][0]['input_trace'][1]['closure_proof']
  for key in ('physical_rows','physical_runs','physical_report'):
   pins[key]='f'*64;route[key+'_sha256']='f'*64;proof[key+'_sha256']='f'*64
  with self.assertRaisesRegex(ValueError,'proof physical pins differ'):self.check()
 def test_forged_physical_report_pin_fails(self):
  proof=self.seed['region_traces'][0]['input_trace'][1]['closure_proof'];proof['physical_report_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'closure proof mismatch'):self.check()
 def test_decimal_string_policy_grid_matches_numeric(self):
  self.snapshot['land_baseline_policy']['grid']={'width':8,'height':4,'west':'-180','north':'90','step':'45'};self.assertTrue(self.check())
  self.snapshot['land_baseline_policy']['grid']['step']='44.9'
  with self.assertRaisesRegex(ValueError,'invalid selected policy grid'):self.check()
 def test_resource_guard_interrupts_crosswalk(self):
  calls=[]
  def guard():
   calls.append(1)
   if len(calls)==3:raise RuntimeError('resource floor')
  with self.assertRaisesRegex(RuntimeError,'resource floor'):c.validate_selected_seed_decisions(self.snapshot,self.seed,self.groups,self.codes,self.metric,guard=guard)
 def test_forged_matching_region_hash_fails(self):
  self.snapshot['seed_regions'][0]['geometry_sha256']='f'*64;self.seed['region_traces'][0]['geometry_sha256']='f'*64
  with self.assertRaisesRegex(ValueError,'polygon hash/closure'):self.check()
 def test_disconnected_selected_slices_fail(self):
  self.snapshot['seed_regions'][0]['segments'][1]['start']=1;self.seed['region_traces'][0]['input_trace'][1]['start']=1
  with self.assertRaisesRegex(ValueError,'do not join'):self.check()
 def test_terminal_proof_and_reverse_terminals(self):
  import hashlib,json
  route=self.snapshot['routes'][0];route['closure_method']='physical_terminal_closure_v1';route['provenance']['checker_sha256']=self.seed['input_sha256']['terminal_checker'];route['start_terminal']={'boundary_id':'b','endpoint':'end'};route['end_terminal']={'boundary_id':'b','endpoint':'start'}
  p=self.seed['region_traces'][0]['input_trace'][1]['closure_proof'];p.update({'schema':'physical-terminal-closure-proof-v1','checker_sha256':self.seed['input_sha256']['terminal_checker'],'support_checker_sha256':self.seed['input_sha256']['closure_checker'],'no_land_land_edge_touched':True,'start_geometry_sha256':self.snapshot['mainland_boundaries'][0]['geometry_sha256'],'end_geometry_sha256':self.snapshot['mainland_boundaries'][0]['geometry_sha256'],'start_endpoint':'end','end_endpoint':'start'})
  self.assertTrue(self.check());p['no_land_land_edge_touched']=False
  with self.assertRaisesRegex(ValueError,'terminal closure checker'):self.check()
if __name__=='__main__':unittest.main()
