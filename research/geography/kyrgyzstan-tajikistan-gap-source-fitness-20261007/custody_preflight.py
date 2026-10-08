#!/usr/bin/env python3
"""Verify pinned whole-source custody, joins and runtime before any GIS."""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import pathlib
import resource
import sys
import time

import producer

OWNED = producer.OWNED
INPUT_PINS = producer.INPUT_PINS
CONTEXT = producer.CONTEXT
EXPECTED_ROUTE_PARTS = 25
EXPECTED_FAMILY_PARTS = 14
EXPECTED_BATCH_PARTS = 2
EXPECTED_PHYSICAL_PARTS = 13


def source_inventory(baseline):
    raw = baseline.pinned_bytes(INPUT_PINS)
    pins = json.loads(raw)
    staged = {OWNED + item["path"]: item for item in pins["files"]}
    if len(staged) != len(pins["files"]):
        raise ValueError("Input manifest contains duplicate paths")
    return pins, staged, raw


def scan_concatenated_jsonl(baseline, staged, paths, expected, id_field, helpers, label):
    found = {}
    all_ids = set()
    carry = b""
    row_count = 0

    def consume(line):
        nonlocal row_count
        if not line:
            return
        row = json.loads(line)
        identity = row.get(id_field)
        if not isinstance(identity, str) or not identity:
            raise ValueError(f"{label} stream contains a missing identity")
        if identity in all_ids:
            raise ValueError(f"{label} stream contains a duplicate identity: {identity}")
        all_ids.add(identity)
        row_count += 1
        if identity in expected:
            found[identity] = row

    for path in paths:
        decoded = producer.decode_pinned(baseline, staged, path)
        lines = (carry + decoded).split(b"\n")
        carry = lines.pop()
        for line in lines:
            consume(line)
    if carry:
        consume(carry)
    rows = [dict(row, id=identity) for identity, row in found.items()]
    helpers.exact_rows(rows, sorted(expected))
    for identity, row in found.items():
        if row != expected[identity]:
            raise ValueError(f"{label} source row differs from the selected context: {identity}")
    return found, row_count


def verify_source_origins(repo, baseline, evidence, pins):
    grouped = {}
    derived = []
    for item in pins["files"]:
        if item["kind"] in ("runtime-bundle", "runtime-manifest"):
            continue
        if item["kind"] in ("derived-scope-context", "exact-issue-scope-inventory"):
            derived.append(item["path"])
            continue
        origin = (item.get("source_commit"), item.get("source_path"))
        if not all(isinstance(x, str) and x for x in origin):
            raise ValueError(f"Source input lacks a whole-file origin: {item['path']}")
        grouped.setdefault(origin[0], []).append((item, origin[1]))

    receipts = []
    verified_source_bytes = 0
    for commit, members in sorted(grouped.items()):
        source_paths = [path for _, path in members]
        if len(source_paths) != len(set(source_paths)):
            raise ValueError(f"Origin source path is duplicated at {commit}")
        descriptors = [{"path": path, "bytes": item["bytes"],
                        "sha256": item["sha256"], "hash_kind": "file-bytes"}
                       for item, path in members]
        source_baseline = evidence.Baseline(repo, commit, descriptors)
        commit_bytes = 0
        for item, origin_path in members:
            source_raw = source_baseline.pinned_bytes(origin_path)
            staged_raw = baseline.pinned_bytes(OWNED + item["path"])
            if source_raw != staged_raw:
                raise ValueError(f"Captured bytes differ from immutable origin: {item['path']}")
            baseline.admit("origin-copy:" + commit + ":" + origin_path, len(source_raw))
            commit_bytes += len(source_raw)
        verified_source_bytes += commit_bytes
        receipts.append({"commit": commit, "file_count": len(members),
                         "raw_bytes": commit_bytes,
                         "paths_sha256": producer.sha(producer.canonical(sorted(source_paths)))})
    return {"status": "pass", "commit_groups": receipts,
            "source_file_count": sum(len(group) for group in grouped.values()),
            "verified_source_bytes": verified_source_bytes,
            "derived_input_paths": sorted(derived),
            "complete_phase_bytes_including_originals": sum(baseline.consumed.values())}


