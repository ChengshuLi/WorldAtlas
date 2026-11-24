"""Merge sparse assignment rows and write complete row-run layers."""

import heapq
import itertools
from collections import Counter
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

import numpy as np

from worldatlas.map_build.core.grid import Grid, column_windows
from worldatlas.shared.files import write_json


def merge_rows(
    streams: list[Iterable[tuple[int, list[tuple[int, int, int]]]]],
) -> Iterator[tuple[int, list[tuple[int, int, int]]]]:
    """Merge row streams from disjoint tiles, including across ±180°.

    Args:
        streams: Streams sorted by row. Each row contains (first_column,
            end_column, code) spans.

    Yields:
        (row, spans) in row order, with each row's spans sorted by column.
    """
    if len(streams) == 1:
        yield from streams[0]
        return
    merged = heapq.merge(*streams, key=lambda item: item[0])
    for y, records in itertools.groupby(merged, key=lambda item: item[0]):
        yield y, sorted(span for _, values in records for span in values)


def write_layer(
    directory: Path | str,
    grid: Grid,
    rows: Iterable[tuple[int, list[tuple[int, int, int]]]],
) -> dict[str, Any]:
    """Write row-run files and a report to a new directory.

    Args:
        directory: Path for the layer files. The directory must not exist.
        grid: Dimensions of the complete output.
        rows: Ordered (row, spans) records. Each span is (first_column,
            end_column, code). Write zero where there is no span.

    Returns:
        Report dictionary with the path, grid dimensions, run count, bounds of
        assigned cells and counts keyed by code as a string.

    Raises:
        ValueError: A row or span is invalid, or the run offsets exceed uint32.
    """
    return write_run_rows(directory, grid, _complete_rows(rows, grid.width))


def _complete_rows(
    rows: Iterable[tuple[int, list[tuple[int, int, int]]]], width: int
) -> Iterator[tuple[int, np.ndarray, np.ndarray]]:
    """Fill the gaps in sparse spans with zero-valued runs.

    Args:
        rows: Ordered row indices and (start, end, code) spans.
        width: Number of columns to cover.

    Yields:
        (row, ends, codes) with a uint32 array for each run field.

    Raises:
        ValueError: A span is outside the row, overlaps, or has an invalid code.
    """
    for y, spans in rows:
        ends, codes = [], []
        stop = 0
        for a, b, code in spans:
            if (
                any(type(v) is not int for v in (a, b, code))
                or not stop <= a < b <= width
                or not 0 < code < 2**32
            ):
                raise ValueError("invalid output span")
            if a > stop:
                ends.append(a)
                codes.append(0)
            ends.append(b)
            codes.append(code)
            stop = b
        if stop < width:
            ends.append(width)
            codes.append(0)
        yield y, np.asarray(ends, dtype=np.uint32), np.asarray(codes, dtype=np.uint32)


