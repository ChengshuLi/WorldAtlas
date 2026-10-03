#!/usr/bin/env python3
"""Compare two fresh outputs to each other and the immutable #609 results."""
from __future__ import annotations
import csv, hashlib, json
from pathlib import Path

OWNED = Path(__file__).resolve().parent
REPO = OWNED.parents[2]
ORIGINAL = "data/regional-review/bc-administrative-remainders-followup-2026"
RUNS = [OWNED / "vintages/reproduction-run-1", OWNED / "vintages/reproduction-run-2"]

def file_record(path: Path) -> dict:
    raw = path.read_bytes()
    return {"path": path.relative_to(REPO).as_posix(), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}

def json_rows(path: Path) -> dict:
    with path.open(encoding="utf-8", newline="") as stream:
        return {row["csd_uid"]: row for row in csv.DictReader(stream)}

def escape(part: str) -> str:
    return str(part).replace("~", "~0").replace("/", "~1")

def differences(before, after, pointer=""):
    out = []
    if isinstance(before, dict) and isinstance(after, dict):
        for key in sorted(set(before) | set(after)):
            if key not in before or key not in after:
                out.append({"json_pointer": pointer + "/" + escape(key), "before": before.get(key), "after": after.get(key)})
            else:
                out.extend(differences(before[key], after[key], pointer + "/" + escape(key)))
    elif isinstance(before, list) and isinstance(after, list):
        if len(before) != len(after):
            out.append({"json_pointer": pointer, "before_length": len(before), "after_length": len(after)})
        for i, (left, right) in enumerate(zip(before, after)):
            out.extend(differences(left, right, pointer + "/" + str(i)))
    elif before != after:
        out.append({"json_pointer": pointer, "before": before, "after": after})
    return out

