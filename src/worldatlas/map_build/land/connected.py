"""Four-neighbor, longitude-wrapped components of canonical physical RLE.

The sequential union-by-size order is deliberately identical to the original
builder, including equal-size ties. Component IDs are generation-local, but
preserving them allows byte-for-byte comparison with existing evidence.
"""

import os
import sys
import time
from array import array
from collections.abc import Callable
from pathlib import Path
from typing import Any

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.run_components import RunComponents
from worldatlas.map_build.execution.control import check_cancelled
from worldatlas.shared.files import sha256_file, write_json


def _read(path: Path | str) -> array:
    """Load a little-endian uint32 component input file.

    Args:
        path: File containing 32-bit unsigned integers.

    Returns:
        Array of unsigned integers in native byte order.
    """
    path = Path(path)
    if path.stat().st_size % 4:
        raise ValueError("misaligned u32 stream")
    values = array("I")
    # The supported Python environments use a 32-bit unsigned int.
    if values.itemsize != 4:  # pragma: no cover
        raise RuntimeError("32-bit unsigned array elements required")
    with path.open("rb") as stream:
        values.fromfile(stream, path.stat().st_size // 4)
    if sys.byteorder != "little":  # pragma: no cover
        # CI runs on little-endian processors.
        values.byteswap()
    return values


def _write(path: Path | str, values: array) -> None:
    """Write unsigned values in little-endian byte order.

    Args:
        path: Destination for the stream.
        values: Unsigned integer array to write.
    """
    if sys.byteorder != "little":  # pragma: no cover
        # CI runs on little-endian processors.
        values = array("I", values)
        values.byteswap()
    with Path(path).open("xb") as stream:
        values.tofile(stream)
        stream.flush()
        os.fsync(stream.fileno())


def build(
    width: int,
    height: int,
    physical_rows: Path | str,
    physical_runs: Path | str,
    output_rows: Path | str,
    output_runs: Path | str,
    *,
    physical_code: int = 17,
    guard: Callable[[], None] = check_cancelled,
) -> dict[str, int]:
    """Find connected runs of one physical class without expanding to cells.

    Args:
        width: Number of columns including both sides of the longitude seam.
        height: Number of grid rows.
        physical_rows: Row-offset file for the physical grid.
        physical_runs: Run file for the physical grid.
        output_rows: New row-offset file for the components.
        output_runs: New component run file.
        physical_code: Physical code to include.
        guard: Cancellation callback.

    Returns:
        Counts of runs, connected components, and cells of the selected class.
    """
    if (
        type(width) is not int
        or type(height) is not int
        or not 0 < width <= 0xFFFFFFFF
        or not 0 < height <= 0xFFFFFFFF
    ):
        raise ValueError("invalid dimensions")
    if physical_code not in (1, 17):
        raise ValueError("components require a physical land or water class")
    rows, runs = _read(physical_rows), _read(physical_runs)
    if (
        len(rows) != height + 1
        or rows[0] != 0
        or len(runs) % 2
        or rows[-1] != len(runs) // 2
    ):
        raise ValueError("invalid stream lengths")
    connected = RunComponents()
    outrows, spans = array("I", [0]), array("I")
    previous = []
    cells = 0

    for y in range(height):
        guard()
        if not rows[y] <= rows[y + 1] <= len(runs) // 2:
            raise ValueError("nonmonotonic row offsets")
        current = []
        x, last_code = 0, None
        for i in range(rows[y] * 2, rows[y + 1] * 2, 2):
            end, code = runs[i], runs[i + 1]
            if not x < end <= width or code not in (0, 1, 17) or code == last_code:
                raise ValueError("invalid or noncanonical physical run")
            if code == physical_code:
                node = connected.add()
                current.append((x, end, node))
                spans.extend((x, end, node))
                cells += end - x
            x, last_code = end, code
        if x != width:
            raise ValueError("incomplete physical row")
        i = j = 0
        while i < len(previous) and j < len(current):
            a, b = previous[i], current[j]
            if a[0] < b[1] and b[0] < a[1]:
                connected.union(a[2], b[2])
            if a[1] < b[1]:
                i += 1
            else:
                j += 1
        if current and current[0][0] == 0 and current[-1][1] == width:
            connected.union(current[0][2], current[-1][2])
        outrows.append(len(connected))
        previous = current
    # A later row can join two pieces that looked separate earlier. Find each
    # run’s final component after connecting every row and the longitude seam.
    components = 0
    for node in range(len(connected)):
        if node % 65536 == 0:
            guard()
        root = connected.find(node)
        spans[3 * node + 2] = root
        components += root == node
    _write(output_rows, outrows)
    _write(output_runs, spans)
    return {
        "runs": len(connected),
        "components": components,
        "selected_cells": cells,
    }


def build_components(
    grid: Grid,
    physical_directory: Path | str,
    directory: Path | str,
    *,
    physical_code: int = 17,
) -> dict[str, Any]:
    """Build the connected components of one class on the given grid.

    Args:
        grid: Physical grid dimensions.
        physical_directory: Directory with land and water row runs.
        directory: New directory for component streams and their report.
        physical_code: Code to treat as connected, normally land (17).

    Returns:
        Report with grid, counts, output digests, and elapsed seconds.
    """
    started = time.monotonic()
    physical_directory, directory = Path(physical_directory), Path(directory)
    directory.mkdir()
    result = build(
        grid.width,
        grid.height,
        physical_directory / "rows.u32le",
        physical_directory / "runs.u32le",
        directory / "rows.u32le",
        directory / "runs.u32le",
        physical_code=physical_code,
    )
    report = dict(
        result,
        grid=vars(grid),
        physical_code=physical_code,
        output_sha256={
            name: sha256_file(directory / name) for name in ("rows.u32le", "runs.u32le")
        },
        processing_seconds=time.monotonic() - started,
    )
    write_json(directory / "report.json", report, sort_keys=False)
    return report
