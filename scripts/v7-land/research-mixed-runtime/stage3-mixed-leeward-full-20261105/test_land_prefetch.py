import unittest
from unittest.mock import patch
import polygon_resolution as p

def f(n,h='a',source='s'):
 return {'extractor_version':'osm-split-land-archive-v1','source_format':'osm-split-land-shapefile','source_id':source,'source_version':'v','source_feature_id':str(n),'geometry_sha256':h}
class TestLandPrefetch(unittest.TestCase):
 def test_batches_and_deduplicates_across_decisions(self):
  a,b=f(1),f(2); decisions=[{'features':[a,b]},{'features':[dict(a)]}]
  def extract(features,src):return [({'fid':x['source_feature_id']},{'hash':x['geometry_sha256']}) for x in features]
  with patch.object(p.polygon_loader,'extract_land_many',side_effect=extract) as m:
   out=p.prefetch_land_features(decisions,{('s','v'):{'source_id':'s'}})
  self.assertEqual(m.call_count,1);self.assertEqual(len(m.call_args.args[0]),2);self.assertEqual(out[(('s','v'),'1')][0],{'fid':'1'})
 def test_same_fid_different_hash_fails(self):
  with self.assertRaisesRegex(ValueError,'conflicting geometry pins'):
   p.prefetch_land_features([{'features':[f(1)]},{'features':[f(1,'b')]}],{('s','v'):{}})
 def test_separate_sources_and_non_archive(self):
  fake={'extractor_version':'other','source_id':'s','source_version':'v','source_feature_id':'3'}
  with patch.object(p.polygon_loader,'extract_land_many',side_effect=lambda fs,s:[({}, {}) for _ in fs]) as m:
   out=p.prefetch_land_features([{'features':[f(1),f(1,source='t'),fake]}],{('s','v'):{},('t','v'):{}})
  self.assertEqual(m.call_count,2);self.assertEqual(len(out),2)
 def test_oversized_set_batches(self):
  features=[f(i) for i in range(1001)]
  with patch.object(p.polygon_loader,'extract_land_many',side_effect=lambda fs,s:[({}, {}) for _ in fs]) as m:
   out=p.prefetch_land_features([{'features':features}],{('s','v'):{}})
  self.assertEqual([len(x.args[0]) for x in m.call_args_list],[1000,1]);self.assertEqual(len(out),1001)
if __name__=='__main__':unittest.main()
