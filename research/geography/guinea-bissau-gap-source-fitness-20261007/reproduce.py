#!/usr/bin/env python3
"""Bounded, immutable reproduction for WorldAtlas issue #1416."""
import argparse
import csv
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import gzip
from datetime import datetime
from zoneinfo import ZoneInfo
from decimal import Decimal

import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.io import MemoryFile
from rasterio.windows import from_bounds
from shapely.geometry import mapping, shape

PACKET = "research/geography/guinea-bissau-gap-source-fitness-20261007"
VINTAGE_ROOT = PACKET + "/vintages/"
BASELINE_COMMIT = "6a47b43025d963daf80915c6d219c75ebcc8cd91"
FAMILY_ID = "gap-source-batch:c1a3828584658dbb0c2dd5c8"
MAX_RUN_OUTPUT = 8 * 1024 * 1024
CLASS_CODES = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100]
RUN_FILES = [
    "component-features.geojson", "current-contacts.geojson",
    "fragment-bindings.csv", "component-route-rows.json", "topology-relations.csv",
    "intersection-geometries.geojson", "worldcover-class-counts.json",
    "legacy-observation.json", "method-results.json", "metric-ledger.json",
]
CONTROL_FILES = [
    "measurement-positive-control.json", "measurement-negative-control.json",
    "packet-positive-control.json", "packet-negative-control.json",
    "reproducibility-control.json",
]
TILES = {
    2020: {
        "path": PACKET + "/sources/esa-worldcover/worldcover-2020-v100-N09W018.tif",
        "sha256": "489229515d39a3f27fc89e86efdbe5179a67f344eeea5c1442f14f77040bedc9",
        "bytes": 10781856, "version": "V1.0.0", "algorithm": "V1.0.0",
        "time_start": "2020-01-01T00:00:00Z", "time_end": "2020-12-31T23:59:59Z",
    },
    2021: {
        "path": PACKET + "/sources/esa-worldcover/worldcover-2021-v200-N09W018.tif",
        "sha256": "402ff66c9e150db6c338854af9d86bedb9cebc06f859ac43f4909a574d5ddd30",
        "bytes": 11458141, "version": "V2.0.0", "algorithm": "V2.0.0",
        "time_start": "2021-01-01T00:00:00Z", "time_end": "2021-12-31T23:59:59Z",
    },
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def load_json(raw, label):
    try:
        return json.loads(raw)
    except Exception as error:
        raise ValueError("Invalid JSON: " + label) from error


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.PIPE)


def baseline_and_scope(repo):
    packet = Path(repo) / PACKET
    scope_raw = (packet / "scope.json").read_bytes()
    snapshot_raw = (packet / "sources/issue-1416.json").read_bytes()
    scope = load_json(scope_raw, "scope.json")
    snapshot = load_json(snapshot_raw, "issue snapshot")
    if scope.get("baseline_commit") != BASELINE_COMMIT or scope.get("issue_number") != 1416:
        raise ValueError("Issue scope or immutable baseline changed")
    if sha(snapshot_raw) != scope.get("issue_snapshot_sha256"):
        raise ValueError("Captured issue source no longer matches its scope receipt")
    issue = snapshot.get("issue", {})
    if issue.get("number") != 1416 or issue.get("state") != "open":
        raise ValueError("Issue source is not the expected open issue")
    contract_match = re.search(r"<!-- worldatlas-work:v1\s*([\s\S]*?)\s*-->", issue.get("body", ""))
    if not contract_match:
        raise ValueError("Issue source lacks the accepted work contract")
    contract = load_json(contract_match.group(1).encode(), "work contract")
    quality = contract.get("evidence_quality", {})
    if quality != scope.get("evidence_quality_contract"):
        raise ValueError("Captured scope disagrees with issue evidence contract")
    body = issue["body"]
    component_text = re.search(r"## Complete physical-component roster\s*```text\s*([\s\S]*?)```", body)
    contact_text = re.search(r"## Complete current contact-feature roster\s*```text\s*([\s\S]*?)```", body)
    legacy_text = re.search(r"## Complete preserved legacy observation\s*```json\s*([\s\S]*?)```", body)
    if not component_text or not contact_text or not legacy_text:
        raise ValueError("Issue does not include all accepted rosters")
    components = component_text.group(1).strip().split()
    contacts = contact_text.group(1).strip().split()
    legacy = load_json(legacy_text.group(1).encode(), "legacy observation")
    if components != scope.get("components") or contacts != scope.get("contacts") or legacy[0] != scope.get("legacy_observation"):
        raise ValueError("Scope roster/legacy row differs from captured issue body")
    expected_family_hash = re.search(r"Family row exact-line SHA-256: `([a-f0-9]{64})`", body)
    if not expected_family_hash:
        raise ValueError("Issue lacks its exact family-row digest")
    pins = quality.get("pins", {})
    pin_files = quality.get("pin_files", {})
    if set(pins) != set(pin_files) or len(pin_files) != 60:
        raise ValueError("Issue pin inventory is incomplete")
    files_by_path = {}
    for key, path in pin_files.items():
        size = int(git(repo, "cat-file", "-s", BASELINE_COMMIT + ":" + path))
        item = {"path": path, "bytes": size, "sha256": pins[key], "hash_kind": "file-bytes"}
        if path in files_by_path and files_by_path[path] != item:
            raise ValueError("Conflicting pin paths")
        files_by_path[path] = item
    # These project bytes implement the selector transform and safe writer. They
    # are explicit baseline inputs even though the issue's original pin set does
    # not name project code.
    for path in ["scripts/evidence/immutable.py", "scripts/administrative.py"]:
        raw = git(repo, "show", BASELINE_COMMIT + ":" + path)
        item = {"path": path, "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes"}
        files_by_path[path] = item
    immutable_path = Path(repo) / "scripts/evidence/immutable.py"
    if immutable_path.read_bytes() != git(repo, "show", BASELINE_COMMIT + ":scripts/evidence/immutable.py"):
        raise ValueError("Current preparation helper differs from pinned baseline code")
    spec = importlib.util.spec_from_file_location("verified_worldatlas_immutable", immutable_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    baseline = helper.Baseline(str(repo), BASELINE_COMMIT, list(files_by_path.values()))
    return baseline, helper, scope, snapshot, quality, pin_files, expected_family_hash.group(1)


def pinned(baseline, key, pin_files):
    paths = pin_files
    path = paths[key]
    return path, baseline.pinned_bytes(path)


def decode_gzip(baseline, key, pin_files):
    path, raw = pinned(baseline, key, pin_files)
    decoded = gzip.decompress(raw)
    baseline.admit(path + ":decoded", len(decoded))
    return path, raw, decoded


def parse_json_lines(raw):
    rows = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            rows.append((line, json.loads(line)))
        except json.JSONDecodeError:
            # Some routing shards have a non-JSON inventory preamble. Preserve
            # it in the pinned input; only parsed data rows are used here.
            continue
    return rows


def exact_roster(expected, actual, label):
    if len(actual) != len(set(actual)) or set(actual) != set(expected) or len(actual) != len(expected):
        raise ValueError(label + " does not exactly match unique accepted subjects")


def verify_hash(raw, expected, label):
    if sha(raw) != expected:
        raise ValueError(label + " bytes do not match their whole-file pin")


def feature_map(features, key, label):
    result = {}
    for feature in features:
        value = feature.get(key, feature.get("properties", {}).get(key))
        if not isinstance(value, str) or not value or value in result:
            raise ValueError(label + " has missing or duplicate identity")
        result[value] = feature
    return result


def coordinate_count(value):
    if (isinstance(value, list) and len(value) >= 2
        and all(isinstance(part, (int, float)) for part in value[:2])):
        return 1
    if isinstance(value, list):
        return sum(coordinate_count(part) for part in value)
    return 0


def coordinate_decimal_places(raw, wanted_ids=None):
    collection = json.loads(raw, parse_float=Decimal)
    wanted = set(wanted_ids) if wanted_ids else None
    places = []
    def walk(value):
        if (isinstance(value, list) and len(value) >= 2
            and all(isinstance(part, (int, float, Decimal)) for part in value[:2])):
            for part in value[:2]:
                places.append(max(0, -part.as_tuple().exponent) if isinstance(part, Decimal) else 0)
            return
        if isinstance(value, list):
            for part in value:
                walk(part)
    for feature in collection.get("features", []):
        if wanted is None or feature.get("id") in wanted or feature.get("properties", {}).get("id") in wanted:
            walk(feature.get("geometry", {}).get("coordinates", []))
    if not places:
        raise ValueError("No coordinate tokens available for precision screen")
    return {"minimum_decimal_places": min(places), "maximum_decimal_places": max(places)}


def parse_csv(raw):
    return list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))


