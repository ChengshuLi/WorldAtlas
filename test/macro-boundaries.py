import hashlib, importlib.util, json, pathlib, sys, unittest
from shapely.geometry import Polygon, box
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('macro',ROOT/'scripts/prepare-macro-boundary-decisions.py');macro=importlib.util.module_from_spec(spec);spec.loader.exec_module(macro)
class MajorityTests(unittest.TestCase):
 def test_strict_majority_and_partial_source_denominator(self):
  self.assertIsNone(macro.majority(.5,.5));self.assertIsNone(macro.majority(.49,.01));self.assertEqual(macro.majority(.51,.01),'first');self.assertEqual(macro.majority(.1,.6),'second')
 def test_ellipsoidal_area_weighting_changes_degree_area_tie(self):
  whole=box(0,0,1,80);low=box(0,0,1,40);high=box(0,40,1,80)
  self.assertAlmostEqual(low.area/whole.area,.5);self.assertGreater(macro.area(low)/macro.area(whole),.6);self.assertEqual(macro.majority(macro.area(low)/macro.area(whole),macro.area(high)/macro.area(whole)),'first')
 def test_holes_are_not_land(self):
  whole=Polygon([(0,0),(2,0),(2,2),(0,2)],holes=[[(.1,.1),(.9,.1),(.9,1.9),(.1,1.9)]])
  left=whole.intersection(box(0,0,1,2));right=whole.intersection(box(1,0,2,2));self.assertLess(macro.area(left)/macro.area(whole),.5);self.assertEqual(macro.majority(macro.area(left)/macro.area(whole),macro.area(right)/macro.area(whole)),'second')
 def test_every_macro_and_location_inventoried_exactly(self):
  d=json.loads((ROOT/'data/macro-boundary-decisions.json').read_text());features=[]
  for part in json.loads((ROOT/'data/world-index.json').read_text())['parts']:features.extend(json.loads((ROOT/'data'/part).read_text())['features'])
  wanted={f['properties']['id'] for f in features}
  for level,count in [('continent',6),('subcontinent',29)]:
   groups=[g for g in d['groups'] if g['level']==level];self.assertEqual(len(groups),count);ids=[x for g in groups for x in g['location_ids']];self.assertEqual(len(ids),len(set(ids)));self.assertEqual(set(ids),wanted)
  self.assertFalse(d['summary']['semantic_complete']);self.assertTrue(all(g['semantic_status']=='open' for g in d['groups']))
 def test_all_proposed_chains_complete_and_original_geometry_untouched(self):
  d=json.loads((ROOT/'data/macro-boundary-decisions.json').read_text());h={u['id']:dict(u) for u in json.loads((ROOT/'data/hierarchy.json').read_text())};before=set(h);features=[]
  for part in json.loads((ROOT/'data/world-index.json').read_text())['parts']:features.extend(json.loads((ROOT/'data'/part).read_text())['features'])
  for u in d['new_groups']:self.assertNotIn(u['id'],h);h[u['id']]=u
  for p in d['group_changes']:
   old=h[p['id']];self.assertEqual(old['name'],p['current_name']);self.assertEqual(old['parent_id'],p['current_parent_id'])
   if p['action']=='rename':old['name']=p['name']
   else:old['parent_id']=p['parent_id']
  changes={x['id']:x for x in d['location_changes']};self.assertEqual(len(changes),d['summary']['whole_location_reparents']);used=set()
  for f in features:
   p=f['properties'];parent=p['parent_id']
   if p['id'] in changes:
    c=changes[p['id']];self.assertEqual(parent,c['current_parent_id']);self.assertEqual(p['name'],c['current_name']);self.assertEqual(hashlib.sha256(json.dumps(f['geometry'],sort_keys=True,separators=(',',':')).encode()).hexdigest(),c['geometry_sha256']);parent=c['parent_id']
   for level in ['province','area','region','subcontinent','continent']:
    self.assertEqual(h[parent]['level'],level);used.add(parent);parent=h[parent]['parent_id']
   self.assertIsNone(parent)
  self.assertTrue(before.issubset(h));self.assertTrue(all(u['id'] in used for u in d['new_groups']))
  for c in changes.values():
   parent=c['parent_id']
   for _ in range(4):parent=h[parent]['parent_id']
   self.assertEqual(h[parent]['name'],c['evidence']['proposed_continent'])
 def test_proof_pins_actual_inputs_and_rejects_incomplete_source_majority(self):
  d=json.loads((ROOT/'data/macro-boundary-decisions.json').read_text())
  for path,pin in d['input_sha256'].items():self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),pin,path)
  for c in d['location_changes']:
   e=c['evidence'];side=e['first_share'] if e['proposed_continent']==e['first_continent'] else e['second_share'];self.assertGreater(side-e['source_uncertainty_share'],.5+1e-8);self.assertAlmostEqual(e['first_share']+e['second_share']+e['outside_surveyed_share'],1,places=9)
  self.assertTrue(d['unresolved_physical_segments']);self.assertGreater(d['summary']['unresolved_measured_locations'],0)
if __name__=='__main__':unittest.main()
