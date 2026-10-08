#!/usr/bin/env python3
"""Check complete candidate and local contact geometry against COG coverage.

This reads existing immutable result geometries and computes coordinate bounds
only. It does not run spatial overlays, rasterize, resample, or classify pixels.
"""

from __future__ import annotations

import gzip
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


BASE = Path(__file__).resolve().parent
PACKET = BASE.parent
RESULT = PACKET / "run-one" / "source-geometry-results.json.gz"
RANGES = BASE / "worldcover-source-ranges.json"
OUTPUT = BASE / "source-coverage.json"
EXPECTED_COMPONENTS = 10
EXPECTED_SUBJECTS = {
    "gb:ZMB:ADM2:96606910B35256638811207",
    "gb:ZMB:ADM2:96606910B48730551364911",
    "gb:ZMB:ADM2:96606910B70191271227661",
    "gb:ZWE:ADM2:62879985B85730198836463",
}
EPS = 1e-12


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def walk_coords(value):
    if isinstance(value, (list, tuple)):
        if len(value) >= 2 and isinstance(value[0], (int, float)) and isinstance(value[1], (int, float)):
            yield float(value[0]), float(value[1])
        else:
            for child in value:
                yield from walk_coords(child)


def geometry_envelope(geometry: dict) -> dict:
    points = list(walk_coords(geometry.get("coordinates")))
    for child in geometry.get("geometries", []):
        points.extend(walk_coords(child.get("coordinates")))
        for grandchild in child.get("geometries", []):
            points.extend(walk_coords(grandchild.get("coordinates")))
    if not points:
        return {"coordinate_count": 0, "bounds_lonlat": None, "empty": True}
    xs, ys = zip(*points)
    return {"coordinate_count": len(points), "bounds_lonlat": [min(xs), min(ys), max(xs), max(ys)], "empty": False}


def assert_inside(label: str, geometry: dict, bbox: list[float], records: list[dict]):
    bounds = geometry_envelope(geometry)
    if bounds["empty"]:
        records.append({"id": label, **bounds, "inside_complete_issue_window": None})
        return bounds
    west, south, east, north = bbox
    min_x, min_y, max_x, max_y = bounds["bounds_lonlat"]
    if min_x < west - EPS or min_y < south - EPS or max_x > east + EPS or max_y > north + EPS:
        raise RuntimeError(f"{label} escapes selected pixel window: {bounds['bounds_lonlat']}")
    records.append({"id": label, **bounds, "inside_complete_issue_window": True})
    return bounds


