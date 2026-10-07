#!/usr/bin/env python3
"""Reproduce the one-component Vava’u source/current support comparison."""
import argparse
import json
from pathlib import Path

from pyproj import Geod
from shapely import __version__ as shapely_version
from shapely.geometry import shape

CONTACT = "gb:TON:ADM1:12702645B14713027314985"
SHAPE_ID = "12702645B14713027314985"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def feature_by_id(path, feature_id):
    collection = load(path)
    for feature in collection["features"]:
        props = feature.get("properties", {})
        if feature.get("id") == feature_id or props.get("shapeID") == feature_id:
            return shape(feature["geometry"])
    raise ValueError(f"Feature not found: {feature_id} in {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--physical-record", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--current", required=True)
    args = parser.parse_args()

    physical = load(args.physical_record)["record"]
    candidate = shape(physical["complete_support"]["mapped_land_support"]["geometry"])
    source = feature_by_id(args.source, SHAPE_ID)
    current = feature_by_id(args.current, CONTACT)
    geod = Geod(ellps="WGS84")

    def geod_area(geometry):
        area, _ = geod.geometry_area_perimeter(geometry)
        return abs(area)

    print(json.dumps({
        "method": "Shapely planar XY predicates on recorded lon/lat; no repair, buffer, transform or densification; WGS84 Geod area of bounded support/intersections only.",
        "shapely_version": shapely_version,
        "candidate_valid": candidate.is_valid,
        "source_valid": source.is_valid,
        "current_valid": current.is_valid,
        "candidate_source_covered": source.covers(candidate),
        "candidate_current_covered": current.covers(candidate),
        "candidate_source_outside_empty": candidate.difference(source).is_empty,
        "candidate_current_outside_empty": candidate.difference(current).is_empty,
        "candidate_area_m2": geod_area(candidate),
        "candidate_source_intersection_area_m2": geod_area(candidate.intersection(source)),
        "candidate_current_intersection_area_m2": geod_area(candidate.intersection(current)),
        "source_candidate_geometry_equal": source.equals(candidate),
        "current_candidate_geometry_equal": current.equals(candidate),
        "limits": [
            "Topological containment does not establish legal boundaries, accuracy, registration, dry land, effective date, or ownership.",
            "Only the single complete retained support pointset is compared; no global producer or geography data is changed."
        ]
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