def canonical_ring(coords):
    points = [tuple(point) for point in coords]
    if len(points) > 1 and points[0] == points[-1]:
        points.pop()
    if not points:
        return tuple()
    def least_rotation(seq):
        n = len(seq)
        doubled = seq + seq
        i, j, k = 0, 1, 0
        while i < n and j < n and k < n:
            left, right = doubled[i + k], doubled[j + k]
            if left == right:
                k += 1
                continue
            if left > right:
                i = i + k + 1
                if i <= j:
                    i = j + 1
            else:
                j = j + k + 1
                if j <= i:
                    j = i + 1
            k = 0
        start = min(i, j)
        return tuple(doubled[start:start + n])
    return min(least_rotation(points), least_rotation(list(reversed(points))))


def coordinate_signature(geometry):
    kind = geometry.get("type")
    coords = geometry.get("coordinates")
    if kind == "Polygon":
        return (kind, canonical_ring(coords[0]), tuple(sorted(canonical_ring(ring) for ring in coords[1:])))
    if kind == "MultiPolygon":
        return (kind, tuple(sorted(coordinate_signature({"type": "Polygon", "coordinates": poly}) for poly in coords)))
    return (kind, json.dumps(coords, sort_keys=True, separators=(",", ":"), ensure_ascii=False))


def topology_relation(left, right):
    if left.is_empty or right.is_empty or left.disjoint(right):
        return "disjoint", None
    intersection = left.intersection(right)
    if intersection.is_empty:
        return "disjoint", None
    if intersection.area > 0:
        return "positive-area", intersection
    if intersection.length > 0:
        return "shared-edge", intersection
    return "point-contact", intersection


def point_inside_window(geometry, dataset):
    xmin, ymin, xmax, ymax = shape(geometry).bounds
    left, bottom, right, top = dataset.bounds
    if xmin < left or xmax > right or ymin < bottom or ymax > top:
        raise ValueError("Subject is not fully within the retained W018 source tile")
    window = from_bounds(xmin, ymin, xmax, ymax, transform=dataset.transform)
    row0 = max(0, math.floor(window.row_off) - 1)
    col0 = max(0, math.floor(window.col_off) - 1)
    row1 = min(dataset.height, math.ceil(window.row_off + window.height) + 1)
    col1 = min(dataset.width, math.ceil(window.col_off + window.width) + 1)
    if row1 <= row0 or col1 <= col0:
        raise ValueError("Empty raster window for subject")
    win = rasterio.windows.Window(col0, row0, col1 - col0, row1 - row0)
    values = dataset.read(1, window=win)
    mask = geometry_mask([geometry], out_shape=values.shape,
                         transform=dataset.window_transform(win),
                         all_touched=False, invert=True)
    selected = values[mask]
    return class_counts(selected), int(mask.sum())


def class_counts(selected):
    unique, counts = np.unique(selected, return_counts=True)
    found = {int(code): int(count) for code, count in zip(unique, counts)}
    return {str(code): found.get(code, 0) for code in CLASS_CODES}


def validate_raster_metadata(meta, year):
    expected = TILES[year]
    if (meta.get("crs") != "EPSG:4326" or meta.get("width") != 36000 or meta.get("height") != 36000
        or meta.get("bounds") != [-18.0, 9.0, -15.0, 12.0]
        or meta.get("pixel_size") != [1 / 12000, -1 / 12000]
        or meta.get("product_tile") != "N09W018"
        or meta.get("product_version") != expected["version"]
        or meta.get("algorithm_version") != expected["algorithm"]
        or meta.get("time_start") != expected["time_start"]
        or meta.get("time_end") != expected["time_end"]
        or meta.get("band_count") != 1 or meta.get("nodata") != 0
        or "CC-BY 4.0" not in meta.get("license", "")):
        raise ValueError("WorldCover CRS/grid/tile/version/epoch metadata drift")


def assert_contacts(contacts, source_features):
    source_by_id = feature_map(source_features, "shapeID", "GNB source")
    ids = []
    for feature in contacts:
        props = feature["properties"]
        metadata = props.get("metadata", {})
        source_id = metadata.get("original_id")
        if not source_id or source_id not in source_by_id:
            raise ValueError("Current contact does not join to one original source feature")
        ids.append(feature["id"])
    if len(ids) != 4 or len(ids) != len(set(ids)):
        raise ValueError("Contact roster is incomplete or duplicated")


