#!/usr/bin/env /usr/bin/python3
"""Fresh accepted-physical connected components, guarded and data-only."""
import argparse,hashlib,json,os,shutil,subprocess,sys,time,uuid
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'stage2-geodesic-20261104'))
import verify_inputs,atomic_move
from write_land_stream import _Rows,_full,_components,PAIR,TRIPLE
REVIEWED_SOURCE_SHA256='2f4df94c6ca50ea66f43092a174962ce4fdd5e5c3137f55ca4f335964894515e'
def need(v,msg):
 if not v:raise ValueError(msg)
def sync_dir(path):
 fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
def require_guardian():
 parent=os.getppid();need(parent==os.getpgrp(),'monitored guardian required')
 try:args=Path(f'/proc/{parent}/cmdline').read_bytes().split(b'\0');valid=len(args)>=3 and Path(os.fsdecode(args[1])).resolve()==(HERE/'guardian.py').resolve()
 except (OSError,ValueError):valid=False
 need(valid and os.getppid()==parent,'monitored guardian required')
def pin(spec,guard):
 need(isinstance(spec,dict) and set(spec)=={'path','sha256'} and isinstance(spec['sha256'],str) and len(spec['sha256'])==64,'invalid input pin');p=Path(spec['path']).resolve(strict=True);need(p.is_file() and verify_inputs.sha_file(p,guard)==spec['sha256'],'input hash mismatch');return p
def require_same_filesystem(work_parent,output_parent):
 need(os.stat(work_parent).st_dev==os.stat(output_parent).st_dev,'work and output must share a filesystem')
