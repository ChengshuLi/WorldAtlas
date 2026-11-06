"""Resolve selected source-defined group features to complete current components.

This does not access Neon or write a grid. The caller authenticates the policy,
code, line, physical lineage and source catalog, and supervises the run. The
archive extractor authenticates the ZIP and materialized shapefile members.
Point-to-polygon names and group conventions are interpreted source evidence,
not proof of island membership. Returned roots are generation-scoped only.
"""
import hashlib,math,re,zipfile
from pathlib import Path

def need(ok,msg):
    if not ok:raise ValueError(msg)

def file_sha(path,guard):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        while True:
            guard();b=f.read(1<<20)
            if not b:break
            h.update(b)
    return h.hexdigest()

def read_geonames(path,ids):
    """Extract exact Indonesian island point records; reject ambiguity."""
    need(isinstance(ids,set) and ids and all(isinstance(x,str) and re.fullmatch(r'[1-9][0-9]{0,15}',x) for x in ids),'invalid GeoNames IDs')
    out={}
    with zipfile.ZipFile(path) as z:
        members=[m for m in z.infolist() if m.filename=='ID.txt']
        need(len(members)==1 and not members[0].is_dir() and members[0].file_size<=64*1024*1024,'invalid GeoNames archive')
        with z.open(members[0]) as f:
            for raw in f:
                need(len(raw)<=1024*1024,'oversized GeoNames record')
                fields=raw.decode('utf-8','strict').rstrip('\r\n').split('\t')
                if not fields or fields[0] not in ids:continue
                need(len(fields)==19 and fields[0] not in out and fields[6:9]==['T','ISL','ID'] and fields[1], 'invalid GeoNames island record')
                try:lat=float(fields[4]);lon=float(fields[5])
                except ValueError:raise ValueError('invalid GeoNames coordinate') from None
                need(math.isfinite(lon) and math.isfinite(lat) and -180<=lon<180 and -90<=lat<=90,'invalid GeoNames coordinate')
                out[fields[0]]={'source_id':'geonames-country-id','source_feature_id':fields[0],'name':fields[1],'lon':lon,'lat':lat}
    need(set(out)==ids,'missing selected GeoNames witness');return out

