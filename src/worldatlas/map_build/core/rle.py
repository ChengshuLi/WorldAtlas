"""Read complete, little-endian row-run grids."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import numpy as np

from worldatlas.map_build.core.grid import Grid, column_windows


def row(
    data: tuple[np.ndarray, np.ndarray], y: int, width: int
) -> tuple[np.ndarray, np.ndarray]:
    """Read the runs in one row without expanding the cells.

    Args:
        data: Row offsets and run data from open_grid.
        y: Zero-based row index.
        width: Number of columns in the grid.

    Returns:
        Two 1-D uint32 views of equal length. The first holds exclusive end
        columns and the second holds codes. For example, ([3, 5], [17, 1])
        means the first three cells have code 17 and the next two have code 1.

    Raises:
        ValueError: Run ends are out of order or fail to cover the row.
    """
    rows, runs = data
    first, last = int(rows[y]), int(rows[y + 1])
    ends, codes = runs[2 * first : 2 * last : 2], runs[2 * first + 1 : 2 * last : 2]
    if (
        not len(ends)
        or ends[0] <= 0
        or ends[-1] != width
        or np.any(ends[1:] <= ends[:-1])
    ):
        raise ValueError('invalid row-run row')
    return ends, codes


def crop(
    rows: np.ndarray, runs: np.ndarray, y: int, x0: int, x1: int, width: int
) -> np.ndarray:
    """Expand part of one row-run row to a code per cell.

    Args:
        rows: Row offsets into the run array.
        runs: Flattened (end_column, code) pairs.
        y: Row to read.
        x0: First unwrapped column.
        x1: Exclusive end column. It may cross the longitude seam.
        width: Number of columns in the full grid.

    Returns:
        A uint32 array with x1 - x0 codes in column order.

    Raises:
        ValueError: The window or row-run records are invalid.
    """
    if not (0 <= y < len(rows) - 1 and 0 < x1 - x0 <= width):
        raise ValueError("invalid crop")
    ends, vals = row((rows, runs), y, width)
    if x0 == 0 and x1 == width:
        lengths = np.diff(np.concatenate((np.array([0], dtype=ends.dtype), ends)))
        return np.repeat(vals, lengths).astype(np.uint32, copy=False)
    result = np.empty(x1 - x0, dtype=np.uint32)
    cur = 0
    for xm, stop in column_windows(x0, x1, width):
        take = stop - xm
        i = int(np.searchsorted(ends, xm, side="right"))
        j = int(np.searchsorted(ends, stop, side="left")) + 1
        clipped = np.minimum(ends[i:j], stop).astype(np.int64)
        lengths = np.diff(np.r_[xm, clipped])
        result[cur : cur + take] = np.repeat(vals[i:j], lengths)
        cur += take
    return result


def close_memmap(array: np.memmap) -> None:
    """Release the file mapping after its readers finish.

    Args:
        array: The owning NumPy map. Its views must no longer be in use.
    """
    # NumPy exposes flush() but provides no public close operation.
    array._mmap.close()  # pyright: ignore[reportAttributeAccessIssue]


@contextmanager
def open_grid(
    directory: Path | str, grid: Grid
) -> Iterator[tuple[np.ndarray, np.ndarray]]:
    """Open a grid's row-run files as read-only memory maps.

    Args:
        directory: Directory containing rows.u32le and runs.u32le.
        grid: Dimensions expected in the files.

    Yields:
        Two 1-D uint32 arrays. Row offsets index (end_column, code) pairs in
        the run array. Use the arrays only while the context is open.

    Raises:
        ValueError: The streams have incomplete values or invalid offsets.
    """
    directory = Path(directory)
    arrays = []
    try:
        for name in ('rows', 'runs'):
            path = directory / (name + '.u32le')
            if path.stat().st_size % 4:
                raise ValueError('incomplete u32 stream')
            arrays.append(np.memmap(path, dtype='<u4', mode='r'))
        rows, runs = arrays
        if len(rows) != grid.height + 1:
            raise ValueError('row-run stream row count does not match the grid')
        if (
            len(runs) % 2
            or rows[0] != 0
            or int(rows[-1]) != len(runs) // 2
            or np.any(rows[1:] <= rows[:-1])
        ):
            raise ValueError('invalid row-run stream offsets')
        # Keep the mappings open here. Plain views share their read-only bytes
        # without carrying the memmap subclass through each slice and operation.
        yield np.asarray(rows), np.asarray(runs)
    finally:
        for array in arrays:
            close_memmap(array)
