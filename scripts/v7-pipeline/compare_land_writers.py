#!/usr/bin/env python3
"""Pair full legacy/numeric writers using fresh source-bound assignments.

No old expected label supplies an assignment. A completed authenticated search
checkpoint is finalized again; archived labels are only the final byte oracle.
"""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
import time

import numpy as np

from benchmark_land_sweep import STAGE2,digest
from compare_land_sweeps import source_module
from exclusive_outputs import create_directory_exclusive,write_json_exclusive
from replay_land_sweep import staged_inputs
import checkpoints
import contracts
import engine


def modules(pins):
    names=('ural_delta','write_land_stream','row_overlay');previous={name:sys.modules.get(name) for name in names}
    try:
        rule=source_module('_numeric_writer_rule',STAGE2/'ural_delta.py',pins['ural_delta.py']);sys.modules['ural_delta']=rule
        reference=source_module('_numeric_writer_reference',STAGE2/'write_land_stream.py',pins['write_land_stream.py'])
        sys.modules['write_land_stream']=reference
        sys.modules['row_overlay']=source_module('_numeric_writer_overlay',STAGE2/'row_overlay.py',pins['row_overlay.py'])
        candidate=source_module('_numeric_writer_candidate',STAGE2/'numeric_land_stream.py',pins['numeric_land_stream.py'])
        return rule,reference,candidate
    finally:
        for name,module in previous.items():
            if module is None:sys.modules.pop(name,None)
            else:sys.modules[name]=module


def compare(staged,replay,out,*,candidate_first=False,batch_rows=128):
    if type(batch_rows) is not int or batch_rows<1:raise ValueError('invalid row batch')
    staged,replay=(Path(path).resolve(strict=True) for path in (staged,replay))
    plan,config,report,paths=staged_inputs(staged)
    completed=json.loads((replay/'comparison.json').read_bytes());identity=json.loads((replay/'invocation.json').read_bytes())
    if completed['status']!='complete-source-bound-search-and-land-streams-identical' or completed['staging_plan_sha256']!=digest(staged/'plan.json'):
        raise ValueError('complete source-bound replay required')
    for module in (checkpoints,contracts,engine):
        name=module.__name__+'.py'
        if Path(module.__file__).resolve()!=STAGE2/name or digest(STAGE2/name)!=identity['code_sha256'][name]:
            raise ValueError('source replay dependency differs: '+name)
    roots=np.fromfile(paths['hint_roots'],dtype='<u4');meta,arrays=checkpoints.read(replay/'checkpoint.npz',identity,roots)
    if meta['phase']!='complete' or meta['cursor']!=paths['component_runs'].stat().st_size//12:raise ValueError('source checkpoint is incomplete')
    decisions,ties=engine.finalize(arrays['hints'],arrays['amb'],arrays['best'],contracts.policy_tolerance_metres(report['land_baseline_policy']),numerical_tie_guard_m=.0001)
    rootfile,codefile=replay/'roots.u32le',replay/'codes.u8'
    if (ties!=report['ties'] or not np.array_equal(np.fromfile(rootfile,dtype='<u4'),roots) or
            not np.array_equal(np.fromfile(codefile,dtype='u1'),decisions)):raise ValueError('source-bound assignments differ')
    names=('write_land_stream.py','numeric_land_stream.py','row_overlay.py','ural_delta.py')
    pins={name:digest(STAGE2/name) for name in names};rule,reference,candidate=modules(pins)
    extra_hash=digest(staged/'search-inputs.json')
    extra=json.loads((staged/'search-inputs.json').read_bytes());snapshot=Path(extra['inputs']['decision_snapshot']['path'])
    if extra['parent_plan_sha256']!=digest(staged/'plan.json') or digest(snapshot)!=config['inputs']['decision_snapshot']['sha256']:
        raise ValueError('source snapshot differs')
    delta=rule.compile_rule(json.loads(snapshot.read_bytes()),report['categories'],config['grid'])
    source_pins={name:digest(replay/name) for name in ('comparison.json','invocation.json','checkpoint.npz','roots.u32le','codes.u8')}
    invocation={'schema':'worldatlas-complete-numeric-land-writer-pair-v1','staging_plan_sha256':digest(staged/'plan.json'),
        'code_sha256':pins,'source_replay_sha256':source_pins,'search_inputs_sha256':extra_hash,
        'snapshot_sha256':config['inputs']['decision_snapshot']['sha256'],'driver_sha256':digest(Path(__file__)),
        'candidate_batch_rows':batch_rows,'order':['candidate','reference'] if candidate_first else ['reference','candidate']}
    create_directory_exclusive(out);write_json_exclusive(out/'invocation.json',invocation,indent=2)
    grid=config['grid'];seed_roots=report['physical_coverage']['seed_roots']
    streams=[paths[name] for name in ('component_rows','component_runs','physical_rows','physical_runs','seed_rows','seed_runs')]
    results={}
    for name in invocation['order']:
        module=candidate if name=='candidate' else reference
        started_at=datetime.now(timezone.utc).isoformat();start=time.perf_counter()
        result=module.write_land_stream(grid['width'],grid['height'],*streams,rootfile,codefile,seed_roots,out/name,
            disk_reserve_bytes=config['controls']['minimum_free_bytes'],delta_rule=delta,
            **({'batch_rows':batch_rows} if name=='candidate' else {}))
        results[name]={'elapsed_seconds':time.perf_counter()-start,'report':result,
            'started_at_utc':started_at,'completed_at_utc':datetime.now(timezone.utc).isoformat()}
        write_json_exclusive(out/(name+'.json'),results[name],indent=2)
    if results['reference']['report']!=results['candidate']['report']:raise ValueError('complete writer reports differ')
    for name in results:
        for kind in ('rows','runs'):
            if digest(out/name/(kind+'.u32le'))!=report['output_'+kind+'_sha256']:raise ValueError('complete land output differs')
        if results[name]['report'].get('ural_delta')!=report.get('ural_delta'):raise ValueError('Ural counts differ')
    staged_inputs(staged)
    if (pins!={name:digest(STAGE2/name) for name in names} or source_pins!={name:digest(replay/name) for name in source_pins}
            or digest(Path(__file__))!=invocation['driver_sha256'] or digest(staged/'plan.json')!=invocation['staging_plan_sha256']
            or digest(staged/'search-inputs.json')!=extra_hash or digest(snapshot)!=invocation['snapshot_sha256']):
        raise ValueError('writer source/code identity changed')
    result={**invocation,'status':'complete-land-writer-bytes-and-reports-identical','results':results,
        'reference_over_candidate':results['reference']['elapsed_seconds']/results['candidate']['elapsed_seconds'],
        'limits':['One writer-only pair; cache order is not balanced.',
            'No production switch, source construction, search or geography acceptance is included.']}
    write_json_exclusive(out/'comparison.json',result,indent=2);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--staged-inputs',type=Path,required=True);parser.add_argument('--source-replay',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True);parser.add_argument('--candidate-first',action='store_true')
    parser.add_argument('--batch-rows',type=int,default=128);args=parser.parse_args()
    print(json.dumps(compare(args.staged_inputs,args.source_replay,args.out,candidate_first=args.candidate_first,batch_rows=args.batch_rows),indent=2))