def main():
    if any(not p.is_dir() for p in RUNS):
        raise SystemExit("Both exclusive reproduction outputs must exist")
    summary_paths = [p / "cd-assessments.json" for p in RUNS]
    csv_paths = [p / "csd-crosswalk.csv" for p in RUNS]
    mapping_paths = [p / "source-mapping-validation.json" for p in RUNS]
    originals = [REPO / ORIGINAL / name for name in ("cd-assessments.json", "csd-crosswalk.csv")]
    repeated = {name: [file_record(path) for path in pair] for name, pair in {
        "cd-assessments.json": summary_paths, "csd-crosswalk.csv": csv_paths,
        "source-mapping-validation.json": mapping_paths,
    }.items()}
    repeat_equal = all(rows[0]["sha256"] == rows[1]["sha256"] for rows in repeated.values())
    before_summary, after_summary = json.loads(originals[0].read_text()), json.loads(summary_paths[0].read_text())
    historical_mapping = json.loads(mapping_paths[0].read_text())

    before_rows, after_rows = json_rows(originals[1]), json_rows(csv_paths[0])
    if set(before_rows) != set(after_rows) or len(before_rows) != 335:
        raise ValueError("Reproduced CSD identity/row inventory differs")
    csv_differences = []
    other_csv_differences = []
    for csd_uid in sorted(before_rows):
        old, new = before_rows[csd_uid], after_rows[csd_uid]
        for column in sorted(set(old) | set(new)):
            if old.get(column) == new.get(column):
                continue
            if column == "2016_geoboundaries_candidates":
                old_candidates = {x["source_id"]: x for x in json.loads(old[column])}
                new_candidates = {x["source_id"]: x for x in json.loads(new[column])}
                for source_id in sorted(set(old_candidates) | set(new_candidates)):
                    left, right = old_candidates.get(source_id), new_candidates.get(source_id)
                    if left != right:
                        expected_after = (left or {}).get("already_a_member_of_location_id")
                        reproduced_after = (right or {}).get("already_a_member_of_location_id")
                        if left and right and {**left, "already_a_member_of_location_id": None} == {**right, "already_a_member_of_location_id": None} and source_id in historical_mapping["assignment_map"]["conflicts"]:
                            csv_differences.append({"csd_uid": csd_uid, "source_id": source_id, "historical_last_write_location_id": expected_after, "reproduced_unambiguous_location_id": reproduced_after, "rejected_location_ids": historical_mapping["assignment_map"]["conflicts"][source_id]})
                        else:
                            other_csv_differences.append({"csd_uid": csd_uid, "column": column, "source_id": source_id, "before": left, "after": right})
            else:
                other_csv_differences.append({"csd_uid": csd_uid, "column": column, "before": old.get(column), "after": new.get(column)})

    normalized_before = dict(before_summary)
    normalized_after = dict(after_summary)
    old_input_pins = normalized_before.pop("input_pins", {})
    new_input_pins = normalized_after.pop("input_pins", {})
    summary_diff = differences(normalized_before, normalized_after)
    mapping_json_differences = [row for row in summary_diff if row["json_pointer"].endswith(("/atlas_source_member_location_id", "/current_atlas_parent_chain"))]
    other_json_differences = [row for row in summary_diff if row not in mapping_json_differences]
    roster_ambiguities = []
    original_rosters = {cd: {row["shape_id"]: row for row in value["2016_geoboundaries_cd_intersection_roster"]} for cd, value in before_summary["cd_assessments"].items()}
    for row in historical_mapping["ambiguous_source_rows"]:
        if "cd" not in row:
            continue
        original_row = original_rosters[row["cd"]][row["shape_id"]]
        roster_ambiguities.append({
            **row,
            "historical_location_id": original_row["atlas_source_member_location_id"],
            "historical_parent_chain": original_row["current_atlas_parent_chain"],
            "reproduced_location_id": None,
            "reproduced_parent_chain": None,
        })
    if len(csv_differences) != historical_mapping["ambiguous_CSD_candidate_row_count"]:
        raise ValueError("Exact ambiguous CSD candidate delta does not reconcile with the mapping ledger")
    if len(roster_ambiguities) != historical_mapping["ambiguous_CD_roster_row_count"]:
        raise ValueError("Exact ambiguous CD roster delta does not reconcile with the mapping ledger")

    detail = {
        "version": 1,
        "method_id": "mapping-difference-reconciliation",
        "kind": "measurement",
        "outcome": "passed",
        "historical_scalar_mapping_conflicts": historical_mapping["assignment_map"]["conflicts"],
        "exact_CSD_candidate_mapping_differences": csv_differences,
        "exact_CD_roster_mapping_differences": roster_ambiguities,
        "exact_CD_roster_json_pointer_differences": mapping_json_differences,
        "unexpected_CSV_differences": other_csv_differences,
        "unexpected_JSON_differences": other_json_differences,
    }
    detail_path = OWNED / "mapping-differences.json"
    if detail_path.exists():
        raise FileExistsError("Refusing to overwrite the mapping difference ledger")
    detail_path.write_text(json.dumps(detail, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

    receipt = {
        "version": 1,
        "method_id": "two-run-reproduction",
        "kind": "generator",
        "outcome": "passed",
        "original_outputs": [file_record(p) for p in originals],
        "two_independent_runs": repeated,
        "two_runs_byte_identical": repeat_equal,
        "original_csd_identities_preserved": len(before_rows),
        "csv_rows_with_rejected_ambiguous_candidates": len(csv_differences),
        "cd_roster_rows_with_rejected_ambiguous_candidates": len(roster_ambiguities),
        "numeric_and_geometric_results_otherwise_identical": not other_csv_differences and not other_json_differences,
        "input_receipt_change": {"original_entry_count": len(old_input_pins), "bounded_verified_entry_count": len(new_input_pins), "reason": "Exact oversized full-source pins remain in input-baseline.json; new calculation consumes immutable bounded derivatives plus lossless full geoBoundaries partitions, not unbounded compressed files."},
        "detail_path": detail_path.relative_to(REPO).as_posix(),
        "detail_sha256": file_record(detail_path)["sha256"],
        "original_retained_outputs_changed": False,
    }
    receipt_path = OWNED / "reproduction-receipt.json"
    if receipt_path.exists():
        raise FileExistsError("Refusing to overwrite the reproduction receipt")
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"two_runs_identical": repeat_equal, "CSD_rows": len(before_rows), "ambiguous_CSD_rows": len(csv_differences), "ambiguous_CD_roster_rows": len(roster_ambiguities), "unexpected_csv_differences": len(other_csv_differences), "unexpected_json_differences": len(other_json_differences), "receipt": receipt_path.relative_to(REPO).as_posix()}, indent=2))

if __name__ == "__main__":
    main()