def build_outputs(repo, run_name):
    baseline, helper, scope, snapshot, quality, pin_files, family_hash = baseline_and_scope(repo)
    administrative_code = baseline.pinned_bytes("scripts/administrative.py")
    if b"rule['source_url'].replace('.geojson','_simplified.geojson')" not in administrative_code:
        raise ValueError("Pinned administrative selector does not implement the recorded simplification transform")
    packet = Path(repo) / PACKET
    baseline.admit("candidate:" + PACKET + "/scope.json", (packet / "scope.json").stat().st_size)
    baseline.admit("candidate:" + PACKET + "/sources/issue-1416.json", (packet / "sources/issue-1416.json").stat().st_size)
    all_ids = scope["components"]
    contacts_ids = scope["contacts"]
    contact_set = set(contacts_ids)
    if len(all_ids) != 45 or len(contacts_ids) != 4:
        raise ValueError("Full 45+4 issue scope required")

    # Admit every external/materialized input and the maximum output budget
    # before creating a vintage or doing geometry/raster computation.
    tile_bytes = {}
    for year, tile in TILES.items():
        raw = (packet / tile["path"].removeprefix(PACKET + "/")).read_bytes()
        verify_hash(raw, tile["sha256"], f"WorldCover {year} tile")
        if len(raw) != tile["bytes"]:
            raise ValueError(f"WorldCover {year} staged byte count changed")
        baseline.admit("candidate:" + tile["path"], len(raw))
        tile_bytes[year] = raw
    route_keys = sorted(key for key in pin_files if key.startswith("routing.admin_bindings."))
    if len(route_keys) != 9:
        raise ValueError("Expected all nine pinned administrative-binding route shards")
    decoded_keys = ["routing.family.010", "source_corpus.gnb_adm2", "routing.land_source_fitness"] + route_keys
    decoded_keys += [key for key in pin_files if key.startswith("component_custody.payload.")]
    if len(decoded_keys) != 23:
        raise ValueError("Expected the family, nine route, 11 custody, simplified-source, and historical-source inputs")
    for key in decoded_keys:
        path, raw = pinned(baseline, key, pin_files)
        if len(raw) < 18 or raw[:2] != bytes.fromhex("1f8b"):
            raise ValueError("A selected compressed source lacks a gzip header")
        decoded_size = int.from_bytes(raw[-4:], "little")
        baseline.admit(path + ":decoded", decoded_size)
    projected = sum(baseline.consumed.values()) + MAX_RUN_OUTPUT + 4096
    if projected > helper.MAX_PHASE_BYTES:
        raise ValueError("Complete admitted input plus output phase exceeds the shared evidence byte budget")

    # Establish the fresh whole-run destination before raster reads or outputs.
    output_paths = [f"{VINTAGE_ROOT}{run_name}/{name}" for name in RUN_FILES]
    vintage = helper.NewVintage(baseline, PACKET + "/", run_name, RUN_FILES)

    family_path, family_raw, family_decoded = decode_gzip(baseline, "routing.family.010", pin_files)
    family_rows = parse_json_lines(family_decoded)
    matched = [(line, row) for line, row in family_rows if row.get("id") == FAMILY_ID]
    if len(matched) != 1:
        raise ValueError("Expected exactly one scoped routing family row in its pinned shard")
    family_line, family = matched[0]
    if sha(family_line) != family_hash or family.get("component_count") != 45:
        raise ValueError("Routing family row digest/count differs from accepted issue")
    exact_roster(all_ids, family.get("complete_component_ids", []), "Routing family row")

    custody_path, custody_raw = pinned(baseline, "component_custody.index", pin_files)
    custody = load_json(custody_raw, "custody index")
    payload_paths = {entry["path"] for entry in custody.get("payloads", [])}
    selected_payloads = [key for key in pin_files if key.startswith("component_custody.payload.")]
    if len(selected_payloads) != 11:
        raise ValueError("Issue source pin list must retain all 11 selected custody payloads")
    component_set = set(all_ids)
    components = {}
    for key in selected_payloads:
        path, raw, decoded = decode_gzip(baseline, key, pin_files)
        if path not in payload_paths:
            raise ValueError("Selected custody payload is absent from the pinned custody index")
        collection = load_json(decoded, path)
        for feature in collection.get("features", []):
            identity = feature.get("id")
            if identity not in component_set:
                continue
            if identity in components:
                raise ValueError("Duplicate component identity across custody payloads")
            if not feature.get("geometry") or feature.get("type") != "Feature":
                raise ValueError("Component geometry missing from custody feature")
            components[identity] = feature
    exact_roster(all_ids, list(components), "Custody payload feature roster")
    fragment_rows = []
    for identity in all_ids:
        bindings = components[identity].get("properties", {}).get("fragment_bindings", [])
        for binding in bindings:
            fragment_rows.append({"component_id": identity,
                                  "fragment_id": binding.get("id"),
                                  "feature_sha256": binding.get("feature_sha256")})
    fragment_ids = [row["fragment_id"] for row in fragment_rows]
    if len(fragment_rows) != 45 or len(fragment_ids) != len(set(fragment_ids)) or any(
        not row["fragment_id"] or not re.fullmatch(r"[a-f0-9]{64}", row["feature_sha256"] or "")
        for row in fragment_rows):
        raise ValueError("Complete source fragment bindings fail identity/hash validation")
    prior472_findings_path, prior472_findings_raw = pinned(baseline, "prior_472.findings", pin_files)
    prior472_findings = load_json(prior472_findings_raw, prior472_findings_path)
    prior472_rows_path, prior472_rows_raw = pinned(baseline, "prior_472.subject_assessments", pin_files)
    prior472_all_rows = parse_csv(prior472_rows_raw)
    prior472_contact_rows = [row for row in prior472_all_rows if row.get("subject_id") in contact_set]
    exact_roster(contacts_ids, [row["subject_id"] for row in prior472_contact_rows], "Prior #472 contact assessments")
    prior812_summary_path, prior812_summary_raw = pinned(baseline, "prior_812.summary", pin_files)
    prior812_summary = load_json(prior812_summary_raw, prior812_summary_path)
    prior812_rows_path, prior812_rows_raw = pinned(baseline, "prior_812.crosswalk", pin_files)
    prior812_all_rows = parse_csv(prior812_rows_raw)
    prior812_contact_rows = [row for row in prior812_all_rows if row.get("atlas_subject_id") in contact_set]
    exact_roster(contacts_ids, [row["atlas_subject_id"] for row in prior812_contact_rows], "Prior #812 contact crosswalk")

    # The current Atlas contacts and both source products come from distinct,
    # explicitly pinned files. The selector transform matches administrative.py.
    part_path, part_raw = pinned(baseline, "current.gnb_contact_part", pin_files)
    part = load_json(part_raw, part_path)
    current_contacts = [feature for feature in part.get("features", []) if feature.get("id") in contact_set]
    exact_roster(contacts_ids, [feature.get("id") for feature in current_contacts], "Current Atlas contacts")
    contact_precision = coordinate_decimal_places(part_raw, contacts_ids)
    policy_path, policy_raw = pinned(baseline, "current.location_policy", pin_files)
    policy = load_json(policy_raw, policy_path)
    registry_path, registry_raw = pinned(baseline, "current.administrative_sources", pin_files)
    registry = load_json(registry_raw, registry_path)
    rule = policy.get("countries", {}).get("GNB", {})
    source_id = "gb:GNB:ADM2"
    source_meta = registry.get(source_id, {})
    selected_full_url = rule.get("source_url")
    selected_simplified_url = selected_full_url.replace(".geojson", "_simplified.geojson") if selected_full_url else None
    if (selected_full_url != source_meta.get("gjDownloadURL")
        or selected_simplified_url != source_meta.get("simplifiedGeometryGeoJSON")):
        raise ValueError("GNB source selector/administrative.py simplification transform mismatch")
    full_path, full_raw = pinned(baseline, "source_corpus.gnb_full_product", pin_files)
    full = load_json(full_raw, full_path)
    simplified_path, simplified_raw, simplified_decoded = decode_gzip(baseline, "source_corpus.gnb_adm2", pin_files)
    if sha(simplified_decoded) != source_meta.get("sha256"):
        raise ValueError("Decompressed simplified GNB product does not match the registry source checksum")
    simplified = load_json(simplified_decoded, simplified_path)
    full_precision = coordinate_decimal_places(full_raw)
    simplified_precision = coordinate_decimal_places(simplified_decoded)
    metadata_path, metadata_raw = pinned(baseline, "prior_472.gnb_adm2_metadata", pin_files)
    source_metadata = load_json(metadata_raw, metadata_path)
    if (source_metadata.get("boundaryISO") != "GNB" or source_metadata.get("boundaryType") != "ADM2"
        or source_metadata.get("boundaryYear") != "2017"
        or source_metadata.get("admUnitCount") not in ("39", 39)
        or "Open Database License 1.0" not in source_metadata.get("boundaryLicense", "")):
        raise ValueError("Pinned GNB ADM2 source metadata disagrees with the issue scope")
    full_features = full.get("features", [])
    simplified_features = simplified.get("features", [])
    full_by_id = feature_map(full_features, "shapeID", "full GNB ADM2")
    simple_by_id = feature_map(simplified_features, "shapeID", "simplified GNB ADM2")
    exact_roster(list(full_by_id), list(simple_by_id), "Full/simplified GNB ADM2 identities")
    if len(full_by_id) != 39:
        raise ValueError("Expected the source metadata's full 39-unit GNB ADM2 roster")
    source_product_diffs = {"topological_equal": 0, "coordinate_identity_exact": 0}
    for identity in full_by_id:
        full_geometry = full_by_id[identity]["geometry"]
        simplified_geometry = simple_by_id[identity]["geometry"]
        if shape(full_geometry).equals(shape(simplified_geometry)):
            source_product_diffs["topological_equal"] += 1
        if coordinate_signature(full_geometry) == coordinate_signature(simplified_geometry):
            source_product_diffs["coordinate_identity_exact"] += 1
    assert_contacts(current_contacts, full_features)
    assert_contacts(current_contacts, simplified_features)
    contact_comparisons = []
    for contact in current_contacts:
        props = contact["properties"]
        contact_meta = props.get("metadata", {})
        source_shape_id = contact_meta.get("original_id")
        full_feature = full_by_id[source_shape_id]
        simple_feature = simple_by_id[source_shape_id]
        current_geometry = shape(contact["geometry"])
        full_geometry = shape(full_feature["geometry"])
        simple_geometry = shape(simple_feature["geometry"])
        contact_comparisons.append({
            "contact_id": contact["id"], "current_name": props.get("name"),
            "source_shape_id": source_shape_id,
            "full_source_name": full_feature["properties"].get("shapeName"),
            "simplified_source_name": simple_feature["properties"].get("shapeName"),
            "name_matches_full_source": props.get("name") == full_feature["properties"].get("shapeName"),
            "current_vertex_count": coordinate_count(contact["geometry"]["coordinates"]),
            "full_source_vertex_count": coordinate_count(full_feature["geometry"]["coordinates"]),
            "simplified_source_vertex_count": coordinate_count(simple_feature["geometry"]["coordinates"]),
            "current_equals_full_topologically": current_geometry.equals(full_geometry),
            "current_equals_simplified_topologically": current_geometry.equals(simple_geometry),
            "current_coordinate_identity_full": coordinate_signature(contact["geometry"]) == coordinate_signature(full_feature["geometry"]),
            "current_coordinate_identity_simplified": coordinate_signature(contact["geometry"]) == coordinate_signature(simple_feature["geometry"]),
            "full_equals_simplified_topologically": full_geometry.equals(simple_geometry),
            "full_coordinate_identity_simplified": coordinate_signature(full_feature["geometry"]) == coordinate_signature(simple_feature["geometry"]),
        })
    contact_comparisons.sort(key=lambda row: row["contact_id"])

    component_geoms = {identity: shape(feature["geometry"]) for identity, feature in components.items()}
    contact_geoms = {feature["id"]: shape(feature["geometry"]) for feature in current_contacts}
    source_products = [("full", full_features), ("simplified", simplified_features)]
    subjects = [("component", identity, feature["geometry"], component_geoms[identity])
                for identity, feature in components.items()]
    subjects += [("contact", identity, feature["geometry"], contact_geoms[identity])
                 for identity, feature in ((f["id"], f) for f in current_contacts)]
    topology_rows = []
    intersections = []
    topology_counts = {}
    for subject_kind, subject_id, raw_geometry, geom in subjects:
        for product, source_features in source_products:
            for source_feature in source_features:
                source_feature_id = source_feature["properties"]["shapeID"]
                source_geom = shape(source_feature["geometry"])
                relation = "unresolved-invalid-input"
                overlay = None
                if geom.is_valid and source_geom.is_valid:
                    relation, overlay = topology_relation(geom, source_geom)
                equal = bool(geom.equals(source_geom)) if geom.is_valid and source_geom.is_valid else False
                coordinate_equal = coordinate_signature(raw_geometry) == coordinate_signature(source_feature["geometry"])
                overlay_id = ""
                if overlay is not None:
                    overlay_id = f"{subject_kind}:{subject_id}|{product}:{source_feature_id}"
                    intersections.append({"type": "Feature", "id": overlay_id,
                        "properties": {"subject_kind": subject_kind, "subject_id": subject_id,
                                       "source_product": product, "source_feature_id": source_feature_id,
                                       "relation": relation, "topological_equal": equal,
                                       "coordinate_identity_exact": coordinate_equal},
                        "geometry": mapping(overlay)})
                row = {"subject_kind": subject_kind, "subject_id": subject_id,
                       "source_product": product, "source_feature_id": source_feature_id,
                       "source_feature_name": source_feature["properties"].get("shapeName", ""),
                       "subject_input_valid": bool(geom.is_valid), "source_input_valid": bool(source_geom.is_valid),
                       "topology_relation": relation, "topological_equal": equal,
                       "coordinate_identity_exact": coordinate_equal, "intersection_feature_id": overlay_id}
                topology_rows.append(row)
                topology_counts[(subject_kind, product, relation)] = topology_counts.get((subject_kind, product, relation), 0) + 1

    tile_raws = {}
    tile_records = {}
    for year, expected in TILES.items():
        raw = tile_bytes[year]
        if len(raw) != expected["bytes"] or sha(raw) != expected["sha256"]:
            raise ValueError(f"WorldCover {year} source byte identity mismatch")
        tile_raws[year] = raw
        local_mtime = datetime.fromtimestamp(Path(repo, expected["path"]).stat().st_mtime,
                                              ZoneInfo("America/Los_Angeles")).isoformat()
        tile_records[year] = {"path": expected["path"], "bytes": len(raw), "sha256": sha(raw),
                              "local_file_mtime": local_mtime,
                              "url": "https://esa-worldcover.s3.eu-central-1.amazonaws.com/" +
                                    ("v100/2020/map/ESA_WorldCover_10m_2020_v100_N09W018_Map.tif" if year == 2020 else
                                     "v200/2021/map/ESA_WorldCover_10m_2021_v200_N09W018_Map.tif")}
    worldcover = []
    raster_meta = {}
    for year, raw in tile_raws.items():
        with MemoryFile(raw) as memory_file:
            with memory_file.open() as dataset:
                tags = dataset.tags()
                meta = {"crs": dataset.crs.to_string() if dataset.crs else None,
                        "width": dataset.width, "height": dataset.height,
                        "band_count": dataset.count, "nodata": dataset.nodata,
                        "bounds": [dataset.bounds.left, dataset.bounds.bottom, dataset.bounds.right, dataset.bounds.top],
                        "pixel_size": [dataset.transform.a, dataset.transform.e],
                        "product_tile": tags.get("product_tile"), "product_version": tags.get("product_version"),
                        "algorithm_version": tags.get("algorithm_version"),
                        "time_start": tags.get("time_start"), "time_end": tags.get("time_end"),
                        "license": tags.get("license"), "title": tags.get("title")}
                validate_raster_metadata(meta, year)
                raster_meta[str(year)] = meta
                for subject_kind, subject_id, geometry, _geom in subjects:
                    counts, pixels = point_inside_window(geometry, dataset)
                    if pixels == 0:
                        raise ValueError("No cell centers sampled inside a scoped subject")
                    worldcover.append({"subject_kind": subject_kind, "subject_id": subject_id,
                                       "product_year": year, "product_version": meta["product_version"],
                                       "algorithm_version": meta["algorithm_version"],
                                       "pixel_rule": "pixel center; all_touched=false",
                                       "candidate_pixel_count": pixels,
                                       "class_counts": counts})

    hist_path, hist_raw, hist_decoded = decode_gzip(baseline, "routing.land_source_fitness", pin_files)
    hist_rows = parse_json_lines(hist_decoded)
    route_records = []
    for key in route_keys:
        _path, _raw, decoded = decode_gzip(baseline, key, pin_files)
        route_records.extend(row for _line, row in parse_json_lines(decoded) if isinstance(row, dict))
    component_route_rows = [row for row in route_records if row.get("component") in set(all_ids)]
    exact_roster(all_ids, [row.get("component") for row in component_route_rows], "Current route rows")
    legacy_sha = scope["legacy_observation"]["original_admin_observations"][0]["whole_original_row_sha256"]
    legacy_matches = []
    def find_legacy(value):
        if isinstance(value, dict):
            if value.get("whole_original_row_sha256") == legacy_sha:
                legacy_matches.append(value)
            for nested in value.values():
                find_legacy(nested)
        elif isinstance(value, list):
            for nested in value:
                find_legacy(nested)
    for _line, row in hist_rows:
        find_legacy(row)
    if len(legacy_matches) != 1 or legacy_matches[0] != scope["legacy_observation"]["original_admin_observations"][0]:
        raise ValueError("Exact preserved legacy observation is not uniquely present in the pinned source record")

    metrics = []
    def add_metric(metric_id, value, unit, input_hash):
        metrics.append({"id": metric_id, "value": int(value), "unit": unit,
                        "vintage": "baseline", "evaluation_commit": BASELINE_COMMIT,
                        "input_sha256": input_hash})
    family_sha = sha(family_raw)
    add_metric("issue_component_count", len(components), "component features", family_sha)
    add_metric("issue_contact_count", len(current_contacts), "current contact features", sha(part_raw))
    add_metric("legacy_observation_count", len(legacy_matches), "preserved historical observations", sha(hist_raw))
    add_metric("component_route_row_count", len(component_route_rows), "current route rows", sha(canonical(component_route_rows)))
    add_metric("fragment_binding_count", len(fragment_rows), "fragment bindings", sha(custody_raw))
    add_metric("source_admin_feature_count", len(full_features), "features", sha(full_raw))
    add_metric("source_admin_simplified_feature_count", len(simplified_features), "features", sha(simplified_raw))
    add_metric("full_simplified_topological_equal_feature_count", source_product_diffs["topological_equal"], "feature pairs", sha(full_raw))
    add_metric("full_simplified_coordinate_identity_feature_count", source_product_diffs["coordinate_identity_exact"], "feature pairs", sha(simplified_raw))
    add_metric("topology_pair_count", len(topology_rows), "subject-feature pairs", sha(full_raw))
    add_metric("intersection_geometry_count", len(intersections), "non-disjoint overlay geometries", sha(full_raw))
    add_metric("worldcover_subject_year_row_count", len(worldcover), "subject-year rows", TILES[2021]["sha256"])
    add_metric("prior_472_scope_member_count", prior472_findings["scope_member_count"], "locations", sha(prior472_findings_raw))
    add_metric("prior_472_gnb_roster_count", prior472_findings["scope_country_counts"]["GNB"], "locations", sha(prior472_findings_raw))
    add_metric("prior_472_contact_assessment_count", len(prior472_contact_rows), "contact rows", sha(prior472_rows_raw))
    for key in ["old_geoboundaries_subject_count", "salb_adm2_count", "salb_autonomous_sector_count",
                "salb_regional_sector_count", "salb_regional_sector_difference_vs_2025_nc4",
                "atlas_parent_vs_overlap_candidate_consistent_rows", "atlas_parent_vs_overlap_candidate_review_rows"]:
        add_metric("prior_812_" + key, prior812_summary[key], "rows/units as named in prior #812", sha(prior812_summary_raw))
    add_metric("prior_812_contact_crosswalk_count", len(prior812_contact_rows), "contact rows", sha(prior812_rows_raw))
    for label, values, input_hash in [("full", full_precision, sha(full_raw)),
                                      ("simplified", simplified_precision, sha(simplified_raw)),
                                      ("current_contacts", contact_precision, sha(part_raw))]:
        for edge, count in values.items():
            add_metric(f"{label}_coordinate_{edge}", count, "decimal places in source coordinate tokens", input_hash)
    for (subject_kind, product, relation), count in sorted(topology_counts.items()):
        add_metric(f"topology_{subject_kind}_{product}_{relation.replace('-', '_')}_pairs", count,
                   "subject-feature pairs", sha(full_raw if product == "full" else simplified_raw))
    for row_index, row in enumerate(worldcover):
        prefix = f"wc_{row['product_year']}_{row['subject_kind']}_{row_index:03d}"
        input_hash = TILES[row["product_year"]]["sha256"]
        add_metric(prefix + "_candidate_pixel_count", row["candidate_pixel_count"], "pixel centers", input_hash)
        for code in CLASS_CODES:
            add_metric(prefix + f"_class_{code}_count", row["class_counts"][str(code)], "classified pixel centers", input_hash)
    for index, row in enumerate(contact_comparisons):
        add_metric(f"contact_{index:02d}_current_vertex_count", row["current_vertex_count"], "coordinates", sha(part_raw))
        add_metric(f"contact_{index:02d}_full_source_vertex_count", row["full_source_vertex_count"], "coordinates", sha(full_raw))
        add_metric(f"contact_{index:02d}_simplified_source_vertex_count", row["simplified_source_vertex_count"], "coordinates", sha(simplified_raw))
    metrics.sort(key=lambda x: x["id"])
    metric_ledger = {"version": 1, "metrics": metrics}

    fragment_output = io.StringIO(newline="")
    fragment_writer = csv.DictWriter(fragment_output, fieldnames=["component_id", "fragment_id", "feature_sha256"],
                                     lineterminator="\n")
    fragment_writer.writeheader()
    for row in sorted(fragment_rows, key=lambda x: (x["component_id"], x["fragment_id"])):
        fragment_writer.writerow(row)
    topology_output = io.StringIO(newline="")
    topology_fields = list(topology_rows[0])
    topology_writer = csv.DictWriter(topology_output, fieldnames=topology_fields, lineterminator="\n")
    topology_writer.writeheader()
    for row in sorted(topology_rows, key=lambda x: (x["subject_kind"], x["subject_id"], x["source_product"], x["source_feature_id"])):
        topology_writer.writerow(row)

    methods = {
        "version": 1,
        "issue": "https://github.com/ChengshuLi/WorldAtlas/issues/1416",
        "baseline_commit": BASELINE_COMMIT,
        "family_row_sha256_without_line_ending": family_hash,
        "source_product_relationship": {
            "source_id": source_id, "full_url": selected_full_url,
            "simplified_url": selected_simplified_url,
            "transformation": "source_url.replace('.geojson','_simplified.geojson'), verified against pinned scripts/administrative.py bytes",
            "full_feature_count": len(full_features), "simplified_feature_count": len(simplified_features),
            "same_feature_ids_and_names": True,
            "full_simplified_topologically_equal_feature_count": source_product_diffs["topological_equal"],
            "full_simplified_coordinate_identity_feature_count": source_product_diffs["coordinate_identity_exact"],
            "representative_year": source_metadata.get("boundaryYear"),
            "source_data_update_date": source_metadata.get("sourceDataUpdateDate"),
            "product_build_date": source_metadata.get("buildDate"),
            "declared_source": source_metadata.get("boundarySource"),
            "license": source_metadata.get("boundaryLicense"),
            "coordinate_precision_decimal_places": {"full": full_precision, "simplified": simplified_precision,
                                                       "current_contacts": contact_precision},
            "native_crs": "GeoJSON; no explicit CRS member. Interpreted as RFC 7946 WGS84 longitude/latitude; source-native production CRS and positional accuracy are not stated.",
            "limits": ["same IDs/names do not establish identical geometries", "no positional accuracy metadata", "administrative boundaries do not establish physical cause, dry land, or territorial ownership"]
        },
        "current_contact_source_comparisons": contact_comparisons,
        "prior_research_reconciliation": {
            "issue_472": {"scope_member_count": prior472_findings["scope_member_count"],
                          "gnb_scope_count": prior472_findings["scope_country_counts"]["GNB"],
                          "contact_rows": [{key: row.get(key) for key in ["subject_id","source_name","retained_name",
                              "classification","finding","source_vintage","source_license","independent_legal_boundary_check"]}
                              for row in sorted(prior472_contact_rows,key=lambda x:x["subject_id"])],
                          "reconciliation_limit":"Prior #472 records its 39-feature 2017 roster and the conflict with a cited 36-sector 2025 report; exact sector completeness remains unresolved."},
            "issue_812": {"summary": {key: prior812_summary[key] for key in ["old_geoboundaries_subject_count","salb_adm2_count",
                              "salb_autonomous_sector_count","salb_regional_sector_count","salb_regional_sector_difference_vs_2025_nc4",
                              "atlas_parent_vs_overlap_candidate_consistent_rows","atlas_parent_vs_overlap_candidate_review_rows"]},
                          "contact_rows": [{key: row.get(key) for key in ["atlas_subject_id","source_name","atlas_parent_name",
                              "salb_normalized_name_candidates","salb_top_parent_name","salb_vintage","salb_license_terms",
                              "screen_result","row_uncertainty"]}
                              for row in sorted(prior812_contact_rows,key=lambda x:x["atlas_subject_id"])],
                          "reconciliation_limit":"Prior #812 is reused for names/identity screening only. Its SALB source terms are restricted to non-commercial use; no SALB geometries or overlap percentages are reused here."}
        },
        "worldcover_sources": [
            {"year": year, **tile_records[year], "metadata": raster_meta[str(year)],
             "license": "CC-BY 4.0", "nominal_resolution": "approximately 10 m; native angular grid is 1/12000 degree",
             "limits": ["classification is a product label, not independent physical truth", "absence of classes 80/90/95 does not prove dry land", "seasonal water, tides, classification omissions, and border uncertainty remain unresolved"]}
            for year in sorted(TILES)
        ],
        "geometry_method": "Shapely/GEOS topological intersection in source longitude/latitude coordinates; no reprojection, repair, snapping, or rounding. Pair classifications are disjoint, positive-area, shared-edge, point-contact, or unresolved-invalid-input. Coordinate identity canonicalizes ring rotation/reversal and multipart ordering with exact numeric equality and zero tolerance.",
        "raster_method": "GDAL/Rasterio window reads from verified full tile bytes held in memory; geometry_mask all_touched=false samples pixel centers in the native WGS84 grid. Counts are product classifications only; 2020 V1.0.0 and 2021 V2.0.0 algorithm versions differ, so no temporal-change inference is made.",
        "legacy_observation": "The historical row is retained exactly as an observation; surface status remains unverified and the recorded parent mapping is not treated as legal authority.",
        "runtime": {"python": sys.version.split()[0], "numpy": np.__version__, "rasterio": rasterio.__version__,
                    "gdal": rasterio.__gdal_version__, "shapely": __import__("shapely").__version__,
                    "geos": __import__("shapely").geos_version_string},
        "results": {"component_count": len(components), "contact_count": len(current_contacts),
                    "fragment_binding_count": len(fragment_rows), "legacy_observation_count": len(legacy_matches),
                    "component_route_row_count": len(component_route_rows),
                    "topology_pair_count": len(topology_rows), "intersection_geometry_count": len(intersections),
                    "worldcover_subject_year_rows": len(worldcover)},
        "status": {"source_fitness": "unapproved", "physical_authority": "unapproved",
                   "geographic_approval": "not requested", "live_import": False,
                   "boundary_repair_or_assignment": False}
    }

    component_collection = {"type": "FeatureCollection", "features": [components[i] for i in all_ids]}
    contact_collection = {"type": "FeatureCollection", "features": [next(f for f in current_contacts if f["id"] == identity) for identity in contacts_ids]}
    intersection_collection = {"type": "FeatureCollection", "features": intersections}
    values = {
        "component-features.geojson": canonical(component_collection),
        "current-contacts.geojson": canonical(contact_collection),
        "fragment-bindings.csv": fragment_output.getvalue().encode(),
        "component-route-rows.json": canonical(component_route_rows),
        "topology-relations.csv": topology_output.getvalue().encode(),
        "intersection-geometries.geojson": canonical(intersection_collection),
        "worldcover-class-counts.json": canonical({"version": 1, "rows": worldcover}),
        "legacy-observation.json": canonical(scope["legacy_observation"]),
        "method-results.json": canonical(methods),
        "metric-ledger.json": canonical(metric_ledger),
    }
    total = sum(map(len, values.values()))
    if total > MAX_RUN_OUTPUT:
        raise ValueError("Complete output run exceeds its 32 MiB disk-admission cap")
    descriptors = helper.NewVintage(baseline, PACKET + "/", run_name, RUN_FILES).publish_bytes(values)
    return {"baseline": baseline, "helper": helper, "scope": scope, "quality": quality,
            "pin_files": pin_files, "descriptors": descriptors, "values": values,
            "family": family, "components": components, "contacts": current_contacts,
            "worldcover": worldcover, "raster_meta": raster_meta, "topology_rows": topology_rows,
            "intersections": intersections, "methods": methods, "metrics": metrics,
            "run_name": run_name}


