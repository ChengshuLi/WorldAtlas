#!/usr/bin/env python3
"""Pair complete preserved-source land kernels with old/new coverage checks.

Every trial independently rebuilds seed tiles, searches every component and
writes every output byte. This does not launch a raw-source/full pipeline or
change source decisions, reports or geographic acceptance.
"""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import time

from benchmark_land_sweep import STAGE2,digest
from exclusive_outputs import create_directory_exclusive,write_json_exclusive
import replay_land_sweep as driver


def compare(staged,out,*,candidate_first=False,compare_writer=False):
    # Authenticate the complete plan before creating the exclusive trial tree.
    driver.staged_inputs(staged)
    identity={'schema':'worldatlas-complete-land-coverage-integration-pair-v1',
        'comparison':'writer' if compare_writer else 'coverage','staging_plan_sha256':digest(staged/'plan.json'),'driver_sha256':digest(Path(__file__)),
        'replay_driver_sha256':digest(Path(driver.__file__)),'stage_builder_sha256':digest(STAGE2/'build_stage2.py'),
        'order':['candidate','reference'] if candidate_first else ['reference','candidate'],
        'scope':'complete preserved-source coverage + seed-index + WGS84 + writer kernels, not raw pipeline/geography acceptance'}
    create_directory_exclusive(out);write_json_exclusive(out/'invocation.json',identity,indent=2)
    results={}
    for name in identity['order']:
        started_at=datetime.now(timezone.utc).isoformat();start=time.perf_counter()
        result=driver.replay(staged,out/name,search=True,legacy_preflight=(name=='reference' and not compare_writer),
            writer_engine=('numeric' if name=='candidate' and compare_writer else 'legacy'))
        results[name]={'elapsed_seconds':time.perf_counter()-start,'started_at_utc':started_at,
            'completed_at_utc':datetime.now(timezone.utc).isoformat(),'result':result}
        write_json_exclusive(out/(name+'.json'),results[name],indent=2)
    reference=results['reference']['result'];candidate=results['candidate']['result']
    for field in ('status','coverage','writer','certified_components','exact_components','exact_queries','ties'):
        if reference[field]!=candidate[field]:raise ValueError('complete land replay differs: '+field)
    for name in results:
        for kind in ('rows','runs'):
            if digest(out/name/'candidate'/(kind+'.u32le'))!=results[name]['result']['writer'][kind+'_sha256']:
                raise ValueError('land output changed after trial')
    if (digest(staged/'plan.json')!=identity['staging_plan_sha256'] or digest(Path(__file__))!=identity['driver_sha256'] or
            digest(Path(driver.__file__))!=identity['replay_driver_sha256'] or digest(STAGE2/'build_stage2.py')!=identity['stage_builder_sha256']):
        raise ValueError('land comparison identity changed')
    result={**identity,'status':'complete-land-replays-all-decisions-bytes-and-reports-identical','results':results,
        'reference_over_candidate':results['reference']['elapsed_seconds']/results['candidate']['elapsed_seconds'],
        'limits':['One ordered pair; cache order is not balanced.',
            'Seed raster production and source/provider/regional admission are separate proofs, not included here.']}
    write_json_exclusive(out/'comparison.json',result,indent=2);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--staged-inputs',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--candidate-first',action='store_true');parser.add_argument('--compare-writer',action='store_true');args=parser.parse_args()
    print(json.dumps(compare(args.staged_inputs,args.out,candidate_first=args.candidate_first,compare_writer=args.compare_writer),indent=2))
