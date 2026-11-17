"""The four explicit distance policies share scope, shores and nearest kernels."""

from worldatlas.map_build.core.geometry import rasterize
from worldatlas.map_build.division.nearest import nearest, query_roots
from worldatlas.map_build.core.layers import write_layer
from worldatlas.map_build.water.basins import participants, physical_water


def nearest_land(context, scope, directory):
    if not query_roots(scope):
        return write_layer(directory, scope.grid, ())
    roots = set()
    components = context.components("land")
    for feature in scope.rule["features"]["distance_reference"]:
        root = components.component_at(*feature["geometry"]["coordinates"])
        if root is None:
            raise ValueError("a distance reference does not identify parent land")
        roots.add(root)
    references = context.shore_geometry.attach(
        scope.snapshot,
        context.shore_order,
        components=components,
        reference_components=roots,
    )
    return nearest(scope, references, "component", directory=directory)


def nearest_coastal_water(context, scope, directory):
    limit = context.configuration["coastal_band_metres"]
    return nearest(scope, context.water_shores(), "cell", limit, directory=directory)


def nearest_basin_water(context, scope, directory):
    feature = scope.rule["features"]["scope_area"][0]
    bounds, mask = rasterize(feature["geometry"], scope.grid)
    water = physical_water(mask, bounds, context.parent_physical, scope.grid)
    scope.set_eligible_area(water, bounds)
    if not scope.has_output():
        return write_layer(directory, scope.grid, ())
    shores = context.water_shores()
    counts = participants(
        water,
        bounds,
        context.parent_physical,
        context.land_ownership,
        scope.grid,
        [
            (e, e, e)
            for e in getattr(context, "shore_order", [p[0] for p in shores.pairs])
        ],
    )
    eligible = {p[0] for p in shores.pairs}
    counts = {owner: n for owner, n in counts.items() if owner in eligible}
    references = shores.filtered(set(counts))
    result = nearest(
        scope,
        references,
        "cell",
        directory=directory,
    )
    result["participant_shore_edges"] = counts
    result["physical_water_cells"] = int(water.sum())
    return result


def nearest_water(context, scope, directory):
    return nearest(scope, context.water_shores(), "cell", directory=directory)
