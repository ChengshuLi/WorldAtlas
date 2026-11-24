"""Read, complete and align rows in little-endian row-run grids."""

from collections.abc import Generator, Sequence
from contextlib import contextmanager
from mmap import ACCESS_READ, ACCESS_WRITE, mmap
from os import fstat
from pathlib import Path
from typing import Literal

import numpy as np

from worldatlas.map_build.core.grid import Grid, column_windows


def merge_adjacent_runs(
    ends: np.ndarray, codes: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Represent adjacent runs with the same code as one run.

    Args:
        ends: One-dimensional uint32 array of exclusive run end columns.
        codes: Matching uint32 array of codes. The row has at least one run.

    Returns:
        Two uint32 arrays with only the last end for each consecutive code.
    """
    last_in_run = np.empty(len(codes), dtype=bool)
    last_in_run[:-1] = codes[:-1] != codes[1:]
    last_in_run[-1] = True
    return ends[last_in_run], codes[last_in_run]


def complete_row(
    width: int,
    spans: Sequence[tuple[int, int, int]] | np.ndarray,
    *,
    minimum_code: Literal[0, 1] = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """Fill uncovered columns with zero and merge adjacent equal codes.

    Args:
        width: Number of columns in the row.
        spans: Ordered (first_column, exclusive_end_column, code) records.
        minimum_code: Use 0 when spans can carry code zero or 1 when
            each supplied span must claim cells. Gaps always get code zero.

    Returns:
        Two one-dimensional uint32 arrays of exclusive run ends and codes.
        For width 6, spans (1, 3, 7) and (3, 5, 7) give ends [1, 5, 6]
        with codes [0, 7, 0].

    Raises:
        ValueError: Spans are malformed, overlap, are out of order, extend past
            the row, or contain a code outside the permitted uint32 range.
    """
    if not len(spans):
        return np.array([width], dtype=np.uint32), np.array([0], dtype=np.uint32)
    records = np.asarray(spans)
    if (
        records.ndim != 2
        or records.shape[1] != 3
        or not np.issubdtype(records.dtype, np.integer)
    ):
        raise ValueError("row spans require integer start, end and code")
    starts, ends, codes = records.T
    if np.any(
        (starts < 0)
        | (starts >= ends)
        | (ends > width)
        | (codes < minimum_code)
        | (codes >= 2**32)
    ) or np.any(starts[1:] < ends[:-1]):
        raise ValueError("invalid row span order, column bounds or code")

    # Put a zero run before every span plus one at the end, then drop the
    # zero-length gaps where the supplied spans touch.
    run_ends = np.empty(2 * len(records) + 1, dtype=np.uint32)
    run_codes = np.zeros_like(run_ends)
    run_ends[:-1:2] = starts
    run_ends[1::2] = ends
    run_ends[-1] = width
    run_codes[1::2] = codes
    nonempty = np.empty(len(run_ends), dtype=bool)
    nonempty[0] = run_ends[0] != 0
    nonempty[1:] = run_ends[1:] > run_ends[:-1]
    return merge_adjacent_runs(run_ends[nonempty], run_codes[nonempty])


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


def overlay(
    *rows: tuple[np.ndarray, np.ndarray],
) -> tuple[np.ndarray, np.ndarray, list[np.ndarray]]:
    """Split rows wherever any input changes value.

    Args:
        rows: One or more rows as (exclusive_end_columns, values) arrays.

    Returns:
        (starts, ends, aligned_values). Each input gets a value per shared
        interval. For example, runs ending at [2, 5] and [3, 5] produce
        [0, 2), [2, 3), and [3, 5).

    Raises:
        ValueError: There are no input rows or their widths differ.
    """
    if not rows:
        raise ValueError("an overlay needs at least one row")
    if not len(rows[0][0]):
        raise ValueError("overlay rows must cover at least one column")
    width = int(rows[0][0][-1])
    if any(not len(ends) or int(ends[-1]) != width for ends, _ in rows):
        raise ValueError("overlay rows have different widths")
    cuts = np.unique(np.concatenate(([0], *(ends for ends, _ in rows))))
    starts, ends = cuts[:-1], cuts[1:]
    values = [
        codes[np.searchsorted(stops, starts, side="right")] for stops, codes in rows
    ]
    return starts, ends, values


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


@contextmanager
def open_mapped_array(
    path: Path, dtype: Literal["<u4", "<u8"], *, writable: bool = False
) -> Generator[np.ndarray]:
    """Open a file as an array of little-endian unsigned integers.

    Args:
        path: File containing the integers.
        dtype: NumPy format for 4-byte or 8-byte integers.
        writable: Allow edits and flush them to the file on successful exit.

    Yields:
        A 1-D NumPy array backed by the file, or an empty array for an empty
        file. Use the array and any slices only within the context.

    Raises:
        ValueError: The file ends partway through an integer.
    """
    with path.open("r+b" if writable else "rb") as stream:
        size = fstat(stream.fileno()).st_size
        count, remainder = divmod(size, np.dtype(dtype).itemsize)
        if remainder:
            raise ValueError(f"incomplete integer stream: {path}")
        if not count:
            # The operating system cannot map a zero-length file.
            empty = np.empty(0, dtype=dtype)
            empty.setflags(write=writable)
            yield empty
            return
        with mmap(
            stream.fileno(), size, access=ACCESS_WRITE if writable else ACCESS_READ
        ) as mapping:
            yield np.ndarray((count,), dtype=dtype, buffer=mapping)
            if writable:
                mapping.flush()


@contextmanager
def open_grid(
    directory: Path | str, grid: Grid
) -> Generator[tuple[np.ndarray, np.ndarray]]:
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
    with (
        open_mapped_array(directory / "rows.u32le", "<u4") as rows,
        open_mapped_array(directory / "runs.u32le", "<u4") as runs,
    ):
        if len(rows) != grid.height + 1:
            raise ValueError('row-run stream row count does not match the grid')
        if (
            len(runs) % 2
            or rows[0] != 0
            or int(rows[-1]) != len(runs) // 2
            or np.any(rows[1:] <= rows[:-1])
        ):
            raise ValueError('invalid row-run stream offsets')
        yield rows, runs
