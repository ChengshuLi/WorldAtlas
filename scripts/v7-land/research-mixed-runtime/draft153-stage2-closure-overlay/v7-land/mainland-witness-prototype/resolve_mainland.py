#!/usr/bin/env python3
"""Resolve selected, source-backed mainland witness groups on the current physical grid.

Research prototype. Current component IDs are ephemeral output, never portable policy.
This does not construct region boundaries, classify islands, or write a map or DB.
"""
import argparse, bisect, hashlib, importlib.util, itertools, json, os, re, tempfile
from decimal import Decimal, ROUND_FLOOR
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parent
HELPER=REPO/'point-component-prototype'/'resolve.py'
NAMED=REPO/'named-identity-prototype'/'named_identity.py'
WATCH=REPO/'named-identity-prototype'/'identity_watch.py'
spec=importlib.util.spec_from_file_location('point_component_helpers',HELPER)
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
need=helper.need

def text(v): return isinstance(v,str) and bool(v.strip())

def locate_component(components, starts, x):
    i=bisect.bisect_right(starts,x)-1
    return components[i][2] if i>=0 and x<components[i][1] else None
def unique(items,key):
    need(isinstance(items,list),'required array missing'); out={}
    for x in items:
        need(isinstance(x,dict) and text(x.get(key)) and x[key] not in out,'missing or duplicate '+key);out[x[key]]=x
    return out

