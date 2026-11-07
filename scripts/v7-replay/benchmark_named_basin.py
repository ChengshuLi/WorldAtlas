#!/usr/bin/env python3
"""Rerun an admitted full basin stage and independently compare every output span.

Inputs, options and interpreter are copied from an immutable pipeline admission.
Only the builder checkout, fresh output and explicit classifier option change.
Download time and the later coverage/comparison checks are not processing time.
This is a benchmark driver, not a resource monitor or a process supervisor.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from exclusive_outputs import create_text_exclusive, write_json_exclusive
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'v7-pipeline'))
from benchmark_stage import run_stage


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def assignment_comparison(reference, candidate, width, height):
    """Compare complete ordered spans without expanding cells or trusting counts."""
    counts = {'rows': 0, 'cells': 0, 'spans': 0}
    hashes = [hashlib.sha256(), hashlib.sha256()]

    def records(path, h):
        previous = -1
        with gzip.open(path, 'rb') as stream:
            for line in stream:
                h.update(line)
                record = json.loads(line)
                y = record.get('row')
                if type(y) is not int or not previous < y < height:
                    raise ValueError('invalid assignment row order')
                previous = y
                end = 0
                spans = record.get('spans')
                if not isinstance(spans, list) or not spans:
                    raise ValueError('empty assignment row')
                for z in spans:
                    a, b, c = z.get('start'), z.get('end'), z.get('code')
                    if (any(type(v) is not int for v in (a, b, c))
                            or not 0 <= a < b <= width or a < end or not 1 <= c <= 6
                            or not isinstance(z.get('rule_id'), str)
                            or not isinstance(z.get('member_id'), str)):
                        raise ValueError('invalid assignment span')
                    end = b
                yield record

    for old, new in itertools.zip_longest(records(reference, hashes[0]), records(candidate, hashes[1])):
        if old is None or new is None or old != new:
            raise ValueError(f'assignment mismatch near row {old and old.get("row")} / {new and new.get("row")}')
        counts['rows'] += 1
        counts['spans'] += len(new['spans'])
        counts['cells'] += sum(z['end'] - z['start'] for z in new['spans'])
    return {**counts, 'all_records_equal': True,
            'decompressed_bytes_equal': hashes[0].digest() == hashes[1].digest(),
            'reference_decompressed_sha256': hashes[0].hexdigest(),
            'candidate_decompressed_sha256': hashes[1].hexdigest()}



def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--admitted', type=Path, required=True)
    ap.add_argument('--reference', type=Path, required=True, help='completed baseline basin directory')
    ap.add_argument('--out', type=Path, required=True, help='fresh benchmark directory')
    ap.add_argument('--classifier', choices=('default', 'interval', 'rectangles', 'point'), default='default')
    args = ap.parse_args()
    baseline = json.loads((args.reference / 'manifest.json').read_text())
    out = args.out.absolute()
    extra = {'default': [], 'interval': ['--research-interval'], 'point': ['--pointwise-nearest'], 'rectangles': ['--research-rectangles']}[args.classifier]
    timing = run_stage(args.admitted, Path(__file__).resolve().parents[2], out, extra, drop_boolean_options=('--research-interval','--research-rectangles','--pointwise-nearest'))
    candidate = out / 'candidate'
    command = timing['command']
    builder = Path(command[1])
    result = json.loads((candidate / 'manifest.json').read_text())
    if result['algorithm_sha256'] != timing['builder_sha256']:
        raise ValueError('builder changed between benchmark admission and stage startup')
    # Equal source pins, raster bytes and grid prevent accidental changed-input
    # "speedups". Processing counters are checked against parsed full outputs.
    for key in ('source', 'grid', 'rasterization'):
        if baseline[key] != result[key]:
            raise ValueError(f'baseline/candidate {key} differs')
    comparison = assignment_comparison(args.reference / 'basin-assignment.jsonl.gz',
                                       candidate / 'basin-assignment.jsonl.gz',
                                       result['grid']['width'], result['grid']['height'])
    if any(comparison[k] != result[m] or comparison[k] != baseline[m]
           for k, m in (('cells', 'physical_water_cells'), ('rows', 'row_count'), ('spans', 'span_count'))):
        raise ValueError('parsed assignment counts do not match manifests')
    def option(name):
        return command[command.index(name) + 1]
    verify = [command[0], str(builder.with_name('verify_basin_coverage.py')),
              '--manifest', str(candidate / 'manifest.json'), '--manifest-sha256', digest(candidate / 'manifest.json'),
              '--physical-rows', option('--rows'), '--physical-runs', option('--runs'),
              '--policy', option('--policy'), '--policy-sha256', option('--policy-sha256')]
    if '--allow-draft-snapshot' in command:
        verify.append('--allow-draft-snapshot')
    with create_text_exclusive(out / 'coverage.log') as log:
        subprocess.run(verify, check=True, stdout=log, stderr=subprocess.STDOUT)
    report = {'schema': 'worldatlas-named-basin-benchmark-v1', 'status': 'full-input-exact-match',
              'command': command, 'environment': timing['environment'], 'comparison': comparison,
              'baseline_processing_seconds': baseline['processing_elapsed_seconds'],
              'candidate_processing_seconds': result['processing_elapsed_seconds'],
              'candidate_process_wall_seconds': timing['process_wall_seconds'],
              'speedup': baseline['processing_elapsed_seconds'] / result['processing_elapsed_seconds'],
              'coverage_verification': json.loads((out / 'coverage.log').read_text()),
              'baseline_timing_source': 'completed original stage manifest; not rerun by this driver',
              'candidate_algorithm_sha256': result['algorithm_sha256'],
              'candidate_nearest_assignment_audit': result['nearest_assignment_audit'],
              'candidate_manifest_sha256': digest(candidate / 'manifest.json'),
              'reference_manifest_sha256': digest(args.reference / 'manifest.json')}
    write_json_exclusive(out / 'report.json', report, indent=2)
    print(json.dumps(report))


if __name__ == '__main__':
    main()
