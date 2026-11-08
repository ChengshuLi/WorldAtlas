#!/usr/bin/env python3
"""Pair complete old/new Python sweeps using fresh source-bound assignments.

Expected output supplies only the final check. The completed source replay's
checksum-verified checkpoint supplies assignments. Run alone for comparable
timing; the tool starts no processes and changes no source/report bytes.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

import numpy as np

from benchmark_land_sweep import STAGE2, digest
from exclusive_outputs import create_directory_exclusive, write_json_exclusive
from replay_land_sweep import staged_inputs
import checkpoints
import contracts
import engine
import preflight
import ural_delta
import write_land_stream as writer


def reference_modules(directory):
    # Only the preflight's ordinary sibling import is scoped. The returned
    # modules retain their own reader and sweep globals after restoration.
    if digest(directory/'ural_delta.py')!=digest(STAGE2/'ural_delta.py'):
        raise ValueError('reference Ural semantics differ')
    def load(name, path):
        spec=importlib.util.spec_from_file_location(name,path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module
    old_writer=load('_land_sweep_reference_writer',directory/'write_land_stream.py')
    previous=sys.modules.get('write_land_stream')
    try:
        sys.modules['write_land_stream']=old_writer
        old_preflight=load('_land_sweep_reference_preflight',directory/'preflight.py')
    finally:
        if previous is None:sys.modules.pop('write_land_stream',None)
        else:sys.modules['write_land_stream']=previous
    return old_preflight,old_writer


def compare(staged, source_replay, baseline_code, out, *, candidate_first=False):
    staged,source_replay,baseline_code=(Path(path).resolve(strict=True) for path in (staged,source_replay,baseline_code))
    plan,config,report,paths=staged_inputs(staged)
    completed=json.loads((source_replay/'comparison.json').read_bytes())
    identity=json.loads((source_replay/'invocation.json').read_bytes())
    if (completed['status']!='complete-source-bound-search-and-land-streams-identical' or
            completed['staging_plan_sha256']!=digest(staged/'plan.json') or identity['staging_plan_sha256']!=digest(staged/'plan.json')):
        raise ValueError('completed source-bound replay required')
    roots=np.fromfile(paths['hint_roots'],dtype='<u4')
    meta,arrays=checkpoints.read(source_replay/'checkpoint.npz',identity,roots)
    if meta['phase']!='complete' or meta['cursor']!=paths['component_runs'].stat().st_size//12:
        raise ValueError('source-bound checkpoint is incomplete')
    codes,ties=engine.finalize(arrays['hints'],arrays['amb'],arrays['best'],
        contracts.policy_tolerance_metres(report['land_baseline_policy']),numerical_tie_guard_m=.0001)
    rootfile,codefile=source_replay/'roots.u32le',source_replay/'codes.u8'
    if (ties!=report['ties'] or not np.array_equal(np.fromfile(rootfile,dtype='<u4'),roots) or
            not np.array_equal(np.fromfile(codefile,dtype='u1'),codes)):
        raise ValueError('fresh source-bound assignments differ')
    code_names=('preflight.py','write_land_stream.py','ural_delta.py')
    old_code={name:digest(baseline_code/name) for name in code_names}
    new_code={name:digest(STAGE2/name) for name in code_names}
    old_preflight,old_writer=reference_modules(baseline_code)
    pins={name:digest(source_replay/name) for name in ('comparison.json','invocation.json','checkpoint.npz','roots.u32le','codes.u8')}
    extra=json.loads((staged/'search-inputs.json').read_bytes());snapshot=Path(extra['inputs']['decision_snapshot']['path'])
    if digest(snapshot)!=config['inputs']['decision_snapshot']['sha256']:raise ValueError('snapshot differs')
    delta=ural_delta.compile_rule(json.loads(snapshot.read_bytes()),report['categories'],config['grid'])
    invocation={'schema':'worldatlas-complete-python-land-sweep-comparison-v1','reference_code_sha256':old_code,
        'candidate_code_sha256':new_code,'staging_plan_sha256':digest(staged/'plan.json'),'source_replay_sha256':pins,
        'driver_sha256':digest(Path(__file__)),'python':sys.version,'cpu_affinity':sorted(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None,
        'scope':'paired complete coverage/writer only; source assignments recomputed from a fresh checksum-verified, identity-bound checkpoint',
        'order':['candidate','reference'] if candidate_first else ['reference','candidate']}
    create_directory_exclusive(out);write_json_exclusive(out/'invocation.json',invocation,indent=2)
    seed=json.loads(paths['seed_report'].read_bytes());grid=config['grid'];seed_roots=report['physical_coverage']['seed_roots']
    streams=[paths[name] for name in ('component_rows','component_runs','physical_rows','physical_runs','seed_rows','seed_runs')]
    results={}
    for name in invocation['order']:
        module,write_module=(preflight,writer) if name=='candidate' else (old_preflight,old_writer)
        begin=datetime.now(timezone.utc).isoformat();started=time.perf_counter()
        coverage=module.validate(grid['width'],grid['height'],*streams,roots,seed_roots,
            required_codes=map(int,report['categories']),seed_rules=seed['seed_rules'],
            expected_rule_population=seed['rule_population'],expected_category_counts=seed['category_cell_counts'])
        preflight_seconds=time.perf_counter()-started;started=time.perf_counter()
        output=write_module.write_land_stream(grid['width'],grid['height'],*streams,rootfile,codefile,seed_roots,
            out/name,disk_reserve_bytes=config['controls']['minimum_free_bytes'],delta_rule=delta)
        results[name]={'preflight_seconds':preflight_seconds,'writer_seconds':time.perf_counter()-started,
            'started_at_utc':begin,'completed_at_utc':datetime.now(timezone.utc).isoformat(),'coverage':coverage,'writer':output}
        write_json_exclusive(out/(name+'.json'),results[name],indent=2)
    if results['reference']['coverage']!=results['candidate']['coverage'] or results['candidate']['coverage']!=report['physical_coverage']:
        raise ValueError('complete coverage differs')
    if results['reference']['writer']!=results['candidate']['writer']:
        raise ValueError('complete writer reports differ')
    for name in results:
        for kind in ('rows','runs'):
            if digest(out/name/(kind+'.u32le'))!=report['output_'+kind+'_sha256']:
                raise ValueError('complete land output differs: '+name+'/'+kind)
    staged_inputs(staged)
    if (old_code!={name:digest(baseline_code/name) for name in code_names} or new_code!={name:digest(STAGE2/name) for name in code_names} or
            pins!={name:digest(source_replay/name) for name in pins} or digest(snapshot)!=config['inputs']['decision_snapshot']['sha256'] or
            digest(Path(__file__))!=invocation['driver_sha256']):
        raise ValueError('comparison code or source-bound input changed')
    result={**invocation,'status':'all-complete-old-new-land-bytes-and-reports-identical','results':results,
        'reference_over_candidate':{name:results['reference'][name]/results['candidate'][name] for name in ('preflight_seconds','writer_seconds')},
        'limits':'One paired run in the recorded order; cache order is not balanced. Not a whole-stage or end-to-end speed ratio.'}
    write_json_exclusive(out/'comparison.json',result,indent=2)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--staged-inputs',type=Path,required=True);parser.add_argument('--source-replay',type=Path,required=True)
    parser.add_argument('--baseline-code',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--candidate-first',action='store_true')
    args=parser.parse_args()
    print(json.dumps(compare(args.staged_inputs,args.source_replay,args.baseline_code,args.out,candidate_first=args.candidate_first),indent=2))


if __name__=='__main__':main()
