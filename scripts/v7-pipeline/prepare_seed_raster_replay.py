#!/usr/bin/env python3
"""Recover pinned seed polygons through normal fresh closure/region checks.

This is a source-region research replay, not a pipeline launch or geography
acceptance. No stored closure proof is substituted for a fresh check, and no
historical source document is rewritten.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time

from benchmark_land_sweep import STAGE2, digest
from compare_land_sweeps import source_module
from exclusive_outputs import create_directory_exclusive, write_json_exclusive
from run_pipeline import stage_scratch

SEED=STAGE2/'seed-producer'
LAND=STAGE2.parent
SCRIPTS=STAGE2.parents[2]


@contextmanager
def producer_modules():
    names=('regions','closure_client','export_adapter','region_client')
    previous={name:sys.modules.get(name) for name in names};modules={};pins={}
    try:
        for name in names:
            path=SEED/(name+'.py');pins[name]=digest(path)
            modules[name]=source_module('_seed_replay_'+name,path,pins[name])
            sys.modules[name]=modules[name]
        yield modules,pins
    finally:
        for name,module in previous.items():
            if module is None:sys.modules.pop(name,None)
            else:sys.modules[name]=module


def physical_equivalence(current, prior, grid, rows_hash, runs_hash):
    for label,report in (('current',current),('prior',prior)):
        output=report.get('physical_output_sha256',report.get('output_sha256',{}))
        if (report.get('status') not in ('candidate-only','stage1-complete') or report.get('grid')!=grid or
                output.get('rows.u32le')!=rows_hash or output.get('runs.u32le')!=runs_hash):
            raise ValueError(label+' physical report is not byte-equivalent')


def closure_contract(grid, rows_hash, runs_hash, report_hash, producer):
    return {'schema':'physical-water-closure-contract-v2',
        'grid':{'crs':'EPSG:4326','width':grid['width'],'height':grid['height'],'west':grid['west'],'north':grid['north'],
                'step_numerator':360,'step_denominator':grid['width']},
        'physical':{'rows_sha256':rows_hash,'runs_sha256':runs_hash,'report_sha256':report_hash,
            'water_code':1,'land_code':17,'producer_code_path':str(producer.resolve()),'encoding_evidence_sha256':digest(producer)},
        # Same ordinary source contract as the supported pipeline. The checker
        # records this historical visit setting but does not enforce a ceiling.
        'resources':{'max_cell_visits':2000000}}


def prepare(staged, prior_report_path, out, *, allow_local_provisional=False):
    started=time.perf_counter();staged=staged.resolve(strict=True)
    plan=json.loads((staged/'plan.json').read_bytes());assets=plan['assets']
    if plan['schema']!='worldatlas-land-sweep-staging-plan-v1':raise ValueError('unknown staging plan')
    names=('fresh-stage2-core-config','fresh-physical-rows','fresh-physical-runs','fresh-physical-report','fresh-stage2-seed-report')
    paths={name:staged/name for name in names}
    for name,path in paths.items():
        if path.stat().st_size!=assets[name]['size_bytes'] or digest(path)!=assets[name]['sha256']:
            raise ValueError('staged source size/hash mismatch: '+name)
    config=json.loads(paths['fresh-stage2-core-config'].read_bytes());grid=config['grid']
    if assets['fresh-stage2-core-config']['sha256']!=plan['core_config_sha256'] or grid!=plan['grid']:
        raise ValueError('staged core identity differs')
    for field,source in (('physical_rows','fresh-physical-rows'),('physical_runs','fresh-physical-runs'),
                         ('physical_report','fresh-physical-report'),('seed_report','fresh-stage2-seed-report')):
        if config['inputs'][field]['sha256']!=assets[source]['sha256']:raise ValueError('core source binding differs: '+field)
    extra_path=staged/'search-inputs.json';extra=json.loads(extra_path.read_bytes())
    if extra['parent_plan_sha256']!=digest(staged/'plan.json'):raise ValueError('snapshot staging identity differs')
    snapshot_pin=extra['inputs']['decision_snapshot'];snapshot_path=Path(snapshot_pin['path']).resolve(strict=True)
    if digest(snapshot_path)!=snapshot_pin['sha256'] or snapshot_pin['sha256']!=config['inputs']['decision_snapshot']['sha256']:
        raise ValueError('decision snapshot pin differs')
    seed=json.loads(paths['fresh-stage2-seed-report'].read_bytes())
    raster_path=staged/'additional-metadata/fresh-stage2-rasterizer-report'
    if digest(raster_path)!=seed['rasterizer_report_sha256']:raise ValueError('rasterizer report pin differs')
    raster=json.loads(raster_path.read_bytes())
    current=json.loads(paths['fresh-physical-report'].read_bytes())
    producer=SCRIPTS/'v7-raw-mask/compose_physical.py'
    checker=LAND/'mainland-source-verification-20261104/validate_water_closure_v2.py'
    terminal=LAND/'mainland-source-verification-20261104/validate_terminal_closure.py'
    code={str(path.relative_to(SCRIPTS)):digest(path) for path in (producer,checker,terminal,SEED/'region_worker.py')}
    identity={'schema':'worldatlas-seed-source-region-replay-v1','staging_plan_sha256':digest(staged/'plan.json'),
        'snapshot_sha256':snapshot_pin['sha256'],'rasterizer_report_sha256':digest(raster_path),'code_sha256':code,
        'driver_sha256':digest(Path(__file__)),'allow_local_provisional':allow_local_provisional,
        'started_at_utc':datetime.now(timezone.utc).isoformat()}
    with producer_modules() as (modules,producer_pins):
        adapter=modules['export_adapter'];snapshot=adapter.load_pinned_snapshot(snapshot_path,snapshot_pin['sha256'],lambda:None)
        local=snapshot.get('source')=='local-derived-from-neon-export'
        revision,entity,boundaries,sources=adapter.boundary_records(snapshot,allow_local=allow_local_provisional)
        decisions,records=adapter.selected_regions(snapshot,revision,boundaries,sources)
        equivalence=None
        if local:
            if prior_report_path is None or 'prior_physical_report' not in config['inputs']:
                raise ValueError('local provisional replay requires the pinned prior physical report')
            if digest(prior_report_path)!=config['inputs']['prior_physical_report']['sha256']:
                raise ValueError('prior physical report pin differs')
            prior=json.loads(prior_report_path.read_bytes())
            physical_equivalence(current,prior,grid,assets['fresh-physical-rows']['sha256'],assets['fresh-physical-runs']['sha256'])
            equivalence={'prior_report_sha256':digest(prior_report_path),'current_report_sha256':assets['fresh-physical-report']['sha256'],
                         'status':'exact-physical-stream-equivalence-provisional-only'}
        physical_equivalence(current,current,grid,assets['fresh-physical-rows']['sha256'],assets['fresh-physical-runs']['sha256'])
        create_directory_exclusive(out)
        identity['producer_code_sha256']=producer_pins;identity['provisional_physical_equivalence']=equivalence
        write_json_exclusive(out/'invocation.json',identity,indent=2)
        physical=create_directory_exclusive(out/'physical-input');contracts=create_directory_exclusive(out/'contract-input')
        work=create_directory_exclusive(out/'region-work');scratch=create_directory_exclusive(out/'scratch')
        regions=create_directory_exclusive(out/'regions')
        for name,source in (('rows.u32le','fresh-physical-rows'),('runs.u32le','fresh-physical-runs'),('report.json','fresh-physical-report')):
            os.link(paths[source],physical/name)
        contract=closure_contract(grid,assets['fresh-physical-rows']['sha256'],assets['fresh-physical-runs']['sha256'],assets['fresh-physical-report']['sha256'],producer)
        contract_path=contracts/'contract.json';write_json_exclusive(contract_path,contract,indent=2)
        closure={'checker_path':str(checker),'checker_sha256':digest(checker),'physical_dir':str(physical),
            'physical_rows_sha256':assets['fresh-physical-rows']['sha256'],'physical_runs_sha256':assets['fresh-physical-runs']['sha256'],
            'contract_path':str(contract_path),'contract_sha256':digest(contract_path),
            'terminal_checker_path':str(terminal),'terminal_checker_sha256':digest(terminal)}
        source_list=[{'source_id':key[0],'version':key[1],**value} for key,value in sources.items()]
        results=[]
        with stage_scratch(str(scratch)):
            for decision in decisions:
                result=modules['region_client'].execute({'schema':'stage2-region-worker-request-v1','revision_id':revision,
                    'records':list(records.values()),'sources':source_list,'decision':decision,'closure':closure},work,lambda:None)
                name=hashlib.sha256(decision['region_id'].encode()).hexdigest()+'.geojson'
                expected=[pin for pin in raster['input_pins'] if Path(pin['path']).name==name]
                if len(expected)!=1:raise ValueError('one exact archived polygon pin required: '+decision['region_id'])
                data=json.dumps({'type':'FeatureCollection','features':[{'type':'Feature','properties':{},'geometry':result['geometry']}]},
                                sort_keys=True,separators=(',',':'),allow_nan=False).encode()
                if hashlib.sha256(data).hexdigest()!=expected[0]['sha256']:
                    raise ValueError('fresh polygon differs from archived source: '+decision['region_id'])
                path=regions/name
                with path.open('xb') as stream:stream.write(data)
                receipt=regions/(name+'.report.json');write_json_exclusive(receipt,result,indent=2)
                results.append({'region_id':decision['region_id'],'geometry':{'path':str(path.resolve()),'sha256':expected[0]['sha256']},
                    'witnesses':decision['witnesses'],'report_sha256':digest(receipt)})
        for name,path in paths.items():
            if digest(path)!=assets[name]['sha256']:raise ValueError('staged source changed: '+name)
        if digest(snapshot_path)!=snapshot_pin['sha256'] or digest(raster_path)!=seed['rasterizer_report_sha256']:
            raise ValueError('snapshot or rasterizer report changed')
        for name,pin in producer_pins.items():
            if digest(SEED/(name+'.py'))!=pin:raise ValueError('producer source changed: '+name)
        if code!={name:digest(SCRIPTS/name) for name in code} or digest(Path(__file__))!=identity['driver_sha256']:
            raise ValueError('source replay code changed')
        result={**identity,'status':'exact-pinned-polygons-recreated-with-fresh-closure-proofs','publishable':False,
            'regions':results,'elapsed_seconds':time.perf_counter()-started,'completed_at_utc':datetime.now(timezone.utc).isoformat(),
            'limitations':['Research source replay, not provider authentication or geographic acceptance.',
                'The new contract binds unchanged historical physical streams; no raw physical rebuild was run.',
                'No stored closure proof was used as a substitute for fresh checker execution.']}
        write_json_exclusive(out/'report.json',result,indent=2)
        return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--staged-inputs',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--prior-physical-report',type=Path)
    parser.add_argument('--allow-local-provisional',action='store_true')
    args=parser.parse_args()
    print(json.dumps(prepare(args.staged_inputs,args.prior_physical_report,args.out,allow_local_provisional=args.allow_local_provisional),indent=2))


if __name__=='__main__':main()