def require_disk_headroom(directory,physical_runs,physical_rows,reserve):
 size=Path(physical_runs).stat().st_size;need(size%8==0,'misaligned physical run stream')
 # At most one component triple for each input physical run, plus rows and
 # conservative compiler/metadata allowance. Keep the configured reserve free.
 upper=(size//8)*12+Path(physical_rows).stat().st_size+64*1024**2
 need(shutil.disk_usage(directory).free>=reserve+upper,'insufficient component-output disk headroom')
 return upper
def coverage(pr,ps,cr,cs,w,h,guard):
 rows=[];land=runs=0
 try:
  rows=[_Rows(pr,ps,h,PAIR),_Rows(cr,cs,h,TRIPLE)]
  for y in range(h):
   if y%128==0:guard()
   p=iter(_full(rows[0].next(),w,{1,17},'physical'));c=iter(_components(rows[1].next(),w));a=next(p);b=next(c);x=0
   while x<w:
    end=min(a[1],b[1]);need((a[2]==17)==(b[2] is not None),'physical/component coverage mismatch');land+=(end-x) if a[2]==17 else 0;x=end
    if a[1]==x:a=next(p,None)
    if b[1]==x:b=next(c,None)
   need(a is None and b is None,'component row overrun')
  for r in rows:r.finish()
  return land
 finally:
  for r in rows:r.close()
def run(config_path,work_dir,output_dir):
 require_guardian();cp,work,out=map(lambda x:Path(x).resolve(),(config_path,work_dir,output_dir));raw=verify_inputs.bounded_bytes(cp,1<<20);cfg=json.loads(raw)
 need(set(cfg)=={'schema','grid','inputs','controls'} and cfg['schema']=='fresh-physical-components-v1' and set(cfg['inputs'])=={'physical_rows','physical_runs','physical_report','component_source'},'invalid component request')
 c=cfg['controls'];need(set(c)=={'minimum_free_bytes'} and type(c['minimum_free_bytes']) is int and c['minimum_free_bytes']>=2*1024**3,'invalid disk reserve')
 g=cfg['grid'];need(isinstance(g,dict) and set(g)=={'width','height','west','north','step'} and type(g['width']) is int and type(g['height']) is int and 1<g['width']<=1000000 and 0<g['height']<=1000000 and g['west']==-180 and g['north']==90 and g['step']==360/g['width'] and 90-g['height']*g['step']>=-90-1e-8,'invalid grid')
 need(work.parent.is_dir() and out.parent.is_dir() and not work.exists() and not out.exists() and work!=out and not work.is_relative_to(out) and not out.is_relative_to(work),'fresh work/output required')
 require_same_filesystem(work.parent,out.parent)
 guard=lambda:need(shutil.disk_usage(work.parent).free>=c['minimum_free_bytes'],'disk guard reached');guard();paths={k:pin(v,guard) for k,v in cfg['inputs'].items()}
 for p in [cp,HERE,*paths.values()]:
  d=p if p==HERE else p.parent;need(all(not t.is_relative_to(d) and not d.is_relative_to(t) for t in (work,out)),'work/output overlaps code or inputs')
 need(cfg['inputs']['component_source']['sha256']==REVIEWED_SOURCE_SHA256,'unreviewed component builder source')
 physical=json.loads(verify_inputs.bounded_bytes(paths['physical_report'],16<<20,guard));po=physical.get('physical_output_sha256',physical.get('output_sha256',{}));need(physical.get('status') in ('candidate-only','stage1-complete') and physical.get('grid')==g and po.get('rows.u32le')==cfg['inputs']['physical_rows']['sha256'] and po.get('runs.u32le')==cfg['inputs']['physical_runs']['sha256'],'physical report mismatch')
 output_upper_bytes=require_disk_headroom(work.parent,paths['physical_runs'],paths['physical_rows'],c['minimum_free_bytes'])
 work.mkdir(mode=0o700);sync_dir(work.parent);stage=work/'result.partial';stage.mkdir(mode=0o700);src=stage/'builder.cpp';binary=stage/'component-builder';data=verify_inputs.bounded_bytes(paths['component_source'],1<<20,guard);need(hashlib.sha256(data).hexdigest()==REVIEWED_SOURCE_SHA256,'source changed')
 with open(src,'xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 driver_sha=verify_inputs.sha_file(HERE/'build_components.py',guard);support={n:verify_inputs.sha_file(HERE.parent/'stage2-geodesic-20261104'/n,guard) for n in ('checkpoints.py','verify_inputs.py','atomic_move.py','write_land_stream.py')};started=time.monotonic()
 compiler=subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',str(src),'-o',str(binary)],check=True,capture_output=True,text=True);guard();need(verify_inputs.sha_file(src,guard)==REVIEWED_SOURCE_SHA256 and verify_inputs.sha_file(paths['component_source'],guard)==REVIEWED_SOURCE_SHA256,'compiler source changed')
 proc=subprocess.run([str(binary),str(g['width']),str(g['height']),str(paths['physical_rows']),str(paths['physical_runs']),str(stage/'rows.u32le'),str(stage/'runs.u32le')],check=True,capture_output=True,text=True);guard();output=proc.stdout.strip();need(output and len(output)<512,'invalid builder output')
 land=coverage(paths['physical_rows'],paths['physical_runs'],stage/'rows.u32le',stage/'runs.u32le',g['width'],g['height'],guard);need(land==physical.get('candidate_dry_cells'),'physical land count mismatch')
 for n in ('rows.u32le','runs.u32le','component-builder'):
  fd=os.open(stage/n,os.O_RDONLY);os.fsync(fd);os.close(fd)
 rsha=verify_inputs.sha_file(stage/'rows.u32le',guard);ssha=verify_inputs.sha_file(stage/'runs.u32le',guard);bsha=verify_inputs.sha_file(binary,guard);version=subprocess.run(['g++','--version'],check=True,capture_output=True,text=True).stdout.splitlines()[0]
 manifest={'schema':'single-generation-component-manifest-v1','status':'complete-research','grid':g,'component_source_sha256':REVIEWED_SOURCE_SHA256,'pins':{'physical_rows':cfg['inputs']['physical_rows'],'physical_runs':cfg['inputs']['physical_runs'],'component_rows':{'path':str(out/'rows.u32le'),'sha256':rsha},'component_runs':{'path':str(out/'runs.u32le'),'sha256':ssha}},'physical_report':cfg['inputs']['physical_report'],'builder_binary':{'path':str(out/'component-builder'),'sha256':bsha},'builder_binary_sha256':bsha,'compiler_version':version,'builder_output':output}
 with open(stage/'manifest.json','x') as f:json.dump(manifest,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 report={'schema':'fresh-physical-components-report-v1','status':'research-awaiting-monitor','publishable':False,'config_sha256':hashlib.sha256(raw).hexdigest(),'driver_sha256':driver_sha,'support_sha256':support,'grid':g,'input_sha256':{k:v['sha256'] for k,v in cfg['inputs'].items()},'component_rows_sha256':rsha,'component_runs_sha256':ssha,'builder_binary_sha256':bsha,'manifest_sha256':verify_inputs.sha_file(stage/'manifest.json',guard),'land_cells':land,'builder_output':output,'output_upper_bound_bytes':output_upper_bytes,'elapsed_seconds':time.monotonic()-started,'limitations':['Physical component coverage was checked against the accepted mask; the mask source was not rerasterized.','Root IDs are ephemeral for this exact build; no continent assignment is made.','Memory use is not capped by this runner.']}
 with open(stage/'report.json','x') as f:json.dump(report,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 for p in cfg['inputs'].values():pin(p,guard)
 need(verify_inputs.bounded_bytes(cp,1<<20,guard)==raw and verify_inputs.sha_file(HERE/'build_components.py',guard)==driver_sha and {n:verify_inputs.sha_file(HERE.parent/'stage2-geodesic-20261104'/n,guard) for n in support}==support,'input or code changed');guard();sync_dir(stage);atomic_move.move_noreplace(stage,out)
 try:sync_dir(out.parent)
 except OSError as exc:raise RuntimeError('component output may exist; durability uncertain, inspect before retry') from exc
 return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('config');p.add_argument('work');p.add_argument('output');a=p.parse_args()
 try:run(a.config,a.work,a.output)
 except Exception as exc:print('error: '+str(exc),file=sys.stderr);raise SystemExit(1)
