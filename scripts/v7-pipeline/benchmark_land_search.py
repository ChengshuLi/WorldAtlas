#!/usr/bin/env python3
"""Replay every global component query against authenticated current seeds.

This diagnoses the search kernel separately from source production and regional
policy application. The reference checkpoint is used only after the search, as
an expected result. No historical assignment is used to select a candidate.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import resource
import sys
import time

import numpy as np

from benchmark_stage import digest, environment
from exclusive_outputs import create_directory_exclusive, write_json_exclusive

REPO = Path(__file__).resolve().parents[2]
STAGE2 = REPO / 'scripts/v7-recovery/land/stage2-geodesic-20261104'


def run(reference, out):
    sys.path.insert(0, str(STAGE2))
    import baseline_runner, build_stage2, checkpoints, contracts, engine, verify_inputs, verify_seed_index
    reference = reference.resolve(strict=True)
    core = reference / 'work/stage2-provisional-only/core'
    cfg = json.loads((core.parent / 'core-requests/config.json').read_text())
    report = json.loads((reference / 'stage2-provisional-only/report.json').read_text())
    if digest(core.parent / 'core-requests/config.json') != report['config_sha256']:
        raise ValueError('core configuration differs from completed producer report')
    create_directory_exclusive(out)
    controls = cfg['controls'];grid = cfg['grid'];width = grid['width'];height = grid['height']
    guard = lambda: checkpoints.guard(out, controls['minimum_free_bytes'])
    used = ('component_rows', 'component_runs', 'hint_roots', 'hint_codes', 'representatives',
            'tile_manifest', 'seed_rows', 'seed_runs')
    if any(cfg['inputs'][name]['sha256'] != report['inputs_sha256'][name] for name in used):
        raise ValueError('search inputs differ from completed producer report')
    paths = {name: build_stage2.pin(cfg['inputs'][name], guard) for name in used}
    checkpoint = core / 'checkpoint.npz'
    if digest(checkpoint) != report['checkpoint_sha256']:
        raise ValueError('reference checkpoint does not match completed producer report')
    # Independently verify every tile against every current seed run before
    # constructing any spatial bound. This is not timed as search work.
    verify_seed_index.verify(paths['seed_rows'],paths['seed_runs'],cfg['tile_directory'],width,height,1024,guard)
    reps = np.fromfile(paths['representatives'], dtype='<u4').reshape(-1, 5)
    tiles = verify_inputs.verify_representatives(cfg['tile_directory'], paths['tile_manifest'],
                                                 reps, width, height, guard=guard)
    roots = np.fromfile(paths['hint_roots'], dtype='<u4')
    hints = np.fromfile(paths['hint_codes'], dtype='u1')
    seeds = report['physical_coverage']['seed_roots']
    offsets = engine.offsets(paths['component_rows'], height, paths['component_runs'].stat().st_size // 12)
    tolerance = contracts.policy_tolerance_metres(report['land_baseline_policy'])
    identity = {'schema': 'worldatlas-land-search-benchmark-v1',
                'inputs': {name: cfg['inputs'][name] for name in used},
                'code': {name: digest(STAGE2 / name) for name in build_stage2.CODE_NAMES},
                'environment': environment()}
    write_json_exclusive(out / 'invocation.json', identity, indent=2)
    started = time.perf_counter()
    cert, exact = build_stage2.search_indexes(cfg['tile_directory'], grid, tiles, reps, controls)
    indexed = time.perf_counter()
    def progress(phase, cursor, queries):
        with (out / 'progress.jsonl').open('a') as stream:
            stream.write(json.dumps({'phase': phase, 'cursor': cursor, 'queries': queries,
                                     'seconds': time.perf_counter() - started}) + '\n')
    result = baseline_runner.run(paths['component_runs'], offsets, roots, hints, seeds, width,
                                 cert, exact, out / 'checkpoint.npz', identity,
                                 chunk=controls['chunk_columns'], tolerance=tolerance,
                                 disk_floor_bytes=controls['minimum_free_bytes'],
                                 checkpoint_seconds=controls['checkpoint_seconds'],
                                 block_records=controls['block_records'], guard=guard, progress=progress)
    elapsed = time.perf_counter() - started
    # Only now read the expected root decisions. They never supplied a hint,
    # upper bound, certificate, stopping condition, or assignment to the run.
    with np.load(checkpoint, allow_pickle=False) as old:
        if not np.array_equal(old['roots'], result['roots']):raise ValueError('root inventory differs')
        expected, ties = engine.finalize(old['hints'], old['amb'], old['best'], tolerance,
                                         numerical_tie_guard_m=.0001)
    if not np.array_equal(expected, result['codes']) or ties != result['ties']:
        raise ValueError('global WGS84 root decisions differ')
    for name in used:build_stage2.pin(cfg['inputs'][name], guard)
    if any(digest(STAGE2 / name) != value for name, value in identity['code'].items()):
        raise ValueError('search code changed during benchmark')
    result['codes'].astype('u1').tofile(out / 'codes.u8')
    output = {'status': 'all-global-component-codes-and-ties-identical',
              'component_count': len(roots), 'search_and_index_seconds': elapsed,
              'index_seconds': indexed - started, 'runner_seconds': elapsed - (indexed - started),
              'certified_components': result['certified_count'], 'exact_components': result['exact_count'],
              'exact_queries': result['exact_queries'], 'codes_sha256': digest(out / 'codes.u8'),
              'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              'scope': 'complete global search and fresh spatial index; excludes source production and regional application'}
    write_json_exclusive(out / 'comparison.json', output, indent=2)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference-run', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.reference_run, args.out), indent=2))


if __name__ == '__main__':
    main()
