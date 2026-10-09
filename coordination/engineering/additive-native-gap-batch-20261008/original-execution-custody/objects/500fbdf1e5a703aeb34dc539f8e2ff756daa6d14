#!/usr/bin/env python3
"""Retain the pinned geoBoundaries USA ADM1 Alaska parent feature."""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import pathlib
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
CAMPAIGN = ROOT / "research/geography/alaska-thirteen-geometry-measurement-20261008"
CORPUS = ROOT / "coordination/engineering/original-geography-source-corpus-20261006"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main() -> None:
    catalogue_path = CORPUS / "catalogue.json"
    catalogue_bytes = catalogue_path.read_bytes()
    catalogue = json.loads(catalogue_bytes)
    product = next(row for row in catalogue["products"] if row.get("key") == "gb:USA:ADM1")
    if product.get("recorded_license") != "Public Domain" or product.get("feature_count") != 56:
        raise RuntimeError("catalogued source license or ADM1 feature count differs")
    if product.get("source_represented_year_claim") != "2018" or "9469f09" not in product.get("recorded_consumed_url", ""):
        raise RuntimeError("catalogued source vintage/release differs")
    if len(product.get("parts", [])) != 1:
        raise RuntimeError("expected one whole USA ADM1 source part")
    pin = product["parts"][0]
    source_path = ROOT / pin["path"]
    encoded = source_path.read_bytes()
    if len(encoded) != pin["bytes"] or sha(encoded) != pin["sha256"]:
        raise RuntimeError("encoded USA ADM1 source body differs from immutable catalogue")
    decoded = gzip.decompress(encoded)
    if len(decoded) != pin["uncompressed_bytes"] or sha(decoded) != pin["uncompressed_sha256"]:
        raise RuntimeError("decoded USA ADM1 source body differs from immutable catalogue")
    collection = json.loads(decoded)
    features = collection.get("features")
    if not isinstance(features, list) or len(features) != 56:
        raise RuntimeError("whole ADM1 source feature count differs")
    alaska = [row for row in features if row.get("properties", {}).get("shapeID") == "66186276B62688952876525"]
    if len(alaska) != 1:
        raise RuntimeError("pinned Alaska ADM1 parent feature is absent or duplicated")
    feature = alaska[0]
    props = feature.get("properties", {})
    if (props.get("shapeName"), props.get("shapeISO"), props.get("shapeGroup"), props.get("shapeType")) != (
            "Alaska", "US-AK", "USA", "ADM1"):
        raise RuntimeError("Alaska parent identity/role differs from the catalogue feature")
    parent_dir = CAMPAIGN / "sources/alaska-adm1-parent"
    parent_dir.mkdir(parents=True, exist_ok=True)
    geometry_path = parent_dir / "feature.geojson"
    receipt_path = parent_dir / "receipt.json"
    if geometry_path.exists() or receipt_path.exists():
        raise RuntimeError("refusing to overwrite an existing parent source capture")
    output = (json.dumps(feature, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
    receipt = {
        "version": 1,
        "status": "source-bytes-verified",
        "geometry_operations_invoked": False,
        "source": {
            "path": source_path.relative_to(ROOT).as_posix(),
            "encoded_bytes": len(encoded), "encoded_sha256": sha(encoded),
            "decoded_bytes": len(decoded), "decoded_sha256": sha(decoded),
            "catalogue_path": catalogue_path.relative_to(ROOT).as_posix(),
            "catalogue_sha256": sha(catalogue_bytes),
            "consumed_url": product["recorded_consumed_url"],
            "recorded_license": product["recorded_license"],
            "represented_year_claim": product["source_represented_year_claim"],
            "whole_feature_count": len(features),
        },
        "selected_parent": {
            "shape_id": props["shapeID"], "shape_name": props["shapeName"],
            "shape_iso": props["shapeISO"], "role": props["shapeType"],
            "geometry_type": feature["geometry"]["type"],
            "path": geometry_path.relative_to(ROOT).as_posix(),
            "bytes": len(output), "sha256": sha(output),
        },
        "limits": [
            "This is the simplified geoBoundaries USA ADM1 Alaska source parent, retained for geometric containment checks; it is not an authoritative political boundary or accuracy finding.",
            "The source represented year is the catalogue claim for the product, not an observation date for every feature.",
        ],
    }
    with tempfile.NamedTemporaryFile(dir=parent_dir, prefix=".parent-", delete=False) as temp:
        temp.write(output)
        temp.flush()
        os.fsync(temp.fileno())
        staged = pathlib.Path(temp.name)
    try:
        os.replace(staged, geometry_path)
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    finally:
        staged.unlink(missing_ok=True)
    print(json.dumps({"status": receipt["status"], "feature_count": len(features),
                      "parent_id": props["shapeID"], "output_bytes": len(output),
                      "output_sha256": sha(output)}))


if __name__ == "__main__":
    main()
