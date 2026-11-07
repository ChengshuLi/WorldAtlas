#!/usr/bin/env python3
"""Rebuild the complete mainland stage on an existing pinned physical mask.

All components, seeds, representatives, hints, geodesic searches and regional
claims are produced afresh by the supported pipeline. The reference supplies
only the physical input and the expected outputs for subsequent comparison.
Run timing workloads sequentially. No resource limits or watchdogs are used.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

from benchmark_stage import digest, environment
from exclusive_outputs import create_directory_exclusive, write_json_exclusive
from run_pipeline import Pipeline, pin, read, validate_runtime


def compare_land(reference, candidate):
    results = {}
    for stage in ('components', 'stage2-provisional-only', 'land'):
        hashes = {}
        for name in ('rows.u32le', 'runs.u32le'):
            left, right = reference / stage / name, candidate / stage / name
            old, new = digest(left), digest(right)
            if old != new:
                raise ValueError(f'{stage}/{name} differs from the complete reference')
            hashes[name] = {'sha256': new, 'bytes': right.stat().st_size}
        results[stage] = hashes
    old, new = (read(root / 'stage2-provisional-only/report.json')
                for root in (reference, candidate))
    if old['ties'] != new['ties']:
        raise ValueError('WGS84 tie decisions differ')
    return {'status': 'all-component-and-land-stream-bytes-identical',
            'streams': results, 'geodesic_ties': new['ties'],
            'certified_components': new['certified_components'],
            'exact_search_components': new['exact_search_components'],
            'exact_queries': new['exact_queries']}


def benchmark(reference, config, out):
    reference = reference.resolve(strict=True)
    config = config.resolve(strict=True)
    physical = reference / 'physical/physical'
    validate_runtime()
    invocation = {'config': pin(config), 'physical_report': pin(physical / 'report.json'),
                  'reference_run': str(reference), 'environment': environment(),
                  'scope': 'fresh complete mainland stage on already-local physical input'}
    create_directory_exclusive(out)
    write_json_exclusive(out / 'invocation.json', invocation, indent=2)
    started = time.perf_counter()
    pipeline = Pipeline(config, out / 'candidate', allow_provisional=True)
    try:
        with pipeline.timing.measure('mainland', 'stage-total'):
            pipeline.mainland(physical)
        pipeline.timing.mark_complete('mainland')
        wall = time.perf_counter() - started
        timing = pipeline.timing.summary(None)['mainland']
    finally:
        pipeline.close()
    write_json_exclusive(out / 'stage-timing.json',
                         {**invocation, 'process_wall_seconds': wall, 'mainland': timing}, indent=2)
    comparison = compare_land(reference, out / 'candidate')
    write_json_exclusive(out / 'comparison.json', comparison, indent=2)
    return {'process_wall_seconds': wall, 'mainland': timing, **comparison}


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
