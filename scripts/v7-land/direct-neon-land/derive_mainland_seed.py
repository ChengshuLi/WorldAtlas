#!/usr/bin/env python3
"""Render explicitly resolved mainland rules to an auditable sparse seed RLE.

No geographic sides or cuts are inferred.  This is only a renderer, not an
independent authorization/lineage check on a supplied compiler config.
"""
import hashlib,json,math,os,sys
from pathlib import Path
import numpy as np
from osgeo import gdal

# Share precisely the polygon validation/raster convention used by the direct compiler.
BASE=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(BASE));import assign_land as base

gdal.UseExceptions()

def fail(ok,message):
    if not ok:raise ValueError(message)

def build(config_path,output):
    raw=Path(config_path).read_bytes(); c=json.loads(raw)
    fail(set(c)=={'schema','snapshot','compiler_config','strip_rows'},'invalid seed config')
    fail(c['schema']=='resolved-mainland-seed-v1','unknown seed schema')
    snapshot_path=base.pin(c['snapshot']); rules_path=base.pin(c['compiler_config'])
    snap=json.loads(Path(snapshot_path).read_bytes());cfg=json.loads(Path(rules_path).read_bytes())
    policy=snap.get('land_mainland_policy');fail(isinstance(policy,dict) and policy.get('execution_status')=='selected_for_research','selected research mainland policy required')
    rev=snap.get('decision_revision',{});entity=snap.get('entity_revision',{});schema=snap.get('schema')
    fail(snap.get('source')=='neon-export' and rev.get('entity_revision')==entity.get('id') and
         schema=='worldatlas-geography-decision-draft-evidence-v1' and rev.get('status')==entity.get('status')=='draft','mainland research policy requires draft snapshot')
    fail(cfg.get('schema')=='land-decision-compiler-prototype-v1' and cfg.get('decision_revision')==rev.get('id') and cfg.get('revision_status')==rev.get('status'),'compiler/snapshot revision mismatch')
    g=cfg.get('grid');fail(g==policy.get('grid') and isinstance(g,dict) and set(g)=={'width','height','step','west','north'},'seed grid mismatch')
    w,h,step=g['width'],g['height'],g['step'];fail(type(w) is int and type(h) is int and w>0 and h>0 and type(step) in (int,float) and math.isfinite(step) and step>0,'invalid grid')
    physicalpins=[cfg[k] for k in ('physical_rows','physical_runs','component_rows','component_runs')]
    for k in ('physical_rows','physical_runs','component_rows','component_runs'):
        fail(cfg[k]['sha256']==policy.get(k+'_sha256'),'policy/compiler input mismatch');base.pin(cfg[k])
    root_list=policy.get('mainland_component_ids');fail(isinstance(root_list,list) and root_list and all(type(x) is int and x>=0 for x in root_list) and len(set(root_list))==len(root_list),'invalid mainland root selection')
    roots=set(root_list);rules={};geom_paths=[];datasets=[]
    for rule in cfg.get('rules',[]):
        root=rule.get('component_id');fail(type(root) is int and root>=0 and root not in rules,'invalid or duplicate component rule');rules[root]=rule
    fail(roots<=rules.keys(),'mainland component lacks an explicit source rule')
    selected={x:rules[x] for x in roots};parts={};part_hits={};ids=set()
    for root,r in selected.items():
        fail(isinstance(r.get('rule_id'),str) and r['rule_id'] and r['rule_id'] not in ids and isinstance(r.get('source_evidence'),list) and r['source_evidence'],'mainland rule lacks source evidence');ids.add(r['rule_id'])
        if r.get('kind')=='whole_component':
            fail(set(r)=={'component_id','rule_id','source_evidence','kind','code'} and type(r['code']) is int and 17<=r['code']<=22,'invalid mainland whole-component rule')
        elif r.get('kind')=='polygon_partition':
            fail(set(r)=={'component_id','rule_id','source_evidence','kind','parts'} and isinstance(r['parts'],list) and r['parts'] and len(r['parts'])<=255,'invalid mainland partition')
            part_ids=set();pl=[]
            for p in r['parts']:
                fail(set(p)=={'part_id','code','geometry'} and isinstance(p['part_id'],str) and p['part_id'] and p['part_id'] not in part_ids and type(p['code']) is int and 17<=p['code']<=22,'invalid mainland partition part');part_ids.add(p['part_id'])
                ds,layer=base.polygon(p['geometry']); datasets.append(ds);geom_paths.append(p['geometry']);pl.append((p['part_id'],p['code'],layer));part_hits[(root,p['part_id'])]=0
            parts[root]=pl
        else:raise ValueError('unsupported mainland rule kind')
    cr=np.memmap(cfg['component_rows']['path'],dtype='<u4',mode='r');cv=np.memmap(cfg['component_runs']['path'],dtype='<u4',mode='r')
    fail(len(cv)%3==0 and len(cr)==h+1 and cr[0]==0 and cr[-1]==len(cv)//3 and np.all(cr[1:]>=cr[:-1]),'invalid component offsets');cv=cv.reshape(-1,3)
    strip=c['strip_rows'];fail(type(strip) is int and 1<=strip<=1024,'invalid strip size')
    out=Path(output).resolve();inputs=[Path(config_path).resolve(),Path(snapshot_path).resolve(),Path(rules_path).resolve()]+[Path(p['path']).resolve() for p in physicalpins+geom_paths]
    fail(not out.exists() and all(not p.is_relative_to(out) and not out.is_relative_to(p.parent) for p in inputs),'output overlaps an input directory')
    out.mkdir(mode=0o700);offsets=[0];seen=set();codes=set()
    with (out/'runs.u32le').open('xb') as stream:
        for y0 in range(0,h,strip):
            nr=min(strip,h-y0);block=cv[int(cr[y0]):int(cr[y0+nr])];active=set(map(int,np.unique(block[:,2])))&roots if len(block) else set();labels={}
            for root in active&parts.keys():
                selected_runs=block[block[:,2]==root];x0=int(selected_runs[:,0].min());x1=int(selected_runs[:,1].max());hit=np.zeros((nr,x1-x0),np.uint8);value=np.zeros_like(hit)
                for pid,code,layer in parts[root]:
                    # Match the final compiler's exact full-width affine origin.
                    raster=gdal.GetDriverByName('MEM').Create('',w,nr,1,gdal.GDT_Byte);raster.SetGeoTransform((g['west'],step,0,g['north']-y0*step,0,-step));raster.GetRasterBand(1).Fill(0)
                    layer.ResetReading();gdal.RasterizeLayer(raster,[1],layer,burn_values=[1]);mask=raster.ReadAsArray()[:,x0:x1]!=0;hit[mask]+=1;value[mask]=code
                    for dy in range(nr):
                        row=cv[int(cr[y0+dy]):int(cr[y0+dy+1])]
                        for a,b,_ in row[row[:,2]==root]:part_hits[(root,pid)]+=int(mask[dy,int(a)-x0:int(b)-x0].sum())
                labels[root]=(x0,hit,value)
            for dy in range(nr):
                y=y0+dy;row=cv[int(cr[y]):int(cr[y+1])];ends=[];vals=[];pos=0
                def emit(end,code):
                    if end==pos:return
                    if vals and vals[-1]==code:ends[-1]=end
                    else:ends.append(end);vals.append(code)
                for a,b,root in row:
                    a,b,root=int(a),int(b),int(root);fail(a>=pos and b>a and b<=w,'invalid component row')
                    if root not in roots:continue
                    emit(a,0);pos=a;seen.add(root)
                    if root not in parts:code=selected[root]['code'];emit(b,code);codes.add(code)
                    else:
                        x0,hit,value=labels[root];lo=a-x0;hi=b-x0
                        fail(np.all(hit[dy,lo:hi]==1),'mainland partition has a gap or overlap')
                        v=value[dy,lo:hi];cuts=np.flatnonzero(np.r_[v[1:]!=v[:-1],True])
                        for z in cuts:emit(a+int(z)+1,int(v[z]));codes.add(int(v[z]))
                    pos=b
                emit(w,0);fail(ends and ends[-1]==w,'incomplete seed row')
                np.column_stack((ends,vals)).astype('<u4').tofile(stream);offsets.append(offsets[-1]+len(ends));fail(offsets[-1]<=np.iinfo(np.uint32).max,'too many seed runs')
    fail(seen==roots,'mainland rule references absent component');fail(all(v>0 for v in part_hits.values()),'mainland partition part has no selected cells')
    fail(codes==set(range(17,23)),'mainland assignments do not cover all six codes')
    np.asarray(offsets,dtype='<u4').tofile(out/'rows.u32le')
    for p in physicalpins+geom_paths+[c['snapshot'],c['compiler_config']]:base.pin(p)
    fail(Path(config_path).read_bytes()==raw,'config changed during build')
    result={'schema':'resolved-mainland-seed-report-v1','status':'unverified-research-not-published','decision_revision':rev['id'],'snapshot_sha256':c['snapshot']['sha256'],'compiler_config_sha256':c['compiler_config']['sha256'],'rows_sha256':base.sha(out/'rows.u32le'),'runs_sha256':base.sha(out/'runs.u32le'),'mainland_components':sorted(roots),'part_cell_counts':{str(k):v for k,v in part_hits.items()},'limitation':'Only renders supplied explicit rules; independent source/revision authentication and same-run compiler handoff required.'}
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('usage: derive_mainland_seed.py CONFIG NEW_OUTPUT_DIR')
    try:print(json.dumps(build(sys.argv[1],sys.argv[2]),indent=2))
    except Exception as e:print(f'error: {e}',file=sys.stderr);raise SystemExit(1)
