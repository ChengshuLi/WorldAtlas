"""The four explicit distance policies share scope, shores and nearest kernels."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import numpy as np

from worldatlas.map_build.division.contracts import point_coordinates
from worldatlas.map_build.division.scope import Scope

if TYPE_CHECKING:
    from worldatlas.map_build.division.engine import ParentDivision

from worldatlas.map_build.core.geometry import rasterize
from worldatlas.map_build.core.layers import write_layer
from worldatlas.map_build.division.nearest import (
    cell_queries,
    component_queries,
    query_roots,
)
from worldatlas.map_build.water.basins import participants, physical_water


def nearest_land(
    context: ParentDivision, scope: Scope, directory: Path | str
) -> dict[str, Any]:
    """Assign land components using the shores of selected reference components.

    Args:
        context: Parent's land components and physical shores.
        scope: Scope and distance reference points for the rule.
        directory: New output directory.

    Returns:
        Claim layer report.

    Raises:
        ValueError: A reference point does not identify parent land.
    """
    query = query_roots(scope)
    if not query:
        return write_layer(directory, scope.grid, ())
    roots = set()
    components = context.components("land")
    for feature in scope.rule["features"]["distance_reference"]:
        root = components.component_at(*point_coordinates(feature))
        if root is None:
            raise ValueError("a distance reference does not identify parent land")
        roots.add(root)
    references = context.shore_geometry.attach(
        scope.snapshot,
        context.shore_order,
        components=components,
        reference_components=roots,
    )
    return component_queries(scope, references, query, directory)


def nearest_coastal_water(
    context: ParentDivision, scope: Scope, directory: Path | str
) -> dict[str, Any]:
    """Assign coastal water within the configured distance from shore.

    Args:
        context: Parent's ownership and coastal distance settings.
        scope: Prepared eligible water cells.
        directory: New output directory.

    Returns:
        Claim layer report. Cells past the distance limit remain available
        to later rules.
    """
    limit = context.configuration["coastal_band_metres"]
    return cell_queries(scope, context.water_shores(), limit, directory=directory)


def nearest_basin_water(
    context: ParentDivision, scope: Scope, directory: Path | str
) -> dict[str, Any]:
    """Assign basin water using the shores of owners that border the basin.

    Args:
        context: Parent's physical water, land owners and shores.
        scope: Rule scope with one basin polygon.
        directory: New output directory.

    Returns:
        Claim layer report. When cells are eligible, include physical-water
        cell counts and bordering shore-edge counts by owner.
    """
    feature = scope.rule["features"]["scope_area"][0]
    bounds, mask = rasterize(dict(feature["geometry"]), scope.grid)
    water = physical_water(mask, bounds, context.parent_physical, scope.grid)
    scope.set_eligible_area(water, bounds)
    if not scope.has_output():
        return write_layer(directory, scope.grid, ())
    shores = context.water_shores()
    counts = participants(
        water,
        bounds,
        context.parent_physical,
        cast(tuple[np.ndarray, np.ndarray], context.land_ownership),
        scope.grid,
        context.shore_order,
    )
    eligible = set(shores.owners)
    counts = {owner: n for owner, n in counts.items() if owner in eligible}
    references = shores.filtered(set(counts))
    result = cell_queries(
        scope,
        references,
        directory=directory,
    )
    result["participant_shore_edges"] = counts
    result["physical_water_cells"] = int(water.sum())
    return result


def nearest_water(
    context: ParentDivision, scope: Scope, directory: Path | str
) -> dict[str, Any]:
    """Assign remaining eligible water to the nearest participating shore.

    Args:
        context: Parent's land owners and their shores.
        scope: Water cells eligible for completion.
        directory: New output directory.

    Returns:
        Claim layer report with counts by owner.
    """
    return cell_queries(scope, context.water_shores(), directory=directory)