def resolve_feature_windows(policy,region,grid,inputs,sources,*,extract,intersect,point_inside,component_at,guard):
    """Re-resolve all selected full source features, with fresh whole-root checks.

    `sources` maps each policy source ID to `{path, version, sha256}`; the OSM
    record also includes `shapefile`. `inputs` maps physical/component rows/runs
    to `{path,sha256}`. The injected functions are the caller-pinned production
    implementations and guard. No historical root list is accepted as input.
    Returns group windows, independently named anchor witnesses, and evidence.
    """
    need(isinstance(policy,dict) and isinstance(region,dict) and isinstance(grid,dict) and isinstance(inputs,dict) and isinstance(sources,dict) and all(callable(x) for x in (extract,intersect,point_inside,component_at,guard)),'invalid group resolver inputs')
    refs=policy.get('sources');need(isinstance(refs,list) and refs and len({x['source_id'] for x in refs})==len(refs),'invalid source catalog')
    for ref in refs:
        x=sources.get(ref['source_id']);need(isinstance(x,dict) and x.get('version')==ref['version'] and x.get('sha256')==ref['sha256'] and isinstance(x.get('path'),str),'source catalog identity mismatch')
        need(file_sha(x['path'],guard)==ref['sha256'],'source bytes mismatch')
    keys=('physical_rows','physical_runs','component_rows','component_runs')
    need(set(inputs)==set(keys) and all(isinstance(inputs[k],dict) and set(inputs[k])=={'path','sha256'} and file_sha(inputs[k]['path'],guard)==inputs[k]['sha256'] for k in keys),'physical input pin mismatch')
    ev=policy.get('evidence',{});need(inputs['component_rows']['sha256']==ev.get('component_rows_sha256') and inputs['component_runs']['sha256']==ev.get('component_runs_sha256'),'component generation mismatch')
    groups=[g for g in policy.get('regional_groups',[]) if g.get('mode') in ('complete_source_feature','independent_named_evidence_and_direct_satellite')]
    need(groups and all(type(g.get('target_code')) is int and g['target_code'] in (18,22) for g in groups),'invalid source groups')
    feature_ids=[f for g in groups for f in g.get('osm_feature_ids',[])];need(feature_ids and len(set(feature_ids))==len(feature_ids),'duplicate or missing group feature')
    pins=policy.get('source_feature_pins',[]);byid={x['source_feature_id']:x for x in pins};need(len(byid)==len(pins) and set(feature_ids)==set(byid),'source feature pin mismatch')
    osm=sources['osm-land-polygons-split-4326'];need(isinstance(osm.get('shapefile'),str),'missing source shapefile')
    need(all(byid[f]['source_id']=='osm-land-polygons-split-4326' and byid[f]['source_version']==osm['version'] for f in feature_ids),'wrong source feature version')
    specs=[{'source_feature_id':f,'geometry_sha256':byid[f]['geometry_sha256']} for f in feature_ids]
    loaded=extract(osm['path'],osm['shapefile'],osm['sha256'],specs,guard);need(isinstance(loaded,list) and len(loaded)==len(specs),'source extractor coverage mismatch')
    geometries={}
    for (geom,meta),spec in zip(loaded,specs):
        need(isinstance(meta,dict) and meta.get('source_feature_id')==spec['source_feature_id'] and meta.get('geometry_sha256')==spec['geometry_sha256'] and meta.get('source_sha256')==osm['sha256'],'source extraction identity mismatch')
        geometries[spec['source_feature_id']]=geom
    geo_ids={i for g in groups for i in g.get('geonames_ids',[])}|{w['id'] for g in groups for w in g.get('named_witnesses',[]) if w.get('source')=='geonames-country-id'}
    records=read_geonames(sources['geonames-country-id']['path'],geo_ids)
    small=set(policy.get('named_small_island_anchor_ids',[]));need(small<=geo_ids,'small-anchor source witness missing')
    official=set(policy.get('anchor_discovery',{}).get('official_reef_anchors',[]));windows=[];anchors={};trace=[]
    for group in groups:
        fids=group['osm_feature_ids'];witnesses=([{'source':'geonames-country-id','id':i} for i in group.get('geonames_ids',[])] or group.get('named_witnesses',[]));need(len(fids)==len(witnesses),'each selected source feature requires one named witness')
        members={}
        for fid,w in zip(fids,witnesses):
            if w.get('source')=='geonames-country-id':
                point=records[w['id']]; source=sources['geonames-country-id'];name=point['name'];lon=point['lon'];lat=point['lat'];is_anchor=w['id'] in small;source_feature=w['id']
            else:
                need(w.get('source')=='indonesia-big-national-gazetteer' and isinstance(w.get('name'),str) and w['name'] and isinstance(w.get('point_lon_lat'),list) and len(w['point_lon_lat'])==2,'invalid official witness');lon,lat=w['point_lon_lat'];need(all(type(v) in (int,float) and math.isfinite(v) for v in (lon,lat)),'invalid official coordinate');source=sources[w['source']];name=w['name'];source_feature=name;is_anchor=name in official
            geom=geometries[fid];need(point_inside(geom,lon,lat),'named witness outside selected source feature')
            root=component_at(inputs['component_rows'],inputs['component_runs'],grid,lon,lat)
            selected,proof=intersect([geom],grid,*(inputs[k]['path'] for k in keys),[],[],guard)
            need(isinstance(selected,list) and root in selected and isinstance(proof,dict) and isinstance(proof.get('per_feature_root_inside_cells'),list) and len(proof['per_feature_root_inside_cells'])==1,'witness/source intersection mismatch')
            counts=proof['per_feature_root_inside_cells'][0];need(set(map(int,counts))==set(selected),'source intersection trace mismatch')
            whole=[];partial=[]
            for component in selected:
                need(type(component) is int and component in region and str(component) in counts and type(counts[str(component)]) is int,'source root outside scanned region')
                total=region[component]['total'];inside=counts[str(component)];need(0<inside<=total,'invalid whole-component intersection')
                if inside==total and region[component]['in_scope']==total:members[component]={'total':total,'in_scope':total};whole.append(component)
                else:partial.append(component)
            need(root in whole,'named witness component not fully covered by source feature')
            if is_anchor:
                need(root not in anchors,'duplicate named anchor root')
                anchors[root]={'code':group['target_code'],'source_id':w['source'],'source_feature_id':source_feature,'source_version':source['version'],'source_sha256':source['sha256'],'main_island_evidence':'Reviewed source-named group witness; whole source-feature coverage checked.'}
            trace.append({'group_id':group['group_id'],'source_feature_id':fid,'witness_source_id':w['source'],'witness_source_feature_id':source_feature,'witness_root_current_generation_only':root,'whole_roots_current_generation_only':sorted(whole),'partial_roots_current_generation_only':sorted(partial),'intersection':proof})
        windows.append({'group_id':group['group_id'],'code':group['target_code'],'components':members,'source':{'source_section':group.get('source_section'),'osm_feature_ids':list(fids),'source_id':'osm-land-polygons-split-4326','source_version':osm['version'],'source_sha256':osm['sha256'],'limitation':group.get('limitation')}})
    for ref in refs:need(file_sha(sources[ref['source_id']]['path'],guard)==ref['sha256'],'source bytes changed')
    for key in keys:need(file_sha(inputs[key]['path'],guard)==inputs[key]['sha256'],'physical input changed')
    return {'windows':windows,'anchors':anchors,'source_trace':trace,'limitations':['Point-to-source-polygon identity and source-group membership are interpreted.','Roots are valid only for the pinned component generation.']}
