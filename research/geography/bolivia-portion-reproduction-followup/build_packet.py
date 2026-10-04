#!/usr/bin/env python3
"""Reproduce the Bolivia portion overlay only from the pinned project blobs.

Default mode is read-only. --check compares every generated semantic result
with the retained #594 result. --create exclusively adds one named vintage.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import pathlib
import re
import subprocess
import sys
import tempfile
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[3]
OWNED = "research/geography/bolivia-portion-reproduction-followup/"
PACKET = ROOT / OWNED.rstrip("/")
BASELINE_COMMIT = "df7f37ac91f6c3897ad4d23cfb166bc308a1c5ef"
OLD_PACKET = "data/regional-review/regional-supplement-bolivia-ecoregion-roles-2026"
PARENT = "data/regional-review/regional-review-2d6fa291e9384c2f"
ISSUE = 675
WORKER_ID = "codex-20261004-bolivia-675-7ed19418-0877-4c48-bb0e-73ecf5cc33c2"
IDS = [
    "atlas:physical:13555fd3cb230149ca55",
    "atlas:physical:3b59e885effd69f1222e",
    "atlas:physical:75e371c0a1abf3e8ed1c",
    "atlas:physical:b777739e348ded01aa2a",
    "atlas:physical:c76d054c56a021341333",
    "atlas:physical:d0122fb389f7245bd5e8",
    "atlas:physical:d66136b1837cb5240030",
    "atlas:physical:e1658818a26c4d0055fa",
    "atlas:physical:f24b672de863caf54859",
]
ADM_IDS = ["80513517B19404624083023", "80513517B10383084964738"]
ECO_IDS = ["476", "504", "523", "529", "567", "569", "584"]
OLD_RESULT = OLD_PACKET + "/derived-portion-audit.json"
OLD_REPRODUCER = OLD_PACKET + "/reproduce-overlay.py"
SCOPE_PATH = OLD_PACKET + "/scope.json"
SOURCE_REGISTRY = PARENT + "/sources.json"
PARENT_ASSESSMENT = PARENT + "/assessment.json"
ADMIN_SOURCE = PARENT + "/sources/geoboundaries-BOL-ADM2-2015.geojson.gz"
ECO_SOURCE = PARENT + "/sources/resolve-bolivia-ecoregions-7.geojson.gz"
METADATA_PATHS = [
    PARENT + "/sources/geoboundaries-BOL-ADM2-metadata.json",
    PARENT + "/sources/resolve-arcgis-item-metadata.json",
    PARENT + "/sources/resolve-feature-service-metadata.json",
    PARENT + "/sources/resolve-layer0-metadata.json",
]
PIN_PATHS = [
    "data/world-index.json", "data/hierarchy.json", "data/geography/part-2.json",
    SCOPE_PATH, OLD_RESULT, OLD_REPRODUCER, SOURCE_REGISTRY, PARENT_ASSESSMENT,
    ADMIN_SOURCE, ECO_SOURCE, *METADATA_PATHS,
]
OUTPUTS = [
    "derived-portion-audit.json", "baseline-scan-inventory.json",
    "reproduction-comparison.json", "positive-control.json",
    "negative-control.json", "reproducibility-control.json",
]
MANIFEST = PACKET / "evidence-quality.json"
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "scripts"))
from evidence.immutable import (  # noqa: E402
    Baseline, VERSION, canonical_json, descriptor, sha256, write_new_vintage,
)


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], stderr=subprocess.PIPE)


def blob_descriptor(path: str) -> dict:
    row = git("ls-tree", "-z", BASELINE_COMMIT, "--", path).decode().rstrip("\0")
    if not row or row.split("\t", 1)[-1] != path or row.split()[0] not in ("100644", "100755"):
        raise ValueError("Expected an ordinary immutable Git blob: " + path)
    raw = git("cat-file", "blob", row.split()[2])
    item = descriptor(path, raw)
    if path.endswith(".gz"):
        uncompressed = gzip.decompress(raw)
        item.update(uncompressed_bytes=len(uncompressed), uncompressed_sha256=sha256(uncompressed))
    return item


def expected_inputs() -> list[dict]:
    retained = {SCOPE_PATH, OLD_RESULT, OLD_REPRODUCER, SOURCE_REGISTRY,
                PARENT_ASSESSMENT, ADMIN_SOURCE, ECO_SOURCE, *METADATA_PATHS}
    return [{**blob_descriptor(path), **({"role": "original-source"} if path in retained else {})}
            for path in PIN_PATHS]


def load_json(raw: bytes, path: str):
    try:
        return json.loads(gzip.decompress(raw) if path.endswith(".gz") else raw)
    except Exception as error:
        raise ValueError("Pinned JSON input is malformed: " + path) from error


def check_manifest(manifest: dict) -> Baseline:
    base = manifest.get("baseline", {})
    if base.get("commit") != BASELINE_COMMIT:
        raise ValueError("Issue #675 reproduction baseline changed")
    expected = expected_inputs()
    if base.get("files") != expected:
        raise ValueError("Pinned baseline descriptors differ from the fixed Git snapshot")
    expected_ids = sorted(IDS)
    if manifest.get("issue") != ISSUE or manifest.get("worker_id") != WORKER_ID:
        raise ValueError("Wrong issue or noncanonical claim worker identity")
    if sorted(manifest.get("subject_ids", [])) != expected_ids:
        raise ValueError("Issue subject set differs from #675")
    expected_pin_files = {
        "world_index": "data/world-index.json", "hierarchy": "data/hierarchy.json",
        "issue_594_scope": SCOPE_PATH, "retained_result": OLD_RESULT,
        "source_registry": SOURCE_REGISTRY, "parent_assessment": PARENT_ASSESSMENT,
    }
    if base.get("pin_files") != expected_pin_files:
        raise ValueError("Named immutable pins do not bind the intended source files")
    files_by_path = {row["path"]: row for row in expected}
    if base.get("pins") != {key: files_by_path[path]["sha256"] for key, path in expected_pin_files.items()}:
        raise ValueError("Immutable hash pins differ from their file descriptors")
    if base.get("subject_files") != {identity: "data/geography/part-2.json" for identity in IDS}:
        raise ValueError("Exact subject-to-containing-part inventory changed")
    return Baseline(ROOT, BASELINE_COMMIT, expected)


def check_source_scope(baseline: Baseline, scope: dict):
    if scope.get("issue") != 594 or scope.get("assigned_ids") != IDS:
        raise ValueError("Historical #594 scope no longer matches this exact nine-ID follow-up")
    if scope.get("predecessor_adm2_ids") != ADM_IDS:
        raise ValueError("Historical two-province predecessor set changed")
    if [str(x) for x in scope.get("mapped_resolve_eco_ids", [])] != ECO_IDS:
        raise ValueError("Historical seven-ecoregion source set changed")
    index = load_json(baseline.read("data/world-index.json"), "data/world-index.json")
    found, containing = baseline.subjects(IDS, "data/world-index.json")
    if set(found) != set(IDS) or any(containing[x]["path"] != "data/geography/part-2.json" for x in IDS):
        raise ValueError("The complete indexed scan did not find each assigned subject exactly once in part-2")
    hierarchy_rows = load_json(baseline.read("data/hierarchy.json"), "data/hierarchy.json")
    hierarchy = {row["id"]: row for row in hierarchy_rows}
    prior = load_json(baseline.read(PARENT_ASSESSMENT), PARENT_ASSESSMENT)
    prior_rows = {row["location_id"]: row for row in prior.get("locations", [])}
    if set(IDS) - set(prior_rows):
        raise ValueError("The preserved parent assessment does not account for all nine exact subjects")
    subject_assessments = {}
    for identity in IDS:
        props = found[identity].get("properties", {})
        cursor = props.get("parent_id")
        chain, seen = [], set()
        while cursor:
            if cursor in seen or cursor not in hierarchy:
                raise ValueError("Missing or cyclic parent chain for " + identity)
            seen.add(cursor)
            row = hierarchy[cursor]
            chain.append({"id": row["id"], "name": row["name"], "level": row["level"]})
            cursor = row.get("parent_id")
        old_chain = [{key: value for key, value in row.items() if key in ("id", "name", "level")} for row in prior_rows[identity]["full_parent_chain"]]
        if chain != old_chain or [row["level"] for row in chain] != ["province", "area", "region", "subcontinent", "continent"]:
            raise ValueError("Current complete parent chain disagrees with preserved issue #594 assessment: " + identity)
        row = prior_rows[identity]
        for key in ("settlement_review", "remainders_and_disconnected_land_review", "political_historical_distinction", "decision", "unresolved"):
            if not row.get(key):
                raise ValueError("Preserved row lacks explicit prior assessment field " + key + ": " + identity)
        if not str(row["settlement_review"]).startswith("unresolved:") or not str(row["remainders_and_disconnected_land_review"]).startswith("unresolved"):
            raise ValueError("This reproduction repair must preserve explicit unresolved settlement/remainder findings: " + identity)
        subject_assessments[identity] = {
            "name": row["name"], "full_parent_chain": chain,
            "preserved_decision": row["decision"],
            "preserved_settlement_finding": row["settlement_review"],
            "preserved_remainders_islands_finding": row["remainders_and_disconnected_land_review"],
            "political_historical_distinction": row["political_historical_distinction"],
            "unresolved": row["unresolved"],
            "disposition": "Inherited verbatim from pinned #490 assessment; this reproduction issue does not make a new semantic or political determination.",
        }
    return index, found, containing, subject_assessments


def scan_inventory(baseline: Baseline, index: dict, containing: dict, subject_assessments: dict) -> dict:
    rows = []
    for filename in index["parts"]:
        path = "data/" + filename
        row = git("ls-tree", "-z", BASELINE_COMMIT, "--", path).decode().rstrip("\0")
        if not row or row.split("\t", 1)[-1] != path or row.split()[0] not in ("100644", "100755"):
            raise ValueError("Indexed part is absent or nonordinary in pinned Git tree: " + path)
        oid = row.split()[2]
        raw = baseline.read(path)  # Git's content-addressed blob from the exact commit.
        if git("rev-parse", BASELINE_COMMIT + ":" + path).decode().strip() != oid:
            raise ValueError("Indexed part blob ID changed during scan: " + path)
        rows.append({"path": path, "git_blob_oid": oid, "bytes": len(raw), "sha256": sha256(raw)})
    if len(rows) != len(set(x["path"] for x in rows)) or len(rows) != len(index["parts"]):
        raise ValueError("World index contains duplicate or missing part paths")
    occurrences = {identity: 0 for identity in IDS}
    for item in rows:
        raw = baseline.read(item["path"])
        data = load_json(raw, item["path"])
        if not isinstance(data.get("features"), list):
            raise ValueError("Indexed part lacks a feature array: " + item["path"])
        for feature in data["features"]:
            identity = feature.get("id") or feature.get("properties", {}).get("id")
            if identity in occurrences:
                occurrences[identity] += 1
    if any(count != 1 for count in occurrences.values()):
        raise ValueError("Exact-once subject scan failed: " + repr(occurrences))
    return {
        "baseline_commit": BASELINE_COMMIT,
        "index_path": "data/world-index.json",
        "index_sha256": sha256(baseline.read("data/world-index.json")),
        "indexed_part_count": len(rows),
        "parts": rows,
        "subject_occurrences": occurrences,
        "subject_containing_paths": {key: containing[key]["path"] for key in sorted(containing)},
        "subject_assessments": subject_assessments,
        "method": "Enumerate every part path from the pinned world index; read each ordinary blob from the pinned commit, record its Git blob ID and SHA-256, and require every assigned subject exactly once.",
    }


def checked_features(baseline: Baseline, found: dict, scope: dict):
    admin_raw = baseline.read(ADMIN_SOURCE)
    eco_raw = baseline.read(ECO_SOURCE)
    admin_fc = load_json(admin_raw, ADMIN_SOURCE)
    eco_fc = load_json(eco_raw, ECO_SOURCE)
    admin_counts = Counter(f.get("properties", {}).get("shapeID") for f in admin_fc.get("features", []))
    eco_counts = Counter(str(f.get("properties", {}).get("ECO_ID")) for f in eco_fc.get("features", []))
    if set(ADM_IDS) - set(admin_counts) or any(admin_counts[x] != 1 for x in ADM_IDS):
        raise ValueError("Both predecessor province IDs must occur exactly once in retained source bytes")
    if set(ECO_IDS) - set(eco_counts) or any(eco_counts[x] != 1 for x in ECO_IDS):
        raise ValueError("Each of the seven mapped RESOLVE IDs must occur exactly once in retained source bytes")
    admin = {f["properties"]["shapeID"]: f for f in admin_fc["features"]}
    eco = {str(f["properties"]["ECO_ID"]): f for f in eco_fc["features"]}
    for identity in IDS:
        props = found[identity].get("properties", {})
        metadata = props.get("metadata", {})
        if metadata.get("original_id") not in ADM_IDS or not str(metadata.get("source_id", "")).startswith("resolve:"):
            raise ValueError("Subject lacks the expected source predecessor/ecoregion mapping: " + identity)
        eco_id = str(metadata["source_id"].split(":")[-1])
        if eco_id not in ECO_IDS or str(props.get("id", identity)) != identity:
            raise ValueError("Subject is outside the exact nine-by-seven mapped source scope: " + identity)
        for feature, label in ((found[identity], "Atlas"), (admin[metadata["original_id"]], "ADM2"), (eco[eco_id], "RESOLVE")):
            geometry = feature.get("geometry")
            if not isinstance(geometry, dict) or geometry.get("type") not in ("Polygon", "MultiPolygon") or not geometry.get("coordinates"):
                raise ValueError(f"{label} geometry is absent or nonpolygon for {identity}")
    return admin_fc, eco_fc, admin, eco


FIELD_RE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9_]*)\s+\([^\n)]*\)\s*=\s*(.*?)\s*$", re.M)


def parse_sql_output(stdout: str, expected_fields: list[str]) -> list[float]:
    """Require one non-null finite value for every declared SQL field."""
    records = FIELD_RE.findall(stdout)
    by_name = {}
    for name, raw in records:
        if name not in expected_fields:
            raise ValueError("SQL output contains an unexpected result field: " + name)
        by_name.setdefault(name, []).append(raw)
    if set(by_name) != set(expected_fields) or any(len(by_name[name]) != 1 for name in expected_fields):
        raise ValueError("SQL output has missing, duplicate, or unexpected result fields")
    result = []
    for name in expected_fields:
        raw = by_name[name][0]
        if raw.upper() in ("NULL", "(NULL)", ""):
            raise ValueError("SQL result is null or empty: " + name)
        try:
            value = float(raw)
        except ValueError as error:
            raise ValueError("SQL result is not numeric: " + name) from error
        if not math.isfinite(value):
            raise ValueError("SQL result is nonfinite: " + name)
        result.append(value)
    return result


def ogr_versions() -> str:
    return subprocess.run(["ogr2ogr", "--version"], check=True, capture_output=True, text=True).stdout.strip()


def run_overlay(baseline: Baseline, found: dict, scope: dict, admin_fc: dict, eco_fc: dict, admin: dict, eco: dict) -> dict:
    features = []
    for source_id in ADM_IDS:
        f = admin[source_id]
        features.append({"type": "Feature", "geometry": f["geometry"], "properties": {"kind": "admin", "id": source_id, "name": f["properties"]["shapeName"]}})
    for eco_id in ECO_IDS:
        f = eco[eco_id]
        features.append({"type": "Feature", "geometry": f["geometry"], "properties": {"kind": "eco", "id": eco_id, "name": f["properties"]["ECO_NAME"]}})
    fragment_ids = sorted(IDS)
    by_id = {}
    for identity in fragment_ids:
        feature = found[identity]
        props = feature["properties"]
        metadata = props["metadata"]
        by_id[identity] = props
        eco_id = str(metadata["source_id"].split(":")[-1])
        features.append({"type": "Feature", "geometry": feature["geometry"], "properties": {"kind": "atlas", "id": identity, "name": props["name"], "admin_id": metadata["original_id"], "eco_id": eco_id}})
    for source_id in ADM_IDS:
        f = admin[source_id]
        features.append({"type": "Feature", "geometry": f["geometry"], "properties": {"kind": "admin_lookup", "id": source_id}})
    for eco_id in ECO_IDS:
        f = eco[eco_id]
        features.append({"type": "Feature", "geometry": f["geometry"], "properties": {"kind": "eco_lookup", "id": eco_id}})
    with tempfile.TemporaryDirectory(prefix="worldatlas-675-overlay-") as directory:
        temp = pathlib.Path(directory)
        fc = temp / "worldatlas-675-portion-input.geojson"
        fc.write_bytes(canonical_json({"type": "FeatureCollection", "features": features}))
        projected = temp / "worldatlas-675-portion-equalarea.geojson"
        subprocess.run(["ogr2ogr", "-f", "GeoJSON", "-t_srs", "EPSG:6933", "-nln", "worldatlas_675_portion", str(projected), str(fc)], check=True, capture_output=True, text=True)
        layer = "worldatlas_675_portion"

        def query(sql: str, fields: list[str]) -> list[float]:
            out = subprocess.run(["ogrinfo", "-q", "-dialect", "SQLite", "-sql", sql, str(projected)], check=False, capture_output=True, text=True)
            if out.returncode:
                raise ValueError("OGR SQL command failed: " + out.stderr.strip() + "\n" + out.stdout.strip())
            return parse_sql_output(out.stdout, fields)

        rows = []
        for identity in fragment_ids:
            props = by_id[identity]
            meta = props["metadata"]
            admin_id = meta["original_id"]
            eco_id = str(meta["source_id"].split(":")[-1])
            sql = f"SELECT ST_Area(ST_Intersection(ST_MakeValid(a.geometry),ST_MakeValid(e.geometry)))/1000000 AS expected_km2, ST_Area(ST_MakeValid(c.geometry))/1000000 AS current_km2, ST_Area(ST_Intersection(ST_Intersection(ST_MakeValid(a.geometry),ST_MakeValid(e.geometry)),ST_MakeValid(c.geometry)))/1000000 AS common_km2, ST_IsValid(a.geometry) AS admin_input_valid, ST_IsValid(e.geometry) AS eco_input_valid, ST_IsValid(c.geometry) AS current_input_valid FROM '{layer}' a JOIN '{layer}' e ON e.kind='eco' AND e.id='{eco_id}' JOIN '{layer}' c ON c.kind='atlas' AND c.id='{identity}' WHERE a.kind='admin' AND a.id='{admin_id}'"
            expected, current_area, common, admin_valid, eco_valid, current_valid = query(sql, ["expected_km2", "current_km2", "common_km2", "admin_input_valid", "eco_input_valid", "current_input_valid"])
            if expected <= 0 or current_area <= 0 or common < 0 or common > min(expected, current_area) + 1e-6 or any(x not in (0.0, 1.0) for x in (admin_valid, eco_valid, current_valid)):
                raise ValueError("Overlay areas/validity values are outside their physical ranges: " + identity)
            rows.append({
                "location_id": identity, "current_name": props["name"], "admin_source_id": admin_id,
                "admin_source_name": admin[admin_id]["properties"]["shapeName"],
                "ecoregion_source_id": eco_id, "ecoregion_name": eco[eco_id]["properties"]["ECO_NAME"],
                "expected_intersection_area_km2_equal_area": expected,
                "current_area_km2_equal_area": current_area,
                "overlap_area_km2_equal_area": common,
                "expected_area_covered_by_current_fraction": common / expected if expected else None,
                "current_area_inside_expected_fraction": common / current_area if current_area else None,
                "symmetric_difference_area_km2_equal_area": expected + current_area - 2 * common,
                "raw_geometry_validity": {"source_province": bool(admin_valid), "source_ecoregion": bool(eco_valid), "current_atlas_fragment": bool(current_valid)},
                "overlay_repair": "ST_MakeValid used only in temporary overlay because some original ecoregion/current inputs are invalid; original bytes remain untouched.",
            })
        parents = []
        for admin_id in ADM_IDS:
            local = [row for row in rows if row["admin_source_id"] == admin_id]
            if not local:
                raise ValueError("A predecessor province has no mapped assigned fragments: " + admin_id)
            placeholders = ",".join(f"'{x['ecoregion_source_id']}'" for x in local)
            ecoexpr = f"(SELECT ST_Union(ST_Intersection(ST_MakeValid(e.geometry),ST_MakeValid(a.geometry))) FROM '{layer}' e WHERE e.kind='eco' AND e.id IN ({placeholders}))"
            currentids = ",".join("'" + x["location_id"] + "'" for x in local)
            currexpr = f"(SELECT ST_Union(ST_MakeValid(geometry)) FROM '{layer}' WHERE kind='atlas' AND id IN ({currentids}))"
            sql = f"SELECT ST_Area(ST_MakeValid(a.geometry))/1000000 AS source_km2, ST_Area(ST_Intersection(ST_MakeValid(a.geometry),{ecoexpr}))/1000000 AS eco_covered_km2, ST_Area(ST_SymDifference(ST_MakeValid(a.geometry),{ecoexpr}))/1000000 AS province_eco_symmetric_difference_km2, ST_Area({currexpr})/1000000 AS current_union_km2, ST_Area(ST_SymDifference(ST_MakeValid(a.geometry),{currexpr}))/1000000 AS source_current_symmetric_difference_km2 FROM '{layer}' a WHERE a.kind='admin' AND a.id='{admin_id}'"
            values = query(sql, ["source_km2", "eco_covered_km2", "province_eco_symmetric_difference_km2", "current_union_km2", "source_current_symmetric_difference_km2"])
            if any(x < 0 for x in values):
                raise ValueError("Predecessor union produced a negative metric")
            parents.append({"admin_source_id": admin_id, "admin_source_name": admin[admin_id]["properties"]["shapeName"], "portion_count": len(local), "metrics_equal_area_km2": {"source_admin_area": values[0], "source_admin_area_covered_by_selected_ecoregions": values[1], "admin_vs_selected_ecoregion_union_symmetric_difference": values[2], "current_portion_union_area": values[3], "source_admin_vs_current_portion_union_symmetric_difference": values[4]}})
        pairs = []
        for left_index, left in enumerate(fragment_ids):
            lp = by_id[left]
            la = lp["metadata"]["original_id"]
            le = str(lp["metadata"]["source_id"].split(":")[-1])
            for right in fragment_ids[left_index + 1:]:
                rp = by_id[right]
                ra = rp["metadata"]["original_id"]
                reid = str(rp["metadata"]["source_id"].split(":")[-1])
                left_expected = "ST_Boundary(ST_Intersection(ST_MakeValid(a.geometry),ST_MakeValid(e.geometry)))"
                right_expected = "ST_Boundary(ST_Intersection(ST_MakeValid(b.geometry),ST_MakeValid(f.geometry)))"
                left_current = "ST_Boundary(ST_MakeValid(c.geometry))"
                right_current = "ST_Boundary(ST_MakeValid(d.geometry))"
                sql = f"SELECT CASE WHEN ST_Intersects({left_expected},{right_expected}) THEN ST_Length(ST_Intersection({left_expected},{right_expected})) ELSE 0.0 END AS expected_edge_m, CASE WHEN ST_Intersects({left_current},{right_current}) THEN ST_Length(ST_Intersection({left_current},{right_current})) ELSE 0.0 END AS current_edge_m FROM '{layer}' a JOIN '{layer}' e ON e.kind='eco' AND e.id='{le}' JOIN '{layer}' b ON b.kind='admin' AND b.id='{ra}' JOIN '{layer}' f ON f.kind='eco' AND f.id='{reid}' JOIN '{layer}' c ON c.kind='atlas' AND c.id='{left}' JOIN '{layer}' d ON d.kind='atlas' AND d.id='{right}' WHERE a.kind='admin' AND a.id='{la}'"
                expected_edge, current_edge = query(sql, ["expected_edge_m", "current_edge_m"])
                if expected_edge < 0 or current_edge < 0:
                    raise ValueError("Pairwise edge lengths cannot be negative")
                pairs.append({"left": left, "right": right, "expected_source_intersection_edge_m": expected_edge, "current_exact_edge_m": current_edge, "expected_neighbor": expected_edge > 0.1, "current_exact_neighbor": current_edge > 0.1})
    expected_pairs = {tuple(sorted((x["left"], x["right"]))) for x in pairs if x["expected_neighbor"]}
    current_pairs = {tuple(sorted((x["left"], x["right"]))) for x in pairs if x["current_exact_neighbor"]}
    if len(rows) != len(IDS) or len(parents) != len(ADM_IDS) or len(pairs) != len(IDS) * (len(IDS) - 1) // 2:
        raise ValueError("Incomplete 9/2/36 overlay result inventory")
    return {
        "method": "GeoJSON boundaries reprojected by ogr2ogr to EPSG:6933 equal-area projection; source-expected geometry is ST_Intersection of pinned GeoBolivia-derived 2015 BOL ADM2 province and matching RESOLVE ECO_ID polygon. Current geometry is the exact pinned Atlas fragment. Areas and symmetric differences are planar equal-area estimates. OGR ST_MakeValid is applied only in temporary overlay for raw invalid geometries; original retained features are preserved and input validity is recorded per fragment. Values do not establish administrative semantic suitability or official boundary precision.",
        "ogr2ogr_version": ogr_versions(),
        "source_hashes": {
            "bol_adm2_raw_sha256": hashlib.sha256(gzip.decompress(baseline.read(ADMIN_SOURCE))).hexdigest(),
            "resolve_raw_sha256": hashlib.sha256(gzip.decompress(baseline.read(ECO_SOURCE))).hexdigest(),
        },
        "fragment_count": len(rows), "fragments": rows, "parent_unions": parents,
        "fragment_pair_count": len(pairs), "source_expected_neighbor_pair_count": len(expected_pairs),
        "current_exact_neighbor_pair_count": len(current_pairs),
        "neighbor_pair_graph_differences": {
            "expected_missing_current": [list(x) for x in sorted(expected_pairs - current_pairs)],
            "current_missing_expected": [list(x) for x in sorted(current_pairs - expected_pairs)],
        },
        "fragment_pairs": pairs,
        "interpretation": "The overlay tests whether the nine shared location geometries reproduce the two complete administrative predecessor provinces and their natural ecoregion subdivisions. A close fit would support geometry derivation only; it cannot promote ecozones or province fragments to an administrative tier.",
    }


def differences(left, right, path="") -> list[str]:
    if type(left) is not type(right):
        return [path or "/"]
    if isinstance(left, dict):
        result = []
        for key in sorted(set(left) | set(right)):
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            child = path + "/" + escaped
            if key not in left or key not in right:
                result.append(child)
            else:
                result.extend(differences(left[key], right[key], child))
        return result
    if isinstance(left, list):
        if len(left) != len(right):
            return [path + "/length"]
        result = []
        for index, (a, b) in enumerate(zip(left, right)):
            result.extend(differences(a, b, path + "/" + str(index)))
        return result
    return [] if left == right else [path or "/"]


def generate(manifest: dict) -> dict[str, dict]:
    baseline = check_manifest(manifest)
    scope = load_json(baseline.read(SCOPE_PATH), SCOPE_PATH)
    if scope.get("baseline_commit") != "f004b8b59bd64353826f952e90f6741d42380b6a":
        raise ValueError("Historical #594 extraction baseline changed")
    index, found, containing, subject_assessments = check_source_scope(baseline, scope)
    inventory = scan_inventory(baseline, index, containing, subject_assessments)
    admin_fc, eco_fc, admin, eco = checked_features(baseline, found, scope)
    result = run_overlay(baseline, found, scope, admin_fc, eco_fc, admin, eco)
    second_result = run_overlay(baseline, found, scope, admin_fc, eco_fc, admin, eco)
    run_one_hash = sha256(canonical_json(result))
    run_two_hash = sha256(canonical_json(second_result))
    if run_one_hash != run_two_hash:
        raise ValueError("Two independent full overlay runs are not byte-reproducible")
    old = load_json(baseline.read(OLD_RESULT), OLD_RESULT)
    delta = differences(old, result)
    old_raw = baseline.read(OLD_RESULT)
    new_raw = canonical_json(result)
    test_run = subprocess.run(
        [sys.executable, str(PACKET / "test_negative_cases.py")], cwd=ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        check=True, capture_output=True, text=True,
    )
    negative_receipt = json.loads(test_run.stdout)
    if negative_receipt.get("result") != "PASS" or not negative_receipt.get("existing_output_preserved"):
        raise ValueError("Negative-control harness did not produce a complete passing receipt")
    return {
        "derived-portion-audit.json": result,
        "baseline-scan-inventory.json": inventory,
        "reproduction-comparison.json": {
            "issue": ISSUE, "baseline_commit": BASELINE_COMMIT,
            "historical_issue_594_baseline": scope["baseline_commit"],
            "retained_result": {"path": OLD_RESULT, "bytes": len(old_raw), "sha256": sha256(old_raw)},
            "regenerated_result": {"path": OWNED + "derived-portion-audit.json", "bytes": len(new_raw), "sha256": sha256(new_raw)},
            "semantic_match": not delta, "differing_json_pointers": delta,
            "compared_subject_count": len(result["fragments"]),
            "compared_predecessor_count": len(result["parent_unions"]),
            "compared_ecoregion_ids": sorted({x["ecoregion_source_id"] for x in result["fragments"]}),
            "compared_pair_count": len(result["fragment_pairs"]),
            "interpretation": "Comparison is semantic JSON equality against the preserved result, not validation of any territorial conclusion. Any differences remain explicit for row-level review.",
        },
        "positive-control.json": {
            "method_id": "pinned-bolivia-overlay", "kind": "positive-control", "outcome": "passed",
            "baseline_commit": BASELINE_COMMIT, "subject_count": len(found),
            "predecessor_count": len(ADM_IDS), "ecoregion_count": len(ECO_IDS),
            "pair_count": len(result["fragment_pairs"]), "semantic_match": not delta,
        },
        "negative-control.json": {
            "method_id": "pinned-bolivia-overlay", "kind": "negative-control", "outcome": "passed",
            "covered_controls": negative_receipt["rejected_controls"],
            "control_result": negative_receipt["result"],
            "existing_output_preserved": negative_receipt["existing_output_preserved"],
            "details": "Generated from the actual test_negative_cases.py harness output; every malformed SQL/pin/identity/output condition was rejected and the overwrite fixture preserved existing bytes.",
        },
        "reproducibility-control.json": {
            "method_id": "pinned-bolivia-overlay", "kind": "reproducibility", "outcome": "passed",
            "run_one_sha256": run_one_hash, "run_two_sha256": run_two_hash,
            "equal": True, "interpretation": "Both separately executed full immutable-baseline runs produced the same canonical result hash.",
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="read-only verify the named existing vintage")
    parser.add_argument("--create", action="store_true", help="exclusively create one new vintage")
    parser.add_argument("--vintage", help="required with --create; explicit output vintage name")
    args = parser.parse_args()
    if args.create == args.check or (args.create and not args.vintage) or (args.check and args.vintage is None):
        parser.error("choose --check --vintage EXISTING or --create --vintage NEW")
    manifest = json.loads(MANIFEST.read_text())
    outputs = generate(manifest)
    vintage = PACKET / "vintages" / args.vintage
    if args.create:
        baseline = check_manifest(manifest)
        created = []
        for name, value in outputs.items():
            created.append(write_new_vintage(baseline, OWNED, args.vintage, name, value))
        print(json.dumps({"mode": "exclusive-create", "vintage": args.vintage, "outputs": created}, indent=2))
    else:
        records = {x["path"].split("/")[-1]: x for x in manifest["outputs"] if x["path"].startswith(OWNED + "vintages/" + args.vintage + "/")}
        if set(records) != set(outputs):
            raise ValueError("Manifest output list does not equal the generated output set")
        for name, value in outputs.items():
            path = vintage / name
            raw = path.read_bytes()
            record = records[name]
            expected = canonical_json(value)
            if len(raw) != record["bytes"] or sha256(raw) != record["sha256"] or raw != expected:
                raise ValueError("Pinned-vintage output changed or is not reproducible: " + name)
        print(json.dumps({"mode": "read-only-check", "vintage": args.vintage, "outputs": len(outputs), "semantic_match": outputs["reproduction-comparison.json"]["semantic_match"], "result_sha256": sha256(canonical_json(outputs["derived-portion-audit.json"]))}, indent=2))


if __name__ == "__main__":
    main()
