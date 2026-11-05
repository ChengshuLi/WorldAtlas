#!/usr/bin/env python3
"""Research-only point-source to current physical-component resolver.

All geography, source selection, target, and island identity come from a pinned
Neon-export candidate. This tool only reports claims, never writes a map or DB.
"""
import argparse, hashlib, json, os, re, struct, tempfile, types
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from pathlib import Path

HEX = re.compile(r'^[0-9a-f]{64}$')
MEMORY_FLOOR_KIB = 1730151

def need(ok, message):
    if not ok: raise ValueError(message)

def text(x): return isinstance(x, str) and bool(x.strip())

def available_memory_kib():
    with open('/proc/meminfo') as f:
        for line in f:
            if line.startswith('MemAvailable:'):return int(line.split()[1])
    raise ValueError('cannot determine available memory')

def guard():
    need(available_memory_kib()>=MEMORY_FLOOR_KIB, 'available memory below safety floor')

def digest(path):
    guard();h=hashlib.sha256();count=0
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):
            h.update(block);count+=len(block)
            if count%(8*1024*1024)==0:guard()
    return h.hexdigest()

def read_bounded(path, label, limit=8*1024*1024):
    guard()
    with open(path, 'rb') as f: data=f.read(limit+1)
    need(len(data)<=limit, f'{label} exceeds bounded size')
    return data

def pinned(ref):
    need(isinstance(ref,dict) and text(ref.get('path')) and isinstance(ref.get('sha256'),str) and HEX.fullmatch(ref['sha256']), 'invalid file pin')
    path=Path(ref['path']); need(path.is_file() and digest(path)==ref['sha256'], 'file hash mismatch')
    return path

def finite_decimal(v):
    need(type(v) in (int,float,str), 'invalid coordinate')
    try: d=Decimal(str(v))
    except InvalidOperation: raise ValueError('invalid coordinate') from None
    need(d.is_finite(), 'nonfinite coordinate')
    return d

def source_crs(data):
    if 'crs' not in data:return 'RFC7946'
    crs=data['crs'];allowed={'urn:ogc:def:crs:OGC:1.3:CRS84','urn:ogc:def:crs:OGC::CRS84','OGC:CRS84'}
    need(isinstance(crs,dict) and set(crs)=={'type','properties'} and crs['type']=='name' and isinstance(crs['properties'],dict) and set(crs['properties'])=={'name'} and crs['properties']['name'] in allowed,'unsupported or ambiguous source CRS')
    return 'OGC:CRS84'

