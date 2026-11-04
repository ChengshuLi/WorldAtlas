"""Validate research-only same-run direct+nearest land lineage.

Hashes and intra-run consistency do not authenticate a Neon revision or prove
geographic correctness. Paths must resolve within the caller's input root.
"""
import json, math
from pathlib import Path
import compose_full_water_grid as c


def validate_nearest_land_report(report,report_path,physical,land,snapshot_hash,revision,input_root,canonical_grid):
    def require(v,msg):
        if not v:raise ValueError('nearest land lineage: '+msg)
    digest=lambda v:isinstance(v,str) and len(v)==64 and all(x in '0123456789abcdef' for x in v)
    require(input_root is not None,'input root required')
    root=Path(input_root).resolve();base=Path(report_path).resolve().parent
    require(base.is_relative_to(root),'report outside input root')
    def local(relative,expected):
        p=(base/relative).resolve();require(p.is_relative_to(root) and p.is_file(),'artifact missing or outside input root')
        require(digest(expected) and c.sha256(p)==expected,'artifact digest mismatch: '+str(relative))
        return p
    def pin(spec):
        require(isinstance(spec,dict) and set(spec)=={'path','sha256'} and isinstance(spec['path'],str) and digest(spec['sha256']),'invalid file pin')
        p=Path(spec['path']).resolve();require(p.is_relative_to(root) and p.is_file() and c.sha256(p)==spec['sha256'],'pinned input missing, outside root, or changed')
        return p
    def doc(path):
        try:
            v=json.loads(path.read_bytes());require(isinstance(v,dict),'artifact must be an object');return v
        except (json.JSONDecodeError,UnicodeDecodeError):raise ValueError('nearest land lineage: invalid JSON') from None
    def same_pin(spec,path):
        p=pin(spec);require(p==path.resolve(),'unexpected artifact path');return p
    required_codes={'run_single_generation_nearest.py','integrate_resolved_land.py','nearest_mainland.py','tile_index.py','distance_kernel.cpp','derive_mainland_seed.py','compile_land.py','assign_land_stream.py','run_single_generation.py','assign_land.py','build_components.cpp'}
    code=report.get('code_sha256')
    require(report.get('schema')=='single-generation-nearest-report-v1' and report.get('status')=='unverified-research-not-published' and report.get('component_generations')==1 and isinstance(code,dict) and set(code)==required_codes and all(digest(x) for x in code.values()),'invalid completion report or code pins')
    require(revision.get('status')=='draft' and report.get('decision_revision')==revision.get('id') and report.get('decision_revision_asserted_status')=='draft' and report.get('entity_revision')==revision.get('entity_revision') and report.get('snapshot_sha256')==snapshot_hash,'revision or snapshot mismatch')
    require(report.get('physical_grid')==canonical_grid and report.get('physical_rows_sha256')==physical.get('rows_sha256') and report.get('physical_runs_sha256')==physical.get('runs_sha256') and report.get('output_rows_sha256')==land.get('rows_sha256') and report.get('output_runs_sha256')==land.get('runs_sha256'),'top-level physical or output mismatch')
    outer_req_path=local('request.json',report.get('request_sha256'));outer=doc(outer_req_path)
    require(outer.get('schema')=='single-generation-nearest-v1' and outer.get('single_generation_request',{}).get('sha256')==report.get('single_generation_request_sha256'),'outer request mismatch')
    single_req_path=local('single/request.json',report.get('single_generation_request_sha256'));pin(outer['single_generation_request'])
    one=doc(single_req_path);require(one.get('schema')=='single-generation-direct-land-v1' and one.get('grid')==canonical_grid and one.get('snapshot',{}).get('sha256')==snapshot_hash and one.get('physical_report',{}).get('sha256')==report.get('physical_report_sha256'),'single request mismatch')
    snap=doc(pin(one['snapshot']));require(snap.get('schema')=='worldatlas-geography-decision-draft-evidence-v1' and snap.get('source')=='neon-export' and snap.get('decision_revision')==revision and snap.get('entity_revision',{}).get('id')==revision.get('entity_revision') and snap.get('entity_revision',{}).get('status')=='draft','snapshot is not the selected draft')
    policy=snap.get('land_mainland_policy');require(isinstance(policy,dict) and policy.get('execution_status')=='selected_for_research' and policy.get('method')=='nearest_mainland_v1' and policy.get('distance')=='minimum_spherical_cell_center' and policy.get('tie')=='fail' and policy.get('precedence')=='mainland_then_reviewed_component_then_nearest' and policy.get('grid')==canonical_grid,'nearest policy missing or unselected')
    for k in ('physical_rows','physical_runs'):
        pin(one[k]);require(one[k]['sha256']==physical[k.replace('physical_','')+'_sha256'] and policy.get(k+'_sha256')==one[k]['sha256'],'physical input pin mismatch')
    physical_doc=doc(pin(one['physical_report']));pout=physical_doc.get('physical_output_sha256',physical_doc.get('output_sha256',{}))
    require(physical_doc.get('status')=='candidate-only' and physical_doc.get('grid')==canonical_grid and pout.get('rows.u32le')==physical['rows_sha256'] and pout.get('runs.u32le')==physical['runs_sha256'] and (not physical.get('physical_mask_sha256') or pout.get('physical-dry.tif')==physical['physical_mask_sha256']),'physical report mismatch')
    kind='raw-pipeline-report' if all(k in physical_doc for k in ('physical_output_sha256','source_manifest','land_config','water_config','stage_reports')) else 'compose-report'
    single=doc(local('single/resolution-report.json',report.get('single_resolution_report_sha256')))
    manifest_path=local('single/manifests/components.json',report.get('component_manifest_sha256'));manifest=doc(manifest_path)
    res_path=local('single/assignment/resolution-report.json',report.get('direct_resolution_report_sha256'));res=doc(res_path)
    resolved_path=local('single/assignment/compiler-config.json',single.get('compiler_config_sha256'));resolved=doc(resolved_path)
    require(single.get('schema')=='single-generation-land-resolution-report-v1' and single.get('status')=='research-partial-no-land-grid' and single.get('component_generations')==1 and single.get('request_sha256')==report.get('single_generation_request_sha256') and single.get('snapshot_sha256')==snapshot_hash and single.get('decision_revision')==revision.get('id') and single.get('decision_revision_asserted_status')=='draft' and single.get('entity_revision')==revision.get('entity_revision') and single.get('physical_report_sha256')==report.get('physical_report_sha256') and single.get('physical_report_kind')==kind and report.get('physical_report_kind')==kind and single.get('component_manifest_sha256')==report.get('component_manifest_sha256') and single.get('resolution_report_sha256')==report.get('direct_resolution_report_sha256'),'single generation resolution mismatch')
    sh=single.get('code_sha256',{});require(sh=={'runner':code['run_single_generation.py'],'compiler':code['compile_land.py'],'stream_backend':code['assign_land_stream.py'],'shared_backend':code['assign_land.py']},'single generation code mismatch')
    require(manifest.get('schema')=='single-generation-component-manifest-v1' and manifest.get('status')=='complete-research' and manifest.get('grid')==canonical_grid and manifest.get('physical_report')==one['physical_report'] and manifest.get('physical_report_kind')==kind and manifest.get('component_source_sha256')==code['build_components.cpp']==one.get('component_source_sha256')==policy.get('component_algorithm_sha256') and manifest.get('builder_binary',{}).get('sha256')==manifest.get('builder_binary_sha256') and isinstance(manifest.get('compiler_version'),str) and bool(manifest['compiler_version']) and isinstance(manifest.get('builder_output'),str) and bool(manifest['builder_output']),'component manifest mismatch')
    mpins=manifest.get('pins',{});require(isinstance(mpins,dict) and set(mpins)=={'physical_rows','physical_runs','component_rows','component_runs'},'invalid component pins')
    for k in ('physical_rows','physical_runs','component_rows','component_runs'):
        pin(mpins[k]);require(mpins[k].get('sha256')==policy.get(k+'_sha256'),'policy component pin mismatch')
    require(mpins['physical_rows']==one['physical_rows'] and mpins['physical_runs']==one['physical_runs'],'manifest physical input mismatch')
    builder=pin(manifest['builder_binary']);require(all(Path(mpins[k]['path']).resolve().parent==builder.parent for k in ('component_rows','component_runs')),'builder/components path mismatch')
    require(res.get('schema')=='direct-land-explicit-resolution-v1' and res.get('status')=='research-partial-no-land-grid' and res.get('snapshot_sha256')==snapshot_hash and res.get('decision_revision')==revision['id'] and res.get('decision_revision_asserted_status')=='draft' and res.get('entity_revision')==revision['entity_revision'] and res.get('grid')==canonical_grid and res.get('component_generation_method')=='single-generation-manifest' and res.get('component_manifest_sha256')==report['component_manifest_sha256'] and Path(res.get('component_manifest_path','')).resolve()==manifest_path and Path(res.get('compiler_config_path','')).resolve()==resolved_path and res.get('compiler_config_sha256')==single.get('compiler_config_sha256') and res.get('program_sha256')==code['compile_land.py'] and res.get('shared_backend_sha256')==code['assign_land.py'] and res.get('component_source_sha256')==code['build_components.cpp'],'direct resolver report mismatch')
    require(res.get('input_pins')=={'snapshot':one['snapshot'],**mpins} and res.get('source_files')==one.get('source_files') and isinstance(res.get('source_files'),list),'resolver input mismatch')
    for item in res['source_files']:pin(item['file'])
    require(resolved.get('schema')=='land-decision-compiler-prototype-v1' and resolved.get('decision_revision')==revision['id'] and resolved.get('revision_status')=='draft' and resolved.get('grid')==canonical_grid and isinstance(resolved.get('rules'),list) and all(resolved.get(k)==mpins[k] for k in mpins) and res.get('explicit_root_count')==len(resolved['rules']),'resolved config mismatch')
    for r in resolved['rules']:
        if r.get('kind')=='polygon_partition':
            for part in r.get('parts',[]):pin(part['geometry'])
    # The adapter's own report binds its serialized request; fixed-path loading
    # avoids trusting an arbitrary path supplied by that request.
    adapter_report=doc(local('integrated/report.json',report.get('adapter_report_sha256')))
    arpath=local('configs/adapter.json',adapter_report.get('request_sha256'));ar=doc(arpath)
    require(adapter_report.get('schema')=='resolved-land-nearest-adapter-report-v1' and adapter_report.get('status')=='unverified-research-not-published' and adapter_report.get('snapshot_sha256')==snapshot_hash and adapter_report.get('compiler_config_sha256')==single.get('compiler_config_sha256') and adapter_report.get('resolution_report_sha256')==report.get('direct_resolution_report_sha256') and ar.get('schema')=='resolved-land-nearest-adapter-v1' and ar.get('snapshot')==one['snapshot'] and ar.get('workers')==outer.get('workers') and ar.get('strip_rows')==outer.get('strip_rows'),'adapter report mismatch')
    same_pin(ar['compiler_config'],resolved_path);same_pin(ar['resolution_report'],res_path);same_pin(ar['component_manifest'],manifest_path)
    ah=adapter_report.get('code_sha256');require(isinstance(ah,dict) and len(ah)==9 and len({Path(k).name for k in ah})==9 and {Path(k).name:v for k,v in ah.items()}=={k:code[k] for k in ('integrate_resolved_land.py','derive_mainland_seed.py','nearest_mainland.py','compile_land.py','assign_land_stream.py','assign_land.py','tile_index.py','distance_kernel.cpp','build_components.cpp')},'adapter code mismatch')
    seed_report=doc(local('integrated/mainland-seed/report.json',adapter_report.get('seed_report_sha256')))
    seed_rows=local('integrated/mainland-seed/rows.u32le',policy.get('mainland_rows_sha256'));seed_runs=local('integrated/mainland-seed/runs.u32le',policy.get('mainland_runs_sha256'))
    require(seed_report.get('schema')=='resolved-mainland-seed-report-v1' and seed_report.get('status')=='unverified-research-not-published' and seed_report.get('snapshot_sha256')==snapshot_hash and seed_report.get('decision_revision')==revision['id'] and seed_report.get('compiler_config_sha256')==single.get('compiler_config_sha256') and seed_report.get('rows_sha256')==policy['mainland_rows_sha256'] and seed_report.get('runs_sha256')==policy['mainland_runs_sha256'] and seed_report.get('mainland_components')==sorted(policy.get('mainland_component_ids',[])),'mainland seed report mismatch')
    nearest_report=doc(local('integrated/nearest/claims.json',adapter_report.get('nearest_claims_sha256')))
    near_cfg=doc(local('integrated/configs/nearest.json',nearest_report.get('config_sha256')))
    require(nearest_report.get('schema')=='nearest-mainland-claims-v1' and nearest_report.get('status')=='unverified-research-not-published' and nearest_report.get('snapshot_sha256')==snapshot_hash and nearest_report.get('decision_revision')==revision['id'] and nearest_report.get('component_generation_method')=='single-generation-manifest' and nearest_report.get('component_manifest_sha256')==report['component_manifest_sha256'] and nearest_report.get('mainland_components')==sorted(policy.get('mainland_component_ids',[])) and nearest_report.get('reviewed_claims')==policy.get('reviewed_component_claims') and nearest_report.get('program_sha256')==code['nearest_mainland.py'] and nearest_report.get('tile_index_program_sha256')==code['tile_index.py'] and nearest_report.get('distance_kernel_source_sha256')==code['distance_kernel.cpp'],'nearest claims report mismatch')
    local('integrated/nearest/mainland-tile-index/distance-kernel.so',nearest_report.get('distance_kernel_binary_sha256'))
    require(near_cfg.get('schema')=='nearest-mainland-build-v1' and near_cfg.get('snapshot')==one['snapshot'] and near_cfg.get('grid')==canonical_grid and near_cfg.get('workers')==outer.get('workers') and all(near_cfg.get(k)==mpins[k] for k in mpins),'nearest config mismatch')
    same_pin(near_cfg['mainland_rows'],seed_rows);same_pin(near_cfg['mainland_runs'],seed_runs)
    merged_path=local('integrated/configs/merged.json',adapter_report.get('merged_config_sha256'));merged=doc(merged_path)
    explicit=resolved['rules'];existing={r.get('component_id') for r in explicit};ids={r.get('rule_id') for r in explicit}
    require(len(existing)==len(explicit) and len(ids)==len(explicit),'duplicate explicit rule')
    generated=[];claims=nearest_report.get('nearest_claims');require(isinstance(claims,list),'nearest claims missing')
    for item in claims:
        require(isinstance(item,dict) and set(item)=={'component_id','code','distance_metres'} and type(item['component_id']) is int and item['component_id']>=0 and type(item['code']) is int and 17<=item['code']<=22 and type(item['distance_metres']) in (int,float) and math.isfinite(item['distance_metres']) and item['distance_metres']>=0,'invalid nearest claim')
        rootid=item['component_id'];rid=f'nearest-mainland:component:{rootid}';require(rootid not in existing and rid not in ids,'nearest claim overlaps explicit or duplicate')
        existing.add(rootid);ids.add(rid);generated.append({'component_id':rootid,'rule_id':rid,'source_evidence':['selected nearest-mainland policy '+snapshot_hash],'kind':'whole_component','code':item['code']})
    rootset=set(policy.get('mainland_component_ids',[])); explicit_map={r['component_id']:r for r in explicit}
    require(bool(rootset) and rootset<=explicit_map.keys(),'mainland root lacks an explicit rule')
    reviewed=policy.get('reviewed_component_claims');require(isinstance(reviewed,list),'invalid reviewed claims')
    binding={b.get('entity_id'):b.get('code') for b in snap.get('category_bindings',[]) if b.get('physical_class')=='land'}
    require(len(binding)==6 and set(binding.values())==set(range(17,23)),'invalid land bindings')
    reviewmap={r.get('component_id'):r for r in reviewed};require(len(reviewmap)==len(reviewed) and set(reviewmap)==set(explicit_map)-rootset,'reviewed claim coverage mismatch')
    for rid,claim in reviewmap.items():
        rule=explicit_map[rid];require(set(claim)=={'rule_id','component_id','entity_id'} and claim.get('entity_id') in binding and rule.get('kind')=='whole_component' and rule.get('rule_id')==claim.get('rule_id') and rule.get('code')==binding[claim['entity_id']],'reviewed claim mismatch')
    require(not (set(item['component_id'] for item in claims)&rootset),'nearest claim overlaps mainland')
    evidence=adapter_report.get('verified_cut_evidence');cut_ids=policy.get('source_cut_feature_ids');require(isinstance(evidence,list) and all(isinstance(x,dict) for x in evidence) and isinstance(cut_ids,list) and all(isinstance(x,str) and bool(x.strip()) for x in cut_ids) and len(set(cut_ids))==len(cut_ids) and len({x.get('feature_id') for x in evidence})==len(evidence) and {x.get('feature_id') for x in evidence}==set(cut_ids),'cut evidence roster mismatch')
    mixed=any(explicit_map[x].get('kind')=='polygon_partition' and len({p.get('code') for p in explicit_map[x].get('parts',[])})>1 for x in rootset)
    require(not mixed or bool(evidence),'mixed mainland partition lacks cut evidence')
    expected_parts={str((rootid,p.get('part_id'))) for rootid in rootset for p in explicit_map[rootid].get('parts',[]) if explicit_map[rootid].get('kind')=='polygon_partition'}
    part_counts=seed_report.get('part_cell_counts');require(isinstance(part_counts,dict) and set(part_counts)==expected_parts and all(type(v) is int and v>0 for v in part_counts.values()),'seed partition evidence mismatch')
    features=snap.get('features',[]);sources=snap.get('sources',[]);require(isinstance(features,list) and isinstance(sources,list),'invalid source catalogs')
    feature_map={f.get('feature_id'):f for f in features};source_map={(x.get('source_id'),x.get('version')):x for x in sources};mapping={(x.get('source_id'),x.get('source_version')):x for x in res['source_files']}
    require(len(feature_map)==len(features) and len(source_map)==len(sources) and len(mapping)==len(res['source_files']),'ambiguous source catalogs')
    for e in evidence:
        f=feature_map.get(e.get('feature_id'));require(isinstance(f,dict),'cut feature absent')
        key=(f.get('source_id'),f.get('source_version'));source=source_map.get(key);m=mapping.get(key)
        require(source is not None and m is not None and e=={'feature_id':f['feature_id'],'source_id':key[0],'source_version':key[1],'source_file_sha256':source.get('sha256'),'geometry_sha256':f.get('geometry_sha256')} and source.get('sha256')==m['file']['sha256'],'cut evidence binding mismatch')
        require(isinstance(m.get('id_property'),str) and bool(m['id_property']) and isinstance(f.get('source_feature_id'),str) and bool(f['source_feature_id']),'invalid cut source identifier')
        feature_doc=doc(pin(m['file']));fs=feature_doc.get('features',[]);hits=[x for x in fs if isinstance(x,dict) and str(x.get('properties',{}).get(m.get('id_property')))==str(f.get('source_feature_id'))]
        require(len(hits)==1 and hits[0].get('geometry',{}).get('type') in ('LineString','MultiLineString'),'cut source feature mismatch')
        import hashlib
        actual=hashlib.sha256(json.dumps(hits[0]['geometry'],sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest();require(actual==f.get('geometry_sha256'),'cut geometry digest mismatch')
    expected=dict(resolved);expected['rules']=sorted(explicit+generated,key=lambda r:r['component_id']);require(merged==expected,'merged rules do not preserve explicit and nearest decisions')
    land_report=doc(local('integrated/land/report.json',adapter_report.get('land_report_sha256')))
    local('integrated/land/config.json',adapter_report.get('merged_config_sha256'))
    expected_rows=local('integrated/land/rows.u32le',land['rows_sha256']);expected_runs=local('integrated/land/runs.u32le',land['runs_sha256'])
    require(Path(land['resolved_rows']).resolve()==expected_rows and Path(land['resolved_runs']).resolve()==expected_runs,'land output path mismatch')
    require(land_report.get('schema')=='land-streaming-research-report-v1' and land_report.get('status')=='experimental-not-published' and land_report.get('decision_revision')==revision['id'] and land_report.get('revision_status')=='draft' and land_report.get('config_sha256')==adapter_report.get('merged_config_sha256') and land_report.get('program_sha256')==code['assign_land_stream.py'] and land_report.get('input_sha256')=={k:mpins[k]['sha256'] for k in mpins} and land_report.get('output_rows_sha256')==land['rows_sha256'] and land_report.get('output_runs_sha256')==land['runs_sha256'] and land_report.get('components')==len(merged['rules']) and type(land_report.get('land_cells')) is int and land_report['land_cells']>0 and (physical_doc.get('candidate_dry_cells') is None or land_report['land_cells']==physical_doc['candidate_dry_cells']) and adapter_report.get('output_rows_sha256')==land['rows_sha256'] and adapter_report.get('output_runs_sha256')==land['runs_sha256'],'final land report mismatch')
    return None
