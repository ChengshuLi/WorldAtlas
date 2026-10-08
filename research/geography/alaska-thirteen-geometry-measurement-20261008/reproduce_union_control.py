#!/usr/bin/env python3
"""Read-only, exact-source reproduction of the Alaska union control disagreement."""
from __future__ import annotations
import hashlib
import json
import pathlib
import struct
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
    "research/geography/alaska-thirteen-source-fitness-20261008/sources/candidate-source-screen.json": "scope-and-join-contract",
    "research/geography/alaska-thirteen-geometry-measurement-20261008/sources/atlas-neighbors/features.geojson": "17-original-atlas-neighbor-features",
    "research/geography/alaska-thirteen-source-fitness-20261008/sources/physical-query-rows.jsonl": "25-physical-relations",
    "research/geography/alaska-thirteen-geometry-measurement-20261008/sources/native-selected/records.bin": "authenticated-selected-native-records",
    "research/geography/alaska-thirteen-geometry-measurement-20261008/sources/native-selected/receipt.json": "native-selection-authentication-receipt",
}

def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def pinned_bytes(path: str, role: str) -> bytes:
    row = next((item for item in PHASE["inputs"] if item["path"] == path and item["role"] == role), None)
    if row is None:
        raise ValueError(f"phase admission lacks expected input pin: {path}")
    raw = (ROOT / path).read_bytes()
    if len(raw) != row["bytes"] or digest(raw) != row["sha256"]:
        raise ValueError(f"source differs from admitted exact bytes: {path}")
    return raw

def load_pinned(path: str, role: str):
    return json.loads(pinned_bytes(path, role))

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
def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode()

physical_raw = pinned_bytes("research/geography/alaska-thirteen-source-fitness-20261008/sources/physical-query-rows.jsonl", "25-physical-relations")
physical_rows = [json.loads(line) for line in physical_raw.decode().splitlines()]
first_physical = next(row for row in physical_rows if row["component_id"] == COMPONENT_ID)
native_receipt = load_pinned("research/geography/alaska-thirteen-geometry-measurement-20261008/sources/native-selected/receipt.json", "native-selection-authentication-receipt")
native_raw = pinned_bytes("research/geography/alaska-thirteen-geometry-measurement-20261008/sources/native-selected/records.bin", "authenticated-selected-native-records")
native_hash_rows = []
for native_id in (2, 1083):
    row = next(item for item in native_receipt["selected_output"]["records"] if item["id"] == native_id)
    record = native_raw[row["output_offset"]:row["output_offset"] + row["bytes"]]
    header = struct.unpack(">11i", record[:44])
    coords = list(struct.iter_unpack(">2i", record[44:]))
    original_points = [(x * 1e-6, y * 1e-6) for x, y in coords]
    normalized_points = [(lon - 360.0 if lon > 180.0 else lon, lat) for lon, lat in original_points]
    normalized_binary64 = hashlib.sha256(b"".join(struct.pack(">2d", lon, lat) for lon, lat in normalized_points)).hexdigest()
    source_relation = next(rel for rel in first_physical["query_relations"] if rel["source_id"] == native_id)
    native_hash_rows.append({"native_id": native_id,
        "record_sha256_matches": hashlib.sha256(record).hexdigest() == source_relation["source_record_sha256"],
        "header_level_matches": (header[2] & 0xff) == source_relation["source_level"],
        "source_pointset_sha256": source_relation["source_pointset_sha256"],
        "measurement_decoder_original_json_pointset_sha256": hashlib.sha256(canonical(original_points)).hexdigest(),
        "measurement_decoder_normalized_binary64_pointset_sha256": normalized_binary64,
        "pointset_hash_matches": normalized_binary64 == source_relation["source_pointset_sha256"],
        "original_relation": {key: source_relation[key] for key in ("source_covers_candidate", "candidate_covers_source", "disjoint", "witness")}})

