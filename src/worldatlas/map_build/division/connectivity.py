"""Select eligible parent components using imported geometric references."""

from pathlib import Path

from shapely import union_all
from shapely.geometry import shape

from worldatlas.map_build.core.layers import write_layer
from worldatlas.map_build.core.rle import row
from worldatlas.map_build.division.intervals import prepare
from worldatlas.map_build.land.connected import build_components


def reference_points(features):
    """Keep explicit points; derive one interior point from combined areas."""
    points, areas = [], []
    for feature in features:
        geometry = feature["geometry"]
        if geometry["type"] == "Point":
            points.append(tuple(geometry["coordinates"]))
        else:
            areas.append(shape(geometry))
    if areas:
        point = union_all(areas).representative_point()
        points.append((point.x, point.y))
    return points


def build_domain(
    grid, physical, parent, snapshot, physical_class, unassigned_only, directory
):
    """Build connectivity before geographic selectors narrow the query extent."""
    directory = Path(directory)
    directory.mkdir()

    def rows():
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