def resolve(req):
    need(req.get('schema')=='mainland-witness-request-v1','invalid request')
    codepaths={'resolver':Path(__file__).resolve(),'helper':HELPER.resolve(),'named_identity':NAMED.resolve(),'identity_watch':WATCH.resolve()}
    code={k:helper.digest(p) for k,p in codepaths.items()}
    need(req.get('code_sha256')==code,'code pin mismatch')
    refs={k:helper.pinned(req[k]) for k in ('snapshot','physical_rows','physical_runs','component_rows','component_runs','component_manifest','component_source')}
    grid=req.get('grid');need(isinstance(grid,dict) and set(grid)=={'width','height','west','north','step'},'invalid grid')
    w,h=grid['width'],grid['height'];step=helper.finite_decimal(grid['step']);west=helper.finite_decimal(grid['west']);north=helper.finite_decimal(grid['north'])
    need(type(w) is int and type(h) is int and w>0 and h>0 and west==Decimal(-180) and north==Decimal(90) and step>0 and Decimal(w)*step==Decimal(360) and Decimal(h)*step<=Decimal(180),'invalid global grid')
    manifest=json.loads(helper.read_bounded(refs['component_manifest'],'component manifest'))
    need(manifest.get('schema')=='single-generation-component-manifest-v1','current independent component generation required')
    mode,lineage_pins,lineage_paths=helper.validate_lineage(manifest,req,grid)
    for k in ('physical_rows','component_rows'):need(refs[k].stat().st_size==(h+1)*4,'row file size mismatch')
    for k,m in (('physical_runs',8),('component_runs',12)):need(refs[k].stat().st_size % m==0,'run alignment error')
    snap=json.loads(helper.read_bounded(refs['snapshot'],'snapshot'))
    rev,entity_rev=snap.get('decision_revision',{}),snap.get('entity_revision',{})
    need(snap.get('schema')=='worldatlas-geography-decision-draft-evidence-v1' and snap.get('source')=='neon-export' and rev.get('status')=='draft' and entity_rev.get('status')=='draft' and text(rev.get('id')) and text(entity_rev.get('id')) and rev.get('entity_revision')==entity_rev.get('id'),'draft Neon revision required')
    groups=unique(snap.get('mainland_witness_groups'),'group_id');witnesses=unique(snap.get('mainland_witnesses'),'witness_id');relations=unique(snap.get('mainland_group_relations'),'relation_id');features=unique(snap.get('features'),'feature_id')
    need(groups and witnesses and len(groups)<=64 and len(witnesses)<=512 and len(relations)<=2016,'empty or oversized selected groups, witnesses or relations')
    entities={}
    for e in snap.get('entities',[]):
        need(isinstance(e,dict) and type(e.get('id')) is int and e['id'] not in entities and text(e.get('name')),'invalid entity');entities[e['id']]=e
    bindings=snap.get('category_bindings');need(isinstance(bindings,list),'category bindings required')
    assigned={};target_owner={};target_codes={}
    for gid,g in groups.items():
        need(set(g)=={'group_id','decision_revision','role','execution_status','target_entity_ids','witness_ids','rationale'} and g.get('decision_revision')==rev['id'] and text(g.get('rationale')) and g.get('execution_status')=='selected_for_research' and g.get('role') in ('mainland','sentinel') and isinstance(g.get('witness_ids'),list) and g['witness_ids'] and len(set(g['witness_ids']))==len(g['witness_ids']) and isinstance(g.get('target_entity_ids'),list) and len(set(g['target_entity_ids']))==len(g['target_entity_ids']),'invalid or unselected group')
        need((g['role']=='mainland' and bool(g['target_entity_ids']) and len(g['witness_ids'])>=2) or (g['role']=='sentinel' and not g['target_entity_ids']),'group target mismatch')
        for eid in g['target_entity_ids']:
            matching=[b for b in bindings if b.get('entity_id')==eid and b.get('physical_class')=='land' and type(b.get('code')) is int and b['code']>0]
            need(type(eid) is int and eid in entities and entities[eid].get('level')=='continent' and eid not in target_owner and len(matching)==1 and matching[0]['code'] not in target_codes.values(),'invalid or conflicting target entity')
            target_owner[eid]=gid;target_codes[eid]=matching[0]['code']
        for wid in g['witness_ids']:
            need(wid in witnesses and wid not in assigned,'orphan or multiply assigned witness');assigned[wid]=gid
    need(set(assigned)==set(witnesses),'unused witness')
    pairs=set()
    for r in relations.values():
        ids=r.get('group_ids');need(set(r)=={'relation_id','decision_revision','execution_status','relation','group_ids'} and r.get('decision_revision')==rev['id'] and r.get('execution_status')=='selected_for_research' and r.get('relation')=='different' and isinstance(ids,list) and len(ids)==2 and ids[0]!=ids[1] and all(x in groups for x in ids),'invalid different-group assertion')
        pair=tuple(sorted(ids));need(pair not in pairs,'duplicate assertion');pairs.add(pair)
    need(pairs==set(itertools.combinations(sorted(groups),2)),'incomplete different-group assertions')
    def keyed(rows):
        need(isinstance(rows,list),'source array required');out={}
        for x in rows:
            need(isinstance(x,dict) and text(x.get('source_id')) and text(x.get('version')),'invalid source identity');key=(x['source_id'],x['version']);need(key not in out,'duplicate source');out[key]=x
        return out
    sources=keyed(snap.get('sources'));assets=keyed(snap.get('source_lineage_assets'));file_specs=keyed(req.get('source_files'))
    deps=snap.get('source_lineage_dependencies');need(isinstance(deps,list),'source lineage dependencies required')
    required=set()
    for d in witnesses.values():
        need(set(d)=={'witness_id','decision_revision','method','execution_status','point_feature_id','identity_feature_id','point_name','identity_name','identity_class','id_property','identity_id_property','identity_name_property','identity_class_property','radius_cells','max_water_cells','rationale'} and d.get('decision_revision')==rev['id'] and d.get('method')=='source_point_named_region_v1' and d.get('execution_status')=='selected_for_research' and all(text(d.get(k)) for k in ('point_feature_id','identity_feature_id','point_name','identity_name','identity_class','id_property','identity_id_property','identity_name_property','identity_class_property','rationale')),'invalid or unselected witness')
        need(type(d.get('radius_cells')) is int and 0<=d['radius_cells']<=16 and type(d.get('max_water_cells')) is int and 0<=d['max_water_cells']<(2*d['radius_cells']+1)**2,'invalid sample policy')
        for field in ('point_feature_id','identity_feature_id'):
            f=features.get(d[field]);need(isinstance(f,dict) and text(f.get('source_feature_id')) and isinstance(f.get('geometry_sha256'),str) and re.fullmatch('[0-9a-f]{64}',f['geometry_sha256']),'invalid source feature');required.add((f.get('source_id'),f.get('source_version')))
    need(set(file_specs)==required,'source file set mismatch')
    files={}
    for key in required:
        s,a=sources.get(key),assets.get(key);need(isinstance(s,dict) and isinstance(a,dict) and a.get('kind')=='raw' and isinstance(a.get('provenance'),dict) and a['provenance'].get('representation')=='provider_original','only provider-original raw sources supported')
        need(all(text(a.get(k)) for k in ('source_uri','attribution','license_name','license_uri','provider','title','r2_bucket','r2_key','sha256')) and re.fullmatch('[0-9a-f]{64}',a['sha256']) and type(a.get('size_bytes')) is int and a['size_bytes']>0,'incomplete raw source metadata')
        need(all(s.get(k)==a.get(k) for k in ('sha256','r2_bucket','r2_key','size_bytes')) and file_specs[key].get('sha256')==a['sha256'] and not any(isinstance(d,dict) and (d.get('source_id'),d.get('version'))==key for d in deps),'source custody or lineage mismatch')
        files[key]=helper.pinned(file_specs[key]);need(files[key].stat().st_size==a['size_bytes'],'source size mismatch')
    wb=helper.read_bounded(WATCH,'identity watchdog code');watch=type('WitnessWatch',(),{})();exec(compile(wb,str(WATCH),'exec'),watch.__dict__)
    named_bytes=helper.read_bounded(NAMED,'named identity code')
    roots={};claims=[]
    for wid,d in sorted(witnesses.items()):
        pf,ident=features[d['point_feature_id']],features[d['identity_feature_id']];pk=(pf['source_id'],pf['source_version']);ik=(ident['source_id'],ident['source_version']);need(pk!=ik,'point and identity sources must be distinct')
        helper.need(helper.available_memory_kib()>=helper.MEMORY_FLOOR_KIB+224*1024,'insufficient memory headroom for source parsing')
        source=json.loads(helper.read_bounded(files[pk],'point source',1024*1024));need(source.get('type')=='FeatureCollection' and isinstance(source.get('features'),list),'invalid point source');point_crs=helper.source_crs(source)
        matches=[f for f in source['features'] if isinstance(f,dict) and isinstance(f.get('properties'),dict) and type(f['properties'].get(d['id_property'])) in (str,int) and str(f['properties'][d['id_property']])==pf['source_feature_id']]
        need(len(matches)==1,'point feature identity must be unique');f=matches[0];geom=f.get('geometry');need('crs' not in f and isinstance(geom,dict) and 'crs' not in geom and geom.get('type')=='Point' and isinstance(geom.get('coordinates'),list) and len(geom['coordinates'])==2 and f['properties'].get('name')==d['point_name'] and helper.geometry_sha(geom)==pf['geometry_sha256'],'point identity or geometry mismatch')
        checkspec={'method':'raw_named_polygon_contains_point_v1','identity_feature_id':ident['source_feature_id'],'identity_id_property':d['identity_id_property'],'identity_name_property':d['identity_name_property'],'identity_class_property':d['identity_class_property'],'identity_class_value':d['identity_class'],'identity_geometry_sha256':ident['geometry_sha256']}
        check=watch.run(named_bytes,{'identity_path':str(files[ik]),'identity_sha256':assets[ik]['sha256'],'point_geometry':geom,'island_identity':d['identity_name'],'spec':checkspec},helper.available_memory_kib)['result']
        lon,lat=map(helper.finite_decimal,geom['coordinates']);need(-180<=lon<180 and -90<=lat<=90,'point outside WGS84');gx=(lon-west)/step;gy=(north-lat)/step
        need(gx!=gx.to_integral_value() and gy!=gy.to_integral_value(),'point on grid boundary is ambiguous');x=int(gx.to_integral_value(rounding=ROUND_FLOOR));y=int(gy.to_integral_value(rounding=ROUND_FLOOR));radius=d['radius_cells'];need(0<=x<w and radius<=y<h-radius and 2*radius+1<=w,'witness neighborhood outside grid')
        observed=[];water=0;center=None
        for yy in range(y-radius,y+radius+1):
            physical=helper.readrow(refs['physical_rows'],refs['physical_runs'],yy,w,'physical');components=helper.readrow(refs['component_rows'],refs['component_runs'],yy,w,'component')
            land=[(a,b) for a,b,v in physical if v==17];spans=[]
            for a,b,_ in components:
                if spans and spans[-1][1]==a:spans[-1]=(spans[-1][0],b)
                else:spans.append((a,b))
            need(land==spans,'component row differs from physical land')
            starts=[a for a,_,_ in components]
            for raw_x in range(x-radius,x+radius+1):
                xx=raw_x%w;root=locate_component(components,starts,xx)
                if root is not None:observed.append(root)
                else:water+=1
                if yy==y and raw_x==x:center=root
        need(center is not None and set(observed)=={center} and water<=d['max_water_cells'],'witness neighborhood is water or ambiguous')
        gid=assigned[wid];roots.setdefault(gid,set()).add(center)
        claims.append({'witness_id':wid,'group_id':gid,'point_feature_id':d['point_feature_id'],'identity_feature_id':d['identity_feature_id'],'identity_check':check,'point_source_crs':point_crs,'row':y,'column':x,'radius_cells':radius,'water_cells':water})
    need(all(len(roots[g])==1 for g in groups),'same-group witness mismatch')
    resolved={g:next(iter(r)) for g,r in roots.items()}
    need(all(resolved[a]!=resolved[b] for a,b in pairs),'different-group witness mismatch')
    for k,p in refs.items():need(helper.digest(p)==req[k]['sha256'],'input changed during resolution')
    for pin,path in zip(lineage_pins,lineage_paths):need(helper.digest(path)==pin['sha256'],'component lineage changed during resolution')
    for k,p in files.items():need(helper.digest(p)==assets[k]['sha256'],'source changed during resolution')
    need({k:helper.digest(p) for k,p in codepaths.items()}==code,'resolver dependency changed')
    return {'schema':'mainland-witness-resolution-v1','status':'selected-research-identity-claims-not-mainland-proof','publishable':False,'decision_revision':rev['id'],'entity_revision':entity_rev['id'],'snapshot_sha256':req['snapshot']['sha256'],'component_manifest_sha256':req['component_manifest']['sha256'],'component_lineage_mode':mode,'grid':grid,'input_sha256':{k:req[k]['sha256'] for k in ('physical_rows','physical_runs','component_rows','component_runs')},'code_sha256':code,'groups':[{'group_id':gid,'role':groups[gid]['role'],'target_entity_ids':groups[gid]['target_entity_ids'],'targets':[{'entity_id':eid,'name':entities[eid]['name'],'category_code':target_codes[eid]} for eid in groups[gid]['target_entity_ids']],'component_id_current_generation_only':resolved[gid]} for gid in sorted(groups)],'witnesses':claims,'relations_checked':[{'relation_id':r['relation_id'],'group_ids':r['group_ids'],'relation':r['relation']} for r in sorted(relations.values(),key=lambda x:x['relation_id'])],'limitations':['Root IDs are ephemeral and valid only for these exact component streams.','Witnesses identify sampled points, not all component geography or absence of unintended land bridges.','Region cuts, coastline closures, provenance authentication and full mainland review remain independent requirements.']}


