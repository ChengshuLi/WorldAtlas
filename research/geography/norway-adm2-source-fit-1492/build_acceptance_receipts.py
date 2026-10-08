#!/usr/bin/env python3
"""Bind computed metric values and geometry controls to exact output bytes."""
import hashlib
import json
import resource
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OWNED = "research/geography/norway-adm2-source-fit-1492/"
COMMIT = "088ab05aeb16ddfa8f0c43e596533f3f11d5fcec"
BASELINE_SHA = "45d4356a46beddea43bfbd20231e0bf3671aa349643de29d0fa088ed5fbf5713"
VINTAGE = "acceptance-receipts-20261008"
METHOD = "norway-exact-component-source-overlay"
OVERLAY = OWNED + "vintages/exact-overlay-acceptance-20261008/overlay-v1.json"
COMPONENTS = OWNED + "vintages/component-geometries-20261008/selected-components.json"
OUTPUTS = ["metric-values.json", "positive-control.json", "negative-control.json"]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def checked_capture(path):
    raw = (ROOT / path).read_bytes()
    receipt_path = Path(path).parent / "publication.json"
    receipt = json.loads((ROOT / receipt_path).read_bytes())
    desc = next((row for row in receipt["outputs"] if row["path"] == path), None)
    if not desc or desc["bytes"] != len(raw) or desc["sha256"] != sha(raw):
        raise SystemExit(f"Retained input does not match its completion receipt: {path}")
    return raw