def main():
    ranges = json.loads(RANGES.read_text(encoding="utf-8"))
    source_bbox = ranges["issue_extent_lonlat"]
    window = ranges["complete_pixel_window"]
    width, height = window["dimensions"]
    pixel_scale = ranges["source"]["pixel_scale_degrees"]
    origin_x, origin_y = ranges["source"]["pixel_origin_lonlat"]
    window_bbox = [
        origin_x + window["columns_half_open"][0] * pixel_scale[0],
        origin_y - window["rows_half_open"][1] * pixel_scale[1],
        origin_x + window["columns_half_open"][1] * pixel_scale[0],
        origin_y - window["rows_half_open"][0] * pixel_scale[1],
    ]
    if width != 9_234 or height != 5_146 or window["decoded_bytes"] != 47_518_164:
        raise RuntimeError("Unexpected source-window pixel dimensions")
    if not (
        window_bbox[0] <= source_bbox[0]
        and window_bbox[1] <= source_bbox[1]
        and window_bbox[2] >= source_bbox[2]
        and window_bbox[3] >= source_bbox[3]
    ):
        raise RuntimeError("Selected pixel support does not fully cover issue bbox")

    result_bytes = RESULT.read_bytes()
    data = json.loads(gzip.decompress(result_bytes))
    components = data["components"]
    subjects = set(data["subject_ids"])
    component_ids = set(data["component_ids"])
    if len(components) != EXPECTED_COMPONENTS or len(component_ids) != EXPECTED_COMPONENTS:
        raise RuntimeError("Original complete component roster is incomplete")
    if subjects != EXPECTED_SUBJECTS:
        raise RuntimeError("Original four contact-subject roster changed")

    records: list[dict] = []
    subject_intersections = {subject: {"bindings": 0, "nonempty": 0, "empty": 0} for subject in subjects}
    for component in components:
        component_id = component["component_id"]
        assert_inside(
            f"candidate:{component_id}",
            component["original_component_feature"]["geometry"],
            source_bbox,
            records,
        )
        for row in component["source_feature_intersections"]:
            source_id = f"gb:{row['country']}:ADM2:{row['shapeID']}"
            if source_id not in subject_intersections:
                continue
            geometry = row["intersection"]["geometry"]
            intersection = row["intersection"]
            if intersection.get("empty") != (geometry_envelope(geometry)["empty"]):
                raise RuntimeError(f"Intersection emptiness mismatch: {component_id}:{source_id}")
            assert_inside(f"local-contact-intersection:{component_id}:{source_id}", geometry, source_bbox, records)
            subject_intersections[source_id]["bindings"] += 1
            subject_intersections[source_id]["empty" if intersection["empty"] else "nonempty"] += 1
    if any(row["bindings"] == 0 or row["nonempty"] == 0 for row in subject_intersections.values()):
        raise RuntimeError(f"One or more contact subjects lack a bound local intersection: {subject_intersections}")

    fragment_features = data["original_contact_fragment_features"]
    if len(fragment_features) != 2:
        raise RuntimeError("Expected both original fragment features for the point-only contact")
    for feature in fragment_features:
        assert_inside(f"contact-fragment:{feature['id']}", feature["geometry"], source_bbox, records)
    contact_rows = data["original_source_contacts"]["matched_rows"]
    if len(contact_rows) != 1:
        raise RuntimeError("Expected the retained point-only contact row")
    for index, row in enumerate(contact_rows):
        assert_inside(f"original-contact-row:{index}:{row['kind']}", row["geometry"], source_bbox, records)

    manifest = {
        "version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "method": "coordinate-envelope containment against COG source-window pixel support; no geometry operations",
        "source_result": {
            "path": str(RESULT.relative_to(PACKET.parent)),
            "compressed_bytes": len(result_bytes),
            "sha256": hashlib.sha256(result_bytes).hexdigest(),
            "decoded_bytes": len(gzip.decompress(result_bytes)),
        },
        "source_window": {
            "bbox_lonlat": source_bbox,
            "pixel_support_bounds_lonlat": window_bbox,
            "pixel_window": window,
            "selected_block_count": ranges["selected_block_count"],
            "selected_block_rows": [7, 12],
            "selected_block_columns": [21, 30],
        },
        "complete_components": {"count": len(component_ids), "ids": sorted(component_ids)},
        "contact_subjects": {
            "count": len(subjects),
            "ids": sorted(subjects),
            "local_candidate_intersection_bindings": subject_intersections,
            "whole_administrative_subjects_included_in_window": False,
            "scope_note": "The source window covers each complete candidate footprint and every local source intersection for the four subjects, not the full extent of the four neighboring administrative polygons.",
        },
        "point_only_contact": {"row_count": len(contact_rows), "fragment_feature_count": len(fragment_features)},
        "checked_geometries": len(records),
        "records": records,
        "result": "complete candidate footprints and local contact geometries are within the retained source window",
        "limits": [
            "Coordinate-envelope inclusion proves the source grid window covers these retained geometries; it does not establish physical classification or position accuracy.",
            "The four full neighboring ADM2 polygons extend beyond this local water-classification window and are not claimed to be covered or classified.",
        ],
    }
    OUTPUT.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result": manifest["result"], "checked_geometries": len(records), "components": len(component_ids), "contact_subjects": len(subjects), "manifest": str(OUTPUT)}, indent=2))


if __name__ == "__main__":
    main()
