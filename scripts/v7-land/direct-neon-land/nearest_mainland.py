#!/usr/bin/env python3
"""Research-only nearest-mainland component claims; no legacy labels are read.

The reviewed mainland seed and all selectors are revisioned, mask-bound inputs.
This stage deliberately does not generate mainland partitions.
"""
import hashlib, json, math, subprocess, multiprocessing, sys
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from tile_index import TileIndex

R = 6371008.8

def require(v, msg):
    if not v: raise ValueError(msg)

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def pin(spec):
    require(isinstance(spec,dict) and set(spec)=={'path','sha256'},'invalid pin')
    require(isinstance(spec['sha256'],str) and len(spec['sha256'])==64 and all(c in '0123456789abcdef' for c in spec['sha256']), 'invalid digest')
    require(Path(spec['path']).is_file() and sha(spec['path'])==spec['sha256'], 'input digest mismatch: '+str(spec['path']))

def unit(lat,lon):
    p=np.deg2rad(lat); l=np.deg2rad(lon); c=np.cos(p)
    return np.column_stack((c*np.cos(l),c*np.sin(l),np.sin(p)))

def segment_distance(y,a,b, ys,aa,bb, width,step,north):
    """Exact minimum spherical distance between two discrete horizontal runs.

    Centers lie on a common regular global grid. The minimum longitude gap of
    two integer intervals is attained by overlapping columns or endpoints.
    """
    aa=np.asarray(aa,dtype=np.int64); bb=np.asarray(bb,dtype=np.int64)
    gap=np.full(len(aa),width,dtype=np.int64)
    for shift in (-width,0,width):
        left=aa+shift; right=bb-1+shift
        gap=np.minimum(gap,np.maximum(0,np.maximum(left-(b-1),a-right)))
    p1=math.radians(north-(y+.5)*step); p2=np.deg2rad(north-(np.asarray(ys)+.5)*step)
    dl=np.deg2rad(gap*step); dp=p2-p1
    hav=np.sin(dp/2)**2+math.cos(p1)*np.cos(p2)*np.sin(dl/2)**2
    return 2*R*np.arcsin(np.sqrt(np.clip(hav,0,1)))

def split_segment(y,a,b,code,chunk):
    while a<b:
        z=min(b,a+chunk); yield (y,a,z,code); a=z

def index_mainlands(segments, width,step,north):
    require(bool(segments),'no mainland seeds')
    data=np.asarray(segments,dtype=np.int64)
    ys,a,b=data[:,0],data[:,1],data[:,2]
    lat=north-(ys+.5)*step; lon=-180+((a+b-1)/2+.5)*step
    mids=unit(lat,lon)
    # Longitude arc length is an upper bound for great-circle distance from
    # midpoint to any point on the segment, including near the poles.
    radius=(b-a-1)*step*math.pi/180*R/2
    return data,cKDTree(mids),float(radius.max())

def nearest_run(y,a,b,index,width,step,north,tol):
    data,tree,maxradius=index
    lat=north-(y+.5)*step; lon=-180+((a+b-1)/2+.5)*step
    point=unit(np.array([lat]),np.array([lon]))[0]
    qr=(b-a-1)*step*math.pi/180*R/2
    k=min(16,len(data)); distances={}
    while True:
        chord,ix=tree.query(point,k=k,workers=1)
        ix=np.atleast_1d(ix); chord=np.atleast_1d(chord)
        rows=data[ix]
        ds=segment_distance(y,a,b,rows[:,0],rows[:,1],rows[:,2],width,step,north)
        distances={int(c):float(ds[rows[:,3]==c].min()) for c in np.unique(rows[:,3])}
        best=min(distances.values())
        # Includes every candidate within tolerance of the best possible run.
        lower=2*R*math.asin(min(1,float(chord[-1])/2))-maxradius-qr
        if k==len(data) or lower>best+tol+1e-6: return distances
        k=min(2*k,len(data))

