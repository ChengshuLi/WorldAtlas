#!/usr/bin/env python3
"""Read back the original detector's complete 13 fragment contact records."""
import gzip, hashlib, json, pathlib, subprocess
ROOT = pathlib.Path(__file__).resolve().parents[3]
CAMPAIGN = ROOT / "research/geography/alaska-thirteen-geometry-measurement-20261008"
FIT = ROOT / "research/geography/alaska-thirteen-source-fitness-20261008/sources"
BASE = "6c0ea95b7a8214ac1548161368bd952af136b5c2"
REPORT = "coordination/engineering/physical-gap-audit-1005-20261005-local18/detection-v4/report.json"
EXPECTED_REPORT_SHA = "230a49dbb3feab482d2946a7a4c75b9b8069acd841fc2609f2251cf6d2d58330"
CODE_COMMIT = "b6e0d0d21cfd6dde68c3c292c9513d3a24896a11"
CODE_PATH = "scripts/audit-physical-gaps.py"
CODE_SHA = "7656263b33f222942f709c3b9671c344dd5350cafd2726423c6632b38a667f07"

sha = lambda b: hashlib.sha256(b).hexdigest()
def canonical(v): return (json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)+"\n").encode()
def git(rev, path): return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{rev}:{path}"])

report_raw = git(BASE, REPORT)
if sha(report_raw) != EXPECTED_REPORT_SHA:
    raise SystemExit("original detector report does not match source pin")
report = json.loads(report_raw)
if report.get("baseline_commit") != "548c5f89f00271050823076a84695bb41e1b8454" or report.get("locations") != 49625 or report.get("invalid_locations"):
    raise SystemExit("original detector full-scan baseline/count differs")
code = git(CODE_COMMIT, CODE_PATH)
if sha(code) != CODE_SHA or b"'exact_location_contacts': detector.contacts(piece)" not in code:
    raise SystemExit("original detector contact-list producer contract differs")

screen = json.loads((FIT / "candidate-source-screen.json").read_bytes())
candidates = json.loads((FIT / "candidate-components.geojson").read_bytes())
ids = [row["component_id"] for row in screen["findings"]]
if len(ids) != 13 or len(set(ids)) != 13 or len(candidates["features"]) != 13:
    raise SystemExit("the exact 13-component input roster differs")
bindings = {f["id"]: f["properties"].get("fragment_bindings", []) for f in candidates["features"]}
if set(bindings) != set(ids) or any(len(rows) != 1 for rows in bindings.values()):
    raise SystemExit("a candidate does not bind exactly one whole detector fragment")
expected_records = {}
for component_id, rows in bindings.items():
    fragment = rows[0]
    expected_records[fragment["id"]] = (component_id, fragment["feature_sha256"])
if len(expected_records) != 13:
    raise SystemExit("fragment identities are not unique")

