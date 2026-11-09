"""Authenticate every tile byte from canonical seed RLE using NumPy APIs.

A tile-row band is ordinary streaming work, not a pixel-expanded raster.
Intervals split only at tile edges. The independently constructed records must
match complete tile files, including order and exact endpoints.
"""
import json
import sys
from pathlib import Path

import numpy as np


def verify(rows, runs, directory, width, height, tile_size=1024, guard=lambda: None):
    if any(type(v) is not int or not 0 < v <= 0xffffffff for v in (width, height, tile_size)):
        raise ValueError('bad dimensions')
    rows, runs, directory = Path(rows), Path(runs), Path(directory)
    if rows.stat().st_size != (height+1)*4 or runs.stat().st_size % 8:
        raise ValueError('bad offsets or runs size')
    offsets = np.memmap(rows, dtype='<u4', mode='r')
    count = runs.stat().st_size//8
    if int(offsets[0]) != 0 or int(offsets[-1]) != count or np.any(offsets[1:] <= offsets[:-1]):
        raise ValueError('bad offsets')
    data = np.memmap(runs, dtype='<u4', mode='r', shape=(count, 2))
    seen = set()
    records = 0
    for y0 in range(0, height, tile_size):
        guard()
        y1 = min(height, y0+tile_size)
        lo, hi = int(offsets[y0]), int(offsets[y1])
        part = data[lo:hi]
        y = np.repeat(np.arange(y0, y1, dtype=np.uint32), np.diff(offsets[y0:y1+1]).astype(np.int64))
        first = np.r_[True, y[1:] != y[:-1]]
        start = np.r_[0, part[:-1, 0]].astype(np.int64)
        start[first] = 0
        end, code = part[:, 0].astype(np.int64), part[:, 1]
        if (np.any(start >= end) or np.any(end > width) or
                np.any((code != 0) & ((code < 17) | (code > 22))) or
                np.any((~first[1:]) & (code[1:] == code[:-1])) or
                np.any(end[np.r_[y[1:] != y[:-1], True]] != width)):
            raise ValueError('bad seed row')
        selected = code != 0
        a, b, labels, ys = start[selected], end[selected], code[selected], y[selected]
        tx0, tx1 = a//tile_size, (b-1)//tile_size
        repeat = tx1-tx0+1
        owner = np.repeat(np.arange(len(a)), repeat)
        within = np.arange(len(owner))-np.repeat(np.cumsum(repeat)-repeat, repeat)
        tx = tx0[owner]+within
        values = np.column_stack((ys[owner], np.maximum(a[owner], tx*tile_size),
                                  np.minimum(b[owner], (tx+1)*tile_size), labels[owner])).astype('<u4')
        order = np.argsort(tx, kind='stable')
        tx, values = tx[order], values[order]
        unique, begin = np.unique(tx, return_index=True)
        for x, left, right in zip(unique, begin, np.r_[begin[1:], len(tx)]):
            guard()
            name = f'{y0//tile_size:05d}-{int(x):05d}.bin'
            path = directory/name
            expected = values[left:right].tobytes()
            if not path.is_file() or path.stat().st_size != len(expected) or path.read_bytes() != expected:
                raise ValueError('tile bytes mismatch: '+name)
            seen.add(name)
            records += int(right-left)
    for path in directory.iterdir():
        if path.suffix == '.bin' and path.name not in seen:
            raise ValueError('unexpected or noncanonical tile filename: '+path.name)
    guard()
    return {'status': 'verified', 'tiles': len(seen), 'tile_records': records}


if __name__ == '__main__':
    if len(sys.argv) != 7:
        raise SystemExit('usage: verify_seed_index.py ROWS RUNS TILE_DIR W H TILE_SIZE')
    print(json.dumps(verify(*sys.argv[1:4], *(int(v) for v in sys.argv[4:]))))