def main():
    started = time.monotonic()
    producer_sha = sha(Path(__file__).read_bytes())
    admission_raw = (ROOT / OWNED / "vintages/baseline-20261008/baseline-admission.json").read_bytes()
    if sha(admission_raw) != BASELINE_SHA:
        raise SystemExit("Pinned baseline admission changed")
    admission = json.loads(admission_raw)
    sys.path.insert(0, str(ROOT / "scripts"))
    from evidence.immutable import Baseline, NewVintage, canonical_json

    baseline = Baseline(ROOT, COMMIT, admission["baseline_files"])
    writer = NewVintage(baseline, OWNED, VINTAGE, OUTPUTS)
    for name, size in [("producer-runtime-and-inputs", 2 * 1024 * 1024),
                       ("metric-values.json", 128 * 1024),
                       ("positive-control.json", 128 * 1024),
                       ("negative-control.json", 256 * 1024),
                       ("publication.json", 4096)]:
        baseline.admit("reserved:" + name, size)
    baseline.admit("producer-script-bytes", len(Path(__file__).read_bytes()))
    overlay_raw = checked_capture(OVERLAY)
    components_raw = checked_capture(COMPONENTS)
    baseline.admit("captured-overlay-bytes", len(overlay_raw))
    baseline.admit("captured-selected-components-bytes", len(components_raw))
    overlay = json.loads(overlay_raw)
    components = json.loads(components_raw)
    if len(overlay["components"]) != 15 or overlay["scope"]["complete_family_member_count"] != 400 or overlay["scope"]["complete_positive_length_neighbor_count"] != 36:
        raise SystemExit("Overlay scope changed")
    if len(overlay["adverse_controls"]) != 15:
        raise SystemExit("Adverse-control roster changed")
    inventory = components["component_delivery_inventory"]
    rows = overlay["components"]
    metrics = {
        "selected-components": overlay["scope"]["selected_component_count"],
        "complete-family-members": overlay["scope"]["complete_family_member_count"],
        "positive-length-neighbors": overlay["scope"]["complete_positive_length_neighbor_count"],
        "exact-source-subject-coverage": sum(x["exact_subject_covers_component"] for x in rows),
        "exact-parent-coverage": sum(x["exact_recorded_parent_covers_component"] for x in rows),
        "strict-no-loss-pass": sum(x["strict_no_loss_under_T_union_C"] for x in rows),
        "strict-no-loss-fail": sum(not x["strict_no_loss_under_T_union_C"] for x in rows),
        "candidate-adds-area-to-current-target": sum(x["candidate_adds_area_beyond_current_atlas_target"] for x in rows),
        "historical-current-contact-equality": sum(x["recorded_vs_recomputed_contact_ids_equal"] for x in overlay["adverse_controls"]),
        "historical-current-contact-differences": sum(not x["recorded_vs_recomputed_contact_ids_equal"] for x in overlay["adverse_controls"]),
        "historical-bbox-candidate-rows": overlay["contact_reconciliation"]["historical_bbox_candidate_rows"],
        "historical-empty-bbox-rows": overlay["contact_reconciliation"]["historical_empty_bbox_rows_not_contacts"],
        "historical-nonempty-contact-rows": overlay["contact_reconciliation"]["historical_nonempty_contact_rows"],
        "recomputed-nonempty-source-intersections": len(overlay["all_nonempty_intersections_and_contacts"]),
        "recomputed-zero-area-contacts": sum(len(x["zero_area_contacts"]) for x in rows),
        "measured-acceptance-gate-passes": sum(x["measured_acceptance_gate_passes"] for x in overlay["adverse_controls"]),
        "adverse-control-sets-rejected": sum(x["all_adverse_controls_rejected"] for x in overlay["adverse_controls"]),
        "original-delivery-unique-IDs": inventory["unique_component_ids"],
        "delivery-config-declared-IDs": inventory["declared_current_components"],
        "delivery-unique-count-excess": inventory["declared_vs_captured_unique_difference"],
        "deterministic-overlay-runs": overlay["runs"]["run_count"],
    }
    if len(metrics) != 21:
        raise SystemExit("Unexpected metric inventory")
    positive_ok = all(x["positive_control_acceptance"] for x in overlay["adverse_controls"])
    negative_ok = all(x["all_adverse_controls_rejected"] for x in overlay["adverse_controls"])
    if not positive_ok or not negative_ok:
        raise SystemExit("A positive/negative control did not pass")
    common = {"version": 1, "method_id": METHOD, "outcome": "passed",
              "input_overlay_sha256": sha(overlay_raw), "component_count": len(rows)}
    metric_product = {**common, "kind": "metric-values", "values": metrics,
                      "producer": {"path": str(Path(__file__).relative_to(ROOT)), "sha256": producer_sha,
                                   "python": sys.version, "elapsed_seconds": time.monotonic() - started},
                      "limits": ["Values summarize the exact 088ab task baseline run; they do not prove external geographic truth."]}
    positive = {**common, "kind": "positive-control", "positive_fixtures_accepted": True,
                "affirmative_fixture_count": len(rows),
                "control_results": [{"component_id": x["component_id"],
                                     "outcome": "passed" if x["positive_control_acceptance"] else "failed"}
                                    for x in overlay["adverse_controls"]]}
    negative = {**common, "kind": "negative-control", "all_adverse_controls_rejected": True,
                "component_control_sets": len(rows),
                "control_results": [{"component_id": x["component_id"],
                                     "outcome": "passed" if x["all_adverse_controls_rejected"] else "failed",
                                     "rejected": {key: x[key] for key in
                                      ("wrong_source_id_rejected", "wrong_source_edition_rejected", "wrong_target_id_rejected",
                                       "wrong_parent_rejected", "missing_family_member_rejected", "missing_neighbor_rejected",
                                       "missing_contact_rejected", "altered_source_bytes_rejected", "forced_target_loss_rejected",
                                       "forced_new_positive_overlap_rejected")}}
                                    for x in overlay["adverse_controls"]]}
    before_disk = shutil.disk_usage(ROOT).free
    before_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    records = writer.publish({"metric-values.json": metric_product,
                              "positive-control.json": positive,
                              "negative-control.json": negative})
    print(json.dumps({"status": "complete", "outputs": records,
                      "phase_bytes": sum(baseline.consumed.values()),
                      "phase_limit_bytes": baseline.max_phase_bytes,
                      "disk_free_before_publish_bytes": before_disk,
                      "disk_free_after_publish_bytes": shutil.disk_usage(ROOT).free,
                      "process_max_rss_before_publish": before_rss,
                      "elapsed_seconds": time.monotonic() - started}, indent=2))


if __name__ == "__main__":
    main()
