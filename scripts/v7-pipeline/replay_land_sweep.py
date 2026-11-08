#!/usr/bin/env python3
"""Validate complete staged land evidence; optionally rerun source-bound search.

No pipeline/source build, service access, compilation or process launch occurs.
Expected land labels are used only after fresh search and writing, never for a
hint, upper bound, certificate, stopping condition or assignment.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time

import numpy as np

from benchmark_land_sweep import STAGE2, digest
from exclusive_outputs import create_directory_exclusive, write_json_exclusive
from stage_land_sweep_inputs import INPUTS, METADATA, STREAMS
import baseline_runner
import build_seed_tiles
import land_runtime
import contracts
import engine
import preflight
import ural_delta
import verify_inputs
import write_land_stream as land_writer


def staged_inputs(directory):
    plan=json.loads((directory/'plan.json').read_bytes())
    if plan['schema']!='worldatlas-land-sweep-staging-plan-v1':raise ValueError('unknown staging plan')
    for name in (*METADATA,*STREAMS):
        pin=plan['assets'][name];path=directory/name
        if path.stat().st_size!=pin['size_bytes'] or digest(path)!=pin['sha256']:
            raise ValueError('staged input size/hash mismatch: '+name)
    config=json.loads((directory/'fresh-stage2-core-config').read_bytes())
    report=json.loads((directory/'fresh-stage2-land-report').read_bytes())
    if report['config_sha256']!=plan['core_config_sha256'] or config['grid']!=plan['grid']:
        raise ValueError('completed report/config identity differs')
    paths={name:directory/source for name,source in INPUTS.items()}
    for name,source in INPUTS.items():
        value=plan['assets'][source]['sha256']
        if config['inputs'][name]['sha256']!=value or report['inputs_sha256'][name]!=value:
            raise ValueError('completed report/input identity differs: '+name)
    for kind in ('rows','runs'):
        if report['output_'+kind+'_sha256']!=plan['assets']['fresh-stage2-land-'+kind]['sha256']:
            raise ValueError('expected output differs from producer report')
    return plan,config,report,paths


def replay(directory, out, *, search=False):
    started_at=datetime.now(timezone.utc).isoformat()
    for module in (baseline_runner,build_seed_tiles,land_runtime,contracts,engine,preflight,ural_delta,verify_inputs,land_writer):
        if Path(module.__file__).resolve()!=STAGE2/(module.__name__+'.py'):
            raise ImportError('land replay module resolved outside its source: '+module.__name__)
    directory=directory.resolve(strict=True)
    plan,config,report,paths=staged_inputs(directory)
    roots=np.fromfile(paths['hint_roots'],dtype='<u4');hints=np.fromfile(paths['hint_codes'],dtype='u1')
    if len(roots)!=len(hints):raise ValueError('root/hint count mismatch')
    seed=json.loads(paths['seed_report'].read_bytes());grid=config['grid'];controls=config['controls']
    seed_roots=report['physical_coverage']['seed_roots']
    code={name:digest(STAGE2/name) for name in land_runtime.CODE_NAMES}
    identity={'schema':'worldatlas-land-evidence-replay-v1','staging_plan_sha256':digest(directory/'plan.json'),
        'code_sha256':code,'driver_sha256':digest(Path(__file__)),'started_at_utc':started_at,'python':sys.version,'platform':list(os.uname()),'search':search,
        'scope':'coverage and optional source-bound WGS84 search/writer; no fresh source construction or geography acceptance'}
    create_directory_exclusive(out);write_json_exclusive(out/'invocation.json',identity,indent=2)
    timings={};phase_utc={}
    def timed(name, function):
        phase_start=datetime.now(timezone.utc).isoformat()
        started=time.perf_counter();result=function();timings[name]=time.perf_counter()-started
        phase_utc[name]={'started_at_utc':phase_start,'completed_at_utc':datetime.now(timezone.utc).isoformat()}
        with (out/'progress.jsonl').open('a') as stream:
            stream.write(json.dumps({'phase':name,'status':'complete','seconds':timings[name],**phase_utc[name]})+'\n')
        return result
    streams=[paths[name] for name in ('component_rows','component_runs','physical_rows','physical_runs','seed_rows','seed_runs')]
    coverage=timed('preflight',lambda:preflight.validate(grid['width'],grid['height'],*streams,roots,seed_roots,
        required_codes=map(int,report['categories']),seed_rules=seed['seed_rules'],
        expected_rule_population=seed['rule_population'],expected_category_counts=seed['category_cell_counts']))
    if coverage!=report['physical_coverage']:raise ValueError('complete coverage differs')
    result={**identity,'status':'complete-global-preflight-identical','coverage':coverage,'timings':timings,'phase_utc':phase_utc}
    write_json_exclusive(out/'coverage.json',result,indent=2)
    if search:
        extra_path=directory/'search-inputs.json';extra_hash=digest(extra_path)
        extra=json.loads(extra_path.read_bytes())
        result['search_inputs_sha256']=extra_hash
        if extra['parent_plan_sha256']!=identity['staging_plan_sha256']:raise ValueError('search staging identity differs')
        for name,pin in extra['inputs'].items():
            path=Path(pin['path']).resolve(strict=True)
            if path.stat().st_size!=pin['size_bytes'] or digest(path)!=pin['sha256'] or config['inputs'][name]['sha256']!=pin['sha256']:
                raise ValueError('search input size/hash mismatch: '+name)
            paths[name]=path
        tiled=out/'seed-tiles'
        timed('seed-tiles',lambda:build_seed_tiles.build(paths['seed_rows'],paths['seed_runs'],
            plan['assets']['fresh-stage2-seed-rows']['sha256'],plan['assets']['fresh-stage2-seed-runs']['sha256'],
            grid['width'],grid['height'],tiled,disk_floor_bytes=controls['minimum_free_bytes']))
        if digest(tiled/'manifest.txt')!=digest(paths['tile_manifest']):
            raise ValueError('fresh source-bound tile index differs')
        reps=np.fromfile(paths['representatives'],dtype='<u4').reshape(-1,5)
        tiles=timed('verify-representatives',lambda:verify_inputs.verify_representatives(tiled,tiled/'manifest.txt',reps,grid['width'],grid['height']))
        cert,exact=timed('spatial-index',lambda:land_runtime.search_indexes(tiled,grid,tiles,reps,controls))
        offsets=engine.offsets(paths['component_rows'],grid['height'],paths['component_runs'].stat().st_size//12)
        def progress(phase,cursor,queries):
            with (out/'progress.jsonl').open('a') as stream:
                stream.write(json.dumps({'phase':phase,'cursor':cursor,'queries':queries})+'\n')
        decisions=timed('source-bound-search',lambda:baseline_runner.run(paths['component_runs'],offsets,roots,hints,seed_roots,
            grid['width'],cert,exact,out/'checkpoint.npz',identity,chunk=controls['chunk_columns'],
            tolerance=contracts.policy_tolerance_metres(report['land_baseline_policy']),
            disk_floor_bytes=controls['minimum_free_bytes'],checkpoint_seconds=controls['checkpoint_seconds'],
            block_records=controls['block_records'],progress=progress))
        if decisions['ties']!=report['ties']:raise ValueError('fresh WGS84 ties differ')
        rootfile,codefile=out/'roots.u32le',out/'codes.u8'
        decisions['roots'].astype('<u4').tofile(rootfile);decisions['codes'].astype('u1').tofile(codefile)
        delta=ural_delta.compile_rule(json.loads(paths['decision_snapshot'].read_bytes()),report['categories'],grid)
        writer=timed('writer',lambda:land_writer.write_land_stream(grid['width'],grid['height'],*streams,rootfile,codefile,seed_roots,
            out/'candidate',disk_reserve_bytes=controls['minimum_free_bytes'],delta_rule=delta))
        if writer.get('ural_delta')!=report.get('ural_delta'):raise ValueError('Ural cell-side populations differ')
        for name in ('rows','runs'):
            if digest(out/'candidate'/(name+'.u32le'))!=plan['assets']['fresh-stage2-land-'+name]['sha256']:
                raise ValueError('complete source-bound land output differs: '+name)
        result.update({'status':'complete-source-bound-search-and-land-streams-identical','writer':writer,
            'certified_components':decisions['certified_count'],'exact_components':decisions['exact_count'],
            'exact_queries':decisions['exact_queries'],'ties':decisions['ties']})
    staged_inputs(directory)
    if digest(directory/'plan.json')!=identity['staging_plan_sha256']:
        raise ValueError('staging plan changed during replay')
    if search:
        if digest(extra_path)!=extra_hash:raise ValueError('search staging identity changed')
        for name,pin in extra['inputs'].items():
            path=Path(pin['path'])
            if path.stat().st_size!=pin['size_bytes'] or digest(path)!=pin['sha256']:
                raise ValueError('search input changed during replay: '+name)
    if code!={name:digest(STAGE2/name) for name in code} or digest(Path(__file__))!=identity['driver_sha256']:
        raise ValueError('land replay code changed')
    result['completed_at_utc']=datetime.now(timezone.utc).isoformat()
    write_json_exclusive(out/'comparison.json',result,indent=2)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--staged-inputs',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--search',action='store_true',help='regenerate seed tiles and WGS84 decisions before writing every land row')
    args=parser.parse_args()
    print(json.dumps(replay(args.staged_inputs,args.out,search=args.search),indent=2))


if __name__=='__main__':main()
