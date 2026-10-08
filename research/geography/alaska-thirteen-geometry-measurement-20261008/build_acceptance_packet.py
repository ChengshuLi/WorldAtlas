#!/usr/bin/env python3
"""Bind the retained Alaska measurement runs to reviewable case and control receipts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "vintages" / "acceptance-receipts-20261008"
METHOD_ID = "alaska-thirteen-full-simplified-atlas-native-measurement-v1"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def output_map(name: str):
    run = ROOT / "vintages" / name
    publication = load(run / "publication.json")
    if publication.get("status") != "complete":
        raise SystemExit(f"{name}: publication is not complete")
    rows = {}
    for row in publication.get("outputs", []):
        path = Path(row["path"])
        raw = path.read_bytes()
        if len(raw) != row["bytes"] or sha(raw) != row["sha256"]:
            raise SystemExit(f"{name}: publication byte mismatch for {path}")
        rows[path.name] = {"bytes": len(raw), "sha256": sha(raw)}
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    run_names = ("run-thirteen", "run-fourteen")
    outputs = {name: output_map(name) for name in run_names}
    if outputs[run_names[0]] != outputs[run_names[1]]:
        raise SystemExit("producer vintages differ")

    measurements = [load(ROOT / "vintages" / name / "measurement.json") for name in run_names]
    if measurements[0] != measurements[1]:
        raise SystemExit("measurement JSON differs across runs")
    measurement = measurements[0]
    if measurement.get("method_id") != METHOD_ID or measurement.get("status") != "measured":
        raise SystemExit("unexpected measurement identity or status")

    cases = measurement["cases"]
    expected_ids = set(measurement["assigned_scope"]["component_ids"])
    if len(cases) != 13 or {row["component_id"] for row in cases} != expected_ids:
        raise SystemExit("case set differs from the exact assigned 13")
    if measurement["physical_relation_preservation"]["relation_count"] != 25:
        raise SystemExit("the 25 original physical relations are not all retained")
    if measurement["assigned_scope"]["native_gshhg_record_count"] != 11:
        raise SystemExit("native record scope differs from the accepted 11")
    if measurement["counties"]["atlas_target_feature_count"] != 7:
        raise SystemExit("Atlas target scope differs from the accepted seven")

    diagnostic = load(ROOT / "execution" / "alaska-individual-case-gates-operating-receipt.json")
    if diagnostic.get("exit_code") != 0 or not diagnostic.get("natural_terminal"):
        raise SystemExit("single-case gate diagnostic did not complete naturally")
    detail = json.loads(diagnostic["stdout"])
    trials = detail.get("single_candidate_trials", [])
    if len(trials) != 13 or {row["component_id"] for row in trials} != expected_ids:
        raise SystemExit("single-case geometry gates do not cover the exact 13")
    by_id = {row["component_id"]: row for row in trials}
    truth_rows = []
    for case in cases:
        component_id = case["component_id"]
        trial = by_id[component_id]
        if trial["target_source_id"] != case["county_target"]["atlas_target_id"]:
            raise SystemExit(f"target join differs for {component_id}")
        truth_rows.append({
            "component_id": component_id,
            "target": case["county_target"],
            "candidate_geometry_sha256": case["candidate_geometry_sha256"],
            "candidate_vs_parent_and_both_county_variants_and_atlas": case["candidate_to_target_intersections_and_uncovered"],
            "full_vs_simplified_and_atlas_source_comparisons": case["source_to_target_variant_differences"],
            "candidate_variant_predicates_agree": case["source_variants_same_for_this_candidate"],
            "strict_single_union_gate": {
                "old_target_preserved_without_loss": trial["old_target_preserved_without_loss"],
                "old_target_loss_area_raw_square_degrees": trial["old_target_loss_area_raw_exact"],
                "gain_equals_candidate_minus_old_target": trial["gain_equals_candidate_minus_old_target"],
                "gain_symmetric_difference_area_raw_square_degrees": trial["gain_symmetric_difference_area_raw_exact"],
                "candidate_retained": trial["candidate_retained"],
                "relation_to_old_target": trial["old_target_relation_to_union"],
                "new_positive_area_neighbor_overlap_ids": trial["added_neighbor_overlaps"],
                "gate_passed": trial["single_case_strict_geometry_gate_pass"],
            },
            "source_parent_coverage": case["source_parent_coverage"],
            "native_land_relations": case["native_land_relations"],
            "native_linked_support_covers_candidate": case["native_linked_support_covers_candidate"],
            "original_physical_query_relations_match": case["original_25_relation_predicates_match"],
            "all_17_original_neighbor_contacts_match": case["original_contacts_match_all_17_actual_atlas_features"],
            "administrative_neighbor_checks": case["administrative_contacts_17_declared_neighbors"],
            "measured_actual_atlas_intersecting_neighbor_ids": case["measured_actual_atlas_intersecting_neighbor_ids"],
            "applicability_and_authority": {
                "source_predicate_support_pass": case["source_predicate_support_pass"],
                "original_physical_status": case["original_physical_status"],
                "original_physical_authority": case["original_physical_authority"],
                "remaining_limitations": case["remaining_limitations"],
                "disposition": case["disposition"],
            },
        })

    if any(row["strict_single_union_gate"]["gate_passed"] for row in truth_rows):
        raise SystemExit("unexpected qualifying single-case geometry proposal")
    if len(measurement["collective_union_checks"]["batch_trials"]) != 9 or any(
        row["collective_union_pass"] for row in measurement["collective_union_checks"]["batch_trials"]
    ):
        raise SystemExit("the nine bounded same-county batch trials do not match the no-qualification result")

    truth = {
        "version": 1,
        "method_id": METHOD_ID,
        "status": "measured-no-qualifying-correction",
        "scope": measurement["assigned_scope"],
        "method": measurement["method"],
        "county_sources": measurement["counties"],
        "case_count": len(truth_rows),
        "cases": truth_rows,
        "physical_relation_preservation": measurement["physical_relation_preservation"],
        "collective_union_trials": measurement["collective_union_checks"]["batch_trials"],
        "source_contact_lineage": measurement["source_contact_lineage"],
        "source_limits": measurement["source_limits"],
        "proposal": measurement["proposal"],
        "controls": measurement["controls"],
        "run_measurement_sha256": outputs[run_names[0]]["measurement.json"]["sha256"],
        "single_case_diagnostic_stdout_sha256": sha(diagnostic["stdout"].encode("utf-8")),
    }
    write_json(OUT / "truth-table.json", truth)

    controls = measurement["controls"]
    if not controls or not all(row.get("passed") is True for row in controls):
        raise SystemExit("measurement positive/negative controls failed")
    positive = [row for row in controls if row["kind"].startswith("positive-")]
    negative = [row for row in controls if row["kind"].startswith("negative-")]
    if not positive or not negative:
        raise SystemExit("missing nonvacuous positive or negative controls")
    write_json(OUT / "positive-control.json", {
        "version": 1, "method_id": METHOD_ID, "kind": "positive-control", "outcome": "passed",
        "measurement_sha256": outputs[run_names[0]]["measurement.json"]["sha256"],
        "positive_controls": positive,
    })
    write_json(OUT / "negative-control.json", {
        "version": 1, "method_id": METHOD_ID, "kind": "negative-control", "outcome": "passed",
        "measurement_sha256": outputs[run_names[0]]["measurement.json"]["sha256"],
        "negative_controls": negative,
    })

    total_bytes = sum(row["bytes"] for row in outputs[run_names[0]].values())
    reproducibility = {
        "version": 1, "method_id": METHOD_ID, "kind": "reproducibility", "outcome": "passed",
        "run_one_sha256": outputs[run_names[0]]["measurement.json"]["sha256"],
        "run_two_sha256": outputs[run_names[1]]["measurement.json"]["sha256"],
        "runs": [
            {
                "name": name,
                "publication": f"{name}/publication.json",
                "outputs": outputs[name],
                "operating_receipt": {
                    "path": f"execution/measure-alaska-{name}-operating-receipt.json",
                    "exit_code": load(ROOT / "execution" / f"measure-alaska-{name}-operating-receipt.json")["exit_code"],
                    "natural_terminal": load(ROOT / "execution" / f"measure-alaska-{name}-operating-receipt.json")["natural_terminal"],
                    "elapsed_seconds": load(ROOT / "execution" / f"measure-alaska-{name}-operating-receipt.json")["elapsed_seconds"],
                    "peak_sampled_group_rss_bytes": load(ROOT / "execution" / f"measure-alaska-{name}-operating-receipt.json")["peak_sampled_group_rss_bytes"],
                    "rss_cap_bytes": load(ROOT / "execution" / f"measure-alaska-{name}-operating-receipt.json")["rss_cap_bytes"],
                    "wall_deadline_seconds": load(ROOT / "execution" / f"measure-alaska-{name}-operating-receipt.json")["wall_deadline_seconds"],
                },
            }
            for name in run_names
        ],
        "fresh_destinations": True,
        "output_bytes_per_run": total_bytes,
        "all_published_output_hashes_equal": True,
        "all_measurement_records_equal": True,
    }
    write_json(OUT / "reproducibility.json", reproducibility)

    native_receipt = load(ROOT / "sources" / "native-selected" / "receipt.json")
    native_points = sum(row["header_int32"][1] for row in native_receipt["selected_output"]["records"])
    native_coordinate_bytes = native_points * 8
    values = {
        "component_count": measurement["assigned_scope"]["component_count"],
        "family_member_count": measurement["assigned_scope"]["family_member_count"],
        "atlas_target_count": measurement["counties"]["atlas_target_feature_count"],
        "simplified_target_count": measurement["counties"]["simplified_target_feature_count"],
        "full_source_feature_count": measurement["counties"]["full_source_feature_count"],
        "physical_relation_count": measurement["physical_relation_preservation"]["relation_count"],
        "native_gshhg_record_count": measurement["assigned_scope"]["native_gshhg_record_count"],
        "native_point_count": native_points,
        "native_coordinate_bytes": native_coordinate_bytes,
        "native_source_pair_count": measurement["native_source_pair_count"],
        "neighbor_feature_count": measurement["administrative_neighbor_context"]["declared_neighbor_count"],
        "candidate_pair_count": measurement["candidate_pair_count"],
        "collective_union_trial_count": len(measurement["collective_union_checks"]["batch_trials"]),
        "single_case_gate_count": len(truth_rows),
        "variant_candidate_agreement_count": sum(row["candidate_variant_predicates_agree"] for row in truth_rows),
        "source_parent_support_count": sum(row["applicability_and_authority"]["source_predicate_support_pass"] for row in truth_rows),
        "native_linked_support_count": sum(row["native_linked_support_covers_candidate"] for row in truth_rows),
        "original_physical_relation_match_count": sum(row["original_physical_query_relations_match"] for row in truth_rows),
        "original_neighbor_contact_match_count": sum(row["all_17_original_neighbor_contacts_match"] for row in truth_rows),
        "new_positive_area_neighbor_overlap_count": sum(
            len(row["new_positive_area_overlap_neighbor_ids"])
            for trial in measurement["collective_union_checks"]["batch_trials"]
            for row in trial["neighbor_checks"] if row["new_positive_area_overlap"]
        ),
        "qualifying_single_case_count": sum(row["strict_single_union_gate"]["gate_passed"] for row in truth_rows),
        "qualifying_batch_count": sum(row["collective_union_pass"] for row in measurement["collective_union_checks"]["batch_trials"]),
        "proposal_feature_count": measurement["proposal"]["feature_count"],
        "positive_control_count": len(positive),
        "negative_control_count": len(negative),
        "reproducible_run_count": 2,
        "output_bytes_per_run": total_bytes,
    }
    units = {
        "component_count": "components", "family_member_count": "members", "atlas_target_count": "features",
        "simplified_target_count": "features", "full_source_feature_count": "features",
        "physical_relation_count": "relations", "native_gshhg_record_count": "records",
        "native_point_count": "points", "native_coordinate_bytes": "bytes",
        "native_source_pair_count": "pairs", "neighbor_feature_count": "features", "candidate_pair_count": "pairs",
        "collective_union_trial_count": "trials", "single_case_gate_count": "cases",
        "variant_candidate_agreement_count": "cases", "source_parent_support_count": "cases",
        "native_linked_support_count": "cases", "original_physical_relation_match_count": "cases",
        "original_neighbor_contact_match_count": "cases", "new_positive_area_neighbor_overlap_count": "overlaps",
        "qualifying_single_case_count": "cases", "qualifying_batch_count": "batches",
        "proposal_feature_count": "features", "positive_control_count": "controls",
        "negative_control_count": "controls", "reproducible_run_count": "runs", "output_bytes_per_run": "bytes",
    }
    metric_values = {
        "version": 1,
        "measurement_sha256": outputs[run_names[0]]["measurement.json"]["sha256"],
        "truth_table_sha256": sha((OUT / "truth-table.json").read_bytes()),
        "values": {key: {"value": values[key], "unit": units[key]} for key in sorted(values)},
    }
    write_json(OUT / "metric-values.json", metric_values)

    description = [
        "# Alaska 13 component geometry measurement",
        "",
        "This packet measures exactly the 13 physical-component IDs assigned in issue #1508. It retains the complete 995-member family as read-only context, all seven Atlas targets, 25 original physical query relations, 11 original GSHHG records, 17 positive-length Atlas neighbors, and all 13 original detector contact geometries.",
        "",
        "## Result",
        "",
        "No individual or tested same-county batch satisfies the full exact geometry gate. The single-case strict no-loss table and all nine deterministic two/three-component batch results are in [truth-table.json](vintages/acceptance-receipts-20261008/truth-table.json); none creates a new positive-area overlap with an actual Atlas neighbor. The candidate proposal and gain GeoJSON files are valid empty FeatureCollections because no candidate qualified. Nothing in this packet approves a repair or changes Atlas production data.",
        "",
        "The seven selected simplified county geometries and the seven non-simplified geometries from geoBoundaries tag `9469f09` were compared directly. Candidate-specific predicates, projected/raw intersection areas, coverage, and uncovered areas agree across the two variants for all 13 candidates. The full and simplified county polygons are not themselves geometrically identical, and neither product resolves which exact boundary version is applicable to the recorded Atlas target. Real-world boundary authority and the intended vintage remain unresolved.",
        "",
        "The 11 GSHHG level-1 records preserve their original headers, offsets, parent/container fields, flags, hashes, and complete native coordinates. They contain 895,990 points (7,167,920 coordinate bytes). These are coarse source-relative land-support observations; per-feature observation date, precision, shoreline registration, and repair authority remain unknown. Original license wording conflicts are retained without a new legal conclusion.",
        "",
        "## Numeric ledger",
        "",
        "The following table is rendered from `metric-values.json`; each row is also bound to the same scalar in the evidence manifest.",
        "",
        "| Measure | Value | Unit |",
        "|---|---:|---|",
    ]
    rendered_rows = []
    for metric_id in sorted(values):
        unit = units[metric_id]
        value = values[metric_id]
        line = len(description) + 1
        description.append(f"| {metric_id} | {value} | {unit} |")
        rendered_rows.append({"metric_id": metric_id, "line": line, "template": f"| {metric_id} | {{value}} | {unit} |", "decimals": 0, "scale": 1})
    description.extend([
        "",
        "## Method and retention",
        "",
        "Inputs and execution code are byte-pinned in `evidence-quality.json`. The producer compares WGS84 longitude/latitude GeoJSON without pre-transforming coordinates; area is reported in raw square degrees as a coordinate-plane diagnostic and in EPSG:3338 Alaska Albers Equal Area square metres. Exact topological coverage and zero-area differences use no tolerance. Invalid source geometries are reported and never repaired, buffered, snapped, or silently discarded.",
        "",
        "Resource admission was completed before the bounded producer runs. `phase-admission.json` records the free-space/process scan and 6,680,375-byte admission headroom under the 256 MiB phase cap. Runs 13 and 14 exited naturally within the 900-second/768 MiB ceilings; their actual times, peak sampled RSS, complete output inventories, and hashes are in `execution/` and [reproducibility.json](vintages/acceptance-receipts-20261008/reproducibility.json). All four scientific output files are byte-identical across fresh run destinations.",
        "",
        "## Reproduction",
        "",
        "From the repository root, use the retained Python 3.12.14 runtime and invoke `measurement_driver.py run-thirteen` or `measurement_driver.py run-fourteen` with a fresh output destination. The exact completed commands and process receipts are retained in the packet. To rebuild the truth table, controls, reproducibility receipt, and numeric ledger without rerunning geometry, run `python3.12 -B research/geography/alaska-thirteen-geometry-measurement-20261008/build_acceptance_packet.py`.",
        "",
        "Research is complete for the bounded measurements. Implementation is not proposed and geographic approval is unapproved. This packet does not determine historical cause, political affiliation, ownership, rights, publication permission, current physical status, or real-world boundary accuracy.",
        "",
    ])
    (ROOT / "README.md").write_text("\n".join(description), encoding="utf-8")
    write_json(OUT / "rendered-table-bindings.json", {
        "version": 1,
        "path": "research/geography/alaska-thirteen-geometry-measurement-20261008/README.md",
        "rows": rendered_rows,
    })
    print(json.dumps({"status": "complete", "cases": len(truth_rows), "metrics": len(values),
                      "positive_controls": len(positive), "negative_controls": len(negative),
                      "output_bytes_per_run": total_bytes, "proposal_features": measurement["proposal"]["feature_count"]},
                     sort_keys=True))


if __name__ == "__main__":
    main()
