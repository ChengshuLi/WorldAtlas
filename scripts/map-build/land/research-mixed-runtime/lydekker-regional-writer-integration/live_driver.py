"""Experimental no-build orchestration from live inputs to mixed-writer claims.

The caller must authenticate the selected Neon record, snapshot, every source,
physical lineage, runtime code and the supplied resolver reports, and review
execution. This module does not read the database or accept prior preview files
as decisions. Returned component IDs are valid only for the pinned generation.
"""
import hashlib,json
from adapter import merge_live_claims

def need(ok,msg):
    if not ok:raise ValueError(msg)

def canonical_sha(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()

def resolve_live(policy,compiled,snapshot,reports,grid,inputs,sources,line_record,*,snapshot_sha256,policy_canonical_sha256,mainland_roots,pending_claims,deps):
    """Resolve source groups and direct satellites, then bridge fresh claims.

    Dependencies are explicit for code pinning and tests. The caller must bind
    each to the reviewed implementation, including exact WGS84 run_pair. All
    known pending groups are supplied explicitly; an empty list is not a proof
    that the pending inventory is complete. Does not create output grid files.
    """
    need(isinstance(policy,dict) and canonical_sha(policy)==policy_canonical_sha256 and policy.get('status')=='selected_for_research','invalid selected research policy pin')
    need(isinstance(compiled,dict) and policy.get('decision_revision')==compiled.get('revision'),'decision revision mismatch')
    need(isinstance(inputs,dict) and set(inputs)=={'physical_rows','physical_runs','component_rows','component_runs'},'invalid physical inputs')
    need(isinstance(mainland_roots,(set,frozenset)) and isinstance(pending_claims,(list,tuple)) and all(isinstance(c,dict) and type(c.get('component_id')) is int for c in pending_claims),'explicit protections required')
    required={'research','verified_line','scan','buffered_bounds','resolve_feature_windows','apply_groups','resolve_with_mixed_replay','collect_runs','apply_satellites','extract','intersect','point_inside','component_at','run_pair','mixed_claims'}
    need(isinstance(deps,dict) and set(deps)==required and all(callable(deps[k]) for k in required-{'mixed_claims'}) and callable(getattr(deps['mixed_claims'],'combine',None)),'invalid runtime dependencies')
    ev=policy['evidence'];cp={'rows':inputs['component_rows']['sha256'],'runs':inputs['component_runs']['sha256']};need(cp=={'rows':ev['component_rows_sha256'],'runs':ev['component_runs_sha256']},'component pin mismatch')
    geo=sources.get('geonames-country-id');need(isinstance(geo,dict),'missing GeoNames source')
    anchor_source={'path':geo['path'],'sha256':geo['sha256'],'source_id':'geonames-country-id','source_version':geo['version'],'country':policy['anchor_discovery']['country']}
    sat=policy['satellite_policy'];need(sat['metric']=='WGS84 ellipsoidal minimum component-center distance' and sat['max_satellite_cells']==20 and sat['max_gap_m']==5000 and sat['tie_m']==0.00001,'unsupported satellite policy')
    bounds=policy['regional_bounds_lon_lat'];line_pin=policy['line'];
    result=deps['research'](inputs['component_rows'],inputs['component_runs'],grid,bounds,line_record,compiled,snapshot,reports,mainland_roots,deps['mixed_claims'],deps['run_pair'],None,line_pin=line_pin,max_satellite_cells=sat['max_satellite_cells'],max_gap_m=sat['max_gap_m'],tie_m=sat['tie_m'],pending_claims=pending_claims,anchor_source=anchor_source)
    line=deps['verified_line'](line_record,line_pin);region=deps['scan'](inputs['component_rows'],inputs['component_runs'],grid,bounds,line)
    windows=[]
    for g in policy['regional_groups']:
        if g.get('mode')=='complete_component_in_source_described_extent':
            windows.append({'group_id':g['group_id'],'code':g['target_code'],'components':deps['scan'](inputs['component_rows'],inputs['component_runs'],grid,g['bounds_lon_lat'],line),'source':{'section':g['source_section'],'limitation':g['limitation']}})
    groups=deps['resolve_feature_windows'](policy,region,grid,inputs,sources,extract=deps['extract'],intersect=deps['intersect'],point_inside=deps['point_inside'],component_at=deps['component_at'])
    result=deps['apply_groups'](result,windows+groups['windows'])
    buffer=deps['scan'](inputs['component_rows'],inputs['component_runs'],grid,deps['buffered_bounds'](bounds,sat['max_gap_m']+sat['tie_m']),line)
    buffered=deps['resolve_with_mixed_replay'](buffer,compiled,snapshot,reports,mainland_roots,deps['mixed_claims'],pending_claims)
    result['proposals'].update({r:p for r,p in buffered['proposals'].items() if r not in region})
    result['competitor_targets']={r:claims[0]['code'] for r,claims in buffered['replayed_claims'].items() if r not in buffered['pending_source_claims']}
    pending={c['component_id'] for c in pending_claims};anchors=dict(result['source_anchors'])
    for root,anchor in groups['anchors'].items():
        if root in pending or root in result['review']:continue
        p=result['proposals'].get(root)
        if p and p['code']==anchor['code'] and p['basis'] in ('selected_affiliation','whole_component_line_side','inferred_source_extent_group_convention'):anchors[root]=anchor
    anchors={r:a for r,a in anchors.items() if r not in pending and r not in result['review'] and r in result['proposals'] and result['proposals'][r]['code']==a['code']}
    need(set(anchors)<=set(buffer),'anchor outside competitor frame')
    runs=deps['collect_runs'](inputs['component_rows'],inputs['component_runs'],grid,{r:c['total'] for r,c in buffer.items()})
    result=deps['apply_satellites'](result,buffer,runs,anchors,deps['run_pair'],width=grid['width'],north=grid['north'],max_satellite_cells=sat['max_satellite_cells'],max_gap_m=sat['max_gap_m'],tie_m=sat['tie_m'],candidate_roots=set(region),allow_unanchored_nearest=True)
    result['proposals']={r:p for r,p in result['proposals'].items() if r in region};result['review']={r:p for r,p in result['review'].items() if r in region}
    result['source_group_trace']=groups['source_trace'];result['decision_snapshot_sha256']=snapshot_sha256
    selected=deps['mixed_claims'].combine(compiled,snapshot,reports,set(mainland_roots))
    bridge=merge_live_claims(policy,compiled,selected,result,snapshot_sha256=snapshot_sha256,component_sha256=cp,policy_canonical_sha256=policy_canonical_sha256,pending_roots=pending,protected_roots=mainland_roots)
    return {'regional_result':result,'writer_bridge':bridge,'limitations':['Research only: caller authenticates all same-run sources, pending inventory, code and physical lineage.','Withheld roots retain baseline codes in the existing writer; no output grid is produced here.']}
