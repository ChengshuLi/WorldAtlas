import json,tempfile,unittest
from pathlib import Path
import numpy as np
import compare_land
from test_build_land import pin,rle
class ComparisonTest(unittest.TestCase):
 def test_runwise_confusion_and_tampering(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   for name in ('candidate','reference','config'):(root/name).mkdir()
   crows,cruns=rle(np.array([[17,18,0,0,19]],dtype=np.uint32),root/'candidate');rrows,rruns=rle(np.array([[17,19,1,20,7]],dtype=np.uint32),root/'reference')
   grid={'width':5,'height':1,'west':-180,'north':90,'step':72};report=root/'candidate'/'report.json';report.write_text(json.dumps({'schema':'simple-v2-land-report-v1','status':'research-not-published','grid':grid,'output_rows_sha256':crows['sha256'],'output_runs_sha256':cruns['sha256']}))
   cfg={'schema':'simple-v2-land-comparison-v1','grid':grid,'candidate_rows':crows,'candidate_runs':cruns,'candidate_report':pin(report),'reference_rows':rrows,'reference_runs':rruns};path=root/'config'/'config.json';path.write_text(json.dumps(cfg))
   got=compare_land.compare(path,root/'result.json');self.assertEqual((got['both_land_cells'],got['matching_land_cells'],got['different_continent_land_cells'],got['candidate_land_reference_water'],got['candidate_water_reference_land']),(2,1,1,1,1));self.assertEqual(got['confusion_reference_to_candidate']['19']['18'],1)
   cfg['reference_runs']['sha256']='0'*64;path.write_text(json.dumps(cfg))
   with self.assertRaisesRegex(ValueError,'hash mismatch'):compare_land.compare(path,root/'bad.json')
   self.assertFalse((root/'bad.json').exists())
if __name__=='__main__':unittest.main()
