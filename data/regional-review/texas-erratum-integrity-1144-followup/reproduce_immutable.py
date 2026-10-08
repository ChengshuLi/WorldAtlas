#!/usr/bin/env python3
"""Authenticate and reproduce the retained Texas 254-county interpretation."""
from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
import re
import sys
import types
import urllib.parse
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OWNED = "data/regional-review/texas-erratum-integrity-1144-followup/"
LEDGER_SHA256 = "3527212b673a0fe2b5f9a9b306698241ee929c70258c6e77458034e90dd827aa"
ISSUE_SNAPSHOT_SHA256 = "132fee5a55e104451d37d714b681ff15f72c0db3bcea81123aadbfa721ba2c89"
HELPER_PATH = "scripts/evidence/immutable.py"
LEGACY = "data/regional-review/texas-source-interpretation-followup-431/reproduce.py"
BASE = "data/regional-review/regional-review-508c7e9f3a462f8f"
ROWS = BASE + "/runs/twelve/county-assessments.jsonl"
PARTS = ["data/geography/part-25.json", "data/geography/part-26.json", "data/geography/part-27.json"]
HIERARCHY = "data/hierarchy.json"


def fail(message: str) -> None:
    raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vintage", required=True)
    parser.add_argument("--repo", default=str(ROOT))
    args = parser.parse_args()
    repo = Path(args.repo).resolve()

    ledger_path = HERE / "input-pins.json"
    ledger_raw = ledger_path.read_bytes()
    if hashlib.sha256(ledger_raw).hexdigest() != LEDGER_SHA256:
        fail("Pinned input ledger changed")
    ledger = json.loads(ledger_raw)
    if ledger.get("version") != 1 or ledger.get("issue") != 1365:
        fail("Wrong issue input ledger")
    descriptors = ledger["files"]
    by_path = {item["path"]: item for item in descriptors}
    if len(by_path) != len(descriptors) or LEGACY not in by_path or HELPER_PATH not in by_path:
        fail("Incomplete or duplicate baseline inventory")

    # Authenticate the helper before executing its exact captured bytes.
    helper_desc = by_path[HELPER_PATH]
    helper_file = repo / HELPER_PATH
    helper_raw = helper_file.read_bytes()
    if len(helper_raw) != helper_desc["bytes"] or hashlib.sha256(helper_raw).hexdigest() != helper_desc["sha256"]:
        fail("Shared immutable helper differs from reviewed bytes")
    module = types.ModuleType("worldatlas_immutable")
    module.__file__ = str(helper_file)
    exec(compile(helper_raw, str(helper_file), "exec"), module.__dict__)

    baseline = module.Baseline(repo, ledger["baseline_commit"], descriptors)
    captured = {}
    for item in descriptors:
        path = item["path"]
        # This confirms the mutable files the legacy producer would have opened;
        # subsequent reads use the authenticated immutable byte strings.
        captured[path] = baseline.materialized_bytes(path)
    snapshot = (HERE / "issue-1365-snapshot.json").read_bytes()
    if hashlib.sha256(snapshot).hexdigest() != ISSUE_SNAPSHOT_SHA256:
        fail("Retained GitHub issue acceptance snapshot changed")
    issue = json.loads(snapshot)
    match = re.search(r"<!-- worldatlas-work:v1\s*(\{.*?\})\s*-->", issue["body"], re.S)
    if not match:
        fail("Issue scope contract missing")
    contract = json.loads(match.group(1))
    ids = contract["evidence_quality"]["subject_ids"]
    if len(ids) != 254 or len(set(ids)) != 254:
        fail("Issue scope is not the exact 254-subject roster")
    for path, digest in contract["evidence_quality"]["pins"].items():
        if by_path[path]["sha256"] != digest:
            fail("Issue declared pin differs: " + path)
    if set(contract["owned_paths"]) != {OWNED}:
        fail("Owned output path differs from issue")

    # Reserve the entire output inventory before parsing any research inputs.
    filenames = ["county-interpretation-erratum.jsonl", "reproduction-summary.json", "validation.json"]
    vintage = module.NewVintage(baseline, OWNED, args.vintage, filenames)

    def read(path: str) -> bytes:
        return captured[path]

    def parsed(path: str):
        return json.loads(read(path))

    rows = [json.loads(line) for line in read(ROWS).decode("utf-8").splitlines() if line]
    row_by_id = {row["subject_id"]: row for row in rows}
    if len(rows) != 254 or len(row_by_id) != 254 or set(row_by_id) != set(ids):
        fail("Historical assessment rows do not exactly match issue scope")

    atlas = {}
    for path in PARTS:
        collection = parsed(path)
        for feature in collection["features"]:
            fid = feature.get("id") or feature.get("properties", {}).get("id")
            if fid in ids:
                if fid in atlas:
                    fail("Duplicate Atlas subject feature: " + fid)
                atlas[fid] = feature
    if set(atlas) != set(ids):
        fail("Atlas containing files do not have exact scoped feature coverage")
    hierarchy_rows = parsed(HIERARCHY)
    hierarchy = {x["id"]: x for x in hierarchy_rows}

    source_fc = parsed(BASE + "/source/geoBoundaries-USA-ADM2.geojson")
    source_by_shape = {}
    for feature in source_fc["features"]:
        props = feature.get("properties", {})
        sid = props.get("shapeID")
        if sid in source_by_shape:
            fail("Duplicate source shape ID: " + str(sid))
        source_by_shape[sid] = feature
    api_by_year = {}
    for year in ("2018", "2025"):
        feature_collection = parsed(f"{BASE}/source/census-{year}/texas-counties.geojson")
        features = feature_collection.get("features", [])
        records = {}
        for feature in features:
            geoid = feature.get("properties", {}).get("GEOID")
            if geoid in records:
                fail(f"Duplicate {year} Census GEOID: {geoid}")
            records[geoid] = feature
        if feature_collection.get("type") != "FeatureCollection" or len(records) != 254:
            fail(f"{year} Census feature roster is not exactly 254")
        api_by_year[year] = records

    # Validate every identity and source join independently before generating output.
    for sid in ids:
        row = row_by_id[sid]
        feature = atlas[sid]
        props = feature.get("properties", {})
        if (props.get("id") != sid or feature.get("id") not in (None, sid) or
                props.get("name") != row["atlas_name"] or props.get("parent_id") != row["parent_id"]):
            fail("Atlas identity/name/parent conflict: " + sid)
        metadata = props.get("metadata", {})
        if (metadata.get("original_id") != row["source_id"] or metadata.get("reference_year") != "2018" or
                metadata.get("administrative_level") != "ADM2" or metadata.get("parent_source_level") != "ADM1" or
                metadata.get("source_role") != "Counties" or metadata.get("geographic_area_code") != "TEX"):
            fail("Atlas retained source identity/vintage/tier/role metadata conflict: " + sid)
        parent = hierarchy.get(row["parent_id"])
        if not parent or parent.get("name") != "Texas" or parent.get("level") != "province":
            fail("County parent is absent or not Texas in the pinned hierarchy: " + sid)
        source = source_by_shape.get(row["source_id"])
        if not source or source["properties"].get("shapeName") != row["source_name"] or source["properties"].get("shapeType") != "ADM2":
            fail("Independent geoBoundaries source identity/name/level conflict: " + sid)
        if row["source_role"] != "Counties" or row["source_vintage"] != "2018" or row["source_license"] != "Public Domain":
            fail("Retained source role/vintage/license fields conflict: " + sid)
        for year, geoid_key, name_key, type_key in (
            ("2018", "census_geoid_2018", "census_county_name_2018", "census2018"),
            ("2025", "census_geoid_2025", "census_county_name_2025", "census2025"),
        ):
            census = api_by_year[year].get(row[geoid_key])
            if not census:
                fail(f"Missing {year} Census GEOID join: {sid}")
            cp = census["properties"]
            if (cp.get("STATE") != "48" or cp.get("BASENAME") != row["atlas_name"] or
                    cp.get("NAME") != row[name_key] or cp.get("FUNCSTAT") != "A" or
                    cp.get("GEOID") != row[geoid_key] or
                    census.get("geometry", {}).get("type") != row["geometry_types"][type_key]):
                fail(f"{year} Census identity/name/parent-vintage join conflict: {sid}")

    component_counts = collections.Counter(row["multipart_components"]["census2018_cbf_500k"] for row in rows)
    type_counts = collections.Counter(row["geometry_types"]["census2018_cbf_500k"] for row in rows)
    expected_components = {1: 243, 3: 5, 4: 1, 5: 1, 6: 1, 7: 2, 26: 1}
    if dict(component_counts) != expected_components or type_counts != {"Polygon": 243, "MultiPolygon": 11} or sum(k * v for k, v in component_counts.items()) != 313:
        fail("Historical CBF record/component distribution changed")

    with zipfile.ZipFile(__import__("io").BytesIO(read(BASE + "/source/census-2018/cb_2018_us_county_500k.zip"))) as archive:
        prj_name = "cb_2018_us_county_500k.prj"
        prj = archive.read(prj_name).decode("ascii")
        if not all(term in prj for term in ("GCS_North_American_1983", "D_North_American_1983", "GRS_1980")):
            fail("Pinned 2018 CBF projection member has an unexpected declared CRS")

    retrieval = parsed(BASE + "/source/census-api-retrieval-manifest.json")
    census_crs = {}
    for item in retrieval:
        if item["file"].endswith("texas-counties.geojson"):
            year = str(item["vintage"])
            query = urllib.parse.parse_qs(urllib.parse.urlparse(item["url"]).query)
            if query.get("outSR") != ["4326"] or query.get("where") != ["STATE = '48'"]:
                fail(f"Actual {year} Census request CRS/scope is not EPSG:4326/Texas")
            census_crs[year] = {"request_url": item["url"], "retrieved_at": item["retrieved_at"], "requested_output_crs": "EPSG:4326 (outSR parameter)"}
        elif item["file"].endswith("counties-layer-metadata.json"):
            metadata_path = BASE + "/source/" + item["file"]
            metadata = parsed(metadata_path)
            sr = metadata.get("spatialReference", {})
            if sr.get("wkid") != 102100 or sr.get("latestWkid") != 3857:
                fail("Census layer native/latest spatial reference declaration changed")
            census_crs[f"{item['vintage']}_service_layer"] = {"url": item["url"], "retrieved_at": item["retrieved_at"], "native_and_latest_spatial_reference": sr}
    if set(census_crs) != {"2018", "2025", "2018_service_layer", "2025_service_layer"}:
        fail("Census request and layer metadata coverage is incomplete")
    geoboundaries = parsed(BASE + "/source/geoBoundaries-USA-ADM2.geojson")
    geoboundaries_crs = geoboundaries.get("crs", {}).get("properties", {}).get("name")
    if geoboundaries_crs != "urn:ogc:def:crs:OGC:1.3:CRS84":
        fail("geoBoundaries declared CRS changed")

    scope_hash = hashlib.sha256(json.dumps(sorted(ids), separators=(",", ":")).encode()).hexdigest()
    output = []
    for sid in sorted(ids):
        row = row_by_id[sid]
        api_2018 = api_by_year["2018"][row["census_geoid_2018"]]
        api_2025 = api_by_year["2025"][row["census_geoid_2025"]]
        output.append({
            "subject_id": sid, "name": row["atlas_name"], "source_id": row["source_id"], "parent_id": row["parent_id"],
            "census_geoid_2018": row["census_geoid_2018"], "census_geoid_2025": row["census_geoid_2025"],
            "census_2018_tigerweb_record_geometry_type": api_2018["geometry"]["type"],
            "census_2018_tigerweb_polygon_component_count": 1,
            "census_2025_tigerweb_record_geometry_type": api_2025["geometry"]["type"],
            "census_2025_tigerweb_polygon_component_count": 1,
            "census_2018_cbf_record_geometry_type": row["geometry_types"]["census2018_cbf_500k"],
            "census_2018_cbf_polygon_component_count": row["multipart_components"]["census2018_cbf_500k"],
            "record_is_not_component": True,
            "geometry_interpretation": "one county feature/record; Polygon has one component; MultiPolygon has the stated number of polygon components",
            "source_crs": "GCS_North_American_1983; datum D_North_American_1983; GRS_1980 ellipsoid; geographic degrees, per archive .prj",
            "legacy_transform_note": "The 2018 CBF shapes were passed to the legacy EPSG:4326-to-6933 transformer as if their coordinates were WGS 84. This is an undocumented NAD83-as-WGS84 coordinate approximation; no datum operation or accuracy was recorded.",
            "numerical_effect_measured": False, "boundary_completeness_established": False,
            "historical_assessment_preserved": row["classification"],
        })
    table = b"".join((json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n").encode() for row in output)
    summary = {
        "issue": 1138, "scope_count": len(ids), "scope_subject_ids_sha256_json_sorted": scope_hash,
        "source_rows": len(rows), "tigerweb_2018_query_features": 254,
        "tigerweb_2018_geometry_type_counts": {"Polygon": 254}, "tigerweb_2018_polygon_components_total": 254,
        "tigerweb_2025_query_features": 254, "tigerweb_2025_geometry_type_counts": {"Polygon": 254},
        "tigerweb_2025_polygon_components_total": 254,
        "record_geometry_type_counts": dict(sorted(type_counts.items())),
        "polygon_component_count_distribution": {str(k): component_counts[k] for k in sorted(component_counts)},
        "polygon_components_total": 313, "crs_prj_member": prj_name, "crs_prj_text": prj,
        "other_input_crs_declarations": {
            "census_tigerweb": census_crs, "geoboundaries_geojson": geoboundaries_crs,
            "texas_government_guide": "PDF text; no coordinate reference system applies.",
            "texas_constitution": "No provision bytes retained; no coordinate reference system applies.",
        },
        "numerical_effect_measured": False, "original_assessments_modified": False,
        "boundary_completeness_or_legal_validity_inferred": False,
    }
    summary_bytes = (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode()
    validation = {
        "version": 1, "issue": 1365, "scope_count": 254, "exact_issue_subjects": True,
        "authenticated_baseline_files": len(descriptors), "all_materialized_inputs_match": True,
        "execution": {"python": sys.version.split()[0], "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "shared_helper_sha256": by_path[HELPER_PATH]["sha256"], "baseline_commit": ledger["baseline_commit"]},
        "identity_joins": {"atlas_features": 254, "geoBoundaries_shape_name_level": 254, "census_2018_name_geoid_parent_vintage": 254, "census_2025_name_geoid_parent_vintage": 254},
        "parsed_outSR_4326": {"2018": True, "2025": True}, "census_service_native_latest_wkid": [102100, 3857],
        "cbf_record_types": {"Polygon": 243, "MultiPolygon": 11}, "cbf_polygon_components": 313,
        "output_matches_retained_original": table == read("data/regional-review/texas-source-interpretation-followup-431/county-interpretation-erratum.jsonl") and summary_bytes == read("data/regional-review/texas-source-interpretation-followup-431/reproduction-summary.json"),
        "territorial_and_legal_limits": ["Census TIGER statistical geography is not a legal boundary determination", "No county boundary completeness or island completeness finding", "Texas constitutional provision source bytes remain unavailable; original restoration-only limit preserved", "No datum displacement was measured", "No publication or geography approval"],
    }
    if not validation["output_matches_retained_original"]:
        fail("Corrected outputs do not exactly preserve the retained valid-run results")
    validation_bytes = (json.dumps(validation, indent=2, sort_keys=True) + "\n").encode()
    vintage.publish_bytes({"county-interpretation-erratum.jsonl": table, "reproduction-summary.json": summary_bytes, "validation.json": validation_bytes})
    print(json.dumps({"vintage": args.vintage, "rows": len(output), "scope_sha256": scope_hash, "table_sha256": hashlib.sha256(table).hexdigest(), "summary_sha256": hashlib.sha256(summary_bytes).hexdigest()}, sort_keys=True))


if __name__ == "__main__":
    main()
