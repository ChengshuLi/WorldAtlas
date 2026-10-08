#!/usr/bin/env python3
"""Measure the exact 13 Alaska candidates against pinned administrative/native inputs."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import pathlib
import struct
import subprocess
import sys

from pyproj import CRS, Transformer
from shapely import is_valid_reason
from shapely.geometry import Polygon, shape, mapping
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree

ROOT = pathlib.Path(__file__).resolve().parents[3]
CAMPAIGN = ROOT / "research/geography/alaska-thirteen-geometry-measurement-20261008"
FIT = ROOT / "research/geography/alaska-thirteen-source-fitness-20261008/sources"
NATIVE = ROOT / "coordination/engineering/gshhg-native-member-custody-20261007/results"
IDS = [
    "physical-component:073d9a81648d56c1b63a4e495fbd0140c17659bedb5c9b211739642b438ee488",
    "physical-component:4d36c81ff35079341e6ec0d5a207ba3844e26f5d55c30c7205924dfd33b8dc18",
    "physical-component:5874689a46f7945e9dcc67cc3b0321d4e534572e4b4bd8a85f4a07c5005d1922",
    "physical-component:66e4f6c15eb17f53815844efc04e7cae9faf9118de313541d3a4be2ff1fcf0a2",
    "physical-component:70174bffffdbb4a421344d6c10d80b760972f9c5452daf0d7c26408fdf18bb53",
    "physical-component:777e7bc99320bf155684f99b0903c336f9a07862de4a7fa0ac8cde990d7d6ee5",
    "physical-component:8435dc6d973751bab55c4eff12c872ba331c3e005254ceb21b76933a8cc6207a",
    "physical-component:8fb2ed9360ba13f6b19f8bb6ee9a16099039d8b59c9f51eab0a442249f428e7d",
    "physical-component:9f130f023a510be6e4b2f9075ed99cf75c4f88053e93189dda3f0bd51080f14a",
    "physical-component:cffd5f514585665c2d76279e036889887df24efa229a67f88052aef0d8ee4a83",
    "physical-component:d688afd3657ded3f0cf85a95956f2d42726f44923b168499320d681080539fb1",
    "physical-component:e76fd386dc9a23375537ede302f7f380a217fd4bbccd9536f856e8b4253a5ab8",
    "physical-component:ef7383db4412abe64b7e8d009679cffa4a3174d6da100c6de1fc37272aadeca9",
]
TARGETS = {
    "52423323B46246640861022": "Aleutians East",
    "52423323B16539688175930": "Valdez-Cordova",
    "52423323B80008995120080": "Kodiak Island",
    "52423323B64721050065013": "Kenai Peninsula",
    "52423323B57268278189593": "Kusilvak",
    "52423323B82121365400499": "Hoonah-Angoon",
    "52423323B55198873775030": "Prince of Wales-Hyder",
}
NATIVE_IDS = [2, 104, 216, 1083, 1480, 2342, 2446, 3041, 3498, 4854, 6395]
EXPECTED_NEIGHBORS = [
    "gb:USA:ADM2:52423323B13000193718373", "gb:USA:ADM2:52423323B16539688175930",
    "gb:USA:ADM2:52423323B20306178640915", "gb:USA:ADM2:52423323B44097334117837",
    "gb:USA:ADM2:52423323B46246640861022", "gb:USA:ADM2:52423323B55198873775030",
    "gb:USA:ADM2:52423323B57268278189593", "gb:USA:ADM2:52423323B58185108898",
    "gb:USA:ADM2:52423323B59860466047217", "gb:USA:ADM2:52423323B64721050065013",
    "gb:USA:ADM2:52423323B69219161179389", "gb:USA:ADM2:52423323B73641468228234",
    "gb:USA:ADM2:52423323B76828844452953", "gb:USA:ADM2:52423323B80008995120080",
    "gb:USA:ADM2:52423323B81884314913913", "gb:USA:ADM2:52423323B82121365400499",
    "gb:USA:ADM2:52423323B88813000222889",
]
HEADER = struct.Struct(">11i")
BASELINE = None
VINTAGE = None
IMMUTABLE_BASELINE_COMMIT = None


def canonical(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_json(path: pathlib.Path):
    return json.loads(read_bytes(path).decode("utf-8"))


def read_bytes(path: pathlib.Path) -> bytes:
    if BASELINE is not None:
        return BASELINE.materialized_bytes(path.relative_to(ROOT).as_posix())
    return path.read_bytes()


def number(value):
    if value is None:
        return None
    return round(float(value), 9)


def safe_area(geometry, projected=False):
    if geometry is None or not geometry.is_valid:
        return None
    try:
        if projected:
            pg = transform(PROJECT, geometry)
            if not pg.is_valid:
                return None
            return number(pg.area)
        return number(geometry.area)
    except Exception:
        return None


def exact_area(geometry, projected=False):
    if geometry is None or not geometry.is_valid:
        return None
    try:
        measured = transform(PROJECT, geometry) if projected else geometry
        if not measured.is_valid:
            return None
        return measured.area
    except Exception:
        return None


def geometry_state(geometry):
    return {"valid": bool(geometry.is_valid), "reason": "Valid Geometry" if geometry.is_valid else is_valid_reason(geometry),
            "type": geometry.geom_type, "empty": bool(geometry.is_empty)}


def safe_pair(a, b):
    if a is None or b is None or not a.is_valid or not b.is_valid:
        return None
    try:
        intersection = a.intersection(b)
        a_only = a.difference(b)
        b_only = b.difference(a)
        symmetric = a.symmetric_difference(b)
        projected_intersection = transform(PROJECT, intersection)
        projected_a_only = transform(PROJECT, a_only)
        projected_b_only = transform(PROJECT, b_only)
        projected_symmetric = transform(PROJECT, symmetric)
        if not all(x.is_valid for x in (intersection, a_only, b_only, symmetric,
                                        projected_intersection, projected_a_only,
                                        projected_b_only, projected_symmetric)):
            return {"status": "invalid-overlay-result", "intersection_area_raw_square_degrees": None,
                    "intersection_area_projected_m2": None, "a_uncovered_area_raw_square_degrees": None,
                    "a_uncovered_area_projected_m2": None, "b_uncovered_area_raw_square_degrees": None,
                    "b_uncovered_area_projected_m2": None, "symmetric_difference_area_projected_m2": None,
                    "a_covers_b": None, "b_covers_a": None}
        return {"status": "measured",
                "intersection_area_raw_square_degrees": number(intersection.area),
                "intersection_area_projected_m2": number(projected_intersection.area),
                "a_uncovered_area_raw_square_degrees": number(a_only.area),
                "a_uncovered_area_projected_m2": number(projected_a_only.area),
                "b_uncovered_area_raw_square_degrees": number(b_only.area),
                "b_uncovered_area_projected_m2": number(projected_b_only.area),
                "symmetric_difference_area_projected_m2": number(projected_symmetric.area),
                "a_covers_b": bool(a.covers(b)), "b_covers_a": bool(b.covers(a)),
                "topologically_equal": bool(a.equals(b)),
                "intersection_geometry_type": intersection.geom_type}
    except Exception as error:
        return {"status": "overlay-error", "error": str(error)[:240],
                "intersection_area_raw_square_degrees": None,
                "intersection_area_projected_m2": None, "a_uncovered_area_raw_square_degrees": None,
                "a_uncovered_area_projected_m2": None, "b_uncovered_area_raw_square_degrees": None,
                "b_uncovered_area_projected_m2": None, "symmetric_difference_area_projected_m2": None,
                "a_covers_b": None, "b_covers_a": None}


def intersections(candidate, other):
    if not candidate.is_valid or not other.is_valid:
        return {"status": "invalid-input", "intersects": None,
                "positive_area_overlap": None, "boundary_contact_only": None,
                "intersection_area_raw_square_degrees": None,
                "intersection_area_projected_m2": None,
                "candidate_uncovered_area_projected_m2": None,
                "candidate_covered_exactly": None}
    try:
        geom = candidate.intersection(other)
        candidate_only = candidate.difference(other)
        projected = transform(PROJECT, geom)
        projected_only = transform(PROJECT, candidate_only)
        if not geom.is_valid or not candidate_only.is_valid or not projected.is_valid or not projected_only.is_valid:
            return {"status": "invalid-overlay-result", "intersects": None,
                    "positive_area_overlap": None, "boundary_contact_only": None,
                    "intersection_area_raw_square_degrees": None,
                    "intersection_area_projected_m2": None,
                    "candidate_uncovered_area_projected_m2": None,
                    "candidate_covered_exactly": None}
        intersects = bool(candidate.intersects(other))
        area = projected.area
        return {"status": "measured", "intersects": intersects,
                "positive_area_overlap": bool(geom.area > 0),
                "boundary_contact_only": bool(intersects and geom.area == 0),
                "intersection_geometry_type": geom.geom_type,
                "intersection_area_raw_square_degrees": number(geom.area),
                "intersection_area_raw_square_degrees_exact": geom.area,
                "intersection_area_projected_m2": number(area),
                "intersection_area_projected_m2_exact": area,
                "candidate_uncovered_area_projected_m2": number(projected_only.area),
                "candidate_uncovered_area_projected_m2_exact": projected_only.area,
                "candidate_covered_exactly": bool(other.covers(candidate)),
                "candidate_area_projected_m2": safe_area(candidate, True),
                "candidate_coverage_ratio": (1.0 if other.covers(candidate) else
                    (number(area / transform(PROJECT, candidate).area) if transform(PROJECT, candidate).area else None))}
    except Exception as error:
        return {"status": "overlay-error", "error": str(error)[:240], "intersects": None,
                "positive_area_overlap": None, "boundary_contact_only": None,
                "intersection_area_raw_square_degrees": None,
                "intersection_area_projected_m2": None,
                "candidate_uncovered_area_projected_m2": None,
                "candidate_covered_exactly": None}


def load_native(record_receipt_path: pathlib.Path):
    receipt = read_json(record_receipt_path)
    if receipt.get("status") != "bytes-verified" or receipt.get("whole_native_member", {}).get("records_authenticated") != 188612:
        raise ValueError("selected native input is not backed by full-member authentication")
    descriptor = receipt["selected_output"]
    path = ROOT / descriptor["path"]
    raw = read_bytes(path)
    if len(raw) != descriptor["bytes"] or sha(raw) != descriptor["sha256"]:
        raise ValueError("selected native whole-file output differs from custody receipt")
    geometries, metadata = {}, {}
    for row in descriptor["records"]:
        begin = row["output_offset"]
        end = begin + row["bytes"]
        record = raw[begin:end]
        if len(record) != row["bytes"] or sha(record) != row["sha256"]:
            raise ValueError(f"selected native record digest differs: {row['id']}")
        header = HEADER.unpack(record[:44])
        if list(header) != row["header_int32"]:
            raise ValueError(f"selected native header identity differs: {row['id']}")
        coordinate_bytes = record[44:]
        coordinates = list(struct.iter_unpack(">2i", coordinate_bytes))
        if len(coordinates) != row["header_int32"][1]:
            raise ValueError(f"selected native coordinate count differs: {row['id']}")
        original_points = [(x * 1e-6, y * 1e-6) for x, y in coordinates]
        points = [(lon - 360.0 if lon > 180.0 else lon, lat) for lon, lat in original_points]
        restored_points = [(lon + 360.0 if lon < 0.0 else lon, lat) for lon, lat in points]
        if restored_points != original_points:
            raise ValueError(f"native longitude branch mapping is not exactly reversible: {row['id']}")
        if points[0] != points[-1]:
            raise ValueError(f"selected native ring is not byte-closed: {row['id']}")
        jumps = [abs(points[i][0] - points[i - 1][0]) for i in range(1, len(points))]
        geom = Polygon(points)
        geometries[row["id"]] = geom
        metadata[row["id"]] = {**row, "original_point_count": len(original_points),
                                "coordinate_int32_bytes_sha256": sha(coordinate_bytes),
                                "original_decoder_convention": "signed int32 longitude,latitude multiplied by 1e-6",
                                "original_pointset_sha256": sha(canonical(original_points)),
                                "normalized_pointset_sha256": sha(canonical(points)),
                                "restored_pointset_sha256": sha(canonical(restored_points)),
                                "longitude_branch_transform": "x>180: x-360; inverse x<0: x+360; y unchanged",
                                "longitude_branch_exact_inverse": restored_points == original_points,
                                "normalized_longitude_max_step_degrees": number(max(jumps, default=0)),
                                "longitude_branch_discontinuity": bool(max(jumps, default=0) > 180)}
    if sorted(geometries) != NATIVE_IDS:
        raise ValueError("selected native source roster differs from exact 11 IDs")
    return geometries, metadata, receipt, path


def relation_kind(geometry):
    if geometry.is_empty:
        return "disjoint"
    if geometry.area > 0:
        return "positive-area-overlap"
    if "Line" in geometry.geom_type or geometry.geom_type in ("MultiLineString", "LinearRing"):
        return "zero-area-line-contact"
    if "Point" in geometry.geom_type:
        return "zero-area-point-contact"
    return "zero-area-contact"


def introduces_positive_area_gain_overlap(gain, neighbor):
    """Exact raw-coordinate positive-area gate; deliberately has no epsilon."""
    return bool(gain.intersection(neighbor).area > 0)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    if VINTAGE is None or args.output_dir != VINTAGE.vintage:
        raise SystemExit("pre-admitted fresh NewVintage destination is required")
    phase_path = CAMPAIGN / "phase-admission.json"
    phase = read_json(phase_path)
    phase_raw = read_bytes(phase_path)
    if phase.get("status") != "PASS" or phase.get("scientific_operations_invoked") is not False:
        raise SystemExit("complete phase admission missing or failed")
    for descriptor in phase.get("inputs", []) + phase.get("project_code", []):
        path = ROOT / descriptor["path"]
        if path.is_symlink() or not path.is_file():
            raise SystemExit(f"phase admission input is missing or not an ordinary file: {descriptor['path']}")
        raw = read_bytes(path)
        if len(raw) != descriptor["bytes"] or sha(raw) != descriptor["sha256"]:
            raise SystemExit(f"phase admission is stale for {descriptor['path']}; rerun admission")
    node = pathlib.Path("/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node")
    workspace_check = subprocess.run([str(node), "scripts/local-workspace.mjs", "check"],
                                      cwd=ROOT, capture_output=True, text=True)
    if workspace_check.returncode != 0:
        raise SystemExit("managed-workspace storage/reservation guard failed; no geometry run launched")

    full_path = CAMPAIGN / "sources/geoboundaries-USA-ADM2-full-9469f09.geojson"
    simple_path = FIT / "selected-2018-usa-adm2-features.geojson"
    atlas_path = FIT / "native-atlas-target-features.geojson"
    neighbor_path = CAMPAIGN / "sources/atlas-neighbors/features.geojson"
    neighbor_receipt_path = CAMPAIGN / "sources/atlas-neighbors/receipt.json"
    original_contacts_path = CAMPAIGN / "sources/original-fragment-contacts/features.geojson"
    original_contacts_receipt_path = CAMPAIGN / "sources/original-fragment-contacts/receipt.json"
    contact_authority_path = CAMPAIGN / "sources/contact-authority/contact-authority-receipt.json"
    detector_vintage_path = CAMPAIGN / "sources/contact-authority/detector-vintage-supplement.json"
    candidate_path = FIT / "candidate-components.geojson"
    screen_path = FIT / "candidate-source-screen.json"
    physical_path = FIT / "physical-query-rows.jsonl"
    family_path = FIT / "complete-native-family-record.jsonl"
    parent_path = CAMPAIGN / "sources/alaska-adm1-parent/feature.geojson"
    parent_receipt_path = CAMPAIGN / "sources/alaska-adm1-parent/receipt.json"
    native_receipt_path = CAMPAIGN / "sources/native-selected/receipt.json"
    native_query_path = FIT / "gshhg-native-query-records.json"
    input_paths = [full_path, simple_path, atlas_path, neighbor_path, neighbor_receipt_path,
                   original_contacts_path, original_contacts_receipt_path, contact_authority_path,
                   detector_vintage_path, CAMPAIGN / "sources/native-selected/records.bin", candidate_path, screen_path,
                   physical_path, family_path, parent_path, parent_receipt_path, native_receipt_path,
                   phase_path, native_query_path, FIT / "usa-adm2-source-metadata.json",
                   FIT / "usa-adm2-attribution.json", FIT / "geoBoundaries-derivative-use-terms.txt"]
    input_manifest = []
    for path in input_paths:
        raw = read_bytes(path)
        input_manifest.append({"path": path.relative_to(ROOT).as_posix(), "bytes": len(raw), "sha256": sha(raw)})
    inp = {row["path"]: row for row in input_manifest}
    if len(inp) != len(input_manifest):
        raise ValueError("duplicate input path")

    full_fc = read_json(full_path)
    simple_fc = read_json(simple_path)
    atlas_fc = read_json(atlas_path)
    neighbor_fc = read_json(neighbor_path)
    neighbor_receipt = read_json(neighbor_receipt_path)
    original_contacts_fc = read_json(original_contacts_path)
    original_contacts_receipt = read_json(original_contacts_receipt_path)
    contact_authority = read_json(contact_authority_path)
    detector_vintage = read_json(detector_vintage_path)
    candidate_fc = read_json(candidate_path)
    screen = read_json(screen_path)
    physical_rows = [json.loads(line) for line in read_bytes(physical_path).decode("utf-8").splitlines() if line]
    family_records = [json.loads(line) for line in read_bytes(family_path).decode("utf-8").splitlines() if line]
    parent_feature = read_json(parent_path)
    parent_receipt = read_json(parent_receipt_path)
    native_geometries, native_meta, native_receipt, native_path = load_native(native_receipt_path)
    native_query = read_json(native_query_path)
    native_query_by_id = {row["id"]: row for row in native_query.get("records", [])}
    if set(native_query_by_id) != set(NATIVE_IDS):
        raise ValueError("original native-query metadata does not match exact 11-record roster")
    for native_id in NATIVE_IDS:
        measured_source = native_meta[native_id]
        expected_source = native_query_by_id[native_id]
        if (measured_source["sha256"] != expected_source["record_sha256"]
                or measured_source["coordinate_int32_bytes_sha256"] != expected_source["coordinate_bytes_sha256"]
                or measured_source["header_int32"][1] != expected_source["n"]
                or measured_source["header_int32"][2] != expected_source["flag"]
                or measured_source["header_int32"][9] != expected_source["container"]):
            raise ValueError(f"selected native record bytes/header differ from original query metadata: {native_id}")

    if sorted(feature["id"] for feature in candidate_fc["features"]) != sorted(IDS):
        raise ValueError("candidate collection does not match exact 13 assigned identities")
    if len(screen.get("findings", [])) != 13 or len(physical_rows) != 13 or len(family_records) != 1:
        raise ValueError("candidate/physical/family inventory count differs")
    family = family_records[0]
    edge_neighbor_ids = screen.get("family_context", {}).get("edge_neighbor_ids", [])
    if family.get("component_count") != 995 or len(family.get("complete_component_ids", [])) != 995 or len(edge_neighbor_ids) != 17:
        raise ValueError("full 995-member family or 17 neighbor context differs")
    if edge_neighbor_ids != EXPECTED_NEIGHBORS or family.get("original_fine_family", {}).get("contact_ids") != EXPECTED_NEIGHBORS:
        raise ValueError("neighbor context IDs differ from issue input contract")
    if (neighbor_receipt.get("status") != "source-bytes-verified"
            or neighbor_receipt.get("baseline_commit") != "6c0ea95b7a8214ac1548161368bd952af136b5c2"
            or neighbor_receipt.get("found_source_ids") != EXPECTED_NEIGHBORS
            or len(neighbor_fc.get("features", [])) != 17
            or neighbor_receipt.get("feature_collection", {}).get("bytes") != neighbor_path.stat().st_size
            or neighbor_receipt.get("feature_collection", {}).get("sha256") != sha(read_bytes(neighbor_path))):
        raise ValueError("actual 17 Atlas neighbor feature receipt or scope differs")
    if (original_contacts_receipt.get("status") != "complete-recorded-contacts"
            or set(original_contacts_receipt.get("component_ids", [])) != set(IDS)
            or original_contacts_receipt.get("fragment_count") != 13
            or original_contacts_receipt.get("baseline_commit") != "6c0ea95b7a8214ac1548161368bd952af136b5c2"
            or len(original_contacts_fc.get("features", [])) != 13
            or original_contacts_receipt.get("output", {}).get("bytes") != original_contacts_path.stat().st_size
            or original_contacts_receipt.get("output", {}).get("sha256") != sha(read_bytes(original_contacts_path))):
        raise ValueError("exact original per-fragment contact records are incomplete or wrong vintage")
    if (contact_authority.get("Atlas_baseline_commit") != "6c0ea95b7a8214ac1548161368bd952af136b5c2"
            or contact_authority.get("all_contact_ids") != EXPECTED_NEIGHBORS
            or detector_vintage.get("original_detector_actual_baseline") != "548c5f89f00271050823076a84695bb41e1b8454"
            or detector_vintage.get("all_actual13_source_fragment_tiles_checked") != sorted({int(x["id"].split(":", 2)[1]) for x in original_contacts_fc["features"]})):
        raise ValueError("source-vintage contact authority chain differs")
    if len(native_geometries) != 11 or len(NATIVE_IDS) != 11:
        raise ValueError("all 11 selected native GSHHG records are required")

    screen_by_id = {row["component_id"]: row for row in screen["findings"]}
    candidate_by_id = {feature["id"]: feature for feature in candidate_fc["features"]}
    physical_by_id = {row["component_id"]: row for row in physical_rows}
    if set(screen_by_id) != set(IDS) or set(physical_by_id) != set(IDS):
        raise ValueError("source-screen or physical relation identity join differs")
    feature_index = {}
    for feature in full_fc.get("features", []):
        shape_id = feature.get("properties", {}).get("shapeID")
        if not shape_id or shape_id in feature_index:
            raise ValueError("full ADM2 source has missing/duplicate shapeID")
        feature_index[shape_id] = feature
    if len(feature_index) != 3233:
        raise ValueError("full non-simplified ADM2 source count must be 3,233")
    simple_index = {f.get("properties", {}).get("shapeID"): f for f in simple_fc.get("features", [])}
    atlas_index = {f.get("properties", {}).get("metadata", {}).get("original_id"): f for f in atlas_fc.get("features", [])}
    neighbor_index = {f.get("properties", {}).get("id"): f for f in neighbor_fc.get("features", [])}
    original_contact_index = {f.get("properties", {}).get("component_id"): f for f in original_contacts_fc.get("features", [])}
    if set(neighbor_index) != set(EXPECTED_NEIGHBORS) or len(neighbor_index) != 17:
        raise ValueError("actual 17 Atlas neighbor feature IDs differ")
    if set(original_contact_index) != set(IDS) or len(original_contact_index) != 13:
        raise ValueError("per-candidate complete original contact source join differs")
    neighbor_receipt_rows = {row["source_id"]: row for row in neighbor_receipt.get("features", [])}
    if set(neighbor_receipt_rows) != set(EXPECTED_NEIGHBORS):
        raise ValueError("17-neighbor receipt feature geometry hashes are incomplete")
    for source_id, feature in neighbor_index.items():
        if sha(canonical(feature["geometry"])) != neighbor_receipt_rows[source_id].get("geometry_sha256"):
            raise ValueError(f"pinned Atlas neighbor feature geometry hash differs: {source_id}")
    contact_receipt_rows = {row["id"]: row for row in original_contacts_receipt.get("fragments", [])}
    if set(contact_receipt_rows) != {feature.get("id") for feature in original_contacts_fc["features"]}:
        raise ValueError("per-fragment original contact receipt rows differ from retained records")
    if set(simple_index) != set(TARGETS) or set(atlas_index) != set(TARGETS):
        raise ValueError("seven simplified or Atlas county target identities differ")
    if len(atlas_index) != 7 or len(simple_index) != 7:
        raise ValueError("expected exact seven current Atlas and simplified county geometries")
    parent_props = parent_feature.get("properties", {})
    if (parent_props.get("shapeID"), parent_props.get("shapeName"), parent_props.get("shapeISO")) != (
            "66186276B62688952876525", "Alaska", "US-AK"):
        raise ValueError("pinned Alaska ADM1 parent identity differs")
    if parent_receipt.get("selected_parent", {}).get("sha256") != inp[parent_path.relative_to(ROOT).as_posix()]["sha256"]:
        raise ValueError("parent geometry bytes differ from verified source capture")

    full_geoms = {sid: shape(feature["geometry"]) for sid, feature in feature_index.items()}
    simple_geoms = {sid: shape(simple_index[sid]["geometry"]) for sid in TARGETS}
    atlas_geoms = {sid: shape(atlas_index[sid]["geometry"]) for sid in TARGETS}
    neighbor_geoms = {sid: shape(neighbor_index[sid]["geometry"]) for sid in EXPECTED_NEIGHBORS}
    parent_geom = shape(parent_feature["geometry"])
    candidates = {cid: shape(candidate_by_id[cid]["geometry"]) for cid in IDS}
    if any(not g.is_valid for g in (parent_geom, *full_geoms.values(), *simple_geoms.values(),
                                    *atlas_geoms.values(), *neighbor_geoms.values(), *candidates.values())):
        # Invalid source geometries stay visible. Their dependent overlays will
        # report invalid-input and cannot be promoted through any repair.
        pass
    full_tree_geoms = [full_geoms[sid] for sid in feature_index]
    full_tree_ids = list(feature_index)
    admin_tree = STRtree(full_tree_geoms)

    transformer = Transformer.from_crs(CRS.from_epsg(4326), CRS.from_epsg(3338), always_xy=True)
    global PROJECT
    PROJECT = transformer.transform
    proj_description = {"source_crs": "EPSG:4326", "target_crs": "EPSG:3338",
                        "always_xy": True, "source_axis_order": "longitude,latitude",
                        "target_linear_unit": "metre", "transformer_description": transformer.description,
                        "transformer_definition": transformer.definition,
                        "reported_accuracy_m": transformer.accuracy}

    cases, native_pairs, admin_pairs = [], [], []
    proposal_features = []
    finding_relation_count = 0
    screen_native_ids = set()
    case_geometry_by_id = {}
    for cid in IDS:
        candidate = candidates[cid]
        finding = screen_by_id[cid]
        physical = physical_by_id[cid]
        target_id = finding["admin_context"]["atlas_target_original_id"]
        if target_id not in TARGETS:
            raise ValueError(f"assigned candidate has unexpected county target: {cid}")
        full_feature = feature_index[target_id]
        simplified_feature = simple_index[target_id]
        atlas_feature = atlas_index[target_id]
        if full_feature["properties"].get("shapeName") != TARGETS[target_id] or simplified_feature["properties"].get("shapeName") != TARGETS[target_id]:
            raise ValueError(f"county target name/source join differs: {cid}")
        if atlas_feature.get("properties", {}).get("id") != finding["admin_context"]["atlas_target_id"]:
            raise ValueError(f"Atlas county target ID join differs: {cid}")
        if sha(canonical(atlas_feature["geometry"])) != sha(canonical(neighbor_index["gb:USA:ADM2:" + target_id]["geometry"])):
            raise ValueError(f"selected Atlas target does not equal its exact pinned neighbor feature: {cid}")
        if sha(canonical(candidate_by_id[cid]["geometry"])) != finding["current_geometry_sha256"]:
            raise ValueError(f"candidate source geometry hash differs: {cid}")
        original_contact = original_contact_index[cid]
        if (original_contact.get("id") not in {row.get("id") for row in finding.get("fragment_bindings", [])}
                and original_contact.get("id") not in {row.get("id") for row in candidate_by_id[cid]["properties"].get("fragment_bindings", [])}):
            raise ValueError(f"original detector fragment identity does not bind to this whole component: {cid}")
        if sha(canonical(original_contact["geometry"])) != sha(canonical(candidate_by_id[cid]["geometry"])):
            raise ValueError(f"original detector fragment geometry differs from current candidate component: {cid}")
        original_contact_receipt = contact_receipt_rows[original_contact["id"]]
        binding = candidate_by_id[cid]["properties"]["fragment_bindings"][0]
        if (binding["id"] != original_contact["id"]
                or binding["feature_sha256"] != original_contact_receipt.get("original_feature_sha256")
                or original_contact.get("properties", {}).get("original_feature_sha256") != binding["feature_sha256"]
                or original_contact_receipt.get("component_id") != cid):
            raise ValueError(f"original whole-fragment feature identity/hash does not bind to the assigned component: {cid}")
        detector_contact_rows = original_contact.get("properties", {}).get("original_detector_properties", {}).get("exact_location_contacts")
        if not isinstance(detector_contact_rows, list):
            raise ValueError(f"complete original detector contact list missing: {cid}")
        if any(row.get("id") not in EXPECTED_NEIGHBORS for row in detector_contact_rows):
            raise ValueError(f"original detector contact points outside the recorded 17-neighbor family: {cid}")
        if sha(canonical(full_feature["geometry"])) == "":
            raise ValueError("unreachable canonical hash failure")

        full_geom, simple_geom, atlas_geom = full_geoms[target_id], simple_geoms[target_id], atlas_geoms[target_id]
        case_geometries = {"candidate": candidate, "full_county_source": full_geom,
                           "simplified_county_source": simple_geom, "atlas_target": atlas_geom,
                           "alaska_adm1_parent": parent_geom}
        states = {key: geometry_state(geometry) for key, geometry in case_geometries.items()}
        county_comparisons = {
            "full_vs_simplified": safe_pair(full_geom, simple_geom),
            "full_vs_atlas": safe_pair(full_geom, atlas_geom),
            "simplified_vs_atlas": safe_pair(simple_geom, atlas_geom),
        }
        target_comparisons = {
            "candidate_vs_full_county": intersections(candidate, full_geom),
            "candidate_vs_simplified_county": intersections(candidate, simple_geom),
            "candidate_vs_atlas_target": intersections(candidate, atlas_geom),
            "candidate_vs_alaska_parent": intersections(candidate, parent_geom),
        }
        variant = county_comparisons["full_vs_simplified"]
        full_candidate = target_comparisons["candidate_vs_full_county"]
        simple_candidate = target_comparisons["candidate_vs_simplified_county"]
        variant_same_for_candidate = bool(
            full_candidate.get("status") == simple_candidate.get("status") == "measured" and
            full_candidate.get("candidate_covered_exactly") == simple_candidate.get("candidate_covered_exactly") and
            full_candidate.get("positive_area_overlap") == simple_candidate.get("positive_area_overlap") and
            full_candidate.get("intersection_area_projected_m2_exact") == simple_candidate.get("intersection_area_projected_m2_exact") and
            full_candidate.get("candidate_uncovered_area_projected_m2_exact") == simple_candidate.get("candidate_uncovered_area_projected_m2_exact") and
            candidate.intersection(full_geom).equals(candidate.intersection(simple_geom)) and
            candidate.difference(full_geom).equals(candidate.difference(simple_geom)))

        linked_native = sorted({row["id"] for row in finding.get("gshhg_covering_records", [])})
        expected_relations = physical["query_relations"]
        if len(expected_relations) > 25:
            raise ValueError("unexpected excess physical query relations")
        finding_relation_count += len(expected_relations)
        source_relations = {row["source_id"]: row for row in finding["physical_query"]["relations"]}
        if set(source_relations) != {row["source_id"] for row in expected_relations}:
            raise ValueError(f"source-screen and physical-query relation joins differ: {cid}")
        screen_native_ids.update(source_relations)
        case_native_rows = []
        for native_id in NATIVE_IDS:
            native = native_geometries[native_id]
            measured = intersections(candidate, native)
            source_relation = source_relations.get(native_id)
            if source_relation is not None:
                relation_match = (measured.get("status") == "measured" and
                    source_relation["candidate_covered"] == measured["candidate_covered_exactly"] and
                    source_relation["candidate_covers_source"] == bool(candidate.covers(native)) and
                    source_relation["disjoint"] == (not measured["intersects"]) and
                    source_relation["source_record_sha256"] == native_meta[native_id]["sha256"] and
                    source_relation["source_level"] == (native_meta[native_id]["header_int32"][2] & 0xff) and
                    source_relation["source_pointset_sha256"] == native_meta[native_id]["original_pointset_sha256"])
            else:
                relation_match = None
            item = {"component_id": cid, "target_source_id": target_id, "gshhg_native_id": native_id,
                    "gshhg_level": native_meta[native_id]["level"],
                    "record_sha256": native_meta[native_id]["sha256"],
                    "geometry_validity": geometry_state(native),
                    "measured": measured,
                    "original_query_relation": ({"candidate_covered": source_relation["candidate_covered"],
                         "candidate_covers_source": source_relation["candidate_covers_source"],
                         "disjoint": source_relation["disjoint"], "witness": source_relation["witness"],
                         "source_level": source_relation["source_level"],
                         "source_record_sha256": source_relation["source_record_sha256"]}
                         if source_relation is not None else None),
                    "original_predicates_match": relation_match}
            native_pairs.append(item)
            if source_relation is not None:
                case_native_rows.append(item)
        if not linked_native or set(linked_native) - set(NATIVE_IDS):
            raise ValueError(f"linked GSHHG source roster invalid: {cid}")
        linked_tests = [row for row in case_native_rows if row["gshhg_native_id"] in linked_native]
        linked_native_covers = bool(linked_tests) and all(
            row["measured"].get("status") == "measured" and row["measured"].get("candidate_covered_exactly")
            and row["original_predicates_match"] is True for row in linked_tests)

        candidate_contacts = []
        if candidate.is_valid:
            for raw_idx in admin_tree.query(candidate):
                idx = int(raw_idx)
                neighbor_id = full_tree_ids[idx]
                neighbor = full_tree_geoms[idx]
                if not neighbor.is_valid:
                    candidate_contacts.append({"shape_id": neighbor_id, "shape_name": feature_index[neighbor_id]["properties"].get("shapeName"),
                                               "status": "invalid-source-geometry", "contact_kind": None,
                                               "intersection_area_projected_m2": None})
                    continue
                try:
                    if not candidate.intersects(neighbor):
                        continue
                    inter = candidate.intersection(neighbor)
                    projected_inter = transform(PROJECT, inter)
                    candidate_contacts.append({"shape_id": neighbor_id,
                        "source_id": "gb:USA:ADM2:" + neighbor_id,
                        "shape_name": feature_index[neighbor_id]["properties"].get("shapeName"),
                        "status": "measured", "contact_kind": relation_kind(inter),
                        "intersection_area_raw_square_degrees": number(inter.area),
                        "intersection_area_projected_m2": number(projected_inter.area),
                        "intersection_geometry_type": inter.geom_type})
                except Exception as error:
                    candidate_contacts.append({"shape_id": neighbor_id,
                        "source_id": "gb:USA:ADM2:" + neighbor_id,
                        "shape_name": feature_index[neighbor_id]["properties"].get("shapeName"),
                        "status": "overlay-error", "contact_kind": None,
                        "error": str(error)[:240]})
        candidate_contacts.sort(key=lambda row: (row.get("shape_id", ""), row.get("contact_kind", "")))
        admin_pairs.extend({"component_id": cid, **row} for row in candidate_contacts)
        known_neighbor_contacts = []
        for neighbor_source_id in EXPECTED_NEIGHBORS:
            neighbor_shape_id = neighbor_source_id.rsplit(":", 1)[1]
            if neighbor_source_id not in neighbor_geoms:
                raise ValueError(f"one of the 17 pinned actual Atlas neighbor IDs is absent: {neighbor_source_id}")
            relation = intersections(candidate, neighbor_geoms[neighbor_source_id])
            known_neighbor_contacts.append({"neighbor_source_id": neighbor_source_id,
                "neighbor_shape_id": neighbor_shape_id,
                "neighbor_name": neighbor_index[neighbor_source_id]["properties"].get("name"),
                "relation": relation})
        original_contact_ids = sorted({row["id"] for row in detector_contact_rows})
        measured_atlas_contact_ids = sorted(row["neighbor_source_id"] for row in known_neighbor_contacts
            if row["relation"].get("status") == "measured" and row["relation"].get("intersects") is True)
        detector_contacts_match = original_contact_ids == measured_atlas_contact_ids

        source_parent_support = {
            name: bool(row.get("status") == "measured" and row.get("candidate_covered_exactly") is True and
                       row.get("candidate_uncovered_area_projected_m2") == 0.0)
            for name, row in target_comparisons.items()
            if name in ("candidate_vs_full_county", "candidate_vs_simplified_county", "candidate_vs_alaska_parent")
        }
        original_relations_agree = all(row["original_predicates_match"] is True for row in case_native_rows)
        source_support_pass = bool(states["candidate"]["valid"] and states["full_county_source"]["valid"] and
            states["simplified_county_source"]["valid"] and states["atlas_target"]["valid"] and
            states["alaska_adm1_parent"]["valid"] and variant_same_for_candidate and
            all(source_parent_support.values()) and linked_native_covers and original_relations_agree and detector_contacts_match)
        case_geometry_by_id[cid] = {"candidate": candidate, "target_id": target_id, "atlas_target": atlas_geom,
            "source_support_pass": source_support_pass, "parent_support_pass": source_parent_support["candidate_vs_alaska_parent"],
            "old_target_positive_overlap": target_comparisons["candidate_vs_atlas_target"].get("positive_area_overlap") is True}
        decision = "measured-awaiting-collective-union-and-neighbor-checks"
        cases.append({
            "component_id": cid,
            "candidate_geometry_sha256": finding["current_geometry_sha256"],
            "county_target": {"shape_id": target_id, "name": TARGETS[target_id],
                "atlas_target_id": finding["admin_context"]["atlas_target_id"],
                "source_role": "Counties", "administrative_level": "ADM2",
                "represented_year_claim": "2018"},
            "linked_gshhg_native_ids": linked_native,
            "original_physical_status": physical["status"],
            "original_physical_authority": physical["physical_authority"],
            "geometry_validity": states,
            "areas": {"candidate_raw_square_degrees": safe_area(candidate),
                "candidate_projected_m2_epsg_3338": safe_area(candidate, True),
                "candidate_raw_square_degrees_exact": exact_area(candidate),
                "candidate_projected_m2_epsg_3338_exact": exact_area(candidate, True),
                "full_county_source_raw_square_degrees": safe_area(full_geom),
                "full_county_source_projected_m2_epsg_3338": safe_area(full_geom, True),
                "full_county_source_raw_square_degrees_exact": exact_area(full_geom),
                "full_county_source_projected_m2_epsg_3338_exact": exact_area(full_geom, True),
                "simplified_county_source_raw_square_degrees": safe_area(simple_geom),
                "simplified_county_source_projected_m2_epsg_3338": safe_area(simple_geom, True),
                "simplified_county_source_raw_square_degrees_exact": exact_area(simple_geom),
                "simplified_county_source_projected_m2_epsg_3338_exact": exact_area(simple_geom, True),
                "atlas_target_raw_square_degrees": safe_area(atlas_geom),
                "atlas_target_projected_m2_epsg_3338": safe_area(atlas_geom, True),
                "atlas_target_raw_square_degrees_exact": exact_area(atlas_geom),
                "atlas_target_projected_m2_epsg_3338_exact": exact_area(atlas_geom, True)},
            "candidate_to_target_intersections_and_uncovered": target_comparisons,
            "source_to_target_variant_differences": county_comparisons,
            "source_variants_same_for_this_candidate": variant_same_for_candidate,
            "candidate_support_requirements": source_parent_support,
            "pre_union_candidate_vs_atlas_diagnostic_only": target_comparisons["candidate_vs_atlas_target"],
            "source_parent_coverage": target_comparisons["candidate_vs_alaska_parent"],
            "native_land_relations": case_native_rows,
            "native_linked_support_covers_candidate": linked_native_covers,
            "original_25_relation_predicates_match": original_relations_agree,
            "administrative_contacts_all_3233_source_features": candidate_contacts,
            "administrative_contacts_17_declared_neighbors": known_neighbor_contacts,
            "original_detector_contact_source_ids": original_contact_ids,
            "measured_actual_atlas_intersecting_neighbor_ids": measured_atlas_contact_ids,
            "original_contacts_match_all_17_actual_atlas_features": detector_contacts_match,
            "source_predicate_support_pass": source_support_pass,
            "disposition": decision,
            "remaining_limitations": [
                "The recorded 2018 County/ADM2 identity is a source binding; geometry agreement does not establish real-world boundary accuracy.",
                "GSHHG 2.3.7 level-1 geometry is coarse land support; individual observation date, shoreline registration, precision and authority are not established.",
                "No historic cause, ownership, rights, political affiliation or source authority is inferred from geometric intersections.",
            ],
        })

    if finding_relation_count != 25 or len(physical_rows) != 13:
        raise ValueError("the preserved physical relation table must contain exactly 25 relations for 13 subjects")
    if screen_native_ids - set(NATIVE_IDS):
        raise ValueError("source relation references a native GSHHG record outside the exact 11-record input set")
    physical_admission = [{"component_id": row["component_id"], "relation_count": len(row["query_relations"]),
        "source_ids": [relation["source_id"] for relation in row["query_relations"]],
        "original_row_sha256": sha(canonical(row))} for row in physical_rows]
    candidate_pair_relations = []
    for left_index, left_id in enumerate(IDS):
        for right_id in IDS[left_index + 1:]:
            left, right = candidates[left_id], candidates[right_id]
            if not left.is_valid or not right.is_valid:
                candidate_pair_relations.append({"left_component_id": left_id, "right_component_id": right_id,
                    "status": "invalid-input", "intersects": None, "positive_area_overlap": None,
                    "boundary_contact_only": None, "intersection_area_raw_square_degrees_exact": None,
                    "intersection_area_projected_m2_exact": None})
                continue
            intersection = left.intersection(right)
            projected_intersection = transform(PROJECT, intersection)
            candidate_pair_relations.append({"left_component_id": left_id, "right_component_id": right_id,
                "status": "measured", "intersects": bool(left.intersects(right)),
                "positive_area_overlap": bool(intersection.area > 0),
                "boundary_contact_only": bool(left.intersects(right) and intersection.area == 0),
                "intersection_geometry_type": intersection.geom_type,
                "intersection_area_raw_square_degrees_exact": intersection.area,
                "intersection_area_projected_m2_exact": projected_intersection.area,
                "same_county_target": case_geometry_by_id[left_id]["target_id"] == case_geometry_by_id[right_id]["target_id"]})

    # Build an exact, minimal first-batch union from two same-county cases
    # whose original candidate-to-Atlas relation has no positive-area overlap.
    # Other cases remain fully measured and visible, but are not silently
    # promoted by source metadata alone.
    batch_groups = {}
    for cid in IDS:
        item = case_geometry_by_id[cid]
        case_row = next(row for row in cases if row["component_id"] == cid)
        if item["source_support_pass"] and item["parent_support_pass"] and not item["old_target_positive_overlap"]:
            batch_groups.setdefault(item["target_id"], []).append(cid)

    batch_trials = []
    selected_batch = None
    selected_union = None
    selected_gain = None
    selected_target_id = None
    for target_id, eligible_ids in batch_groups.items():
        if len(eligible_ids) < 2:
            continue
        old_target = atlas_geoms[target_id]
        for batch_size in (2, 3):
            for candidate_subset in itertools.combinations(eligible_ids, batch_size):
                candidate_ids = list(candidate_subset)
                proposed_target = unary_union([old_target] + [case_geometry_by_id[cid]["candidate"] for cid in candidate_ids])
                expected_gain = unary_union([case_geometry_by_id[cid]["candidate"].difference(old_target) for cid in candidate_ids])
                actual_gain = proposed_target.difference(old_target)
                union_equals_expected_gain = bool(actual_gain.is_valid and expected_gain.is_valid and actual_gain.equals(expected_gain)
                                                  and actual_gain.symmetric_difference(expected_gain).is_empty)
                target_preserved = bool(proposed_target.is_valid and proposed_target.covers(old_target)
                                        and old_target.difference(proposed_target).is_empty)
                candidates_retained = {cid: bool(proposed_target.covers(case_geometry_by_id[cid]["candidate"])) for cid in candidate_ids}
                neighbor_rows = []
                new_neighbor_overlaps = []
                for neighbor_source_id in EXPECTED_NEIGHBORS:
                    if neighbor_source_id == "gb:USA:ADM2:" + target_id:
                        continue
                    neighbor = neighbor_geoms[neighbor_source_id]
                    baseline_overlap = old_target.intersection(neighbor)
                    proposed_overlap = proposed_target.intersection(neighbor)
                    added_overlap = actual_gain.intersection(neighbor)
                    baseline_projected = transform(PROJECT, baseline_overlap)
                    proposed_projected = transform(PROJECT, proposed_overlap)
                    added_projected = transform(PROJECT, added_overlap)
                    positive_added = introduces_positive_area_gain_overlap(actual_gain, neighbor)
                    row = {"neighbor_source_id": neighbor_source_id,
                        "baseline_relation": relation_kind(baseline_overlap),
                        "proposed_relation": relation_kind(proposed_overlap),
                        "baseline_intersection_area_raw_square_degrees": baseline_overlap.area,
                        "baseline_intersection_area_projected_m2": baseline_projected.area,
                        "proposed_intersection_area_raw_square_degrees": proposed_overlap.area,
                        "proposed_intersection_area_projected_m2": proposed_projected.area,
                        "added_gain_intersection_area_raw_square_degrees": added_overlap.area,
                        "added_gain_intersection_area_projected_m2": added_projected.area,
                        "new_positive_area_overlap": positive_added}
                    neighbor_rows.append(row)
                    if positive_added:
                        new_neighbor_overlaps.append(neighbor_source_id)
                batch_passed = bool(target_preserved and union_equals_expected_gain and actual_gain.area > 0
                    and all(candidates_retained.values()) and not new_neighbor_overlaps)
                trial = {"target_source_id": target_id, "candidate_ids": candidate_ids,
                    "old_target_geometry_sha256": sha(canonical(mapping(old_target))),
                    "proposed_target_geometry_sha256": sha(canonical(mapping(proposed_target))),
                    "added_gain_geometry_sha256": sha(canonical(mapping(actual_gain))),
                    "target_preserved_without_loss": target_preserved,
                    "union_gain_equals_candidate_minus_old_target_union": union_equals_expected_gain,
                    "added_gain_area_raw_square_degrees": actual_gain.area,
                    "added_gain_area_projected_m2_epsg_3338": transform(PROJECT, actual_gain).area,
                    "every_candidate_retained": candidates_retained,
                    "neighbor_checks": neighbor_rows,
                    "new_positive_area_overlap_neighbor_ids": new_neighbor_overlaps,
                    "collective_union_pass": batch_passed}
                batch_trials.append(trial)
                if batch_passed and selected_batch is None:
                    selected_batch, selected_union, selected_gain, selected_target_id = candidate_ids, proposed_target, actual_gain, target_id

    if selected_batch is not None:
        for case_row in cases:
            cid = case_row["component_id"]
            item = case_geometry_by_id[cid]
            if cid in selected_batch:
                case_row["disposition"] = "selected-initial-same-county-union-proposal"
            elif item["source_support_pass"] and item["parent_support_pass"]:
                case_row["disposition"] = "measured-not-selected-for-initial-union-batch"
            elif not item["parent_support_pass"]:
                case_row["disposition"] = "parent-support-unresolved-or-failed"
            else:
                case_row["disposition"] = "source-or-original-contact-support-unresolved"
        selected_original = atlas_geoms[selected_target_id]
        proposal_features.append({"type": "Feature", "id": "atlas-union:" + selected_target_id,
            "properties": {"target_source_id": selected_target_id, "component_ids_added": selected_batch,
                "baseline_commit": "6c0ea95b7a8214ac1548161368bd952af136b5c2",
                "old_target_geometry_sha256": sha(canonical(mapping(selected_original))),
                "proposed_target_geometry_sha256": sha(canonical(mapping(selected_union))),
                "added_gain_geometry_sha256": sha(canonical(mapping(selected_gain))),
                "status": "exact source-supported measurement proposal; no repair, physical, administrative or publication authority"},
            "geometry": mapping(selected_union)})
    else:
        for case_row in cases:
            cid = case_row["component_id"]
            item = case_geometry_by_id[cid]
            if item["source_support_pass"] and item["parent_support_pass"]:
                case_row["disposition"] = "measured-no-two-case-initial-batch-passed-collective-union-checks"
            elif not item["parent_support_pass"]:
                case_row["disposition"] = "parent-support-unresolved-or-failed"
            else:
                case_row["disposition"] = "source-or-original-contact-support-unresolved"
    gain_collection = {"type": "FeatureCollection", "features": ([{
        "type": "Feature", "id": "gain:" + selected_target_id,
        "properties": {"target_source_id": selected_target_id, "component_ids_added": selected_batch,
            "geometry_role": "exact proposed target union minus exact frozen old target"},
        "geometry": mapping(selected_gain)}] if selected_batch is not None else [])}

    # Nonvacuous controls use the actual input feature identities and predicates.
    first_case = cases[0]
    first_id = IDS[0]
    first_target_id = screen_by_id[first_id]["admin_context"]["atlas_target_original_id"]
    positive_control = {
        "kind": "positive-control",
        "component_id": first_id,
        "target_source_id": first_target_id,
        "candidate_intersection_raw_square_degrees": first_case["candidate_to_target_intersections_and_uncovered"]["candidate_vs_full_county"]["intersection_area_raw_square_degrees"],
        "expected": "positive-area candidate/full-county intersection",
        "passed": first_case["candidate_to_target_intersections_and_uncovered"]["candidate_vs_full_county"].get("positive_area_overlap") is True,
    }
    remote_feature = next((feature for feature in full_fc["features"]
        if feature.get("properties", {}).get("shapeName") == "New York" and
        feature.get("properties", {}).get("shapeISO") in ("US-NY", "")), None)
    if remote_feature is None:
        remote_feature = next(feature for feature in full_fc["features"]
            if feature.get("properties", {}).get("shapeName") == "Maui" )
    remote_geom = shape(remote_feature["geometry"])
    remote_relation = intersections(candidates[first_id], remote_geom)
    negative_control = {"kind": "negative-control", "component_id": first_id,
        "remote_shape_id": remote_feature["properties"]["shapeID"],
        "remote_shape_name": remote_feature["properties"]["shapeName"],
        "expected": "disjoint candidate/admin source geometry",
        "measured_relation": remote_relation,
        "passed": remote_relation.get("status") == "measured" and remote_relation.get("intersects") is False}
    mutated_target = first_target_id + "-mutated"
    join_rejected = mutated_target not in feature_index
    join_control = {"kind": "negative-input-join-control", "original_shape_id": first_target_id,
        "mutated_shape_id": mutated_target, "expected": "unknown target ID is rejected without fallback",
        "passed": join_rejected}
    invalid_input = Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])
    invalid_control = {"kind": "negative-invalid-geometry-control", "geometry_type": invalid_input.geom_type,
        "valid": bool(invalid_input.is_valid), "validity_reason": is_valid_reason(invalid_input),
        "expected": "invalid geometry remains rejected and un-repaired",
        "passed": (not invalid_input.is_valid and intersections(invalid_input, candidates[first_id])["status"] == "invalid-input")}
    positive_union_old = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
    positive_union_candidate = Polygon([(1, 0), (2, 0), (2, 1), (1, 1), (1, 0)])
    positive_union = unary_union([positive_union_old, positive_union_candidate])
    positive_union_gain = positive_union.difference(positive_union_old)
    positive_union_expected_gain = positive_union_candidate.difference(positive_union_old)
    union_old_loss = positive_union_old.difference(positive_union)
    positive_union_control = {"kind": "positive-control-exact-coordinate-union-fixture",
        "input_class": "fixed fixture only; does not qualify any actual Alaska candidate or batch",
        "coordinates": {"old_target": mapping(positive_union_old), "candidate": mapping(positive_union_candidate)},
        "expected": "exact adjacent-square union preserves the complete old target and adds the full candidate",
        "old_target_valid": bool(positive_union_old.is_valid),
        "union_valid": bool(positive_union.is_valid),
        "old_target_preserved": bool(positive_union.covers(positive_union_old) and union_old_loss.is_empty),
        "candidate_retained": bool(positive_union.covers(positive_union_candidate)),
        "gain_equals_candidate_minus_old_target": bool(positive_union_gain.equals(positive_union_expected_gain)
            and positive_union_gain.symmetric_difference(positive_union_expected_gain).is_empty),
        "positive_gain_area_raw_square_degrees_exact": positive_union_gain.area,
        "passed": bool(positive_union.is_valid and positive_union_gain.is_valid
            and positive_union.covers(positive_union_old) and union_old_loss.is_empty
            and positive_union.covers(positive_union_candidate)
            and positive_union_gain.equals(positive_union_expected_gain)
            and positive_union_gain.area > 0)}
    control_neighbor_id = next(identity for identity in EXPECTED_NEIGHBORS if identity != "gb:USA:ADM2:" + first_target_id)
    control_neighbor = neighbor_geoms[control_neighbor_id]
    control_baseline_overlap = positive_union_old.intersection(control_neighbor)
    adverse_gain = positive_union_gain.union(control_neighbor)
    adverse_new_overlap_area = adverse_gain.intersection(control_neighbor).area
    negative_overlap_control = {"kind": "negative-control-new-positive-area-neighbor-overlap",
        "component_id": first_id, "target_source_id": first_target_id,
        "neighbor_source_id": control_neighbor_id,
        "expected": "the exact zero-tolerance gain/neighbor overlap predicate rejects an addition that creates positive area against an actual Atlas neighbor",
        "baseline_overlap_area_raw_square_degrees_exact": control_baseline_overlap.area,
        "adverse_added_gain_overlap_area_raw_square_degrees_exact": adverse_new_overlap_area,
        "production_rejection_predicate": introduces_positive_area_gain_overlap(adverse_gain, control_neighbor),
        "passed": bool(adverse_new_overlap_area > 0 and introduces_positive_area_gain_overlap(adverse_gain, control_neighbor))}
    controls = [positive_control, negative_control, join_control, invalid_control,
                positive_union_control, negative_overlap_control]
    if not all(row["passed"] for row in controls):
        failed = [row for row in controls if not row["passed"]]
        raise RuntimeError("one or more nonvacuous geometry/input controls failed; failed="
                           + json.dumps(failed, sort_keys=True, allow_nan=False))

    parents = {feature["id"]: screen_by_id[feature["id"]]["admin_context"]["atlas_target_original_id"]
               for feature in candidate_fc["features"]}
    qualified_ids = selected_batch or []
    proposal_collection = {"type": "FeatureCollection", "features": proposal_features}
    input_report = []
    for path in sorted(input_paths):
        raw = read_bytes(path)
        input_report.append({"path": path.relative_to(ROOT).as_posix(), "bytes": len(raw), "sha256": sha(raw)})
    result = {
        "version": 1,
        "method_id": "alaska-thirteen-full-simplified-atlas-native-measurement-v1",
        "status": "measured",
        "assigned_scope": {"component_count": 13, "component_ids": IDS,
            "family_id": family["id"], "family_member_count": 995,
            "read_only_edge_neighbor_count": 17, "read_only_edge_neighbor_ids": EXPECTED_NEIGHBORS,
            "physical_query_relation_count": 25, "native_gshhg_record_count": 11,
            "native_gshhg_record_ids": NATIVE_IDS},
        "source_contact_lineage": {"original_detector_fragment_count": original_contacts_receipt["fragment_count"],
            "original_detector_contact_count": sum(x["exact_location_contact_count"] for x in original_contacts_receipt["fragments"]),
            "original_detector_baseline_commit": detector_vintage["original_detector_actual_baseline"],
            "actual_neighbor_geometry_count": len(neighbor_geoms),
            "actual_neighbor_baseline_commit": neighbor_receipt["baseline_commit"],
            "family_contact_ids_match_edge_neighbor_ids": family["original_fine_family"]["contact_ids"] == EXPECTED_NEIGHBORS,
            "original_fragment_feature_hashes_and_geometries_bind_to_exact_13_components": True,
            "baseline_vintage_is_pinned_and_matches_original_detector": True,
            "contact_authority_scope": "source-vintage-specific original baseline proof; not a current-world Atlas claim"},
        "inputs": {"immutable_execution_baseline_commit": IMMUTABLE_BASELINE_COMMIT,
                   "phase_admission": {"path": phase_path.relative_to(ROOT).as_posix(),
                          "bytes": len(phase_raw), "sha256": sha(phase_raw),
                          "complete_phase_bytes": phase["complete_phase_bytes"], "cap_bytes": phase["cap_bytes"]},
                   "files": input_report,
                   "decoded_native_aliases": phase["decoded_aliases"],
                   "native_full_member": native_receipt["whole_native_member"],
                   "native_reader": native_receipt["reader"],
                   "native_index": native_receipt["member_index"]},
        "method": {
            "geoboundaries_coordinate_assumption": "GeoJSON longitude,latitude in geographic WGS84/EPSG:4326 as implied by source product; no source coordinate transformation was applied before topology checks.",
            "native_coordinate_decode": "GSHHG binary signed int32 longitude,latitude multiplied by 1e-6 to match the original query decoder; values greater than 180 degrees are shifted by -360 degrees; the exact inverse restores x<0 by +360; no seam heuristic or coordinate snapping is applied.",
            "axis_order": "always_xy longitude,latitude",
            "projected_area_crs": "EPSG:3338 Alaska Albers Equal Area; output linear units metres; area values in square metres",
            "raw_area_units": "square degrees (coordinate-plane diagnostic only; not physical area)",
            "projection": proj_description,
            "validity": "Shapely validity is reported for every used geometry; invalid source geometry is never repaired, buffered, snapped or silently discarded.",
            "strict_no_loss": "Exact topological covers predicate and candidate minus reference area exactly 0.0 after EPSG:3338 projection; no tolerance is used.",
            "variant_agreement": "Full/simplified results agree for a case only when the candidate's exact coverage boolean, overlap boolean, projected intersection area and projected uncovered area are identical.",
            "source_registration": "No per-feature datum realization, ground control, observation date or shoreline registration is established by these files.",
            "geometry_repairs": [],
        },
        "source_limits": {
            "administrative": "geoBoundaries USA ADM2 release tag 9469f09; full source retained for 3,233 features; selected source targets represent the 2018 source-year claim; source product variants may differ.",
            "parent": "The source parent check uses the geoBoundaries USA ADM1 Alaska feature from the same release tag and its recorded 2018 claim; it is a source parent reference, not a new political or real-world authority finding.",
            "native": "GSHHG 2.3.7 released 2017-06-15; 11 retained records are level 1; per-feature observation dates and precision/registration are not established. Coarse land support is not repair approval.",
            "licensing": "Original packet attribution/use-term statements and source product licenses are retained as inputs; this result adds no legal conclusion.",
            "geographic_authority": "No repair authority, history, ownership, rights, political affiliation, release approval or publication permission is asserted.",
        },
        "counties": {"full_source_feature_count": len(full_geoms), "simplified_target_feature_count": len(simple_geoms),
                      "atlas_target_feature_count": len(atlas_geoms), "actual_atlas_neighbor_feature_count": len(neighbor_geoms),
                      "parent_source_feature_id": parent_props["shapeID"]},
        "physical_relation_preservation": {"source_row_count": len(physical_rows),
            "relation_count": finding_relation_count, "rows": physical_admission},
        "administrative_neighbor_context": {"declared_neighbor_count": len(EXPECTED_NEIGHBORS),
            "pairs_measured": len(EXPECTED_NEIGHBORS) * len(IDS),
            "all_full_source_contacts_discovered": len(admin_pairs),
            "contacts_by_candidate": {cid: [row for row in admin_pairs if row["component_id"] == cid] for cid in IDS},
            "declared_neighbor_pairs": {cid: [row for row in cases[i]["administrative_contacts_17_declared_neighbors"]] for i, cid in enumerate(IDS)}},
        "native_source_pair_count": len(native_pairs),
        "native_relations": native_pairs,
        "candidate_pair_count": len(candidate_pair_relations),
        "candidate_pairwise_contacts": candidate_pair_relations,
        "cases": cases,
        "controls": controls,
        "collective_union_checks": {"initial_batch_candidate_count": 0 if selected_batch is None else len(selected_batch),
            "selected_target_source_id": selected_target_id, "selected_component_ids": selected_batch or [],
            "batch_trials": batch_trials,
            "meaning": "All 13 cases remain measured. Only a same-county two-or-three-case batch with source/parent support, exact union gain and no new positive-area overlap against any other actual Atlas family neighbor is emitted as a proposal."},
        "proposal": {"qualifying_component_ids": qualified_ids,
            "geometry_file": "proposal-geometry.geojson",
            "feature_count": len(proposal_features),
            "gain_geometry_file": "proposal-gain-geometry.geojson",
            "meaning": "Exact frozen original target unioned with the selected same-county candidate batch, plus a separate exact added-gain geometry. This is a measurement proposal, never an approved repair or production change."},
        "outputs": ["measurement.json", "proposal-geometry.geojson", "proposal-gain-geometry.geojson"],
    }
    if not positive_control["passed"] or not negative_control["passed"] or not join_control["passed"] or not invalid_control["passed"]:
        raise RuntimeError("positive/negative input or geometry control failed")

    payloads = {
        "measurement.json": canonical(result),
        "proposal-geometry.geojson": canonical(proposal_collection),
        "proposal-gain-geometry.geojson": canonical(gain_collection),
    }
    generated = [{"path": name, "bytes": len(raw), "sha256": sha(raw)}
                 for name, raw in sorted(payloads.items())]
    manifest = {"version": 1, "method_id": result["method_id"],
                "input_set_sha256": sha(canonical(input_report)), "outputs": generated}
    payloads["output-manifest.json"] = canonical(manifest)
    total = sum(len(raw) for raw in payloads.values())
    if total + 4096 > phase["ceilings"]["generated_output_bytes"]:
        raise RuntimeError("actual deterministic output exceeded its admitted byte reserve")
    publication_rows = VINTAGE.publish_bytes(payloads)
    print(json.dumps({"status": "measured", "component_count": len(cases),
        "physical_relations": finding_relation_count, "native_record_pairs": len(native_pairs),
        "admin_neighbor_pairs": len(admin_pairs), "qualifying_candidates": len(qualified_ids),
        "output_bytes": total, "output_manifest_sha256": sha(payloads["output-manifest.json"]),
        "published_outputs": publication_rows, "publication_receipt": str(VINTAGE.root / "publication.json"),
        "controls_passed": len(controls)}))


if __name__ == "__main__":
    main()
