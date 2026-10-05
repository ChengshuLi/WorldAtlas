#!/usr/bin/env python3
"""Reproduce the Kosovo seven-feature/source-role crosswalk from immutable inputs."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

BASELINE = "96f2a6d201236ba62f471535db240b123de60c09"
PACKET = "data/regional-review/followup-kosovo-422-district-source-20261005"
PARENT = "data/regional-review/regional-review-3c4fe25a21fa428d/source"
PINNED = {
    "data/world-index.json": "a62d4a74f0f969e228dfcdeb2797bb689ce9836c2498cadd31ed622ad2c38c03",
    "data/hierarchy.json": "568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b",
    "data/geographic-releases/current-manifest.json": "85075dd4eceebf5bc8e7b554fb4e1573aed2c5baae546ca21746643852c55b81",
    "data/administrative-sources.json": "ed0051d2956271c72f8917e7da0c6f53e5dfb595bee5920cac489a65a747d633",
    "data/macro-foundation/current-membership-inventory.json.gz": "db58f274debe5917f7fa21fdd2ab563f4761cfb673bd814b6402708fa10b06ab",
    "data/macro-foundation/review-index.json": "31dfd5cbfd8f3def829f655e7ddd855d2d2865e5ac63f9d1a97d1c08782910cf",
    "data/macro-foundation/regional-handoffs.json.gz": "29af5204c1f28d2616d7d8d8bb18e5d718c8c1e6dab3637868b03a2381b5db2a",
    "data/macro-foundation/macro-certificate.json": "f50f70fcb0756712ab7a7a388bc8cada093080518f07d3a6f7329758980ea81b",
    "data/macro-foundation/approved-boundary-decisions.json": "b67d5a3bcf8101cffb089c0262286378a80bb642cd6dde33f7721419227e3f18",
}
SUBJECTS = {
    "gb:XKX:ADM1:2360587B5118871504069",
    "gb:XKX:ADM1:2360587B74553771763221",
    "gb:XKX:ADM1:2360587B95703323116719",
}
RELATED_SCOPE_PATH = f"{PACKET}/related-scope-1008.json"
NAME_TO_REGION = {
    "District of Prishtina": "Prishtinë",
    "District of Mitrovica": "Mitrovicë",
    "District of Peja": "Pejë",
    "District of Prizren": "Prizren",
    "District of Ferizaj": "Ferizaj",
    "District of Gjilan": "Gjilan",
    "District of Gjakova": "Gjakovë",
}


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def baseline_bytes(repo: Path, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{BASELINE}:{path}"], cwd=repo)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    repo = args.root.resolve()
    for path, expected in PINNED.items():
        actual = digest(baseline_bytes(repo, path))
        if actual != expected:
            raise SystemExit(f"pinned input mismatch: {path}: {actual} != {expected}")

    issue_snapshot = json.loads((repo / PACKET / "github-issue-contract.json").read_bytes())
    issue_match = re.search(r"<!-- worldatlas-work:v1\s*\n([\s\S]*?)\n-->", issue_snapshot["body"])
    if not issue_match or set(json.loads(issue_match.group(1))["evidence_quality"]["subject_ids"]) != SUBJECTS:
        raise SystemExit("pinned issue 999 API snapshot differs from the exact source-work scope")
    related = json.loads((repo / RELATED_SCOPE_PATH).read_bytes())
    other_scope = set(related["subject_ids"])
    if related.get("source_issue") != 1008 or 999 not in related.get("depends_on", []) or related.get("subject_count") != 4:
        raise SystemExit("related issue 1008 scope/dependency snapshot is incomplete")

    rows = {}
    subject_path = "data/geography/part-28.json"
    part = json.loads(baseline_bytes(repo, subject_path))
    atlas_ids = {
        feature["properties"]["id"]: {"path": subject_path, "properties": feature["properties"]}
        for feature in part.get("features", [])
        if feature.get("properties", {}).get("id", "").startswith("gb:XKX:ADM1:")
    }
    hierarchy = json.loads(baseline_bytes(repo, "data/hierarchy.json"))
    atlas_parents = {feature["id"]: feature for feature in hierarchy}
    if not SUBJECTS <= atlas_ids.keys():
        raise SystemExit("one or more exact issue subjects are missing from the pinned world index parts")

    geo_path = f"{PARENT}/gb/gb-XKX-ADM1.geojson"
    geo_raw = baseline_bytes(repo, geo_path)
    geo = json.loads(geo_raw)
    meta_path = f"{PARENT}/gb/XKX-ADM1-geoBoundaries-XKX-ADM1-metaData.json"
    meta_raw = baseline_bytes(repo, meta_path)
    meta = json.loads(meta_raw)
    source_manifest_path = f"{PARENT}/source-manifest.json"
    source_manifest_raw = baseline_bytes(repo, source_manifest_path)
    source_manifest = json.loads(source_manifest_raw)
    neighbor_ids = {"gb:MKD:ADM2", "gb:SRB:ADM2", "gb:MNE:ADM1"}
    neighbors = [
        {key: row.get(key) for key in ["source_id", "path", "bytes", "sha256", "features", "vintage", "type", "canonical", "catalog_source", "license", "license_source", "catalog_adm_count"]}
        for row in source_manifest["sources"] if row["source_id"] in neighbor_ids
    ]
    if {row["source_id"] for row in neighbors} != neighbor_ids:
        raise SystemExit("pinned parent source manifest does not contain all three neighboring layer references")
    feature_ids = set()
    for feature in geo.get("features", []):
        props = feature["properties"]
        shape_id = props["shapeID"]
        identifier = f"gb:XKX:ADM1:{shape_id}"
        feature_ids.add(identifier)
        atlas = atlas_ids.get(identifier)
        parent_id = atlas["properties"].get("parent_id") if atlas else None
        parent = atlas_parents.get(parent_id)
        area_id = parent.get("parent_id") if parent else None
        area = atlas_parents.get(area_id)
        rows[identifier] = {
            "shape_id": shape_id,
            "source_name": props.get("shapeName"),
            "source_type": props.get("shapeType"),
            "source_group": props.get("shapeGroup"),
            "kas_statistical_region_name": NAME_TO_REGION.get(props.get("shapeName")),
            "in_issue_999_scope": identifier in SUBJECTS,
            "followup_issue": 999 if identifier in SUBJECTS else 1008 if identifier in other_scope else None,
            "atlas_feature_path": atlas["path"] if atlas else None,
            "atlas_name": atlas["properties"].get("name") if atlas else None,
            "atlas_parent_id": parent_id,
            "atlas_parent_name": parent.get("name") if parent else None,
            "atlas_parent_level": parent.get("level") if parent else None,
            "atlas_parent_child_count": parent.get("metadata", {}).get("child_count") if parent else None,
            "atlas_area_parent_id": area_id,
            "atlas_area_parent_name": area.get("name") if area else None,
            "atlas_source_role": atlas["properties"].get("metadata", {}).get("source_role") if atlas else None,
            "atlas_area_code": atlas["properties"].get("metadata", {}).get("geographic_area_code") if atlas else None,
            "atlas_region_code": atlas["properties"].get("metadata", {}).get("geographic_region_code") if atlas else None,
        }
    if len(geo.get("features", [])) != 7 or len(feature_ids) != 7:
        raise SystemExit("pinned geoBoundaries source is not exactly seven unique shape IDs")
    if feature_ids != set(rows) or set(rows) != set(atlas_ids) & feature_ids:
        raise SystemExit("source feature/Atlas feature identity crosswalk is incomplete")
    if SUBJECTS & other_scope or SUBJECTS | other_scope != feature_ids:
        raise SystemExit("issues 999 and 1008 do not partition the seven source subjects")
    if set(rows) != feature_ids or set(NAME_TO_REGION) != {r["source_name"] for r in rows.values()}:
        raise SystemExit("the all-seven name map is incomplete")
    if int(meta["admUnitCount"]) != 48:
        raise SystemExit("unexpected pinned source metadata count")
    kas = json.loads((repo / PACKET / "kas-statistical-regions.json").read_bytes())
    members = [municipality for region in kas["regions"] for municipality in region["municipalities"]]
    if len(kas["regions"]) != 7 or len(members) != 38 or len(set(members)) != 38:
        raise SystemExit("KAS extract does not contain seven regions and 38 unique municipalities")
    if {r["kas_statistical_region_name"] for r in rows.values()} != {r["name"] for r in kas["regions"]}:
        raise SystemExit("geoBoundaries district-name/KAS region-name correspondence is incomplete")

    result = {
        "version": 1,
        "issue": 999,
        "baseline_commit": BASELINE,
        "source_path": geo_path,
        "source_bytes": len(geo_raw),
        "source_sha256": digest(geo_raw),
        "metadata_path": meta_path,
        "metadata_bytes": len(meta_raw),
        "metadata_sha256": digest(meta_raw),
        "source_manifest_path": source_manifest_path,
        "source_manifest_bytes": len(source_manifest_raw),
        "source_manifest_sha256": digest(source_manifest_raw),
        "metadata_admUnitCount": int(meta["admUnitCount"]),
        "source_feature_count": len(rows),
        "official_statistical_region_count": len(kas["regions"]),
        "official_administrative_municipality_count": len(members),
        "all_source_feature_ids_match_atlas_ids": True,
        "name_match_only_not_geometry_match": True,
        "issue_subject_count": len(SUBJECTS),
        "issue_subjects_are_subset_of_seven": SUBJECTS <= set(rows),
        "neighboring_source_layers": sorted(neighbors, key=lambda row: row["source_id"]),
        "features": [rows[k] for k in sorted(rows)],
        "kas_regions": kas["regions"],
        "limitations": [
            "The 48 metadata value is inconsistent with seven exact source features and KAS's 38 municipality / seven non-administrative region structure; its provenance is unknown.",
            "KAS's proposed regions and membership table do not prove polygon equivalence. No lawful, machine-readable official 2021/2024 boundary geometry with reuse terms was retrieved.",
            "The underlying OSM snapshot/database and relation IDs for the original geoBoundaries input are absent from the pinned metadata.",
        ],
    }
    out = repo / PACKET / "source-crosswalk.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out.relative_to(repo)), "sha256": digest(out.read_bytes()),
                      "source_features": len(rows), "source_feature_ids": sorted(rows),
                      "issue_subjects": sorted(SUBJECTS), "kas_regions": len(kas["regions"]),
                      "municipalities": len(members)}))


if __name__ == "__main__":
    main()
