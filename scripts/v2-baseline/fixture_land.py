"""Synthetic shared RLE and component fixtures, without distance code."""
import hashlib,json,subprocess,unittest
from pathlib import Path
import numpy as np

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
  builder=p/'provenance'/'builder';source=Path(__file__).parent.parent/'v7-land'/'build_components.cpp'
  subprocess.run(['g++','-std=c++17','-O2',str(source),'-o',str(builder)],check=True);cr=p/'provenance'/'cr';cu=p/'provenance'/'cu';subprocess.run([str(builder),'36','3',pr['path'],pu['path'],str(cr),str(cu)],check=True,capture_output=True)
  physical_report=p/'provenance'/'physical.json';physical_report.write_text(json.dumps({'status':'candidate-only','grid':grid,'output_sha256':{'rows.u32le':pr['sha256'],'runs.u32le':pu['sha256']}}))
  seed_report=p/'provenance'/'seed.json';seed_report.write_text(json.dumps({'schema':'direct-mainland-regions-research-v1','status':'local-research-not-approved-or-published','grid':{k:grid[k] for k in ('width','height','step')},'inputs':{'physical_component_rows_sha256':pin(cr)['sha256'],'physical_component_runs_sha256':pin(cu)['sha256']},'outputs':{'rows_sha256':sr['sha256'],'runs_sha256':su['sha256']}}))
  cfg={'schema':'simple-v2-land-v1','grid':grid,'physical_rows':pr,'physical_runs':pu,'mainland_rows':sr,'mainland_runs':su,'physical_report':pin(physical_report),'seed_provenance':pin(seed_report),'minimum_free_bytes':0};path=p/'config'/'cfg.json';path.write_text(json.dumps(cfg));return path,cfg
