"""Assign selected basin water using current shores, independent of its provider.

Discover participants on the complete physical-water footprint. Only then remove
the water already assigned by the coastal band. Distances use the same exact
WGS84 cell-center solver as coastal assignment, restricted to those participants.
"""

from collections import Counter
from dataclasses import dataclass

import numpy as np

from map_build.water import shared_nearest as nearest
from map_build.water.coastal_shore_index_batch import BatchedCoastalShoreIndex
from map_build.water.rectangle_nearest import classify
from map_build.core.geometry import rasterize


class Shorelines:
    """Share one complete physical shore index and reuse its entity trees."""

    def __init__(self, physical, land, grid, pairs):
        self.grid = grid
        self.pairs = pairs
        codes = [land_code for _, land_code, _ in pairs]
        self.spans = BatchedCoastalShoreIndex(
            physical, land, grid.width, grid.height, land_codes=codes
        )
        present = set(map(int, np.unique(self.spans.codes)))
        self.indexes = {}
        if present:
            centers = self.spans.centers_for_crop(grid.bounds, grid.step, codes)
            self.indexes = nearest.make_indexes(centers, [p for p in pairs if p[1] in present])


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
                    raise ValueError(f'physical shore has unbound land code {code}')
                counts[entities[int(code)]] += int(number)
    return dict(counts)


def assign(water, bounds, grid, shores, participant_counts, tolerance, *, coastal=None):
    """Assign remaining cells; all participant shores remain in the search."""
    if not np.isfinite(tolerance) or tolerance < 0:
        raise ValueError('tie tolerance must be finite and nonnegative')
    chosen = [p for p in shores.pairs if p[0] in participant_counts]
    if set(participant_counts) - {p[0] for p in chosen}:
        raise ValueError('unknown basin participant entity')
    x0, x1, y0, y1 = bounds
    remaining = water.copy()
    if coastal is not None:
        for y in range(y0, y1):
            remaining[y - y0] &= nearest.crop(*coastal, y, x0, x1, grid.width) == 0
    output = np.zeros(water.shape, dtype=np.uint32)
    if not remaining.any():
        return output
    if not chosen:
        raise ValueError('basin has remaining water but no source-backed shore participant')
    if len(chosen) == 1:
        output[remaining] = chosen[0][2]
        return output

    # Full shore trees make omitted-crop shores impossible. Keep the proven
    # rectangular certificates and complete exact refinement for uncertain cells.
    def points(lat, lon):
        return nearest.classify(
            lat,
            lon,
            grid.bounds,
            grid.width,
            grid.height,
            grid.step,
            chosen,
            tolerance,
            shores.indexes,
        )

    for first in range(y0, y1, 256):
        last = min(first + 256, y1)
        for xa, xb in ((x0, min(x1, grid.width)), (0, max(0, x1 - grid.width))):
            if xa == xb:
                continue
            offset = (xa - x0) % grid.width
            selected = remaining[first - y0 : last - y0, offset : offset + xb - xa]
            result, _ = classify(
                selected,
                xa,
                first,
                grid.bounds,
                grid.width,
                grid.height,
                grid.step,
                chosen,
                tolerance,
                shores.indexes,
                points,
            )
            output[first - y0 : last - y0, offset : offset + xb - xa] = result
    return output


@dataclass
class BasinResult:
    bounds: tuple
    water: np.ndarray
    assignments: np.ndarray
    participant_shore_edges: dict


def build_basin(geometry, grid, physical, land, shores, tolerance, *, coastal=None):
    bounds, mask = rasterize(geometry, grid)
    water = physical_water(mask, bounds, physical, grid)
    counts = participants(water, bounds, physical, land, grid, shores.pairs)
    assignments = assign(water, bounds, grid, shores, counts, tolerance, coastal=coastal)
    return BasinResult(bounds, water, assignments, counts)
