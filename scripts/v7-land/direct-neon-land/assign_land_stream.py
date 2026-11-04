#!/usr/bin/python3
"""Research candidate: stream physical/component runs into continent RLE.

Same component-rule semantics as the prototype compiler, but no whole-world
cell arrays for ordinary components. Partition rasters use full-width strips
to preserve boundary behavior, while hit and label arrays use component extents. Not a production replacement without review.
"""
import hashlib,json,math,os,sys
from pathlib import Path
import numpy as np
from osgeo import gdal
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import assign_land as base

gdal.UseExceptions()
SENTINEL=0xffffffff


def build(cfg_path,output):
    cb=Path(cfg_path).read_bytes();cfg=json.loads(cb)
    base.keys(cfg,('schema','decision_revision','revision_status','provenance_note','grid','physical_rows','physical_runs','component_rows','component_runs','strip_rows','rules'),'config')
    if cfg.get('schema')!='land-decision-compiler-prototype-v1':raise ValueError('unknown schema')
    if not cfg.get('decision_revision') or cfg.get('revision_status') not in ('draft','accepted') or not cfg.get('provenance_note'):raise ValueError('decision metadata required')
    g=cfg['grid'];base.keys(g,('width','height','step','west','north'),'grid');w,h,step=g['width'],g['height'],g['step']
    if not isinstance(w,int) or not isinstance(h,int) or w<=0 or h<=0 or not all(math.isfinite(v) for v in (step,g['west'],g['north'])) or not 0<step<=360 or g['west'] < -180 or g['west']+w*step>180.0000001 or g['north']>90 or g['north']-h*step< -90.0000001:raise ValueError('invalid grid')
    source=[base.pin(cfg[k]) for k in ('physical_rows','physical_runs','component_rows','component_runs')]
    pr,pv,cr,cv=[np.memmap(x,dtype='<u4',mode='r') for x in source]
    if len(pr)!=h+1 or len(cr)!=h+1 or pr[0]!=0 or cr[0]!=0 or len(pv)%2 or len(cv)%3 or pr[-1]!=len(pv)//2 or cr[-1]!=len(cv)//3 or np.any(pr[1:]<pr[:-1]) or np.any(cr[1:]<cr[:-1]):raise ValueError('invalid input offsets or lengths')
    pv=pv.reshape(-1,2);cv=cv.reshape(-1,3)
    rules={};partition={};opened=[];ids=set()
    for rule in cfg['rules']:
        base.keys(rule,('component_id','rule_id','source_evidence','kind','code','parts'),'rule')
        root=rule['component_id'];rid=rule.get('rule_id')
        if not isinstance(root,int) or not 0<=root<SENTINEL or not rid or not rule.get('source_evidence'):raise ValueError('every rule needs a component, ID and source evidence')
        if root in rules or rid in ids:raise ValueError('duplicate component or rule ID')
        ids.add(rid)
        if rule['kind']=='whole_component':
            if 'parts' in rule or rule['code'] not in range(17,23):raise ValueError('invalid whole component')
            rules[root]=rule['code']
        elif rule['kind']=='polygon_partition':
            if 'code' in rule or not rule.get('parts') or len(rule['parts'])>255:raise ValueError('invalid partition')
            pids=[p.get('part_id') for p in rule['parts']]
            if len(set(pids))!=len(pids):raise ValueError('duplicate part ID')
            rules[root]=0;parts=[]
            for p in rule['parts']:
                base.keys(p,('part_id','code','geometry'),'partition part')
                if p['code'] not in range(17,23) or not p.get('part_id'):raise ValueError('invalid partition part')
                ds,layer=base.polygon(p['geometry']);opened.append((ds,layer));parts.append((p['code'],layer,p['geometry']))
            partition[root]=parts
        else:raise ValueError('unknown rule kind')
    if not rules:raise ValueError('no rules')
    strip=cfg.get('strip_rows',128)
    if not isinstance(strip,int) or not 1<=strip<=1024:raise ValueError('invalid strip size')
    os.mkdir(output);out=Path(output);seen=set();offsets=[0];total_land=0
    with (out/'runs.u32le').open('xb') as stream:
        for y0 in range(0,h,strip):
            n=min(strip,h-y0);block=cv[int(cr[y0]):int(cr[y0+n])]
            active=set(int(x) for x in np.unique(block[:,2])) if len(block) else set()
            missing=active-rules.keys()
            if missing:raise ValueError(f'unassigned component IDs: {sorted(missing)[:20]}')
            # Rasterize full-width strips to preserve the baseline transform.
            # Keep hit/label arrays only over each active component's extent.
            values=np.zeros((n,w),dtype=np.uint8) if active & partition.keys() else None
            for root in active & partition.keys():
                selected=block[block[:,2]==root];x0=int(selected[:,0].min());x1=int(selected[:,1].max())
                hits=np.zeros((n,x1-x0),dtype=np.uint8);labels=np.zeros_like(hits)
                for code,layer,_ in partition[root]:
                    # Preserve the exact full-width affine transform used by the
                    # baseline. Re-origining at x0 changes GDAL's boundary-on-center
                    # rounding for non-binary steps, even when mathematically equal.
                    raster=gdal.GetDriverByName('MEM').Create('',w,n,1,gdal.GDT_Byte)
                    raster.SetGeoTransform((g['west'],step,0,g['north']-y0*step,0,-step));raster.GetRasterBand(1).Fill(0);layer.ResetReading()
                    gdal.RasterizeLayer(raster,[1],layer,burn_values=[1]);mask=raster.ReadAsArray()[:,x0:x1]!=0
                    hits[mask]+=1;labels[mask]=code
                for dy in range(n):
                    row=cv[int(cr[y0+dy]):int(cr[y0+dy+1])]
                    for start,end,rid in row[row[:,2]==root]:
                        lo,hi=int(start)-x0,int(end)-x0
                        if np.any(hits[dy,lo:hi]!=1):raise ValueError(f'partition gap or overlap on component {root} in rows {y0}:{y0+n}')
                        values[dy,int(start):int(end)]=labels[dy,lo:hi]
            for dy in range(n):
                y=y0+dy;physical=pv[int(pr[y]):int(pr[y+1])];components=cv[int(cr[y]):int(cr[y+1])]
                pi=0;ci=0;start=0;outends=[];outcodes=[]
                def emit(end,code):
                    if outcodes and outcodes[-1]==code:outends[-1]=end
                    else:outends.append(end);outcodes.append(code)
                for end,code in physical:
                    end,code=int(end),int(code)
                    if end<=start or end>w or code not in (1,17):raise ValueError(f'invalid physical row {y}')
                    if code==1:
                        if ci<len(components) and int(components[ci,0])<end:raise ValueError(f'physical/component footprint mismatch row {y}')
                        emit(end,1)
                    else:
                        pos=start
                        while pos<end:
                            if ci>=len(components):raise ValueError(f'physical/component footprint mismatch row {y}')
                            a,b,root=map(int,components[ci])
                            if a!=pos or b<=a or b>end or root==SENTINEL:raise ValueError(f'physical/component footprint mismatch row {y}')
                            seen.add(root);total_land+=b-a
                            if root not in rules:raise ValueError(f'unassigned component ID: {root}')
                            value=rules[root]
                            if value:emit(b,value)
                            else:
                                v=values[dy,a:b]
                                if np.any(v==0):raise ValueError('unassigned land remains')
                                changes=np.flatnonzero(np.r_[v[1:]!=v[:-1],True])
                                for z in changes:emit(a+int(z)+1,int(v[z]))
                            pos=b;ci+=1
                    start=end
                if start!=w or ci!=len(components):raise ValueError(f'incomplete or mismatched row {y}')
                pairs=np.column_stack((outends,outcodes)).astype('<u4');pairs.tofile(stream);offsets.append(offsets[-1]+len(outends))
                if offsets[-1]>np.iinfo(np.uint32).max:raise ValueError('too many runs')
    unused=set(rules)-seen
    if unused:raise ValueError(f'rules reference absent component IDs: {sorted(unused)[:20]}')
    np.asarray(offsets,dtype='<u4').tofile(out/'rows.u32le')
    if Path(cfg_path).read_bytes()!=cb:raise ValueError('config changed during build')
    for k in ('physical_rows','physical_runs','component_rows','component_runs'):base.pin(cfg[k])
    for parts in partition.values():
        for _,_,entry in parts:base.pin(entry)
    (out/'config.json').write_bytes(cb)
    report={'schema':'land-streaming-research-report-v1','status':'experimental-not-published','decision_revision':cfg['decision_revision'],'revision_status':cfg['revision_status'],
            'config_sha256':hashlib.sha256(cb).hexdigest(),'program_sha256':base.sha(__file__),'gdal_version':gdal.VersionInfo('--version'),'numpy_version':np.__version__,
            'input_sha256':{k:cfg[k]['sha256'] for k in ('physical_rows','physical_runs','component_rows','component_runs')},'land_cells':total_land,'components':len(seen),
            'output_rows_sha256':base.sha(out/'rows.u32le'),'output_runs_sha256':base.sha(out/'runs.u32le'),
            'limitations':'Prototype; component connectivity, geographic decisions and real global equivalence require independent verification.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('usage: assign_land_stream.py CONFIG NEW_OUTPUT_DIR')
    try:print(json.dumps(build(sys.argv[1],sys.argv[2]),indent=2))
    except Exception as e:print(f'error: {e}',file=sys.stderr);raise SystemExit(1)
