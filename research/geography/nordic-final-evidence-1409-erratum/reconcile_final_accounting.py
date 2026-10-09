#!/usr/bin/env python3
"""Correct the final Nordic v14 report's recorded phase-byte maximum.

This is a bounded report-only correction. It reads authenticated Git blobs from
the accepted #1389 packet and publishes only fresh vintages inside this issue's
owned directory. It performs no GIS, source, provider, or production operation.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import types

ROOT = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
HERE = Path(__file__).resolve().parent
OWNED = "research/geography/nordic-final-evidence-1409-erratum/"
BASELINE_COMMIT = "643e4123ce9881a9d07f564166edae34aec7aa08"
SOURCE_LOCK_PATH = "research/geography/nordic-reproduction-integrity-1233-erratum/source-lock.json"
SOURCE_LOCK_SHA = "b59c618cc31cdd02a4d7f6b8b204a0466349de775981feb816e514fb99cbdf8f"

INPUTS = [
    {"id": "input_00", "path": "research/geography/nordic-reproduction-integrity-1233-erratum/README.md", "bytes": 8137, "sha256": "ce27fbe3fa4661b516ab42c57168d4085e3bfe78fde0562bdfb3c0b1d104d78f"},
    {"id": "input_01", "path": "research/geography/nordic-reproduction-integrity-1233-erratum/evidence-quality.json", "bytes": 78433, "sha256": "d7ac3a7f080025208fd8cc9d7db3e781faddf0bba8a5ee822b43f86b95070b8a"},
    {"id": "input_02", "path": "research/geography/nordic-reproduction-integrity-1233-erratum/pairwise-reproducibility.json", "bytes": 1827, "sha256": "e702d76524e67a24bf5748a66bfae525d4c8baa84c8acc821a139f8494284be8"},
    {"id": "input_03", "path": "research/geography/nordic-reproduction-integrity-1233-erratum/reproduce.py", "bytes": 44535, "sha256": "2c9e90bc16a3d54fe2729ea629283e3d0703a98bf25345ec38128610b60e3890"},
    {"id": "input_04", "path": "research/geography/nordic-reproduction-integrity-1233-erratum/reproduction-metrics.json", "bytes": 907, "sha256": "76c4bff7b025105a7af83a4399ff3884dacfde2f8917f90ec721136e7dc11ac4"},
    {"id": "input_05", "path": SOURCE_LOCK_PATH, "bytes": 44637, "sha256": SOURCE_LOCK_SHA},
    {"id": "input_06", "path": "research/geography/nordic-reproduction-integrity-1233-erratum/validation-controls.json", "bytes": 1903, "sha256": "f3add13fdb08a2a57b5d0cc1cfbf4156116edcf5193766db5d7a0f2711bd2d85"},
    {"id": "input_07", "path": "research/geography/nordic-reproduction-integrity-1233-erratum/vintages/repro-v14-one-20261007/authentication-and-phase-accounting.json", "bytes": 3316661, "sha256": "39f9ee4661149ec85261038aa9812c04b2d3f1e0b1b42b2032a6e6df6eee4c6f"},
    {"id": "input_08", "path": "research/geography/nordic-reproduction-integrity-1233-erratum/vintages/repro-v14-two-20261007/authentication-and-phase-accounting.json", "bytes": 3316661, "sha256": "8913542cdb56c62af045a3e09c225bfa687b345360519759904f16795f1425e5"},
]
REPORT_IDS = ("input_07", "input_08")
REPORT_RUNS = {"input_07": "repro-v14-one-20261007", "input_08": "repro-v14-two-20261007"}
OLD_MAXIMUM = 157734275
PHASE_LIMIT = 268435456
MAX_FILE = 32 * 1024 * 1024
MAX_PHASE = 256 * 1024 * 1024


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git_blob(commit: str, path: str) -> bytes:
    if not re.fullmatch(r"[0-9a-f]{40}", commit) or path.startswith("/") or ".." in Path(path).parts:
        raise ValueError("unsafe immutable Git reference")
    return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{commit}:{path}"])


def bootstrap_helper():
    lock_raw = git_blob(BASELINE_COMMIT, SOURCE_LOCK_PATH)
    if len(lock_raw) != 44637 or sha(lock_raw) != SOURCE_LOCK_SHA:
        raise ValueError("source lock differs from issue-pinned whole-file bytes")
    lock = json.loads(lock_raw)
    pin = lock.get("authenticated_helper")
    if not isinstance(pin, dict):
        raise ValueError("source lock lacks its executed preparation-helper pin")
    helper_raw = git_blob(pin["commit"], pin["path"])
    if len(helper_raw) != pin["bytes"] or sha(helper_raw) != pin["sha256"]:
        raise ValueError("authenticated helper bytes differ from source lock")
    module = types.ModuleType("worldatlas_pinned_immutable")
    exec(compile(helper_raw, pin["path"], "exec"), module.__dict__)
    if module.VERSION != "worldatlas-evidence-preparation-v1":
        raise ValueError("unexpected immutable preparation helper version")
    return lock, pin, helper_raw, module


def baseline_for(module):
    rows = [{"path": row["path"], "bytes": row["bytes"], "sha256": row["sha256"], "hash_kind": "file-bytes"} for row in INPUTS]
    baseline = module.Baseline(str(ROOT), BASELINE_COMMIT, rows, max_phase_bytes=MAX_PHASE)
    helper_lock, helper_pin, helper_raw, _ = bootstrap_helper()
    baseline.admit(f"executed-helper:{helper_pin['commit']}:{helper_pin['path']}", len(helper_raw))
    if helper_pin != json.loads(baseline.pinned_bytes(SOURCE_LOCK_PATH))["authenticated_helper"]:
        raise ValueError("executed helper pin disagrees with authenticated baseline lock")
    return baseline, helper_lock, helper_pin, helper_raw


def expected_by_path():
    return {row["path"]: row for row in INPUTS}


def find_pin_for_path(path):
    pin = expected_by_path().get(path)
    if pin is None:
        raise ValueError("report target is not an issue-pinned accepted v14 path")
    return pin


def verify_pair_bindings(baseline, lock):
    evidence = json.loads(baseline.pinned_bytes(INPUTS[1]["path"]))
    metrics = json.loads(baseline.pinned_bytes(INPUTS[4]["path"]))
    pairwise = json.loads(baseline.pinned_bytes(INPUTS[2]["path"]))
    runner = baseline.pinned_bytes(INPUTS[3]["path"])
    if len(runner) != INPUTS[3]["bytes"] or sha(runner) != INPUTS[3]["sha256"]:
        raise ValueError("accepted runner code bytes differ from original issue pin")
    output_rows = {x.get("path"): x for x in evidence.get("outputs", [])}
    for row in INPUTS[7:9]:
        descriptor = output_rows.get(row["path"])
        if not descriptor or descriptor.get("bytes") != row["bytes"] or descriptor.get("sha256") != row["sha256"]:
            raise ValueError("accepted manifest does not bind an exact v14 report")
    if metrics.get("results", {}).get("maximum_complete_phase_bytes") != OLD_MAXIMUM:
        raise ValueError("prior published maximum differs from the captured defect")
    if metrics.get("input_report_path") != INPUTS[7]["path"] or metrics.get("input_report_sha256") != INPUTS[7]["sha256"]:
        raise ValueError("prior metrics are not bound to accepted v14-one report")
    expected_runs = [REPORT_RUNS[x] for x in REPORT_IDS]
    if [x.get("run_id") for x in pairwise.get("runs", [])] != expected_runs:
        raise ValueError("prior pairwise record does not target exactly the accepted v14 pair")
    if [x.get("report_sha256") for x in pairwise.get("runs", [])] != [INPUTS[7]["sha256"], INPUTS[8]["sha256"]]:
        raise ValueError("prior pairwise record does not bind exact v14 report hashes")
    if pairwise.get("run_one_sha256") != pairwise.get("run_two_sha256"):
        raise ValueError("prior accepted v14 pair is not reproducible")
    if lock.get("issue") != 1389 or lock.get("baseline_commit") != "79ffb2ed04702e16f009e4675a8d74ef9bd09d4f":
        raise ValueError("source lock issue or scientific baseline changed")
    return {"metrics": metrics, "pairwise": pairwise, "runner_sha256": sha(runner)}


def pointers_with_phase_bytes(value, path=""):
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            child_path = path + "/" + escaped
            if key == "phase_bytes":
                found.append((child_path, child))
            found.extend(pointers_with_phase_bytes(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(pointers_with_phase_bytes(child, path + "/" + str(index)))
    return found


EXPECTED_PHASES = {
    "/combined_complete_source_overlay/phase_bytes",
    "/complete_component_scan/phase_bytes",
    "/complete_contact_scan/phase_bytes",
    "/complete_fragment_scan/phase_bytes",
    "/families/components/phase_bytes",
    "/families/contacts/phase_bytes",
    "/families/fragments/phase_bytes",
    "/families/retained_evidence/phase_bytes",
    "/families/source_and_vintages/phase_bytes",
    "/physical_reproduction/phase_bytes",
    "/source_and_atlas_comparisons/phase_accounting/NOR/phase_bytes",
    "/source_and_atlas_comparisons/phase_accounting/SWE/phase_bytes",
}


def validate_report_object(report, expected_run):
    if report.get("issue") != 1389 or report.get("run_id") != expected_run:
        raise ValueError("report is not the expected accepted v14 execution vintage")
    if report.get("status") != "authenticated bounded evidence reproduction; geography adjudication not performed":
        raise ValueError("accepted v14 report status changed")
    code = report.get("execution_code", {})
    runner = next(row for row in INPUTS if row["id"] == "input_03")
    if code != {"bytes": runner["bytes"], "path": runner["path"], "sha256": runner["sha256"]}:
        raise ValueError("report does not bind the accepted v14 executed runner")
    phases = pointers_with_phase_bytes(report)
    paths = [path for path, _ in phases]
    if set(paths) != EXPECTED_PHASES or len(paths) != len(EXPECTED_PHASES):
        raise ValueError("complete accepted phase inventory is missing, duplicated or extended")
    if any(type(value) is not int or value <= 0 for _, value in phases):
        raise ValueError("phase-byte candidates must be positive exact integers")
    return sorted(({"json_pointer": path, "phase_bytes": value} for path, value in phases), key=lambda x: x["json_pointer"])


def authenticate_report(raw, pin, expected_run):
    if len(raw) != pin["bytes"] or sha(raw) != pin["sha256"]:
        raise ValueError("report bytes differ from the pinned accepted v14 report")
    report = json.loads(raw)
    phases = validate_report_object(report, expected_run)
    return report, phases


def analyze_reports(baseline, helper_pin, helper_raw, pair_info):
    source_pins = pair_info["lock"].get("pins", [])
    if len(source_pins) != 57 or len({row.get("id") for row in source_pins}) != 57:
        raise ValueError("original source lock no longer preserves the full 57-pin roster")
    inputs = []
    phase_sets = []
    for pin_id in REPORT_IDS:
        pin = next(row for row in INPUTS if row["id"] == pin_id)
        raw = baseline.pinned_bytes(pin["path"])
        report, phases = authenticate_report(raw, pin, REPORT_RUNS[pin_id])
        inputs.append({"id": pin_id, "path": pin["path"], "commit": BASELINE_COMMIT, "bytes": len(raw), "sha256": sha(raw), "run_id": report["run_id"], "execution_code": report["execution_code"]})
        phase_sets.append(phases)
    if phase_sets[0] != phase_sets[1]:
        raise ValueError("accepted v14 reports disagree on the actual phase inventory or byte values")
    phases = phase_sets[0]
    maximum = max(row["phase_bytes"] for row in phases)
    prior_fragment = next(row["phase_bytes"] for row in phases if row["json_pointer"] == "/families/fragments/phase_bytes")
    if prior_fragment != OLD_MAXIMUM or maximum <= OLD_MAXIMUM:
        raise ValueError("the captured old maximum or consequential mismatch no longer reproduces")
    return {
        "phases": phases,
        "phase_count": len(phases),
        "prior_published_maximum_bytes": OLD_MAXIMUM,
        "maximum_recorded_phase_bytes": maximum,
        "correction_delta_bytes": maximum - OLD_MAXIMUM,
        "phase_limit_bytes": PHASE_LIMIT,
        "remaining_below_limit_bytes": PHASE_LIMIT - maximum,
        "inputs": inputs,
        "executed_runner_sha256": pair_info["runner_sha256"],
        "reporting_helper": {"commit": helper_pin["commit"], "path": helper_pin["path"], "bytes": len(helper_raw), "sha256": sha(helper_raw), "version": "worldatlas-evidence-preparation-v1"},
        "interpretation": "157860872 is the maximum byte count recorded across all 12 complete phase objects in both accepted v14 reports. It remains below the recorded 268435456-byte phase cap. This is recorded phase-byte accounting, not process RSS or a new end-to-end resource-budget certification.",
        "limits": [
            "The original v14 computation was not rerun; its two accepted complete reports were authenticated and independently rescanned for every phase_bytes field.",
            "The audit does not establish exhaustive original raw/decoded/runtime resource accounting beyond the retained records.",
            "Source authority, license, legal boundaries, territorial meaning, hydrology, historical accuracy and geographic approval remain unresolved under their existing owners.",
            "No source acquisition, GIS computation, geography correction, import, migration, deployment or publication was performed.",
        ],
    }


def get_pointer(value, pointer):
    node = value
    for raw in pointer.lstrip("/").split("/"):
        key = raw.replace("~1", "/").replace("~0", "~")
        node = node[int(key)] if isinstance(node, list) else node[key]
    return node


def remove_pointer(value, pointer):
    parts = pointer.lstrip("/").split("/")
    node = value
    for raw in parts[:-1]:
        key = raw.replace("~1", "/").replace("~0", "~")
        node = node[int(key)] if isinstance(node, list) else node[key]
    key = parts[-1].replace("~1", "/").replace("~0", "~")
    if isinstance(node, list):
        del node[int(key)]
    else:
        del node[key]


def rejection_control(name, operation):
    try:
        operation()
    except (ValueError, KeyError, TypeError, FileExistsError, FileNotFoundError, OSError):
        return {"case": name, "expected": "reject", "observed": "rejected", "passed": True}
    raise ValueError("negative control unexpectedly passed: " + name)


def run_input_controls(baseline, analysis, helper, helper_pin, helper_raw):
    reports = []
    for pin_id in REPORT_IDS:
        pin = next(row for row in INPUTS if row["id"] == pin_id)
        raw = baseline.pinned_bytes(pin["path"])
        reports.append((pin, raw, json.loads(raw)))
    pin, raw, report = reports[0]
    controls = []
    for pointer in sorted(EXPECTED_PHASES):
        mutated = copy.deepcopy(report)
        remove_pointer(mutated, pointer)
        controls.append(rejection_control("missing-required-phase:" + pointer, lambda mutated=mutated: validate_report_object(mutated, REPORT_RUNS["input_07"])))
    controls.append(rejection_control("missing-maximum-candidate", lambda: validate_report_object({k: v for k, v in report.items() if k != "complete_fragment_scan"}, REPORT_RUNS["input_07"])))
    altered = bytearray(raw); altered[-1] = ord(" " if altered[-1] != ord(" ") else "\n")
    controls.append(rejection_control("altered-report-bytes", lambda: authenticate_report(bytes(altered), pin, REPORT_RUNS["input_07"])))
    foreign_pin = next(row for row in INPUTS if row["id"] == "input_08")
    controls.append(rejection_control("foreign-v14-report-in-v14-one-slot", lambda: authenticate_report(reports[1][1], pin, REPORT_RUNS["input_07"])))
    wrong_version = copy.deepcopy(report); wrong_version["run_id"] = "repro-v12-one-20261007"
    controls.append(rejection_control("wrong-v12-v14-target", lambda: validate_report_object(wrong_version, REPORT_RUNS["input_07"])))
    controls.append(rejection_control("unlisted-v12-input-path", lambda: find_pin_for_path(pin["path"].replace("v14", "v12"))))
    controls.append(rejection_control("stale-published-summary", lambda: require_summary(analysis, OLD_MAXIMUM)))
    changed_comparison = copy.deepcopy(report)
    rows = changed_comparison["source_and_atlas_comparisons"]["countries"]["NOR"]["subject_feature_comparisons"]
    if not rows:
        raise ValueError("accepted v14 report has no comparison row for the changed-output control")
    rows[0]["symmetric_difference_planar_area"] = float(rows[0]["symmetric_difference_planar_area"]) + 1.0
    changed_raw = json.dumps(changed_comparison, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode() + b"\n"
    controls.append(rejection_control("changed-comparison-output", lambda: authenticate_report(changed_raw, pin, REPORT_RUNS["input_07"])))
    if not analysis["maximum_recorded_phase_bytes"] == 157860872:
        raise ValueError("independent report scan no longer derives the observed maximum")
    return controls


def require_summary(analysis, summary_maximum):
    if summary_maximum != analysis["maximum_recorded_phase_bytes"]:
        raise ValueError("stale or false summary maximum")
    return True


def run_writer_controls(baseline, helper, run_id):
    vintage_root = ROOT / OWNED / "vintages"
    parent = vintage_root.parent
    for ancestor in [parent, *parent.parents]:
        if ancestor.is_symlink():
            raise ValueError("symlink in owned destination ancestry")
        if ancestor == ROOT.parent:
            break
    vintage_root.mkdir(mode=0o700, exist_ok=True)
    controls = []

    occupied = vintage_root / "control-occupied-directory"
    occupied.mkdir(mode=0o700)
    sentinel = occupied / "report.json"
    sentinel.write_text("foreign-preserved\n", encoding="utf-8")
    controls.append(rejection_control("occupied-run-directory", lambda: helper.NewVintage(baseline, OWNED, "control-occupied-directory", ["report.json"])))
    if sentinel.read_text(encoding="utf-8") != "foreign-preserved\n":
        raise ValueError("occupied run sentinel changed")
    controls[-1]["sentinel_preserved"] = True
    sentinel.unlink(); occupied.rmdir()

    broken = vintage_root / "control-broken-link"
    broken.symlink_to(vintage_root / "missing-target")
    controls.append(rejection_control("dangling-run-destination", lambda: helper.NewVintage(baseline, OWNED, "control-broken-link", ["report.json"])))
    if not broken.is_symlink():
        raise ValueError("dangling destination link changed")
    controls[-1]["link_preserved"] = True
    broken.unlink()

    occupied_output = vintage_root / "control-output-collision"
    occupied_output.mkdir(mode=0o700)
    out = occupied_output / "report.json"
    out.write_text("output-sentinel-preserved\n", encoding="utf-8")
    controls.append(rejection_control("occupied-output-file", lambda: helper.NewVintage(baseline, OWNED, "control-output-collision", ["report.json"])))
    if out.read_text(encoding="utf-8") != "output-sentinel-preserved\n":
        raise ValueError("occupied output sentinel changed")
    controls[-1]["sentinel_preserved"] = True
    out.unlink(); occupied_output.rmdir()

    controls.append(rejection_control("escaped-destination", lambda: helper.NewVintage(baseline, OWNED, "../escaped-run", ["report.json"])))
    return controls


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode()


def load_context():
    source_lock, helper_pin, helper_raw, helper = bootstrap_helper()
    baseline, _, _, _ = baseline_for(helper)
    pair_info = verify_pair_bindings(baseline, source_lock)
    analysis = analyze_reports(baseline, helper_pin, helper_raw, {"lock": source_lock, **pair_info})
    return source_lock, helper_pin, helper_raw, helper, baseline, pair_info, analysis


def run_one(run_id):
    source_lock, helper_pin, helper_raw, helper, baseline, pair_info, analysis = load_context()
    output = helper.NewVintage(baseline, OWNED, run_id, ["report.json"])
    script_bytes = HERE.joinpath(Path(__file__).name).read_bytes()
    controls = run_input_controls(baseline, analysis, helper, helper_pin, helper_raw)
    if run_id == "report-correction-one-20261009":
        controls.extend(run_writer_controls(baseline, helper, run_id))
    assessment = {"method_id": "correct-v14-recorded-phase-maximum", "maximum_recorded_phase_bytes": analysis["maximum_recorded_phase_bytes"], "phase_count": analysis["phase_count"], "phase_values": analysis["phases"], "prior_published_maximum_bytes": analysis["prior_published_maximum_bytes"], "correction_delta_bytes": analysis["correction_delta_bytes"], "phase_limit_bytes": analysis["phase_limit_bytes"], "remaining_below_limit_bytes": analysis["remaining_below_limit_bytes"]}
    value = {
        "version": 1, "issue": 1559, "kind": "measurement", "method_id": "correct-v14-recorded-phase-maximum", "outcome": "passed", "run_id": run_id,
        "assessment": assessment, "assessment_sha256": sha(canonical(assessment)),
        "input_reports": analysis["inputs"], "executed_runner_sha256": analysis["executed_runner_sha256"],
        "reporting_helper": analysis["reporting_helper"], "control_results": controls,
        "corrected_interpretation": analysis["interpretation"], "limits": analysis["limits"],
        "executed_reporting_code": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "bytes": len(script_bytes), "sha256": sha(script_bytes)},
    }
    records = output.publish({"report.json": value})
    print(json.dumps({"run_id": run_id, "report": records[0], "publication": json.loads((output.root / "publication.json").read_text()), "assessment_sha256": value["assessment_sha256"], "control_count": len(controls)}, indent=2))


def read_complete_run(helper, baseline, run_id):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{7,63}", run_id):
        raise ValueError("unsafe run id")
    folder = ROOT / OWNED / "vintages" / run_id
    report_path = folder / "report.json"
    receipt_path = folder / "publication.json"
    if report_path.is_symlink() or receipt_path.is_symlink() or not report_path.is_file() or not receipt_path.is_file():
        raise ValueError("run output/receipt is missing or symlinked")
    value = json.loads(report_path.read_bytes())
    receipt = json.loads(receipt_path.read_bytes())
    row = next((x for x in receipt.get("outputs", []) if x.get("path") == str(report_path.relative_to(ROOT))), None)
    raw = report_path.read_bytes()
    if receipt.get("status") != "complete" or not row or row.get("bytes") != len(raw) or row.get("sha256") != sha(raw):
        raise ValueError("fresh run does not have a valid whole-file publication receipt")
    if value.get("run_id") != run_id or value.get("issue") != 1559 or value.get("outcome") != "passed":
        raise ValueError("fresh run identity/status mismatch")
    if value.get("executed_reporting_code", {}).get("sha256") != sha(HERE.joinpath(Path(__file__).name).read_bytes()):
        raise ValueError("fresh run did not execute current reporting code bytes")
    for item in value.get("input_reports", []):
        pin = find_pin_for_path(item.get("path", ""))
        if item.get("commit") != BASELINE_COMMIT or item.get("sha256") != pin["sha256"] or item.get("bytes") != pin["bytes"]:
            raise ValueError("fresh run report input is not an accepted v14 pin")
    return value, row, sha(receipt_path.read_bytes())


def summarize(run_one_id, run_two_id, summary_id):
    source_lock, helper_pin, helper_raw, helper, baseline, _, analysis = load_context()
    first, first_row, first_receipt = read_complete_run(helper, baseline, run_one_id)
    second, second_row, second_receipt = read_complete_run(helper, baseline, run_two_id)
    if first["assessment"] != second["assessment"] or first["assessment_sha256"] != second["assessment_sha256"]:
        raise ValueError("fresh independent reporting runs disagree")
    pairwise = {
        "version": 1, "issue": 1559, "kind": "reproducibility", "method_id": "correct-v14-recorded-phase-maximum", "outcome": "passed",
        "run_one_sha256": first["assessment_sha256"], "run_two_sha256": second["assessment_sha256"],
        "comparison": "Both fresh exclusive runs independently authenticated both v14 reports, found the exact same 12 phase-byte pointers and values, derived the same maximum, and emitted identical canonical assessments.",
        "runs": [
            {"run_id": run_one_id, "path": first_row["path"], "bytes": first_row["bytes"], "sha256": first_row["sha256"], "publication_sha256": first_receipt, "assessment_sha256": first["assessment_sha256"]},
            {"run_id": run_two_id, "path": second_row["path"], "bytes": second_row["bytes"], "sha256": second_row["sha256"], "publication_sha256": second_receipt, "assessment_sha256": second["assessment_sha256"]},
        ],
    }
    positive = {"version": 1, "issue": 1559, "kind": "positive-control", "method_id": "correct-v14-recorded-phase-maximum", "outcome": "passed", "cases": [{"case": "both-authenticated-v14-runs", "expected": "complete exact phase inventory and matching maximum", "observed": "157860872 bytes in each report", "passed": True}]}
    negative_cases = [x for x in first["control_results"] if x.get("expected") == "reject"]
    if len(negative_cases) < 20 or any(not x.get("passed") for x in negative_cases):
        raise ValueError("required negative controls are missing or failed")
    negative = {"version": 1, "issue": 1559, "kind": "negative-control", "method_id": "correct-v14-recorded-phase-maximum", "outcome": "passed", "cases": negative_cases}
    vintage = helper.NewVintage(baseline, OWNED, summary_id, ["pairwise-reproducibility.json", "positive-controls.json", "negative-controls.json"])
    records = vintage.publish({"pairwise-reproducibility.json": pairwise, "positive-controls.json": positive, "negative-controls.json": negative})
    print(json.dumps({"summary_id": summary_id, "assessment": first["assessment"], "outputs": records, "publication": json.loads((vintage.root / "publication.json").read_text()), "negative_controls": len(negative_cases)}, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id")
    parser.add_argument("--compare-runs", nargs=2, metavar=("RUN_ONE", "RUN_TWO"))
    parser.add_argument("--summary-id")
    args = parser.parse_args()
    if args.run_id and not args.compare_runs and not args.summary_id:
        run_one(args.run_id)
    elif args.compare_runs and args.summary_id and not args.run_id:
        summarize(args.compare_runs[0], args.compare_runs[1], args.summary_id)
    else:
        parser.error("use --run-id RUN, or --compare-runs RUN_ONE RUN_TWO --summary-id SUMMARY_RUN")


if __name__ == "__main__":
    main()
