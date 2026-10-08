#!/usr/bin/env python3
"""Safely reproduce the retained #1319 row/control comparison in a new vintage."""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import re
import sys

from safe_outputs import (
    EVALUATION_COMMIT, EVIDENCE_PATH, admitted_baseline, exact_report_inputs,
    exercise_preflight_controls, new_vintage_with_api, safe_output_root,
    verify_historical_manifest,
)

REPO = Path(__file__).resolve().parents[3]
ISSUE = 1485
PRODUCTS = ["summary.json", "correction-ledger.json", "positive-control.json",
            "negative-control.json", "reproducibility.json"]


def compare_retained_reports(original_bytes: bytes, corrected_gzip: bytes):
    original = json.loads(original_bytes)
    corrected = json.loads(gzip.decompress(corrected_gzip))
    old_rows = original["exact_subjects"]
    new_rows = corrected["exact_subjects"]
    if len(old_rows) != 224 or len(new_rows) != 224:
        raise ValueError("Expected complete 224-subject original and corrected reports")
    old_ids = [row["id"] for row in old_rows]
    new_ids = [row["id"] for row in new_rows]
    if old_ids != new_ids or len(set(old_ids)) != 224:
        raise ValueError("Original and corrected report subject keys/order differ")
    if original["province_assessments"] != corrected["province_assessments"]:
        raise ValueError("The 27 retained province-group assessments changed")

    changes = []
    for old, new in zip(old_rows, new_rows):
        if old["id"] != new["id"]:
            raise ValueError("Row join changed identity")
        for field in old:
            if old[field] != new.get(field):
                changes.append({"id": old["id"], "name": old.get("name"), "field": field,
                                "before": old[field], "after": new.get(field)})
    if len(changes) != 16 or any(row["before"] is not None for row in changes):
        raise ValueError("Corrected roster comparison no longer has exactly 16 null-to-source values")
    changed_subjects = {row["id"] for row in changes}
    agar = [row for row in new_rows if row.get("province_name") == "Agar"]
    if len(agar) != 4 or {row["id"] for row in agar} != changed_subjects:
        raise ValueError("The four Agar subjects are no longer exactly the changed subjects")
    expected_agar_hash = "190564a28ca08e96785ad20d9a6d2d235c7b0972d731c102ba361c16ac01374e"
    if not all(row.get("current_roster_source_system") == "IGOD / Local Government Directory" and
               row.get("current_roster_source_sha256") == expected_agar_hash and
               row.get("current_roster_name_exact_match") is True for row in agar):
        raise ValueError("Agar source binding differs from the retained IGOD capture")
    sheopur = next(row for row in corrected["province_assessments"] if row["province"] == "Sheopur")
    if sheopur.get("lgd_source_sha256") is not None or sheopur.get("classification") != "insufficient-evidence":
        raise ValueError("Sheopur uncertainty was not preserved")
    counts = {category: sum(row.get("classification") == category for row in new_rows)
              for category in ("justified", "correction-needed", "insufficient-evidence")}
    if counts != {"justified": 0, "correction-needed": 11, "insufficient-evidence": 213}:
        raise ValueError("Retained classification totals changed")
    source = corrected.get("source", {})
    if (source.get("features_actual") != 6822 or source.get("features_metadata") != 6836 or
            source.get("count_difference") != 14):
        raise ValueError("Retained geoBoundaries 6,822/6,836 discrepancy changed or is absent")
    return old_rows, new_rows, changes, counts, corrected


