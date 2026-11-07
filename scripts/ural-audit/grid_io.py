"""Read an uncompressed or gzip-encoded pinned little-endian RLE array."""
import gzip, hashlib
import numpy as np
def read_grid(path, expected):
    with (gzip.open(path, 'rb') if str(path).endswith('.gz') else open(path, 'rb')) as f:
        data = f.read()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('uncompressed grid checksum mismatch')
    return np.frombuffer(data, dtype='<u4')
