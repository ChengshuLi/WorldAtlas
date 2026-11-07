#!/usr/bin/env python3
"""Replay pinned enclosed-water inputs and compare every assignment and decision.

The complete admitted command is timed separately from the comparison. Source
inputs and reference outputs remain unchanged; both outputs must be hash-bound
by completed producer manifests.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import sqlite3

from benchmark_stage import digest, run_stage
from exclusive_outputs import write_json_exclusive


def compare_closed(reference, candidate):
    manifests = []
    for root in (reference, candidate):
        manifest = json.loads((root / 'manifest.json').read_text())
        if manifest.get('schema') != 'worldatlas-full-water-assignment-tiles-v1':
            raise ValueError('invalid closed-water manifest')
        for key, name in (('pending_file', 'pending-components.jsonl.gz'),
                          ('work_database', 'work.sqlite3')):
            spec = manifest.get(key, {})
            if spec.get('path') != name or digest(root / name) != spec.get('sha256'):
                raise ValueError('closed-water artifact hash mismatch: ' + name)
        tiles = manifest.get('tiles', [])
        if len(tiles) != 1 or tiles[0].get('span_file', {}).get('path') != 'closed-water-assignments.jsonl.gz':
            raise ValueError('invalid closed-water assignment inventory')
        if digest(root / 'closed-water-assignments.jsonl.gz') != tiles[0]['span_file'].get('sha256'):
            raise ValueError('closed-water assignment hash mismatch')
        manifests.append(manifest)
    semantic = ('schema', 'status', 'grid', 'coverage', 'source', 'assigned_cells', 'pending_cells',
                'pending_components', 'direct_components', 'mixed_components', 'input_span_count',
                'span_count', 'algorithm_parameters')
    if any(manifests[0].get(key) != manifests[1].get(key) for key in semantic):
        raise ValueError('closed-water scientific metadata differs')
    hashes = {}
    for name in ('closed-water-assignments.jsonl.gz', 'pending-components.jsonl.gz'):
        content = hashlib.sha256()
        with gzip.open(reference / name, 'rb') as left, gzip.open(candidate / name, 'rb') as right:
            while True:
                a, b = left.read(1 << 20), right.read(1 << 20)
                if a != b:
                    raise ValueError('closed-water decompressed bytes differ: ' + name)
                if not a:
                    break
                content.update(a)
        hashes[name] = content.hexdigest()
    databases = [sqlite3.connect((root / 'work.sqlite3').resolve().as_uri() + '?mode=ro', uri=True)
                 for root in (reference, candidate)]
    counts = {}
    try:
        for table, order in (('components', 'root'), ('spans', 'y,a'), ('mixed', 'y,a')):
            cursors = [db.execute(f'SELECT * FROM {table} ORDER BY {order}') for db in databases]
            count = 0
            for a, b in itertools.zip_longest(*cursors):
                if a != b:
                    raise ValueError('closed-water work decisions differ: ' + table)
                count += 1
            counts[table] = count
    finally:
        for db in databases:
            db.close()
    return {'status': 'all-assignment-bytes-and-component-decisions-identical',
            'assigned_cells': manifests[0]['assigned_cells'], 'pending_cells': manifests[0]['pending_cells'],
            'span_count': manifests[0]['span_count'], 'work_table_rows': counts,
            'decompressed_sha256': hashes, 'reference_manifest_sha256': digest(reference / 'manifest.json'),
            'candidate_manifest_sha256': digest(candidate / 'manifest.json')}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for key in ('admitted', 'reference', 'code-root', 'out'):
        ap.add_argument('--' + key, type=Path, required=True)
    args = ap.parse_args()
    admission = json.loads(args.admitted.read_text())
    if Path(admission['invocation']['command'][1]).name != 'build_closed_water.py':
        raise ValueError('a complete closed-water admission is required')
    timing = run_stage(args.admitted, args.code_root, args.out)
    comparison = compare_closed(args.reference, args.out / 'candidate')
    write_json_exclusive(args.out / 'comparison.json', comparison, indent=2)
    print(json.dumps({'process_wall_seconds': timing['process_wall_seconds'], **comparison}))


if __name__ == '__main__':
    main()
