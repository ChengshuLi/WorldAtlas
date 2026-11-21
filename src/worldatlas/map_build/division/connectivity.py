"""Select eligible parent components using imported geometric references."""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.layers import write_layer
from worldatlas.map_build.core.rle import row
from worldatlas.map_build.division.intervals import prepare
from worldatlas.map_build.land.connected import build_components


def build_domain(
    grid: Grid,
    physical: tuple[np.ndarray, np.ndarray],
    parent: tuple[np.ndarray, np.ndarray],
    snapshot: tuple[np.ndarray, np.ndarray],
    physical_class: str,
    unassigned_only: bool,
    directory: Path | str,
) -> dict[str, Any]:
    """Find connected components of the cells a rule may claim.

    Apply parent, class and prior-ownership filters before any polygon scope.
    This lets a water rule use the full water component that contains its point.

    Args:
        grid: Dimensions for all three input grids.
        physical: Physical land and water streams.
        parent: Row-run mask of the parent's cells.
        snapshot: Row-run owner IDs before the rule group.
        physical_class: Eligible class, or "mixed" for both.
        unassigned_only: Whether to exclude cells that already have an owner.
        directory: New directory for the domain mask and components.

    Returns:
        Report for the connected-component grid.
    """
    directory = Path(directory)
    directory.mkdir()

    def rows() -> Iterator[tuple[int, list[tuple[int, int, int]]]]:
        """Read each row and mark its eligible cells.

        Yields:
            (row, spans) with code 1 on each eligible span.
        """
        for y in range(grid.height):
            within = row(parent, y, grid.width)
            records = prepare(
                row(physical, y, grid.width),
                within,
                within,
                row(snapshot, y, grid.width),
                physical_class=physical_class,
                unassigned_only=unassigned_only,
            )
            if records:
                yield y, records

    mask = directory / "domain"
    write_layer(mask, grid, rows())
    return build_components(grid, mask, directory / "components", physical_code=1)