def canonical_ring_control():
    polygon_a = {"type": "Polygon", "coordinates": [[[0,0],[1,0],[1,1],[0,1],[0,0]]]}
    polygon_b = {"type": "Polygon", "coordinates": [[[1,1],[1,0],[0,0],[0,1],[1,1]]]}
    if coordinate_signature(polygon_a) != coordinate_signature(polygon_b):
        raise ValueError("Exact coordinate canonicalization control failed")
    polygon_c = {"type": "Polygon", "coordinates": [[[1,1.0000000000001],[1,0],[0,0],[0,1],[1,1.0000000000001]]]}
    if coordinate_signature(polygon_a) == coordinate_signature(polygon_c):
        raise ValueError("Coordinate identity control accepted a nonzero coordinate change")


def topology_classification_control():
    from shapely.geometry import box
    subject = box(0, 0, 1, 1)
    cases = {
        "positive-area": (box(0.5, 0, 1.5, 1), "positive-area"),
        "shared-edge": (box(1, 0, 2, 1), "shared-edge"),
        "point-contact": (box(1, 1, 2, 2), "point-contact"),
        "disjoint": (box(2, 2, 3, 3), "disjoint"),
        "topological-equality": (box(0, 0, 1, 1), "positive-area"),
    }
    observed = {}
    for name, (other, expected) in cases.items():
        relation, _ = topology_relation(subject, other)
        if relation != expected:
            raise ValueError("Topological relation control failed: " + name)
        observed[name] = relation
    if not subject.equals(cases["topological-equality"][0]):
        raise ValueError("Topological equality control failed")
    canonical_ring_control()
    return observed


