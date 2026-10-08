#!/usr/bin/env python3
"""Directed controls for the exact source-fitness producer."""
from __future__ import annotations
import argparse
import json
import pathlib
import re

import producer

OWNED = producer.OWNED
POSITIVE = (
    "physical-component:04431dc98d19b4236a143d2c0bb388fed2e41d4768356cf5a74ae4b9194fd9bf",
    "gb:KGZ:ADM2:92254566B28866404519709",
)
MAX_OUTPUT_FILE_BYTES = 32 * 1024 * 1024


def read_run_outputs(repo, run_dir, baseline):
    repo = pathlib.Path(repo).resolve()
    supplied_run_dir = pathlib.Path(run_dir)
    if not supplied_run_dir.is_absolute():
        supplied_run_dir = repo / supplied_run_dir
    for path in (supplied_run_dir, *supplied_run_dir.parents):
        if path == repo.parent:
            break
        if path.is_symlink():
            raise ValueError("Symlink in source-run output path")
    run_dir = supplied_run_dir.resolve()
    owned_root = (repo / OWNED / "vintages").resolve()
    if not run_dir.is_relative_to(owned_root) or run_dir == owned_root:
        raise ValueError("Run outputs must be inside the owned evidence vintages")
    receipt_path = run_dir / "publication.json"
    if receipt_path.is_symlink() or not receipt_path.is_file():
        raise ValueError("Source-run publication receipt is missing or symlinked")
    receipt_bytes = receipt_path.read_bytes()
    if len(receipt_bytes) > 4096:
        raise ValueError("Source-run publication receipt exceeds its byte bound")
    receipt = json.loads(receipt_bytes)
    if receipt.get("version") != 1 or receipt.get("status") != "complete":
        raise ValueError("Source run has no complete publication receipt")
    outputs = receipt.get("outputs")
    if not isinstance(outputs, list) or not outputs:
        raise ValueError("Source-run publication receipt has no outputs")
    result = {}
    for record in outputs:
        path = record.get("path")
        if not isinstance(path, str) or not path.startswith(run_dir.relative_to(repo).as_posix() + "/"):
            raise ValueError("Source-run output escaped its admitted vintage")
        target = repo / path
        if target.is_symlink() or not target.is_file():
            raise ValueError("Source-run output is missing or symlinked")
        raw = target.read_bytes()
        if (len(raw) > MAX_OUTPUT_FILE_BYTES or len(raw) != record.get("bytes") or
                producer.sha(raw) != record.get("sha256")):
            raise ValueError("Source-run output differs from its publication receipt")
        baseline.admit("published-run:" + path, len(raw))
        result[target.name] = raw
    if len(result) != len(outputs) or set(result) != {
        "source-fitness.json", "run-summary.json"
    }:
        raise ValueError("Source run does not contain the exact complete output set")
    if {path.name for path in run_dir.iterdir()} != set(result) | {"publication.json"}:
        raise ValueError("Source run contains missing or unlisted files")
    return result


