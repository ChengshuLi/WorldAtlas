"""Shared whole-file pin guard for retained candidate source captures."""
import hashlib

def verify_source_bytes(path, raw, source):
    expected_path = source.get('retained_source_features') or source.get('retained_query_features')
    expected_bytes = source.get('retained_source_bytes')
    expected_sha256 = source.get('retained_source_sha256')
    if path != expected_path:
        raise ValueError(f'Unexpected source path: {path}')
    if not isinstance(expected_bytes, int) or len(raw) != expected_bytes:
        raise ValueError(f'Whole-file source pin length mismatch: {path}')
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError(f'Whole-file source pin hash mismatch: {path}')
    return raw
