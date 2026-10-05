#!/usr/bin/env python3
"""Reproduce the exact #467 source-to-atlas scope inventory from retained inputs."""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKET = Path(__file__).resolve().parent


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


issue = read_json(PACKET / "issue-467-snapshot.json")
body = issue["body"]
start = body.index("```json\n") + len("```json\n")
end = body.index("\n```", start)
scope = json.loads(body[start:end])
ids = scope["member_location_ids"]
assert len(ids) == scope["location_count"] == 224
assert hashlib.sha256("\n".join(ids).encode()).hexdigest() == scope["member_location_ids_sha256"]

inventory_path = ROOT / "data/macro-foundation/current-membership-inventory.json.gz"
inventory = json.loads(gzip.decompress(inventory_path.read_bytes()))
hierarchy_path = ROOT / "data/hierarchy.json"
hierarchy = read_json(hierarchy_path)
parent_by_id = {row["id"]: row for row in hierarchy}

features = {}
for relative in read_json(ROOT / "data/world-index.json")["parts"]:
    part = read_json(ROOT / "data" / relative)
    for feature in part["features"]:
        properties = feature["properties"]
        if properties["id"] in ids:
            features[properties["id"]] = properties
assert set(features) == set(ids), f"missing scoped source features: {set(ids) - set(features)}"

source_paths = {
    "gb:BEN:ADM1": PACKET / "sources/geoboundaries-9469f09/BEN-ADM1/geoBoundaries-BEN-ADM1.geojson",
    "gb:BEN:ADM2": PACKET / "sources/geoboundaries-9469f09/BEN-ADM2/geoBoundaries-BEN-ADM2.geojson",
    "gb:BFA:ADM2": PACKET / "sources/geoboundaries-9469f09/BFA-ADM2/geoBoundaries-BFA-ADM2.geojson",
    "gb:BFA:ADM3": PACKET / "sources/geoboundaries-9469f09/BFA-ADM3/geoBoundaries-BFA-ADM3.geojson",
}
source_features = {}
for source_id, path in source_paths.items():
    source = read_json(path)
    expected_country, expected_level = source_id.split(":")[1:]
    for feature in source["features"]:
        properties = feature["properties"]
        key = f"gb:{expected_country}:{expected_level}:{properties['shapeID']}"
        source_features[key] = feature

missing_source = set(ids) - set(source_features)
assert not missing_source, f"scope members absent from retained sources: {sorted(missing_source)}"

rows = []
for identifier in ids:
    atlas = features[identifier]
    source_feature = source_features[identifier]
    source = source_feature["properties"]
    source_geometry_sha256 = hashlib.sha256(
        json.dumps(source_feature["geometry"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    parent_id = atlas["parent_id"]
    parent = parent_by_id[parent_id]
    rows.append({
        "id": identifier,
        "source_id": atlas["metadata"]["source_id"],
        "source_role_declared": atlas["metadata"].get("source_role"),
        "source_role_selection_reason": atlas["metadata"].get("selection_reason"),
        "name": atlas["name"],
        "source_name": source["shapeName"],
        "name_match": atlas["name"] == source["shapeName"],
        "source_shape_type": source["shapeType"],
        "atlas_parent_id": parent_id,
        "atlas_parent_name": parent["name"],
        "atlas_parent_tier": parent["level"],
        "metadata_parent_source_level": atlas["metadata"].get("parent_source_level"),
        "metadata_parent_match": atlas["metadata"].get("parent_match"),
        "reference_owner": atlas.get("reference_owner"),
        "original_geometry_sha256": atlas["metadata"].get("original_geometry_sha256"),
        "source_geometry_sha256": source_geometry_sha256,
        "source_geometry_type": source_feature["geometry"]["type"],
    })

source_hashes = {source_id: digest(path) for source_id, path in source_paths.items()}
metadata_hashes = {}
for source_id in source_paths:
    country, level = source_id.split(":")[1:]
    path = PACKET / f"sources/geoboundaries-9469f09/{country}-{level}/geoBoundaries-{country}-{level}-metaData.json"
    metadata_hashes[source_id] = digest(path)

output = {
    "version": 1,
    "issue": 467,
    "retrieval_date": "2026-10-04",
    "scope": scope,
    "baseline": {
        "main_commit": "fdab75892d979b995a1d20f311006aeeddb770b5",
        "inventory_path": "data/macro-foundation/current-membership-inventory.json.gz",
        "inventory_sha256": digest(inventory_path),
        "hierarchy_path": "data/hierarchy.json",
        "hierarchy_sha256": digest(hierarchy_path),
    },
    "sources": {
        source_id: {
            "geojson_path": str(path.relative_to(PACKET)),
            "geojson_sha256": source_hashes[source_id],
            "metadata_path": str((PACKET / f"sources/geoboundaries-9469f09/{source_id.split(':')[1]}-{source_id.split(':')[2]}/geoBoundaries-{source_id.split(':')[1]}-{source_id.split(':')[2]}-metaData.json").relative_to(PACKET)),
            "metadata_sha256": metadata_hashes[source_id],
            "retained_feature_count": len(read_json(path)["features"]),
            "scope_feature_count": sum(row["source_id"] == source_id for row in rows),
            "purpose": "parent-reference-only" if source_id in {"gb:BEN:ADM1", "gb:BFA:ADM2"} else "scoped-location-source",
        }
        for source_id, path in source_paths.items()
    },
    "exact_subjects": ids,
    "units": rows,
}
out_path = PACKET / "scope-source-inventory.json"
out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"output": str(out_path.relative_to(ROOT)), "subjects": len(rows), "source_hashes": source_hashes, "metadata_hashes": metadata_hashes, "scope_name_matches": sum(row["name_match"] for row in rows)}, indent=2))
