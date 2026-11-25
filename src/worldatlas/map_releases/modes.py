"""Build per-level legends and color lookups over a single encoded map grid."""

import re
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
from worldatlas.map_releases.colors import RGB, color_land
from worldatlas.shared.files import write_json


class MapMode(TypedDict):
    """Locate one geographic level's display data within the release."""

    level_id: str
    label: str
    path: str


def land_code_borders(
    directory: Path, grid: Grid, land_codes: Sequence[int]
) -> set[tuple[int, int]]:
    """Find pairs of encoded land codes that share at least one cell edge.

    Args:
        directory: Final grid's decoded row offsets and runs.
        grid: Grid dimensions. The last and first columns share an edge.
        land_codes: Map codes with physical class land.

    Returns:
        Unordered borders represented by (smaller code, larger code) tuples.
        A diagonal touch does not contribute a pair.
    """
    # A sorted code lookup works for sparse uint32 codes, including 2**32 - 1.
    land = np.array(sorted(land_codes), dtype=np.uint32)
    packed: set[int] = set()
    previous = None
    with open_grid(directory, grid) as streams:
        for y in range(grid.height):
            ends, codes = row(streams, y, grid.width)
            dry = np.where(np.isin(codes, land, kind="sort"), codes, np.uint32(0))
            current = (ends, dry)
            first, second = dry, np.r_[dry[1:], dry[:1]]
            if previous is not None:
                _, _, (north, south) = overlay(previous, current)
                first, second = np.r_[first, north], np.r_[second, south]
            border = (first != second) & (first != 0) & (second != 0)
            lo, hi = (
                np.minimum(first[border], second[border]),
                np.maximum(first[border], second[border]),
            )
            # Pack both uint32 codes into one word to deduplicate without
            # allocating a Python pair for every occurrence of a border.
            packed.update(np.unique((lo.astype(np.uint64) << 32) | hi).tolist())
            previous = current
    return {(pair >> 32, pair & 0xFFFFFFFF) for pair in packed}


def write_map_modes(
    bundle: Path,
    final: Path,
    grid: Grid,
    geography: GeographicSelection,
    bindings: list[MapCodeBinding],
    counts: dict[str, int],
    water: RGB,
) -> list[MapMode]:
    """Write the projected code lookup, legend, and unbuilt count for each mode.

    Args:
        bundle: Local release directory.
        final: Decoded canonical grid directory.
        grid: Dimensions of the completed map.
        geography: Frozen hierarchy and authored colors from the build.
        bindings: Canonical bindings in the order used by the viewer config.
        counts: Cell counts keyed by map code as a string.
        water: Shared water fill as an 8-bit sRGB triple.

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

    borders = land_code_borders(final, grid, land_codes)
    (bundle / "modes").mkdir()
    modes: list[MapMode] = []
    for level in sorted(owners_by_level, key=lambda name: (level_depth(name), name)):
        owners = owners_by_level[level]
        totals: Counter[int] = Counter()
        for code, entity_id in owners.items():
            totals[entity_id] += counts[str(code)]
        neighbors: dict[int, set[int]] = {
            owners[code]: set() for code in land_codes if code in owners
        }
        for a, b in borders:
            first, second = owners.get(a), owners.get(b)
            if first is not None and second is not None and first != second:
                neighbors[first].add(second)
                neighbors[second].add(first)

        authored: dict[int, RGB] = {}
        for entity_id in neighbors:
            if (color := entities[entity_id]["color_rgb"]) is not None:
                red, green, blue = bytes.fromhex(color[1:])
                authored[entity_id] = (red, green, blue)
        colors = color_land(neighbors, authored, water)
        if re.fullmatch(r"[A-Za-z0-9_-]+", level) is None:
            raise ValueError(f"invalid geographic level for a release path: {level!r}")
        mode_path = f"modes/{level}.json"
        write_json(
            bundle / mode_path,
            {
                "entity_ids_by_category": [
                    owners.get(binding["code"]) for binding in bindings
                ],
                "legend": [
                    {
                        "id": entity_id,
                        "name": entities[entity_id]["name"],
                        "color": list(colors.get(entity_id, water)),
                        "count": count,
                    }
                    for entity_id, count in sorted(totals.items())
                ],
                "unbuilt_cells": grid.width * grid.height - totals.total(),
            },
        )
        modes.append(
            {
                "level_id": level,
                "label": level.replace("_", " ").capitalize(),
                "path": mode_path,
            }
        )
    return modes