def read_supervision_receipt(repo, source_run, run_summary_raw, baseline_commit):
    run_name = pathlib.Path(source_run).name
    root = pathlib.Path(repo) / OWNED / "vintages" / "process-supervision" / run_name
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Externally supervised process receipt is missing")
    for child in root.iterdir():
        if child.is_symlink() or not child.is_file():
            raise ValueError("Unsafe entry in process-supervision receipt")
    publication_path = root / "publication.json"
    if not publication_path.is_file() or publication_path.stat().st_size > 4096:
        raise ValueError("Process-supervision publication receipt is missing or oversized")
    publication = json.loads(publication_path.read_bytes())
    records = publication.get("outputs")
    expected = {"supervision.json", "stdout.txt", "stderr.txt", "rss-samples.jsonl"}
    if publication.get("status") != "complete" or not isinstance(records, list):
        raise ValueError("Process-supervision publication is incomplete")
    by_path = {item.get("path"): item for item in records if isinstance(item, dict)}
    if len(by_path) != 4 or set(by_path) != expected or len(records) != 4:
        raise ValueError("Process-supervision publication has a non-exact output set")
    if {path.name for path in root.iterdir()} != expected | {"publication.json"}:
        raise ValueError("Process-supervision folder has unlisted or missing files")
    bodies = {}
    for name, item in by_path.items():
        path = root / name
        raw = path.read_bytes()
        limit = (4 * 1024 * 1024 if name == "rss-samples.jsonl" else
                 1 * 1024 * 1024 if name in ("stdout.txt", "stderr.txt") else 32768)
        if len(raw) != item.get("bytes") or len(raw) > limit or producer.sha(raw) != item.get("sha256"):
            raise ValueError("Process-supervision output differs from its publication descriptor")
        baseline.admit("process-supervision:" + name, len(raw))
        bodies[name] = raw
    receipt = json.loads(bodies["supervision.json"])
    samples = [json.loads(line) for line in bodies["rss-samples.jsonl"].splitlines() if line]
    sampled_peak = max((x.get("process_tree_rss_bytes", -1) for x in samples), default=-1)
    run_summary = json.loads(run_summary_raw)
    admission = run_summary.get("precalculation_admission", {})
    memory = admission.get("fixed_memory_snapshot", {})
    page_counts = memory.get("page_counts", {})
    candidate_memory = memory.get("free_inactive_speculative_candidate_bytes")
    required_memory = producer.MAX_RSS_BYTES + producer.HOST_MEMORY_RESERVE_BYTES
    fixed_memory_valid = (
        isinstance(candidate_memory, int) and candidate_memory >= required_memory and
        candidate_memory <= memory.get("physical_memory_bytes", -1) and
        memory.get("candidate_is_guaranteed_available_memory") is False and
        memory.get("candidate_includes_reclaimable_pages") is True and
        memory.get("page_size_bytes", 0) > 0 and
        candidate_memory == sum(page_counts.values()) * memory.get("page_size_bytes", 0) and
        memory.get("free_page_bytes") == page_counts.get("Pages free", -1) * memory.get("page_size_bytes", 0)
    )
    source_run_dir = pathlib.Path(source_run)
    if not source_run_dir.is_absolute():
        source_run_dir = pathlib.Path(repo) / source_run_dir
    source_run_publication = source_run_dir.resolve() / "publication.json"
    if source_run_publication.is_symlink() or not source_run_publication.is_file():
        raise ValueError("Supervised source-run publication is missing")
    if (receipt.get("version") != 1 or receipt.get("status") != "pass" or
            receipt.get("baseline_commit") != baseline_commit or
            receipt.get("vintage") != run_name or
            receipt.get("source_run_summary_sha256") != producer.sha(run_summary_raw) or
            receipt.get("source_run_publication_sha256") != producer.sha(source_run_publication.read_bytes()) or
            receipt.get("producer_ru_maxrss_bytes") != run_summary.get("max_rss_bytes") or
            not isinstance(receipt.get("producer_ru_maxrss_bytes"), int) or
            receipt.get("producer_ru_maxrss_bytes") > producer.MAX_RSS_BYTES or
            receipt.get("producer_rss_limit_bytes") != producer.MAX_RSS_BYTES or
            receipt.get("external_stop_bytes") != producer.EXTERNAL_RSS_STOP_BYTES or
            receipt.get("external_margin_below_768mib_bytes") != producer.EXTERNAL_RSS_MARGIN_BYTES or
            receipt.get("maximum_sampled_process_tree_rss_bytes") != sampled_peak or
            receipt.get("external_rss_measurement") != "Sum of ps RSS bytes for producer and all observed descendants/process-group members; shared pages may be counted more than once." or
            receipt.get("sample_count") != len(samples) or
            receipt.get("samples_are_polling_not_a_kernel_hard_limit") is not True or
            receipt.get("elapsed_seconds", producer.MAX_SECONDS + 1) > producer.MAX_SECONDS or
            run_summary.get("status") != "complete" or
            run_summary.get("elapsed_seconds", producer.MAX_SECONDS + 1) > producer.MAX_SECONDS or
            not fixed_memory_valid or
            sampled_peak >= producer.EXTERNAL_RSS_STOP_BYTES or
            receipt.get("coordinated_window_id") != admission.get("coordinated_window_id")):
        raise ValueError("External process lifetime RSS evidence does not qualify the exact source run")
    if not samples or any(not isinstance(x.get("process_tree_rss_bytes"), int) or
                          x["process_tree_rss_bytes"] < 0 for x in samples):
        raise ValueError("Process-supervision RSS samples are absent or malformed")
    return {"receipt": receipt, "publication_sha256": producer.sha(publication_path.read_bytes()),
            "samples_sha256": producer.sha(bodies["rss-samples.jsonl"]),
            "sampled_process_tree_peak_bytes": sampled_peak}


