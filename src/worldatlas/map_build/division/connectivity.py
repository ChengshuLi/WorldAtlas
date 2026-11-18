"""Select eligible parent components using imported geometric references."""

from pathlib import Path

from worldatlas.map_build.core.layers import write_layer
from worldatlas.map_build.core.rle import row
from worldatlas.map_build.division.intervals import prepare
from worldatlas.map_build.land.connected import build_components


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
