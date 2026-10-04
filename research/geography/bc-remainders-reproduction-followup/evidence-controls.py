#!/usr/bin/env python3
"""Bind the already executed source checks to typed, immutable validation receipts."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
VALIDATION = HERE / "validation"

def read(name: str):
    return json.loads((HERE / name).read_text(encoding="utf-8"))

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(name: str, value: dict) -> None:
    path = VALIDATION / name
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite validation vintage: {path.relative_to(HERE)}")
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

def main() -> None:
    VALIDATION.mkdir(exist_ok=False)
    extraction = read("input-extraction-receipt.json")
    mapping = read("vintages/reproduction-run-1/source-mapping-validation.json")
    comparison = read("reproduction-receipt.json")
    differences = read("mapping-differences.json")
    controls = read("negative-controls.json")
    if not comparison["two_runs_byte_identical"] or not comparison["numeric_and_geometric_results_otherwise_identical"]:
        raise ValueError("Reproduction evidence does not pass the positive result controls")
    if comparison["original_retained_outputs_changed"] or controls["retained_originals_changed"]:
        raise ValueError("Original source or result bytes changed")
    if len(differences["historical_scalar_mapping_conflicts"]) != 84:
        raise ValueError("Mapping conflict count does not match the reconciled ledger")
    if len(differences["exact_CSD_candidate_mapping_differences"]) != 426 or len(differences["exact_CD_roster_mapping_differences"]) != 148:
        raise ValueError("Exact ambiguous row ledgers do not reconcile")
    if len(controls["controls"]) != 5 or any(x["outcome"] != "passed" for x in controls["controls"]):
        raise ValueError("Required negative control missing or failed")
    run_hashes = []
    for run in (1, 2):
        paths = [HERE / f"vintages/reproduction-run-{run}/{name}" for name in (
            "cd-assessments.json", "csd-crosswalk.csv", "source-mapping-validation.json")]
        run_hashes.append(hashlib.sha256("\n".join(sha(p) for p in paths).encode()).hexdigest())
    if run_hashes[0] != run_hashes[1]:
        raise ValueError("Independent run hashes differ")

    method = "bc-remainder-audit"
    write("positive-control.json", {
        "version": 1, "method_id": method, "kind": "positive-control", "outcome": "passed",
        "assigned_cd_count": extraction["subject_count"],
        "target_csd_count": extraction["target_csd_source_features_retained"],
        "all_parent_chains_present": not mapping["missing_parent_chains"],
        "all_numeric_and_geometric_results_reconciled": comparison["numeric_and_geometric_results_otherwise_identical"],
        "original_retained_outputs_changed": comparison["original_retained_outputs_changed"]
    })
    write("negative-control.json", {
        "version": 1, "method_id": method, "kind": "negative-control", "outcome": "passed",
        "source_receipt": "research/geography/bc-remainders-reproduction-followup/negative-controls.json",
        "control_count": len(controls["controls"]),
        "all_controls_passed": all(x["outcome"] == "passed" for x in controls["controls"]),
        "retained_originals_changed": controls["retained_originals_changed"]
    })
    write("reproducibility.json", {
        "version": 1, "method_id": method, "kind": "reproducibility", "outcome": "passed",
        "run_one_sha256": run_hashes[0], "run_two_sha256": run_hashes[1],
        "run_output_names": ["cd-assessments.json", "csd-crosswalk.csv", "source-mapping-validation.json"]
    })
    summary = {
        "assigned_cd_count": extraction["subject_count"],
        "reproduced_csd_row_count": comparison["original_csd_identities_preserved"],
        "complete_geoboundaries_feature_count": extraction["original_source_feature_count"],
        "unique_source_member_id_count": mapping["assignment_map"]["unique_source_member_ids"] + len(mapping["assignment_map"]["conflicts"]),
        "unique_unambiguous_source_member_id_count": mapping["assignment_map"]["unique_source_member_ids"],
        "ambiguous_source_member_id_count": len(mapping["assignment_map"]["conflicts"]),
        "ambiguous_csd_candidate_row_count": len(differences["exact_CSD_candidate_mapping_differences"]),
        "ambiguous_cd_roster_row_count": len(differences["exact_CD_roster_mapping_differences"]),
        "independent_run_count": 2,
        "all_unambiguous_source_candidate_rows_reconciled": True,
        "unexpected_csv_difference_count": len(differences["unexpected_CSV_differences"]),
        "unexpected_json_difference_count": len(differences["unexpected_JSON_differences"])
    }
    write("summary.json", summary)

if __name__ == "__main__":
    main()
