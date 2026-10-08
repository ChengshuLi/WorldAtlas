#!/usr/bin/env python3
"""Read-only, exact-source reproduction of the Alaska union control disagreement."""
from __future__ import annotations
import hashlib
import json
import pathlib
import sys
import shapely
from shapely.geometry import shape
from shapely.ops import unary_union

ROOT = pathlib.Path(__file__).resolve().parents[3]
CAMPAIGN = ROOT / "research/geography/alaska-thirteen-geometry-measurement-20261008"
PHASE = json.loads((CAMPAIGN / "phase-admission.json").read_bytes())
TARGET_ID = "gb:USA:ADM2:52423323B46246640861022"
COMPONENT_ID = "physical-component:073d9a81648d56c1b63a4e495fbd0140c17659bedb5c9b211739642b438ee488"
INPUTS = {
    "research/geography/alaska-thirteen-source-fitness-20261008/sources/candidate-components.geojson": "exact-13-candidate-geometries",
    "research/geography/alaska-thirteen-source-fitness-20261008/sources/native-atlas-target-features.geojson": "seven-atlas-target-geometries",
}

def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def load_pinned(path: str, role: str):
    row = next((item for item in PHASE["inputs"] if item["path"] == path and item["role"] == role), None)
    if row is None:
        raise ValueError(f"phase admission lacks expected input pin: {path}")
    raw = (ROOT / path).read_bytes()
    if len(raw) != row["bytes"] or digest(raw) != row["sha256"]:
        raise ValueError(f"source differs from admitted exact bytes: {path}")
    return json.loads(raw)

def describe(geom):
    return {
        "geometry_type": geom.geom_type,
        "is_empty": bool(geom.is_empty),
        "is_valid": bool(geom.is_valid),
        "area": geom.area,
        "length": geom.length,
        "bounds": list(geom.bounds) if not geom.is_empty else None,
        "wkb_sha256": digest(geom.wkb),
    }

script_path = "research/geography/alaska-thirteen-geometry-measurement-20261008/reproduce_union_control.py"
script_pin = next(row for row in PHASE["project_code"] if row["path"] == script_path)
script_raw = pathlib.Path(__file__).read_bytes()
if len(script_raw) != script_pin["bytes"] or digest(script_raw) != script_pin["sha256"]:
    raise ValueError("diagnostic script differs from phase code pin")
features = {}
for path, role in INPUTS.items():
    fc = load_pinned(path, role)
    features.update((feature["id"], feature) for feature in fc["features"])
old = shape(features[TARGET_ID]["geometry"])
candidate = shape(features[COMPONENT_ID]["geometry"])
unionary = unary_union([old, candidate])
union_method = old.union(candidate)
old_minus_unionary = old.difference(unionary)
boundary_minus_unionary = old.boundary.difference(unionary)
old_parts = list(old.geoms) if old.geom_type == "MultiPolygon" else [old]
part_failures = []
for index, part in enumerate(old_parts):
    part_difference = part.difference(unionary)
    if not unionary.covers(part):
        part_failures.append({"index": index, "part": describe(part),
            "part_relation_to_union": part.relate(unionary),
            "union_covers_part": bool(unionary.covers(part)),
            "part_difference_union": describe(part_difference),
            "part_relation_to_candidate": part.relate(candidate),
            "candidate_relation_to_part": candidate.relate(part),
            "part_intersection_candidate": describe(part.intersection(candidate)),
            "part_difference_candidate": describe(part.difference(candidate)),
            "part_union_candidate": describe(part.union(candidate)),
            "part_union_candidate_covers_part": bool(part.union(candidate).covers(part)),
            "part_union_candidate_relation_to_part": part.relate(part.union(candidate))})
variants = {"unary_union_old_then_candidate": unionary,
            "old_union_candidate": union_method,
            "candidate_union_old": candidate.union(old)}
result = {
    "status": "diagnostic-only-no-qualification",
    "source_pins": [{"path": path, "role": role,
        "bytes": next(row["bytes"] for row in PHASE["inputs"] if row["path"] == path and row["role"] == role),
        "sha256": next(row["sha256"] for row in PHASE["inputs"] if row["path"] == path and row["role"] == role)}
        for path, role in INPUTS.items()],
    "runtime": {"shapely": shapely.__version__, "geos": shapely.geos_version_string},
    "target_source_id": TARGET_ID,
    "component_id": COMPONENT_ID,
    "old_target": describe(old),
    "candidate": describe(candidate),
    "old_target_self_relation": old.relate(old),
    "old_target_self_covers": bool(old.covers(old)),
    "old_target_polygon_part_count": len(old_parts),
    "old_target_polygon_part_cover_failure_count": len(part_failures),
    "old_target_polygon_part_cover_failures": part_failures,
    "old_target_relation_to_unary_union": old.relate(unionary),
    "union_relation_to_old_target": unionary.relate(old),
    "unary_union": describe(unionary),
    "old_target_difference_unary_union": describe(old_minus_unionary),
    "old_boundary_difference_unary_union": describe(boundary_minus_unionary),
    "predicates": {
        "unary_union_covers_old": bool(unionary.covers(old)),
        "old_covers_unary_union": bool(old.covers(unionary)),
        "old_difference_union_empty": bool(old_minus_unionary.is_empty),
        "boundary_difference_union_empty": bool(boundary_minus_unionary.is_empty),
        "unary_union_equals_old_union_candidate": bool(unionary.equals(union_method)),
        "old_union_candidate_covers_old": bool(union_method.covers(old)),
        "old_union_candidate_relation_to_old": old.relate(union_method),
    },
    "union_variants": {name: describe(geom) for name, geom in variants.items()},
}
print(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False))
