import unittest
from overlay import overlay_row,validate_component_claims
C=lambda aid,code,entries=None:{'affiliation_id':aid,'entry_ids':entries or [aid+'-entry'],'code':code}
class OverlayTests(unittest.TestCase):
 def runrow(self,component=None,regions=None,physical=None,baseline=None,components=None):
  stats={};changes=[];physical=physical or [(0,2,1),(2,8,17),(8,10,1)];baseline=baseline or [(2,0),(8,18),(10,0)];components=components or [(2,5,10),(5,8,11)];claims=validate_component_claims(component or {})
  result=overlay_row(10,physical,baseline,components,claims,regions or [],stats,lambda *x:changes.append(x));return result,stats,changes
 def test_whole_component(self):
  out,stats,trace=self.runrow({10:[C('a',19)]});self.assertEqual(out,[(2,0),(5,19),(8,18),(10,0)]);self.assertEqual(stats['a']['changed_cells'],3);self.assertEqual(trace,[(2,5,18,19,('a',),('a-entry',))])
 def test_region_clips_water_and_roots(self):
  out,stats,trace=self.runrow(regions=[{'claim':C('r',20),'roots':{10},'spans':[(1,7)]}]);self.assertEqual(out,[(2,0),(5,20),(8,18),(10,0)]);self.assertEqual(stats['r']['applied_cells'],3);self.assertEqual(trace[0][:4],(2,5,18,20))
 def test_mixed_same_target_traces_both(self):
  out,stats,trace=self.runrow({10:[C('a',19,['e1','e2'])]},[{'claim':C('b',19,['e2','e3']),'roots':{10},'spans':[(3,5)]}]);self.assertEqual(out,[(2,0),(5,19),(8,18),(10,0)]);self.assertEqual(trace[1][4:],(('a','b'),('e1','e2','e3')));self.assertEqual(stats['a']['changed_cells'],3);self.assertEqual(stats['b']['changed_cells'],2)
 def test_conflict_fails_closed(self):
  with self.assertRaisesRegex(ValueError,'conflicting'):self.runrow({10:[C('a',19)]},[{'claim':C('b',20),'roots':{10},'spans':[(3,5)]}])
 def test_noop_tracks_without_changed_span(self):
  out,stats,trace=self.runrow({10:[C('a',18)]});self.assertEqual(stats['a']['applied_cells'],3);self.assertEqual(stats['a']['changed_cells'],0);self.assertFalse(trace)
 def test_unassigned_water_preserved(self):
  out,_,_=self.runrow(regions=[{'claim':C('r',19),'roots':{10,11},'spans':[(0,10)]}]);self.assertEqual(out[0],(2,0));self.assertEqual(out[-1],(10,0))
 def test_bad_component_coverage(self):
  with self.assertRaisesRegex(ValueError,'component'):self.runrow(components=[(2,5,10),(6,8,11)])
 def test_physical_water_assignment_rejected(self):
  with self.assertRaisesRegex(ValueError,'physical water'):self.runrow(baseline=[(2,17),(8,18),(10,0)])
 def test_overlapping_region_spans_rejected(self):
  with self.assertRaisesRegex(ValueError,'region row spans'):self.runrow(regions=[{'claim':C('r',19),'roots':{10},'spans':[(2,5),(4,6)]}])
 def test_unordered_or_duplicate_entry_links_rejected(self):
  with self.assertRaisesRegex(ValueError,'claim'):validate_component_claims({10:[C('a',19,['z','a'])]})
 def test_duplicate_affiliation_disagreement_rejected(self):
  with self.assertRaisesRegex(ValueError,'inconsistent duplicate'):self.runrow({10:[C('a',19)]},[{'claim':C('a',19,['other']),'roots':{10},'spans':[(2,5)]}])
if __name__=='__main__':unittest.main()