found = {}
used_shards = []
for pin in report["outputs"]:
    raw = git(BASE, pin["path"])
    if len(raw) != pin["bytes"] or sha(raw) != pin["sha256"]:
        raise SystemExit(f"original candidate shard source pin mismatch: {pin['path']}")
    decoded = gzip.decompress(raw)
    if len(decoded) != pin["uncompressed_bytes"] or sha(decoded) != pin["uncompressed_sha256"]:
        raise SystemExit(f"original candidate shard decoded pin mismatch: {pin['path']}")
    collection = json.loads(decoded)
    for feature in collection.get("features", []):
        fragment_id = feature.get("id")
        if fragment_id not in expected_records:
            continue
        if fragment_id in found:
            raise SystemExit(f"duplicate original fragment record: {fragment_id}")
        component_id, expected_feature_sha = expected_records[fragment_id]
        actual_feature_sha = sha(canonical(feature))
        if actual_feature_sha != expected_feature_sha:
            raise SystemExit(f"whole-fragment source feature hash mismatch: {fragment_id}")
        if not isinstance(feature.get("properties", {}).get("exact_location_contacts"), list):
            raise SystemExit(f"complete original contacts are absent: {fragment_id}")
        tile_id = int(fragment_id.split(":", 2)[1])
        if tile_id not in {row["id"] for row in report["tiles"] if row["status"] == "checked"}:
            raise SystemExit(f"original fragment tile is not recorded checked: {fragment_id}")
        candidate = next(f for f in candidates["features"] if f["id"] == component_id)
        if sha(canonical(feature["geometry"])) != sha(canonical(candidate["geometry"])):
            raise SystemExit(f"whole fragment geometry does not equal current component geometry: {fragment_id}")
        found[fragment_id] = {"id": fragment_id, "component_id": component_id, "feature": feature,
            "original_feature_sha256": actual_feature_sha,
            "geometry_sha256": sha(canonical(feature["geometry"])),
            "exact_location_contact_count": len(feature["properties"]["exact_location_contacts"]),
            "source_shard": pin["path"], "source_shard_sha256": pin["sha256"],
            "tile": feature["properties"]["tile"]}
    if any(key in found for key in expected_records):
        used_shards.append({"commit": BASE, "path": pin["path"], "bytes": len(raw), "sha256": sha(raw),
            "uncompressed_bytes": len(decoded), "uncompressed_sha256": sha(decoded)})
    del raw, decoded, collection
if set(found) != set(expected_records):
    raise SystemExit(f"original fragment records incomplete: missing={sorted(set(expected_records)-set(found))}")

candidate_fc = {"type": "FeatureCollection", "features": [
    {"type": "Feature", "id": fragment_id, "properties": {"component_id": row["component_id"],
      "original_feature_sha256": row["original_feature_sha256"], "geometry_sha256": row["geometry_sha256"],
      "exact_location_contact_count": row["exact_location_contact_count"], "tile": row["tile"],
      "source_shard": row["source_shard"], "source_shard_sha256": row["source_shard_sha256"],
      "original_detector_properties": row["feature"]["properties"]},
     "geometry": row["feature"]["geometry"]}
    for fragment_id, row in sorted(found.items())]}
blob = canonical(candidate_fc)
output = CAMPAIGN / "sources/original-fragment-contacts/features.geojson"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_bytes(blob)
receipt = {"version": 1, "status": "complete-recorded-contacts", "scope": "exact 13 assigned whole original detector fragments",
 "baseline_commit": BASE, "original_detector_report": {"path": REPORT, "bytes": len(report_raw), "sha256": sha(report_raw),
   "full_location_count": report["locations"], "invalid_location_count": len(report["invalid_locations"]), "baseline_commit": report["baseline_commit"]},
 "original_detector_code": {"commit": CODE_COMMIT, "path": CODE_PATH, "bytes": len(code), "sha256": sha(code), "complete_contact_field": "exact_location_contacts"},
 "source_candidate_shards": used_shards, "component_count": 13, "component_ids": ids,
 "fragment_count": len(found), "fragments": [{k: v for k, v in row.items() if k != "feature"} for _, row in sorted(found.items())],
 "output": {"path": output.relative_to(ROOT).as_posix(), "bytes": len(blob), "sha256": sha(blob)},
 "contact_record_contract": "original detector records detector.contacts(piece) on every emitted fragment; retained per-feature contact list is complete for this detector run and its exact baseline vintage",
 "limits": ["Original detector contact lists are source-vintage-specific to the pinned full Atlas run.",
   "This readback performs no overlay or geometry repair and grants no correction or publication approval."]}
receipt_path = CAMPAIGN / "sources/original-fragment-contacts/receipt.json"
receipt_path.write_bytes(canonical(receipt))
print(json.dumps({"status": receipt["status"], "fragments": len(found), "contacts": sum(x["exact_location_contact_count"] for x in found.values()),
 "output_bytes": len(blob), "output_sha256": sha(blob), "receipt_sha256": sha(receipt_path.read_bytes()), "shards": [x["path"] for x in used_shards]}, indent=2))
