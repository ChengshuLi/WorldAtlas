"""Inventory source exceptions before constructing a continent-cell proposal."""

import argparse
import hashlib
import json
from pathlib import Path

import shapefile
from shapely.geometry import shape


def inspect(source_dir: Path):
    reader = shapefile.Reader(
        str(source_dir / "ne_10m_admin_0_map_units/ne_10m_admin_0_map_units.shp")
    )
    exceptions = []
    transcontinental = {
        "Russia",
        "Turkey",
        "Kazakhstan",
        "Egypt",
        "Indonesia",
        "Georgia",
        "Azerbaijan",
    }
    for item in reader.iterShapeRecords():
        attrs = item.record.as_dict()
        geom = shape(item.shape.__geo_interface__)
        if (
            attrs["ADMIN"] in transcontinental
            or attrs["CONTINENT"] == "Seven seas (open ocean)"
        ):
            exceptions.append(
                {
                    "name": attrs["GEOUNIT"],
                    "source_continent": attrs["CONTINENT"],
                    "bounds": list(geom.bounds),
                    "reason": "Requires explicit geographic allocation; do not copy country continent tag.",
                }
            )
    archives = [
        {"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        for path in sorted(source_dir.glob("*.zip"))
    ]
    return {
        "status": "research_only",
        "exceptions": exceptions,
        "archives": archives,
        "grid": {
            "width": 16384,
            "height": 6827,
            "step_degrees": 360 / 16384,
            "north": 90,
            "west": -180,
            "southern_edge": 90 - 6827 * 360 / 16384,
        },
        "warning": "Natural Earth physical labels are approximate label geometries, not precise continent or ocean boundary authority.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_text(json.dumps(inspect(args.source_dir), indent=2) + "\n")
