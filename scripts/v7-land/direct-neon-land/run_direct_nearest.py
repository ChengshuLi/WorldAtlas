#!/usr/bin/env python3
"""Research-only same-run direct resolver -> mainland seed -> nearest -> RLE."""
import argparse,hashlib,json,sys
from pathlib import Path
import nearest_mainland as nearest
import integrate_resolved_land as adapter

sys.path.insert(0,str(adapter.DIRECT));import compile_land as direct

def build(path,output,allow=False):
    adapter.require(allow,'explicit unverified research mode required')
    raw=Path(path).read_bytes();req=json.loads(raw);required={'schema','direct_config','workers','strip_rows'}
    adapter.require(required<=set(req)<=required|{'component_manifest'} and req['schema']=='direct-nearest-orchestration-v1','invalid orchestration request')
    nearest.pin(req['direct_config']);dc=json.loads(Path(req['direct_config']['path']).read_bytes());nearest.pin(dc['snapshot'])
    manifest=req.get('component_manifest')
    if manifest is not None:nearest.pin(manifest)
    inp=[Path(path).resolve(),Path(req['direct_config']['path']).resolve(),Path(dc['snapshot']['path']).resolve()]
    if manifest is not None:inp.append(Path(manifest['path']).resolve())
    out=Path(output).resolve();adapter.require(not out.exists() and all(not p.is_relative_to(out) and not out.is_relative_to(p.parent) for p in inp),'output overlaps input')
    tracked=[Path(__file__).resolve(),Path(adapter.__file__).resolve(),Path(nearest.__file__).resolve(),Path(nearest.__file__).parent/'tile_index.py',Path(nearest.__file__).parent/'distance_kernel.cpp',Path(seed_path()),adapter.DIRECT/'compile_land.py',adapter.DIRECT/'assign_land_stream.py',adapter.DIRECT.parent/'assign_land.py',Path(nearest.__file__).parent.parent/'build_components.cpp']
    start={str(p):nearest.sha(p) for p in tracked}
    out.mkdir(mode=0o700);(out/'configs').mkdir()
    report=direct.prepare(req['direct_config']['path'],out/'resolved',True,manifest['path'] if manifest else None,resolve_only=True)
    resolved=out/'resolved'/'compiler-config.json';rr=out/'resolved'/'resolution-report.json'
    adapter.require(report['compiler_config_sha256']==nearest.sha(resolved) and json.loads(rr.read_bytes())==report,'resolver output mismatch')
    def pin(p):return {'path':str(p),'sha256':nearest.sha(p)}
    ar={'schema':'resolved-land-nearest-adapter-v1','snapshot':dc['snapshot'],'compiler_config':pin(resolved),'resolution_report':pin(rr),'workers':req['workers'],'strip_rows':req['strip_rows']}
    if manifest is not None:ar['component_manifest']=manifest
    ap=out/'configs'/'adapter.json';ap.write_text(json.dumps(ar,sort_keys=True,separators=(',',':'))+'\n')
    result=adapter.build(ap,out/'integrated',True)
    nearest.pin(req['direct_config']);nearest.pin(dc['snapshot'])
    if manifest is not None:nearest.pin(manifest)
    adapter.require(Path(path).read_bytes()==raw and {str(p):nearest.sha(p) for p in tracked}==start,'orchestrator inputs or code changed')
    final={'schema':'direct-nearest-orchestration-report-v1','status':'unverified-research-not-published','request_sha256':hashlib.sha256(raw).hexdigest(),'direct_config_sha256':req['direct_config']['sha256'],'resolution_report_sha256':nearest.sha(rr),'adapter_report_sha256':nearest.sha(out/'integrated'/'report.json'),'output_rows_sha256':result['output_rows_sha256'],'output_runs_sha256':result['output_runs_sha256'],'component_generation_method':'single-generation-manifest' if manifest else 'independent-recompute-in-both-stages','limitation':'Research-only. Snapshot authenticity, source provenance, mainland decisions and full-world correctness require independent review. No prior continent grid read.'}
    (out/'report.json').write_text(json.dumps(final,indent=2)+'\n');return final

def seed_path():return Path(adapter.seed.__file__).resolve()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('request');p.add_argument('output');p.add_argument('--allow-unverified-snapshot',action='store_true');a=p.parse_args()
    try:print(json.dumps(build(a.request,a.output,a.allow_unverified_snapshot),indent=2))
    except Exception as e:print('error: '+str(e),file=sys.stderr);raise SystemExit(1)
