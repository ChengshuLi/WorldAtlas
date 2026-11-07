"""Ensure a valid archive cannot be mistaken for a consumed region segment."""
import copy
import unittest
from audit_selected_panama_region import require_panama_region_usage

class PanamaRegionUsage(unittest.TestCase):
 def setUp(self):
  self.segment = {'kind':'boundary','id':'panama_colombia_osm_admin_boundary','start':0,'end':5254,'reverse':False}
  self.trace = {'vertices':5254,'geometry_sha256':'a'*64}
  self.decision = {'segments':[copy.deepcopy(self.segment)]}
  self.report = {'input_trace':[{**self.segment,'geometry_sha256':'a'*64}]}
 def test_source_appears_in_selected_and_executed_segment(self):
  require_panama_region_usage(self.decision,self.trace,self.report)
 def test_rejects_boundary_selected_elsewhere(self):
  self.decision['segments'] = []
  with self.assertRaisesRegex(ValueError,'does not consume'):require_panama_region_usage(self.decision,self.trace,self.report)
 def test_rejects_partial_or_mismatched_execution(self):
  self.decision['segments'][0]['end'] = 2
  with self.assertRaisesRegex(ValueError,'does not consume'):require_panama_region_usage(self.decision,self.trace,self.report)
  self.decision['segments'][0]['end'] = 5254;self.report['input_trace'][0]['geometry_sha256']='b'*64
  with self.assertRaisesRegex(ValueError,'differs'):require_panama_region_usage(self.decision,self.trace,self.report)

if __name__=='__main__':unittest.main()
