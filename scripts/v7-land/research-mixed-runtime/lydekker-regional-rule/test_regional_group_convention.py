import unittest
from regional_group_convention import apply_groups
class TestGroups(unittest.TestCase):
 def test_only_complete_endpoint_held_roots_apply(self):
  result={'proposals':{2:{'code':22,'basis':'selected_affiliation'},3:{'code':18,'basis':'whole_component_line_side'}},'review':{1:'outside_line_latitude',4:'source_group_pending_review',5:'protected_mainland',6:'partly_outside_region',7:'crosses_or_touches_line'}}
  components={i:{'total':2,'in_scope':1 if i==6 else 2} for i in range(1,8)}
  result=apply_groups(result,[{'group_id':'x','code':18,'components':components,'source':{'id':'s'}}])
  self.assertEqual(result['proposals'][1]['code'],18);self.assertEqual(result['proposals'][2]['code'],22)
  self.assertEqual(result['selected_group_conflicts'][2][0]['target_code'],18)
  self.assertNotIn(4,result['proposals']);self.assertNotIn(5,result['proposals']);self.assertNotIn(6,result['proposals']);self.assertNotIn(7,result['proposals'])
 def test_opposing_group_conventions_remain_review(self):
  r={'proposals':{},'review':{1:'outside_line_latitude'}};c={1:{'total':1,'in_scope':1}}
  out=apply_groups(r,[{'group_id':'a','code':18,'components':c,'source':{}},{'group_id':'b','code':22,'components':c,'source':{}}])
  self.assertNotIn(1,out['proposals']);self.assertEqual(out['review'][1],'conflicting_regional_group_conventions')
  self.assertEqual({(z['group_id'],z['target_code']) for z in out['regional_group_proposals'][1]},{('a',18),('b',22)})

class TestCrossPassGroups(unittest.TestCase):
 def test_opposition_across_calls_holds_and_preserves_both_sources(self):
  c={1:{'total':1,'in_scope':1}}
  a={'group_id':'a','code':18,'components':c,'source':{'id':'a'}}
  b={'group_id':'b','code':22,'components':c,'source':{'id':'b'}}
  first=apply_groups({'proposals':{},'review':{1:'outside_line_latitude'}},[a])
  same=apply_groups(first,[dict(a,group_id='a2')])
  self.assertEqual(same['proposals'][1]['code'],18);self.assertEqual(len(same['regional_group_proposals'][1]),2)
  conflict=apply_groups(same,[b])
  self.assertNotIn(1,conflict['proposals']);self.assertEqual(conflict['review'][1],'conflicting_regional_group_conventions')
  self.assertEqual({(x['group_id'],x['target_code']) for x in conflict['regional_group_proposals'][1]},{('a',18),('a2',18),('b',22)})
  again=apply_groups(conflict,[a]);self.assertNotIn(1,again['proposals'])

class TestEarlierDefaults(unittest.TestCase):
 def test_group_overrides_line_and_preserves_satellite_provenance(self):
  c={1:{'total':1,'in_scope':1},2:{'total':1,'in_scope':1},3:{'total':1,'in_scope':1}}
  result={'proposals':{1:{'code':22,'basis':'whole_component_line_side'},2:{'code':18,'basis':'source_anchored_nearest_main_island'},3:{'code':22,'basis':'source_anchored_nearest_main_island'}},'review':{},'satellites':{2:{'source':'x'},3:{'source':'y'}}}
  out=apply_groups(result,[{'group_id':'a','code':18,'components':c,'source':{'id':'a'}}])
  self.assertEqual(out['proposals'][1]['code'],18)
  self.assertEqual(out['proposals'][2]['basis'],'inferred_source_extent_group_convention');self.assertEqual(out['satellites'][2]['source'],'x')
  self.assertNotIn(3,out['proposals']);self.assertEqual(out['review'][3],'conflicting_group_and_anchor')
  self.assertEqual(out['regional_group_proposals'][3][0]['target_code'],18);self.assertEqual(out['satellites'][3]['source'],'y')
  self.assertEqual(out['group_anchor_conflicts'][3]['prior_satellite_proposal']['code'],22)
  self.assertEqual(out['group_anchor_conflicts'][3]['prior_satellite_evidence']['source'],'y')
  later=apply_groups(out,[{'group_id':'b','code':18,'components':{3:c[3]},'source':{'id':'b'}}])
  self.assertNotIn(3,later['proposals']);self.assertEqual(later['review'][3],'conflicting_group_and_anchor')
  self.assertEqual({x['group_id'] for x in later['regional_group_proposals'][3]},{'a','b'})

class TestConflictingGroupsOverDefaults(unittest.TestCase):
 def test_same_pass_conflict_removes_line_and_satellite(self):
  c={1:{'total':1,'in_scope':1},2:{'total':1,'in_scope':1}}
  result={'proposals':{1:{'code':18,'basis':'whole_component_line_side'},2:{'code':18,'basis':'source_anchored_nearest_main_island'}},'review':{},'satellites':{2:{'source':'named'}}}
  out=apply_groups(result,[{'group_id':'a','code':18,'components':c,'source':{}},{'group_id':'b','code':22,'components':c,'source':{}}])
  for r in (1,2):
   self.assertNotIn(r,out['proposals']);self.assertEqual(out['review'][r],'conflicting_regional_group_conventions')
   self.assertEqual({(x['group_id'],x['target_code']) for x in out['regional_group_proposals'][r]},{('a',18),('b',22)})
  self.assertEqual(out['satellites'][2]['source'],'named')
