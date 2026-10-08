#!/usr/bin/env python3
"""Preserve issue-scope correction bytes and its pinned source pointer."""
import gzip
import hashlib
import json
import shutil
import struct
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OWNED = "research/geography/norway-adm2-source-fit-1492/"
COMMIT = "088ab05aeb16ddfa8f0c43e596533f3f11d5fcec"
BASELINE_SHA = "45d4356a46beddea43bfbd20231e0bf3671aa349643de29d0fa088ed5fbf5713"
VINTAGE = "issue-scope-correction-20261008"
OUTPUTS = ["issue-body-before.md", "issue-body-after.md", "correction.json"]
OLD_HASH = "eb2b6c25d1a8b8ead2bcb67f7e0423b5f1cc5609ac3f600bb98cd6d5cb11db40"
NEW_HASH = "eb2b6c25d1a2b8ead2bcb67f7e0423b5f1cc5609ac3f600bb98cd6d5cb11db40"
OLD_ID = "physical-component:" + OLD_HASH
NEW_ID = "physical-component:" + NEW_HASH


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    started = time.monotonic()
    own_script_hash = digest(Path(__file__).read_bytes())
    admission_path = ROOT / OWNED / "vintages/baseline-20261008/baseline-admission.json"
    admission_raw = admission_path.read_bytes()
    if digest(admission_raw) != BASELINE_SHA:
        raise SystemExit("Baseline admission changed")
    admission = json.loads(admission_raw)
    sys.path.insert(0, str(ROOT / "scripts"))
    from evidence.immutable import Baseline, NewVintage, canonical_json, MAX_FILE_BYTES

    baseline = Baseline(ROOT, COMMIT, admission["baseline_files"])
    writer = NewVintage(baseline, OWNED, VINTAGE, OUTPUTS)
    # Actual issue body is read only after a bounded complete output reserve.
    for name, size in (("issue-body-before.md", 64 * 1024),
                       ("issue-body-after.md", 64 * 1024),
                       ("correction.json", 16 * 1024),
                       ("publication.json", 4096)):
        baseline.admit("reserved-output:" + name, size)
    scope_base = ROOT / OWNED / "vintages/family-scope-20261008"
    scope_receipt_raw = (scope_base / "publication.json").read_bytes()
    scope_receipt = json.loads(scope_receipt_raw)
    scope_file_path = scope_base / "family-scope.json"
    scope_raw = scope_file_path.read_bytes()
    scope_desc = next((x for x in scope_receipt.get("outputs", [])
                       if x.get("path") == str(scope_file_path.relative_to(ROOT))), None)
    if not scope_desc or scope_desc.get("sha256") != digest(scope_raw) or scope_desc.get("bytes") != len(scope_raw):
        raise SystemExit("Family-scope output does not match its completion receipt")
    baseline.admit("captured-input:family-scope.json", len(scope_raw))
    family_scope = json.loads(scope_raw)
    if family_scope.get("scope", {}).get("complete_member_count") != 400 or family_scope.get("scope", {}).get("complete_positive_length_neighbor_count") != 36:
        raise SystemExit("Family-scope artifact does not confirm the issue's 400/36 context")
    before_rss = __import__("resource").getrusage(__import__("resource").RUSAGE_SELF).ru_maxrss
    before_disk = shutil.disk_usage(ROOT).free

    api = json.loads(subprocess.check_output(
        ["gh", "api", "repos/ChengshuLi/WorldAtlas/issues/1492"], text=True))
    body = api.get("body")
    if not isinstance(body, str):
        raise SystemExit("Issue body missing")
    if body.count(NEW_HASH) != 2 or OLD_HASH in body:
        raise SystemExit("Current issue body drifted from the exact two-occurrence correction")
    body_before = body.replace(NEW_HASH, OLD_HASH)
    before_raw, after_raw = body_before.encode("utf-8"), body.encode("utf-8")
    for name, raw in (("issue-body-before.md", before_raw), ("issue-body-after.md", after_raw)):
        if len(raw) > 64 * 1024:
            raise SystemExit("Issue body exceeded its admitted individual output reserve")
        baseline.admit("captured-input:" + name, len(raw))

    source_path = "coordination/engineering/global-source-comparisons-a-001-20261006/scientific/components-001.json.gz"
    source_gzip = baseline.pinned_bytes(source_path)
    decoded_size = struct.unpack("<I", source_gzip[-4:])[0]
    baseline.admit(source_path + ":decoded", decoded_size)
    decoded = gzip.decompress(source_gzip)
    if len(decoded) != decoded_size or decoded.count(NEW_ID.encode("ascii")) != 1 or OLD_ID.encode("ascii") in decoded:
        raise SystemExit("Pinned source shard does not support the exact correction")

    result = {
        "version": 1,
        "status": "issue-scope-id-correction-preserved",
        "issue": 1492,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "issue_updated_at": api.get("updated_at"),
        "issue_state": api.get("state"),
        "before_body": {"path": "issue-body-before.md", "bytes": len(before_raw), "sha256": digest(before_raw)},
        "after_body": {"path": "issue-body-after.md", "bytes": len(after_raw), "sha256": digest(after_raw)},
        "correction": {"old_id": OLD_ID, "new_id": NEW_ID, "occurrences_replaced": 2,
                       "scope_counts_unchanged": {"selected": family_scope["scope"]["selected_count"],
                                                  "family_members": family_scope["scope"]["complete_member_count"],
                                                  "neighbors": family_scope["scope"]["complete_positive_length_neighbor_count"]}},
        "pinned_source": {"commit": COMMIT, "path": source_path,
                          "bytes": baseline.pins[source_path]["bytes"],
                          "sha256": baseline.pins[source_path]["sha256"],
                          "decompressed_bytes": decoded_size,
                          "corrected_id_occurrences": decoded.count(NEW_ID.encode("ascii")),
                          "wrong_id_occurrences": decoded.count(OLD_ID.encode("ascii")),
                          "baseline_admission_sha256": BASELINE_SHA},
        "producer": {"path": str(Path(__file__).relative_to(ROOT)), "sha256": own_script_hash,
                     "python": sys.version, "elapsed_seconds": time.monotonic() - started},
        "admission": {"phase_bytes_before_publish": sum(baseline.consumed.values()),
                      "phase_limit_bytes": baseline.max_phase_bytes,
                      "disk_free_before_bytes": before_disk,
                      "disk_free_after_bytes": shutil.disk_usage(ROOT).free,
                      "process_max_rss_before_bytes": before_rss,
                      "process_max_rss_after_bytes": __import__("resource").getrusage(__import__("resource").RUSAGE_SELF).ru_maxrss},
        "limits": ["The before body is reconstructed from the immediately preceding recorded issue body by reversing only the exact two corrected identifier occurrences; all other bytes are preserved.",
                   "This is a clerical identifier correction, not a change in selected count or family scope."]
    }
    payloads = {"issue-body-before.md": before_raw,
                "issue-body-after.md": after_raw,
                "correction.json": canonical_json(result)}
    for name, raw in payloads.items():
        if len(raw) > MAX_FILE_BYTES:
            raise SystemExit("Correction output exceeds per-file limit")
    if digest(Path(__file__).read_bytes()) != own_script_hash:
        raise SystemExit("Producer changed during run")
    records = writer.publish_bytes(payloads)
    print(json.dumps({"status": result["status"], "correction": result["correction"],
                      "outputs": records}, indent=2))


if __name__ == "__main__":
    main()