def run_controls(repo, baseline_commit, source_run, control_vintage):
    repo = pathlib.Path(repo).resolve()
    baseline, evidence, contract_helpers, config = producer.bootstrap(
        repo, baseline_commit, phase="overlay")
    if "controls" not in config["code_files"]:
        raise ValueError("Controls entry point is not in the pinned execution inventory")
    baseline.materialized_bytes(config["code_files"]["controls"])
    run = evidence.NewVintage(
        baseline, OWNED, control_vintage, ["control-receipt.json"]
    )

    outputs = read_run_outputs(repo, source_run, baseline)
    fitness_raw = outputs["source-fitness.json"]
    supervision = read_supervision_receipt(repo, source_run, outputs["run-summary.json"],
                                           baseline_commit)
    fitness = json.loads(fitness_raw)
    component_ids = config["component_ids"]
    if fitness.get("scope", {}).get("component_ids") != component_ids:
        raise ValueError("Positive-control source run has different component scope")
    if len(fitness.get("component_source_fit_rows", [])) != len(component_ids) * 99:
        raise ValueError("Positive-control source run has an incomplete comparison ledger")

    positive_rows = [
        row for row in fitness["component_source_fit_rows"]
        if row.get("component_id") == POSITIVE[0] and row.get("source_feature_id") == POSITIVE[1]
    ]
    if (len(positive_rows) != 1 or positive_rows[0].get("intersects") is not True or
            positive_rows[0].get("positive_area_intersection") is not True or
            positive_rows[0].get("source_feature_covers_component") is True):
        raise ValueError("Positive control did not retain the expected exact source-product relation")

    (input_pins, context, pointsets_by_id, products, _, catalogue, metadata,
     attribution, jrc_summary) = producer.load_inputs(baseline, contract_helpers, config)
    if fitness.get("jrc_support") != jrc_summary:
        raise ValueError("Positive control did not reproduce the pinned JRC support/cohort summary")
    missing_jrc_output_rejected = "jrc_support" not in {
        key: value for key, value in fitness.items() if key != "jrc_support"
    }
    altered_jrc = json.loads(json.dumps(fitness["jrc_support"]))
    altered_jrc["exact_intersections_sha256"] = "0" * 64
    altered_jrc_rejected = altered_jrc != jrc_summary
    if not missing_jrc_output_rejected or not altered_jrc_rejected:
        raise ValueError("JRC support summary negative controls failed")
    actual_product_context = producer.output_product_context(
        baseline, products, catalogue, metadata, attribution, input_pins
    )
    if actual_product_context != fitness.get("source_products"):
        raise ValueError("Positive control did not reproduce the retained source-product context")

    source_product_indices = [
        index for index, item in enumerate(input_pins["files"])
        if item.get("kind") == "whole-simplified-source-product"
    ]
    if len(source_product_indices) != 2:
        raise ValueError("Pinned whole-file inventory does not contain the two expected source products")

    def source_context_rejects(candidate, label):
        try:
            producer.output_product_context(
                baseline, products, catalogue, metadata, attribution, candidate
            )
        except ValueError:
            return True
        raise ValueError(f"Source-product context accepted {label}")

    wrong_prefix = json.loads(json.dumps(input_pins))
    wrong_prefix["files"][source_product_indices[0]]["path"] = (
        "foreign-prefix/" + wrong_prefix["files"][source_product_indices[0]]["path"]
    )
    wrong_prefix_rejected = source_context_rejects(wrong_prefix, "a wrong-prefix descriptor")

    foreign_origin = json.loads(json.dumps(input_pins))
    foreign_origin["files"][source_product_indices[0]]["source_commit"] = "0" * 40
    foreign_origin_rejected = source_context_rejects(foreign_origin, "a foreign source origin")

    missing_product = json.loads(json.dumps(input_pins))
    del missing_product["files"][source_product_indices[0]]
    missing_product_rejected = source_context_rejects(missing_product, "a missing source product")

    reordered_products = json.loads(json.dumps(input_pins))
    left, right = source_product_indices
    reordered_products["files"][left], reordered_products["files"][right] = (
        reordered_products["files"][right], reordered_products["files"][left]
    )
    reordered_products_rejected = source_context_rejects(
        reordered_products, "reordered source-product descriptors"
    )

    try:
        contract_helpers.exact_rows(
            [dict(feature, id=identity) for identity, feature in pointsets_by_id.items()
             if identity != component_ids[-1]],
            component_ids,
        )
    except ValueError:
        missing_subject_rejected = True
    else:
        raise ValueError("Negative control accepted a missing actual component record")

    altered_routes = json.loads(json.dumps(context["routes"]))
    original = altered_routes[component_ids[0]]["current_geometry_sha256"]
    altered_routes[component_ids[0]]["current_geometry_sha256"] = "0" * 64 if original != "0" * 64 else "1" * 64
    try:
        producer.validate_pointset_route_hashes(pointsets_by_id, altered_routes, contract_helpers)
    except ValueError:
        changed_source_field_rejected = True
    else:
        raise ValueError("Negative control accepted a changed routed geometry hash")

    receipt = {
        "version": 1,
        "status": "pass",
        "source_run": {
            "path": str(pathlib.Path(source_run).resolve().relative_to(repo)),
            "source_fitness_sha256": producer.sha(fitness_raw),
        },
        "external_process_supervision": {
            "path": (OWNED + "vintages/process-supervision/" + pathlib.Path(source_run).name),
            "publication_sha256": supervision["publication_sha256"],
            "rss_samples_sha256": supervision["samples_sha256"],
            "maximum_sampled_process_tree_rss_bytes": supervision["sampled_process_tree_peak_bytes"],
            "producer_ru_maxrss_bytes": supervision["receipt"]["producer_ru_maxrss_bytes"],
            "external_stop_bytes": producer.EXTERNAL_RSS_STOP_BYTES,
            "margin_below_768mib_bytes": producer.EXTERNAL_RSS_MARGIN_BYTES,
        },
        "scope_component_count": len(component_ids),
        "jrc_support_positive_control": {
            "validated": True,
            "exact_intersections_sha256": jrc_summary["exact_intersections_sha256"],
            "bounded_cohorts_sha256": jrc_summary["bounded_cohorts_sha256"],
            "cohort_count": jrc_summary["cohorts"],
            "raster_pixel_values_read": jrc_summary["raster_pixel_values_read"],
            "cross_tile_component_id": jrc_summary["positive_cross_tile_support"]["component_id"],
            "cross_tile_block_indices_by_tile": jrc_summary["positive_cross_tile_support"]["block_indices_by_tile"],
        },
        "positive_control": {
            "component_id": POSITIVE[0], "source_feature_id": POSITIVE[1],
            "intersects": positive_rows[0]["intersects"],
            "positive_area_intersection": positive_rows[0]["positive_area_intersection"],
            "source_feature_covers_component": positive_rows[0]["source_feature_covers_component"],
        },
        "source_product_context_controls": {
            "positive_real_context_sha256": producer.sha(producer.canonical(actual_product_context)),
            "wrong_prefix_rejected": wrong_prefix_rejected,
            "foreign_origin_rejected": foreign_origin_rejected,
            "missing_product_rejected": missing_product_rejected,
            "reordered_products_rejected": reordered_products_rejected,
        },
        "negative_controls": {
            "missing_actual_component_record_rejected": missing_subject_rejected,
            "altered_routed_geometry_hash_rejected": changed_source_field_rejected,
            "missing_jrc_support_summary_rejected": missing_jrc_output_rejected,
            "altered_jrc_support_hash_rejected": altered_jrc_rejected,
        },
        "limits": [
            "The positive control verifies a retained source-product relation only; it does not establish land, water, authority, lineage, or historical ownership.",
            "The negative controls exercise exact-scope and source-join rejection paths; they do not authenticate scientific truth.",
        ],
    }
    if len(producer.canonical(receipt)) > producer.MAX_CONTROL_OUTPUT_BYTES:
        raise ValueError("Directed-control receipt exceeds its admitted output budget")
    publication = run.publish({"control-receipt.json": receipt})
    print(json.dumps({"status": "pass", "vintage": control_vintage,
                      "publication": publication}, sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--baseline-commit", required=True)
    parser.add_argument("--source-run", required=True)
    parser.add_argument("--control-vintage", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-f0-9]{40}", args.baseline_commit):
        raise ValueError("An exact immutable baseline commit is required")
    run_controls(args.repo, args.baseline_commit, args.source_run, args.control_vintage)


if __name__ == "__main__":
    main()
