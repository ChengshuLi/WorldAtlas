#!/usr/bin/env python3
"""Reproduce issue #482's v5 member, source-identity and parent-chain checks."""
from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKET = Path(__file__).resolve().parent
SCOPE = json.loads((PACKET / "issue-scope.json").read_text())
HIERARCHY_BYTES = (ROOT / "data/hierarchy.json").read_bytes()
HIERARCHY = {row["id"]: row for row in json.loads(HIERARCHY_BYTES)}
INDEX = json.loads((ROOT / "data/world-index.json").read_text())
FEATURES = {}
FEATURE_FILES = {}
for part in INDEX["parts"]:
    for feature in json.loads((ROOT / "data" / part).read_text())["features"]:
        FEATURES[feature["id"]] = feature
        FEATURE_FILES[feature["id"]] = "data/" + part


def check(label: str, condition: bool) -> None:
    print(("PASS " if condition else "FAIL ") + label)
    if not condition:
        raise SystemExit(1)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def ancestors(parent_id: str) -> list[dict]:
    result = []
    seen = set()
    current = parent_id
    while current:
        if current in seen:
            raise ValueError("parent cycle at " + current)
        seen.add(current)
        row = HIERARCHY.get(current)
        if row is None:
            raise KeyError("missing parent " + current)
        result.append(row)
        current = row.get("parent_id")
    return result


ids = SCOPE["member_location_ids"]
check("issue snapshot and machine scope agree", SCOPE["location_count"] == len(ids) == 144)
check("member ID list is unique", len(set(ids)) == len(ids))
check("frozen issue member fingerprint matches current handoff", digest(json.dumps(sorted(ids), separators=(",", ":")).encode()) == SCOPE["frozen_region_member_ids_sha256"])
issue_member_hash_reproduced = digest(json.dumps(ids, separators=(",", ":")).encode()) == SCOPE["member_location_ids_sha256"]
print(("PASS " if issue_member_hash_reproduced else "UNRESOLVED ") + "secondary issue member_location_ids_sha256 reproduces from listed IDs: " + str(issue_member_hash_reproduced))
check("current published hierarchy hash matches assigned v5", digest(HIERARCHY_BYTES) == SCOPE["release"]["hierarchy_sha256"])
check("all assigned location features occur exactly once", all(i in FEATURES for i in ids))

area_ids = {x["id"] for x in SCOPE["area_scopes"]}
province_ids = {x["id"] for x in SCOPE["province_scopes"]}
check("all eight declared area records exist", len(area_ids) == 8 and area_ids <= HIERARCHY.keys())
check("all 47 declared province records exist", len(province_ids) == 47 and province_ids <= HIERARCHY.keys())

subject_rows = []
direct_provinces = collections.Counter()
descendant_areas = collections.Counter()
for location_id in ids:
    feature = FEATURES[location_id]
    props = feature["properties"]
    metadata = props.get("metadata", {})
    chain = ancestors(props["parent_id"])
    chain_ids = [x["id"] for x in chain]
    chain_levels = [x.get("level") for x in chain]
    province = chain[0] if chain and chain[0].get("level") == "province" else None
    areas = [x for x in chain if x.get("level") == "area"]
    if province:
        direct_provinces[province["id"]] += 1
    for area in areas:
        descendant_areas[area["id"]] += 1
    expected_levels = ["province", "area", "region", "subcontinent", "continent"]
    check(f"{location_id} complete five-level parent chain", chain_levels == expected_levels)
    check(f"{location_id} parent chain includes assigned region", SCOPE["region_id"] in chain_ids)
    subject_rows.append({
        "id": location_id,
        "containing_file": FEATURE_FILES[location_id],
        "name": props["name"],
        "source_id": metadata.get("source_id"),
        "source_name": metadata.get("source_name"),
        "source_role": metadata.get("source_role"),
        "source_reference_year": metadata.get("reference_year"),
        "source_reference_version": metadata.get("reference_version"),
        "source_license": metadata.get("license"),
        "current_geometry_type": feature.get("geometry", {}).get("type"),
        "current_component_count": len(feature.get("geometry", {}).get("coordinates", [])),
        "province_id": province["id"] if province else None,
        "province_name": province.get("name") if province else None,
        "area_ids": [x["id"] for x in areas],
        "parent_chain": [{"id": x["id"], "name": x["name"], "level": x["level"]} for x in chain],
        "reference_owner_attribute": metadata.get("reference_polity"),
        "reference_owner_is_not_location_evidence": True,
        "assessment_status": "not_yet_assessed",
        "assessment": None
    })

