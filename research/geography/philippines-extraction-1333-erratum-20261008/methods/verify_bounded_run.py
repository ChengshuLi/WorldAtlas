#!/usr/bin/env python3
"""Import-safe acceptance reader for guarded fresh synthetic control runs."""
import hashlib
import json
from pathlib import Path


def verify_run(directory):
    root = Path(directory)
    receipt_path = root / 'publication.json'
    if root.is_symlink() or receipt_path.is_symlink() or not receipt_path.is_file():
        raise ValueError('Missing ordinary completion receipt')
    receipt_raw = receipt_path.read_bytes()
    receipt = json.loads(receipt_raw)
    if receipt.get('version') != 1 or receipt.get('status') != 'complete':
        raise ValueError('Run is not complete')
    rows = receipt.get('outputs')
    if not isinstance(rows, list) or not rows or len({row['path'] for row in rows}) != len(rows):
        raise ValueError('Missing or duplicate output receipt rows')
    expected = {Path(row['path']).name for row in rows}
    actual = {path.name for path in root.iterdir() if path.name != 'publication.json'}
    if actual != expected:
        raise ValueError('Run output inventory differs from completion receipt')
    expected_prefix = 'research/geography/philippines-extraction-1333-erratum-20261008/vintages/' + root.name + '/'
    for row in rows:
        if not row.get('path', '').startswith(expected_prefix):
            raise ValueError('Receipt output escaped its owned fresh run')
        path = root / Path(row['path']).name
        if path.is_symlink() or not path.is_file():
            raise ValueError('Receipt output is not an ordinary file')
        raw = path.read_bytes()
        if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('Receipt output byte identity mismatch: ' + path.name)
    return {'status': 'complete', 'outputs': len(rows), 'receipt_sha256': hashlib.sha256(receipt_raw).hexdigest()}