def verify_routing_phase(repo, commit, config):
    baseline, _, helpers, _ = producer.bootstrap(repo, commit, phase="routing")
    pins, staged, _ = source_inventory(baseline)
    context = json.loads(baseline.pinned_bytes(CONTEXT))
    ids = sorted(config["component_ids"])
    routes = context["routes"]
    helpers.exact_rows([dict(row, id=identity) for identity, row in routes.items()], ids)
    parts = sorted((x for x in pins["files"] if x["kind"] == "routing-whole-part"),
                   key=lambda x: x["path"])
    if len(parts) != EXPECTED_ROUTE_PARTS:
        raise ValueError("Require every complete actionability component-stream part")
    expected_paths_rel = [f"inputs/actionability-components/components-{i:03d}.bin.gz"
                          for i in range(EXPECTED_ROUTE_PARTS)]
    if [item["path"] for item in parts] != expected_paths_rel:
        raise ValueError("Actionability component-stream parts are incomplete or reordered")
    expected_paths = [OWNED + path for path in expected_paths_rel]
    found, row_count = scan_concatenated_jsonl(
        baseline, staged, expected_paths, routes, "component", helpers, "routing")
    if set(found) != set(ids):
        raise ValueError("Complete routing stream does not contain the exact 15 selected components")
    return {"status": "pass", "stream_rows": row_count, "selected_rows": len(found),
            "source_sha256": [item["sha256"] for item in parts],
            "phase_bytes": sum(baseline.consumed.values())}


def verify_family_batch_phase(repo, commit, config):
    baseline, _, helpers, _ = producer.bootstrap(repo, commit, phase="family-batches")
    pins, staged, _ = source_inventory(baseline)
    context = json.loads(baseline.pinned_bytes(CONTEXT))
    families = context["selected_families_source_rows"]
    family_parts = sorted((x for x in pins["files"]
                           if x["kind"] in ("family-whole-part", "selected-families-whole-part")),
                          key=lambda x: x["path"])
    batch_parts = sorted((x for x in pins["files"] if x["kind"] == "operational-batch-whole-part"),
                         key=lambda x: x["path"])
    if len(family_parts) != EXPECTED_FAMILY_PARTS or len(batch_parts) != EXPECTED_BATCH_PARTS:
        raise ValueError("Require every complete family and operational-batch part")
    family_paths_rel = [f"inputs/context/families-{i:03d}.bin.gz" for i in range(EXPECTED_FAMILY_PARTS)]
    batch_paths_rel = [f"inputs/context/batches-{i:03d}.bin.gz" for i in range(EXPECTED_BATCH_PARTS)]
    if [x["path"] for x in family_parts] != family_paths_rel or [x["path"] for x in batch_parts] != batch_paths_rel:
        raise ValueError("Family or operational-batch source parts are incomplete")
    family_paths = [OWNED + path for path in family_paths_rel]
    batch_paths = [OWNED + path for path in batch_paths_rel]
    found_families, family_count = scan_concatenated_jsonl(
        baseline, staged, family_paths, families, "id", helpers, "family")
    batch = context["operational_batch"]
    found_batches, batch_count = scan_concatenated_jsonl(
        baseline, staged, batch_paths, {batch["id"]: batch}, "id", helpers, "operational batch")
    if set(found_families) != set(config["family_ids"]) or set(found_batches) != {batch["id"]}:
        raise ValueError("Complete family/batch streams do not contain the exact selected rows")
    if (len(batch["complete_fine_family_ids"]) != 85 or
            len(batch["complete_component_ids"]) != 441 or
            len(set(batch["complete_component_ids"])) != 441):
        raise ValueError("Complete selected operational batch is not 85 families / 441 components")
    return {"status": "pass", "family_stream_rows": family_count,
            "selected_family_rows": len(found_families), "batch_stream_rows": batch_count,
            "selected_batch_rows": len(found_batches), "batch_families": 85,
            "batch_components": 441, "phase_bytes": sum(baseline.consumed.values())}


