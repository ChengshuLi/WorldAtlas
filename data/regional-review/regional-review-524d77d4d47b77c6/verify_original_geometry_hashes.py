#!/usr/bin/env python3
"""Compare Atlas original_geometry_sha256 values with exact retained 2017 source geometry."""
import hashlib
import json
import subprocess
from pathlib import Path

BASELINE = "062e0585025359c596a887e5a10d3e25479aff21"
OWNED = Path("data/regional-review/regional-review-524d77d4d47b77c6")
SOURCE = "data/regional-review/regional-review-9b38f58111efd323/sources/geoboundaries-chn-adm2-2017.geojson"

def git_blob(path):
    return subprocess.check_output(["git", "show", f"{BASELINE}:{path}"])

scope = json.loads((OWNED / "scope.json").read_text())
ids = {x for x in scope["member_location_ids"] if x.startswith("gb:CHN:ADM2:")}
index = json.loads(git_blob("data/world-index.json"))
current = {}
for relative in index["parts"]:
    for feature in json.loads(git_blob("data/" + relative))["features"]:
        feature_id = feature.get("properties", {}).get("id")
        if feature_id in ids:
            if feature_id in current:
                raise SystemExit(f"duplicate pinned feature {feature_id}")
            current[feature_id] = feature
if set(current) != ids:
    raise SystemExit(f"pinned index mismatch: found {len(current)} of {len(ids)} IDs")

source = json.loads(git_blob(SOURCE))
source_by_id = {f["properties"]["shapeID"]: f for f in source["features"]}
rows = []
for feature_id in sorted(ids):
    feature = current[feature_id]
    metadata = feature["properties"]["metadata"]
    source_id = metadata["original_id"]
    source_feature = source_by_id.get(source_id)
    if source_feature is None:
        raise SystemExit(f"source ID absent: {source_id}")
    retained_hash = hashlib.sha256(json.dumps(source_feature["geometry"], sort_keys=True).encode()).hexdigest()
    declared_hash = metadata.get("original_geometry_sha256")
    rows.append({
        "id": feature_id,
        "atlas_name": feature["properties"].get("name"),
        "source_id": source_id,
        "declared_original_geometry_sha256": declared_hash,
        "retained_source_geometry_sha256_python_json_sort_keys": retained_hash,
        "metadata_hash_matches_retained_source": declared_hash == retained_hash,
    })

print(json.dumps({
    "baseline_commit": BASELINE,
    "retained_source_path": SOURCE,
    "scope_rows": len(rows),
    "matches": sum(r["metadata_hash_matches_retained_source"] for r in rows),
    "mismatches": sum(not r["metadata_hash_matches_retained_source"] for r in rows),
    "rows": rows,
}, ensure_ascii=False))
