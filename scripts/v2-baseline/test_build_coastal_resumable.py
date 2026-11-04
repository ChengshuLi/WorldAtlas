import json,tempfile,unittest
from pathlib import Path
import build_coastal_resumable as run
from test_coastal_band import make_rle,pin

class ResumableTest(unittest.TestCase):
 def test_pause_resume_rechecks_completed_tile(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);i=root/'input';i.mkdir();(i/'p').mkdir();(i/'l').mkdir();grid={'width':360,'height':2,'west':-180,'north':90,'step':1}
   pr,pu=make_rle(i/'p',360,2,[(1,10,17)],False);lr,lu=make_rle(i/'l',360,2,[(1,10,17)],True)
   land=i/'land.json';land.write_text(json.dumps({'schema':'simple-v2-land-report-v1','status':'research-not-published','grid':grid,'inputs':{'physical_rows':pr,'physical_runs':pu},'output_rows_sha256':lr['sha256'],'output_runs_sha256':lu['sha256']}))
   cfg={'schema':'simple-v2-coastal-resumable-v1','grid':grid,'physical_rows':pr,'physical_runs':pu,'land_rows':lr,'land_runs':lu,'land_report':pin(land),'tile_width':180,'tile_height':1,'pad_degrees':1,'minimum_free_bytes':0}
   config=i/'config.json';config.write_text(json.dumps(cfg));out=root/'out'
   part=run.build(config,out,1);self.assertEqual(part['status'],'paused-research-partial');self.assertEqual(part['completed_tiles'],1)
   span=out/'tiles/000000/attempt-0001/coastal-spans.jsonl.gz';original=span.read_bytes();span.write_bytes(original+b'tamper')
   with self.assertRaisesRegex(ValueError,'saved tile failed verification'):run.build(config,out,1)
   span.write_bytes(original);whole=run.build(config,out);self.assertTrue(whole['tile_cores_cover_grid']);self.assertEqual(whole['tile_count'],4)
   with self.assertRaisesRegex(ValueError,'already complete'):run.build(config,out)
if __name__=='__main__':unittest.main()