def rows_mem(path,h,nfields):
    arr=np.memmap(path,dtype='<u4',mode='r')
    require(len(arr)%(nfields)==0,'bad run stream size')
    return arr.reshape(-1,nfields)

def read_offsets(path,h,runs):
    r=np.memmap(path,dtype='<u4',mode='r')
    require(len(r)==h+1 and r[0]==0 and r[-1]==len(runs) and np.all(r[1:]>=r[:-1]),'invalid row offsets')
    return r

_worker_index=None
_worker_tolerance=None

def _init_query_worker(index,tolerance):
    global _worker_index,_worker_tolerance
    _worker_index=index;_worker_tolerance=tolerance

def _run_query(item):
    root,y,a,b=item
    return root,_worker_index.nearest(y,a,b,_worker_tolerance)

def validate_seed_row(components,labels,width,root_ids):
    """Vectorized exact footprint validation, returning nonzero seed runs."""
    require(len(labels)>0 and int(labels[-1,0])==width and int(labels[0,0])>0 and np.all(labels[1:,0]>labels[:-1,0]) and np.all(np.isin(labels[:,1],[0,17,18,19,20,21,22])),'invalid mainland seed row')
    require(np.all(components[:,0]<components[:,1]) and np.all(components[:,1]<=width) and (len(components)<2 or np.all(components[1:,0]>=components[:-1,1])),'invalid component row')
    starts=np.r_[np.uint32(0),labels[:-1,0]];mask=labels[:,1]!=0; a=starts[mask];b=labels[mask,0];codes=labels[mask,1]
    selected=np.isin(components[:,2],root_ids)
    total_selected=int((components[selected,1].astype(np.int64)-components[selected,0]).sum())
    if len(a):
        pos=np.searchsorted(components[:,1],a,side='right')
        require(np.all(pos<len(components)),'mainland seed outside physical land')
        require(np.all(components[pos,0]<=a) and np.all(components[pos,1]>=b) and np.all(selected[pos]),'mainland seed missing, mixed, or outside selected components')
    require(int((b.astype(np.int64)-a).sum())==total_selected,'mainland seed missing, mixed, or outside selected components')
    return np.column_stack((a,b,codes)).astype(np.uint32,copy=False)

