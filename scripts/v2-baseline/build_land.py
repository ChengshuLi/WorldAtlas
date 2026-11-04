#!/usr/bin/env python3
"""Source-driven mainland seed + nearest-mainland connected-island baseline.

Inputs are an independently built physical RLE and mainland-only 0/17..22 RLE.
There is deliberately no historical assignment input or named-island override.
"""
import argparse, hashlib, json, math, multiprocessing as mp, shutil, subprocess, sys, time
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

def build(cfgpath,out):
    started=time.time(); raw=Path(cfgpath).read_bytes();cfg=json.loads(raw)
    expected={'schema','grid','physical_rows','physical_runs','mainland_rows','mainland_runs','physical_report','seed_provenance'}
    n.require(expected<=set(cfg)<=expected|{'workers','chunk_columns','tolerance_metres','minimum_free_bytes'},'invalid config')
    n.require(cfg['schema']=='simple-v2-land-v1','unknown schema');g=cfg['grid'];w=g['width'];h=g['height'];step=g['step'];north=g['north']
    n.require(set(g)=={'width','height','step','west','north'} and w>0 and h>0 and g['west']==-180 and abs(w*step-360)<1e-8 and north<=90 and north-h*step>=-90-1e-8,'invalid grid')
    workers=cfg.get('workers',1);chunk=cfg.get('chunk_columns',128);tol=cfg.get('tolerance_metres',1e-5)
    n.require(type(workers)==int and 1<=workers<=8 and type(chunk)==int and 1<=chunk<=1024 and 0<=tol<=1,'invalid controls')
    reserve=cfg.get('minimum_free_bytes',2*(1<<30));n.require(type(reserve) is int and reserve>=0,'invalid disk reserve')
    input_keys=('physical_rows','physical_runs','mainland_rows','mainland_runs','physical_report','seed_provenance')
    for k in input_keys:pin(cfg[k])
    phys=json.loads(Path(cfg['physical_report']['path']).read_bytes());physical_output=phys.get('physical_output_sha256',phys.get('output_sha256',{}))
    n.require(phys.get('status')=='candidate-only' and phys.get('grid')==g and physical_output.get('rows.u32le')==cfg['physical_rows']['sha256'] and physical_output.get('runs.u32le')==cfg['physical_runs']['sha256'],'physical report mismatch')
    seed=json.loads(Path(cfg['seed_provenance']['path']).read_bytes());sg=seed.get('grid',{})
    if seed.get('schema')=='direct-region-seed-research-report-v1':
        n.require(seed.get('status')=='unreviewed-research-not-published' and sg==g and seed.get('output_rows_sha256')==cfg['mainland_rows']['sha256'] and seed.get('output_runs_sha256')==cfg['mainland_runs']['sha256'],'seed provenance mismatch')
        seed_components=(seed.get('component_rows_sha256'),seed.get('component_runs_sha256'))
    else:
        n.require(seed.get('schema')=='direct-mainland-regions-research-v1' and seed.get('status')=='local-research-not-approved-or-published' and sg=={k:g[k] for k in ('width','height','step')} and seed.get('outputs',{}).get('rows_sha256')==cfg['mainland_rows']['sha256'] and seed.get('outputs',{}).get('runs_sha256')==cfg['mainland_runs']['sha256'],'seed provenance mismatch')
        seed_components=(seed.get('inputs',{}).get('physical_component_rows_sha256'),seed.get('inputs',{}).get('physical_component_runs_sha256'))
    out=Path(out).resolve();inputs=[Path(cfgpath).resolve()]+[Path(cfg[k]['path']).resolve() for k in input_keys]
    n.require(not out.exists() and all(not p.is_relative_to(out) and not out.is_relative_to(p.parent) for p in inputs),'output must be new and outside input directories')
    n.require(shutil.disk_usage(out.parent).free>=reserve,'free disk below configured reserve');out.mkdir(mode=0o700)
    binary=out/'component-builder';source=HERE.parent/'v7-land'/'build_components.cpp'
    code_paths=[Path(__file__).resolve(),source,Path(n.__file__),Path(tile_index.__file__),KERNEL/'distance_kernel.cpp'];code_hashes={p.name:n.sha(p) for p in code_paths}
    subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',str(source),'-o',str(binary)],check=True)
    proc=subprocess.run([str(binary),str(w),str(h),cfg['physical_rows']['path'],cfg['physical_runs']['path'],str(out/'component-rows.u32le'),str(out/'component-runs.u32le')],check=True,capture_output=True,text=True)
    n.require(shutil.disk_usage(out).free>=reserve,'free disk below configured reserve')
    n.require(seed_components==(n.sha(out/'component-rows.u32le'),n.sha(out/'component-runs.u32le')),'seed component provenance mismatch')
    cr=n.rows_mem(out/'component-runs.u32le',h,3);co=n.read_offsets(out/'component-rows.u32le',h,cr)
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
    def collect(results):
        for root,ds in results:
            target=best.setdefault(root,{})
            for code,d in ds.items():target[code]=min(d,target.get(code,math.inf))
    try:
        if workers>1:pool=mp.get_context('fork').Pool(workers,initializer=n._init_query_worker,initargs=(index,tol))
        else:n._init_query_worker(index,tol)
        def drain():
            if batch:collect(pool.map(n._run_query,batch,chunksize=16) if pool else map(n._run_query,batch));batch.clear()
        for y in range(h):
            row=cr[int(co[y]):int(co[y+1])];row=row[~np.isin(row[:,2],rootarr)]
            for a,b,root in row:
                for _,lo,hi,_ in n.split_segment(y,int(a),int(b),0,chunk):
                    batch.append((int(root),y,lo,hi))
                    if len(batch)==512:drain()
        drain()
    finally:
        if pool:pool.close();pool.join()
    n.require(set(best)==seen-roots,'unassigned component')
    assignments={};ties=[]
    for root,ds in best.items():
        minimum=min(ds.values());win=sorted(c for c,d in ds.items() if d<=minimum+tol)
        assignments[root]=win[0]
        if len(win)>1:ties.append({'component_id':root,'candidates':win,'distance_metres':minimum})
    n.require(shutil.disk_usage(out).free>=reserve,'free disk below configured reserve')
    write_rle(out,cr,co,mr,mo,assignments,h,w,reserve)
    for k in ('physical_rows','physical_runs','mainland_rows','mainland_runs','physical_report','seed_provenance'):pin(cfg[k])
    n.require(Path(cfgpath).read_bytes()==raw,'config changed')
    report={'schema':'simple-v2-land-report-v1','status':'research-not-published','config_sha256':hashlib.sha256(raw).hexdigest(),'inputs':{k:cfg[k] for k in ('physical_rows','physical_runs','mainland_rows','mainland_runs','physical_report','seed_provenance')},'grid':g,'component_builder':proc.stdout.strip(),'component_builder_binary_sha256':n.sha(binary),'distance_kernel_binary_sha256':n.sha(index.dir/'distance-kernel.so'),'compiler_version':subprocess.run(['g++','--version'],capture_output=True,text=True,check=True).stdout.splitlines()[0],'seeded_roots':sorted(roots),'island_components':len(assignments),'ties':ties,'output_rows_sha256':n.sha(out/'rows.u32le'),'output_runs_sha256':n.sha(out/'runs.u32le'),'code_sha256':code_hashes,'elapsed_seconds':time.time()-started,'method':'wrapped 4-neighbor physical land components; each unseeded component assigned by minimum spherical cell-center distance to seeded mainland; tolerance ties choose lowest code; no named exceptions','caveat':'Mainland seed and input physical grid must be source-derived. Mainland-cell center distance approximates coastline shore distance; exact historical V2 cut and tie conventions are unverified. No historical continent assignment input.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('config');p.add_argument('output');a=p.parse_args()
    try: print(json.dumps(build(a.config,a.output),indent=2))
    except Exception as e: print('error: '+str(e),file=sys.stderr);raise