def main():
    p=argparse.ArgumentParser();p.add_argument('request');p.add_argument('output');a=p.parse_args();path=Path(a.request).resolve();raw=helper.read_bounded(path,'request');req=json.loads(raw);result=resolve(req);need(helper.read_bounded(path,'request')==raw,'request changed');result['request_sha256']=hashlib.sha256(raw).hexdigest();out=Path(a.output).resolve()
    manifest=json.loads(helper.read_bounded(req['component_manifest']['path'],'component manifest'))
    input_paths=[path,*[Path(req[k]['path']).resolve() for k in ('snapshot','physical_rows','physical_runs','component_rows','component_runs','component_manifest','component_source')],*[Path(x['path']).resolve() for x in req['source_files']],*[Path(x['path']).resolve() for x in helper.lineage_specs(manifest)],HELPER.resolve(),NAMED.resolve(),WATCH.resolve(),Path(__file__).resolve()]
    need(all(not out.is_relative_to(p.parent) for p in input_paths),'output overlaps input directory');payload=(json.dumps(result,sort_keys=True,indent=2)+'\n').encode();tmp=None
    linked=False
    try:
        with tempfile.NamedTemporaryFile(dir=out.parent,prefix='.mainland-witness-',delete=False) as f:tmp=f.name;f.write(payload);f.flush();os.fsync(f.fileno())
        os.link(tmp,out);linked=True
        fd=os.open(out.parent,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
        os.unlink(tmp);tmp=None
        fd=os.open(out.parent,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
    except Exception as e:
        if linked or out.exists():raise RuntimeError('witness report may exist; inspect before retry') from e
        if tmp is not None:
            try:os.unlink(tmp)
            except OSError:pass
        raise

if __name__=='__main__':
    try:main()
    except Exception as e:
        import sys
        print('error: '+str(e),file=sys.stderr);raise SystemExit(1)
