#!/usr/bin/env python3
"""Exercise immutable-input rejection and exclusive-write controls."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research/geography/southern-indian-ocean-baseline-pins"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(OUT))
import build_packet as bp  # noqa: E402
from scripts.evidence.immutable import Baseline, descriptor, write_new_vintage  # noqa: E402


def rejects(label, fn, labels):
    try:
        fn()
    except Exception:
        labels.add(label)
    else:
        raise AssertionError("negative control did not reject: " + label)


scope = json.loads((OUT / "scope.json").read_text())
receipt, _, _, _ = bp.build_packet()
baseline_files = receipt["baseline_files"]
results = set()

# A different but valid commit is rejected by the issue-scoped pin check before
# any output path is passed to the exclusive writer.
rejects("changed baseline commit", lambda: bp.validate_request_pins(
    scope, baseline_commit=bp.SOURCE_SNAPSHOT_COMMIT), results)
rejects("changed source snapshot commit", lambda: bp.validate_request_pins(
    scope, source_snapshot_commit=bp.BASELINE_COMMIT), results)
rejects("unknown immutable commit", lambda: bp.git_blob("0" * 40, "data/hierarchy.json"), results)
rejects("duplicate subject", lambda: Baseline(ROOT, bp.BASELINE_COMMIT, baseline_files).subjects([bp.IDS[0], bp.IDS[0]]), results)
rejects("missing subject", lambda: Baseline(ROOT, bp.BASELINE_COMMIT, baseline_files).subjects(["atlas:coverage:missing"]), results)

changed = [dict(row) for row in baseline_files]
changed[0]["sha256"] = "0" * 64
rejects("changed baseline descriptor", lambda: Baseline(ROOT, bp.BASELINE_COMMIT, changed), results)
packet_row = bp.tree_inventory(bp.SOURCE_SNAPSHOT_COMMIT, bp.ORIGINAL_PACKET)[0]
raw = bp.git_blob(bp.SOURCE_SNAPSHOT_COMMIT, packet_row["path"])
rejects("changed source snapshot bytes", lambda: bp.assert_snapshot_file(
    packet_row["path"], raw + b"changed", packet_row), results)

crosswalk = {identity: {"path": "data/geography/part-28.json"} for identity in bp.IDS}
crosswalk[bp.IDS[0]] = {"path": "data/geography/part-13.json"}
expected = {identity: "data/geography/part-28.json" for identity in bp.IDS}
rejects("wrong actual containing file", lambda: bp.validate_containing_crosswalk(crosswalk, expected), results)

with tempfile.TemporaryDirectory(prefix=".immutable-control-", dir=OUT) as temporary:
    repo = Path(temporary)
    (repo / "x").write_bytes(b"pinned")
    subprocess.run(["git", "-C", temporary, "init", "-q"], check=True)
    git_env = ["git", "-C", temporary, "-c", "user.name=Control", "-c", "user.email=control@example.invalid"]
    subprocess.run(git_env + ["add", "x"], check=True)
    subprocess.run(git_env + ["commit", "-qm", "control pin"], check=True)
    commit = subprocess.check_output(["git", "-C", temporary, "rev-parse", "HEAD"], text=True).strip()
    pinned = Baseline(repo, commit, [descriptor("x", b"pinned")])
    existing = repo / "research/geography/control/vintages/control/kept.json"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"preserve")
    before = existing.read_bytes()
    rejects("overwrite refusal", lambda: write_new_vintage(
        pinned, "research/geography/control/", "control", "kept.json", {"changed": True}), results)
    if existing.read_bytes() != before:
        raise AssertionError("overwrite control modified its existing bytes")
    absent = repo / "research/geography/control/vintages/control/new.json"
    bad = [descriptor("x", b"pinned")]
    bad[0]["sha256"] = "0" * 64
    rejects("changed pin before output creation", lambda: write_new_vintage(
        Baseline(repo, commit, bad), "research/geography/control/", "control", "new.json", {"x": 1}), results)
    if absent.exists():
        raise AssertionError("failed pin control created output")
    results.add("existing bytes preserved")

expected_results = {
    "changed baseline commit", "changed source snapshot commit", "unknown immutable commit",
    "duplicate subject", "missing subject", "changed baseline descriptor", "changed source snapshot bytes",
    "wrong actual containing file", "overwrite refusal", "changed pin before output creation",
    "existing bytes preserved",
}
if results != expected_results:
    raise AssertionError(f"control set mismatch: {sorted(results ^ expected_results)}")
print(json.dumps({"result": "PASS", "controls": sorted(results),
                  "existing_output_preserved": True, "failed_pin_created_no_output": True}, indent=2))
