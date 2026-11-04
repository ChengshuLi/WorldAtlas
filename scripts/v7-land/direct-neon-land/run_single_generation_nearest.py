#!/usr/bin/env python3
"""Research-only one-component-generation direct+nearest land orchestration."""
import argparse,hashlib,json
from pathlib import Path
import nearest_mainland as nearest
import integrate_resolved_land as adapter
import run_single_generation as single

def build(path,output,allow=False):
    adapter.require(allow,'explicit unverified research mode required')
    raw=Path(path).read_bytes();req=json.loads(raw)
    adapter.require(set(req)=={'schema','single_generation_request','workers','strip_rows'} and req['schema']=='single-generation-nearest-v1','invalid orchestration request')
    nearest.pin(req['single_generation_request']);one=json.loads(Path(req['single_generation_request']['path']).read_bytes());nearest.pin(one['snapshot'])
    snapshot=json.loads(Path(one['snapshot']['path']).read_bytes());revision=snapshot.get('decision_revision',{});entity=snapshot.get('entity_revision',{});policy=snapshot.get('land_mainland_policy',{})
    adapter.require(snapshot.get('schema')=='worldatlas-geography-decision-draft-evidence-v1' and revision.get('status')==entity.get('status')=='draft' and isinstance(policy,dict) and policy.get('execution_status')=='selected_for_research','selected draft mainland policy required before component generation')
    nearest.pin(one['physical_report'])
    inp=[Path(path).resolve(),Path(req['single_generation_request']['path']).resolve(),Path(one['snapshot']['path']).resolve(),Path(one['physical_report']['path']).resolve()]
    out=Path(output).resolve();adapter.require(not out.exists() and all(not p.is_relative_to(out) and not out.is_relative_to(p.parent) for p in inp),'output overlaps input')
    code={str(p):nearest.sha(p) for p in [Path(__file__).resolve(),Path(adapter.__file__).resolve(),Path(nearest.__file__).resolve(),Path(nearest.__file__).parent/'tile_index.py',Path(nearest.__file__).parent/'distance_kernel.cpp',Path(adapter.seed.__file__).resolve(),adapter.DIRECT/'compile_land.py',adapter.DIRECT/'assign_land_stream.py',adapter.DIRECT/'run_single_generation.py',adapter.DIRECT.parent/'assign_land.py',Path(nearest.__file__).parent.parent/'build_components.cpp']}
    out.mkdir(mode=0o700);(out/'configs').mkdir()
    top=single.run(req['single_generation_request']['path'],out/'single',True,resolve_only=True)
    manifest=out/'single'/'manifests'/'components.json';rr=out/'single'/'assignment'/'resolution-report.json';resolved=out/'single'/'assignment'/'compiler-config.json';top_path=out/'single'/'resolution-report.json'
    adapter.require(top.get('schema')=='single-generation-land-resolution-report-v1' and top.get('status')=='research-partial-no-land-grid' and top.get('component_generations')==1 and top.get('request_sha256')==req['single_generation_request']['sha256'] and top.get('snapshot_sha256')==one['snapshot']['sha256'] and top.get('physical_report_sha256')==one['physical_report']['sha256'] and top.get('component_manifest_sha256')==nearest.sha(manifest) and top.get('resolution_report_sha256')==nearest.sha(rr) and top.get('compiler_config_sha256')==nearest.sha(resolved) and top.get('code_sha256')==single.code_hashes(),'single-generation report mismatch')
    def pin(p):return {'path':str(p),'sha256':nearest.sha(p)}
    ar={'schema':'resolved-land-nearest-adapter-v1','snapshot':one['snapshot'],'compiler_config':pin(resolved),'resolution_report':pin(rr),'component_manifest':pin(manifest),'workers':req['workers'],'strip_rows':req['strip_rows']}
    ap=out/'configs'/'adapter.json';ap.write_text(json.dumps(ar,sort_keys=True,separators=(',',':'))+'\n')
    result=adapter.build(ap,out/'integrated',True)
    nr=json.loads((out/'integrated'/'nearest'/'claims.json').read_bytes())
    adapter.require(nr.get('component_generation_method')=='single-generation-manifest' and nr.get('component_manifest_sha256')==ar['component_manifest']['sha256'],'nearest did not reuse component generation')
    for p in (req['single_generation_request'],one['snapshot'],one['physical_rows'],one['physical_runs'],one['physical_report'],ar['component_manifest'],ar['resolution_report'],ar['compiler_config'],*[x['file'] for x in one['source_files']]):nearest.pin(p)
    component=json.loads(manifest.read_bytes())
    for p in (*component['pins'].values(),component['builder_binary'],component['physical_report']):nearest.pin(p)
    artifacts={'seed_report_sha256':out/'integrated/mainland-seed/report.json','nearest_claims_sha256':out/'integrated/nearest/claims.json','merged_config_sha256':out/'integrated/configs/merged.json','land_report_sha256':out/'integrated/land/report.json','output_rows_sha256':out/'integrated/land/rows.u32le','output_runs_sha256':out/'integrated/land/runs.u32le'}
    adapter.require(json.loads((out/'integrated/report.json').read_bytes())==result and all(nearest.sha(p)==result.get(k) for k,p in artifacts.items()),'adapter artifacts changed after completion')
    adapter.require(json.loads(top_path.read_bytes())==top and nearest.sha(rr)==top['resolution_report_sha256'] and nearest.sha(manifest)==top['component_manifest_sha256'] and nearest.sha(resolved)==top['compiler_config_sha256'],'single-resolution artifacts changed after completion')
    adapter.require(Path(path).read_bytes()==raw and {k:nearest.sha(k) for k in code}==code,'orchestrator inputs or code changed')
    (out/'request.json').write_bytes(raw)
    adapter.require(nearest.sha(out/'request.json')==hashlib.sha256(raw).hexdigest(),'persisted request hash mismatch')
    named_code={Path(p).name:h for p,h in code.items()}
    adapter.require(len(named_code)==len(code),'duplicate code basenames')
    final={'schema':'single-generation-nearest-report-v1','status':'unverified-research-not-published','request_sha256':hashlib.sha256(raw).hexdigest(),'single_generation_request_sha256':req['single_generation_request']['sha256'],'snapshot_sha256':one['snapshot']['sha256'],'decision_revision':revision['id'],'decision_revision_asserted_status':revision['status'],'entity_revision':revision['entity_revision'],'physical_rows_sha256':one['physical_rows']['sha256'],'physical_runs_sha256':one['physical_runs']['sha256'],'physical_report_sha256':one['physical_report']['sha256'],'physical_report_kind':top['physical_report_kind'],'physical_grid':one['grid'],'code_sha256':named_code,'single_resolution_report_sha256':nearest.sha(top_path),'component_manifest_sha256':ar['component_manifest']['sha256'],'direct_resolution_report_sha256':ar['resolution_report']['sha256'],'adapter_report_sha256':nearest.sha(out/'integrated'/'report.json'),'component_generations':1,'output_rows_sha256':result['output_rows_sha256'],'output_runs_sha256':result['output_runs_sha256'],'limitation':'Research-only. Snapshot authenticity, source provenance, mainland decisions and full-world correctness require independent review; same-run manifest is not independent verification. No prior continent grid read.'}
    (out/'report.json').write_text(json.dumps(final,indent=2)+'\n');return final
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('request');p.add_argument('output');p.add_argument('--allow-unverified-snapshot',action='store_true');a=p.parse_args()
    try:print(json.dumps(build(a.request,a.output,a.allow_unverified_snapshot),indent=2))
    except Exception as e:print('error: '+str(e),file=__import__('sys').stderr);raise SystemExit(1)
