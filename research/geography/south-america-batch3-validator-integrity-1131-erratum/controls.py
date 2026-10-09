#!/usr/bin/env python3
"""Exercise actual CLI rejection paths and retain compact control receipts."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

from reproduce import ROOT, OWNED, LEDGER, canonical, sha

HERE = Path(__file__).resolve().parent
CLI = HERE / "reproduce.py"


def run(args):
    return subprocess.run([sys.executable, str(CLI), *args], cwd=ROOT,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def record(case_id, passed, detail, raw=None):
    return {"id": case_id, "passed": bool(passed), "detail": detail,
            "fixture_sha256": sha(raw) if raw is not None else None,
            "fixture_bytes": len(raw) if raw is not None else None}


def check_reject(case_id, doc, expected_fragment):
    raw = canonical(doc)
    fixture_dir = ROOT / OWNED / "controls" / "inputs"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    fixture = fixture_dir / f"{case_id}.json"
    with fixture.open("xb") as stream:
        stream.write(raw)
    run_id = "control-" + case_id
    result = run(["--run-id", run_id, "--pointer-fixture", str(fixture)])
    destination = ROOT / OWNED / "runs" / run_id
    ok = result.returncode == 2 and expected_fragment in result.stderr and not os.path.lexists(destination)
    return record(case_id, ok, result.stderr.strip(), raw)


def main():
    source = json.loads((ROOT / LEDGER).read_text())
    rows = source["objects"]
    cases = []
    for position in (0, len(rows) // 2, len(rows) - 1):
        duplicate = json.loads(json.dumps(source))
        duplicate["objects"].insert(position, json.loads(json.dumps(rows[-1])))
        cases.append(check_reject(f"duplicate-position-{position}", duplicate, "exactly 6 records"))
    missing = json.loads(json.dumps(source)); missing["objects"].pop()
    cases.append(check_reject("missing-record", missing, "exactly 6 records"))
    foreign = json.loads(json.dumps(source)); foreign["objects"][0]["id"] = "foreign-pointer"
    cases.append(check_reject("foreign-record", foreign, "missing or foreign"))
    wrong_path = json.loads(json.dumps(source)); wrong_path["objects"][0]["upstream_path"] += ".renamed"
    cases.append(check_reject("wrong-path", wrong_path, "path or vintage mismatch"))
    wrong_vintage = json.loads(json.dumps(source)); wrong_vintage["objects"][0]["upstream_commit"] = "0" * 40
    cases.append(check_reject("wrong-vintage", wrong_vintage, "path or vintage mismatch"))
    wrong_hash = json.loads(json.dumps(source)); wrong_hash["objects"][0]["lfs_object_sha256"] = "0" * 64
    cases.append(check_reject("wrong-lfs-hash", wrong_hash, "hash or size mismatch"))
    wrong_size = json.loads(json.dumps(source)); wrong_size["objects"][0]["lfs_object_bytes"] += 1
    cases.append(check_reject("wrong-lfs-size", wrong_size, "hash or size mismatch"))

    runs = ROOT / OWNED / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    for name, kind in (("existing-file", "file"), ("existing-directory", "directory"), ("broken-symlink", "broken")):
        target = runs / ("control-" + name)
        if kind == "file":
            target.write_text("sentinel")
        elif kind == "directory":
            target.mkdir()
            (target / "sentinel").write_text("preserve")
        else:
            target.symlink_to(ROOT / OWNED / "absent-target")
        before = hashlib.sha256((target / "sentinel").read_bytes()).hexdigest() if kind == "directory" else None
        result = run(["--run-id", "control-" + name])
        after = hashlib.sha256((target / "sentinel").read_bytes()).hexdigest() if kind == "directory" else None
        ok = result.returncode == 2 and before == after
        cases.append(record(name, ok, result.stderr.strip()))
    escape = run(["--run-id", "../escape"])
    cases.append(record("path-escape", escape.returncode == 2 and "safe lowercase slug" in escape.stderr, escape.stderr.strip()))

    report = {"version": 1, "method_id": "batch3-provenance-crossfield-validator",
              "kind": "negative-control", "outcome": "passed" if all(case["passed"] for case in cases) else "failed",
              "actual_entry_point": "reproduce.py", "cases": cases,
              "all_passed": all(case["passed"] for case in cases),
              "note": "Each rejection used the actual CLI. Malformed ledgers were rejected before any run directory was created; conflicting destination sentinels remained unchanged."}
    output = ROOT / OWNED / "pointer-destination-controls.json"
    with output.open("xb") as stream:
        stream.write(canonical(report))
    print(json.dumps(report, sort_keys=True))
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
