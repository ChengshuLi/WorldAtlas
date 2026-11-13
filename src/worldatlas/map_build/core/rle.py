"""Read complete, little-endian row-run grids."""

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
