"""Shared whole-file pin guard for retained candidate source captures."""
import hashlib

def verify_source_bytes(path, raw, source):
    rows = source.get('retained_source_files')
    if not isinstance(rows, list):
        rows = [{'path': source.get('retained_source_features') or source.get('retained_query_features'),
                 'bytes': source.get('retained_source_bytes'),
                 'sha256': source.get('retained_source_sha256')}]
    descriptor = next((row for row in rows if row.get('path') == path), None)
    if descriptor is None:
        raise ValueError(f'Unexpected source path: {path}')
    expected_bytes = descriptor.get('bytes')
    expected_sha256 = descriptor.get('sha256')
    if not isinstance(expected_bytes, int) or len(raw) != expected_bytes:
        raise ValueError(f'Whole-file source pin length mismatch: {path}')
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError(f'Whole-file source pin hash mismatch: {path}')
    return raw
