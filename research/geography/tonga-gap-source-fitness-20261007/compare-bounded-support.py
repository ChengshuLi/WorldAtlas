#!/usr/bin/env python3
"""Reproduce the one-component Vava’u source/current support comparison."""
import argparse
import json
from pathlib import Path

from shapely import __version__ as shapely_version
from shapely.geometry import box, shape

from geometry import METHOD, land_area_m2

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
    parser.add_argument("--validation-directory", required=True)
    args = parser.parse_args()

    physical = load(args.physical_record)["record"]
    candidate = shape(physical["complete_support"]["mapped_land_support"]["geometry"])
    source = feature_by_id(args.source, SHAPE_ID)
    current = feature_by_id(args.current, CONTACT)
    # Project-approved source-edge WGS84 area helper. Area is only measured for
    # the complete candidate support; containment supplies the source relation.
    candidate_area = land_area_m2(candidate)

    # Nonvacuous synthetic controls exercise the exact covers/difference paths
    # used above and verify positive area from the project helper.
    outer = box(0, 0, 10, 10)
    inside = box(2, 2, 4, 4)
    outside = box(8, 8, 12, 12)
    positive_ok = outer.covers(inside) and inside.difference(outer).is_empty and land_area_m2(inside) > 0
    negative_ok = not outer.covers(outside) and not outside.difference(outer).is_empty and land_area_m2(outside) > 0
    validation_dir = Path(args.validation_directory)
    validation_dir.mkdir(parents=True, exist_ok=True)
    controls = [
        {"version": 1, "method_id": "bounded-vavau-source-comparison", "kind": "positive-control",
         "outcome": "passed" if positive_ok else "failed",
         "case": "A contained polygon is covered; its source difference is empty; project area helper returns positive area."},
        {"version": 1, "method_id": "bounded-vavau-source-comparison", "kind": "negative-control",
         "outcome": "passed" if negative_ok else "failed",
         "case": "A partly exterior polygon is not covered; its source difference is nonempty; project area helper returns positive area."}
    ]
    if not positive_ok or not negative_ok:
        raise RuntimeError("Geographic method control failed")
    for control in controls:
        name = "positive-control.json" if control["kind"] == "positive-control" else "negative-control.json"
        (validation_dir / name).write_text(json.dumps(control, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({
        "method": {"helper": METHOD, "topology": "Shapely planar XY predicates on recorded lon/lat; no repair, buffer, transform or densification."},
        "shapely_version": shapely_version,
        "candidate_valid": candidate.is_valid,
        "source_valid": source.is_valid,
        "current_valid": current.is_valid,
        "candidate_source_covered": source.covers(candidate),
        "candidate_current_covered": current.covers(candidate),
        "candidate_source_outside_empty": candidate.difference(source).is_empty,
        "candidate_current_outside_empty": candidate.difference(current).is_empty,
        "candidate_support_area_m2": candidate_area,
        "positive_control_passed": positive_ok,
        "negative_control_passed": negative_ok,
        "source_candidate_geometry_equal": source.equals(candidate),
        "current_candidate_geometry_equal": current.equals(candidate),
        "limits": [
            "Topological containment does not establish legal boundaries, accuracy, registration, dry land, effective date, or ownership.",
            "Only the single complete retained support pointset is compared; no global producer or geography data is changed."
        ]
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