def verify_physical_phase(repo, commit, config):
    baseline, _, helpers, _ = producer.bootstrap(repo, commit, phase="physical")
    pins, staged, _ = source_inventory(baseline)
    context = json.loads(baseline.pinned_bytes(CONTEXT))
    routes = context["routes"]
    expected = context["physical_records"]
    ids = sorted(config["component_ids"])
    helpers.exact_rows([dict(row, id=identity) for identity, row in expected.items()], ids)
    parts = sorted((x for x in pins["files"] if x["kind"] == "physical-whole-part"),
                   key=lambda x: x["path"])
    if len(parts) != EXPECTED_PHYSICAL_PARTS:
        raise ValueError("Require every whole physical-comparison part referenced by selected routes")
    required_sources = {routes[cid]["whole_physical_containing_file"] for cid in ids}
    if {x["source_path"] for x in parts} != required_sources:
        raise ValueError("Physical comparison source parts differ from selected route references")
    found = {}
    source_path_by_id = {}
    row_count = 0
    for item in parts:
        decoded = producer.decode_pinned(baseline, staged, OWNED + item["path"])
        for line in decoded.splitlines():
            if not line:
                continue
            row = json.loads(line)
            identity = row.get("component_id")
            if identity not in expected:
                continue
            if identity in found:
                raise ValueError(f"Selected physical comparison record is duplicated: {identity}")
            if item["source_path"] != routes[identity]["whole_physical_containing_file"]:
                raise ValueError(f"Physical record came from a different whole source part: {identity}")
            if row != expected[identity]:
                raise ValueError(f"Complete physical comparison row differs from selected context: {identity}")
            if producer.sha(producer.canonical(row)) != routes[identity]["whole_physical_row_sha256"]:
                raise ValueError(f"Physical comparison row hash differs from route descriptor: {identity}")
            found[identity] = row
            source_path_by_id[identity] = item["source_path"]
            row_count += 1
    helpers.exact_rows([dict(row, id=identity) for identity, row in found.items()], ids)
    return {"status": "pass", "whole_file_count": len(parts),
            "selected_rows": row_count, "source_paths_by_component": source_path_by_id,
            "phase_bytes": sum(baseline.consumed.values())}


