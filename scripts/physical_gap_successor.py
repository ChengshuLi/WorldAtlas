"""Authenticate retained encoded and decoded physical-source byte relations."""
from __future__ import annotations

import hashlib
import re
import zlib

from evidence.immutable import MAX_FILE_BYTES, safe_path

HEX256 = re.compile(r'^[a-f0-9]{64}$')


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _exact_keys(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError(f'{label} has an unknown or missing field')


def _descriptor(row, label):
    _exact_keys(row, ('path', 'bytes', 'sha256', 'hash_kind'), label)
    path = safe_path(row['path'])
    if (row['hash_kind'] != 'file-bytes' or type(row['bytes']) is not int
            or row['bytes'] < 0 or row['bytes'] > MAX_FILE_BYTES
            or not isinstance(row['sha256'], str) or not HEX256.fullmatch(row['sha256'])):
        raise ValueError(f'{label} is not a complete whole-file descriptor')
    return path


def decode_gzip_layers(encoded: bytes, layers: int) -> bytes:
    """Decode an exact stack of single-member gzip layers within file limits."""
    if type(layers) is not int or layers < 1 or layers > 3:
        raise ValueError('Gzip layer count must be an explicit integer from one through three')
    if not isinstance(encoded, bytes) or len(encoded) > MAX_FILE_BYTES:
        raise ValueError('Encoded source exceeds the existing per-file budget')
    raw = encoded
    for _ in range(layers):
        decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
        try:
            decoded = decoder.decompress(raw, MAX_FILE_BYTES + 1)
            if len(decoded) > MAX_FILE_BYTES or decoder.unconsumed_tail:
                raise ValueError('Decoded source exceeds the existing per-file budget')
            decoded += decoder.flush(MAX_FILE_BYTES + 1 - len(decoded))
        except zlib.error as error:
            raise ValueError('Source bytes are not a valid gzip layer') from error
        if (len(decoded) > MAX_FILE_BYTES or not decoder.eof or decoder.unused_data
                or decoder.unconsumed_tail):
            raise ValueError('Gzip layer is truncated, has trailing bytes, or exceeds its decoded budget')
        raw = decoded
    return raw


def verify_decoded_relation(encoded_descriptor, encoded, decoded_descriptor, decoded, layers):
    """Verify retained encoded and decoded source bytes and their exact gzip relation."""
    _descriptor(encoded_descriptor, 'encoded source')
    _descriptor(decoded_descriptor, 'decoded source')
    if (len(encoded) != encoded_descriptor['bytes'] or _sha(encoded) != encoded_descriptor['sha256']
            or len(decoded) != decoded_descriptor['bytes'] or _sha(decoded) != decoded_descriptor['sha256']):
        raise ValueError('Encoded or decoded source bytes differ from their retained descriptors')
    if decode_gzip_layers(encoded, layers) != decoded:
        raise ValueError('Decoded source bytes do not equal the retained gzip-layer result')
    return {'encoded_bytes': len(encoded), 'encoded_sha256': _sha(encoded),
            'decoded_bytes': len(decoded), 'decoded_sha256': _sha(decoded), 'gzip_layers': layers}
