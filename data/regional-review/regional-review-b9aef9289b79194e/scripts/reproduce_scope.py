#!/usr/bin/env python3
"""Reproduce #435's exact subject-to-current-Atlas roster from its issue snapshot."""
from __future__ import annotations

import gzip
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OWNED = ROOT / "data/regional-review/regional-review-b9aef9289b79194e"
ISSUE = OWNED / "source/issue-api-snapshot.json"
OUT = OWNED / "findings"
OUT.mkdir(parents=True, exist_ok=True)
issue = json.loads(ISSUE.read_text(encoding="utf-8"))
match = re.search(r"```json\s*(\{.*?\})\s*```", issue["body"], re.S)
if not match:
    raise SystemExit("issue has no fenced machine-readable scope")
scope = json.loads(match.group(1))
ids = scope.get("member_location_ids", [])
if len(ids) != 226 or len(set(ids)) != 226 or scope.get("location_count") != 226:
    raise SystemExit("issue scope is not exactly 226 unique IDs")
(OWNED / "source/issue-scope.json").write_text(
    json.dumps(scope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
index = json.loads((ROOT / "data/world-index.json").read_text(encoding="utf-8"))
hierarchy_rows = json.loads((ROOT / "data/hierarchy.json").read_text(encoding="utf-8"))
hierarchy = {row["id"]: row for row in hierarchy_rows}
features_by_id = {}
for relative in index["parts"]:
    document = json.loads((ROOT / "data" / relative).read_text(encoding="utf-8"))
    for feature in document.get("features", []):
        props = feature.get("properties", {})
        key = props.get("id")
        if key in ids:
            if key in features_by_id:
                raise SystemExit(f"duplicate current Atlas feature: {key}")
            features_by_id[key] = (props, feature.get("geometry"), relative)
missing = sorted(set(ids) - set(features_by_id))
if missing:
    raise SystemExit(f"issue subjects missing from current Atlas: {missing}")

def polygon_components(geometry):
    if not geometry:
        return None
    if geometry.get("type") == "Polygon":
        return 1
    if geometry.get("type") == "MultiPolygon":
        return len(geometry.get("coordinates", []))
    return None

rows = []
source_counts = Counter()
parent_counts = Counter()
area_counts = Counter()
geometry_counts = Counter()
for key in ids:
    props, geometry, relative = features_by_id[key]
    meta = props.get("metadata", {})
    parent_id = props.get("parent_id")
    parent = hierarchy.get(parent_id, {})
    area = hierarchy.get(parent.get("parent_id"), {})
    source_id = meta.get("source_id")
    source_counts[source_id] += 1
    parent_counts[parent_id] += 1
    area_id = area.get("id")
    area_counts[str(area_id)] += 1
    geometry_type = geometry.get("type") if geometry else None
    geometry_counts[(geometry_type, polygon_components(geometry))] += 1
    rows.append({
        "id": key, "name": props.get("name"),
        "parent_id": parent_id, "parent_name": parent.get("name"),
        "parent_level": parent.get("level"), "parent_parent_id": parent.get("parent_id"),
        "area_id": area_id, "area_name": area.get("name"),
        "reference_owner": props.get("reference_owner"),
        "source_id": source_id, "source_name": meta.get("source_name"),
        "source_url": meta.get("source_url"), "source_license": meta.get("license"),
        "source_reference_year": meta.get("reference_year"),
        "source_original_id": meta.get("original_id"),
        "source_administrative_level": meta.get("administrative_level"),
        "source_parent_level": meta.get("parent_source_level"),
        "source_role": meta.get("source_role"), "selection_reason": meta.get("selection_reason"),
        "geography_part": relative, "geometry_type": geometry_type,
        "polygon_component_count": polygon_components(geometry),
        "original_geometry_sha256": meta.get("original_geometry_sha256"),
        "semantic_review_status": meta.get("semantic_review", {}).get("status"),
    })
with gzip.open(ROOT / "data/macro-foundation/regional-handoffs.json.gz", "rt", encoding="utf-8") as stream:
    inventory = json.load(stream)
regions = inventory.get("regions", [])
if isinstance(regions, dict):
    region_entry = regions.get(scope["region_id"])
else:
    region_entry = next((x for x in regions if x.get("region_id") == scope["region_id"]), None)
if region_entry is None:
    raise SystemExit(f"region missing from frozen macro inventory: {scope['region_id']}")
with (OUT / "subject-roster.jsonl").open("w", encoding="utf-8", newline="\n") as stream:
    for row in rows:
        stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
summary = {
    "method": "Exact issue subject IDs joined to current main world-index geography features and hierarchy rows; no geometry overlay or territorial approval is implied.",
    "issue_number": issue["number"],
    "issue_snapshot_path": "data/regional-review/regional-review-b9aef9289b79194e/source/issue-api-snapshot.json",
    "issue_scope_path": "data/regional-review/regional-review-b9aef9289b79194e/source/issue-scope.json",
    "issue_scope_sha256": hashlib.sha256((OWNED / "source/issue-scope.json").read_bytes()).hexdigest(),
    "baseline_commit": "4877ef4e99528615daf657a376b7605d1657f817",
    "subject_count_declared": scope["location_count"],
    "subject_count_unique": len(set(ids)),
    "subject_count_matched": len(features_by_id),
    "subject_ids_sha256_sorted_lf": hashlib.sha256(("\n".join(sorted(ids)) + "\n").encode()).hexdigest(),
    "region_id": scope["region_id"], "issue_release": scope["release"],
    "frozen_region_inventory_entry": region_entry,
    "area_scopes": scope["area_scopes"], "province_scopes": scope["province_scopes"],
    "source_record_counts": dict(sorted(source_counts.items())),
    "current_parent_counts": dict(sorted(parent_counts.items())),
    "current_area_counts": dict(sorted(area_counts.items())),
    "current_geometry_type_component_counts": {f"{key[0]}:{key[1]}": value for key, value in sorted(geometry_counts.items(), key=str)},
    "limits": [
        "Roster/parent joins and structural counts do not establish that an area or parent is geographically correct.",
        "Geometry component counts do not establish island completeness, boundary validity or source continuity.",
        "Source-specific identities, boundary overlays, license/vintage evidence and neighboring granularity require separate checks.",
    ],
}
(OUT / "scope-reproduction.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({
    "subjects": len(ids), "matched": len(features_by_id),
    "source_record_counts": summary["source_record_counts"],
    "parent_count": len(parent_counts), "parents": dict(sorted(parent_counts.items())),
    "geometry_components": summary["current_geometry_type_component_counts"],
    "issue_scope_sha256": summary["issue_scope_sha256"],
    "frozen_region_entry_found": True,
}, ensure_ascii=False, indent=2))
