#!/usr/bin/env python3
"""Run materialized-input and destination controls in an isolated base worktree."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PACKET = "data/regional-review/texas-erratum-integrity-1144-followup"
BASELINE = json.loads((HERE / "input-pins.json").read_text())
BASE = BASELINE["baseline_commit"]
BASE_DATA = "data/regional-review/regional-review-508c7e9f3a462f8f"
ROWS = BASE_DATA + "/runs/twelve/county-assessments.jsonl"
RETRIEVAL = BASE_DATA + "/source/census-api-retrieval-manifest.json"
SCRIPT = "data/regional-review/texas-erratum-integrity-1144-followup/reproduce_immutable.py"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def run_case(repo: Path, label: str, restore: dict[str, bytes], mutate, vintage: str) -> dict:
    for path, raw in restore.items():
        (repo / path).write_bytes(raw)
    before = {path: sha((repo / path).read_bytes()) for path in restore}
    mutate(repo)
    changed = {path: sha((repo / path).read_bytes()) for path in restore}
    proc = subprocess.run([sys.executable, SCRIPT, "--repo", str(repo), "--vintage", vintage], cwd=repo, text=True, capture_output=True)
    output = repo / PACKET / "vintages" / vintage
    after = {path: sha((repo / path).read_bytes()) for path in restore}
    if proc.returncode == 0 or output.exists() or changed == before:
        raise AssertionError(f"{label}: runner accepted drift, wrote output, or fixture did not change")
    for path, raw in restore.items():
        (repo / path).write_bytes(raw)
    restored = {path: sha((repo / path).read_bytes()) for path in restore}
    if restored != before:
        raise AssertionError(f"{label}: control fixture restoration failed")
    return {"case": label, "outcome": "rejected_before_output", "changed_inputs": {path: changed[path] for path in restore if changed[path] != before[path]}, "fixture_restored_sha256": restored, "error": proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "runner exited nonzero"}


def main() -> None:
    original_script = (HERE / "reproduce_immutable.py").read_bytes()
    original_ledger = (HERE / "input-pins.json").read_bytes()
    original_snapshot = (HERE / "issue-1365-snapshot.json").read_bytes()
    results = []
    with tempfile.TemporaryDirectory(prefix="worldatlas-texas-1365-") as temp:
        repo = Path(temp) / "checkout"
        subprocess.run(["git", "-C", str(ROOT), "worktree", "add", "--detach", str(repo), BASE], check=True, stdout=subprocess.DEVNULL)
        try:
            target = repo / PACKET
            target.mkdir(parents=True)
            shutil.copy2(HERE / "reproduce_immutable.py", target / "reproduce_immutable.py")
            shutil.copy2(HERE / "input-pins.json", target / "input-pins.json")
            shutil.copy2(HERE / "issue-1365-snapshot.json", target / "issue-1365-snapshot.json")
            row_raw = (repo / ROWS).read_bytes()
            retrieval_raw = (repo / RETRIEVAL).read_bytes()
            helper_raw = (repo / "scripts/evidence/immutable.py").read_bytes()
            rows = [json.loads(line) for line in row_raw.splitlines() if line]

            def swap_geoids(tree):
                changed_rows = [dict(row) for row in rows]
                for field in ("census_geoid_2018", "census_geoid_2025"):
                    changed_rows[0][field], changed_rows[1][field] = changed_rows[1][field], changed_rows[0][field]
                (tree / ROWS).write_bytes(b"".join(json.dumps(row, ensure_ascii=False, sort_keys=True).encode() + b"\n" for row in changed_rows))

            def change_crs(tree):
                raw = retrieval_raw.replace(b"outSR=4326", b"outSR=3857", 1)
                if raw == retrieval_raw:
                    raise AssertionError("No literal outSR=4326 request available for control")
                (tree / RETRIEVAL).write_bytes(raw)

            def remove_final_geoid(tree):
                changed_rows = [dict(row) for row in rows]
                last = max(changed_rows, key=lambda row: row["subject_id"])
                last["census_geoid_2018"] = "00000"
                (tree / ROWS).write_bytes(b"".join(json.dumps(row, ensure_ascii=False, sort_keys=True).encode() + b"\n" for row in changed_rows))

            def duplicate_subject(tree):
                changed_rows = [dict(row) for row in rows]
                changed_rows[0]["subject_id"] = changed_rows[1]["subject_id"]
                (tree / ROWS).write_bytes(b"".join(json.dumps(row, ensure_ascii=False, sort_keys=True).encode() + b"\n" for row in changed_rows))

            def drift_helper(tree):
                (tree / "scripts/evidence/immutable.py").write_bytes(helper_raw + b"\n# fixture drift\n")

            for i, (name, mutate, restore) in enumerate([
                ("swapped_census_geoids", swap_geoids, {ROWS: row_raw}),
                ("changed_2018_outSR", change_crs, {RETRIEVAL: retrieval_raw}),
                ("missing_lexicographically_last_geoid", remove_final_geoid, {ROWS: row_raw}),
                ("duplicate_subject", duplicate_subject, {ROWS: row_raw}),
                ("shared_helper_code_drift", drift_helper, {"scripts/evidence/immutable.py": helper_raw}),
            ], 1):
                results.append(run_case(repo, name, restore, mutate, f"control-drift-{i}"))

            # The output writer itself must preserve both existing sentinels and
            # dangling symlinks; use the exact real entry point and fresh paths.
            for name in ("control-existing", "control-partial"):
                dest = target / "vintages" / name
                dest.mkdir(parents=True)
                sentinel = dest / "sentinel.txt"
                sentinel.write_bytes(b"preserve previous evidence\n")
                sentinel_sha = sha(sentinel.read_bytes())
                proc = subprocess.run([sys.executable, SCRIPT, "--repo", str(repo), "--vintage", name], cwd=repo, text=True, capture_output=True)
                if proc.returncode == 0 or sha(sentinel.read_bytes()) != sentinel_sha or len(list(dest.iterdir())) != 1:
                    raise AssertionError(name + ": pre-existing destination was changed")
                results.append({"case": name, "outcome": "rejected_preserving_sentinel", "sentinel_sha256": sentinel_sha, "error": proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "runner exited nonzero"})
                shutil.rmtree(dest)
            link = target / "vintages" / "control-dangling-link"
            link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(target / "does-not-exist")
            proc = subprocess.run([sys.executable, SCRIPT, "--repo", str(repo), "--vintage", "control-dangling-link"], cwd=repo, text=True, capture_output=True)
            if proc.returncode == 0 or not link.is_symlink():
                raise AssertionError("dangling destination symlink was accepted or removed")
            results.append({"case": "control-dangling-link", "outcome": "rejected_preserving_symlink", "is_symlink": True, "target_exists": link.exists()})
        finally:
            subprocess.run(["git", "-C", str(ROOT), "worktree", "remove", "--force", str(repo)], check=True)
    result = {"version": 1, "issue": 1365, "method_id": "immutable-texas-erratum-join", "kind": "negative-control", "outcome": "passed", "baseline_commit": BASE, "python": sys.version.split()[0], "control_harness_sha256": sha(Path(__file__).read_bytes()), "cases": results, "runner_sha256": sha(original_script), "pin_ledger_sha256": sha(original_ledger), "issue_snapshot_sha256": sha(original_snapshot)}
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
