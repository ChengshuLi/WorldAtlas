#!/usr/bin/env python3
"""Verify and time complete Python land sweeps on a completed run's local inputs.

This does not launch the pipeline, contact a service, compile code or start a
process. It verifies every consumed source/checkpoint pin, runs the complete
coverage and writer sweeps, and checks all output bytes and Ural populations.
It excludes seed construction, WGS84 search and regional application.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import numpy as np

SCRIPTS = Path(__file__).resolve().parents[1]
STAGE2 = SCRIPTS / 'v7-recovery/land/stage2-geodesic-20261104'
for directory in (SCRIPTS, STAGE2):
    if str(directory) not in sys.path:
        sys.path.append(str(directory))
from exclusive_outputs import create_directory_exclusive, write_json_exclusive
import contracts
import engine
import numeric_preflight as preflight
import ural_delta
from numeric_land_stream import write_land_stream


def digest(path):
    hasher=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1 << 20),b''):
            hasher.update(block)
    return hasher.hexdigest()


def checked(pin):
    path=Path(pin['path']).resolve(strict=True)
    if digest(path)!=pin['sha256']:
        raise ValueError('land sweep input hash mismatch: '+str(path))
    return path


def benchmark(reference, out):
    reference=reference.resolve(strict=True)
    stage=reference/'stage2-provisional-only'
    config_path=reference/'work/stage2-provisional-only/core-requests/config.json'
    report_path=stage/'report.json'
    report_bytes=report_path.read_bytes();report=json.loads(report_bytes)
    report_hash=hashlib.sha256(report_bytes).hexdigest()
    expected={name:report['output_'+kind+'_sha256'] for kind,name in (('rows','rows.u32le'),('runs','runs.u32le'))}
    if any(digest(stage/name)!=value for name,value in expected.items()):
        raise ValueError('reference land streams differ from completed producer report')
    if digest(config_path)!=report['config_sha256']:
        raise ValueError('core config differs from completed land report')
    config=json.loads(config_path.read_bytes())
    names=('component_rows','component_runs','physical_rows','physical_runs','seed_rows','seed_runs',
           'seed_report','decision_snapshot','hint_roots')
    pins={name:config['inputs'][name] for name in names}
    if any(pin['sha256']!=report['inputs_sha256'][name] for name,pin in pins.items()):
        raise ValueError('land input identity differs from completed report')
    paths={name:checked(pin) for name,pin in pins.items()}
    checkpoint=reference/'work/stage2-provisional-only/core/checkpoint.npz'
    checkpoint_hash=digest(checkpoint)
    if checkpoint_hash!=report['checkpoint_sha256']:
        raise ValueError('checkpoint differs from completed land report')
    roots=np.fromfile(paths['hint_roots'],dtype='<u4')
    with np.load(checkpoint,allow_pickle=False) as values:
        if not np.array_equal(values['roots'],roots):
            raise ValueError('checkpoint root inventory differs')
        codes,ties=engine.finalize(values['hints'],values['amb'],values['best'],
            contracts.policy_tolerance_metres(report['land_baseline_policy']),numerical_tie_guard_m=.0001)
    if ties!=report['ties']:
        raise ValueError('checkpoint tie decisions differ')
    grid=config['grid'];seed_roots=report['physical_coverage']['seed_roots']
    seed=json.loads(paths['seed_report'].read_bytes())
    delta=ural_delta.compile_rule(json.loads(paths['decision_snapshot'].read_bytes()),report['categories'],grid)
    code={name:digest(STAGE2/name) for name in ('numeric_preflight.py','numeric_land_stream.py','row_overlay.py','write_land_stream.py','ural_delta.py','engine.py','contracts.py')}
    invocation={'schema':'worldatlas-python-land-sweep-benchmark-v1','reference':str(reference),
        'inputs':pins,'reference_report_sha256':report_hash,'config_sha256':report['config_sha256'],
        'expected_output_sha256':expected,'checkpoint_sha256':checkpoint_hash,'code_sha256':code,'python':sys.version,
        'platform':list(os.uname()),'cpu_affinity':sorted(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None,
        'scope':'complete coverage and writer only; excludes fresh source, search and regional work'}
    create_directory_exclusive(out)
    write_json_exclusive(out/'invocation.json',invocation,indent=2)
    rootfile,codefile=out/'roots.u32le',out/'codes.u8'
    roots.tofile(rootfile);codes.astype('u1').tofile(codefile)
    streams=[paths[name] for name in names[:6]]
    started=time.perf_counter()
    coverage=preflight.validate(grid['width'],grid['height'],*streams,roots,seed_roots,
        required_codes=map(int,report['categories']),seed_rules=seed['seed_rules'],
        expected_rule_population=seed['rule_population'],expected_category_counts=seed['category_cell_counts'],
        batch_rows=preflight.DEFAULT_BATCH_ROWS)
    coverage_seconds=time.perf_counter()-started
    started=time.perf_counter()
    writer=write_land_stream(grid['width'],grid['height'],*streams,rootfile,codefile,seed_roots,
        out/'candidate',disk_reserve_bytes=0,delta_rule=delta)
    writer_seconds=time.perf_counter()-started
    if coverage!=report['physical_coverage']:
        raise ValueError('complete physical/component/seed coverage differs')
    if writer.get('ural_delta')!=report.get('ural_delta'):
        raise ValueError('complete Ural cell-side populations differ')
    for name in ('rows.u32le','runs.u32le'):
        if digest(out/'candidate'/name)!=expected[name] or digest(stage/name)!=expected[name]:
            raise ValueError('complete land stream differs: '+name)
    for pin in pins.values():checked(pin)
    if digest(report_path)!=report_hash or digest(config_path)!=report['config_sha256'] or digest(checkpoint)!=checkpoint_hash:
        raise ValueError('config or checkpoint changed during comparison')
    if code!={name:digest(STAGE2/name) for name in code}:
        raise ValueError('land sweep code changed during comparison')
    result={**invocation,'status':'all-complete-land-streams-and-coverage-identical',
        'preflight_seconds':coverage_seconds,'writer_seconds':writer_seconds,'writer':writer,'coverage':coverage}
    write_json_exclusive(out/'comparison.json',result,indent=2)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference-run',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(benchmark(args.reference_run,args.out),indent=2))


if __name__=='__main__':main()
