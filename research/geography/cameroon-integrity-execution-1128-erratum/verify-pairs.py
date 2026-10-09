#!/usr/bin/env python3
"""Verify two independently named safe runs from each successor entry point."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
VINTAGES = Path(__file__).resolve().parent / "vintages"
sys.path.insert(0, str(ROOT))
from scripts.evidence.contracts import exact_rows
from scripts.evidence.immutable import MAX_FILE_BYTES, MAX_PHASE_BYTES


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load_run(name, expected):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", name):
        raise ValueError("Unsafe vintage name")
    root = VINTAGES / name
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Run directory missing or linked")
    receipt = json.loads((root / "publication.json").read_bytes())
    if receipt.get("status") != "complete":
        raise ValueError("Run lacks a completion receipt")
    records = receipt.get("outputs", [])
    by_name = {}
    for record in records:
        path = record["path"]
        if not path.startswith("research/geography/cameroon-integrity-execution-1128-erratum/vintages/" + name + "/"):
            raise ValueError("Receipt escaped its admitted vintage")
        target = ROOT / path
        if target.is_symlink() or not target.is_file():
            raise ValueError("Receipt output missing or linked")
        raw = target.read_bytes()
        if len(raw) > MAX_FILE_BYTES:
            raise ValueError("Published ordinary output exceeds 32 MiB")
        if len(raw) != record["bytes"] or sha(raw) != record["sha256"]:
            raise ValueError("Publication record does not match output bytes")
        if target.name in by_name:
            raise ValueError("Duplicate output basename")
        by_name[target.name] = raw
    if set(by_name) != set(expected):
        raise ValueError("Unexpected or incomplete published output set")
    return root, by_name


def compare_pair(label, first, second, expected, exclusions=()):
    one_root, one = load_run(first, expected)
    two_root, two = load_run(second, expected)
    common = set(one) - set(exclusions)
    if any(one[name] != two[name] for name in common):
        raise ValueError(label + " pair differs byte-for-byte")
    if set(one) != set(two):
        raise ValueError(label + " output inventories differ")
    return {"entry_point": label, "fresh_vintages": [first, second],
            "byte_identical_products": sorted(common),
            "run_specific_controls": list(exclusions),
            "first_publication_sha256": sha((one_root / "publication.json").read_bytes()),
            "second_publication_sha256": sha((two_root / "publication.json").read_bytes())}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("corrected_one")
    parser.add_argument("corrected_two")
    parser.add_argument("legacy_one")
    parser.add_argument("legacy_two")
    parser.add_argument("pair_vintage")
    args = parser.parse_args()
    from common import EXPECTED_IDS, OLD, OWNED, SOURCE, baseline, source_joins
    from scripts.evidence.immutable import NewVintage
    base = baseline()
    pair_writer = NewVintage(base, OWNED, args.pair_vintage,
                             ["reproduction-positive-control.json", "reproduction-negative-control.json",
                              "reproducibility.json", "pair-verification.json"])
    corrected = ["corrected-measurements.json", "source-joins.json", "independent-geodesic-check.json",
                 "duplicate-crosswalk-fixture.json", "controls.json", "geometry-positive-control.json",
                 "geometry-negative-control.json", "geometry-mixed-winding-control.json", "roster-controls.json",
                 "admission-controls.json", "input-mutation-controls.json",
                 "failed-publication-control.json", "provenance.json"]
    legacy = ["legacy-replay.json", "legacy-products.json", "legacy-provenance.json"]
    result = {"version": 1,
              "corrected": compare_pair("reproduce-corrected.py", args.corrected_one, args.corrected_two,
                                         corrected, exclusions=("failed-publication-control.json",)),
              "legacy": compare_pair("reproduce-legacy.py", args.legacy_one, args.legacy_two, legacy)}
    first_root, first = load_run(args.corrected_one, corrected)
    corrected_data = json.loads(first["corrected-measurements.json"])
    archived = json.loads(base.materialized_bytes(OLD + "/corrected-measurements.json"))
    numeric_values = 0
    corrected_rows = exact_rows(corrected_data["rows"], EXPECTED_IDS, key="subject_id")
    archived_rows = exact_rows(archived["rows"], EXPECTED_IDS, key="subject_id")
    for identity in EXPECTED_IDS:
        row, previous = corrected_rows[identity], archived_rows[identity]
        if row["recorded_numeric_values"] != previous["recorded_numeric_values"]:
            raise ValueError("A historical numeric measurement changed")
        if row["measurements"] != row["recorded"]:
            raise ValueError("One of the selected geodesic scores fails the corrected reconciliation")
        numeric_values += len(row["recorded_numeric_values"])
    if numeric_values != 2486 or len(corrected_rows) != 226 or len(corrected_data["aggregate_counts"]) != 14:
        raise ValueError("Unexpected corrected subject, numeric, or aggregate counts")
    if corrected_data["aggregate_counts"] != archived["aggregate_counts"]:
        raise ValueError("One of the 14 historical aggregate counts changed")
    independent = exact_rows(json.loads(first["independent-geodesic-check.json"])["rows"], EXPECTED_IDS, key="subject_id")
    if len(independent) != 226 or sum(len(x["scores"]) for x in independent.values()) != 678:
        raise ValueError("Independent geodesic check is not exact for 226 rows and 678 scores")
    if any(corrected_rows[i]["measurements"] != independent[i]["scores"] for i in EXPECTED_IDS):
        raise ValueError("Independent exterior-minus-hole ring scores differ from the corrected producer")
    source_join = exact_rows(json.loads(first["source-joins.json"])["rows"], EXPECTED_IDS, key="subject_id")
    if len(source_join) != 226:
        raise ValueError("Independent source/parent joins are incomplete")
    original_crosswalk = json.loads(base.materialized_bytes(SOURCE + "/candidate-crosswalk.json"))
    from common import source_joins
    if json.loads(first["source-joins.json"]) != source_joins(base, original_crosswalk["crosswalk"]):
        raise ValueError("Persisted joins do not reproduce from the independent pinned source rows")
    fixture_raw = first["duplicate-crosswalk-fixture.json"]
    fixture = json.loads(fixture_raw)
    if (len(fixture["crosswalk"]) != 226 or fixture["crosswalk"][:-1] != original_crosswalk["crosswalk"][:-1]
            or fixture["crosswalk"][-1] != original_crosswalk["crosswalk"][0]):
        raise ValueError("Retained duplicate crosswalk is not a one-row replacement of the original")
    missing = sorted(set(EXPECTED_IDS) - {row["subject_id"] for row in fixture["crosswalk"]})
    if missing != ["gb:CMR:ADM3:9386221B99754301414299"]:
        raise ValueError("Retained duplicate crosswalk omitted an unexpected issue subject")
    roster = json.loads(first["roster-controls.json"])
    if any(row["accepted"] for row in roster["new_exact_crosswalk_controls"]["crosswalk_cases"].values()):
        raise ValueError("A malformed crosswalk control was accepted")
    issue_controls = roster["preserved_issue_id_controls"]["cases"]
    if (not issue_controls["exact"]["accepted"] or
            any(issue_controls[x]["accepted"] for x in ("duplicate", "missing", "fabricated"))):
        raise ValueError("Original successful issue-ID guard no longer passes")
    admission = json.loads(first["admission-controls.json"])["cases"]
    mutation = json.loads(first["input-mutation-controls.json"])
    if not all(admission.values()) or not all(x["rejected_before_compute_or_publication"] for x in mutation.values()):
        raise ValueError("Destination or changed-input/code admission control failed")
    legacy_root, legacy_files = load_run(args.legacy_one, legacy)
    legacy_replay = json.loads(legacy_files["legacy-replay.json"])
    if not legacy_replay["generated_products_equal"] or not all(
        x["protected_originals_unchanged_after_this_replay"] for x in legacy_replay["runs"]
    ):
        raise ValueError("Legacy replay changed protected sources or produced different products")
    products = json.loads(legacy_files["legacy-products.json"])
    import base64
    legacy_report_path = OLD + "/reproduction/legacy-integrity-reproduction.json"
    legacy_report = json.loads(base64.b64decode(products[legacy_report_path]["base64"]))
    if legacy_report["original_packet_modified"] or not legacy_report["duplicate_output_bytes_equal_original_roster"]:
        raise ValueError("Pinned legacy wrapper did not reproduce its recorded exact/duplicate results")
    if not all(x["matches_immutable_original"] for run in legacy_report["runs"] for x in run["outputs"].values()):
        raise ValueError("Legacy outputs differ from their pinned historical bytes")
    for filename, expected_kind in (("geometry-positive-control.json", "positive-control"),
                                    ("geometry-negative-control.json", "negative-control")):
        control = json.loads(first[filename])
        if (control.get("method_id") != "orientation-safe-geodesic-recomputation" or
                control.get("kind") != expected_kind or control.get("outcome") != "passed"):
            raise ValueError("Geodesic measurement control is missing or unsuccessful")
    phase_receipts = [
        (first["provenance.json"], json.loads((first_root / "publication.json").read_bytes())),
        (legacy_files["legacy-provenance.json"], json.loads((legacy_root / "publication.json").read_bytes())),
    ]
    for raw_provenance, receipt in phase_receipts:
        provenance = json.loads(raw_provenance)
        if provenance["phase_input_bytes"] > MAX_PHASE_BYTES:
            raise ValueError("Complete decoded-input phase exceeds 256 MiB")
        input_bytes = sum(row["bytes"] for row in provenance["unique_phase_inputs"])
        if input_bytes != provenance["phase_input_bytes"]:
            raise ValueError("Phase byte receipt does not sum to captured unique inputs")
        total_output = sum(row["bytes"] for row in receipt["outputs"])
        if input_bytes + total_output + 4096 > MAX_PHASE_BYTES:
            raise ValueError("Captured input and output closure exceeds 256 MiB")
    result["content_checks"] = {"issue_subjects": 226, "original_numeric_values": numeric_values,
                                "corrected_scores": 678, "aggregate_counts": 14,
                                "independent_ring_scores_match": True,
                                "exact_candidate_parent_joins": 226,
                                "duplicate_fixture_bytes": len(fixture_raw), "duplicate_fixture_sha256": sha(fixture_raw),
                                "missing_issue_subject": missing[0],
                                "legacy_generated_products_match_pins": True,
                                "protected_originals_unchanged": True,
                                "aggregate_counts_by_name": corrected_data["aggregate_counts"],
                                "scope_count": corrected_data["scope_count"],
                                "ocha_tier_counts": corrected_data["ocha_neighboring_tiers"],
                                "duplicate_crosswalk": {
                                    "row_count": len(fixture["crosswalk"]),
                                    "unique_subjects": len({row["subject_id"] for row in fixture["crosswalk"]}),
                                    "missing_subject_count": len(missing),
                                },
                                "issue_reported_fixture": {
                                    "bytes": 263846,
                                    "sha256": "3dba096bc814c323f99ccc5a86a5e7a4c977a58b1f7e85f6332f6088107e0818",
                                    "exact_bytes_retained": False,
                                    "reproduced": False,
                                },
                                "phase_input_bytes": sum(base.consumed.values()),
                                "decoded_input_files": [x for x in base.consumed if ":decoded:" in x]}
    for name in (args.corrected_one, args.corrected_two):
        root, files = load_run(name, corrected)
        failure = json.loads(files["failed-publication-control.json"])
        if failure.get("status") != "failed" or not failure.get("publication_receipt_absent"):
            raise ValueError("A post-computation fault was incorrectly published as success")
        partial = ROOT / failure["partial_run_path"]
        if (partial / "publication.json").exists() or (partial / "computed.json").is_symlink():
            raise ValueError("Incomplete control run has a completion receipt or linked result")
        computed = (partial / "computed.json").read_bytes()
        if sha(computed) != next(x["sha256"] for x in failure["retained_partial_outputs"] if x["name"] == "computed.json"):
            raise ValueError("Retained partial result hash mismatch")
    def product_digest(run_name, names, excluded=()):
        root, outputs = load_run(run_name, names)
        digest = hashlib.sha256()
        for name in sorted(set(outputs) - set(excluded)):
            digest.update(name.encode() + b"\0" + outputs[name])
        return digest.hexdigest()
    first_group = hashlib.sha256((product_digest(args.corrected_one, corrected, ("failed-publication-control.json",)) +
                                  product_digest(args.legacy_one, legacy)).encode()).hexdigest()
    second_group = hashlib.sha256((product_digest(args.corrected_two, corrected, ("failed-publication-control.json",)) +
                                   product_digest(args.legacy_two, legacy)).encode()).hexdigest()
    reproducibility = {"method_id": "cameroon-safe-evidence-reproduction", "kind": "reproducibility",
                       "outcome": "passed", "run_one_sha256": first_group, "run_two_sha256": second_group,
                       "fresh_run_names": [args.corrected_one, args.corrected_two, args.legacy_one, args.legacy_two],
                       "product_pairs_equal": first_group == second_group,
                       "failed_partial_outputs_remain_unreceipted": True}
    if first_group != second_group:
        raise ValueError("Corrected or legacy entry point pairs are not reproducible")
    positive = {"method_id": "cameroon-safe-evidence-reproduction", "kind": "positive-control", "outcome": "passed",
                "publication_receipts_reconciled": True,
                "corrected_and_legacy_products_reconciled": True,
                "original_numeric_values": numeric_values, "score_values": 678,
                "issue_subjects": 226, "exact_candidate_parent_joins": 226,
                "duplicate_crosswalk_rows": len(fixture["crosswalk"]),
                "duplicate_unique_subjects": len({row["subject_id"] for row in fixture["crosswalk"]}),
                "missing_issue_subjects": len(missing), "aggregate_count": 14,
                "ocha_adm1_regions": corrected_data["ocha_neighboring_tiers"]["adm1_regions"],
                "ocha_adm2_departments": corrected_data["ocha_neighboring_tiers"]["adm2_departments"],
                "ocha_adm3_arrondissements": corrected_data["ocha_neighboring_tiers"]["adm3_arrondissements"]}
    negative = {"method_id": "cameroon-safe-evidence-reproduction", "kind": "negative-control", "outcome": "passed",
                "malformed_crosswalks_rejected": True, "changed_inputs_and_code_rejected": True,
                "sentinels_symlinks_and_traversal_rejected": all(admission.values()),
                "post_computation_failure_unreceipted": True,
                "protected_legacy_sources_unchanged": True}
    result["verification_vintage"] = args.pair_vintage
    pair_report = {"method_id": "cameroon-safe-evidence-reproduction",
                   "kind": "verification-summary", "outcome": "passed", **result}
    pair_writer.publish({"reproduction-positive-control.json": positive,
                         "reproduction-negative-control.json": negative,
                         "reproducibility.json": reproducibility,
                         "pair-verification.json": pair_report})
    print(json.dumps(pair_report, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