def build(config_path,output,allow_unverified_snapshot=False,component_manifest=None):
    require(allow_unverified_snapshot, 'snapshot authenticity is unverified; pass --allow-unverified-snapshot for research only')
    require(sys.byteorder=='little','the component and distance kernels require a little-endian host')
    program_sha=sha(__file__); index_program_sha=sha(Path(__file__).parent/'tile_index.py'); kernel_source_sha=sha(Path(__file__).parent/'distance_kernel.cpp')
    cfg_bytes=Path(config_path).read_bytes(); cfg=json.loads(cfg_bytes)
    required={'schema','snapshot','grid','physical_rows','physical_runs','component_rows','component_runs','mainland_rows','mainland_runs'}
    require(required<=set(cfg)<=required|{'workers'},'invalid config fields')
    workers=cfg.get('workers',1); require(type(workers) is int and 1<=workers<=8,'workers must be an integer from 1 to 8')
    require(cfg['schema']=='nearest-mainland-build-v1','unknown schema')
    pins=[cfg[k] for k in ('snapshot','physical_rows','physical_runs','component_rows','component_runs','mainland_rows','mainland_runs')]
    if component_manifest is not None:pins.append(component_manifest)
    for p in pins:pin(p)
    out=Path(output).resolve(); inputs=[Path(config_path).resolve()]+[Path(p['path']).resolve() for p in pins]
    require(not out.exists() and all(not p.is_relative_to(out) and not out.is_relative_to(p.parent) for p in inputs),'output must be new and isolated')
    grid=cfg['grid']; require(set(grid)=={'width','height','step','west','north'},'invalid grid')
    w,h,step,west,north=(grid[k] for k in ('width','height','step','west','north'))
    require(type(w) is int and type(h) is int and w>0 and h>0 and type(step) in (float,int) and math.isfinite(step) and step>0 and west==-180 and north<=90 and north-h*step>=-90-1e-8 and abs(w*step-360)<1e-8,'global grid required')
    snap=json.loads(Path(cfg['snapshot']['path']).read_bytes()); rev=snap.get('decision_revision',{}); erev=snap.get('entity_revision',{})
    require(snap.get('source')=='neon-export' and snap.get('schema') in ('worldatlas-geography-decision-export-v1','worldatlas-geography-decision-draft-evidence-v1') and isinstance(rev.get('id'),str) and bool(rev['id']) and erev.get('id')==rev.get('entity_revision') and (rev.get('status'),erev.get('status')) in (('draft','draft'),('accepted','accepted')),'invalid revision snapshot')
    require(snap['schema']=='worldatlas-geography-decision-draft-evidence-v1' and rev['status']==erev['status']=='draft','mainland research policy requires draft snapshot')
    pol=snap.get('land_mainland_policy'); require(isinstance(pol,dict),'missing reviewed mainland policy')
    keys={'execution_status','method','distance','tie','precedence','physical_rows_sha256','physical_runs_sha256','component_algorithm_sha256','component_rows_sha256','component_runs_sha256','mainland_rows_sha256','mainland_runs_sha256','mainland_component_ids','reviewed_component_claims','source_cut_feature_ids','grid','chunk_columns','tolerance_metres'}
    require(set(pol)==keys and pol['execution_status']=='selected_for_research' and pol['method']=='nearest_mainland_v1' and pol['distance']=='minimum_spherical_cell_center' and pol['tie']=='fail' and pol['precedence']=='mainland_then_reviewed_component_then_nearest','unsupported or incomplete mainland policy')
    for k in ('physical_rows','physical_runs','component_rows','component_runs','mainland_rows','mainland_runs'): require(pol[k+'_sha256']==cfg[k]['sha256'],'policy/input pin mismatch: '+k)
    cuts=pol['source_cut_feature_ids']; require(isinstance(cuts,list) and all(isinstance(x,str) and bool(x.strip()) for x in cuts) and len(set(cuts))==len(cuts),'invalid cut evidence IDs')
    require(pol['grid']==grid,'policy grid mismatch')
    chunk=pol['chunk_columns']; tol=pol['tolerance_metres']
    require(type(chunk) is int and 1<=chunk<=1024 and type(tol) in (int,float) and math.isfinite(tol) and 0<=tol<=1,'invalid distance parameters')
    root_list=pol['mainland_component_ids']; require(isinstance(root_list,list) and bool(root_list) and all(type(v) is int and v>=0 for v in root_list) and len(set(root_list))==len(root_list),'invalid mainland components')
    roots=set(root_list)
    bindings=[b for b in snap.get('category_bindings',[]) if b.get('physical_class')=='land']
    require(len(bindings)==6 and {b.get('code') for b in bindings}==set(range(17,23)) and len({b.get('entity_id') for b in bindings})==6 and all(type(b.get('entity_id')) is int for b in bindings),'six distinct land bindings required')
    entities={b['entity_id']:b['code'] for b in bindings}
    entity_rows=snap.get('entities'); require(isinstance(entity_rows,list) and len({e.get('id') for e in entity_rows})==len(entity_rows) and set(entities)<={e.get('id') for e in entity_rows},'invalid entity revision or land bindings')
    require(isinstance(pol['reviewed_component_claims'],list),'reviewed component claims must be a list')
    claims={}
    for v in pol['reviewed_component_claims']:
        require(isinstance(v,dict) and set(v)=={'rule_id','component_id','entity_id'} and isinstance(v['rule_id'],str) and v['rule_id'] and type(v['component_id']) is int and v['component_id']>=0 and v['entity_id'] in entities,'invalid reviewed component claim')
        require(v['component_id'] not in claims and v['component_id'] not in roots,'duplicate/conflicting reviewed component claim')
        claims[v['component_id']]=v
    require(len({c['rule_id'] for c in claims.values()})==len(claims),'duplicate reviewed rule ID')
    source=Path(__file__).resolve().parent.parent/'build_components.cpp'
    require(source.is_file() and sha(source)==pol['component_algorithm_sha256'],'component algorithm mismatch')
    # Standalone mode independently regenerates components. Same-run mode may
    # reuse the direct orchestrator's manifest but must not claim independence.
    manifest=None; manifest_related=[]
    if component_manifest is not None:
        manifest=json.loads(Path(component_manifest['path']).read_bytes())
        require(manifest.get('schema')=='single-generation-component-manifest-v1' and manifest.get('status')=='complete-research' and manifest.get('component_source_sha256')==pol['component_algorithm_sha256'] and manifest.get('grid')==grid,'invalid component manifest')
        for key in ('physical_rows','physical_runs','component_rows','component_runs'):
            require(manifest.get('pins',{}).get(key)==cfg[key],f'component manifest pin mismatch: {key}')
        for item in manifest['pins'].values():pin(item)
        physical_report=manifest.get('physical_report');binary_pin=manifest.get('builder_binary');pin(physical_report);pin(binary_pin);manifest_related=[physical_report,binary_pin]
        report=json.loads(Path(physical_report['path']).read_bytes());outputs=report.get('physical_output_sha256',report.get('output_sha256',{}))
        require(report.get('status')=='candidate-only' and report.get('grid')==grid and outputs.get('rows.u32le')==cfg['physical_rows']['sha256'] and outputs.get('runs.u32le')==cfg['physical_runs']['sha256'],'component manifest physical report mismatch')
        kind='raw-pipeline-report' if all(k in report for k in ('physical_output_sha256','source_manifest','land_config','water_config','stage_reports')) else 'compose-report'
        require(manifest.get('physical_report_kind')==kind and manifest.get('builder_binary_sha256')==binary_pin['sha256'] and all(Path(cfg[k]['path']).resolve().parent==Path(binary_pin['path']).resolve().parent for k in ('component_rows','component_runs')) and isinstance(manifest.get('compiler_version'),str) and bool(manifest['compiler_version']) and isinstance(manifest.get('builder_output'),str) and bool(manifest['builder_output']),'component manifest evidence mismatch')
    out.mkdir(mode=0o700)
    if manifest is None:
        binary=out/'component-builder'; rebuilt_rows=out/'verified-component-rows.u32le'; rebuilt_runs=out/'verified-component-runs.u32le'
        compiler=subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',str(source),'-o',str(binary)],capture_output=True,text=True)
        require(compiler.returncode==0,'component builder compilation failed: '+compiler.stderr[-3000:])
        proc=subprocess.run([str(binary),str(w),str(h),cfg['physical_rows']['path'],cfg['physical_runs']['path'],str(rebuilt_rows),str(rebuilt_runs)],capture_output=True,text=True)
        require(proc.returncode==0,'component regeneration failed: '+proc.stderr[-3000:])
        require(sha(rebuilt_rows)==cfg['component_rows']['sha256'] and sha(rebuilt_runs)==cfg['component_runs']['sha256'],'component connectivity mismatch')
    require(sha(source)==pol['component_algorithm_sha256'],'component source changed')
    cr=rows_mem(cfg['component_runs']['path'],h,3); co=read_offsets(cfg['component_rows']['path'],h,cr)
    mr=rows_mem(cfg['mainland_runs']['path'],h,2); mo=read_offsets(cfg['mainland_rows']['path'],h,mr)
    index=TileIndex(out/'mainland-tile-index',w,h,step,north,segment_distance,unit,R)
    seen=set(); seed_codes=set();root_array=np.asarray(sorted(roots),dtype=np.uint32)
    # Seed intervals must be fully contained in selected component runs and
    # have equal total area. Together these conditions prove exact coverage.
    for y in range(h):
        components=cr[int(co[y]):int(co[y+1])]; labels=mr[int(mo[y]):int(mo[y+1])]
        seed_row=validate_seed_row(components,labels,w,root_array)
        if len(components):seen.update(map(int,np.unique(components[:,2])))
        if len(seed_row):seed_codes.update(map(int,np.unique(seed_row[:,2])));index.append_row(y,seed_row)
    require(roots<=seen and set(claims)<=seen,'unknown mainland or reviewed component')
    require(seed_codes==set(range(17,23)),'mainland seed must cover every land category')
    index.finish()
    best={}; batch=[]
    def collect(results):
        for root,distances in results:
            for code,d in distances.items():
                acc=best.setdefault(root,{});acc[code]=min(d,acc.get(code,math.inf))
    # At most 512 query runs are queued at a time. Fork shares the read-only
    # tile-center index, while each worker has its own fixed-size tile cache.
    pool=None
    try:
        if workers>1:
            pool=multiprocessing.get_context('fork').Pool(workers,initializer=_init_query_worker,initargs=(index,tol))
        else:_init_query_worker(index,tol)
        def drain():
            if batch:
                collect(pool.map(_run_query,batch,chunksize=16) if pool else map(_run_query,batch));batch.clear()
        excluded=np.asarray(sorted(roots|set(claims)),dtype=np.uint32)
        for y in range(h):
            row=cr[int(co[y]):int(co[y+1])]
            row=row[~np.isin(row[:,2],excluded)]
            for a,b,root in row:
                root=int(root)
                for _,lo,hi,_ in split_segment(y,int(a),int(b),0,chunk):
                    batch.append((root,y,lo,hi))
                    if len(batch)==512:drain()
        drain()
    finally:
        if pool:pool.close();pool.join()
    require(set(best)==seen-roots-set(claims),'unassigned component')
    generated=[]
    for root,ds in sorted(best.items()):
        minimum=min(ds.values()); winners=[c for c,d in ds.items() if d<=minimum+tol]
        require(len(winners)==1,f'ambiguous nearest mainland component {root}: {winners}')
        generated.append({'component_id':root,'code':winners[0],'distance_metres':minimum})
    for p in pins+manifest_related:pin(p)
    require(sha(source)==pol['component_algorithm_sha256'],'component source changed during build')
    require(Path(config_path).read_bytes()==cfg_bytes,'config changed during build')
    require(sha(__file__)==program_sha and sha(Path(__file__).parent/'tile_index.py')==index_program_sha and sha(Path(__file__).parent/'distance_kernel.cpp')==kernel_source_sha,'program changed during build')
    result={'schema':'nearest-mainland-claims-v1','status':'unverified-research-not-published','decision_revision':rev['id'],'snapshot_sha256':cfg['snapshot']['sha256'],'config_sha256':hashlib.sha256(cfg_bytes).hexdigest(),'program_sha256':program_sha,'tile_index_program_sha256':index_program_sha,'distance_kernel_source_sha256':kernel_source_sha,'distance_kernel_binary_sha256':sha(index.dir/'distance-kernel.so'),'distance_kernel_compiler':subprocess.run(['g++','--version'],capture_output=True,text=True,check=True).stdout.splitlines()[0],'tile_index_stats':index.stats(),'component_generation_method':'single-generation-manifest' if manifest is not None else 'independent-recompute','component_manifest_sha256':component_manifest['sha256'] if component_manifest is not None else None,'query_workers':workers,'query_cache_note':'Cache statistics in this report describe only the parent process; each worker has a separate bounded cache.','mainland_components':sorted(roots),'reviewed_claims':list(claims.values()),'nearest_claims':generated,'limitation':'The snapshot and mainland seed are not authenticated; mainland geometry and decisions require independent review. No prior continent labels were read.'}
    (out/'claims.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    import argparse,sys
    p=argparse.ArgumentParser(); p.add_argument('config'); p.add_argument('output'); p.add_argument('--allow-unverified-snapshot',action='store_true'); a=p.parse_args()
    try: print(json.dumps(build(a.config,a.output,a.allow_unverified_snapshot),indent=2))
    except Exception as e: print('error: '+str(e),file=sys.stderr); raise SystemExit(1)