def write_run_rows(
    directory: Path | str,
    grid: Grid,
    rows: Iterable[tuple[int, np.ndarray, np.ndarray]],
) -> dict[str, Any]:
    """Write complete rows directly from run arrays.

    Args:
        directory: New directory for the streams and layer report.
        grid: Dimensions of the complete output.
        rows: Ordered (row, ends, codes) tuples. Ends are exclusive columns.
            Both arrays are one-dimensional uint32 with equal length. Code
            zero marks unassigned cells. Omitted rows are entirely unassigned.

    Returns:
        Layer report with counts by code, assigned bounds, and total runs.

    Raises:
        ValueError: Rows are unordered, runs are invalid, or the stream
            exceeds the uint32 format.
    """
    directory = Path(directory)
    directory.mkdir()
    iterator = iter(rows)
    current = next(iterator, None)
    offsets = [0]
    counts = Counter()
    assigned_bounds = None
    with (directory / "runs.u32le").open("xb") as output:
        y = 0
        while y < grid.height:
            if current is not None and (
                type(current[0]) is not int or not y <= current[0] < grid.height
            ):
                raise ValueError(
                    "layer rows must be ordered and unique, and inside the grid"
                )
            if current is None or current[0] > y:
                stop = grid.height if current is None else current[0]
                length = stop - y
                np.tile(np.asarray([grid.width, 0], dtype="<u4"), length).tofile(output)
                offsets.extend(range(offsets[-1] + 1, offsets[-1] + length + 1))
                y = stop
                continue
            _, ends, codes = current
            if (
                ends.ndim != 1
                or ends.shape != codes.shape
                or ends.dtype != np.uint32
                or codes.dtype != np.uint32
                or not len(ends)
                or ends[0] == 0
                or ends[-1] != grid.width
                or np.any(ends[1:] <= ends[:-1])
            ):
                raise ValueError("invalid complete output row")
            # A repeated code needs only the exclusive end of its last run.
            stops = np.empty(ends.size, dtype=bool)
            stops[:-1] = codes[1:] != codes[:-1]
            stops[-1] = True
            ends, codes = ends[stops], codes[stops]
            np.column_stack((ends, codes)).astype("<u4", copy=False).tofile(output)
            assigned = np.flatnonzero(codes)
            if assigned.size:
                starts = np.r_[np.uint32(0), ends[:-1]]
                left, right = int(starts[assigned[0]]), int(ends[assigned[-1]])
                if assigned_bounds is None:
                    assigned_bounds = [left, right, y, y + 1]
                else:
                    assigned_bounds[0] = min(assigned_bounds[0], left)
                    assigned_bounds[1] = max(assigned_bounds[1], right)
                    assigned_bounds[3] = y + 1
                ids, indices = np.unique(codes[assigned], return_inverse=True)
                totals = np.zeros(len(ids), dtype=np.uint64)
                np.add.at(totals, indices, ends[assigned] - starts[assigned])
                for code, count in zip(ids, totals, strict=True):
                    counts[str(int(code))] += int(count)
            offsets.append(offsets[-1] + len(ends))
            current = next(iterator, None)
            y += 1
        if current is not None:
            raise ValueError("assignment row outside the grid")
    # Reaching this limit requires writing over four billion runs, which is
    # impractical in tests.
    if offsets[-1] >= 2**32:  # pragma: no cover
        raise ValueError("run offsets exceed the u32 representation")
    np.asarray(offsets, dtype="<u4").tofile(directory / "rows.u32le")
    report = {
        "directory": str(directory.resolve()),
        "assigned_bounds": assigned_bounds,
        "grid": {"width": grid.width, "height": grid.height, "step": grid.step},
        "counts": dict(counts),
        "run_count": offsets[-1],
    }
    write_json(directory / "report.json", report, sort_keys=False)
    return report


def column_spans(
    values: np.ndarray, first: int, end: int, width: int
) -> list[tuple[int, int, int]]:
    """Convert one possibly wrapped row of values to nonzero runs.

    Args:
        values: 1-D cell values in the window's traversal order.
        first: First unwrapped column.
        end: Exclusive end of the window.
        width: Number of columns in the full grid.

    Returns:
        Sorted (first, end, value) records with zero-valued runs omitted.
    """
    spans = []
    offset = 0
    for left, right in column_windows(first, end, width):
        if left == right:
            continue
        part = values[offset : offset + right - left]
        stops = np.r_[0, np.flatnonzero(part[1:] != part[:-1]) + 1, len(part)]
        spans.extend(
            (left + int(a), left + int(b), int(part[a]))
            for a, b in zip(stops, stops[1:])
            if part[a]
        )
        offset += right - left
    return sorted(spans)


def patch_rows(
    values: np.ndarray, bounds: tuple[int, int, int, int], grid: Grid
) -> Iterator[tuple[int, list[tuple[int, int, int]]]]:
    """Convert a rectangular block of codes to sparse row spans.

    Args:
        values: Two-dimensional array of codes. Omit cells with code zero.
        bounds: (first_column, end_column, first_row, end_row). An end column
            past the grid width wraps to column zero.
        grid: Complete grid containing the patch.

    Yields:
        (row, spans) in row order. Each span is (first_column, end_column, code).

    Raises:
        ValueError: Array dimensions differ from the window dimensions.
    """
    x0, x1, y0, y1 = bounds
    if values.shape != (y1 - y0, x1 - x0):
        raise ValueError("assignment dimensions differ from its bounds")
    for y, row in enumerate(values, y0):
        records = column_spans(row, x0, x1, grid.width)
        if records:
            yield y, records
