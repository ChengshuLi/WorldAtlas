"""Read and write complete, little-endian row-run grids."""

from contextlib import contextmanager
from pathlib import Path

import numpy as np


def row(data, y, width):
    rows, runs = data
    first, last = int(rows[y]), int(rows[y + 1])
    ends, codes = runs[2 * first : 2 * last : 2], runs[2 * first + 1 : 2 * last : 2]
    if not len(ends) or ends[0] <= 0 or ends[-1] != width or np.any(ends[1:] <= ends[:-1]):
        raise ValueError('invalid row-run row')
    return ends, codes


def encode_row(values):
    values = np.asarray(values)
    if values.ndim != 1 or not len(values) or values.dtype.kind not in 'iu':
        raise ValueError('expected a nonempty integer row')
    if np.any(values < 0) or np.any(values >= 2**32) or len(values) >= 2**32:
        raise ValueError('row exceeds the u32 stream representation')
    stops = np.r_[np.flatnonzero(values[1:] != values[:-1]) + 1, len(values)]
    result = np.empty(len(stops) * 2, dtype='<u4')
    result[0::2], result[1::2] = stops, values[stops - 1]
    return result


@contextmanager
def open_grid(directory, grid):
    directory = Path(directory)
    arrays = []
    try:
        for name in ('rows', 'runs'):
            path = directory / (name + '.u32le')
            if path.stat().st_size % 4:
                raise ValueError('incomplete u32 stream')
            arrays.append(np.memmap(path, dtype='<u4', mode='r'))
        rows, runs = arrays
        if (
            len(rows) != grid.height + 1
            or len(runs) % 2
            or rows[0] != 0
            or int(rows[-1]) != len(runs) // 2
            or np.any(rows[1:] <= rows[:-1])
        ):
            raise ValueError('invalid row-run stream offsets')
        yield rows, runs
    finally:
        for array in arrays:
            array._mmap.close()
