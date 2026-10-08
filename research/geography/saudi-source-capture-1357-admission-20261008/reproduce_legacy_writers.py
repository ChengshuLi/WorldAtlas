#!/usr/bin/env python3
"""Boundedly reproduce legacy receipt-link writes in complete private copies."""
from __future__ import annotations

import json
import os
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

import admission
import run_safe

REPO = run_safe.REPO_ROOT
OWNED = run_safe.HERE
OLD = REPO / run_safe.PREDECESSOR
COPIED_FILES = [
    "source_extract.py", "run_final.py", "frozen-execution.json", "issue-1336-api.json",
    "compat/inputs.py", "compat/immutable.py", "inputs/legacy-input-config.json",
]


def originals() -> dict[str, dict]:
    result = {}
    for name in COPIED_FILES:
        raw = admission.read_regular(OLD / name)
        result[name] = {"bytes": len(raw), "sha256": admission.sha256(raw)}
    return result


def fixture(root: Path) -> Path:
    packet = root / "research/geography/saudi-fortynine-numeric-gap-family-source-fitness-20261007"
    (packet / "compat").mkdir(parents=True)
    (packet / "inputs").mkdir()
    for name in COPIED_FILES:
        shutil.copyfile(OLD / name, packet / name)
    (packet / "issue-1336-api.json").write_text('{"auditor_deliberate_drift":true}\n')
    return packet


def run_wrapper(root: Path) -> subprocess.CompletedProcess:
    script = root / "research/geography/saudi-fortynine-numeric-gap-family-source-fitness-20261007/run_final.py"
    return subprocess.run([sys.executable, str(script), "--run-id", "run-1", "--repo", str(root)],
                          cwd=root, text=True, capture_output=True, check=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="execution/legacy-writer-reproduction.json")
    args = parser.parse_args()
    before = originals()
    cases = []
    with tempfile.TemporaryDirectory(prefix="legacy-writer-probes-", dir=OWNED / "execution") as temp:
        base = Path(temp)

        root = base / "dangling/repo"
        packet = fixture(root)
        runs = packet / "runs"
        runs.mkdir()
        link = runs / "run-1-execution.json"
        target = root / "outside-dangling-receipt.json"
        link_text = "../../../../outside-dangling-receipt.json"
        link.symlink_to(link_text)
        proc = run_wrapper(root)
        escaped_raw = admission.read_regular(target)
        escaped = json.loads(escaped_raw)
        cases.append({
            "case": "dangling-receipt-leaf",
            "entrypoint": "predecessor run_final.py --run-id run-1",
            "child_exit_code": escaped["exit_code"],
            "child_rejection": "Frozen local input changed" in escaped.get("stderr", ""),
            "wrapper_exit_code": proc.returncode,
            "escaped_target": "outside-dangling-receipt.json",
            "escaped_bytes": len(escaped_raw),
            "escaped_sha256": admission.sha256(escaped_raw),
            "complete_source_pass": escaped["complete_source_pass"],
            "literal_link_preserved": link.is_symlink() and os.readlink(link) == link_text,
            "only_issue_api_fixture_changed": True,
        })

        root = base / "parent-link/repo"
        packet = fixture(root)
        outside = root / "outside-runs"
        outside.mkdir()
        runs_link = packet / "runs"
        runs_link.symlink_to(outside, target_is_directory=True)
        proc = run_wrapper(root)
        escaped_path = outside / "run-1-execution.json"
        escaped_raw = admission.read_regular(escaped_path)
        escaped = json.loads(escaped_raw)
        cases.append({
            "case": "live-runs-parent-link",
            "entrypoint": "predecessor run_final.py --run-id run-1",
            "child_exit_code": escaped["exit_code"],
            "child_rejection": "Frozen local input changed" in escaped.get("stderr", ""),
            "wrapper_exit_code": proc.returncode,
            "escaped_target": "outside-runs/run-1-execution.json",
            "escaped_bytes": len(escaped_raw),
            "escaped_sha256": admission.sha256(escaped_raw),
            "complete_source_pass": escaped["complete_source_pass"],
            "literal_link_preserved": runs_link.is_symlink() and runs_link.resolve() == outside,
            "only_issue_api_fixture_changed": True,
        })

        for case_name in ("existing-receipt", "partial-output"):
            root = base / case_name / "repo"
            packet = fixture(root)
            runs = packet / "runs"
            runs.mkdir()
            if case_name == "existing-receipt":
                sentinel = runs / "run-1-execution.json"
            else:
                sentinel = runs / "run-1/output/partial.json"
                sentinel.parent.mkdir(parents=True)
            sentinel.write_bytes(b"preserve-me")
            before_sentinel = admission.sha256(sentinel.read_bytes())
            proc = run_wrapper(root)
            after_sentinel = admission.sha256(sentinel.read_bytes())
            cases.append({"case": case_name, "wrapper_exit_code": proc.returncode,
                          "sentinel_before_sha256": before_sentinel,
                          "sentinel_after_sha256": after_sentinel,
                          "sentinel_preserved": before_sentinel == after_sentinel,
                          "child_started": False})

    after = originals()
    if before != after:
        raise admission.AdmissionError("Legacy originals changed during private-copy reproduction")
    if any(row.get("wrapper_exit_code") == 0 for row in cases):
        raise admission.AdmissionError("A legacy destination control unexpectedly succeeded")
    if any(not row.get("sentinel_preserved", row.get("literal_link_preserved", False)) for row in cases):
        raise admission.AdmissionError("A preexisting sentinel or symlink changed")
    if any(not row.get("child_rejection", True) for row in cases):
        raise admission.AdmissionError("The controlled early child rejection was not observed")
    result = {
        "version": 1,
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "status": "legacy-writer-defect-reproduced-in-private-copies",
        "changed_fixture_input": "issue-1336-api.json only; deliberate valid JSON drift",
        "early_child_failure": "Frozen local input changed before Git source-body reads",
        "private_copy_files": COPIED_FILES,
        "predecessor_originals_before": before,
        "predecessor_originals_after": after,
        "predecessor_originals_preserved": before == after,
        "observations": cases,
        "interpretation": "Failure receipts truthfully report incomplete execution. Findings are escaped writes through dangling/live links, not false-success receipts.",
        "source_replay_performed": False,
        "geographic_or_source_approval": False,
    }
    output = admission.safe_relative(args.output)
    admission.write_exclusive_json(REPO, f"{OWNED.relative_to(REPO).as_posix()}/{output}", result)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