features = {}
for path, role in INPUTS.items():
    if not path.endswith(".geojson"):
        continue
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
screen = load_pinned("research/geography/alaska-thirteen-source-fitness-20261008/sources/candidate-source-screen.json", "scope-and-join-contract")
neighbors_fc = load_pinned("research/geography/alaska-thirteen-geometry-measurement-20261008/sources/atlas-neighbors/features.geojson", "17-original-atlas-neighbor-features")
neighbor_geoms = {feature["id"]: shape(feature["geometry"]) for feature in neighbors_fc["features"]}
single_candidate_trials = []
for finding in screen["findings"]:
    cid = finding["component_id"]
    target_id = finding["admin_context"]["atlas_target_original_id"]
    candidate_geom = shape(features[cid]["geometry"])
    old_geom = shape(features["gb:USA:ADM2:" + target_id]["geometry"])
    proposed = unary_union([old_geom, candidate_geom])
    loss = old_geom.difference(proposed)
    gain = proposed.difference(old_geom)
    expected = candidate_geom.difference(old_geom)
    added_neighbor_overlaps = []
    neighbor_results = []
    for neighbor_id, neighbor_geom in sorted(neighbor_geoms.items()):
        if neighbor_id == "gb:USA:ADM2:" + target_id:
            continue
        overlap = gain.intersection(neighbor_geom)
        is_positive = bool(overlap.area > 0)
        neighbor_results.append({"neighbor_source_id": neighbor_id,
            "gain_intersection": describe(overlap), "new_positive_area_overlap": is_positive})
        if is_positive:
            added_neighbor_overlaps.append(neighbor_id)
    preserved = bool(proposed.covers(old_geom) and loss.is_empty)
    gain_match = bool(gain.equals(expected) and gain.symmetric_difference(expected).is_empty)
    retained = bool(proposed.covers(candidate_geom))
    single_candidate_trials.append({"component_id": cid, "target_source_id": "gb:USA:ADM2:" + target_id,
        "candidate": describe(candidate_geom), "old_target": describe(old_geom),
        "proposed_union": describe(proposed), "old_target_relation_to_union": old_geom.relate(proposed),
        "old_target_preserved_without_loss": preserved, "old_target_loss": describe(loss),
        "candidate_retained": retained, "actual_gain": describe(gain),
        "expected_gain": describe(expected), "gain_equals_candidate_minus_old_target": gain_match,
        "added_neighbor_overlaps": added_neighbor_overlaps,
        "neighbor_checks": neighbor_results,
        "single_case_strict_geometry_gate_pass": bool(proposed.is_valid and preserved and retained
            and gain_match and gain.area > 0 and not added_neighbor_overlaps)})
variants = {"unary_union_old_then_candidate": unionary,
            "old_union_candidate": union_method,
            "candidate_union_old": candidate.union(old)}
CANDIDATE_GROUPS = {
    "52423323B46246640861022": [
        "physical-component:073d9a81648d56c1b63a4e495fbd0140c17659bedb5c9b211739642b438ee488",
        "physical-component:8fb2ed9360ba13f6b19f8bb6ee9a16099039d8b59c9f51eab0a442249f428e7d",
    ],
    "52423323B16539688175930": [
        "physical-component:4d36c81ff35079341e6ec0d5a207ba3844e26f5d55c30c7205924dfd33b8dc18",
        "physical-component:70174bffffdbb4a421344d6c10d80b760972f9c5452daf0d7c26408fdf18bb53",
        "physical-component:8435dc6d973751bab55c4eff12c872ba331c3e005254ceb21b76933a8cc6207a",
    ],
    "52423323B80008995120080": [
        "physical-component:5874689a46f7945e9dcc67cc3b0321d4e534572e4b4bd8a85f4a07c5005d1922",
        "physical-component:777e7bc99320bf155684f99b0903c336f9a07862de4a7fa0ac8cde990d7d6ee5",
    ],
}
batch_diagnostics = []
for target_id, candidate_ids in CANDIDATE_GROUPS.items():
    old_target = shape(features["gb:USA:ADM2:" + target_id]["geometry"])
    for size in (2, 3):
        if len(candidate_ids) < size:
            continue
        import itertools
        for subset in itertools.combinations(candidate_ids, size):
            added = [shape(features[cid]["geometry"]) for cid in subset]
            proposed = unary_union([old_target] + added)
            actual_gain = proposed.difference(old_target)
            expected_gain = unary_union([geom.difference(old_target) for geom in added])
            old_loss = old_target.difference(proposed)
            gain_residual = actual_gain.symmetric_difference(expected_gain)
            sequential = old_target
            for geom in added:
                sequential = sequential.union(geom)
            batch_diagnostics.append({"target_source_id": "gb:USA:ADM2:" + target_id,
                "candidate_ids": list(subset),
                "old_target": describe(old_target),
                "proposed_union": describe(proposed),
                "old_target_relation_to_union": old_target.relate(proposed),
                "old_target_covers_union": bool(old_target.covers(proposed)),
                "union_covers_old_target": bool(proposed.covers(old_target)),
                "old_target_difference_union": describe(old_loss),
                "candidate_retained": {cid: bool(proposed.covers(geom)) for cid, geom in zip(subset, added)},
                "actual_gain": describe(actual_gain),
                "expected_gain": describe(expected_gain),
                "gain_equals_expected": bool(actual_gain.equals(expected_gain)),
                "gain_symmetric_difference": describe(gain_residual),
                "sequential_union": describe(sequential),
                "sequential_covers_old_target": bool(sequential.covers(old_target)),
                "sequential_old_target_relation": old_target.relate(sequential)})
result = {
    "status": "diagnostic-only-no-qualification",
    "single_candidate_trials": single_candidate_trials,
    "candidate_batch_diagnostics": batch_diagnostics,
    "source_pins": [{"path": path, "role": role,
        "bytes": next(row["bytes"] for row in PHASE["inputs"] if row["path"] == path and row["role"] == role),
        "sha256": next(row["sha256"] for row in PHASE["inputs"] if row["path"] == path and row["role"] == role)}
        for path, role in INPUTS.items()],
    "runtime": {"shapely": shapely.__version__, "geos": shapely.geos_version_string},
    "native_original_predicate_pin_comparison": native_hash_rows,
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
