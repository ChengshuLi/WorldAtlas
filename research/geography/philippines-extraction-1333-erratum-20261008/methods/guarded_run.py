#!/usr/bin/env python3
"""Bounded successor controls for the Philippines #1333 preserved extraction.

The original 22-subject operation is deliberately refused from its pinned
whole-input inventory before any gzip decoding or product generation. A small
synthetic control can exercise the same complete-run writer safely.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / 'scripts'))
from evidence.immutable import Baseline, NewVintage, MAX_FILE_BYTES, MAX_PHASE_BYTES

OWNED = 'research/geography/philippines-extraction-1333-erratum-20261008/'
MANIFEST = Path(__file__).resolve().parents[1] / 'evidence-quality.json'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def baseline_for(repo=REPO):
    manifest = json.loads(MANIFEST.read_bytes())
    return Baseline(repo, manifest['baseline']['commit'], manifest['baseline']['files'])


def validate_inventory(closure, expected):
    """Require the complete exact path/hash/size roster from the pinned receipt."""
    def key(row):
        return row['path'], row['bytes'], row['sha256'], row.get('uncompressed_bytes'), row.get('uncompressed_sha256')
    if not closure or len({row['path'] for row in closure}) != len(closure):
        raise ValueError('Missing or duplicate descriptor in complete original input inventory')
    if {key(row) for row in closure} != {key(row) for row in expected}:
        raise ValueError('Original operation input inventory is incomplete or substituted')


def validate_logical_streams(streams, file_limit=MAX_FILE_BYTES):
    if not streams or any(not isinstance(row.get('bytes'), int) or row['bytes'] <= 0 for row in streams):
        raise ValueError('Missing or invalid complete logical stream descriptor')
    too_large = [row for row in streams if row['bytes'] > file_limit]
    if too_large:
        raise ValueError('Complete logical stream exceeds per-file limit: ' + too_large[0]['name'])


def refuse_original(repo=REPO, baseline=None):
    """Admit complete body and phase limits from raw descriptors only."""
    evidence = json.loads(MANIFEST.read_bytes())
    baseline = baseline or baseline_for(repo)
    closure = evidence['original_operation']['input_closure']
    receipt = json.loads(baseline.pinned_bytes(evidence['original_operation']['receipt_path']))
    expected = []
    for row in receipt['input_closure']:
        path = row['path']
        if row['vintage'] == 'candidate':
            path = 'research/geography/philippines-ten-gap-family-source-fitness-20261007/' + path
        expected.append({'path': path, 'bytes': row['bytes'], 'sha256': row['sha256'],
                         'uncompressed_bytes': row.get('uncompressed_bytes'),
                         'uncompressed_sha256': row.get('uncompressed_sha256')})
    validate_inventory(closure, expected)
    # Authenticate every raw encoded input before considering any decoded bytes.
    raw_total = sum(row['bytes'] for row in closure)
    for row in closure:
        raw = baseline.read(row['path'])
        if len(raw) != row['bytes'] or sha(raw) != row['sha256']:
            raise ValueError('Original whole-input descriptor drift: ' + row['path'])
        if len(raw) > MAX_FILE_BYTES:
            raise ValueError('Original raw body exceeds per-file limit: ' + row['path'])
    if raw_total > MAX_PHASE_BYTES:
        raise ValueError('Original raw inputs exceed complete-operation phase budget')
    decoded_rows = [row for row in closure if 'uncompressed_bytes' in row]
    # Reject the individual logical streams first. Do not decompress them.
    oversized = [row for row in decoded_rows if row['uncompressed_bytes'] > MAX_FILE_BYTES]
    if oversized:
        raise ValueError('Original decoded/logical body exceeds per-file limit: ' + oversized[0]['path'])
    decoded_total = sum(row['uncompressed_bytes'] for row in decoded_rows)
    refusals = []
    try:
        validate_logical_streams(evidence['original_operation']['logical_streams'])
    except ValueError as error:
        refusals.append(str(error))
    try:
        admit_phase_sizes(sum(baseline.consumed.values()), decoded_total)
    except ValueError as error:
        refusals.append(str(error))
    if refusals:
        raise ValueError('; '.join(refusals))
    # This operation is never allowed to proceed: its retained full logical
    # streams exceed the ordinary-file cap even if descriptors were chunked.
    raise ValueError('Original full operation is refused; full logical streams exceed the bounded contract')


def admit_phase_sizes(raw_bytes, decoded_bytes, output_bytes=0, budget=MAX_PHASE_BYTES, reserve=4096):
    if min(raw_bytes, decoded_bytes, output_bytes, reserve) < 0 or raw_bytes + decoded_bytes + output_bytes + reserve > budget:
        raise ValueError('Raw, decoded and output bytes exceed complete phase budget')


def run_synthetic(repo, vintage, baseline=None):
    """Exercise a bounded complete publication using no geographic input."""
    baseline = baseline or baseline_for(repo)
    outputs = ['control.json', 'control-summary.json']
    run = NewVintage(baseline, OWNED, vintage, outputs)
    # Both outputs are explicit non-geographic guard-control records.
    return run.publish({
        'control.json': {'kind': 'synthetic-control', 'geographic_claim': False,
                         'input': 'bounded fixture only', 'result': 'complete'},
        'control-summary.json': {'output_count': 2, 'status': 'complete',
                                 'geographic_claim': False},
    })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--synthetic-vintage')
    args = parser.parse_args()
    if args.synthetic_vintage:
        records = run_synthetic(REPO, args.synthetic_vintage)
        print(json.dumps({'status': 'complete', 'geographic_claim': False,
                          'outputs': records}, sort_keys=True))
        return
    try:
        refuse_original(REPO)
    except ValueError as error:
        message = str(error)
        if 'Complete logical stream exceeds per-file limit' in message and 'complete phase budget' in message:
            print(json.dumps({'status': 'refused', 'before_decode': True, 'products_generated': False,
                              'reason': message}, sort_keys=True))
            return
        raise


if __name__ == '__main__':
    main()
