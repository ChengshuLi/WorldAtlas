#!/usr/bin/env python3
"""Restore the complete selected family from pinned, split upstream records."""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[2]
ROUTE = REPO / "coordination/engineering/global-actionability-routing-20261007"
PHYSICAL = REPO / "coordination/engineering/physical-gap-components-1005-20261005-local19"
OUT = PACKET / "inputs"
FAMILY_ID = "gap-source-batch:0a4b122a996ef2050e5cac94"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def split_jsonl(shards: list[Path]):
    carry = b""
    for path in shards:
        chunk = gzip.decompress(path.read_bytes())
        records = (carry + chunk).split(b"\n")
        carry = records.pop()
        for line in records:
            if line:
                yield json.loads(line)
    if carry:
        yield json.loads(carry)


def json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def main() -> None:
    family_rows = list(split_jsonl(sorted((ROUTE / "results").glob("families-*.bin.gz"))))
    selected = [row for row in family_rows if row.get("id") == FAMILY_ID]
    if len(selected) != 1:
        raise ValueError(f"Expected one complete family row, found {len(selected)}")
    family = selected[0]
    component_ids = set(family["complete_component_ids"])
    contact_ids = set(family["complete_positive_length_neighbor_ids"])
    if len(component_ids) != 48 or len(contact_ids) != 8:
        raise ValueError("The frozen scope is not the complete 48-component/eight-contact family")

    route_components = [r for r in split_jsonl(sorted((ROUTE / "results").glob("components-*.bin.gz")))
                        if r.get("component") in component_ids]
    if {r.get("component") for r in route_components} != component_ids:
        raise ValueError("The route component stream does not contain the complete family")
    admin_rows = [r for r in split_jsonl(sorted((ROUTE / "results").glob("admin-bindings-*.bin.gz")))
                  if r.get("component") in component_ids]
    if {r.get("component") for r in admin_rows} != component_ids:
        raise ValueError("The route admin-binding stream does not contain the complete family")

    custody = json.loads((PHYSICAL / "custody-v1/index.json").read_bytes())
    aliases = {a["original"]["path"]: a for a in custody["aliases"]}
    physical_ids = [f"{PHYSICAL.relative_to(REPO)}/components-v3/components-{i:03d}.json.gz" for i in range(11)]
    physical_features = {}
    physical_receipts = []
    for original_path in physical_ids:
        alias = aliases[original_path]
        payload_path = REPO / alias["payload"]
        encoded = payload_path.read_bytes()
        descriptor = alias["original"]
        if len(encoded) != descriptor["bytes"] or sha256(encoded) != descriptor["sha256"]:
            raise ValueError(f"Custody payload mismatch: {payload_path}")
        decoded = gzip.decompress(encoded)
        if len(decoded) != descriptor["uncompressed_bytes"] or sha256(decoded) != descriptor["uncompressed_sha256"]:
            raise ValueError(f"Decoded custody payload mismatch: {payload_path}")
        collection = json.loads(decoded)
        for feature in collection.get("features", []):
            if feature.get("id") in component_ids:
                if feature["id"] in physical_features:
                    raise ValueError(f"Duplicate physical source feature: {feature['id']}")
                physical_features[feature["id"]] = feature
        physical_receipts.append({"original_path": original_path, "payload_path": alias["payload"],
                                  "bytes": len(encoded), "sha256": sha256(encoded),
                                  "decoded_bytes": len(decoded), "decoded_sha256": sha256(decoded)})
    if set(physical_features) != component_ids:
        raise ValueError(f"Incomplete physical source roster: {len(physical_features)}/48")

    route_by_id = {r["component"]: r for r in route_components}
    geometry_hash_mismatches = []
    feature_hash_mismatches = []
    for cid, feature in physical_features.items():
        route_row = route_by_id[cid]
        if sha256(json_bytes(feature["geometry"])) != route_row.get("current_geometry_sha256"):
            geometry_hash_mismatches.append(cid)
        if sha256(json_bytes(feature)) != route_row.get("current_feature_sha256"):
            feature_hash_mismatches.append(cid)
    if geometry_hash_mismatches or feature_hash_mismatches:
        raise ValueError(f"Current geometry hash mismatch for {len(geometry_hash_mismatches)} components")

    contact_features = []
    for path in sorted((REPO / "data/geography").glob("part-*.json")):
        if not path.exists():
            continue
        doc = json.loads(path.read_bytes())
        features = doc.get("features", []) if isinstance(doc, dict) else doc
        contact_features.extend(f for f in features if f.get("id") in contact_ids or
                                f.get("properties", {}).get("id") in contact_ids)
    contact_by_id = {f.get("id", f.get("properties", {}).get("id")): f for f in contact_features}
    if set(contact_by_id) != contact_ids:
        raise ValueError(f"Current contact roster mismatch: {len(contact_by_id)}/8")

    OUT.mkdir(parents=True, exist_ok=True)
    outputs = {
        "complete-family.json": json_bytes(family),
        "route-component-rows.jsonl": b"".join(json_bytes(r) for r in sorted(route_components, key=lambda x: x["component"])),
        "route-admin-binding-rows.jsonl": b"".join(json_bytes(r) for r in sorted(admin_rows, key=lambda x: x["component"])),
        "physical-component-features.geojson": json_bytes({"type": "FeatureCollection", "features":
            [physical_features[i] for i in sorted(component_ids)]}),
        "current-contact-features.geojson": json_bytes({"type": "FeatureCollection", "features":
            [contact_by_id[i] for i in sorted(contact_ids)]}),
    }
    for name, data in outputs.items():
        (OUT / name).write_bytes(data)
    receipt = {
        "family_id": FAMILY_ID,
        "component_count": len(component_ids),
        "contact_count": len(contact_ids),
        "component_ids": sorted(component_ids),
        "contact_ids": sorted(contact_ids),
        "physical_source_payloads": physical_receipts,
        "geometry_hash_mismatches": geometry_hash_mismatches,
        "feature_hash_mismatches": feature_hash_mismatches,
        "outputs": {name: {"bytes": len(data), "sha256": sha256(data)} for name, data in outputs.items()},
        "method_limits": ["Restores source/route bytes without changing geometry.",
                          "Recorded source names and ownership are not validated by this extraction step."],
    }
    (OUT / "restoration-receipt.json").write_bytes(json_bytes(receipt))
    print(json.dumps({"components": len(component_ids), "contacts": len(contact_ids),
                      "geometry_hash_mismatches": geometry_hash_mismatches,
                      "feature_hash_mismatches": feature_hash_mismatches,
                      "outputs": receipt["outputs"]}, indent=2))


if __name__ == "__main__":
    main()