def run_controls(run_id: str, *, repo: Path = REPO, state=None, before_publish=None):
    # Reject the whole output vintage, not just the last summary/ledger files.
    safe_output_root(repo, run_id, PRODUCTS)
    state = state or admitted_baseline(repo)
    issue, contract, baseline, module, commit, files, pins = state
    vintage = new_vintage_with_api(repo, baseline, module, run_id, PRODUCTS)
    historical = verify_historical_manifest(repo, baseline)
    original_bytes, run_one, run_two = exact_report_inputs(baseline)
    old_rows, new_rows, changes, counts, corrected = compare_retained_reports(original_bytes, run_one)
    expected_ids = contract["evidence_quality"]["subject_ids"]
    if set(row["id"] for row in new_rows) != set(expected_ids):
        raise ValueError("Complete corrected rows differ from the exact issue scope")
    source_inventory_path = EVIDENCE_PATH + "sources/source-inventory.json"
    source_inventory = json.loads(baseline.pinned_bytes(source_inventory_path))
    boundary = next(row for row in source_inventory["sources"] if row["id"] == "geoBoundaries-IND-ADM3-2018")
    roster = next(row for row in source_inventory["sources"] if row["id"] == "current-admin-roster:Agar-Malwa")
    if (boundary["compressed_sha256"] != pins["data/global-sources/IND-ADM3.geojson.gz"] or
            boundary["metadata_sha256"] != pins["data/global-sources/IND-ADM3-metadata.json"] or
            roster["sha256"] != "190564a28ca08e96785ad20d9a6d2d235c7b0972d731c102ba361c16ac01374e"):
        raise ValueError("Original source inventory hashes differ from retained pins")

    adverse = exercise_preflight_controls(repo, "adverse-" + run_id[:24])
    positive = {"version": 1, "method_id": "safe-output-admission", "kind": "positive-control",
                "outcome": "passed", "baseline_commit": commit,
                "subjects": len(new_rows), "province_groups": len(corrected["province_assessments"]),
                "corrected_fields": len(changes), "classification_counts": counts,
                "full_retained_rows_compared": True, "source_bytes_redecoded": False}
    negative = {"version": 1, "method_id": "safe-output-admission", "kind": "negative-control",
                "outcome": "passed", "preflight_cases": adverse,
                "original_assessments_sha256": module.sha256(original_bytes),
                "retained_output_pair_equal": run_one == run_two,
                "no_symlink_target_or_preexisting_sentinel_overwritten": True}
    repro = {"version": 1, "method_id": "safe-output-admission", "kind": "reproducibility",
             "outcome": "passed", "run_one_sha256": module.sha256(run_one),
             "run_two_sha256": module.sha256(run_two), "subjects": len(new_rows),
             "province_groups": len(corrected["province_assessments"]),
             "corrected_fields": len(changes), "new_scientific_generation": False}
    summary = {"version": 1, "issue": ISSUE, "evaluation_commit": EVALUATION_COMMIT,
               "output_safety_baseline_commit": commit, "subjects": len(new_rows),
               "province_groups": len(corrected["province_assessments"]),
               "corrected_fields": len(changes), "newly_roster_bound_subjects": 4,
               "classification_counts": counts, "sheopur_roster_source_available": False,
               "geoboundaries_actual_features": 6822, "geoboundaries_metadata_features": 6836,
               "geoboundaries_count_difference": 14, "historical_inputs_checked": historical["count"],
               "historical_phase_input_bytes": historical["complete_phase_historical_bytes"],
               "complete_phase_input_bytes": historical["complete_phase_input_bytes"],
               "new_scientific_generation": False, "geographic_approval": False}
    ledger = {"version": 1, "issue": ISSUE, "baseline_assessments_sha256": module.sha256(original_bytes),
              "corrected_assessments_sha256": module.sha256(run_one), "changes": changes,
              "unchanged_province_assessments_sha256": module.sha256(json.dumps(
                  corrected["province_assessments"], sort_keys=True, separators=(",", ":")).encode()),
              "uncertainty_preserved": [
                  "geoBoundaries source represents 2018 ADM3/Sub-District; legal territorial meaning, current correspondence, completeness and rights were not re-adjudicated.",
                  "Original source inventory reports 6,822 retained features versus 6,836 metadata units; the 14-unit discrepancy remains unresolved.",
                  "IGOD is administrative roster evidence only; it does not establish jurisdiction or polygons, and no page-specific Agar-Malwa reuse terms were identified.",
                  "Sheopur remains without a retained current roster source; all other source, boundary and current-legal uncertainties remain as in the original packet."]}
    values = {"summary.json": summary, "correction-ledger.json": ledger,
              "positive-control.json": positive, "negative-control.json": negative,
              "reproducibility.json": repro}
    if before_publish is not None:
        before_publish(vintage.root)
    records = vintage.publish(values)
    return {"issue": issue["number"], "baseline_commit": commit, "outputs": records,
            "subjects": len(old_rows), "province_groups": len(corrected["province_assessments"]),
            "field_changes": len(changes), "historical_evaluation": historical}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", args.run_id):
        parser.error("run-id must be 1-64 lowercase letters, digits or interior hyphens")
    try:
        result = run_controls(args.run_id)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as error:
        print(f"control output admission failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