def expect_rejection(fn, label):
    try:
        fn()
    except (ValueError, KeyError, IndexError, FileExistsError):
        return {"case": label, "outcome": "rejected"}
    raise ValueError("Negative control was accepted: " + label)


def output_digest(repo, run_name):
    path = Path(repo) / PACKET / "vintages" / run_name
    publication = load_json((path / "publication.json").read_bytes(), "publication receipt")
    if publication.get("status") != "complete":
        raise ValueError("Run lacks a complete publication receipt")
    rows = []
    for record in publication.get("outputs", []):
        raw = (Path(repo) / record["path"]).read_bytes()
        if len(raw) != record["bytes"] or sha(raw) != record["sha256"]:
            raise ValueError("Run output differs from its complete receipt")
        rows.append({"name": Path(record["path"]).name, "bytes": len(raw), "sha256": sha(raw)})
    return sha(canonical(sorted(rows, key=lambda x: x["name"])))


def build_controls(repo, one, two, controls_name):
    baseline, helper, scope, snapshot, quality, pin_files, family_hash = baseline_and_scope(repo)
    output_paths = [f"{VINTAGE_ROOT}{controls_name}/{name}" for name in CONTROL_FILES]
    control_vintage = helper.NewVintage(baseline, PACKET + "/", controls_name, CONTROL_FILES)
    one_sha, two_sha = output_digest(repo, one), output_digest(repo, two)
    if one_sha != two_sha:
        raise ValueError("Fresh complete output runs differ")
    run_one = Path(repo) / PACKET / "vintages" / one
    run_two = Path(repo) / PACKET / "vintages" / two
    route_output = load_json((run_one / "component-route-rows.json").read_bytes(), "component route rows")
    exact_roster(scope["components"], [row.get("component") for row in route_output], "Generated current route rows")
    sentinel_before = {p.name: sha(p.read_bytes()) for p in sorted(run_one.iterdir()) if p.is_file()}
    command = [sys.executable, "-I", str(Path(__file__).resolve()), "--repo", str(repo), "--run-name", one]
    rejected_run = subprocess.run(command, cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    sentinel_after = {p.name: sha(p.read_bytes()) for p in sorted(run_one.iterdir()) if p.is_file()}
    if rejected_run.returncode == 0 or sentinel_before != sentinel_after:
        raise ValueError("Real producer entry point did not safely reject an occupied run")

    worldcover_output = load_json((run_one / "worldcover-class-counts.json").read_bytes(), "WorldCover outputs")
    rows = worldcover_output.get("rows", [])
    expected_pairs = {(kind, identity, year) for kind, identities in
                      [("component", scope["components"]), ("contact", scope["contacts"])]
                      for identity in identities for year in TILES}
    actual_pairs = {(row.get("subject_kind"), row.get("subject_id"), row.get("product_year")) for row in rows}
    if len(rows) != 98 or actual_pairs != expected_pairs:
        raise ValueError("Positive WorldCover output control has a missing/duplicate subject-year row")
    for row in rows:
        if row.get("candidate_pixel_count", 0) <= 0 or set(row.get("class_counts", {})) != {str(c) for c in CLASS_CODES}:
            raise ValueError("Positive WorldCover output control is empty or incomplete")
        if sum(row["class_counts"].values()) != row["candidate_pixel_count"]:
            raise ValueError("WorldCover class counts do not close to sampled cell centers")

    scope_ids = scope["components"]
    roster_cases = [
        expect_rejection(lambda: exact_roster(scope_ids, scope_ids[:-1], "missing member"), "omitted component"),
        expect_rejection(lambda: exact_roster(scope_ids, scope_ids + [scope_ids[0]], "duplicate member"), "duplicate component"),
        expect_rejection(lambda: exact_roster(scope_ids, scope_ids[:-1] + ["physical-component:foreign"], "foreign member"), "foreign component"),
    ]
    route_roster_cases = [
        expect_rejection(lambda: exact_roster(scope_ids, scope_ids[:-1], "route row omitted"), "omitted current route row"),
        expect_rejection(lambda: exact_roster(scope_ids, scope_ids + [scope_ids[0]], "route duplicate"), "duplicate current route row"),
        expect_rejection(lambda: exact_roster(scope_ids, scope_ids[:-1] + ["physical-component:foreign"], "route foreign"), "foreign current route row"),
    ]
    contact_roster_cases = [
        expect_rejection(lambda: exact_roster(scope["contacts"], scope["contacts"][:-1], "contact missing"), "missing contact join"),
        expect_rejection(lambda: exact_roster(scope["contacts"], scope["contacts"] + [scope["contacts"][0]], "contact duplicate"), "duplicate contact join"),
    ]
    tile_raw = (Path(repo) / TILES[2021]["path"]).read_bytes()
    if len(tile_raw) != TILES[2021]["bytes"] or sha(tile_raw) != TILES[2021]["sha256"]:
        raise ValueError("Control WorldCover input no longer matches its source pin")
    baseline.admit("control-source:" + TILES[2021]["path"], len(tile_raw))
    source_case = expect_rejection(lambda: verify_hash(tile_raw[:-1] + bytes([tile_raw[-1] ^ 1]),
                                                       TILES[2021]["sha256"], "mutated WorldCover source"),
                                   "one-byte source mutation")
    _, contact_raw = pinned(baseline, "current.gnb_contact_part", pin_files)
    contact_features = load_json(contact_raw, "pinned current contact part")["features"]
    actual_contacts = [f for f in contact_features if f.get("id") in set(scope["contacts"])]
    _, full_raw = pinned(baseline, "source_corpus.gnb_full_product", pin_files)
    source_features = load_json(full_raw, "pinned full source")["features"]
    joined_ids = [f.get("properties", {}).get("metadata", {}).get("original_id") for f in actual_contacts]
    source_by_id = feature_map(source_features, "shapeID", "pinned full source")
    if len(joined_ids) != 4 or any(identity not in source_by_id for identity in joined_ids):
        raise ValueError("Independent contact-to-source positive join failed")
    missing_source_case = expect_rejection(lambda: assert_contacts(actual_contacts,
        [f for f in source_features if f["properties"].get("shapeID") != joined_ids[0]]),
        "missing actual contact source feature")
    duplicate_source_case = expect_rejection(lambda: feature_map(source_features + [source_features[0]],
        "shapeID", "duplicate source feature"), "duplicate source feature identity")
    base_meta = {"crs":"EPSG:4326","width":36000,"height":36000,"bounds":[-18.0,9.0,-15.0,12.0],
                 "pixel_size":[1/12000,-1/12000],"product_tile":"N09W018","product_version":"V2.0.0",
                 "algorithm_version":"V2.0.0","time_start":"2021-01-01T00:00:00Z","time_end":"2021-12-31T23:59:59Z"}
    raster_cases=[]
    for field, value, label in [("crs","EPSG:3857","altered CRS"),
                                ("pixel_size",[1/6000,-1/6000],"altered pixel scale"),
                                ("time_start","2020-01-01T00:00:00Z","altered epoch"),
                                ("bounds",[-17.0,9.0,-14.0,12.0],"altered tile origin")]:
        altered=dict(base_meta); altered[field]=value
        raster_cases.append(expect_rejection(lambda altered=altered: validate_raster_metadata(altered,2021),label))
    fixture_counts = class_counts(np.array([80,90,95,10,0], dtype=np.uint8))
    if any(fixture_counts[str(code)] != 1 for code in [0,10,80,90,95]):
        raise ValueError("Positive classification-count control failed")
    topology_cases = topology_classification_control()
    pixel_positive = {"method_id":"worldcover-pixel-center-screen", "kind":"positive-control", "outcome":"passed",
                      "actual_subject_year_rows":len(rows), "occupied_entry_rejected":True,
                      "observation":"All 49 subjects have one nonempty, class-count-closed row for each authenticated W018 year tile."}
    pixel_negative = {"method_id":"worldcover-pixel-center-screen", "kind":"negative-control", "outcome":"passed",
                      "altered_inputs_rejected":raster_cases+[source_case],
                      "nonvacuous_class_count_fixture":fixture_counts,
                      "nonvacuous_case":"The fixture contains classes 80/90/95, another class, and no-data, each counted exactly."}
    packet_positive = {"method_id":"bounded-geometry-packet", "kind":"positive-control", "outcome":"passed",
                       "accepted_components":45, "accepted_route_rows":len(route_output), "accepted_contacts":4,
                       "fragment_bindings":len(parse_csv((run_one / "fragment-bindings.csv").read_bytes())),
                       "geometry_cases":topology_cases, "exact_coordinate_identity":"ring rotation/reversal and multipart ordering canonicalized; any coordinate delta is rejected"}
    packet_negative = {"method_id":"bounded-geometry-packet", "kind":"negative-control", "outcome":"passed",
                       "rejected_scope_mutations":roster_cases,
                       "rejected_route_row_mutations":route_roster_cases,
                       "rejected_contact_join_mutations":contact_roster_cases+[missing_source_case,duplicate_source_case],
                       "rejected_source_byte_mutation":source_case, "rejected_raster_metadata_mutations":raster_cases,
                       "occupied_run_entrypoint_exit":rejected_run.returncode,
                       "occupied_run_files_unchanged":sentinel_before==sentinel_after}
    reproducibility = {"method_id":"bounded-geometry-packet", "kind":"reproducibility", "outcome":"passed",
                       "run_one_sha256":one_sha, "run_two_sha256":two_sha,
                       "run_one":one, "run_two":two,
                       "file_inventory":"all published files in each complete NewVintage receipt, excluding only path-dependent publication receipts"}
    values = {
        CONTROL_FILES[0]: canonical(pixel_positive), CONTROL_FILES[1]: canonical(pixel_negative),
        CONTROL_FILES[2]: canonical(packet_positive), CONTROL_FILES[3]: canonical(packet_negative),
        CONTROL_FILES[4]: canonical(reproducibility),
    }
    if sum(map(len, values.values())) > 1024 * 1024:
        raise ValueError("Control receipt set exceeds its 1 MiB disk-admission cap")
    return control_vintage.publish_bytes(values)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--run-name")
    parser.add_argument("--controls", action="store_true")
    parser.add_argument("--run-one")
    parser.add_argument("--run-two")
    parser.add_argument("--controls-name", default="validation-controls-v1")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    if args.controls:
        if not args.run_one or not args.run_two:
            parser.error("--controls requires --run-one and --run-two")
        records = build_controls(repo, args.run_one, args.run_two, args.controls_name)
        print(json.dumps({"status":"complete", "outputs":records}, sort_keys=True))
        return
    if not args.run_name or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", args.run_name):
        parser.error("--run-name must be a fresh lowercase safe identifier")
    result = build_outputs(repo, args.run_name)
    print(json.dumps({"status":"complete", "run_name":args.run_name,
                      "outputs":result["descriptors"], "output_bytes":sum(map(len,result["values"].values())),
                      "metrics":len(result["metrics"]), "topology_rows":len(result["topology_rows"]),
                      "intersection_geometries":len(result["intersections"])}, sort_keys=True))


if __name__ == "__main__":
    main()
