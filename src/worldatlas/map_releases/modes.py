"""Build per-level legends and color lookups over a single encoded map grid."""

from collections import Counter, defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import TypedDict

import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.rle import open_grid, overlay, row
from worldatlas.map_build.inputs.selection_types import (
    GeographicSelection,
    MapCodeBinding,
)
from worldatlas.map_releases.colors import RGB, WATER, color_land


class LegendEntry(TypedDict):
    """Describe one entity shown in the legend."""

    id: int
    name: str
    color: list[int]
    count: int


class MapMode(TypedDict):
    """Describe how the shared grid is displayed at one geographic level."""

    level_id: str
    label: str
    entity_ids_by_category: list[int | None]
    legend: list[LegendEntry]
    unbuilt_cells: int


def packed_land_pairs(first: np.ndarray, second: np.ndarray) -> list[int]:
    """Deduplicate distinct land codes aligned by cell edge or screen proximity.

    Args:
        first: Array of uint32 land codes or zero for water or uncovered cells.
        second: Matching array of codes paired with the first array.

    Returns:
        Unique pairs packed into uint64 words, with the smaller code first.
    """
    keep = (first != second) & (first != 0) & (second != 0)
    low = np.minimum(first[keep], second[keep]).astype(np.uint64)
    high = np.maximum(first[keep], second[keep])
    return np.unique((low << 32) | high).tolist()


def nearby_land_pairs(overview: np.ndarray, radius: int) -> set[int]:
    """Find land codes that look close together on the overview map.

    Args:
        overview: Two-dimensional uint32 land-code grid. Water is zero.
        radius: Maximum distance between sample centers, in overview pixels.

    Returns:
        Packed pairs with land samples within the radius. Columns wrap at the
        dateline. Rows stop at the top and bottom of the map.
    """
    pairs: set[int] = set()
    for dy in range(min(radius + 1, len(overview))):
        for dx in range(-radius, radius + 1):
            if (dy == 0 and dx <= 0) or dx * dx + dy * dy > radius * radius:
                continue
            aligned = np.roll(overview, -dx, axis=1)
            pairs.update(
                packed_land_pairs(overview[: len(overview) - dy], aligned[dy:])
            )
    return pairs