def geometry_sha(g):
    return hashlib.sha256(json.dumps(g,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()

def readrow(rows_path,runs_path,y,width,kind):
    with open(rows_path,'rb') as f:
        f.seek(y*4); data=f.read(8)
    need(len(data)==8, 'row offsets truncated'); a,b=struct.unpack('<II',data)
    size=8 if kind=='physical' else 12
    with open(runs_path,'rb') as f:
        need(b>=a and b-a<=width and b*size<=os.fstat(f.fileno()).st_size, 'invalid row offsets or excessive run count')
        guard()
        f.seek(a*size); data=f.read((b-a)*size)
    need(len(data)==(b-a)*size, 'run row truncated')
    vals=list(struct.iter_unpack('<II' if kind=='physical' else '<III',data))
    if kind=='physical':
        x=0; spans=[]
        for end,code in vals:
            need(x<end<=width and code in (1,17), 'invalid physical row')
            spans.append((x,end,code));x=end
        need(x==width, 'physical row not complete');return spans
    last=0
    for start,end,root in vals:
        need(last<=start<end<=width and root!=0xffffffff, 'invalid component row');last=end
    return vals

def lineage_specs(manifest):
    if manifest.get('schema')=='single-generation-component-manifest-v1':
        return [manifest.get('physical_report'),manifest.get('builder_binary')]
    if manifest.get('schema')=='simple-v2-land-report-v1':
        inputs=manifest.get('inputs',{});return [inputs.get(k) for k in ('physical_report','component_builder_binary','component_builder_source','spherical_report','spherical_checkpoint')]
    raise ValueError('unsupported component lineage report')

def checkpoint_header(path):
    guard()
    with open(path,'rb') as f:prefix=f.read(65536)
    i=prefix.find(b'"best":{');need(i>=0,'checkpoint header missing')
    try:obj=json.loads(prefix[:i]+b'"best":{}}}')
    except (ValueError,UnicodeDecodeError):raise ValueError('invalid checkpoint header') from None
    payload=obj.get('payload',{});need(payload.get('schema')=='simple-v2-query-checkpoint-v1' and isinstance(payload.get('identity'),dict),'invalid checkpoint identity')
    return payload

def validate_lineage(manifest,req,grid):
    kind=manifest.get('schema');specs=lineage_specs(manifest);paths=[pinned(x) for x in specs]
    if kind=='single-generation-component-manifest-v1':
        need(manifest.get('status')=='complete-research' and manifest.get('grid')==grid and manifest.get('component_source_sha256')==req['component_source']['sha256'], 'component manifest identity mismatch')
        for k in ('physical_rows','physical_runs','component_rows','component_runs'):need(manifest.get('pins',{}).get(k)==req[k], 'component manifest stream pin mismatch')
        need(manifest.get('builder_binary_sha256')==manifest['builder_binary']['sha256'] and text(manifest.get('compiler_version')) and text(manifest.get('builder_output')), 'invalid builder provenance')
        physical_report=paths[0];mode='single-generation-manifest'
    else:
        need(manifest.get('status')=='research-not-published' and manifest.get('grid')==grid and text(manifest.get('component_topology_provenance')), 'baseline component lineage mismatch')
        inputs=manifest.get('inputs',{})
        for k in ('physical_rows','physical_runs','component_rows','component_runs'):need(isinstance(inputs.get(k),dict) and inputs[k].get('sha256')==req[k]['sha256'],'baseline component stream pin mismatch')
        need(inputs.get('component_builder_source',{}).get('sha256')==req['component_source']['sha256'],'baseline component builder source mismatch')
        physical_report,builder,source,spherical_report,checkpoint=paths
        sr=json.loads(read_bounded(spherical_report,'spherical report'));need(sr.get('schema')=='simple-v2-land-report-v1' and sr.get('status')=='research-not-published' and sr.get('grid')==grid and sr.get('component_generation')=='independent-recompute' and sr.get('checkpoint_sha256')==inputs['spherical_checkpoint']['sha256'] and sr.get('component_builder_binary_sha256')==inputs['component_builder_binary']['sha256'] and sr.get('code_sha256',{}).get('build_components.cpp')==req['component_source']['sha256'],'prior component build provenance mismatch')
        for k in ('physical_rows','physical_runs'):need(sr.get('inputs',{}).get(k,{}).get('sha256')==req[k]['sha256'],'prior physical stream mismatch')
        cp=checkpoint_header(checkpoint);ci=cp['identity'];need(cp.get('next_row')==grid['height'] and cp.get('queries')==sr.get('queries') and ci.get('grid')==grid and ci.get('config_sha256')==sr.get('config_sha256') and ci.get('component_rows_sha256')==req['component_rows']['sha256'] and ci.get('component_runs_sha256')==req['component_runs']['sha256'] and ci.get('code_sha256',{}).get('build_components.cpp')==req['component_source']['sha256'],'prior checkpoint component identity mismatch')
        mode='wgs84-report-with-prior-independent-component-build'
    pp=json.loads(read_bounded(physical_report,'physical report'));outputs=pp.get('physical_output_sha256',pp.get('output_sha256',{}))
    need(pp.get('status')=='candidate-only' and pp.get('grid')==grid and outputs.get('rows.u32le')==req['physical_rows']['sha256'] and outputs.get('runs.u32le')==req['physical_runs']['sha256'], 'physical report does not bind inputs')
    return mode,specs,paths

def resolve(req):
    code_path=Path(__file__).resolve(); code_hash=digest(code_path)
    need(req.get('resolver_sha256')==code_hash, 'resolver code pin mismatch')
    need(req.get('schema')=='point-component-request-v1', 'invalid request schema')
    refs={k:pinned(req[k]) for k in ('snapshot','physical_rows','physical_runs','component_rows','component_runs','component_manifest','component_source')}
    g=req.get('grid');need(isinstance(g,dict) and type(g.get('width')) is int and type(g.get('height')) is int and g['width']>0 and g['height']>0, 'invalid grid')
    manifest=json.loads(read_bounded(refs['component_manifest'],'component manifest'))
    lineage_mode,lineage_pins,lineage_paths=validate_lineage(manifest,req,g)
    width,height=g['width'],g['height'];step=finite_decimal(g.get('step'));west=finite_decimal(g.get('west'));north=finite_decimal(g.get('north'))
    need(step>0 and west==Decimal(-180) and north==Decimal(90) and Decimal(width)*step==Decimal(360) and Decimal(height)*step<=Decimal(180), 'invalid global grid geometry')
    for k in ('physical_rows','component_rows'):need(refs[k].stat().st_size==(height+1)*4,'row file size mismatch')
    for k,m in (('physical_runs',8),('component_runs',12)):need(refs[k].stat().st_size%m==0,'run alignment error')
    raw_snap=json.loads(read_bounded(refs['snapshot'],'snapshot'));snapshot_schema=raw_snap.get('schema');adapter_path=Path(__file__).with_name('adapter.py').resolve();adapter_hash=None
    if snapshot_schema=='worldatlas-geography-decision-draft-evidence-v1':
        adapter_bytes=read_bounded(adapter_path,'adapter code');adapter_hash=hashlib.sha256(adapter_bytes).hexdigest();need(req.get('adapter_sha256')==adapter_hash,'adapter code pin mismatch')
        module=types.ModuleType('point_component_adapter');exec(compile(adapter_bytes,str(adapter_path),'exec'),module.__dict__);snap=module.adapt(raw_snap)
    else:
        snap=raw_snap;need(snap.get('schema')=='point-component-decision-snapshot-v1' and snap.get('source')=='neon-export' and snap.get('status')=='draft' and text(snap.get('revision')), 'draft Neon export required')
    need(not req.get('code_files'), 'extraction code execution is not supported')
    sources=snap.get('sources'); decisions=snap.get('decisions');assets=req.get('source_files')
    need(isinstance(sources,list) and isinstance(decisions,list) and decisions and isinstance(assets,list), 'missing sources or decisions')
    def keyed(items):
        out={}
        for it in items:
            need(isinstance(it,dict) and text(it.get('source_id')) and text(it.get('version')), 'invalid source identity')
            k=(it['source_id'],it['version']);need(k not in out,'duplicate source identity');out[k]=it
        return out
    source_map=keyed(sources);asset_map=keyed(assets);need(set(source_map)==set(asset_map), 'source file set mismatch')
    entities=snap.get('target_entities');need(isinstance(entities,list) and entities, 'target entities required');entity_map={}
    for e in entities:
        need(isinstance(e,dict) and type(e.get('id')) is int and text(e.get('name')) and e.get('physical_class')=='land' and e['id'] not in entity_map, 'invalid or duplicate target entity');entity_map[e['id']]=e
    files={}
    for key,s in source_map.items():
        need(text(s.get('uri')) and text(s.get('attribution')) and text(s.get('license')) and text(s.get('r2_bucket')) and text(s.get('r2_key')) and text(s.get('license_uri')) and text(s.get('provider')) and text(s.get('title')) and type(s.get('size_bytes')) is int and s['size_bytes']>0 and s.get('kind')=='raw' and isinstance(s.get('provenance'),dict) and s['provenance'].get('representation')=='provider_original' and isinstance(s.get('sha256'),str) and HEX.fullmatch(s['sha256']), 'incomplete or non-raw source metadata')
        a=asset_map[key];need(a.get('sha256')==s['sha256'],'source snapshot pin mismatch');files[key]=pinned(a);need(files[key].stat().st_size==s['size_bytes'], 'source size mismatch')
    seen_ids=set();seen_roots={};claims=[];named_bytes=None;named_hash=None;watch_module=None;watch_hash=None
    named_path=Path(__file__).resolve().parent.parent/'named-identity-prototype'/'named_identity.py';watch_path=named_path.with_name('identity_watch.py')
    for d in sorted(decisions,key=lambda v:v.get('affiliation_id','')):
        need(isinstance(d,dict) and text(d.get('affiliation_id')) and d['affiliation_id'] not in seen_ids, 'invalid or duplicate affiliation');seen_ids.add(d['affiliation_id'])
        need(d.get('method') in ('source_point_component_v1','source_point_named_region_component_v1') and d.get('execution_status')=='selected_for_research' and type(d.get('entity_id')) is int and text(d.get('island_identity')) and text(d.get('point_name')) and d['entity_id'] in entity_map, 'unselected or malformed decision')
        pk=(d.get('point_source_id'),d.get('point_source_version'));ik=(d.get('identity_source_id'),d.get('identity_source_version'))
        need(pk in files and ik in files and pk!=ik and text(d.get('source_feature_id')) and text(d.get('id_property')) and isinstance(d.get('geometry_sha256'),str) and HEX.fullmatch(d['geometry_sha256']), 'missing point or identity evidence')
        need(available_memory_kib()>=MEMORY_FLOOR_KIB+224*1024,'insufficient host memory headroom for point parsing')
        data=json.loads(read_bounded(files[pk],'point source',1024*1024));need(available_memory_kib()>=MEMORY_FLOOR_KIB+224*1024,'insufficient host memory headroom after point parsing');need(data.get('type')=='FeatureCollection' and isinstance(data.get('features'),list),'point source must be FeatureCollection');point_crs=source_crs(data)
        matches=[f for f in data['features'] if isinstance(f,dict) and isinstance(f.get('properties'),dict) and d['id_property'] in f['properties'] and f['properties'][d['id_property']] is not None and type(f['properties'][d['id_property']]) in (str,int) and str(f['properties'][d['id_property']])==d['source_feature_id']]
        need(len(matches)==1, 'point feature identity must be unique');f=matches[0];need('crs' not in f,'nested feature CRS unsupported');geom=f.get('geometry');need(isinstance(geom,dict) and 'crs' not in geom,'nested geometry CRS unsupported');need(geom.get('type')=='Point' and isinstance(geom.get('coordinates'),list) and len(geom['coordinates'])==2, '2D point required')
        need(geometry_sha(geom)==d['geometry_sha256'], 'point geometry hash mismatch'); need(f['properties'].get('name')==d['point_name'], 'point name mismatch')
        identity_check=None;identity_memory_monitor=None
        if d['method']=='source_point_named_region_component_v1':
            if watch_module is None:
                named_bytes=read_bounded(named_path,'named identity code');named_hash=hashlib.sha256(named_bytes).hexdigest();need(req.get('named_identity_sha256')==named_hash,'named identity code pin mismatch')
                watch_bytes=read_bounded(watch_path,'identity watchdog code');watch_hash=hashlib.sha256(watch_bytes).hexdigest();need(req.get('identity_watch_sha256')==watch_hash,'identity watchdog code pin mismatch')
                watch_module=types.ModuleType('identity_watch');exec(compile(watch_bytes,str(watch_path),'exec'),watch_module.__dict__)
            spec={'method':'raw_named_polygon_contains_point_v1','identity_feature_id':d.get('identity_source_feature_id'),'identity_id_property':d.get('identity_id_property'),'identity_name_property':d.get('identity_name_property'),'identity_class_property':d.get('identity_class_property'),'identity_class_value':d.get('identity_class_value'),'identity_geometry_sha256':d.get('identity_geometry_sha256')}
            worker_request={'identity_path':str(files[ik]),'identity_sha256':source_map[ik]['sha256'],'point_geometry':geom,'island_identity':d['island_identity'],'spec':spec}
            monitored=watch_module.run(named_bytes,worker_request,available_memory_kib);identity_check=monitored['result'];identity_memory_monitor=monitored['memory_monitor']
        lon,lat=map(finite_decimal,geom['coordinates']);need(-180<=lon<180 and -90<=lat<=90, 'point outside WGS84')
        gx=(lon-west)/step;gy=(north-lat)/step;need(gx!=gx.to_integral_value() and gy!=gy.to_integral_value(), 'point on grid boundary is ambiguous')
        x=int(gx.to_integral_value(rounding=ROUND_FLOOR));y=int(gy.to_integral_value(rounding=ROUND_FLOOR));need(0<=x<width and 0<=y<height,'point outside grid')
        physical=readrow(refs['physical_rows'],refs['physical_runs'],y,width,'physical')
        components=readrow(refs['component_rows'],refs['component_runs'],y,width,'component')
        land_ranges=[(a,b) for a,b,c in physical if c==17]; component_ranges=[]
        for a,b,_ in components:
            if component_ranges and component_ranges[-1][1]==a:component_ranges[-1]=(component_ranges[-1][0],b)
            else:component_ranges.append((a,b))
        need(land_ranges==component_ranges, 'component row differs from physical land')
        land=[v for a,b,v in physical if a<=x<b];hits=[r for a,b,r in components if a<=x<b]
        need(land==[17] and len(hits)==1,'point must resolve to exactly one physical land component');root=hits[0]
        need(root not in seen_roots, 'multiple or conflicting claims for component');seen_roots[root]=d['affiliation_id']
        claims.append({'affiliation_id':d['affiliation_id'],'method':d['method'],'entity_id':d['entity_id'],'entity_name':entity_map[d['entity_id']]['name'],'entity_code':entity_map[d['entity_id']].get('code'),'feature_id':d.get('feature_id'),'rationale':d.get('rationale'),'island_identity':d['island_identity'],'point_name':d['point_name'],'source_feature_id':d['source_feature_id'],'point_source':{'source_id':pk[0],'version':pk[1],'sha256':source_map[pk]['sha256'],'r2_bucket':source_map[pk]['r2_bucket'],'r2_key':source_map[pk]['r2_key'],'uri':source_map[pk]['uri'],'geometry_sha256':d['geometry_sha256']},'identity_source':{'source_id':ik[0],'version':ik[1],'sha256':source_map[ik]['sha256'],'r2_bucket':source_map[ik]['r2_bucket'],'r2_key':source_map[ik]['r2_key'],'uri':source_map[ik]['uri']},'identity_feature_id':d.get('identity_feature_id'),'identity_check':identity_check,'source_crs':{'point':point_crs,'identity':identity_check.get('identity_source_crs') if identity_check else None},'source_crs_scope':'collection_feature_geometry' if identity_check else None,'identity_memory_monitor':identity_memory_monitor,'grid_cell':{'x':x,'y':y},'component_id':root})
    for k in refs:need(digest(refs[k])==req[k]['sha256'], 'input changed during resolution')
    for spec,path in zip(lineage_pins,lineage_paths):need(digest(path)==spec['sha256'], 'component lineage changed during resolution')
    for key,p in files.items():need(digest(p)==source_map[key]['sha256'], 'source changed during resolution')
    need(digest(code_path)==code_hash, 'resolver code changed during resolution')
    if adapter_hash is not None:need(digest(adapter_path)==adapter_hash, 'adapter code changed during resolution')
    if named_hash is not None:need(digest(named_path)==named_hash and digest(watch_path)==watch_hash, 'named identity code changed during resolution')
    return {'schema':'source-point-component-report-v1','status':'research-only-not-a-build','revision':snap['revision'],'entity_revision':snap.get('entity_revision'),'snapshot_schema':snapshot_schema,'adapter_sha256':adapter_hash,'named_identity_sha256':named_hash,'identity_watch_sha256':watch_hash,'resolver_sha256':code_hash,'snapshot_sha256':req['snapshot']['sha256'],'component_manifest_sha256':req['component_manifest']['sha256'],'component_lineage_mode':lineage_mode,'component_source_sha256':req['component_source']['sha256'],'grid':g,'input_sha256':{k:req[k]['sha256'] for k in ('physical_rows','physical_runs','component_rows','component_runs')},'claims':claims,'limitations':['The export and semantic island-identity assertion are not authenticated by hashes.','Whole-grid component topology and source attribution require independent validation.','This report is not a build result or permission to publish.']}

def main():
    p=argparse.ArgumentParser();p.add_argument('request');p.add_argument('output');a=p.parse_args()
    request_path=Path(a.request).resolve();request=read_bounded(request_path,'request')
    req=json.loads(request);result=resolve(req);need(read_bounded(request_path,'request')==request,'request changed during resolution')
    result['request_sha256']=hashlib.sha256(request).hexdigest();out=Path(a.output).resolve()
    manifest=json.loads(read_bounded(req['component_manifest']['path'],'component manifest'))
    input_paths=[request_path,Path(__file__).resolve(),Path(__file__).with_name('adapter.py').resolve(),(Path(__file__).resolve().parent.parent/'named-identity-prototype'/'named_identity.py').resolve(),(Path(__file__).resolve().parent.parent/'named-identity-prototype'/'identity_watch.py').resolve()]+[Path(req[k]['path']).resolve() for k in ('snapshot','physical_rows','physical_runs','component_rows','component_runs','component_manifest','component_source')]+[Path(x['path']).resolve() for x in req['source_files']]+[Path(x['path']).resolve() for x in lineage_specs(manifest)]
    need(all(not out.is_relative_to(p.parent) for p in input_paths), 'output overlaps an input directory'); payload=(json.dumps(result,sort_keys=True,indent=2)+'\n').encode()
    tmp=None
    try:
        with tempfile.NamedTemporaryFile(dir=out.parent,prefix='.point-report-',delete=False) as f:
            tmp=f.name;f.write(payload);f.flush();os.fsync(f.fileno())
        os.link(tmp,out) # atomic publication; never replace an existing path
    finally:
        if tmp is not None:os.unlink(tmp)
if __name__=='__main__':main()
