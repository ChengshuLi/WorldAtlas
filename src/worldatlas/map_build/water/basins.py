"""Physical basin footprints and source-neutral shoreline participant discovery."""

from collections import Counter
import numpy as np
from worldatlas.map_build.water import shared_nearest as nearest


def physical_water(mask, bounds, physical, grid):
    x0, x1, y0, y1 = bounds
    for y in range(y0, y1):
        mask[y - y0] &= nearest.crop(*physical, y, x0, x1, grid.width) == 1
    return mask


def participants(water, bounds, physical, land, grid, pairs):
    """Count basin-water edges touching each entity's physical land shore."""
    x0, x1, y0, y1 = bounds
    entities = {land_code: entity for entity, land_code, _ in pairs}
    counts = Counter()
    for y in range(y0, y1):
        selected = water[y - y0]
        if not selected.any():
            continue
        for dy, dx in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            adjacent = y + dy
            if not 0 <= adjacent < grid.height:
                continue
            dry = nearest.crop(*physical, adjacent, x0 + dx, x1 + dx, grid.width) == 17
            land_codes = nearest.crop(*land, adjacent, x0 + dx, x1 + dx, grid.width)
            codes, numbers = np.unique(land_codes[selected & dry], return_counts=True)
            for code, number in zip(codes, numbers):
                if int(code) not in entities:
                    raise ValueError(f"physical shore has unbound land code {code}")
                counts[entities[int(code)]] += int(number)
    return dict(counts)