def land_code_relationships(
    directory: Path, grid: Grid, land_codes: Sequence[int]
) -> tuple[set[tuple[int, int]], set[tuple[int, int]]]:
    """Find exact land borders and nearby land on the overview in one grid read.

    Args:
        directory: Final grid's decoded row offsets and runs.
        grid: Grid dimensions. The last and first columns share an edge.
        land_codes: Map codes with physical class land.

    Returns:
        (Shared-edge pairs, nearby pairs), both as sets of ascending code tuples.
        Proximity spans about two degrees on screen, including across water.
    """
    if not land_codes:
        return set(), set()

    # Search the sorted list without scanning every land code for each row.
    land = np.array(sorted(land_codes), dtype=np.uint32)
    borders: set[int] = set()
    # About half a degree per sample. Use this overview for color preferences
    # and keep the exact shared-edge check on the original grid.
    width = min(720, grid.width)
    height = max(1, round(grid.height * width / grid.width))
    sample_x = (np.arange(width) + 0.5) * grid.width / width
    sample_y = ((np.arange(height) + 0.5) * grid.height / height).astype(int)
    overview = np.empty((height, width), dtype=np.uint32)
    overview_row_by_source = {y: i for i, y in enumerate(sample_y)}
    previous = None
    with open_grid(directory, grid) as streams:
        for y in range(grid.height):
            ends, codes = row(streams, y, grid.width)
            # An insertion point beyond the last land code clips to the last
            # entry and fails the exact comparison.
            matching = land.take(land.searchsorted(codes), mode="clip")
            dry = np.where(matching == codes, codes, np.uint32(0))
            current = (ends, dry)
            first, second = dry, np.r_[dry[1:], dry[:1]]
            if previous is not None:
                _, _, (north, south) = overlay(previous, current)
                first, second = np.r_[first, north], np.r_[second, south]
            borders.update(packed_land_pairs(first, second))
            if (overview_row := overview_row_by_source.get(y)) is not None:
                overview[overview_row] = dry[
                    np.searchsorted(ends, sample_x, side="right")
                ]
            previous = current

    near = nearby_land_pairs(overview, radius=width // 180)
    return (
        {(pair >> 32, pair & 0xFFFFFFFF) for pair in borders},
        {(pair >> 32, pair & 0xFFFFFFFF) for pair in near - borders},
    )


def build_map_modes(
    final: Path,
    grid: Grid,
    geography: GeographicSelection,
    bindings: list[MapCodeBinding],
    counts: dict[str, int],
) -> list[MapMode]:
    """Build the projected code lookup, legend, and unbuilt count for each mode.

    Args:
        final: Decoded canonical grid directory.
        grid: Dimensions of the completed map.
        geography: Frozen hierarchy and authored colors from the build.
        bindings: Canonical bindings in the order used by the viewer config.
        counts: Cell counts keyed by map code as a string.

    Returns:
        Mode descriptors ordered from shallowest to deepest geographic level.
    """
    entities = {entity["id"]: entity for entity in geography["entities"]}
    level_parents = {level["id"]: level["parent_id"] for level in geography["levels"]}
    owners_by_level: dict[str, dict[int, int]] = defaultdict(dict)
    land_codes = []
    for binding in bindings:
        code = binding["code"]
        if not counts.get(str(code), 0):
            continue
        if binding["physical_class"] == "land":
            land_codes.append(code)
        entity = entities[binding["entity_id"]]
        while (parent := entity["parent_id"]) is not None:
            owners_by_level[entity["level_id"]][code] = entity["id"]
            entity = entities[parent]

    def level_depth(level: str) -> int:
        """Count the ancestor levels above a geographic level.

        Args:
            level: Catalog ID, for example, subcontinent.

        Returns:
            Number of levels above this level, including the root.
        """
        depth = 0
        while (parent := level_parents[level]) is not None:
            depth += 1
            level = parent
        return depth

    borders, nearby = land_code_relationships(final, grid, land_codes)
    modes: list[MapMode] = []
    for level in sorted(owners_by_level, key=lambda name: (level_depth(name), name)):
        owners = owners_by_level[level]
        totals: Counter[int] = Counter()
        for code, entity_id in owners.items():
            totals[entity_id] += counts[str(code)]
        neighbors: dict[int, set[int]] = {
            owners[code]: set() for code in land_codes if code in owners
        }
        nearby_neighbors: dict[int, set[int]] = {entity: set() for entity in neighbors}
        for graph, pairs in ((neighbors, borders), (nearby_neighbors, nearby)):
            for a, b in pairs:
                first, second = owners.get(a), owners.get(b)
                if first is not None and second is not None and first != second:
                    graph[first].add(second)
                    graph[second].add(first)

        authored: dict[int, RGB] = {}
        for entity_id in neighbors:
            if (color := entities[entity_id]["color_rgb"]) is not None:
                red, green, blue = bytes.fromhex(color[1:])
                authored[entity_id] = (red, green, blue)
        colors = color_land(neighbors, nearby_neighbors, authored)
        modes.append(
            {
                "level_id": level,
                "label": level.replace("_", " ").capitalize(),
                "entity_ids_by_category": [
                    owners.get(binding["code"]) for binding in bindings
                ],
                "legend": [
                    {
                        "id": entity_id,
                        "name": entities[entity_id]["name"],
                        "color": list(colors.get(entity_id, WATER)),
                        "count": count,
                    }
                    for entity_id, count in sorted(totals.items())
                ],
                "unbuilt_cells": grid.width * grid.height - totals.total(),
            }
        )
    return modes
