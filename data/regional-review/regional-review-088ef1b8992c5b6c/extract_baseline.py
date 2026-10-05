#!/usr/bin/env python3
"""Re-extract the exact #468 Atlas subset from its acceptance baseline."""
import gzip
import hashlib
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[3]
OWNED = ROOT / "data/regional-review/regional-review-088ef1b8992c5b6c"
COMMIT = "80fb0e7744809438d02881f8d3435d9efb71d2e8"
scope = json.loads((OWNED / "issue-scope-pinned.json").read_text())
requested = set(scope["member_location_ids"])


def blob(path):
    return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{COMMIT}:{path}"])


def sha(value):
    return hashlib.sha256(value).hexdigest()


index_raw = blob("data/world-index.json")
hierarchy_raw = blob("data/hierarchy.json")
macro_raw = blob("data/macro-foundation/regional-handoffs.json.gz")
publication_validation_raw = blob("data/validation/macro-publication-v5.json")
index = json.loads(index_raw)
hierarchy_rows = json.loads(hierarchy_raw)
hierarchy = {row["id"]: row for row in hierarchy_rows}
macro = json.loads(gzip.decompress(macro_raw))
publication_validation = json.loads(publication_validation_raw)
region = next(row for row in macro["regions"] if row["region_id"] == scope["region_id"])
if (
    publication_validation["macro_certificate_sha256"] != scope["macro_certificate_sha256"]
    or publication_validation["release"] != scope["release"]
    or region["envelope"]["geometry_sha256"] != scope["frozen_region_geometry_sha256"]
    or region["envelope"]["member_location_ids_sha256"] != scope["frozen_region_member_ids_sha256"]
    or region["regional_interiors_approved"]
    or region["location_attribute_imports_ready"]
):
    raise SystemExit("Pinned macro envelope or approval gate differs from the issue scope")
features, inventory, source_lineage = [], [], []
for part in index["parts"]:
    raw = blob("data/" + part)
    inventory.append({"path": "data/" + part, "sha256": sha(raw), "bytes": len(raw)})
    for feature in json.loads(raw)["features"]:
        identity = feature.get("properties", {}).get("id")
        if identity in requested:
            features.append(feature)
            props = feature["properties"]
            source_lineage.append({
                "id": identity,
                "name": props.get("name"),
                "parent_id": props.get("parent_id"),
                "parent_name": hierarchy.get(props.get("parent_id"), {}).get("name"),
                "source_id": props.get("metadata", {}).get("source_id"),
                "source_role": props.get("metadata", {}).get("source_role"),
                "source_vintage": props.get("metadata", {}).get("source_vintage"),
            })
if {f["properties"]["id"] for f in features} != requested or len(features) != len(requested):
    raise SystemExit("Baseline member IDs do not exactly equal the issue roster")
features.sort(key=lambda f: f["properties"]["id"])
geojson = json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False,
                    sort_keys=True, separators=(",", ":")).encode()
compressed = gzip.compress(geojson, compresslevel=9, mtime=0)
(OWNED / "baseline-members.geojson.gz").write_bytes(compressed)
(OWNED / "baseline-feature-inventory.csv").write_text(
    "path,sha256,bytes\n" + "".join(f'{r["path"]},{r["sha256"]},{r["bytes"]}\n' for r in inventory)
)
parent_ids = {row["parent_id"] for row in source_lineage if row["parent_id"]}
parent_ids.update(row["id"] for row in scope["province_scopes"])
parent_ids.update(row["id"] for row in scope["area_scopes"])
parent_ids.add(scope["region_id"])
for identity in list(parent_ids):
    parent = hierarchy.get(identity, {})
    if parent.get("parent_id"):
        parent_ids.add(parent["parent_id"])
parents = sorted(identity for identity in parent_ids if identity in hierarchy)
(OWNED / "baseline-parent-context.json").write_text(json.dumps({
    "baseline_commit": COMMIT,
    "parents": [hierarchy[p] for p in parents],
    "macro_handoffs_sha256": sha(macro_raw),
    "macro_publication_validation_sha256": sha(publication_validation_raw),
    "macro_certificate_sha256": macro["macro_certificate_sha256"],
    "issue_macro_certificate_sha256": publication_validation["macro_certificate_sha256"],
    "region_envelope": region["envelope"],
    "regional_interiors_approved": region["regional_interiors_approved"],
    "location_attribute_imports_ready": region["location_attribute_imports_ready"],
    "area_scopes": scope["area_scopes"],
    "exact_scope_feature_count": len(features),
}, ensure_ascii=False, indent=2) + "\n")
(OWNED / "baseline-source-lineage.json").write_text(json.dumps({
    "baseline_commit": COMMIT,
    "features": source_lineage,
}, ensure_ascii=False, indent=2) + "\n")
receipt = {
    "baseline_commit": COMMIT,
    "issue_number": 468,
    "scope_batch_id": scope["batch_id"],
    "scope_release": scope["release"],
    "scope_count": scope["location_count"],
    "scope_ids_sha256": scope["member_location_ids_sha256"],
    "world_index_sha256": sha(index_raw),
    "hierarchy_sha256": sha(hierarchy_raw),
    "macro_handoffs_sha256": sha(macro_raw),
    "macro_publication_validation_sha256": sha(publication_validation_raw),
    "macro_certificate_sha256": publication_validation["macro_certificate_sha256"],
    "feature_inventory": inventory,
    "extracted_geojson_sha256": sha(geojson),
    "compressed_geojson_sha256": sha(compressed),
    "compressed_geojson_bytes": len(compressed),
}
(OWNED / "baseline-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt, indent=2))
