#!/usr/bin/env python3
"""Exercise both real output entry points and adverse paths under the owned scope."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import re
from datetime import datetime, timezone

from control_writer import PRODUCTS as CONTROL_PRODUCTS, compare_retained_reports
from producer_republish import PRODUCTS as PRODUCER_PRODUCTS, produce_vintage
from safe_outputs import (
    EVIDENCE_PATH, OWNED_PATH, WORKER_ID, admitted_baseline, current_commit,
    exercise_preflight_controls, safe_output_root,
)

REPO = Path(__file__).resolve().parents[3]
OWNED = REPO / OWNED_PATH
VINTAGES = OWNED / "vintages"
PYTHON = sys.executable


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def call(script: str, run_id: str):
    return subprocess.run([PYTHON, "-B", str(OWNED / script), "--run-id", run_id],
                          cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def expect_rejection(result, label: str):
    if result.returncode == 0:
        raise AssertionError(f"Actual entry point accepted adverse case: {label}")
    return {"outcome": "passed", "exit_code": result.returncode,
            "diagnostic": (result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "")[:300]}


def verify_receipt(run_id: str, products: list[str]):
    root = VINTAGES / run_id
    receipt = json.loads((root / "publication.json").read_bytes())
    if receipt.get("status") != "complete" or receipt.get("version") != 1:
        raise AssertionError(f"Missing final completion receipt for {run_id}")
    expected = set(products)
    actual = {Path(row["path"]).name for row in receipt.get("outputs", [])}
    if expected != actual or len(actual) != len(products):
        raise AssertionError(f"Receipt inventory is incomplete for {run_id}")
    for row in receipt["outputs"]:
        raw = (REPO / row["path"]).read_bytes()
        if len(raw) != row["bytes"] or sha(raw) != row["sha256"]:
            raise AssertionError(f"Receipt product mismatch: {row['path']}")
    files = {path.name for path in root.iterdir()}
    if files != expected | {"publication.json"}:
        raise AssertionError(f"Unexpected products or incomplete receipt in {run_id}: {files}")
    return receipt


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default="head088ab2",
                        help="unique short tag for fresh run IDs and the immutable result path")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,19}", args.tag):
        parser.error("tag must be 1-20 lowercase letters, digits or interior hyphens")
    prefix = "check-" + args.tag
    result_path = OWNED / "validation" / f"adversarial-controls-{args.tag}.json"
    if os.path.lexists(result_path):
        raise FileExistsError(f"Refusing to replace existing validation evidence: {result_path.relative_to(REPO)}")

    cases = {}
    producer_ids = (f"producer-{args.tag}-one", f"producer-{args.tag}-two")
    control_ids = (f"controls-{args.tag}-one", f"controls-{args.tag}-two")
    for run_id, product in ((producer_ids[0], "assessments.json.gz"), (producer_ids[1], "assessments.json.gz")):
        result = call("producer_republish.py", run_id) if not (VINTAGES / run_id).exists() else None
        if result is not None:
            if result.returncode != 0:
                raise AssertionError(f"Producer entry point failed for {run_id}: {result.stderr}")
        verify_receipt(run_id, [product])
    producer_one = (VINTAGES / producer_ids[0] / "assessments.json.gz").read_bytes()
    producer_two = (VINTAGES / producer_ids[1] / "assessments.json.gz").read_bytes()
    if producer_one != producer_two:
        raise AssertionError("Two fresh actual producer-entrypoint outputs differ")
    cases["producer_two_fresh_runs"] = {"outcome": "passed", "product": "assessments.json.gz",
                                         "run_one_sha256": sha(producer_one), "run_two_sha256": sha(producer_two)}

    for run_id in control_ids:
        result = call("control_writer.py", run_id) if not (VINTAGES / run_id).exists() else None
        if result is not None:
            if result.returncode != 0:
                raise AssertionError(f"Control writer failed for {run_id}: {result.stderr}")
        verify_receipt(run_id, CONTROL_PRODUCTS)
    for name in CONTROL_PRODUCTS:
        one = (VINTAGES / control_ids[0] / name).read_bytes()
        two = (VINTAGES / control_ids[1] / name).read_bytes()
        if one != two:
            raise AssertionError(f"Two fresh control-writer products differ: {name}")
    cases["control_writer_two_fresh_runs"] = {
        "outcome": "passed", "products": {name: sha((VINTAGES / control_ids[0] / name).read_bytes())
                                               for name in CONTROL_PRODUCTS}}

    state = admitted_baseline(REPO)
    issue, contract, baseline, module, commit, files, pins = state
    original, run_one, run_two = __import__("safe_outputs").exact_report_inputs(baseline)
    old_rows, new_rows, changes, counts, corrected = compare_retained_reports(original, run_one)
    if run_one != run_two or len(old_rows) != 224 or len(new_rows) != 224 or len(changes) != 16:
        raise AssertionError("Full retained-row comparison differs from original acceptance")
    cases["full_retained_row_join"] = {
        "outcome": "passed", "subjects": len(new_rows), "province_groups": len(corrected["province_assessments"]),
        "changed_fields": len(changes), "classification_counts": counts,
        "original_sha256": sha(original), "corrected_sha256": sha(run_one),
        "no_geometry_replay": True}

    tag = "entrypoint-" + args.tag
    scratch = OWNED / "negative-fixtures" / tag
    scratch.mkdir(parents=True, exist_ok=False)
    VINTAGES.mkdir(parents=True, exist_ok=True)
    try:
        file_id = prefix + "-blocked-file"
        file_path = VINTAGES / file_id
        file_path.write_bytes(b"ordinary-file-sentinel\n")
        before = sha(file_path.read_bytes())
        cases["actual_producer_ordinary_file"] = expect_rejection(call("producer_republish.py", file_id), "ordinary file")
        if sha(file_path.read_bytes()) != before:
            raise AssertionError("Existing ordinary file was modified")
        file_path.unlink()

        directory_id = prefix + "-blocked-directory"
        directory = VINTAGES / directory_id
        directory.mkdir()
        dir_sentinel = directory / "sentinel.bin"
        dir_sentinel.write_bytes(b"ordinary-directory-sentinel\n")
        before = sha(dir_sentinel.read_bytes())
        cases["actual_control_writer_ordinary_directory"] = expect_rejection(call("control_writer.py", directory_id), "ordinary directory")
        if sha(dir_sentinel.read_bytes()) != before:
            raise AssertionError("Existing directory sentinel was modified")
        shutil.rmtree(directory)

        live_target = scratch / "live-target"
        live_target.mkdir()
        live_sentinel = live_target / "sentinel.bin"
        live_sentinel.write_bytes(b"live-link-target-sentinel\n")
        before = sha(live_sentinel.read_bytes())
        live_id = prefix + "-blocked-live-symlink"
        live_link = VINTAGES / live_id
        live_link.symlink_to(live_target, target_is_directory=True)
        cases["actual_producer_live_symlink"] = expect_rejection(call("producer_republish.py", live_id), "live symlink")
        if sha(live_sentinel.read_bytes()) != before:
            raise AssertionError("Live symlink target sentinel was modified")
        live_link.unlink()

        dangling_target = scratch / "not-created"
        dangling_id = prefix + "-blocked-dangling-symlink"
        dangling_link = VINTAGES / dangling_id
        dangling_link.symlink_to(dangling_target)
        cases["actual_control_writer_dangling_symlink"] = expect_rejection(call("control_writer.py", dangling_id), "dangling symlink")
        if os.path.lexists(dangling_target):
            raise AssertionError("Dangling symlink target was created")
        dangling_link.unlink()

        traversal = subprocess.run([PYTHON, "-B", str(OWNED / "producer_republish.py"), "--run-id", "../escape"],
                                   cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        cases["actual_producer_traversal"] = expect_rejection(traversal, "traversal run-id")

        preflight = exercise_preflight_controls(REPO, "unit-" + args.tag)
        if preflight.get("cases_passed") != 6 or any(value != "passed" for value in preflight["cases"].values()):
            raise AssertionError("Preflight ordinary/live/dangling/traversal/ancestor controls incomplete")
        cases["complete_preflight_cases"] = preflight

        # Simulate a symlink appearing after report comparison but before the
        # helper's second pre-write admission. Only our private sentinel exists.
        post_target = scratch / "post-compute-target"
        post_target.mkdir()
        post_sentinel = post_target / "sentinel.bin"
        post_sentinel.write_bytes(b"post-computation-sentinel\n")
        before = sha(post_sentinel.read_bytes())
        def inject_symlink(root):
            root.symlink_to(post_target, target_is_directory=True)
        try:
            post_id = prefix + "-post-compute-symlink"
            produce_vintage(post_id, repo=REPO, state=state, before_publish=inject_symlink)
        except (ValueError, FileExistsError):
            pass
        else:
            raise AssertionError("Post-computation symlink race was accepted")
        race_root = VINTAGES / (prefix + "-post-compute-symlink")
        if not race_root.is_symlink() or sha(post_sentinel.read_bytes()) != before or (post_target / "publication.json").exists():
            raise AssertionError("Post-computation failure altered target or published receipt")
        race_root.unlink()
        cases["post_computation_symlink"] = {"outcome": "passed", "sentinel_sha256": before,
                                               "target_unchanged": True, "publication_receipt": False}

        run_two_path = EVIDENCE_PATH + "vintages/generator-integrity-erratum/runs/2026-10-07/run-2/assessments.json.gz"
        incomplete_files = [row for row in files if row["path"] != run_two_path]
        incomplete_baseline = module.Baseline(REPO, commit, incomplete_files)
        incomplete_state = (issue, contract, incomplete_baseline, module, commit, incomplete_files,
                            {key: value for key, value in pins.items() if key != run_two_path})
        try:
            missing_id = prefix + "-missing-retained-input"
            produce_vintage(missing_id, repo=REPO, state=incomplete_state)
        except ValueError as error:
            if "unpinned" not in str(error).lower() and "pin" not in str(error).lower():
                raise
        else:
            raise AssertionError("Producer accepted a missing required retained run")
        if (VINTAGES / (prefix + "-missing-retained-input")).exists():
            raise AssertionError("Missing-input failure left an output vintage")
        cases["missing_retained_input"] = {"outcome": "passed", "expected_output_vintage": False}

        guard_path = EVIDENCE_PATH + "vintages/generator-integrity-erratum/integrity_guards.py"
        guard_bytes = baseline.pinned_bytes(guard_path)
        guard_module = __import__("types").ModuleType("pinned_original_integrity_guard")
        exec(compile(guard_bytes, f"{commit}:{guard_path}", "exec"), guard_module.__dict__)
        run_one_path = EVIDENCE_PATH + "vintages/generator-integrity-erratum/runs/2026-10-07/run-1/assessments.json.gz"
        source_bytes = baseline.pinned_bytes(run_one_path)
        descriptor = {"path": run_one_path, "bytes": len(source_bytes), "sha256": sha(source_bytes)}
        guard_module.verify_bound_input(descriptor, source_bytes, source_bytes)
        try:
            guard_module.verify_bound_input(descriptor, source_bytes, source_bytes + b"changed")
        except ValueError:
            cases["changed_input"] = {"outcome": "passed", "original_sha256": sha(source_bytes),
                                       "changed_input_rejected": True}
        else:
            raise AssertionError("Original input guard accepted changed whole-file bytes")
    finally:
        # All fixture data is created by this invocation; preserve only its
        # hashes and outcomes in the immutable result written below.
        shutil.rmtree(scratch)

    result = {
        "version": 1, "issue": 1485, "status": "passed",
        "worker_id": WORKER_ID,
        "tested_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository_head": current_commit(REPO), "output_safety_baseline": commit,
        "actual_entry_points": ["producer_republish.py", "control_writer.py"],
        "cases": cases,
        "limits": ["Both successful producer outputs republish retained compressed results; the 40,040,002-byte decoded native source exceeds the 32 MiB file limit, so no fresh geometry science was run.",
                   "Tests establish output-path behavior and report reproduction, not current territorial meaning, complete boundaries, source rights, or geographic approval."],
    }
    validation = OWNED / "validation"
    validation.mkdir(exist_ok=True)
    target = result_path
    with target.open("xb") as stream:
        stream.write((json.dumps(result, sort_keys=True, indent=2) + "\n").encode())
    print(json.dumps({"status": result["status"], "cases": len(cases), "evidence": str(target.relative_to(REPO))}, sort_keys=True))


if __name__ == "__main__":
    main()
