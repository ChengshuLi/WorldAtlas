import gzip,hashlib,json,subprocess,tempfile,unittest
from pathlib import Path
import numpy as np
import coastal_band as band
import build_land

def pin(path):return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
def make_rle(path,w,h,land_cells,land_grid):
 offsets=[0];runs=[]
 for y in range(h):
  positions={x:code for yy,x,code in land_cells if yy==y};last=None
  for x in range(w):
   value=positions.get(x,0 if land_grid else 1)
   if last is not None and value!=last:runs.append((x,last))
   last=value
  runs.append((w,last));offsets.append(len(runs))
 rows=path/'rows';stream=path/'runs';np.array(offsets,dtype='<u4').tofile(rows);np.array(runs,dtype='<u4').tofile(stream);return pin(rows),pin(stream)
class BandTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.inputs=self.root/'inputs';self.inputs.mkdir();(self.inputs/'p').mkdir();(self.inputs/'l').mkdir()
  self.w=3600;self.h=902;self.grid={'width':self.w,'height':self.h,'west':-180,'north':90,'step':.1}
 def tearDown(self):self.tmp.cleanup()
 def fixture(self,cells):
  pp=[(y,x,17) for y,x,_ in cells];pr,pu=make_rle(self.inputs/'p',self.w,self.h,pp,False);lr,lu=make_rle(self.inputs/'l',self.w,self.h,cells,True)
  report=self.inputs/'land-report.json';report.write_text(json.dumps({'schema':'simple-v2-land-report-v1','status':'research-not-published','grid':self.grid,'inputs':{'physical_rows':pr,'physical_runs':pu},'output_rows_sha256':lr['sha256'],'output_runs_sha256':lu['sha256']}))
  cfg={'schema':'simple-v2-coastal-band-v1','grid':self.grid,'physical_rows':pr,'physical_runs':pu,'land_rows':lr,'land_runs':lu,'land_report':pin(report),'core':[1799,1805,899,900],'pad_degrees':1.0,'max_shore_segments':100,'chunk':2,'minimum_free_bytes':0}
  path=self.inputs/'config.json';path.write_text(json.dumps(cfg));return path,cfg
 def spans(self,out):
  with gzip.open(out/'coastal-spans.jsonl.gz','rt') as f:return [x for row in f for x in json.loads(row)['spans']]
 def test_twelve_nm_band_and_open_water(self):
  cfg,_=self.fixture([(899,1800,17)]);out=self.root/'out';result=band.build(cfg,out);spans=self.spans(out)
  self.assertEqual([(x['start'],x['end'],x['code']) for x in spans],[(1799,1800,1),(1801,1803,1)])
  self.assertEqual(result['assigned_cells'],3);self.assertEqual(result['unassigned_water_cells'],2);self.assertEqual(result['status'],'research-partial-not-published')
 def test_equal_distance_uses_lowest_code(self):
  cfg,_=self.fixture([(899,1800,17),(899,1802,18)]);out=self.root/'out';band.build(cfg,out)
  spans=self.spans(out);self.assertTrue(any(s['start']<=1801<s['end'] and s['code']==1 for s in spans))
 def test_land_builder_output_feeds_coast(self):
  cells=[(899,x,code) for x,code in zip((1790,1793,1796,1800,1803,1806),range(17,23))]
  pr,pu=make_rle(self.inputs/'p',self.w,self.h,[(y,x,17) for y,x,_ in cells],False);sr,su=make_rle(self.inputs/'l',self.w,self.h,cells,True)
  prov=self.root/'provenance';prov.mkdir();builder=prov/'builder';source=Path(build_land.__file__).parent.parent/'v7-land'/'build_components.cpp';subprocess.run(['g++','-std=c++17','-O2',str(source),'-o',str(builder)],check=True)
  cr,cu=prov/'cr',prov/'cu';subprocess.run([str(builder),str(self.w),str(self.h),pr['path'],pu['path'],str(cr),str(cu)],check=True,capture_output=True)
  physical_report=prov/'physical.json';physical_report.write_text(json.dumps({'status':'candidate-only','grid':self.grid,'output_sha256':{'rows.u32le':pr['sha256'],'runs.u32le':pu['sha256']}}))
  seed_report=prov/'seed.json';seed_report.write_text(json.dumps({'schema':'direct-mainland-regions-research-v1','status':'local-research-not-approved-or-published','grid':{k:self.grid[k] for k in ('width','height','step')},'inputs':{'physical_component_rows_sha256':pin(cr)['sha256'],'physical_component_runs_sha256':pin(cu)['sha256']},'outputs':{'rows_sha256':sr['sha256'],'runs_sha256':su['sha256']}}))
  lc=self.inputs/'land-config.json';lc.write_text(json.dumps({'schema':'simple-v2-land-v1','grid':self.grid,'physical_rows':pr,'physical_runs':pu,'mainland_rows':sr,'mainland_runs':su,'physical_report':pin(physical_report),'seed_provenance':pin(seed_report),'minimum_free_bytes':0}))
  land_out=self.root/'land';build_land.build(lc,land_out)
  cfg={'schema':'simple-v2-coastal-band-v1','grid':self.grid,'physical_rows':pr,'physical_runs':pu,'land_rows':pin(land_out/'rows.u32le'),'land_runs':pin(land_out/'runs.u32le'),'land_report':pin(land_out/'report.json'),'core':[1799,1805,899,900],'pad_degrees':1,'minimum_free_bytes':0};cp=self.inputs/'coast-config.json';cp.write_text(json.dumps(cfg))
  result=band.build(cp,self.root/'coast');self.assertGreater(result['assigned_cells'],0);self.assertEqual(result['inputs']['land_report'],pin(land_out/'report.json'))
 def test_free_space_guard(self):
  cfg,c=self.fixture([(899,1800,17)]);c['minimum_free_bytes']=1<<60;cfg.write_text(json.dumps(c))
  with self.assertRaisesRegex(ValueError,'free disk below'):band.build(cfg,self.root/'out')
  self.assertFalse((self.root/'out').exists())
 def test_tampered_report_and_unverified_tile_rejected(self):
  cfg,c=self.fixture([(899,1800,17)]);c['land_report']['sha256']='0'*64;cfg.write_text(json.dumps(c))
  with self.assertRaisesRegex(ValueError,'hash mismatch'):band.build(cfg,self.root/'out')
  self.assertFalse((self.root/'out').exists())
if __name__=='__main__':unittest.main()
