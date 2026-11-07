"""The driver's post-write extent audit must distinguish positive and negative sources."""
import copy,hashlib,json,unittest
from pathlib import Path
from unittest.mock import patch
import apply_selected_mixed as driver
from test_mixed_driver import DriverTests,js

class NegativeExtentTests(unittest.TestCase):
 def claim(self):
  return {'method':'component_containment_excluding_source_v1','component_ids':[11],
   'source_features':[{'feature_id':'positive'},{'feature_id':'negative'}],
   'intersection':{'per_feature_root_inside_cells':[{'11':3,'12':1}]},
   'source_negative_intersection':{'per_feature_root_inside_cells':[{'12':1}]},
   'source_negative_filter':{'selected_roots':[11],'excluded_roots':[12],'selected_count':1,'excluded_count':1,'negative_roots_outside_positive':0},'containment':{'policy':'all-source-cell-centers-v1','stage':'positive_full_center_before_exclusion','selected_count':2,'selected_cells':4,'excluded_partial_components':[],'excluded_partial_count':0,'excluded_partial_cells':0}}
 def test_positive_and_negative_are_not_conflated(self):
  c=self.claim();features,counts=driver.positive_extent_features(c)
  self.assertEqual(features,[{'feature_id':'positive'}]);self.assertEqual(counts,[{'11':3,'12':1}])
 def test_selected_root_touching_negative_is_rejected(self):
  c=self.claim();c['source_negative_intersection']['per_feature_root_inside_cells'][0]['11']=1
  with self.assertRaisesRegex(ValueError,'partition mismatch'):driver.positive_extent_features(c)
 def test_wrong_filter_or_malformed_features_rejected(self):
  for mutation in ('wrong_selected','missing_negative','bad_excluded','duplicate_feature','omitted_root'):
   c=self.claim()
   if mutation=='wrong_selected':c['source_negative_filter']['selected_roots']=[12]
   if mutation=='missing_negative':c['source_negative_intersection']['per_feature_root_inside_cells']=[]
   if mutation=='bad_excluded':c['source_negative_filter']['excluded_roots']=[13]
   if mutation=='duplicate_feature':c['source_features'][1]['feature_id']='positive'
   if mutation=='omitted_root':c['intersection']['per_feature_root_inside_cells'][0]['13']=1;c['containment']['selected_count']=3;c['containment']['selected_cells']=5
   with self.subTest(mutation=mutation),self.assertRaises(ValueError):driver.positive_extent_features(c)
 def test_partial_positive_is_not_a_full_candidate(self):
  c=self.claim();c['intersection']['per_feature_root_inside_cells'][0]['13']=2;c['source_negative_intersection']['per_feature_root_inside_cells'][0]['13']=1;c['source_negative_filter']['negative_roots_outside_positive']=1;c['containment'].update(excluded_partial_components=[{'component_id_evidence_only':13,'inside_cells':2,'whole_cells':3}],excluded_partial_count=1,excluded_partial_cells=3)
  self.assertEqual(driver.positive_extent_features(c)[0],[{'feature_id':'positive'}])
  c['containment']['excluded_partial_components'][0]['inside_cells']=1
  with self.assertRaisesRegex(ValueError,'partial containment'):driver.positive_extent_features(c)
 def test_noncanonical_root_rejected(self):
  c=self.claim();c['intersection']['per_feature_root_inside_cells'][0]['011']=3
  with self.assertRaisesRegex(ValueError,'cell counts'):driver.positive_extent_features(c)
 def test_nonnegative_claim_still_checks_feature_count(self):
  c=self.claim();c['method']='component_intersection_v1'
  with self.assertRaisesRegex(ValueError,'polygon feature counts mismatch'):driver.positive_extent_features(c)

class NegativeExtentFullDriver(DriverTests):
 def test_real_postwrite_extent_audit_handles_negative_source(self):
  rp=Path(self.cfg['point_request']['path']);req=json.loads(rp.read_text());sp=Path(req['snapshot']['path']);snap=json.loads(sp.read_text());snap['affiliations'][1]['method']='component_containment_excluding_source_v1';req['snapshot']=js(sp,snap);self.cfg['point_request']=js(rp,req);self.point['snapshot_sha256']=req['snapshot']['sha256']
  for name in ('negative_component_filter','federal_register_rectangle'):self.cfg['code'][name]=hashlib.sha256((driver.HERE/(name+'.py')).read_bytes()).hexdigest()
  c=self.poly['claims'][0];c.update(NegativeExtentTests().claim());c['affiliation_id']='poly';c['entity_id']=3;c['entity_code']=20;c['source_features']=[{'feature_id':'f'},{'feature_id':'negative'}]
  with patch.object(driver.polygon_policy,'adapt',return_value={'schema':'stage3-polygon-decisions-v1','revision':'r','decisions':[],'source_pins':[]}):self.runv()
  r=json.loads((self.b/'out/report.json').read_text());entry=r['polygon_component_extents']['poly']['11'];self.assertEqual(entry['whole_component_cells'],3);self.assertEqual(entry['per_feature'],[{'feature_id':'f','inside_cells':3,'outside_cells':0}]);self.assertEqual(r['polygon_resolution']['claims'][0]['source_negative_filter']['excluded_roots'],[12])
