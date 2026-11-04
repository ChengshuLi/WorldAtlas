import hashlib,json,subprocess,tempfile,unittest
from pathlib import Path
import numpy as np
import build_land
import build_seed
import build_components

def pin(p):return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def rle(grid,path):
 off=[0]; runs=[]
 for row in grid:
  last=row[0]
  for i,v in enumerate(row[1:],1):
   if v!=last:runs.append((i,last));last=v
  runs.append((len(row),last));off.append(len(runs))
 o=path/'rows';r=path/'runs';np.array(off,dtype='<u4').tofile(o);np.array(runs,dtype='<u4').tofile(r);return pin(o),pin(r)
class TestBuild(unittest.TestCase):
 def fixture(self,p,partial=False):
  for name in ('phys','seed','provenance','config'): (p/name).mkdir()
  physical=np.ones((3,36),dtype=np.uint32);seed=np.zeros_like(physical)
  for code,x in enumerate([1,6,11,16,21,26],17):physical[1,x]=17;seed[1,x]=code
  physical[1 if partial else 2,2]=17
  pr,pu=rle(physical,p/'phys');sr,su=rle(seed,p/'seed');grid={'width':36,'height':3,'step':10,'west':-180,'north':30}
  builder=p/'provenance'/'builder';source=Path(build_land.__file__).parent.parent/'v7-land'/'build_components.cpp'
  subprocess.run(['g++','-std=c++17','-O2',str(source),'-o',str(builder)],check=True);cr=p/'provenance'/'cr';cu=p/'provenance'/'cu';subprocess.run([str(builder),'36','3',pr['path'],pu['path'],str(cr),str(cu)],check=True,capture_output=True)
  physical_report=p/'provenance'/'physical.json';physical_report.write_text(json.dumps({'status':'candidate-only','grid':grid,'output_sha256':{'rows.u32le':pr['sha256'],'runs.u32le':pu['sha256']}}))
  seed_report=p/'provenance'/'seed.json';seed_report.write_text(json.dumps({'schema':'direct-mainland-regions-research-v1','status':'local-research-not-approved-or-published','grid':{k:grid[k] for k in ('width','height','step')},'inputs':{'physical_component_rows_sha256':pin(cr)['sha256'],'physical_component_runs_sha256':pin(cu)['sha256']},'outputs':{'rows_sha256':sr['sha256'],'runs_sha256':su['sha256']}}))
  cfg={'schema':'simple-v2-land-v1','grid':grid,'physical_rows':pr,'physical_runs':pu,'mainland_rows':sr,'mainland_runs':su,'physical_report':pin(physical_report),'seed_provenance':pin(seed_report),'minimum_free_bytes':0};path=p/'config'/'cfg.json';path.write_text(json.dumps(cfg));return path,cfg
 def test_complete_and_separate_seed(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);cfg,_=self.fixture(p);result=build_land.build(cfg,p/'out');self.assertEqual(result['island_components'],1)
   rows=np.fromfile(p/'out/rows.u32le',dtype='<u4');runs=np.fromfile(p/'out/runs.u32le',dtype='<u4').reshape(-1,2)
   def at(y,x):
    rr=runs[rows[y]:rows[y+1]];return int(rr[np.searchsorted(rr[:,0],x,side='right'),1])
   self.assertEqual(at(2,2),17);self.assertEqual(at(1,26),22);self.assertEqual(at(0,0),0)
 def test_partial_seed_fails(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);cfg,_=self.fixture(p,True)
   with self.assertRaisesRegex(ValueError,'mainland seed missing'):build_land.build(cfg,p/'out')
   self.assertFalse((p/'out/report.json').exists())
 def test_actual_seed_builder_feeds_land(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);path,cfg=self.fixture(p);cr=p/'provenance'/'cr';cu=p/'provenance'/'cu';offset=np.fromfile(cr,dtype='<u4');runs=np.fromfile(cu,dtype='<u4').reshape(-1,3);row=runs[offset[1]:offset[2]];rules=[]
   for code,x in zip(range(17,23),(1,6,11,16,21,26)):
    hit=row[(row[:,0]<=x)&(x<row[:,1])];self.assertEqual(len(hit),1);rules.append({'component_id':int(hit[0,2]),'region_id':None,'inside_code':code,'outside_code':code})
   sc={'schema':'direct-region-seed-research-v1','grid':{**cfg['grid'],'crs':'EPSG:4326'},'component_rows':pin(cr),'component_runs':pin(cu),'regions':[],'rules':rules,'evidence':[],'strip_rows':2,'reserve_bytes':0};sp=p/'config'/'seed-config.json';sp.write_text(json.dumps(sc));seed_out=p/'seed-output';build_seed.build(sp,seed_out)
   component_config=p/'config'/'components.json';component_config.write_text(json.dumps({'schema':'simple-v2-components-v1','grid':cfg['grid'],'physical_rows':cfg['physical_rows'],'physical_runs':cfg['physical_runs'],'physical_report':cfg['physical_report'],'minimum_free_bytes':0}));component_out=p/'components';build_components.build(component_config,component_out)
   cfg['mainland_rows']=pin(seed_out/'rows.u32le');cfg['mainland_runs']=pin(seed_out/'runs.u32le');cfg['seed_provenance']=pin(seed_out/'report.json');cfg['component_manifest']=pin(component_out/'report.json');path.write_text(json.dumps(cfg));result=build_land.build(path,p/'out');self.assertEqual(result['island_components'],1);self.assertEqual(result['component_generation'],'pinned-component-manifest')
 def test_portable_seed_report_contract(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);path,cfg=self.fixture(p);seed=Path(cfg['seed_provenance']['path']);old=json.loads(seed.read_text())
   seed.write_text(json.dumps({'schema':'direct-region-seed-research-report-v1','status':'unreviewed-research-not-published','grid':cfg['grid'],'grid_crs':'EPSG:4326','component_rows_sha256':old['inputs']['physical_component_rows_sha256'],'component_runs_sha256':old['inputs']['physical_component_runs_sha256'],'output_rows_sha256':cfg['mainland_rows']['sha256'],'output_runs_sha256':cfg['mainland_runs']['sha256']}));cfg['seed_provenance']=pin(seed);path.write_text(json.dumps(cfg));result=build_land.build(path,p/'out');self.assertEqual(result['status'],'research-not-published')
 def test_same_run_components_match_independent_and_reject_tampering(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);path,cfg=self.fixture(p);component_config=p/'config'/'components.json';component_config.write_text(json.dumps({'schema':'simple-v2-components-v1','grid':cfg['grid'],'physical_rows':cfg['physical_rows'],'physical_runs':cfg['physical_runs'],'physical_report':cfg['physical_report'],'minimum_free_bytes':0}));component_out=p/'components';build_components.build(component_config,component_out)
   independent=build_land.build(path,p/'independent');cfg['component_manifest']=pin(component_out/'report.json');cfg['workers']=4;path.write_text(json.dumps(cfg));reused=build_land.build(path,p/'reused')
   self.assertEqual(reused['component_generation'],'pinned-component-manifest');self.assertEqual(independent['component_generation'],'independent-recompute');self.assertEqual((p/'independent/rows.u32le').read_bytes(),(p/'reused/rows.u32le').read_bytes());self.assertEqual((p/'independent/runs.u32le').read_bytes(),(p/'reused/runs.u32le').read_bytes())
   with (component_out/'runs.u32le').open('ab') as f:f.write(b'\0')
   with self.assertRaisesRegex(ValueError,'component artifact mismatch'):build_land.build(path,p/'bad')
   self.assertFalse((p/'bad').exists())
 def test_disk_guard_and_report_binding(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);path,cfg=self.fixture(p);cfg['minimum_free_bytes']=1<<60;path.write_text(json.dumps(cfg))
   with self.assertRaisesRegex(ValueError,'free disk below'):build_land.build(path,p/'out')
   self.assertFalse((p/'out').exists())
   cfg['minimum_free_bytes']=0;report=Path(cfg['physical_report']['path']);doc=json.loads(report.read_text());doc['output_sha256']['rows.u32le']='0'*64;report.write_text(json.dumps(doc));cfg['physical_report']=pin(report);path.write_text(json.dumps(cfg))
   with self.assertRaisesRegex(ValueError,'physical report mismatch'):build_land.build(path,p/'out')
   self.assertFalse((p/'out').exists())
if __name__=='__main__':unittest.main()
