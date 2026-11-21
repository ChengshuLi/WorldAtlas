"""Index complete reference intervals; real sampled cells supply upper bounds."""

import hashlib
import json
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.shared.files import sha256_file


def build_reference_index(
    grid: Grid,
    rows: Iterable[tuple[int, np.ndarray]],
    directory: Path | str,
    *,
    tile_cells: int = 1024,
    samples_per_category: int = 32,
) -> dict[str, Any]:
    """Store reference shore runs in tiles for distance lookups.

    Args:
        grid: Dimensions and coordinates of the reference grid.
        rows: Ordered (row, runs) records, each with an N-by-3 array of (start,
            end, owner).
        directory: New directory for tile files, sample cells and report.
        tile_cells: Number of cells along each side of a tile.
        samples_per_category: Maximum representative samples per category in a
            tile.

    Returns:
        Dictionary with grid, tile checksums, and the sampled cells' checksum.
    """
    if (
        type(tile_cells) is not int
        or tile_cells <= 0
        or type(samples_per_category) is not int
        or samples_per_category <= 0
    ):
        raise ValueError("reference index needs positive tile and sample sizes")
    started = time.monotonic()
    directory = Path(directory)
    directory.mkdir()
    tiles, representatives, buffers = [], [], []
    current_tile = None
    previous_row = -1

    def flush() -> None:
        """Write the current tile row's pending runs to disk."""
        if not buffers:
            return
        values = np.concatenate(buffers)
        columns = values[:, 1] // tile_cells
        order = np.argsort(columns, kind="stable")
        values, columns = values[order], columns[order]
        firsts = np.r_[0, np.flatnonzero(columns[1:] != columns[:-1]) + 1]
        for first, last in zip(firsts, np.r_[firsts[1:], len(values)]):
            tx = int(columns[first])
            records = values[first:last].astype("<u4", copy=False)
            data = records.tobytes()
            (directory / f"{current_tile:05d}-{tx:05d}.bin").write_bytes(data)
            codes = list(map(int, np.unique(records[:, 3])))
            tiles.append(
                (
                    current_tile,
                    tx,
                    codes,
                    len(records),
                    hashlib.sha256(data).hexdigest(),
                )
            )
            for code in codes:
                selected = np.flatnonzero(records[:, 3] == code)
                picked = selected[
                    np.unique(
                        np.linspace(
                            0,
                            len(selected) - 1,
                            min(samples_per_category, len(selected)),
                            dtype=int,
                        )
                    )
                ]
                for y, a, b, _ in records[picked]:
                    representatives.append((int(y), (int(a) + int(b) - 1) // 2, code))
        buffers.clear()

    for y, intervals in rows:
        if type(y) is not int or not previous_row < y < grid.height:
            raise ValueError(
                "reference rows must be ordered, unique and within the grid"
            )
        previous_row = y
        parts = np.asarray(intervals)
        if not len(parts):
            continue
        if (
            parts.ndim != 2
            or parts.shape[1] != 3
            or not np.issubdtype(parts.dtype, np.integer)
        ):
            raise ValueError("reference intervals require integer start, end and owner")
        left, right, codes = parts.T
        if (
            np.any(left < 0)
            or np.any(left >= right)
            or np.any(right > grid.width)
            or np.any(left[1:] < right[:-1])
            or np.any(codes <= 0)
            or np.any(codes >= 2**32)
        ):
            raise ValueError("invalid reference intervals")
        ty = y // tile_cells
        if ty != current_tile:
            flush()
            current_tile = ty
        first_tiles, last_tiles = left // tile_cells, (right - 1) // tile_cells
        lengths = (last_tiles - first_tiles + 1).astype(np.int64)
        source = np.repeat(np.arange(len(parts)), lengths)
        offsets = np.repeat(np.cumsum(lengths) - lengths, lengths)
        tx = np.repeat(first_tiles, lengths) + np.arange(len(source)) - offsets
        buffers.append(
            np.column_stack(
                (
                    np.full(len(source), y),
                    np.maximum(left[source], tx * tile_cells),
                    np.minimum(right[source], (tx + 1) * tile_cells),
                    codes[source],
                )
            )
        )
    flush()
    if not tiles:
        raise ValueError("cannot index empty reference cells")
    np.asarray(representatives, dtype="<u4").tofile(directory / "representatives.u32le")
    result = dict(
        grid=vars(grid),
        tile_cells=tile_cells,
        tiles=tiles,
        representatives=len(representatives),
        representatives_sha256=sha256_file(directory / "representatives.u32le"),
        processing_seconds=time.monotonic() - started,
    )
    (directory / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
