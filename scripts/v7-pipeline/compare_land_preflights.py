#!/usr/bin/env python3
"""Pair complete coverage sweeps, leaving the production default unchanged."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
import time

import numpy as np

from benchmark_land_sweep import STAGE2,digest
from compare_land_sweeps import rule_module,source_module,sweep_modules
from exclusive_outputs import create_directory_exclusive,write_json_exclusive
from replay_land_sweep import staged_inputs


def compare(staged,out,*,candidate_first=False):
    staged=Path(staged).resolve(strict=True)
    plan,config,report,paths=staged_inputs(staged)
    names=('preflight.py','write_land_stream.py','ural_delta.py','row_overlay.py','numeric_preflight.py')
    pins={name:digest(STAGE2/name) for name in names}
    reference,_=sweep_modules(STAGE2,pins,rule_module(pins['ural_delta.py']))
    previous=sys.modules.get('row_overlay')
    try:
        sys.modules['row_overlay']=source_module('_land_numeric_overlay',STAGE2/'row_overlay.py',pins['row_overlay.py'])
        candidate=source_module('_land_numeric_preflight',STAGE2/'numeric_preflight.py',pins['numeric_preflight.py'])
    finally:
        if previous is None:sys.modules.pop('row_overlay',None)
        else:sys.modules['row_overlay']=previous
    seed=json.loads(paths['seed_report'].read_bytes());roots=np.fromfile(paths['hint_roots'],dtype='<u4')
    grid=config['grid'];seed_roots=report['physical_coverage']['seed_roots']
    streams=[paths[name] for name in ('component_rows','component_runs','physical_rows','physical_runs','seed_rows','seed_runs')]
    identity={'schema':'worldatlas-numeric-land-preflight-pair-v1','staging_plan_sha256':digest(staged/'plan.json'),
        'code_sha256':pins,'driver_sha256':digest(Path(__file__)),
        'order':['candidate','reference'] if candidate_first else ['reference','candidate']}
    create_directory_exclusive(out);write_json_exclusive(out/'invocation.json',identity,indent=2)
    results={}
    for name in identity['order']:
        module=candidate if name=='candidate' else reference
        started_at=datetime.now(timezone.utc).isoformat();start=time.perf_counter()
        coverage=module.validate(grid['width'],grid['height'],*streams,roots,seed_roots,
            required_codes=map(int,report['categories']),seed_rules=seed['seed_rules'],
            expected_rule_population=seed['rule_population'],expected_category_counts=seed['category_cell_counts'])
        results[name]={'elapsed_seconds':time.perf_counter()-start,'coverage':coverage,
            'started_at_utc':started_at,'completed_at_utc':datetime.now(timezone.utc).isoformat()}
        write_json_exclusive(out/(name+'.json'),results[name],indent=2)
    if results['candidate']['coverage']!=results['reference']['coverage'] or results['reference']['coverage']!=report['physical_coverage']:
        raise ValueError('complete coverage/population reports differ')
    staged_inputs(staged)
    if pins!={name:digest(STAGE2/name) for name in names} or digest(Path(__file__))!=identity['driver_sha256'] or digest(staged/'plan.json')!=identity['staging_plan_sha256']:
        raise ValueError('source/code identity changed')
    result={**identity,'status':'complete-preflight-reports-identical','results':results,
        'reference_over_candidate':results['reference']['elapsed_seconds']/results['candidate']['elapsed_seconds'],
        'limitations':['One paired coverage sweep; cache order is not balanced.',
            'No production default, writer, search, seed or geography decision is changed.']}
    write_json_exclusive(out/'comparison.json',result,indent=2);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--staged-inputs',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--candidate-first',action='store_true');args=parser.parse_args()
    print(json.dumps(compare(args.staged_inputs,args.out,candidate_first=args.candidate_first),indent=2))
