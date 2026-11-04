import json,unittest
import numpy as np
import coastal_band,compare_coastal
import test_coastal_band as fixture_module

class CoastalComparison(unittest.TestCase):
 def test_tile_confusion_and_hash_guard(self):
  fixture=fixture_module.BandTest('runTest');fixture.setUp()
  try:
   cfg,_=fixture.fixture([(899,1800,17)]);tile=fixture.root/'tile';coastal_band.build(cfg,tile)
   ref=fixture.root/'reference';ref.mkdir();offset=[0];runs=[]
   for y in range(fixture.h):
    runs.extend([(1799,7),(1800,1),(1801,17),(1802,2),(1803,7),(1804,1),(fixture.w,7)] if y==899 else [(fixture.w,7)]);offset.append(len(runs))
   rows=ref/'rows';stream=ref/'runs';np.asarray(offset,dtype='<u4').tofile(rows);np.asarray(runs,dtype='<u4').tofile(stream)
   c={'schema':'simple-v2-coastal-comparison-v1','tile_report':fixture_module.pin(tile/'report.json'),'reference_rows':fixture_module.pin(rows),'reference_runs':fixture_module.pin(stream)};path=fixture.inputs/'compare.json';path.write_text(json.dumps(c));result=compare_coastal.compare(path,fixture.root/'comparison.json');counts=result['counts']
   self.assertEqual((result['candidate_band_cells'],counts['matched_continental_water'],counts['different_continent_water'],counts['candidate_band_reference_ocean'],counts['reference_band_missing_from_candidate']),(3,1,1,1,1))
   c['reference_runs']['sha256']='0'*64;path.write_text(json.dumps(c))
   with self.assertRaisesRegex(ValueError,'hash mismatch'):compare_coastal.compare(path,fixture.root/'bad.json')
  finally:fixture.tearDown()
if __name__=='__main__':unittest.main()
