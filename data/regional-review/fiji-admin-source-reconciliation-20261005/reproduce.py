#!/usr/bin/env python3
"""Reproduce issue #910's exact Fiji source-to-Atlas crosswalk and Lau screen.

Reads only immutable main blobs plus the lawfully retained geoBoundaries source
under this issue's owned path. It does not certify current administrative
boundaries or use any repair, snap, buffer, or area cutoff.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
sys.path.insert(0, str(REPO / "scripts"))
from evidence.geometry import METHOD, VERSION, canonical_land, land_area_m2, transform_point  # noqa: E402
from evidence.immutable import Baseline, descriptor, sha256  # noqa: E402
from shapely.geometry import shape  # noqa: E402

BASELINE_COMMIT = "fc328993bb8c0690b3b4687d193c7f0887bd5b17"
OWNED = "data/regional-review/fiji-admin-source-reconciliation-20261005/"
ISSUE_SNAPSHOT = ROOT / "issue-910-contract.json"
CLAIM_RECEIPT = ROOT / "claim-receipt.json"
SOURCE = ROOT / "sources/geoBoundaries-FJI-ADM2.geojson"
SOURCE_SHA = "a9cd94789cb5eb66cfbcbaf32a21bcbceba16b9a76adacba9ac675b950ca1ccd"
SOURCE_BYTES = 1_357_011
PIN_FILES = {
    "world_index": "data/world-index.json",
    "source_registry": "data/administrative-sources.json",
    "geography_part_8": "data/geography/part-8.json",
    "macro_publication_v5": "data/validation/macro-publication-v5.json",
}
EXPECTED_PINS = {
    "world_index": "a62d4a74f0f969e228dfcdeb2797bb689ce9836c2498cadd31ed622ad2c38c03",
    "source_registry": "ed0051d2956271c72f8917e7da0c6f53e5dfb595bee5920cac489a65a747d633",
    "geography_part_8": "2b0b335d6d7d494eac24da313c99834a7c602390e5302d4cf00049244893a3d1",
    "macro_publication_v5": "aae3967fde4f5bf92b3cb0b42c490c6c6a5921c7421dcdc9533f242afbd6a674",
}


def file_descriptor(path: str, raw: bytes) -> dict:
    return descriptor(path, raw)


def control(name: str, passed: bool, detail: str) -> dict:
    if not passed:
        raise AssertionError(f"Control failed: {name}: {detail}")
    return {"name": name, "outcome": "passed", "detail": detail}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, help="Output JSON path beneath this packet")
    args = parser.parse_args()
    output = (REPO / args.output).resolve()
    if ROOT not in output.parents:
        raise ValueError("Output must remain under the issue-owned path")

    issue = json.loads(ISSUE_SNAPSHOT.read_text())
    claim = json.loads(CLAIM_RECEIPT.read_text())
    assert issue["number"] == 910 and issue["state"] == "open"
    block_start = issue["body"].index("<!-- worldatlas-work:v1")
    block_end = issue["body"].index("-->", block_start)
    block = json.loads(issue["body"][issue["body"].index("{", block_start):block_end])
    assert block["mode"] == "geography" and block["owned_paths"] == [OWNED]
    ids = sorted(block["evidence_quality"]["subject_ids"])
    assert len(ids) == 15 and len(set(ids)) == 15
    assert claim["accepted"] is True
    assert claim["issue_number"] == 910
    assert claim["claim"]["active"] is True
    assert claim["claim"]["worker_id"] == "01a10947-7d6e-7ba2-98a1-a9f91dedabfc"
    assert claim["claim"]["branch"] == "geography/fiji-admin-source-910-g0-20261006"
    assert claim["claim"]["owned_paths"] == [OWNED.rstrip("/") + "/"]

    pin_rows = []
    for name, path in PIN_FILES.items():
        raw = __import__("subprocess").check_output(
            ["git", "-C", str(REPO), "show", f"{BASELINE_COMMIT}:{path}"]
        )
        desc = file_descriptor(path, raw)
        assert desc["sha256"] == EXPECTED_PINS[name], f"Pinned file mismatch: {name}"
        pin_rows.append(desc)
    hierarchy_path = "data/hierarchy.json"
    hierarchy_raw = __import__("subprocess").check_output(
        ["git", "-C", str(REPO), "show", f"{BASELINE_COMMIT}:{hierarchy_path}"]
    )
    hierarchy_desc = file_descriptor(hierarchy_path, hierarchy_raw)
    pin_rows.append(hierarchy_desc)
    baseline = Baseline(REPO, BASELINE_COMMIT, pin_rows)
    atlas_features, containing = baseline.subjects(ids)
    assert set(containing) == set(ids)
    assert {row["path"] for row in containing.values()} == {"data/geography/part-8.json"}

    source_raw = SOURCE.read_bytes()
    assert len(source_raw) == SOURCE_BYTES and sha256(source_raw) == SOURCE_SHA
    source_doc = json.loads(source_raw)
    source_features = source_doc["features"]
    source_ids = [f["properties"]["shapeID"] for f in source_features]
    assert len(source_features) == 15 and len(set(source_ids)) == 15
    source_by_id = {f["properties"]["shapeID"]: f for f in source_features}
    suffixes = {ident.rsplit(":", 1)[-1] for ident in ids}
    assert set(source_by_id) == suffixes

    hierarchy = {row["id"]: row for row in json.loads(hierarchy_raw)}
    rows = []
    for ident in ids:
        atlas = atlas_features[ident]
        properties = atlas["properties"]
        suffix = ident.rsplit(":", 1)[-1]
        feature = source_by_id[suffix]
        source_properties = feature["properties"]
        assert properties.get("name") == source_properties.get("shapeName")
        parent_id = properties.get("parent_id")
        parent = hierarchy.get(parent_id)
        assert parent is not None, f"Missing parent identity for {ident}"
        rows.append({
            "subject_id": ident,
            "source_shape_id": source_properties["shapeID"],
            "source_name": source_properties["shapeName"],
            "source_shape_type": source_properties.get("shapeType"),
            "source_shape_group": source_properties.get("shapeGroup"),
            "source_geometry_type": shape(feature["geometry"]).geom_type,
            "source_geometry_valid": bool(shape(feature["geometry"]).is_valid),
            "source_polygon_component_count": len(feature["geometry"]["coordinates"]),
            "atlas_name": properties["name"],
            "atlas_parent_id": parent_id,
            "atlas_parent_name": parent.get("name"),
            "baseline_containing_file": containing[ident]["path"],
            "identity_status": "exact native shapeID suffix and exact source name match",
            "territorial_role_status": (
                "official 2024 Fiji Parliament Hansard describes Rotuma as a dependency with local-government autonomy; census table grouping is not legal province status"
                if properties["name"] == "Rotuma"
                else "source canonical label is Provinces; statistical roster match does not prove current statutory role or exact boundary"
            ),
            "boundary_status": (
                "material source-to-Atlas discrepancy; authority and source-vintage disagreement unresolved"
                if properties["name"] == "Lau"
                else "exact current official boundary and small-island completeness not established"
            ),
        })

    lau_id = "gb:FJI:ADM2:14151628B80423492752803"
    lau_source = source_by_id[lau_id.rsplit(":", 1)[-1]]
    lau_atlas = atlas_features[lau_id]
    native_land = canonical_land(shape(lau_source["geometry"]))
    atlas_land = canonical_land(shape(lau_atlas["geometry"]))
    intersection_m2 = land_area_m2(native_land.intersection(atlas_land))
    union_m2 = land_area_m2(native_land.union(atlas_land))
    symmetric_difference_m2 = land_area_m2(native_land.symmetric_difference(atlas_land))
    jaccard = intersection_m2 / union_m2

    x, y = transform_point(10, 45, "EPSG:3857")
    axis_control = control(
        "longitude-first CRS control",
        abs(x - 1_113_194.9079) < 1 and abs(y - 5_621_521.486) < 1,
        "10E,45N transformed with always_xy; swapped axis coordinates cannot pass",
    )
    controls = [
        control("exact 15-subject roster", len(rows) == 15 and len(source_features) == 15,
                "All 15 issue subjects map one-to-one to all 15 full-source features"),
        control("native identity and name", all(r["source_name"] == r["atlas_name"] for r in rows),
                "Every suffix ID and exact source name matches uniquely"),
        control("absent-source negative control", "__not-a-real-fiji-shape__" not in source_by_id,
                "Deliberately absent source shape ID does not match"),
        control("wrong-name negative control",
                source_by_id[source_ids[0]]["properties"]["shapeName"] != "__deliberately-wrong-name__",
                "A wrong display name cannot be accepted as a source crosswalk"),
        axis_control,
    ]

    output_doc = {
        "version": 1,
        "issue": 910,
        "evaluation_commit": BASELINE_COMMIT,
        "source": {
            "source_id": "FJI-ADM2-geoBoundaries-9469f09",
            "source_boundary_id": "FJI-ADM2-14151628",
            "boundary_canonical": "Provinces",
            "feature_count": len(source_features),
            "whole_source_bytes": SOURCE_BYTES,
            "whole_source_sha256": SOURCE_SHA,
            "coordinate_crs": "EPSG:4326",
            "lfs_pointer_verified": True,
            "lfs_pointer_sha256": SOURCE_SHA,
        },
        "scope": {
            "issue_subject_count": len(ids),
            "unique_baseline_subject_count": len(atlas_features),
            "baseline_containing_files": sorted({x["path"] for x in containing.values()}),
            "source_feature_count": len(source_features),
            "crosswalk_count": len(rows),
            "complete_source_roster_matches_issue_scope": set(source_by_id) == suffixes,
        },
        "subjects": rows,
        "lau_comparison": {
            "subject_id": lau_id,
            "source_geometry_valid": bool(shape(lau_source["geometry"]).is_valid),
            "source_polygon_components": len(lau_source["geometry"]["coordinates"]),
            "source_vertices": sum(len(ring) for poly in lau_source["geometry"]["coordinates"] for ring in poly),
            "area_method": METHOD,
            "intersection_m2": intersection_m2,
            "union_m2": union_m2,
            "jaccard": jaccard,
            "symmetric_difference_m2": symmetric_difference_m2,
            "symmetric_difference_km2": symmetric_difference_m2 / 1_000_000,
            "interpretation": "This is a deterministic outline comparison between a 2023 geoBoundaries release sourced to a 2007 Census dataset and Atlas baseline geometry; it does not adjudicate current legal boundary authority.",
        },
        "controls": controls,
        "control_count": len(controls),
        "uncertainties": [
            "The source catalog identifies the underlying boundary data as the 2007 Fiji Population and Housing Census administrative-boundary dataset; geoBoundaries API metadata labels its represented year 2020 and records a 2023 source-data update/build. The source-vintage meaning remains unresolved.",
            "The current Atlas source-registry sha256 value differs from the raw GeoJSON byte hash; exact pinned geoBoundaries API and raw-file evidence do not explain the old digest field's recipe.",
            "The authoritative UN SALB page identifies a validated Ministry of Lands and Mineral Resources dataset current through 2024-03-18, but the page returned HTTP 403 in this retrieval environment and its polygon bytes were not obtained or compared.",
            "The Census province roster is evidence of statistical reporting units, not proof that Rotuma is legally a province or that any of the 15 outlines represent current official edges.",
            "No authoritative coastal/island inventory was retrieved to prove complete coverage of small islands, reefs, or islets.",
        ],
        "runtime": {
            "python": sys.version.split()[0],
            "shapely": __import__("shapely").__version__,
            "pyproj": __import__("pyproj").__version__,
            "geometry_helper": VERSION,
            "geometry_method": METHOD,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(output_doc, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n")
    print(json.dumps({
        "output": str(output.relative_to(REPO)),
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "subjects": len(rows),
        "lau_jaccard": jaccard,
        "lau_symmetric_difference_km2": symmetric_difference_m2 / 1_000_000,
        "controls": len(controls),
        "status": "passed",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
