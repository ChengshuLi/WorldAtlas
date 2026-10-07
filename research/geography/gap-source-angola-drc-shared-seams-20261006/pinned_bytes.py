"""Shared full-file byte-pin validation used by producer and mutation controls."""
import hashlib


def verify_pinned_bytes(raw, expected_bytes, expected_sha256, label):
    actual_sha256 = hashlib.sha256(raw).hexdigest()
    if len(raw) != expected_bytes or actual_sha256 != expected_sha256:
        raise ValueError(f'{label} does not match its full-file byte pin')
    return actual_sha256
