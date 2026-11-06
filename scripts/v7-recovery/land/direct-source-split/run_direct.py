#!/usr/bin/env /usr/bin/python3
"""Research-only source-bound mainland cut; no existing label grid is an input.

Consumes pinned local exports of a selected Neon draft and its witness evidence.
A hash does not authenticate those exports. Outputs are not approved or selected.
Run under an external process-group resource monitor; failures leave no report.
"""
import argparse, hashlib, json, math, os, resource, shutil, struct, time
from array import array
from pathlib import Path
import numpy as np
from selection import selected_cut, need
from boundary import TripleRows, reject_center_hits, reject_terminal_near_land, select_witnesses, verify_witness_assignments, resolve_fragments
from partition_core import rasterize_barriers
from cut_graph import partition


def require_guardian():
    parent=os.getppid();need(parent==os.getpgrp(),'monitored guardian required')
    try:
        args=Path(f'/proc/{parent}/cmdline').read_bytes().split(b'\0')
        valid=len(args)>=3 and Path(os.fsdecode(args[1])).resolve()==Path(__file__).with_name('guardian.py').resolve()
    except (OSError,ValueError):
        valid=False
    need(valid and os.getppid()==parent,'monitored guardian required')


def digest(path, guard):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        while True:
            block=f.read(1<<20)
            if not block: break
            h.update(block); guard()
    return h.hexdigest()


def bounded(path,limit):
    with Path(path).open('rb') as f:
        need(os.fstat(f.fileno()).st_size<=limit,'document too large')
        data=f.read(limit+1)
    need(len(data)<=limit,'document too large')
    return data


def strict_json(raw):
    def unique(pairs):
        result={}
        for key,value in pairs:
            need(key not in result,'duplicate JSON key');result[key]=value
        return result
    def nonfinite(value):raise ValueError('nonfinite JSON number')
    return json.loads(raw,object_pairs_hook=unique,parse_constant=nonfinite)


