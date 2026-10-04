#!/usr/bin/env python3
"""Exercise rejection paths without creating or modifying evidence outputs."""
import subprocess, sys
from pathlib import Path
from tempfile import TemporaryDirectory
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import build_packet as bp
from scripts.evidence.immutable import Baseline, descriptor, write_new_vintage
checks = []
def rejects(label, fn):
    try: fn()
    except Exception: checks.append(label)
    else: raise AssertionError(f"negative control did not reject: {label}")

rejects("bad immutable commit", lambda: bp.git_blob("0" * 40, "data/hierarchy.json"))
real = Baseline(bp.ROOT, bp.BASELINE_COMMIT, bp.baseline_input_descriptors(bp.json_blob(bp.SOURCE_SNAPSHOT_COMMIT, bp.ORIGINAL_PACKET + "baseline-extract.json")))
rejects("duplicate requested subject", lambda: real.subjects([bp.IDS[0], bp.IDS[0]]))
rejects("missing requested subject", lambda: real.subjects(["atlas:does-not-exist"]))
receipt, crosswalk, _ = bp.build_packet()
wrong = {row["id"]: row["actual_containing_file"] for row in crosswalk["subjects"]}
wrong[bp.IDS[0]] = dict(wrong[bp.IDS[0]], path="data/geography/part-13.json")
rejects("wrong actual containing part", lambda: bp.validate_actual_containing_parts(wrong))
mutated = [dict(row) for row in receipt["baseline_files"]]
mutated[0]["sha256"] = "0" * 64
rejects("changed whole-file descriptor", lambda: Baseline(bp.ROOT, bp.BASELINE_COMMIT, mutated))
with TemporaryDirectory() as td:
    repo = Path(td); (repo / "x").write_bytes(b"pin")
    subprocess.run(["git", "-C", td, "init", "-q"], check=True)
    subprocess.run(["git", "-C", td, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "add", "x"], check=True)
    subprocess.run(["git", "-C", td, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "pin"], check=True)
    commit = subprocess.check_output(["git", "-C", td, "rev-parse", "HEAD"], text=True).strip()
    pin = Baseline(repo, commit, [descriptor("x", b"pin")])
    path = repo / "research/geography/control/vintages/control/kept.json"
    path.parent.mkdir(parents=True); path.write_bytes(b"keep"); before = path.read_bytes()
    rejects("exclusive overwrite", lambda: write_new_vintage(pin, "research/geography/control/", "control", "kept.json", {"replace": True}))
    assert path.read_bytes() == before, "overwrite control changed existing bytes"
expected = {"bad immutable commit", "duplicate requested subject", "missing requested subject", "wrong actual containing part", "changed whole-file descriptor", "exclusive overwrite"}
assert set(checks) == expected
print({"result": "PASS", "rejected_controls": sorted(checks), "existing_output_preserved": True})