check("all 144 location parents resolve", len(subject_rows) == 144)
for area in SCOPE["area_scopes"]:
    check(f"area {area['name']} descendant count", descendant_areas[area["id"]] == area["full_area_location_count"] == area["owned_member_location_count"])
for province in SCOPE["province_scopes"]:
    check(f"province {province['name']} descendant count", direct_provinces[province["id"]] == province["full_province_locations"])
check("exactly the assigned eight areas are on member ancestry", set(descendant_areas) == area_ids)
check("exactly the assigned 47 provinces are on member ancestry", set(direct_provinces) == province_ids)
region_chain = ancestors(HIERARCHY[SCOPE["region_id"]]["parent_id"])
check("region's parent chain is subcontinent then continent", [x["level"] for x in region_chain] == ["subcontinent", "continent"])

# Match the three explicitly pinned geoBoundaries cohorts to raw source rows.
gb_specs = {
    "gb:MDG:ADM2": ("geoBoundaries-MDG-ADM2-2020.geojson", 119),
    "gb:MUS:ADM1": ("geoBoundaries-MUS-ADM1-2017.geojson", 12),
    "gb:SYC:ADM2": ("geoBoundaries-SYC-ADM2-2020.geojson", 8),
}
for source_id, (filename, count) in gb_specs.items():
    source = json.loads((PACKET / "sources" / filename).read_text())
    source_by_id = {row["properties"]["shapeID"]: row for row in source["features"]}
    current_ids = [i for i in ids if FEATURES[i]["properties"].get("metadata", {}).get("source_id") == source_id]
    check(f"raw source feature count for {source_id}", len(source["features"]) == count)
    check(f"all {source_id} scoped source IDs resolve uniquely", len(current_ids) == count and all(i.split(":")[-1] in source_by_id for i in current_ids))
    check(f"all {source_id} source tiers agree with metadata", all(source_by_id[i.split(":")[-1]]["properties"]["shapeType"] == source_id.split(":")[-1] for i in current_ids))
    check(f"all {source_id} names match pinned source names", all(FEATURES[i]["properties"]["name"] == source_by_id[i.split(":")[-1]]["properties"]["shapeName"] for i in current_ids))

comoros = json.loads((PACKET / "sources/geoBoundaries-COM-ADM1-2017.geojson").read_text())
comoros_ids = {row["properties"]["shapeID"] for row in comoros["features"]}
comoros_metadata = FEATURES["atlas:territory:COM"]["properties"]["metadata"]
check("three named Comoros ADM1 source islands are retained", len(comoros_ids) == 3 and set(comoros_metadata["source_member_ids"]) == {f"gb:COM:ADM1:{x}" for x in comoros_ids})

out = PACKET / "subject-inventory.jsonl"
# Preserve the semantic work ledger across reproducible structural re-runs.
prior = {}
if out.exists():
    prior = {row["id"]: row for row in (json.loads(line) for line in out.read_text().splitlines())}
for row in subject_rows:
    old = prior.get(row["id"], {})
    for key in ("assessment_status", "assessment", "uncertainties", "additional_source_check", "disconnected_component_candidates", "settlement_disposition"):
        if key in old:
            row[key] = old[key]
out.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in subject_rows))
status_counts = collections.Counter(row["assessment_status"] for row in subject_rows)
print(f"WROTE {out.relative_to(ROOT)} with {len(subject_rows)} rows; preserved assessment status: {dict(status_counts)}")