def run(request, output):
    require_guardian()
    raise RuntimeError('planar nearest-side method retired; a reviewed WGS84 replacement is required')
    started=time.monotonic(); request=Path(request).resolve(strict=True); out=Path(output).resolve()
    raw=bounded(request,1<<20);cfg=strict_json(raw)
    need(set(cfg)=={'schema','grid','inputs','rule_id','boundary_id','limits'} and cfg['schema']=='direct-source-split-request-v1','invalid request')
    grid=cfg['grid']; need(set(grid)=={'width','height','west','north','step'} and type(grid['width']) is int and type(grid['height']) is int
         and 0<grid['width']<=1000000 and 0<grid['height']<=1000000 and grid['west']==-180 and grid['north']==90
         and grid['step']==360/grid['width'] and 90-grid['height']*grid['step']>=-90-1e-8,'invalid grid')
    lim=cfg['limits']; need(set(lim)=={'minimum_free_bytes','max_nodes','max_raster_work','max_residual_cells','max_residual_segment_tests'}
         and all(type(v) is int and v>0 for v in lim.values())
         and lim['minimum_free_bytes']>=2*1024**3
         and lim['max_nodes']<=50000000 and lim['max_raster_work']<=5000000
         and lim['max_residual_cells']<=100000 and lim['max_residual_segment_tests']<=10000000,'invalid resource limits')
    need(not out.exists() and out.parent.is_dir(),'new output directory required')
    def guard():
        need(shutil.disk_usage(out.parent).free>=lim['minimum_free_bytes'],'disk floor reached')
    guard(); inputs=cfg['inputs']; need(set(inputs)=={'snapshot','witness','component_rows','component_runs'},'invalid input set')
    paths={}
    for name,pin in inputs.items():
        need(isinstance(pin,dict) and set(pin)=={'path','sha256'} and isinstance(pin['sha256'],str)
             and len(pin['sha256'])==64 and all(c in '0123456789abcdef' for c in pin['sha256']),'invalid input pin')
        p=Path(pin['path']).resolve(strict=True);need(p.is_file() and digest(p,guard)==pin['sha256'],'input pin mismatch: '+name);paths[name]=p
    for path in [request,*paths.values(),Path(__file__).resolve(),Path(__file__).with_name('selection.py').resolve(),Path(__file__).with_name('boundary.py').resolve(),Path(__file__).with_name('cut_graph.py').resolve(),Path(__file__).with_name('partition_core.py').resolve()]:
        need(not out.is_relative_to(path.parent) and not path.is_relative_to(out),'output overlaps input or code')
    codepaths=[Path(__file__),Path(__file__).with_name('selection.py'),Path(__file__).with_name('boundary.py'),Path(__file__).with_name('cut_graph.py'),Path(__file__).with_name('partition_core.py')]
    codehash={p.name:digest(p,guard) for p in codepaths}
    snapshot=strict_json(bounded(paths['snapshot'],16<<20));witness=strict_json(bounded(paths['witness'],16<<20))
    info=selected_cut(snapshot,witness,inputs['snapshot']['sha256'],{k:inputs[k]['sha256'] for k in ('component_rows','component_runs')},cfg['rule_id'],cfg['boundary_id'],grid)
    line=info['line'];need(len(line)<=100000,'boundary vertex limit');w,h,step=grid['width'],grid['height'],grid['step'];root=info['component']
    components=TripleRows(paths['component_rows'],paths['component_runs'],h,max_width=w)
    def component_row(y):
        a=components.row(y)
        need(not len(a) or (np.all(a[:,0]<a[:,1]) and np.all(a[:,1]<=w) and np.all(a[1:,0]>=a[:-1,1])),'invalid component row')
        return a
    def rows(y):return [(int(a),int(b)) for a,b,k in component_row(y) if int(k)==root]
    def eligible(x,y):
        if not (0<=x<w and 0<=y<h):return False
        row=component_row(y);i=int(np.searchsorted(row[:,1],x,side='right'))
        return i<len(row) and int(row[i,0])<=x<int(row[i,1]) and int(row[i,2])==root
    def xy(lon,lat):return math.floor((lon-grid['west'])/step),math.floor((grid['north']-lat)/step)
    seeds,checks,side_codes=select_witnesses(info['witnesses'],xy,eligible,line,info['inside_code'],info['outside_code'])
    path=[[(lon-grid['west'])/step,(grid['north']-lat)/step] for lon,lat in line]
    need(all(0<=x<=w and 0<=y<=h for x,y in path),'boundary exceeds grid')
    reject_center_hits(path,w,h,guard=guard,max_work=lim['max_raster_work']);reject_terminal_near_land(path,w,h,eligible);guard();cuts=rasterize_barriers([path],w,h,guard=guard,max_work=lim['max_raster_work']);guard()
    out.mkdir(mode=0o700);result=partition(rows,w,h,cuts,seeds,out/'graph',guard,max_nodes=lim['max_nodes'])
    graphpaths=[out/'graph'/n for n in ('partition-rows.u32le','partition-spans.u32le','residual-rows.u32le','residual-spans.u32le')]
    graphhash={p.name:digest(p,guard) for p in graphpaths}
    graph=TripleRows(out/'graph/partition-rows.u32le',out/'graph/partition-spans.u32le',h,max_width=w)
    remaining=TripleRows(out/'graph/residual-rows.u32le',out/'graph/residual-spans.u32le',h,max_width=w)
    groups={};residual=0
    for y in np.flatnonzero(remaining.offsets[1:]!=remaining.offsets[:-1]):
        guard()
        for a,b,group in remaining.row(int(y)):
            need(0<=int(a)<int(b)<=w,'invalid residual span');residual+=int(b)-int(a)
            need(residual<=lim['max_residual_cells'],'residual cell limit');groups.setdefault(int(group),[]).extend((x,int(y)) for x in range(int(a),int(b)))
    need(residual*max(1,len(line)-1)<=lim['max_residual_segment_tests'],'residual compute limit')
    fragment_codes=resolve_fragments(groups,cuts,line,grid['west'],grid['north'],step,w,h,eligible,max_cells=lim['max_residual_cells'],side_codes=side_codes)
    offsets=array('I',[0]);count=0
    with (out/'direct-spans.u32le').open('xb') as f:
        for y in range(h):
            if y%64==0:guard()
            parts=[(int(a),int(b),int(k)) for a,b,k in graph.row(y)]
            parts += [(int(a),int(b),fragment_codes[int(k)]) for a,b,k in remaining.row(y)]
            parts.sort();merged=[]
            for a,b,k in parts:
                need(0<=a<b<=w and (not merged or merged[-1][1]<=a),'overlapping split output')
                if merged and merged[-1][1]==a and merged[-1][2]==k:merged[-1]=(merged[-1][0],b,k)
                else:merged.append((a,b,k))
            def coverage(intervals):
                result=[]
                for a,b in intervals:
                    if result and result[-1][1]==a:result[-1]=(result[-1][0],b)
                    else:result.append((a,b))
                return result
            need(coverage([(a,b) for a,b,_ in merged])==coverage(rows(y)),'component coverage mismatch')
            for a,b,k in merged:f.write(struct.pack('<III',a,b,k))
            count+=len(merged);need(count<=0xffffffff,'offset overflow');offsets.append(count)
        f.flush();os.fsync(f.fileno())
    with (out/'direct-rows.u32le').open('xb') as f:
        f.write(np.asarray(offsets,dtype='<u4').tobytes());f.flush();os.fsync(f.fileno())
    components.close();graph.close();remaining.close()
    direct=TripleRows(out/'direct-rows.u32le',out/'direct-spans.u32le',h,max_width=w);verify_witness_assignments(direct,checks);direct.close()
    need({p.name:digest(p,guard) for p in graphpaths}==graphhash,'intermediate graph changed')
    for name,p in paths.items():need(digest(p,guard)==inputs[name]['sha256'],'input changed: '+name)
    need(bounded(request,1<<20)==raw and {p.name:digest(p,guard) for p in codepaths}==codehash,'request or code changed')
    report={'schema':'direct-source-split-report-v1','status':'experimental-not-selected','publishable':False,'input_sha256':{k:v['sha256'] for k,v in inputs.items()},'request_sha256':hashlib.sha256(raw).hexdigest(),'code_sha256':codehash,'boundary_sha256':info['boundary_sha256'],'boundary_lineage_status':info['boundary_lineage_status'],'grid':grid,'component_id_current_generation_only':root,'selected_cells':result['selected_cells'],'residual_cells':residual,'direct_rows_sha256':digest(out/'direct-rows.u32le',guard),'direct_spans_sha256':digest(out/'direct-spans.u32le',guard),'elapsed_seconds':time.monotonic()-started,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'limitations':['Nearest-segment residual side is experimental, not proven generally.','Requires independent full-output equality and end-to-end benchmark before any switch.','Pinned snapshots are not authenticated by hashes.']}
    pending=out/'report.pending';final=out/'report.json';linked=False
    try:
        fd=os.open(out,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
        with pending.open('x') as f:json.dump(report,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
        os.link(pending,final);linked=True
        fd=os.open(out,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
        pending.unlink()
        fd=os.open(out,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
    except OSError as exc:
        if linked or final.exists():raise RuntimeError('report marker may exist; inspect before retry') from exc
        raise
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('request');p.add_argument('output');a=p.parse_args()
    try:print(json.dumps(run(a.request,a.output)))
    except Exception as e:raise SystemExit('error: '+str(e))