def run(repo, commit, vintage):
    started = time.monotonic()
    repo = pathlib.Path(repo).resolve()
    baseline, evidence, helpers, config = producer.bootstrap(repo, commit, phase="source-custody")
    if sum(baseline.consumed.values()) > producer.MAX_INPUT_BYTES:
        raise ValueError("Complete original source custody phase exceeds the admitted byte bound")
    source_pins, _, source_manifest_raw = source_inventory(baseline)
    origins = verify_source_origins(repo, baseline, evidence, source_pins)
    source_phase = {"status": "pass", "bytes_including_origin_rechecks": sum(baseline.consumed.values()),
                    "limit_bytes": baseline.max_phase_bytes}
    route_result = verify_routing_phase(repo, commit, config)
    family_batch_result = verify_family_batch_phase(repo, commit, config)
    physical_result = verify_physical_phase(repo, commit, config)
    baseline, evidence, helpers, config = producer.bootstrap(repo, commit, phase="preflight-overlay")
    output = evidence.NewVintage(
        baseline, OWNED, vintage, ["custody-preflight.json", "preflight-summary.json"]
    )
    spatial_runtime, _, runtime_manifest, runtime_manifest_sha = producer.load_spatial_runtime(baseline, config)
    loaded = producer.load_inputs(baseline, helpers, config, require_custody=False,
                                  inventory_preverified=True)
    pins, context, pointsets, products, contacts, catalogue, metadata, attribution = loaded

    if len(pointsets) != 15 or len(contacts) != 9:
        raise ValueError("Complete pointset/contact source scope differs from exact issue roster")
    product_counts = {key: len(value["features"]) for key, value in products.items()}
    if product_counts != {"gb:KGZ:ADM2": 41, "gb:TJK:ADM2": 58}:
        raise ValueError("Complete simplified administrative product counts differ")
    receipt = {
        "version": 1,
        "status": "pass",
        "context_sha256": producer.sha(producer.canonical(context)),
        "input_pins_sha256": producer.sha(source_manifest_raw),
        "input_file_count": len(source_pins["files"]),
        "source_file_count": config["source_file_count"],
        "runtime_artifact_count": config["runtime_file_count"],
        "scope": {
            "subject_ids": config["subject_ids"],
            "family_ids": config["family_ids"],
            "component_ids": config["component_ids"],
            "contact_ids": config["contact_ids"],
        },
        "source_origin_receipt": origins,
        "whole_stream_receipts": {
            "source_origin_phase": source_phase,
            "routing": route_result,
            "families_and_batch": family_batch_result,
            "physical_comparisons": physical_result,
        },
        "selected_context": {
            "context_sha256": producer.sha(producer.canonical(context)),
            "complete_families": len(context["selected_families_source_rows"]),
            "operational_batch_id": context["operational_batch"]["id"],
            "operational_batch_families": len(context["operational_batch"]["complete_fine_family_ids"]),
            "operational_batch_components": len(context["operational_batch"]["complete_component_ids"]),
            "component_pointset_count": len(pointsets),
            "physical_record_count": len(context["physical_records"]),
            "contact_feature_count": len(contacts),
            "complete_source_feature_counts": product_counts,
        },
        "runtime": {
            "captured_manifest_sha256": runtime_manifest_sha,
            "python": runtime_manifest["python"]["version"],
            "shapely": spatial_runtime.__version__,
            "geos": spatial_runtime.geos_version_string,
            "captured_bytes": runtime_manifest["captured_bytes"],
            "captured_file_count": runtime_manifest["captured_file_count"],
            "proj_used": False,
        },
        "limits": [
            "This preflight verifies bytes, identities and source-row joins before geographic operations; it establishes no source authority or physical land/water truth.",
            "The complete captured Python/Shapely/GEOS runtime is pinned; Apple system libraries are supplied by the recorded macOS host.",
        ],
    }
    if receipt["selected_context"]["context_sha256"] != producer.sha(producer.canonical(context)):
        raise ValueError("Selected context changed during preflight")
    max_rss = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) if sys.platform == "darwin" else int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)
    if max_rss > producer.MAX_RSS_BYTES:
        raise ValueError("Custody preflight exceeded the admitted RAM ceiling")
    summary = {
        "status": "complete",
        "preflight_only": True,
        "geographic_operations": 0,
        "elapsed_seconds": time.monotonic() - started,
        "max_rss_bytes": max_rss,
        "full_phase_consumed_bytes": sum(baseline.consumed.values()),
        "full_phase_limit_bytes": baseline.max_phase_bytes,
        "output_limit_bytes": 12 * 1024 * 1024,
        "runtime_raw_bytes": runtime_manifest["captured_bytes"],
        "runtime_bundle_bytes": runtime_manifest["bundle"]["bytes"],
        "runtime_file_count": runtime_manifest["captured_file_count"],
        "source_input_file_count": len([x for x in pins["files"] if x["kind"] not in ("runtime-bundle", "runtime-manifest")]),
        "runtime_input_file_count": len([x for x in pins["files"] if x["kind"] in ("runtime-bundle", "runtime-manifest")]),
        "custody_receipt_sha256": producer.sha(producer.canonical(receipt)),
    }
    publication = output.publish({"custody-preflight.json": receipt,
                                  "preflight-summary.json": summary})
    print(json.dumps({"status": "pass", "vintage": vintage, "publication": publication,
                      "summary": summary}, sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--baseline-commit", required=True)
    parser.add_argument("--vintage", default="custody-1")
    args = parser.parse_args()
    run(args.repo, args.baseline_commit, args.vintage)


if __name__ == "__main__":
    main()
