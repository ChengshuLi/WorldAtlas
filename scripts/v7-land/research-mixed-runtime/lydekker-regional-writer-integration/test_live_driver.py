import copy,unittest
from test_adapter import fixture,S,C
from live_driver import resolve_live,canonical_sha

class Mixed:
 def __init__(self,selected):self.selected=selected
 def combine(self,*args):return copy.deepcopy(self.selected)

def setup():
 p,c,selected,result=fixture()
 p.update(regional_bounds_lon_lat=[115,-12,145,8],anchor_discovery={'country':'ID'},satellite_policy={'metric':'WGS84 ellipsoidal minimum component-center distance','max_satellite_cells':20,'max_gap_m':5000,'tie_m':0.00001},regional_groups=[])
 result['source_anchors']={};result['replayed_claims']={};result['pending_source_claims']={}
 calls=[]
 def research(*args,**kw):calls.append(('research',kw['pending_claims']));return copy.deepcopy(result)
 def scan(*a):return {1:{'total':2,'in_scope':2},2:{'total':1,'in_scope':1},3:{'total':1,'in_scope':1}}
 def source(*a,**kw):calls.append(('source',));return {'windows':[],'anchors':{},'source_trace':{'fresh':True}}
 def apply_groups(x,w):calls.append(('groups',));return x
 def replay(*a):return {'proposals':{},'replayed_claims':{},'pending_source_claims':{}}
 def satellite(x,*a,**kw):calls.append(('satellites',kw['allow_unanchored_nearest']));return x
 def guard():calls.append(('guard',))
 ident=lambda *a,**kw:None
 d={'research':research,'verified_line':ident,'scan':scan,'buffered_bounds':ident,'resolve_feature_windows':source,'apply_groups':apply_groups,'resolve_with_mixed_replay':replay,'collect_runs':ident,'apply_satellites':satellite,'extract':ident,'intersect':ident,'point_inside':ident,'component_at':ident,'run_pair':ident,'guard':guard,'mixed_claims':Mixed(selected)}
 inputs={'component_rows':{'sha256':C['rows']},'component_runs':{'sha256':C['runs']},'physical_rows':{},'physical_runs':{}}
 sources={'geonames-country-id':{'path':'/unused','sha256':'d'*64,'version':'v'}}
 args=(p,c,{},[],{'width':8,'north':90},inputs,sources,{},)
 kwargs={'snapshot_sha256':S,'policy_canonical_sha256':canonical_sha(p),'mainland_roots':{9},'pending_claims':[{'component_id':3}],'deps':d}
 return args,kwargs,calls

class LiveDriverTests(unittest.TestCase):
 def test_order_and_claim_protections(self):
  args,kw,calls=setup();out=resolve_live(*args,**kw);bridge=out['writer_bridge']
  self.assertEqual([x[0] for x in calls],['guard','research','source','groups','satellites','guard'])
  self.assertTrue(calls[1][1]);self.assertTrue(calls[4][1])
  self.assertNotIn(3,bridge['component_claims']);self.assertIn(3,bridge['blocked_region_roots']);self.assertIn(9,bridge['blocked_region_roots'])
  self.assertEqual(bridge['component_claims'][2][0]['code'],18);self.assertEqual(out['regional_result']['source_group_trace'],{'fresh':True})
 def test_pin_mismatch_stops_before_research(self):
  args,kw,calls=setup();kw['policy_canonical_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'policy pin'):resolve_live(*args,**kw)
  self.assertEqual(calls,[])
 def test_current_generation_must_match(self):
  args,kw,calls=setup();args[5]['component_rows']['sha256']='z'*64
  with self.assertRaisesRegex(ValueError,'component pin'):resolve_live(*args,**kw)
  self.assertEqual(calls,[])
class LiveWriterIntegration(unittest.TestCase):
 def test_orchestration_to_real_overlay_blocks_region_bypass(self):
  import importlib.util,os
  from adapter import protected_region_rows,RULE
  path=os.environ.get('OVERLAY_PATH')
  if not path:self.skipTest('actual writer overlay unavailable')
  spec=importlib.util.spec_from_file_location('actual_live_overlay',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  args,kw,calls=setup();b=resolve_live(*args,**kw)['writer_bridge'];stats={};changes=[]
  raw=lambda row:[{'claim':{'affiliation_id':'other','entry_ids':['entry'],'code':22},'roots':{3,9},'spans':[(0,4)]}]
  region=protected_region_rows(raw,b['blocked_region_roots'])(0)
  out=m.overlay_row(4,[(0,4,17)],[(4,18)],[(0,1,1),(1,2,2),(2,3,3),(3,4,9)],b['component_claims'],region,stats,lambda *v:changes.append(v))
  self.assertEqual(out,[(1,22),(4,18)]);self.assertEqual(stats[RULE]['applied_cells'],1);self.assertNotIn('other',stats);self.assertNotIn('pending',stats)
if __name__=='__main__':unittest.main()
