#!/usr/bin/env python3
"""Run the bounded controls and publish concise positive/negative receipts."""
from __future__ import annotations

import json
import argparse
import hashlib
import platform
import re
from pathlib import Path
import subprocess
import sys

import admission
import run_safe

METHOD_ID = "saudi-complete-admission-and-writer-custody"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suffix", default="current")
    args = parser.parse_args()
    if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.suffix) is None:
        raise SystemExit("suffix must contain only letters, numbers, and hyphens")
    root = run_safe.REPO_ROOT
    owned = run_safe.HERE
    _lock, actual, expected_outputs, receipts = run_safe.load_plan(root)
    lock_path = root / run_safe.PREDECESSOR / "frozen-execution.json"
    lock_raw = admission.read_regular(lock_path)
    lock = json.loads(lock_raw)
    output_reserve = sum(row["bytes"] for row in expected_outputs.values())
    parameters = {"lock_sha256": admission.sha256(lock_raw), "lock_bytes": len(lock_raw),
                  "output_reserve_bytes": output_reserve,
                  "runtime_reserve_bytes": run_safe.RUNTIME_RESERVE_BYTES,
                  "supplemental_files": actual["supplemental_inputs"]}
    boundary = []
    for label, limit in (("one-byte-below", actual["complete_phase_bytes"] - 1),
                         ("exact-boundary", actual["complete_phase_bytes"]),
                         ("one-byte-above", actual["complete_phase_bytes"] + 1)):
        trial = json.loads(json.dumps(lock))
        trial["limits"]["maximum_total_declared_bytes"] = limit
        result = admission.plan_from_lock(trial, **parameters, phase_bytes=limit)
        boundary.append({"case": label, "phase_limit_bytes": limit,
                         "complete_phase_bytes": result["complete_phase_bytes"],
                         "admitted": result["admitted"]})
    if [row["admitted"] for row in boundary] != [False, True, True]:
        raise admission.AdmissionError("Plan boundary controls did not enforce the inclusive cap")

    tests = subprocess.run([sys.executable, "-B", str(owned / "test_safety.py")],
                           cwd=root, text=True, capture_output=True, check=False)
    summary_line = next((line for line in tests.stderr.splitlines() if line.startswith("Ran ")), "")
    if tests.returncode != 0 or not summary_line:
        raise admission.AdmissionError("Bounded safety test suite did not complete successfully")
    try:
        count = int(summary_line.split()[1])
    except (IndexError, ValueError):
        raise admission.AdmissionError("Safety test count was not captured") from None
    runtime_path = Path(sys.executable).resolve(strict=True)
    runtime_raw = admission.read_regular(runtime_path)
    test_report = {"version": 1, "status": "passed", "exit_code": tests.returncode,
                   "tests_run": count, "stdout": tests.stdout,
                   "stderr": tests.stderr, "entrypoint": "test_safety.py",
                   "runtime": {"implementation": platform.python_implementation(),
                               "version": platform.python_version(),
                               "executable": str(runtime_path),
                               "executable_bytes": len(runtime_raw),
                               "executable_sha256": admission.sha256(runtime_raw)}}

    refusal_path = owned / "execution/refusals/run-4-admission.json"
    refusal = json.loads(admission.read_regular(refusal_path))
    reproduction = json.loads(admission.read_regular(owned / "execution/legacy-writer-reproduction.json"))
    preservation = json.loads(admission.read_regular(owned / "execution/predecessor-preservation.json"))
    historical = json.loads(admission.read_regular(owned / "execution/verified-historical-products.json"))
    if actual["admitted"] or refusal.get("status") != "refused-before-source-read":
        raise admission.AdmissionError("Actual full-source phase was not refused before source reads")
    if not reproduction.get("predecessor_originals_preserved") or not preservation.get("status", "").startswith("all-predecessor"):
        raise admission.AdmissionError("Predecessor preservation controls failed")
    if historical["product_count_per_run"] != 14 or historical["runs"][0]["products_sha256"] != historical["runs"][1]["products_sha256"]:
        raise admission.AdmissionError("Historical complete product controls failed")

    stem = f"{owned.relative_to(root).as_posix()}/execution/"
    test_path = stem + f"test-run-{args.suffix}.json"
    positive_path = stem + f"positive-control-{args.suffix}.json"
    negative_path = stem + f"negative-control-{args.suffix}.json"
    positive = {"method_id": METHOD_ID, "kind": "positive-control", "outcome": "passed",
                "phase_limit_boundary_cases": boundary,
                "predecessor_file_count": preservation["file_count"],
                "predecessor_total_bytes": preservation["total_bytes"],
                "historical_product_count_per_run": historical["product_count_per_run"],
                "historical_product_bytes_per_run": historical["bytes_per_run"],
                "historical_inventory_hashes_equal": historical["runs"][0]["products_sha256"] == historical["runs"][1]["products_sha256"],
                "ordinary_occupied_and_partial_controls_preserved": all(row.get("sentinel_preserved", True) for row in reproduction["observations"]),
                "test_run": test_report}
    negative = {"method_id": METHOD_ID, "kind": "negative-control", "outcome": "passed",
                "actual_plan_admitted": actual["admitted"],
                "actual_complete_phase_bytes": actual["complete_phase_bytes"],
                "actual_phase_limit_bytes": actual["phase_limit_bytes"],
                "refusal_before_source_read": refusal["source_bodies_read"] is False and refusal["decompression_started"] is False and refusal["producer_started"] is False,
                "legacy_link_probe_cases": [row for row in reproduction["observations"] if row["case"] in ("dangling-receipt-leaf", "live-runs-parent-link")],
                "new_wrapper_linked_destination_rejections": ["test_new_wrapper_rejects_linked_receipt_and_parent_before_child"],
                "new_freeze_writer_exclusive": ["test_freeze_writer_preadmits_before_derivation_and_never_overwrites",
                                                "test_freeze_refusal_does_not_derive_or_admit_writer"],
                "late_output_verification": ["test_new_wrapper_rejects_late_success_with_wrong_product_bytes"],
                "independent_reader_aggregate": ["test_independent_reader_inputs_aggregate_into_complete_phase"],
                "test_run": test_report}
    admission.write_exclusive_json(root, test_path, test_report)
    admission.write_exclusive_json(root, positive_path, positive)
    admission.write_exclusive_json(root, negative_path, negative)
    print(json.dumps({"test_count": count, "controls": [positive_path, negative_path],
                      "actual_plan": actual["complete_phase_bytes"],
                      "admitted": actual["admitted"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
