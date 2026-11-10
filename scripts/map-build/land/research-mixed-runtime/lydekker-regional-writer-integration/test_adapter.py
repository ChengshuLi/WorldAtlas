import copy,unittest,hashlib,json
from adapter import merge_live_claims,filter_region_claims,protected_region_rows,RULE,LINE,LINE_SHA
S='a'*64; C={'rows':'b'*64,'runs':'c'*64}
def fixture():
 p={'rule_set_id':RULE,'status':'selected_for_research','decision_revision':'r','line':{'line_id':LINE,'geometry_sha256':LINE_SHA},'evidence':{'component_rows_sha256':C['rows'],'component_runs_sha256':C['runs']}}
 c={'revision':'r','affiliation_ids':['selected','pending'],'affiliation_entry_links':{'selected':['entry'],'pending':['entry']}};selected={1:[{'affiliation_id':'selected','entry_ids':['entry'],'code':22}],3:[{'affiliation_id':'pending','entry_ids':['entry'],'code':18}]};r={'line_id':LINE,'geometry_sha256':LINE_SHA,'component_input_sha256':C,'proposals':{1:{'basis':'selected_affiliation','code':22},2:{'basis':'whole_component_line_side','code':18}},'review':{3:'source_group_pending_review'}}
 return p,c,selected,r
def digest(p):return hashlib.sha256(json.dumps(p,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def run(p,c,s,r,**kw):return merge_live_claims(p,c,s,r,snapshot_sha256=S,component_sha256=C,policy_canonical_sha256=digest(p),pending_roots=kw.get('pending',{3}),protected_roots=kw.get('protected',{9}))
class Tests(unittest.TestCase):
 def test_selected_preserved_pending_withheld_regional_added(self):
  p,c,s,r=fixture();out=run(p,c,s,r);self.assertEqual(out['component_claims'][1],s[1]);self.assertNotIn(3,out['component_claims']);self.assertEqual(out['withheld_selected_pending_roots'],[3]);self.assertEqual(out['component_claims'][2][0]['code'],18);self.assertEqual(out['component_claims'][2][0]['affiliation_id'],RULE)
 def test_conflicts_and_stale_inputs_fail_closed(self):
  p,c,s,r=fixture();r['proposals'][1]['code']=18
  with self.assertRaisesRegex(ValueError,'selected'):run(p,c,s,r)
  p,c,s,r=fixture();r['review'][2]='conflicting_group_and_anchor'
  with self.assertRaisesRegex(ValueError,'reviewed'):run(p,c,s,r)
  p,c,s,r=fixture();r['component_input_sha256']={'rows':'x','runs':'y'}
  with self.assertRaisesRegex(ValueError,'generation'):run(p,c,s,r)
  p,c,s,r=fixture()
  with self.assertRaisesRegex(ValueError,'protected'):run(p,c,s,r,protected={2,9})
  p,c,s,r=fixture();s[1][0]['entry_ids']=['unlinked']
  with self.assertRaisesRegex(ValueError,'linked'):run(p,c,s,r)
  p,c,s,r=fixture()
  with self.assertRaisesRegex(ValueError,'policy definition'):merge_live_claims(p,c,s,r,snapshot_sha256=S,component_sha256=C,policy_canonical_sha256='f'*64,pending_roots=set(),protected_roots=set())
 def test_reviewed_pending_is_withheld_even_if_caller_omits_it(self):
  p,c,s,r=fixture();out=run(p,c,s,r,pending=set())
  self.assertNotIn(3,out['component_claims']);self.assertEqual(out['withheld_selected_pending_roots'],[3])
  self.assertIn(3,out['blocked_region_roots'])
 def test_region_channel_filters_pending_review_and_protected(self):
  claim={'affiliation_id':'other','entry_ids':['entry'],'code':22}
  source=[{'claim':claim,'roots':{3,4,9,10},'spans':[(0,6)]}]
  out=filter_region_claims(source,{3,4,9})
  self.assertEqual(out[0]['roots'],{10});self.assertEqual(source[0]['roots'],{3,4,9,10})
  self.assertEqual(filter_region_claims(source,{3,4,9,10}),[])
 def test_source_evidence_required_and_retained(self):
  p,c,s,r=fixture();r['proposals'][2]={'basis':'source_anchored_nearest_main_island','code':18}
  with self.assertRaisesRegex(ValueError,'satellite source'):run(p,c,s,r)
  r['satellites']={2:{'source_id':'gazette','source_feature_id':'island','source_version':'v1','source_sha256':'d'*64,'parent_root_current_generation_only':8,'distance_m':500}}
  out=run(p,c,s,r);self.assertEqual(out['regional_proposal_trace'][2]['evidence']['source_id'],'gazette')
  r['proposals'][2]={'basis':'inferred_source_extent_group_convention','code':18}
  with self.assertRaisesRegex(ValueError,'regional-group'):run(p,c,s,r)
  r['regional_group_proposals']={2:[{'group_id':'group','target_code':18,'source':{'id':'source'}}]}
  out=run(p,c,s,r);self.assertEqual(out['regional_proposal_trace'][2]['evidence'][0]['group_id'],'group')
 def test_region_callback_cannot_leak_protected_root(self):
  raw=lambda row:[{'claim':{'affiliation_id':'other','entry_ids':['entry'],'code':22},'roots':{3,10},'spans':[(0,6)]}]
  wrapped=protected_region_rows(raw,{3});self.assertEqual(wrapped(0)[0]['roots'],{10})
 def test_user_protections_are_explicit(self):
  p,c,s,r=fixture()
  with self.assertRaises(TypeError):merge_live_claims(p,c,s,r,snapshot_sha256=S,component_sha256=C,policy_canonical_sha256=digest(p),protected_roots=set())

class OverlayIntegration(unittest.TestCase):
 def test_real_overlay_blocks_all_claim_channels_but_retains_baseline(self):
  import importlib.util,os
  path=os.environ.get('OVERLAY_PATH')
  if not path:self.skipTest('actual writer overlay unavailable')
  spec=importlib.util.spec_from_file_location('actual_mixed_overlay',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  p,c,s,r=fixture();r['review'][4]='conflicting_group_and_anchor';bridge=run(p,c,s,r,pending=set());changes=[];stats={}
  region=[{'claim':{'affiliation_id':'other','entry_ids':['entry'],'code':22},'roots':{3,4,9},'spans':[(0,5)]}]
  filtered=protected_region_rows(lambda row:region,bridge['blocked_region_roots'])(0)
  result=m.overlay_row(5,[(0,5,17)],[(5,18)],[(0,1,1),(1,2,2),(2,3,3),(3,4,4),(4,5,9)],bridge['component_claims'],filtered,stats,lambda *x:changes.append(x))
  self.assertEqual(result,[(1,22),(5,18)])
  self.assertEqual(stats['selected']['applied_cells'],1);self.assertEqual(stats[RULE]['applied_cells'],1)
  self.assertNotIn('pending',stats);self.assertNotIn('other',stats);self.assertEqual(len(changes),1)
