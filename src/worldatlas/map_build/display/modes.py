"""Build per-level legends and color lookups over a single encoded map grid."""

from collections import Counter, defaultdict
from pathlib import Path
from typing import TypedDict

from psycopg import Connection

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.display.colors import RGB, assign_land_colors
from worldatlas.map_build.display.neighbors import scan_color_neighbors
from worldatlas.map_build.inputs.configuration import DisplayColors
from worldatlas.map_build.inputs.selection_types import (
    GeographicSelection,
    MapCodeBinding,
)
from worldatlas.shared.files import read_json, write_json


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


def write_map_modes(
    directory: Path,
    grid: Grid,
    geography: GeographicSelection,
    display_colors: DisplayColors,
    output: Path,
) -> str:
    """Save the colors, legend counts, and category lookup for every built level.

    Args:
        directory: Completed map grid directory with a cell count report.
        grid: Dimensions of the completed map.
        geography: Frozen hierarchy and code bindings from the build.
        display_colors: Reserved RGB triples for water and unbuilt land.
        output: Path for the build's map mode snapshot.

    Returns:
        Path to the saved JSON file as a string.
    """
    bindings = sorted(geography["category_bindings"], key=lambda item: item["code"])
    modes = build_map_modes(
        directory,
        grid,
        geography,
        bindings,
        read_json(directory / "report.json")["counts"],
        (display_colors["water_rgb"], display_colors["unbuilt_land_rgb"]),
    )
    return str(write_json(output, modes))


def save_generated_colors(database: Connection, modes: list[MapMode]) -> None:
    """Update the catalog with the latest RGBs from a completed build.

    Args:
        database: Open writable catalog connection. The caller commits.
        modes: Saved map modes with one RGB triple per displayed entity.
    """
    ids: list[int] = []
    colors: list[str] = []
    for mode in modes:
        for entry in mode["legend"]:
            ids.append(entry["id"])
            colors.append("#" + bytes(entry["color"]).hex().upper())
    database.execute(
        """
        UPDATE atlas.geographic_entities AS entity
        SET color_rgb = generated.rgb
        FROM unnest(%s::bigint[], %s::text[]) AS generated(id, rgb)
        WHERE entity.id = generated.id AND entity.color_rgb IS DISTINCT FROM generated.rgb
        """,
        (ids, colors),
    )


def build_map_modes(
    final: Path,
    grid: Grid,
    geography: GeographicSelection,
    bindings: list[MapCodeBinding],
    counts: dict[str, int],
    fill_colors: tuple[RGB, RGB],
) -> list[MapMode]:
    """Build the projected code lookup, legend, and unbuilt count for each mode.

    Args:
        final: Decoded canonical grid directory.
        grid: Dimensions of the completed map.
        geography: Frozen hierarchy from the build.
        bindings: Canonical bindings in the order used by the viewer config.
        counts: Cell counts keyed by map code as a string.
        fill_colors: Fixed RGB colors in (water, unassigned land) order.

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

    neighboring_codes, codes_near_water = scan_color_neighbors(final, grid, land_codes)
    modes: list[MapMode] = []
    for level in sorted(owners_by_level, key=lambda name: (level_depth(name), name)):
        owners = owners_by_level[level]
        totals: Counter[int] = Counter()
        for code, entity_id in owners.items():
            totals[entity_id] += counts[str(code)]
        neighbors: dict[int, set[int]] = {
            owners[code]: set() for code in land_codes if code in owners
        }
        for a, b in neighboring_codes:
            first, second = owners.get(a), owners.get(b)
            if first is not None and second is not None and first != second:
                neighbors[first].add(second)
                neighbors[second].add(first)

        land_near_water = {owners[code] for code in codes_near_water if code in owners}
        colors = assign_land_colors(neighbors, land_near_water, fill_colors)
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
                        "color": list(colors.get(entity_id, fill_colors[0])),
                        "count": count,
                    }
                    for entity_id, count in sorted(totals.items())
                ],
                "unbuilt_cells": grid.width * grid.height - totals.total(),
            }
        )
    return modes
