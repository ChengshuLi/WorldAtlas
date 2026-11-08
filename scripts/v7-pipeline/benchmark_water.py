#!/usr/bin/env python3
"""Rebuild the complete water stage on pinned completed physical and land input.

The supported pipeline produces every basin, coast tile, prefill, ocean,
enclosed-water and final stream afresh. Comparison is outside the measured
water interval. Run timing workloads sequentially, without watchdogs or caps.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

from benchmark_stage import environment
from execution_state import verify_pins
from exclusive_outputs import create_directory_exclusive, write_json_exclusive
from run_pipeline import Pipeline, pin, read, validate_runtime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'v7-replay'))
from compare_grids import compare


def benchmark(reference, config, out):
    reference, config = reference.resolve(strict=True), config.resolve(strict=True)
    out = out.resolve()
    if out.is_relative_to(reference) or reference.is_relative_to(out):
        raise ValueError('benchmark output and reference must be disjoint')
    report = read(reference / 'report.json')
    if not all(report['stages'][stage]['outputs_complete'] for stage in ('physical', 'mainland', 'water')):
        raise ValueError('completed physical, land and water reference outputs required')
    verify_pins(report['final'].values())
    physical, land = reference / 'physical/physical', reference / 'land'
    inputs = {key: pin(path) for key, path in {
        'physical_report': physical / 'report.json', 'land_report': land / 'report.json',
        'physical_rows': physical / 'rows.u32le', 'physical_runs': physical / 'runs.u32le',
        'land_rows': land / 'rows.u32le', 'land_runs': land / 'runs.u32le'}.items()}
    grid = read(physical / 'report.json')['grid']
    validate_runtime()
    invocation = {'config': pin(config), 'inputs': inputs, 'reference_run': str(reference),
                  'reference_report': pin(reference / 'report.json'),
                  'environment': environment(),
                  'scope': 'fresh complete water stage on already-local physical and land input'}
    create_directory_exclusive(out)
    write_json_exclusive(out / 'invocation.json', invocation, indent=2)
    started = time.perf_counter()
    pipeline = Pipeline(config, out / 'candidate', allow_provisional=True)
    try:
        with pipeline.timing.measure('water', 'stage-total'):
            final = pipeline.water(physical, land)
        pipeline.timing.mark_complete('water')
        wall = time.perf_counter() - started
        timing = pipeline.timing.summary(None)['water']
    finally:
        pipeline.close()
    write_json_exclusive(out / 'stage-timing.json',
                         {**invocation, 'process_wall_seconds': wall, 'water': timing}, indent=2)
    verify_pins([invocation['config'], invocation['reference_report'], *inputs.values()])
    comparison = compare(final, reference / 'final', grid['width'], grid['height'],
                         {name: report['final'][key]['sha256'] for key, name in
                          (('rows', 'rows.u32le'), ('runs', 'runs.u32le'))}, out / 'comparison.json')
    if comparison['changed_cells'] or not comparison['byte_identical']:
        raise ValueError('fresh water output differs from the complete reference')
    return {'process_wall_seconds': wall, 'water': timing, 'comparison': comparison}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference-run', type=Path, required=True)
    parser.add_argument('--config', type=Path, help='original pinned pipeline configuration')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(benchmark(args.reference_run, args.config or args.reference_run / 'request.json',
                               args.out), indent=2))


if __name__ == '__main__':
    main()
