import json,tempfile,unittest
from pathlib import Path
import aggregate_coastal_comparisons as agg
import coastal_band,compare_coastal
import test_coastal_band as fixture
import numpy as np
from test_build_land import pin
class AggregateTest(unittest.TestCase):
 def fixture(self,root):
  for name in ('inputs','tile1','tile2','comparisons','config'):(root/name).mkdir()
  files={}
  for name in ('physical_rows','physical_runs','land_rows','land_runs','land_report','reference_rows','reference_runs'):
   p=root/'inputs'/name;p.write_bytes(name.encode());files[name]=pin(p)
  grid={'width':4,'height':2,'west':-180,'north':90,'step':90};tiles=[]
  for i,box in enumerate(([0,2,0,2],[2,4,0,2]),1):
   sp=root/f'tile{i}'/'spans.gz';sp.write_bytes(b'synthetic-pinned-by-comparator');report=root/f'tile{i}'/'report.json'
   tile={'schema':'simple-v2-coastal-tile-report-v1','status':'research-partial-not-published','grid':grid,'core':box,'span_file':{'path':'spans.gz','sha256':pin(sp)['sha256']},'inputs':{k:files[k] for k in ('physical_rows','physical_runs','land_rows','land_runs','land_report')},'code_sha256':{k:'a'*64 for k in ('coastal_band','core','shore','geometry','grid_io','output_io')},'method':'12 nautical miles inclusive; spherical distance to physical-grid land/water edge; lowest continent code wins ties within 0.00001 metres','assigned_cells':1};report.write_text(json.dumps(tile))
   comp=root/'comparisons'/f'{i}.json';counts={k:0 for k in agg.COUNT_KEYS};counts['matched_continental_water']=1
   c={'schema':'simple-v2-coastal-comparison-report-v1','status':'research-validation-only','grid':grid,'core':box,'tile_report_sha256':pin(report)['sha256'],'inputs':{'schema':'simple-v2-coastal-comparison-v1','tile_report':pin(report),'reference_rows':files['reference_rows'],'reference_runs':files['reference_runs']},'code_sha256':{k:'b'*64 for k in ('compare','band_io','grid_io','output_io','shore','core')},'candidate_band_cells':1,'counts':counts};comp.write_text(json.dumps(c));tiles.append(pin(comp))
  cfg={'schema':'simple-v2-coastal-comparisons-v1','grid':grid,'comparisons':tiles};path=root/'config'/'aggregation.json';path.write_text(json.dumps(cfg));return path,cfg
 def test_full_coverage_and_gap_rejection(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);path,cfg=self.fixture(root);r=agg.aggregate(path,root/'report.json');self.assertEqual(r['candidate_band_cells'],2);self.assertEqual(r['counts']['matched_continental_water'],2)
   cfg['comparisons'].pop();path.write_text(json.dumps(cfg))
   with self.assertRaisesRegex(ValueError,'coverage gap'):agg.aggregate(path,root/'bad.json')
 def test_real_tile_and_comparison_pipeline(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td)
   for name in ('physical','land','reference','config','tile-config','compare-config','comp1','comp2','agg-config','final'):(root/name).mkdir()
   grid={'width':4,'height':2,'west':-180,'north':90,'step':90};pr,pu=fixture.make_rle(root/'physical',4,2,[(0,0,17)],False);lr,lu=fixture.make_rle(root/'land',4,2,[(0,0,17)],True)
   land_report=root/'land'/'report.json';land_report.write_text(json.dumps({'schema':'simple-v2-land-report-v1','status':'research-not-published','grid':grid,'inputs':{'physical_rows':pr,'physical_runs':pu},'output_rows_sha256':lr['sha256'],'output_runs_sha256':lu['sha256']}))
   rr=root/'reference'/'rows';ru=root/'reference'/'runs';np.asarray([0,2,3],dtype='<u4').tofile(rr);np.asarray([(1,17),(4,7),(4,7)],dtype='<u4').tofile(ru);comparisons=[]
   for i,box in enumerate(([0,2,0,2],[2,4,0,2]),1):
    c={'schema':'simple-v2-coastal-band-v1','grid':grid,'physical_rows':pr,'physical_runs':pu,'land_rows':lr,'land_runs':lu,'land_report':pin(land_report),'core':box,'pad_degrees':180,'minimum_free_bytes':0};cp=root/'tile-config'/f'{i}.json';cp.write_text(json.dumps(c));tdir=root/f'tile{i}';coastal_band.build(cp,tdir)
    cc={'schema':'simple-v2-coastal-comparison-v1','tile_report':pin(tdir/'report.json'),'reference_rows':pin(rr),'reference_runs':pin(ru)};ccp=root/'compare-config'/f'{i}.json';ccp.write_text(json.dumps(cc));rp=root/f'comp{i}'/'report.json';compare_coastal.compare(ccp,rp);comparisons.append(pin(rp))
   ac={'schema':'simple-v2-coastal-comparisons-v1','grid':grid,'comparisons':comparisons};ap=root/'agg-config'/'config.json';ap.write_text(json.dumps(ac));report=agg.aggregate(ap,root/'final'/'report.json');self.assertEqual(report['comparison_count'],2);self.assertEqual(report['candidate_band_cells'],0)
 def test_tampered_tile_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);path,_=self.fixture(root);(root/'tile1'/'spans.gz').write_bytes(b'tampered')
   with self.assertRaisesRegex(ValueError,'hash mismatch'):agg.aggregate(path,root/'bad.json')
if __name__=='__main__':unittest.main()
