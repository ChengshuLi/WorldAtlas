#!/usr/bin/env python3
"""Join issue 396's exact subjects to immutable current-main atlas records."""
import hashlib
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[4]
PACKET = ROOT / "data/regional-review/regional-review-82307d5498a4432a"
BASELINE = "f1a6c0abc29de7bf7b7a081a8a9864b0450c0427"

def git_blob(path):
    return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{BASELINE}:{path}"])

issue = json.loads((PACKET / "source/issue-396-api-response.json").read_text())
import re
match = re.search(r"```json\s*(\{.*?\})\s*```", issue["body"], re.S)
if not match:
    raise SystemExit("workload JSON was not found in issue 396 snapshot")
scope = json.loads(match.group(1))
subject_ids = scope["member_location_ids"]
if len(subject_ids) != 34 or len(set(subject_ids)) != 34:
    raise SystemExit("issue workload must contain exactly 34 unique subjects")
index_raw = git_blob("data/world-index.json")
index = json.loads(index_raw)
index_features = {}
containing = {}
part_hashes = {}
parent_id = "framework:province:kemerovo-oblast:9da7abdd4dab"
for relative in index["parts"]:
    path = "data/" + relative
    raw = git_blob(path)
    part_hashes[path] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    collection = json.loads(raw)
    for feature in collection["features"]:
        feature_id = feature.get("id") or feature.get("properties", {}).get("id")
        if feature_id in subject_ids:
            if feature_id in index_features:
                raise SystemExit(f"duplicate baseline ID across parts: {feature_id}")
            index_features[feature_id] = feature
            containing[feature_id] = path
missing = sorted(set(subject_ids) - index_features.keys())
if missing:
    raise SystemExit(f"baseline main is missing {len(missing)} issue subjects: {missing}")
parent_ids = sorted({f.get("properties", {}).get("parent_id") for f in index_features.values()})
if parent_ids != [parent_id]:
    raise SystemExit(f"unexpected immediate parent IDs: {parent_ids}")
hierarchy_raw = git_blob("data/hierarchy.json")
parent = next((x for x in json.loads(hierarchy_raw) if x.get("id") == parent_id), None)
if parent is None:
    raise SystemExit(f"baseline hierarchy is missing immediate parent {parent_id}")
source = json.loads((PACKET / "source/issue-396-scoped-geoboundaries-features.geojson").read_text())
source_by_id = {"gb:RUS:ADM2:" + f["properties"]["shapeID"]: f for f in source["features"]}
if set(source_by_id) != set(subject_ids):
    raise SystemExit("retained source extract does not equal issue subject roster")
rows = []
for subject_id in sorted(subject_ids):
    atlas = index_features[subject_id]
    source_feature = source_by_id[subject_id]
    props = atlas["properties"]
    meta = props.get("metadata", {})
    source_geometry_hash = hashlib.sha256(json.dumps(source_feature["geometry"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    atlas_geometry_hash = hashlib.sha256(json.dumps(atlas["geometry"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    rows.append({
        "subject_id": subject_id,
        "source_shape_name": source_feature["properties"].get("shapeName"),
        "atlas_name": props.get("name"),
        "atlas_parent_id": props.get("parent_id"),
        "atlas_parent_name": parent.get("name"),
        "source_role_in_atlas_metadata": meta.get("source_role"),
        "source_layer_type": source_feature["properties"].get("shapeType"),
        "source_vintage": meta.get("reference_year"),
        "source_license": meta.get("license"),
        "source_url": meta.get("source_url"),
        "source_geometry_sha256": source_geometry_hash,
        "atlas_geometry_sha256": atlas_geometry_hash,
        "source_geometry_hash_matches_atlas_geometry": source_geometry_hash == atlas_geometry_hash,
        "atlas_semantic_review_status": meta.get("semantic_review", {}).get("status"),
        "atlas_containing_path": containing[subject_id],
    })
result = {
    "version": 1,
    "method": "Exact issue member IDs joined to raw source shapeID and immutable current-main world-index feature IDs; baseline parts scanned for duplicate/missing IDs.",
    "evaluation_commit": BASELINE,
    "issue_number": 396,
    "issue_scope_count": len(subject_ids),
    "matched_count": len(rows),
    "missing_ids": missing,
    "parent_ids": parent_ids,
    "parent_name": parent.get("name"),
    "world_index": {"path": "data/world-index.json", "sha256": hashlib.sha256(index_raw).hexdigest(), "bytes": len(index_raw)},
    "hierarchy": {"path": "data/hierarchy.json", "sha256": hashlib.sha256(hierarchy_raw).hexdigest(), "bytes": len(hierarchy_raw)},
    "scanned_part_hashes": part_hashes,
    "rows": rows,
    "limits": ["Source-hash correspondence confirms recorded provenance, not source authority, legal role, current boundaries, or boundary accuracy.", "Atlas semantic_review.status is an existing open review state, not a decision."]
}
out = PACKET / "findings/current-main-subject-join.json"
out.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
print(json.dumps({"matched": len(rows), "parent": result["parent_name"], "direct_geometry_hash_equal_count": sum(r["source_geometry_hash_matches_atlas_geometry"] for r in rows), "containing_paths": sorted(set(r["atlas_containing_path"] for r in rows)), "part_count_scanned": len(part_hashes)}))
