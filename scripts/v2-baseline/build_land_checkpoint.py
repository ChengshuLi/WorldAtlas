#!/usr/bin/env python3
"""Source-driven mainland seed + nearest-mainland connected-island baseline.

Inputs are an independently built physical RLE and mainland-only 0/17..22 RLE.
There is deliberately no historical assignment input or named-island override.
"""
import argparse, fcntl, hashlib, json, math, multiprocessing as mp, os, shutil, subprocess, sys, time, uuid
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
KERNEL=HERE.parent/'v7-land'/'direct-neon-land'
sys.path.insert(0,str(KERNEL))
import nearest_mainland as n
import tile_index
from tile_index import TileIndex

def pin(spec):
    n.pin(spec)

def write_rle(out, cr, co, mr, mo, assignments, h, w, reserve):
    offsets=np.zeros(h+1,dtype='<u4'); count=0
    with open(out/'runs.u32le','xb') as f:
        for y in range(h):
            if y%128==0:n.require(shutil.disk_usage(out).free>=reserve,'free disk below configured reserve')
            cs=cr[int(co[y]):int(co[y+1])]; ls=mr[int(mo[y]):int(mo[y+1])]
            seg=[]; x=0; li=0; lstart=0
            def emit(end,code):
                nonlocal count
                if seg and seg[-1][1]==code: seg[-1]=(end,code)
                else: seg.append((end,code))
            for a,b,root in cs:
                a=int(a);b=int(b);root=int(root)
                if x<a: emit(a,0)
                if root in assignments: emit(b,assignments[root])
                else:
                    while li<len(ls) and int(ls[li,0])<=a:
                        lstart=int(ls[li,0]);li+=1
                    p=a
                    while p<b:
                        end=min(b,int(ls[li,0]));code=int(ls[li,1]);n.require(code in range(17,23),'mainland seed gap during output');emit(end,code);p=end
                        if p==int(ls[li,0]):lstart=p;li+=1
                x=b
            if x<w:emit(w,0)
            n.require(seg and seg[-1][0]==w,'incomplete output row')
            np.asarray(seg,dtype='<u4').tofile(f);count+=len(seg);n.require(count<2**32,'too many output runs');offsets[y+1]=count
    offsets.tofile(out/'rows.u32le')

def checkpoint_write(path,payload,reserve):
    path=Path(path);n.require(shutil.disk_usage(path.parent).free>=reserve,'checkpoint disk reserve breached')
    tmp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    # JSON object keys become strings on disk. Normalize before hashing so
    # numeric IDs sort identically before and after a checkpoint is loaded.
    payload=json.loads(json.dumps(payload,allow_nan=False))
    body=json.dumps(payload,separators=(',',':'),sort_keys=True,allow_nan=False).encode()
    envelope={'payload':payload,'sha256':hashlib.sha256(body).hexdigest()}
    try:
        with open(tmp,'x') as f:
            json.dump(envelope,f,separators=(',',':'),allow_nan=False);f.flush();os.fsync(f.fileno())
        n.require(shutil.disk_usage(path.parent).free>=reserve,'checkpoint disk reserve breached')
        os.replace(tmp,path)
        directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(directory)
        finally:os.close(directory)
    finally:
        tmp.unlink(missing_ok=True)

