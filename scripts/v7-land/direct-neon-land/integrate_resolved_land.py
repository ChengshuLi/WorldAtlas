#!/usr/bin/env python3
"""Research adapter: resolved direct rules + rendered seeds + nearest claims.

The input rules config must be produced by the validated direct resolver in the
same orchestration. This standalone research wrapper cannot authenticate that
provenance; never treat a local config or snapshot status as approval.
"""
import hashlib,json,math,os,sys
from pathlib import Path
import derive_mainland_seed as seed
import nearest_mainland as nearest

DIRECT=Path(__file__).resolve().parent
sys.path.insert(0,str(DIRECT));import assign_land_stream as stream

def require(ok,msg):
    if not ok:raise ValueError(msg)

def verify_cut_evidence(snapshot,resolution,policy):
    """Verify pinned source line bytes; never infer sides or create polygons."""
    ids=policy.get('source_cut_feature_ids')
    require(isinstance(ids,list) and all(isinstance(x,str) and x.strip() for x in ids) and len(set(ids))==len(ids),'invalid cut evidence IDs')
    features=snapshot.get('features',[]); sources=snapshot.get('sources',[]); mappings=resolution.get('source_files',[])
    feature_map={x.get('feature_id'):x for x in features}; source_map={(x.get('source_id'),x.get('version')):x for x in sources}; maps={(x.get('source_id'),x.get('source_version')):x for x in mappings}
    require(len(feature_map)==len(features) and len(source_map)==len(sources) and len(maps)==len(mappings),'ambiguous cut evidence catalogs')
    docs={};result=[]
    for fid in ids:
        feature=feature_map.get(fid);require(isinstance(feature,dict),'unknown cut feature')
        key=(feature.get('source_id'),feature.get('source_version'));source=source_map.get(key);mapping=maps.get(key)
        require(source is not None and mapping is not None and mapping['file']['sha256']==source.get('sha256'),'cut source not pinned in resolver')
        nearest.pin(mapping['file']);path=mapping['file']['path']
        if path not in docs:
            doc=json.loads(Path(path).read_bytes());require(doc.get('type')=='FeatureCollection' and isinstance(doc.get('features'),list),'invalid cut source collection');docs[path]=doc['features']
        field=mapping.get('id_property');require(isinstance(field,str) and bool(field),'cut source ID property missing')
        hits=[f for f in docs[path] if f.get('type')=='Feature' and isinstance(f.get('properties'),dict) and field in f['properties'] and str(f['properties'][field])==str(feature.get('source_feature_id'))]
        require(len(hits)==1,'cut source feature ID not unique')
        geom=hits[0].get('geometry');require(isinstance(geom,dict) and geom.get('type') in ('LineString','MultiLineString'),'cut evidence must be a source line')
        lines=[geom.get('coordinates')] if geom['type']=='LineString' else geom.get('coordinates');require(isinstance(lines,list) and bool(lines),'empty cut geometry')
        for line in lines:
            require(isinstance(line,list) and len(line)>=2,'invalid cut line')
            previous=None
            for p in line:
                require(isinstance(p,list) and len(p)==2 and all(type(v) in (int,float) and math.isfinite(v) for v in p) and -180<=p[0]<=180 and -90<=p[1]<=90,'invalid cut coordinate')
                require(previous is None or abs(p[0]-previous)<=180,'unsplit cut antimeridian edge');previous=p[0]
        gh=hashlib.sha256(json.dumps(geom,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
        require(gh==feature.get('geometry_sha256'),'cut geometry digest mismatch')
        result.append({'feature_id':fid,'source_id':key[0],'source_version':key[1],'source_file_sha256':mapping['file']['sha256'],'geometry_sha256':gh})
    return result

def build(request_path,output,allow=False):
    require(allow,'explicit unverified research mode required')
    code_files=[Path(__file__).resolve(),Path(seed.__file__).resolve(),Path(nearest.__file__).resolve(),DIRECT/'compile_land.py',DIRECT/'assign_land_stream.py',DIRECT.parent/'assign_land.py',Path(nearest.__file__).parent/'tile_index.py',Path(nearest.__file__).parent/'distance_kernel.cpp',DIRECT.parent/'build_components.cpp']
    code_hashes={str(p):nearest.sha(p) for p in code_files}
    raw=Path(request_path).read_bytes(); req=json.loads(raw)
    required={'schema','snapshot','compiler_config','resolution_report','workers','strip_rows'}
    require(required<=set(req)<=required|{'component_manifest'} and req['schema']=='resolved-land-nearest-adapter-v1','invalid adapter request')
    require(type(req['workers']) is int and 1<=req['workers']<=8 and type(req['strip_rows']) is int and 1<=req['strip_rows']<=1024,'invalid execution settings')
    for k in ('snapshot','compiler_config','resolution_report'):nearest.pin(req[k])
    snap=json.loads(Path(req['snapshot']['path']).read_bytes());cfg=json.loads(Path(req['compiler_config']['path']).read_bytes());rr=json.loads(Path(req['resolution_report']['path']).read_bytes())
    require(rr.get('schema')=='direct-land-explicit-resolution-v1' and rr.get('status')=='research-partial-no-land-grid' and rr.get('snapshot_sha256')==req['snapshot']['sha256'] and rr.get('compiler_config_sha256')==req['compiler_config']['sha256'] and Path(rr.get('compiler_config_path','')).resolve()==Path(req['compiler_config']['path']).resolve() and rr.get('grid')==cfg.get('grid') and rr.get('decision_revision')==cfg.get('decision_revision') and rr.get('decision_revision_asserted_status')==cfg.get('revision_status'),'resolver report/config mismatch')
    require(rr.get('program_sha256')==nearest.sha(DIRECT/'compile_land.py') and rr.get('shared_backend_sha256')==nearest.sha(DIRECT.parent/'assign_land.py') and rr.get('component_source_sha256')==nearest.sha(DIRECT.parent/'build_components.cpp'),'resolver code mismatch')
    require(rr.get('explicit_root_count')==len(cfg.get('rules',[])) and rr.get('input_pins',{}).get('snapshot')==req['snapshot'],'resolver input mismatch')
    require(rr.get('gdal_version')==seed.gdal.VersionInfo('--version') and rr.get('numpy_version')==seed.np.__version__,'resolver/seed runtime versions differ')
    for k in ('physical_rows','physical_runs','component_rows','component_runs'):require(rr.get('input_pins',{}).get(k)==cfg.get(k),'resolver physical/component mismatch')
    require(isinstance(rr.get('source_files'),list),'invalid resolver source files')
    for source in rr['source_files']:nearest.pin(source['file'])
    manifest=req.get('component_manifest')
    if manifest is None:require(rr.get('component_generation_method')=='independent-recompute' and rr.get('component_manifest_sha256') is None,'resolver component generation mismatch')
    else:
        nearest.pin(manifest);require(rr.get('component_generation_method')=='single-generation-manifest' and rr.get('component_manifest_sha256')==manifest['sha256'] and Path(rr.get('component_manifest_path','')).resolve()==Path(manifest['path']).resolve(),'resolver component manifest mismatch')
    pol=snap.get('land_mainland_policy');require(isinstance(pol,dict) and pol.get('execution_status')=='selected_for_research','selected research mainland policy required')
    cut_evidence=verify_cut_evidence(snap,rr,pol)
    roots=set(pol.get('mainland_component_ids',[]));require(bool(roots),'missing mainland components')
    bindings={b['entity_id']:b['code'] for b in snap.get('category_bindings',[]) if b.get('physical_class')=='land'}
    explicit={};ids=set()
    for r in cfg.get('rules',[]):
        root=r.get('component_id');rid=r.get('rule_id')
        require(type(root) is int and root>=0 and root not in explicit and isinstance(rid,str) and rid and rid not in ids,'duplicate or invalid explicit rule');explicit[root]=r;ids.add(rid)
    require(roots<=explicit.keys(),'mainland root has no explicit rule')
    mixed=any(r.get('kind')=='polygon_partition' and len({p.get('code') for p in r.get('parts',[])})>1 for root,r in explicit.items() if root in roots)
    require(not mixed or bool(cut_evidence),'mixed-continent mainland partition requires pinned cut evidence')
    # The nearest policy's exemptions must match the actual resolved rules,
    # so an implicit or stale island override cannot slip into the pipeline.
    claims=pol.get('reviewed_component_claims');require(isinstance(claims,list),'invalid reviewed component list')
    policy_claims={}
    for c in claims:
        require(isinstance(c,dict) and set(c)=={'rule_id','component_id','entity_id'} and c.get('entity_id') in bindings and type(c.get('component_id')) is int and c['component_id'] not in policy_claims,'invalid or duplicate reviewed claim')
        policy_claims[c['component_id']]=c
    outside={root:r for root,r in explicit.items() if root not in roots}
    require(set(policy_claims)==set(outside),'resolved reviewed components differ from policy exemptions')
    for root,r in outside.items():
        c=policy_claims[root];require(r.get('kind')=='whole_component' and r.get('rule_id')==c.get('rule_id') and r.get('code')==bindings[c['entity_id']],'reviewed component rule conflicts with policy')
    out=Path(output).resolve();inputs=[Path(request_path).resolve(),Path(req['snapshot']['path']).resolve(),Path(req['compiler_config']['path']).resolve(),Path(req['resolution_report']['path']).resolve()]+([Path(manifest['path']).resolve()] if manifest is not None else [])
    for k in ('physical_rows','physical_runs','component_rows','component_runs'):
        nearest.pin(cfg[k]);inputs.append(Path(cfg[k]['path']).resolve())
    require(not out.exists() and all(not p.is_relative_to(out) and not out.is_relative_to(p.parent) for p in inputs),'output overlaps an input directory')
    out.mkdir(mode=0o700);conf=out/'configs';conf.mkdir()
    sc={'schema':'resolved-mainland-seed-v1','snapshot':req['snapshot'],'compiler_config':req['compiler_config'],'strip_rows':req['strip_rows']}
    sp=conf/'seed.json';sp.write_text(json.dumps(sc,sort_keys=True,separators=(',',':'))+'\n')
    sr=seed.build(sp,out/'mainland-seed')
    require(sr['rows_sha256']==pol.get('mainland_rows_sha256') and sr['runs_sha256']==pol.get('mainland_runs_sha256'),'resolved mainland seed differs from policy pins')
    cpins={k:cfg[k] for k in ('physical_rows','physical_runs','component_rows','component_runs')}
    nc={'schema':'nearest-mainland-build-v1','snapshot':req['snapshot'],'grid':cfg['grid'],**cpins,'mainland_rows':{'path':str(out/'mainland-seed'/'rows.u32le'),'sha256':sr['rows_sha256']},'mainland_runs':{'path':str(out/'mainland-seed'/'runs.u32le'),'sha256':sr['runs_sha256']},'workers':req['workers']}
    np=conf/'nearest.json';np.write_text(json.dumps(nc,sort_keys=True,separators=(',',':'))+'\n')
    nr=nearest.build(np,out/'nearest',True,component_manifest=manifest)
    merged=dict(cfg);merged['rules']=list(cfg['rules'])
    for claim in nr['nearest_claims']:
        root=claim['component_id'];code=claim['code'];rid=f'nearest-mainland:component:{root}'
        require(root not in explicit and rid not in ids and type(code) is int and 17<=code<=22,'nearest claim overlaps explicit rule')
        ids.add(rid);merged['rules'].append({'component_id':root,'rule_id':rid,'source_evidence':['selected nearest-mainland policy '+req['snapshot']['sha256']],'kind':'whole_component','code':code})
    merged['rules'].sort(key=lambda r:r['component_id']);mp=conf/'merged.json';mp.write_text(json.dumps(merged,sort_keys=True,separators=(',',':'))+'\n')
    land=stream.build(mp,out/'land')
    for p in [req['snapshot'],req['compiler_config'],req['resolution_report'],*cpins.values(),*[source['file'] for source in rr['source_files']],*([manifest] if manifest is not None else [])]:nearest.pin(p)
    require(Path(request_path).read_bytes()==raw,'adapter request changed')
    require({str(p):nearest.sha(p) for p in code_files}==code_hashes,'adapter code changed during build')
    result={'schema':'resolved-land-nearest-adapter-report-v1','status':'unverified-research-not-published','request_sha256':hashlib.sha256(raw).hexdigest(),'snapshot_sha256':req['snapshot']['sha256'],'compiler_config_sha256':req['compiler_config']['sha256'],'resolution_report_sha256':req['resolution_report']['sha256'],'code_sha256':code_hashes,'verified_cut_evidence':cut_evidence,'seed_report_sha256':nearest.sha(out/'mainland-seed'/'report.json'),'nearest_claims_sha256':nearest.sha(out/'nearest'/'claims.json'),'merged_config_sha256':nearest.sha(mp),'land_report_sha256':nearest.sha(out/'land'/'report.json'),'output_rows_sha256':land['output_rows_sha256'],'output_runs_sha256':land['output_runs_sha256'],'limitation':'No authentication of local resolver config or snapshot. Requires a validated same-run direct resolver and reviewed mainland decisions. No prior continent grid was read.'}
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('request');p.add_argument('output');p.add_argument('--allow-unverified-snapshot',action='store_true');a=p.parse_args()
    try:print(json.dumps(build(a.request,a.output,a.allow_unverified_snapshot),indent=2))
    except Exception as e:print(f'error: {e}',file=sys.stderr);raise SystemExit(1)
