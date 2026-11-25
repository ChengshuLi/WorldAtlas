"""Physical basin footprints and source-neutral shoreline participant discovery."""

from collections import Counter
from collections.abc import Collection

import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.rle import crop


def physical_water(
    mask: np.ndarray,
    bounds: tuple[int, int, int, int],
    physical: tuple[np.ndarray, np.ndarray],
    grid: Grid,
) -> np.ndarray:
    """Keep only the physical water cells in a polygon mask.

    Args:
        mask: Two-dimensional bool polygon mask, updated in place.
        bounds: Grid window represented by the mask.
        physical: Physical row offsets and run data.
        grid: Dimensions of the complete grid.

    Returns:
        The same mask, with land cells cleared.
    """
    x0, x1, y0, y1 = bounds
    for y in range(y0, y1):
        mask[y - y0] &= crop(*physical, y, x0, x1, grid.width) == 1
    return mask


def participants(
    water: np.ndarray,
    bounds: tuple[int, int, int, int],
    physical: tuple[np.ndarray, np.ndarray],
    land: tuple[np.ndarray, np.ndarray],
    grid: Grid,
    owners: Collection[int],
) -> dict[int, int]:
    """Count the shore edges touching water in the basin.

    Args:
        water: Bool mask of physical water inside the basin.
        bounds: Basin grid window, with exclusive ends.
        physical: Land and water grid streams.
        land: Land ownership grid streams.
        grid: Complete grid, including the longitude seam.
        owners: Child entity IDs allowed to own physical shores.

    Returns:
        Dictionary from bordering owner code to the number of edges where
        its physical land touches basin water.
    """
    x0, x1, y0, y1 = bounds
    eligible = set(owners)
    counts = Counter()
    for y in range(y0, y1):
        selected = water[y - y0]
        if not selected.any():
            continue
        for dy, dx in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            adjacent = y + dy
            if not 0 <= adjacent < grid.height:
                continue
            dry = crop(*physical, adjacent, x0 + dx, x1 + dx, grid.width) == 17
            land_codes = crop(*land, adjacent, x0 + dx, x1 + dx, grid.width)
            codes, numbers = np.unique(land_codes[selected & dry], return_counts=True)
            for code, number in zip(codes, numbers):
                if int(code) not in eligible:
                    raise ValueError(f"physical shore has unknown shore owner {code}")
                counts[int(code)] += int(number)
    return dict(counts)
