#!/usr/bin/python3
"""Pinned local diagnostic only. Caller must independently verify tile/seed identity."""
import hashlib,json,os,re,shutil,sys,time
from decimal import Decimal, InvalidOperation
from pathlib import Path
import numpy as np, pyproj, scipy
import hints

NAMES={'physical_rows','physical_runs','component_rows','component_runs','seed_rows','seed_runs','representatives','tile_manifest','resolution_report','decision_snapshot','component_manifest'}

def need(v,msg):
 if not v: raise ValueError(msg)
def representative_byte_limit(tile_count):return tile_count*6*32*20
def read_bytes(path):
 return Path(path).read_bytes()
def digest(path,guard):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  while True:
   guard();b=f.read(1<<20)
   if not b:break
   h.update(b)
 return h.hexdigest()
def run(config_path,out_path):
 cp=Path(config_path).resolve();out=Path(out_path).resolve(); raw=read_bytes(cp);cfg=json.loads(raw)
 need(set(cfg)=={'schema','grid','codes','inputs','decision_revision','entity_revision','policy_id','policy_version','minimum_free_bytes'} and cfg['schema']=='source-only-hints-diagnostic-request-v1','bad request')
 inp=cfg['inputs'];need(isinstance(inp,dict) and set(inp)==NAMES,'bad inputs')
 paths={};
 for k,v in inp.items():
  need(isinstance(v,dict) and set(v)=={'path','sha256'} and isinstance(v['sha256'],str) and len(v['sha256'])==64,'bad pin');paths[k]=Path(v['path']).resolve()
 need(out.parent.is_dir() and not out.exists(),'output must be fresh')
 for p in [cp,*paths.values(),Path(__file__).resolve(),Path(hints.__file__).resolve()]: need(not p.is_relative_to(out) and not out.is_relative_to(p.parent),'output overlaps input/code directory')
 disk=cfg['minimum_free_bytes'];need(type(disk)==int and disk>0,'invalid disk reserve')
 def guard():
  if shutil.disk_usage(out.parent).free<disk:raise RuntimeError('disk reserve reached')
 guard(); start=time.monotonic(); code_before={p.name:digest(p,guard) for p in (Path(hints.__file__),Path(__file__))}
 for k in sorted(paths):need(paths[k].is_file() and digest(paths[k],guard)==inp[k]['sha256'],'input hash mismatch: '+k)
 grid=cfg['grid'];need(isinstance(grid,dict) and set(grid)=={'width','height','step','west','north'} and type(grid['width']) is int and 1<=grid['width']<=0xffffffff and type(grid['height']) is int and 1<=grid['height']<=0xffffffff and grid['west']==-180,'bad grid')
 snapshot_bytes=read_bytes(paths['decision_snapshot']);snap=json.loads(snapshot_bytes)
 need(snap.get('schema')=='worldatlas-geography-decision-draft-evidence-v1' and snap.get('source')=='neon-export','invalid snapshot')
 dr=snap.get('decision_revision',{});er=snap.get('entity_revision',{})
 need(dr.get('id')==cfg['decision_revision'] and er.get('id')==cfg['entity_revision'] and dr.get('entity_revision')==er.get('id') and dr.get('status')=='draft' and er.get('status')=='draft','revision mismatch')
 policies=snap.get('distance_policies',[]);need(isinstance(policies,list),'missing distance policies')
 need(isinstance(cfg['policy_id'],str) and bool(cfg['policy_id']) and isinstance(cfg['policy_version'],str) and bool(cfg['policy_version']),'invalid requested policy identity')
 policies=[p for p in policies if isinstance(p,dict) and p.get('policy_id')==cfg['policy_id'] and p.get('version')==cfg['policy_version'] and p.get('execution_status')=='selected_for_research']
 need(len(policies)==1,'missing/ambiguous selected WGS84 policy');metric=policies[0];need(metric.get('decision_revision')==cfg['decision_revision'],'policy revision mismatch');need(isinstance(metric.get('policy_id'),str) and bool(metric['policy_id']) and isinstance(metric.get('version'),str) and bool(metric['version']),'invalid policy identity')
 try: valid=metric.get('algorithm')=='wgs84_ellipsoidal_geodesic_inverse' and metric.get('units')=='metres' and Decimal(str(metric.get('semi_major_axis_m')))==Decimal('6378137') and Decimal(str(metric.get('inverse_flattening')))==Decimal('298.257223563')
 except InvalidOperation:valid=False
 need(valid,'unsupported WGS84 policy')
 bindings=snap.get('category_bindings',[]);need(isinstance(bindings,list),'missing categories');land=[b.get('code') for b in bindings if isinstance(b,dict) and b.get('physical_class')=='land']
 need(len(land)==len(set(land)) and set(land)==set(cfg['codes']),'land categories mismatch')
 report_bytes=read_bytes(paths['resolution_report']);report=json.loads(report_bytes)
 expected={k:inp[k]['sha256'] for k in ('physical_rows','physical_runs','component_rows','component_runs')}
 seed=hints.seed_roots_from_resolution(report,grid=grid,input_sha256=expected,snapshot_sha256=inp['decision_snapshot']['sha256'],component_manifest_sha256=inp['component_manifest']['sha256'],decision_revision=cfg['decision_revision'],entity_revision=cfg['entity_revision'])
 # Count bounded tile manifest records. The caller must still authenticate the
 # manifest against the current seed raster before accepting these hints.
 manifest=read_bytes(paths['tile_manifest']); lines=manifest.splitlines();need(0<len(lines)<=((grid['width']+1023)//1024)*((grid['height']+1023)//1024),'bad tile count')
 seen=set()
 for line in lines:
  try:
   fields=line.decode('ascii').split();need(len(fields)==5,'bad tile manifest');ty,tx,n,mask=map(int,fields[:4]);sha=fields[4]
  except (UnicodeError,ValueError):raise ValueError('bad tile manifest') from None
  tw=min(1024,grid['width']-tx*1024);th=min(1024,grid['height']-ty*1024)
  need(ty>=0 and tx>=0 and tw>0 and th>0 and 1<=n<=tw*th and 0<mask<64 and re.fullmatch('[0-9a-f]{64}',sha) is not None and (ty,tx) not in seen,'invalid tile manifest entry');seen.add((ty,tx))
 rep_path=paths['representatives']; rep_max=representative_byte_limit(len(lines)); size=rep_path.stat().st_size
 need(size%20==0 and 0<size<=rep_max,'bad representative size')
 guard()
 rep_bytes=read_bytes(rep_path);need(len(rep_bytes)==size,'representative size changed');reps=np.frombuffer(rep_bytes,dtype='<u4').reshape(-1,5)
 os.mkdir(out,0o700);fd=os.open(out.parent,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
 db=out/'inventory.sqlite';count=hints.inventory(paths['component_rows'],paths['component_runs'],seed,grid['width'],grid['height'],db,guard)
 rh=hashlib.sha256();hh=hashlib.sha256();n=0
 with open(out/'roots.u32le','xb') as rf,open(out/'hints.u8','xb') as hf:
  for roots,codes in hints.choose_hints(db,reps,grid['width'],grid['height'],grid['step'],grid['north'],cfg['codes'],guard=guard):
   a=roots.astype('<u4',copy=False).tobytes();b=codes.astype('u1',copy=False).tobytes();rf.write(a);hf.write(b);rh.update(a);hh.update(b);n+=len(roots)
  rf.flush();hf.flush();os.fsync(rf.fileno());os.fsync(hf.fileno())
 need(n==count,'count mismatch')
 for k in sorted(paths):need(digest(paths[k],guard)==inp[k]['sha256'],'input changed: '+k)
 need(read_bytes(cp)==raw,'request changed');need(all(digest(p,guard)==code_before[p.name] for p in (Path(hints.__file__),Path(__file__))),'code changed');guard()
 result={'schema':'source-only-hints-diagnostic-report-v1','status':'diagnostic-not-independently-authenticated','publishable':False,'request_sha256':hashlib.sha256(raw).hexdigest(),'inputs_sha256':{k:inp[k]['sha256'] for k in sorted(inp)},'grid':grid,'decision_revision':cfg['decision_revision'],'entity_revision':cfg['entity_revision'],'distance_policy':metric,'seed_roots':seed,'root_count':n,'roots_sha256':rh.hexdigest(),'hints_sha256':hh.hexdigest(),'code_sha256':code_before,'runtime':{'numpy':np.__version__,'scipy':scipy.__version__,'pyproj':pyproj.__version__,'proj':pyproj.proj_version_str},'elapsed_seconds':time.monotonic()-start,'limitations':'Current representatives and tile manifest must be independently proven to derive from current seed; physical coverage, witness authenticity, and final certificate/exact verification are not performed by this diagnostic. Equidistant KD-tree witnesses can change hint bytes across implementations; hints are never labels. No historic checkpoint is read.'}
 # Sync the data directory before publishing the marker; never replace a marker.
 fd=os.open(out,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd);guard()
 tmp=out/'report.pending';final=out/'report.json';linked=False
 try:
  with open(tmp,'x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
  guard();os.link(tmp,final);linked=True
  fd=os.open(out,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
  os.unlink(tmp);fd=os.open(out,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
 except Exception as e:
  if linked or final.exists(): raise RuntimeError('completion marker may exist; outcome requires inspection') from e
  raise
 return result
if __name__=='__main__':
 if len(sys.argv)!=3:raise SystemExit('usage: run_diagnostic.py REQUEST.json NEW_OUTPUT_DIRECTORY')
 print(json.dumps(run(sys.argv[1],sys.argv[2]),sort_keys=True))