def build(cfgpath,out,checkpoint,resume=False,checkpoint_seconds=60.0):
    cp=Path(checkpoint).resolve();n.require(cp.parent.is_dir(),'checkpoint directory must exist')
    with open(str(cp)+'.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        return _build(cfgpath,out,checkpoint,resume,checkpoint_seconds)

def _build(cfgpath,out,checkpoint,resume=False,checkpoint_seconds=60.0):
    started=time.time(); raw=Path(cfgpath).read_bytes();cfg=json.loads(raw)
    expected={'schema','grid','physical_rows','physical_runs','mainland_rows','mainland_runs','physical_report','seed_provenance'}
    n.require(expected<=set(cfg)<=expected|{'workers','chunk_columns','tolerance_metres','minimum_free_bytes','component_manifest'},'invalid config')
    n.require(cfg['schema']=='simple-v2-land-v1','unknown schema');g=cfg['grid'];w=g['width'];h=g['height'];step=g['step'];north=g['north']
    n.require(set(g)=={'width','height','step','west','north'} and w>0 and h>0 and g['west']==-180 and abs(w*step-360)<1e-8 and north<=90 and north-h*step>=-90-1e-8,'invalid grid')
    workers=cfg.get('workers',1);chunk=cfg.get('chunk_columns',128);tol=cfg.get('tolerance_metres',1e-5)
    n.require(type(workers)==int and 1<=workers<=8 and type(chunk)==int and 1<=chunk<=1024 and 0<=tol<=1,'invalid controls')
    reserve=cfg.get('minimum_free_bytes',2*(1<<30));n.require(type(reserve) is int and reserve>=0,'invalid disk reserve')
    input_keys=('physical_rows','physical_runs','mainland_rows','mainland_runs','physical_report','seed_provenance')+(('component_manifest',) if 'component_manifest' in cfg else ())
    for k in input_keys:pin(cfg[k])
    phys=json.loads(Path(cfg['physical_report']['path']).read_bytes());physical_output=phys.get('physical_output_sha256',phys.get('output_sha256',{}))
    n.require(phys.get('status')=='candidate-only' and phys.get('grid')==g and physical_output.get('rows.u32le')==cfg['physical_rows']['sha256'] and physical_output.get('runs.u32le')==cfg['physical_runs']['sha256'],'physical report mismatch')
    seed=json.loads(Path(cfg['seed_provenance']['path']).read_bytes());sg=seed.get('grid',{})
    if seed.get('schema')=='direct-region-seed-research-report-v1':
        n.require(seed.get('status')=='unreviewed-research-not-published' and sg==g and seed.get('grid_crs')=='EPSG:4326' and seed.get('output_rows_sha256')==cfg['mainland_rows']['sha256'] and seed.get('output_runs_sha256')==cfg['mainland_runs']['sha256'],'seed provenance mismatch')
        seed_components=(seed.get('component_rows_sha256'),seed.get('component_runs_sha256'))
    else:
        n.require(seed.get('schema')=='direct-mainland-regions-research-v1' and seed.get('status')=='local-research-not-approved-or-published' and sg=={k:g[k] for k in ('width','height','step')} and seed.get('outputs',{}).get('rows_sha256')==cfg['mainland_rows']['sha256'] and seed.get('outputs',{}).get('runs_sha256')==cfg['mainland_runs']['sha256'],'seed provenance mismatch')
        seed_components=(seed.get('inputs',{}).get('physical_component_rows_sha256'),seed.get('inputs',{}).get('physical_component_runs_sha256'))
    source=HERE.parent/'v7-land'/'build_components.cpp';code_paths=[Path(__file__).resolve(),source,Path(n.__file__),Path(tile_index.__file__),KERNEL/'distance_kernel.cpp'];code_hashes={p.name:n.sha(p) for p in code_paths}
    manifest=None;component_files=[]
    if 'component_manifest' in cfg:
        manifest_path=Path(cfg['component_manifest']['path']).resolve();manifest=json.loads(manifest_path.read_bytes());base=manifest_path.parent
        n.require(manifest.get('schema')=='simple-v2-components-report-v1' and manifest.get('status')=='research-not-published' and manifest.get('grid')==g and manifest.get('inputs')=={k:cfg[k] for k in ('physical_rows','physical_runs','physical_report')} and manifest.get('component_source_sha256')==code_hashes['build_components.cpp'] and isinstance(manifest.get('builder_output'),str) and bool(manifest['builder_output']) and isinstance(manifest.get('compiler_version'),str) and bool(manifest['compiler_version']),'component manifest mismatch')
        component_rows=base/'rows.u32le';component_runs=base/'runs.u32le';binary=base/'component-builder';component_files=[component_rows,component_runs,binary]
        n.require(all(p.is_file() for p in component_files) and n.sha(component_rows)==manifest.get('rows_sha256') and n.sha(component_runs)==manifest.get('runs_sha256') and n.sha(binary)==manifest.get('builder_binary_sha256'),'component artifact mismatch')
        n.require(seed_components==(manifest['rows_sha256'],manifest['runs_sha256']),'seed component provenance mismatch')
    out=Path(out).resolve();inputs=[Path(cfgpath).resolve()]+[Path(cfg[k]['path']).resolve() for k in input_keys]+component_files+code_paths
    checkpoint=Path(checkpoint).resolve();n.require(checkpoint.parent.is_dir() and checkpoint not in inputs and not checkpoint.is_relative_to(out),'checkpoint must be outside inputs/output in an existing directory')
    n.require(not out.exists() and all(not p.is_relative_to(out) and not out.is_relative_to(p.parent) for p in inputs),'output must be new and outside input directories')
    n.require(shutil.disk_usage(out.parent).free>=reserve,'free disk below configured reserve');out.mkdir(mode=0o700)
    if manifest is None:
        binary=out/'component-builder';component_rows=out/'component-rows.u32le';component_runs=out/'component-runs.u32le'
        subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',str(source),'-o',str(binary)],check=True)
        proc=subprocess.run([str(binary),str(w),str(h),cfg['physical_rows']['path'],cfg['physical_runs']['path'],str(component_rows),str(component_runs)],check=True,capture_output=True,text=True);builder_output=proc.stdout.strip();compiler_version=subprocess.run(['g++','--version'],capture_output=True,text=True,check=True).stdout.splitlines()[0]
        n.require(seed_components==(n.sha(component_rows),n.sha(component_runs)),'seed component provenance mismatch')
    else:builder_output=manifest['builder_output'];compiler_version=manifest['compiler_version']
    n.require(shutil.disk_usage(out).free>=reserve,'free disk below configured reserve')
    cr=n.rows_mem(component_runs,h,3);co=n.read_offsets(component_rows,h,cr)
    mr=n.rows_mem(cfg['mainland_runs']['path'],h,2);mo=n.read_offsets(cfg['mainland_rows']['path'],h,mr)
    roots=set(); seen=set(); codes=set()
    # Nonzero seed intervals must each lie wholly within physical component runs.
    for y in range(h):
        cs=cr[int(co[y]):int(co[y+1])]; ls=mr[int(mo[y]):int(mo[y+1])]
        n.require(len(ls)>0 and int(ls[-1,0])==w and int(ls[0,0])>0 and np.all(ls[1:,0]>ls[:-1,0]) and np.all(np.isin(ls[:,1],[0,17,18,19,20,21,22])),'invalid seed row')
        if len(cs):seen.update(map(int,np.unique(cs[:,2])))
        starts=np.r_[np.uint32(0),ls[:-1,0]];mask=ls[:,1]!=0; a=starts[mask];b=ls[mask,0]
        if len(a):
            p=np.searchsorted(cs[:,1],a,side='right');n.require(np.all(p<len(cs)),'seed outside physical land')
            n.require(np.all(cs[p,0]<=a) and np.all(cs[p,1]>=b),'seed crosses water or components')
            roots.update(map(int,np.unique(cs[p,2])));codes.update(map(int,np.unique(ls[mask,1])))
    n.require(codes==set(range(17,23)),'mainland seed must include six classes');rootarr=np.asarray(sorted(roots),dtype=np.uint32)
    index=TileIndex(out/'mainland-tile-index',w,h,step,north,n.segment_distance,n.unit,n.R)
    for y in range(h):
        if y%128==0:n.require(shutil.disk_usage(out).free>=reserve,'free disk below configured reserve')
        row=n.validate_seed_row(cr[int(co[y]):int(co[y+1])],mr[int(mo[y]):int(mo[y+1])],w,rootarr)
        if len(row):index.append_row(y,row)
    index.finish(); best={}; batch=[];pool=None
    n.require(type(checkpoint_seconds) in (int,float) and 0<checkpoint_seconds<=3600,'invalid checkpoint interval')
    identity={'config_sha256':hashlib.sha256(raw).hexdigest(),'code_sha256':code_hashes,'component_rows_sha256':n.sha(component_rows),'component_runs_sha256':n.sha(component_runs),'grid':g}
    startrow=0;queries=0
    if resume:
        envelope=json.loads(checkpoint.read_bytes());saved=envelope['payload'];body=json.dumps(saved,separators=(',',':'),sort_keys=True,allow_nan=False).encode();n.require(envelope.get('sha256')==hashlib.sha256(body).hexdigest(),'checkpoint checksum mismatch');n.require(saved.get('schema')=='simple-v2-query-checkpoint-v1' and saved.get('identity')==identity,'checkpoint identity mismatch')
        startrow=saved['next_row'];queries=saved['queries'];n.require(type(startrow)==int and 0<=startrow<=h and type(queries)==int and queries>=0,'invalid checkpoint cursor')
        n.require(isinstance(saved.get('best'),dict),'invalid checkpoint distances')
        for k,ds in saved['best'].items():
            root=int(k);n.require(root in seen-roots and isinstance(ds,dict) and bool(ds),'invalid checkpoint component')
            vals={}
            for code,d in ds.items():
                code=int(code);n.require(code in range(17,23) and type(d) in (int,float) and math.isfinite(d) and d>=0,'invalid checkpoint distance');vals[code]=d
            best[root]=vals
    else:n.require(not checkpoint.exists(),'checkpoint already exists; use --resume')
    total=0;prefix_queries=0;prefix_roots=set();prefix_runs=int(co[startrow])
    for offset in range(0,len(cr),500000):
        part=cr[offset:offset+500000];part=part[~np.isin(part[:,2],rootarr)];length=part[:,1].astype(np.uint64)-part[:,0];total+=int(((length+chunk-1)//chunk).sum())
        if resume and offset<prefix_runs:
            pre=cr[offset:min(offset+500000,prefix_runs)];pre=pre[~np.isin(pre[:,2],rootarr)];length=pre[:,1].astype(np.uint64)-pre[:,0];prefix_queries+=int(((length+chunk-1)//chunk).sum());prefix_roots.update(map(int,np.unique(pre[:,2])))
    n.require(queries<=total,'checkpoint query count exceeds total')
    if resume:n.require(queries==prefix_queries and set(best)==prefix_roots,'checkpoint cursor, query count, or roots mismatch')
    progress_path=checkpoint.with_name(checkpoint.name+'.progress.jsonl');last_progress=0.;last_checkpoint=time.monotonic()
    def progress(row,stage):
        event={'schema':'simple-v2-query-progress-v1','stage':stage,'time_unix':time.time(),'row':row,'height':h,'queries':queries,'total_queries':total,'attempt_elapsed_seconds':time.time()-started,'resumed_from_row':startrow}
        with open(progress_path,'a') as f:f.write(json.dumps(event,separators=(',',':'))+'\n');f.flush()
        print(json.dumps(event,separators=(',',':')),file=sys.stderr,flush=True)
    def save(row):
        checkpoint_write(checkpoint,{'schema':'simple-v2-query-checkpoint-v1','identity':identity,'next_row':row,'queries':queries,'best':best},reserve);progress(row,'checkpoint')
    progress(startrow,'query-start')
    def collect(results):
        for root,ds in results:
            target=best.setdefault(root,{})
            for code,d in ds.items():target[code]=min(d,target.get(code,math.inf))
    try:
        if workers>1:pool=mp.get_context('fork').Pool(workers,initializer=n._init_query_worker,initargs=(index,tol))
        else:n._init_query_worker(index,tol)
        def drain():
            nonlocal queries,last_progress
            if batch:
                q=len(batch);collect(pool.map(n._run_query,batch,chunksize=16) if pool else map(n._run_query,batch));batch.clear();queries+=q
                if time.monotonic()-last_progress>=5:progress(y,'query');last_progress=time.monotonic()
        for y in range(startrow,h):
            row=cr[int(co[y]):int(co[y+1])];row=row[~np.isin(row[:,2],rootarr)]
            for a,b,root in row:
                for _,lo,hi,_ in n.split_segment(y,int(a),int(b),0,chunk):
                    batch.append((int(root),y,lo,hi))
                    if len(batch)==512:drain()
            if time.monotonic()-last_checkpoint>=checkpoint_seconds:
                drain();save(y+1);last_checkpoint=time.monotonic()
        drain();save(h)
    finally:
        if pool:pool.close();pool.join()
    n.require(queries==total and set(best)==seen-roots,'unassigned component or query count mismatch')
    assignments={};ties=[]
    for root,ds in best.items():
        minimum=min(ds.values());win=sorted(c for c,d in ds.items() if d<=minimum+tol)
        assignments[root]=win[0]
        if len(win)>1:ties.append({'component_id':root,'candidates':win,'distance_metres':minimum})
    n.require(shutil.disk_usage(out).free>=reserve,'free disk below configured reserve')
    write_rle(out,cr,co,mr,mo,assignments,h,w,reserve)
    for k in input_keys:pin(cfg[k])
    if manifest is not None:n.require(n.sha(component_rows)==manifest['rows_sha256'] and n.sha(component_runs)==manifest['runs_sha256'] and n.sha(binary)==manifest['builder_binary_sha256'],'component artifact changed')
    n.require(Path(cfgpath).read_bytes()==raw and {p.name:n.sha(p) for p in code_paths}==code_hashes,'config or code changed')
    report={'schema':'simple-v2-land-report-v1','status':'research-not-published','config_sha256':hashlib.sha256(raw).hexdigest(),'inputs':{k:cfg[k] for k in input_keys},'grid':g,'component_generation':'pinned-component-manifest' if manifest is not None else 'independent-recompute','component_builder':builder_output,'component_builder_binary_sha256':n.sha(binary),'distance_kernel_binary_sha256':n.sha(index.dir/'distance-kernel.so'),'compiler_version':compiler_version,'seeded_roots':sorted(roots),'island_components':len(assignments),'ties':ties,'output_rows_sha256':n.sha(out/'rows.u32le'),'output_runs_sha256':n.sha(out/'runs.u32le'),'code_sha256':code_hashes,'elapsed_seconds':time.time()-started,'checkpoint_sha256':n.sha(checkpoint),'queries':queries,'resumed_from_row':startrow,'method':'wrapped 4-neighbor physical land components; each unseeded component assigned by minimum spherical cell-center distance to seeded mainland; tolerance ties choose lowest code; no named exceptions','caveat':'Mainland seed and input physical grid must be source-derived. Mainland-cell center distance approximates coastline shore distance; exact historical V2 cut and tie conventions are unverified. No historical continent assignment input.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('config');p.add_argument('output');p.add_argument('--checkpoint',required=True);p.add_argument('--resume',action='store_true');p.add_argument('--checkpoint-seconds',type=float,default=60);a=p.parse_args()
    try: print(json.dumps(build(a.config,a.output,a.checkpoint,a.resume,a.checkpoint_seconds),indent=2))
    except Exception as e: print('error: '+str(e),file=sys.stderr);raise
