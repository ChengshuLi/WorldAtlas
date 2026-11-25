"""Encode entity ownership and physical class only when packaging a map grid."""

from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.layers import write_run_rows
from worldatlas.map_build.core.rle import open_grid, overlay, row
from worldatlas.map_build.inputs.selection_types import MapCodeBinding


def encode(
    grid: Grid,
    physical_directory: Path | str,
    ownership_directory: Path | str,
    bindings: Sequence[MapCodeBinding],
    directory: Path | str,
) -> dict[str, Any]:
    """Write the final grid of map codes from ownership and physical class.

    Args:
        grid: Dimensions shared by both inputs.
        physical_directory: Grid of land and water codes.
        ownership_directory: Grid of entity IDs.
        bindings: Map codes keyed by entity ID and physical class.
        directory: New directory for the encoded row-run files.

    Returns:
        Layer report with bounds, dimensions and cell counts by map code.

    Raises:
        ValueError: A code binding is ambiguous or missing for a cell's owner and class.
    """
    pairs = sorted(
        ((b["entity_id"] << 1) | (b["physical_class"] == "land"), b["code"])
        for b in bindings
    )
    keys = np.asarray([k for k, _ in pairs], dtype=np.uint64)
    codes = np.asarray([c for _, c in pairs], dtype=np.uint32)
    if not len(keys) or np.any(keys[1:] == keys[:-1]):
        raise ValueError("ambiguous map category bindings")
    with (
        open_grid(physical_directory, grid) as physical,
        open_grid(ownership_directory, grid) as ownership,
    ):

        def rows() -> Iterator[tuple[int, np.ndarray, np.ndarray]]:
            """Encode matching runs of land or water and entity IDs one row at a time.

            Yields:
                (row, ends, codes) with one uint32 array for each run field.
            """
            for y in range(grid.height):
                _, ends, (kind, entity) = overlay(
                    row(physical, y, grid.width), row(ownership, y, grid.width)
                )
                lookup = (entity.astype(np.uint64) << 1) | (kind == 17).astype(
                    np.uint64
                )
                positions = np.searchsorted(keys, lookup)
                safe = np.minimum(positions, len(keys) - 1)
                valid = (positions < len(keys)) & (keys[safe] == lookup)
                if np.any((entity != 0) & ~valid):
                    raise ValueError("missing entity/physical-class map binding")
                values = np.where(entity != 0, codes[safe], 0)
                yield y, ends.astype(np.uint32, copy=False), values

        return write_run_rows(directory, grid, rows())
