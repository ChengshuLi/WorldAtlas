import json,unittest
from pathlib import Path
import coastal_band as fixed
import coastal_band_adaptive as adaptive
from test_coastal_band import BandTest

class AdaptiveTest(BandTest):
 def test_adaptive_equals_fixed_for_safe_equatorial_tile(self):
  cfg,_=self.fixture([(899,1800,17),(899,1802,18)])
  a=self.root/'adaptive';b=self.root/'fixed';ra=adaptive.build(cfg,a);rb=fixed.build(cfg,b)
  self.assertEqual(self.spans(a),self.spans(b));self.assertEqual(ra['assigned_cells'],rb['assigned_cells'])
 def test_polar_empty_tile_certifies_without_longitude_boundary(self):
  cfg,c=self.fixture([]);c['core']=[1700,1710,0,1];cfg.write_text(json.dumps(c))
  with self.assertRaisesRegex(ValueError,'crop cannot certify'):fixed.build(cfg,self.root/'fixed')
  r=adaptive.build(cfg,self.root/'adaptive');self.assertEqual(r['crop'][:2],(0,self.w));self.assertEqual(r['assigned_cells'],0)
 def test_high_latitude_result_matches_full_longitude(self):
  cfg,c=self.fixture([(49,1820,17)])
  c['core']=[1800,1802,49,50];cfg.write_text(json.dumps(c))
  with self.assertRaisesRegex(ValueError,'crop cannot certify'):fixed.build(cfg,self.root/'fixed')
  adaptive.build(cfg,self.root/'adaptive')
  c['pad_degrees']=180;cfg.write_text(json.dumps(c));fixed.build(cfg,self.root/'full')
  self.assertEqual(self.spans(self.root/'adaptive'),self.spans(self.root/'full'))
  self.assertTrue(self.spans(self.root/'adaptive'))
 def test_crop_halo_expands_with_latitude(self):
  a=adaptive.adaptive_crop([100,110,1000,1010],3600,1800,.1,1)
  b=adaptive.adaptive_crop([100,110,50,60],3600,1800,.1,1)
  c=adaptive.adaptive_crop([100,110,0,1],3600,1800,.1,1)
  self.assertGreater(b[1]-b[0],a[1]-a[0]);self.assertEqual(c[:2],(0,3600))
if __name__=='__main__':unittest.main()
