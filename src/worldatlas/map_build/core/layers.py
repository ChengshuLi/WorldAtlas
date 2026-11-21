"""Merge sparse assignment rows and write complete row-run layers."""

import heapq
import itertools
import json
from collections import Counter
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

import numpy as np

from worldatlas.map_build.core.grid import Grid


def merge_rows(
    streams: list[Iterable[tuple[int, list[tuple[int, int, int]]]]],
) -> Iterator[tuple[int, list[tuple[int, int, int]]]]:
    """Merge row streams from disjoint tiles, including across ±180°.

    Args:
        streams: Streams sorted by row. Each row contains (first_column,
            end_column, code) spans.

    Yields:
        (row, spans) in row order, with each row's spans sorted by column.

    Raises:
        ValueError: Spans from different tiles overlap.
    """
    if len(streams) == 1:
        yield from streams[0]
        return
    merged = heapq.merge(*streams, key=lambda item: item[0])
    for y, records in itertools.groupby(merged, key=lambda item: item[0]):
        spans = sorted(span for _, values in records for span in values)
        if any(a[1] > b[0] for a, b in zip(spans, spans[1:])):
            raise ValueError("assignment tiles overlap")
        yield y, spans


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
            spans = current[1]
            if spans:
                bounds = [int(spans[0][0]), int(spans[-1][1]), y, y + 1]
                if assigned_bounds is None:
                    assigned_bounds = bounds
                else:
                    assigned_bounds = [
                        min(assigned_bounds[0], bounds[0]),
                        max(assigned_bounds[1], bounds[1]),
                        assigned_bounds[2],
                        y + 1,
                    ]
            pairs = []
            stop = 0

            def append(end: int, code: int) -> None:
                """Extend the last run or append a run with a new code.

                Args:
                    end: Exclusive end column.
                    code: Value of this run.
                """
                if pairs and pairs[-1][1] == code:
                    pairs[-1] = (end, code)
                else:
                    pairs.append((end, code))

            for a, b, code in spans:
                if (
                    any(type(v) is not int for v in (a, b, code))
                    or not stop <= a < b <= grid.width
                    or not 0 < code < 2**32
                ):
                    raise ValueError("invalid output span")
                if a > stop:
                    append(a, 0)
                append(b, code)
                counts[str(code)] += b - a
                stop = b
            if stop < grid.width:
                append(grid.width, 0)
            np.asarray(pairs, dtype="<u4").tofile(output)
            offsets.append(offsets[-1] + len(pairs))
            # Testing this limit would require writing over four billion runs.
            if offsets[-1] >= 2**32:  # pragma: no cover
                raise ValueError("run offsets exceed the u32 representation")
            current = next(iterator, None)
            y += 1
        if current is not None:
            raise ValueError("assignment row outside the grid")
    np.asarray(offsets, dtype="<u4").tofile(directory / "rows.u32le")
    report = {
        "directory": str(directory.resolve()),
        "assigned_bounds": assigned_bounds,
        "grid": {"width": grid.width, "height": grid.height, "step": grid.step},
        "counts": dict(counts),
        "run_count": offsets[-1],
    }
    (directory / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


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
        spans = []
        for a, b in ((x0, min(x1, grid.width)), (0, max(0, x1 - grid.width))):
            if a == b:
                continue
            offset = (a - x0) % grid.width
            part = row[offset : offset + b - a]
            stops = np.r_[0, np.flatnonzero(part[1:] != part[:-1]) + 1, len(part)]
            for first, last in zip(stops, stops[1:]):
                code = int(part[first])
                if code:
                    spans.append((a + int(first), a + int(last), code))
        if spans:
            yield y, sorted(spans)
