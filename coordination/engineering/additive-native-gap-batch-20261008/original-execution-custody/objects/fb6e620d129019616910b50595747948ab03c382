#!/usr/bin/env python3
"""Capture the exact 17 Atlas neighbor features from the pinned baseline parts."""
import hashlib, json, pathlib, subprocess
ROOT = pathlib.Path(__file__).resolve().parents[3]
CAMPAIGN = ROOT / "research/geography/alaska-thirteen-geometry-measurement-20261008"
BASELINE = "6c0ea95b7a8214ac1548161368bd952af136b5c2"
PARTS = {
    "data/geography/part-25.json": (4525239, "dada55df1b7f0f2a2b307f4aea071d0e48791e3105875755fe74a292a6763394"),
    "data/geography/part-26.json": (4608983, "44de5da3531f5641e0496ab7b01ed73871b40705e2a3eafdda470926872b6632"),
    "data/geography/part-27.json": (4863162, "e8df7555853e9262162c5e5d5c85e5c30be3fa8f0e6339bafec0e08323054758"),
}
EXPECTED = [
    "gb:USA:ADM2:52423323B13000193718373", "gb:USA:ADM2:52423323B16539688175930",
    "gb:USA:ADM2:52423323B20306178640915", "gb:USA:ADM2:52423323B44097334117837",
    "gb:USA:ADM2:52423323B46246640861022", "gb:USA:ADM2:52423323B55198873775030",
    "gb:USA:ADM2:52423323B57268278189593", "gb:USA:ADM2:52423323B58185108898",
    "gb:USA:ADM2:52423323B59860466047217", "gb:USA:ADM2:52423323B64721050065013",
    "gb:USA:ADM2:52423323B69219161179389", "gb:USA:ADM2:52423323B73641468228234",
    "gb:USA:ADM2:52423323B76828844452953", "gb:USA:ADM2:52423323B80008995120080",
    "gb:USA:ADM2:52423323B81884314913913", "gb:USA:ADM2:52423323B82121365400499",
    "gb:USA:ADM2:52423323B88813000222889",
]

def sha(b): return hashlib.sha256(b).hexdigest()
def canonical(v): return (json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)+"\n").encode()

found = {}
part_receipts = []
for path, (expected_bytes, expected_sha) in PARTS.items():
    raw = subprocess.check_output(["git", "-C", str(ROOT), "show", f"{BASELINE}:{path}"])
    if len(raw) != expected_bytes or sha(raw) != expected_sha:
        raise SystemExit(f"baseline part pin mismatch: {path}")
    collection = json.loads(raw)
    for feature in collection.get("features", []):
        shape_id = feature.get("properties", {}).get("id")
        if shape_id in EXPECTED:
            if shape_id in found:
                raise SystemExit(f"duplicate Atlas feature: {shape_id}")
            found[shape_id] = feature
    part_receipts.append({"commit": BASELINE, "path": path, "bytes": len(raw), "sha256": sha(raw)})
if set(found) != set(EXPECTED):
    raise SystemExit(f"incomplete neighbor source feature set: missing={sorted(set(EXPECTED)-set(found))}")
features = [found[shape_id] for shape_id in EXPECTED]
raw_fc = canonical({"type": "FeatureCollection", "features": features})
output = CAMPAIGN / "sources/atlas-neighbors/features.geojson"
output.write_bytes(raw_fc)
receipt = {
    "version": 1, "status": "source-bytes-verified", "scope": "exact 17 original Atlas neighbor features, source readback only",
    "baseline_commit": BASELINE, "source_parts": part_receipts,
    "expected_source_ids": EXPECTED, "found_source_ids": [f["properties"]["id"] for f in features],
    "feature_count": len(features), "feature_collection": {"path": output.relative_to(ROOT).as_posix(), "bytes": len(raw_fc), "sha256": sha(raw_fc)},
    "features": [{"source_id": f["properties"]["id"], "feature_id": f.get("id"),
        "original_shape_id": f["properties"].get("metadata", {}).get("original_id"),
        "geometry_sha256": sha(canonical(f["geometry"])), "geometry_type": f["geometry"]["type"]} for f in features],
    "limitations": ["This capture binds the original detector vintage; it does not establish current-world Atlas equivalence.",
        "No geometry operations, overlays, repairs, or approval were performed in this source capture."]
}
receipt_path = CAMPAIGN / "sources/atlas-neighbors/receipt.json"
receipt_path.write_bytes(canonical(receipt))
print(json.dumps({"status": receipt["status"], "feature_count": len(features), "feature_collection_bytes": len(raw_fc), "feature_collection_sha256": sha(raw_fc), "receipt_sha256": sha(receipt_path.read_bytes())}, indent=2))
