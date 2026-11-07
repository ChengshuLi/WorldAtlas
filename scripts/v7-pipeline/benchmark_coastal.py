#!/usr/bin/env python3
"""Replay a complete pinned coastal batch and compare every emitted assignment.

Use a coastal batch admitted.json from the supported pipeline, the complete
reference batch, and the checkout to test. The replay is timed separately from
verification. Existing outputs and reference inputs are never overwritten.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
from pathlib import Path

from benchmark_stage import digest, run_stage
from exclusive_outputs import write_json_exclusive


def compare_batches(reference, candidate):
    def read_batch(root):
        batch = json.loads((root / 'batch-complete.json').read_text())
        if (batch.get('schema') != 'worldatlas-sealed-coastal-batch-v1'
                or batch.get('status') != 'complete-research-not-published'
                or batch.get('timing_complete') is not True):
            raise ValueError(f'incomplete coastal batch: {root}')
        tiles = batch.get('tiles')
        if (not isinstance(tiles, list) or not tiles
                or [item.get('tile') for item in tiles] != list(range(len(tiles)))):
            raise ValueError('coastal tile inventory is not complete and ordered')
        return batch

    old, new = read_batch(reference), read_batch(candidate)
    for key in ('snapshot_sha256', 'plan_sha256', 'grid', 'sealed_input_sha256', 'metadata_sha256'):
        if old.get(key) != new.get(key):
            raise ValueError(f'coastal replay input mismatch: {key}')
    if len(old['tiles']) != len(new['tiles']):
        raise ValueError('coastal replay tile count differs')
    semantic_keys = ('schema', 'status', 'grid', 'core_cols', 'core_rows', 'shore_crop_bounds',
                     'policy_id', 'policy_definition', 'decision_snapshot_sha256', 'decision_revision',
                     'entity_revision', 'inputs', 'physical_water_cells', 'assigned_cells',
                     'span_count', 'coastal_centers', 'coverage')
    content = hashlib.sha256()
    water = assigned = spans = byte_count = 0
    for old_tile, new_tile in zip(old['tiles'], new['tiles']):
        if old_tile['tile'] != new_tile['tile'] or old_tile['box'] != new_tile['box']:
            raise ValueError('coastal replay tile bounds differ')
        manifests, paths = [], []
        for root, item in ((reference, old_tile), (candidate, new_tile)):
            folder = root / f'tile-{item["tile"]:04d}'
            path = folder / 'manifest.json'
            if digest(path) != item['manifest_sha256']:
                raise ValueError('coastal manifest hash differs from batch completion')
            manifest = json.loads(path.read_text())
            if (manifest.get('schema') != 'worldatlas-coastal-tile-candidate-v1'
                    or manifest.get('status') != 'partial-unverified-research-not-published'
                    or manifest.get('core_cols', []) + manifest.get('core_rows', []) != item['box']):
                raise ValueError('coastal manifest identity differs from batch completion')
            span_file = manifest.get('span_file', {})
            if span_file.get('path') != 'coastal-assignments.jsonl.gz':
                raise ValueError('unexpected coastal assignment filename')
            path = folder / span_file['path']
            if digest(path) != span_file.get('sha256'):
                raise ValueError('coastal assignment hash differs from manifest')
            manifests.append(manifest)
            paths.append(path)
        if any(manifests[0].get(key) != manifests[1].get(key) for key in semantic_keys):
            raise ValueError(f'coastal scientific metadata differs: tile {old_tile["tile"]}')
        with gzip.open(paths[0], 'rb') as left, gzip.open(paths[1], 'rb') as right:
            while True:
                a, b = left.read(1 << 20), right.read(1 << 20)
                if a != b:
                    raise ValueError(f'coastal assignment bytes differ: tile {old_tile["tile"]}')
                if not a:
                    break
                content.update(a)
                byte_count += len(a)
        water += manifests[0]['physical_water_cells']
        assigned += manifests[0]['assigned_cells']
        spans += manifests[0]['span_count']
    return {'status': 'all-tile-assignment-bytes-identical', 'tile_count': len(old['tiles']),
            'physical_water_cells': water, 'assigned_cells': assigned, 'span_count': spans,
            'assignment_bytes': byte_count, 'assignment_content_sha256': content.hexdigest(),
            'reference_completion_sha256': digest(reference / 'batch-complete.json'),
            'candidate_completion_sha256': digest(candidate / 'batch-complete.json')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--admitted', type=Path, required=True)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--code-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    admission = json.loads(args.admitted.read_text())
    if Path(admission['invocation']['command'][1]).name != 'batch_coastal_tiles.py':
        raise ValueError('a complete coastal batch admission is required')
    timing = run_stage(args.admitted, args.code_root, args.out)
    comparison = compare_batches(args.reference, args.out / 'candidate')
    write_json_exclusive(args.out / 'comparison.json', comparison, indent=2)
    print(json.dumps({'process_wall_seconds': timing['process_wall_seconds'], **comparison}))


if __name__ == '__main__':
    main()
