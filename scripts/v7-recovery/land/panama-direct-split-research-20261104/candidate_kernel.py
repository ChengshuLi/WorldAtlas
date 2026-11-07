"""Reusable non-metric stream and grid-graph helpers for research diagnostics.

This module contains no nearest-side policy and does not generate geographic
assignments. The retired planar side-selection prototype was removed.
"""
import hashlib
import os
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'mainland-source-recovery-20261104/topology-proposal'))
sys.path.insert(0, str(ROOT / 'audit/ocean-interfaces-20261103/fresh-water-partition'))
from build_partition import partition
from partition_core import rasterize_barriers

W, H, STEP = 131072, 54614, 360 / 131072

def need(value, message):
    if not value:
        raise ValueError(message)

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()

class TripleRows:
    """Read checked uint32 triple rows with bounded per-row memory."""
    def __init__(self, rows_path, spans_path, height):
        self.offsets = np.fromfile(rows_path, dtype='<u4')
        self.fd = os.open(spans_path, os.O_RDONLY)
        try:
            need(len(self.offsets) == height + 1 and self.offsets[0] == 0
                 and np.all(self.offsets[1:] >= self.offsets[:-1]),
                 'invalid triple row offsets')
            need(os.fstat(self.fd).st_size == int(self.offsets[-1]) * 12,
                 'invalid triple stream size')
        except BaseException:
            os.close(self.fd)
            self.fd = None
            raise
    def row(self, y):
        need(type(y) is int and 0 <= y < len(self.offsets) - 1, 'row out of range')
        a, b = map(int, self.offsets[y:y+2])
        data = os.pread(self.fd, (b-a) * 12, a * 12)
        need(len(data) == (b-a) * 12, 'short triple row')
        return np.frombuffer(data, dtype='<u4').reshape(-1, 3)
    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
    def __del__(self):
        if getattr(self, 'fd', None) is not None:
            self.close()
