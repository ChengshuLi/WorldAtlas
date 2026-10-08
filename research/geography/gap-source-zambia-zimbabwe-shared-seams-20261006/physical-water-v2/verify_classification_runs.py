#!/usr/bin/env python3
"""Verify both complete WorldCover result bundles without reading raster pixels."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
PACKET = BASE.parent
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_RUN_BYTES = 64 * 1024 * 1024
MAX_PAIR_BYTES = 128 * 1024 * 1024


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def expected_inventory(geometry_path: Path) -> dict:
    geometry_gzip = geometry_path.read_bytes()
    geometry_decoded = gzip.decompress(geometry_gzip)
    data = json.loads(geometry_decoded)
    components = [row["component_id"] for row in data["components"]]
    subjects = list(data["subject_ids"])
    contact_pairs = set()
    for component in data["components"]:
        for row in component["source_feature_intersections"]:
            subject_id = f"gb:{row['country']}:ADM2:{row['shapeID']}"
            if subject_id in subjects:
                contact_pairs.add((component["component_id"], subject_id))
    fragment_ids = [row["id"] for row in data["original_contact_fragment_features"]]
    source_contact_geometry_hashes = []
    for row in data["original_source_contacts"]:
        geometry = row["geometry"]
        raw = json.dumps(geometry, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        source_contact_geometry_hashes.append(sha256(raw))
    range_path = BASE / "worldcover-source-ranges.json"
    range_raw = range_path.read_bytes()
    range_manifest = json.loads(range_raw)
    ifd_path = BASE / range_manifest["ifd_metadata_range"]["file"]
    frozen_path = BASE / "frozen-inputs.json"
    frozen_raw = frozen_path.read_bytes()
    coverage_raw = (BASE / "source-coverage.json").read_bytes()
    geometry_two_raw = PACKET / "run-two/source-geometry-results.json.gz"
    return {
        "component_ids": set(components),
        "subject_ids": set(subjects),
        "contact_pairs": contact_pairs,
        "fragment_ids": set(fragment_ids),
        "original_source_contact_geometry_hashes": source_contact_geometry_hashes,
        "expected_input_pins": {
            "frozen_inputs_sha256": sha256(frozen_raw),
            "range_manifest_sha256": sha256(range_raw),
            "tiff_ifd_range_sha256": sha256(ifd_path.read_bytes()),
            "source_coverage_sha256": sha256(coverage_raw),
            "source_geometry_run_one_sha256": sha256(geometry_gzip),
            "source_geometry_run_two_sha256": sha256(geometry_two_raw),
            "source_geometry_uncompressed_bytes": len(geometry_decoded),
            "source_geometry_uncompressed_sha256": sha256(geometry_decoded),
        },
        "expected_producer_sha256": json.loads(frozen_raw)["producer_and_checker_hashes"]["classify_worldcover.py"],
    }


def safe_result_path(root: Path, relative_path: str) -> Path:
    path = Path(relative_path)
    if path.is_absolute() or ".." in path.parts:
        raise RuntimeError(f"Unsafe result path: {relative_path}")
    target = (root / path).resolve()
    if not target.is_relative_to(root.resolve()):
        raise RuntimeError(f"Result path escapes its bundle: {relative_path}")
    return target


def audit_bundle(run_dir: Path, expected_run: str, expected: dict) -> dict:
    receipt_path = run_dir / "execution-receipt.json"
    if not receipt_path.is_file():
        raise RuntimeError(f"Missing execution receipt: {receipt_path}")
    receipt_raw = receipt_path.read_bytes()
    if len(receipt_raw) > MAX_FILE_BYTES:
        raise RuntimeError(f"Receipt exceeds the 32 MiB cap: {receipt_path}")
    receipt = json.loads(receipt_raw)
    if receipt.get("run") != expected_run:
        raise RuntimeError(f"Wrong run label in {receipt_path}: {receipt.get('run')}")
    index_relative = receipt.get("result_index_file")
    index_path = safe_result_path(run_dir, index_relative)
    index_raw = index_path.read_bytes()
    if len(index_raw) > MAX_FILE_BYTES or sha256(index_raw) != receipt.get("result_index_sha256"):
        raise RuntimeError(f"Index size/hash does not match its receipt: {index_path}")
    index = json.loads(index_raw)
    if index.get("output_layout") != "worldcover-classification-index-v1; component and point-contact-fragment records are in ordered JSON shards listed in this index":
        raise RuntimeError("Unexpected classification output layout")

    result_rows = receipt.get("result_files")
    if not isinstance(result_rows, list) or result_rows != sorted(result_rows, key=lambda row: row["path"]):
        raise RuntimeError("Receipt result files are missing or not in canonical path order")
    expected_paths = {row["path"] for row in result_rows}
    if len(expected_paths) != len(result_rows) or index_relative not in expected_paths:
        raise RuntimeError("Receipt paths are duplicated or do not include the index")
    total_bytes = len(receipt_raw)
    result_rows_by_path = {row["path"]: row for row in result_rows}
    for row in result_rows:
        path = safe_result_path(run_dir, row["path"])
        raw = path.read_bytes()
        if len(raw) > MAX_FILE_BYTES or len(raw) != row["bytes"] or sha256(raw) != row["sha256"]:
            raise RuntimeError(f"Result shard size/hash mismatch: {path}")
        total_bytes += len(raw)
    actual_paths = {str(path.relative_to(run_dir)) for path in run_dir.rglob("*") if path.is_file() and path != receipt_path}
    if actual_paths != expected_paths:
        raise RuntimeError(f"Unlisted or missing files in result bundle: {actual_paths ^ expected_paths}")
    if total_bytes != receipt.get("bundle_bytes_including_receipt") or total_bytes > MAX_RUN_BYTES:
        raise RuntimeError("Receipt-inclusive run output size is wrong or over the 64 MiB cap")
    if receipt.get("result_file_count") != len(result_rows) or receipt.get("result_bytes") != sum(row["bytes"] for row in result_rows):
        raise RuntimeError("Receipt output file count/byte total is inconsistent")

    for field in ("component_result_shards", "point_contact_fragment_shards"):
        for descriptor in index.get(field, []):
            if result_rows_by_path.get(descriptor.get("path")) != descriptor:
                raise RuntimeError(f"Index shard receipt binding disagrees for {descriptor.get('path')}")

    component_ids = []
    for descriptor in index.get("component_result_shards", []):
        shard = json.loads(safe_result_path(run_dir, descriptor["path"]).read_text(encoding="utf-8"))
        if shard.get("record_type") != "component-result":
            raise RuntimeError("Component shard has the wrong record type")
        component_ids.append(shard["record"]["component_id"])
    fragment_ids = []
    for descriptor in index.get("point_contact_fragment_shards", []):
        shard = json.loads(safe_result_path(run_dir, descriptor["path"]).read_text(encoding="utf-8"))
        if shard.get("record_type") != "point-contact-fragment":
            raise RuntimeError("Contact fragment shard has the wrong record type")
        fragment_ids.append(shard["record"]["fragment_id"])
    if set(component_ids) != expected["component_ids"] or len(component_ids) != len(expected["component_ids"]):
        raise RuntimeError("Component output roster is incomplete or duplicated")
    if set(fragment_ids) != expected["fragment_ids"] or len(fragment_ids) != len(expected["fragment_ids"]):
        raise RuntimeError("Original contact-fragment roster is incomplete or duplicated")
    if index.get("component_result_count") != len(component_ids) or index.get("point_contact_fragment_count") != len(fragment_ids):
        raise RuntimeError("Index record counts disagree with its shard lists")

    scope = index.get("scope", {})
    if set(scope.get("component_ids", [])) != expected["component_ids"] or scope.get("component_count") != len(expected["component_ids"]):
        raise RuntimeError("Index scope does not bind all ten original candidate components")
    if set(scope.get("contact_subject_ids", [])) != expected["subject_ids"]:
        raise RuntimeError("Index scope does not bind all four original contact subjects")
    local_rows = scope.get("local_source_intersections_per_contact_subject", {})
    if set(local_rows) != expected["subject_ids"]:
        raise RuntimeError("Index omits one or more contact subjects")
    observed_pairs = set()
    for subject_id, rows in local_rows.items():
        for row in rows:
            pair = (row["component_id"], subject_id)
            if pair in observed_pairs:
                raise RuntimeError(f"Duplicate local contact intersection: {pair}")
            observed_pairs.add(pair)
    if observed_pairs != expected["contact_pairs"]:
        raise RuntimeError("Local contact output does not preserve the complete source-intersection roster")
    point_hashes = [row["geometry_sha256"] for row in scope.get("point_only_contact_evidence", [])]
    if sorted(point_hashes) != sorted(expected["original_source_contact_geometry_hashes"]):
        raise RuntimeError("Original point-only contact evidence hashes changed or are missing")
    pins = index.get("input_pins", {})
    if pins != expected["expected_input_pins"]:
        raise RuntimeError("Result index input pins do not match the current frozen source inputs")
    if receipt.get("producer_sha256") != expected["expected_producer_sha256"]:
        raise RuntimeError("Result receipt producer hash does not match the frozen classifier code")
    return {"receipt": receipt, "index": index, "index_sha256": sha256(index_raw), "result_files": result_rows, "bundle_bytes": total_bytes}


def verify_two_runs(run_one: Path, run_two: Path, expected: dict) -> dict:
    one = audit_bundle(run_one, "one", expected)
    two = audit_bundle(run_two, "two", expected)
    if one["bundle_bytes"] + two["bundle_bytes"] > MAX_PAIR_BYTES:
        raise RuntimeError("Combined result bundles exceed the 128 MiB pair cap")
    if one["index_sha256"] != two["index_sha256"] or one["result_files"] != two["result_files"]:
        raise RuntimeError("The two independently generated result bundles are not byte-reproducible")
    if one["index"].get("input_pins") != two["index"].get("input_pins"):
        raise RuntimeError("The two output runs do not share identical immutable input pins")
    if one["receipt"].get("producer_sha256") != two["receipt"].get("producer_sha256"):
        raise RuntimeError("The two output runs used different producer code")
    return {
        "result": "passed",
        "component_count": len(expected["component_ids"]),
        "contact_subject_count": len(expected["subject_ids"]),
        "local_contact_intersection_count": len(expected["contact_pairs"]),
        "point_contact_fragment_count": len(expected["fragment_ids"]),
        "original_source_contact_evidence_count": len(expected["original_source_contact_geometry_hashes"]),
        "result_file_count_per_run": len(one["result_files"]),
        "result_files_sha256_equal": True,
        "input_pins_equal": True,
        "producer_hash_equal": True,
        "run_one_bundle_bytes": one["bundle_bytes"],
        "run_two_bundle_bytes": two["bundle_bytes"],
        "combined_bundle_bytes": one["bundle_bytes"] + two["bundle_bytes"],
        "source_pixels_read": False,
    }


def controls_only() -> dict:
    # Import here so actual verification remains narrowly scoped and all controls
    # exercise the same production output writer used by the classifier.
    sys.path.insert(0, str(BASE))
    import classify_worldcover as producer

    synthetic = {
        "selected_original_blocks_loaded": 0,
        "selected_original_blocks_decoded_bytes": 0,
        "synthetic_controls": {"result": "passed"},
        "source": {"id": "synthetic"},
        "scope": {
            "issue": 1234,
            "component_count": 1,
            "component_ids": ["synthetic-component"],
            "contact_subject_ids": ["synthetic-subject"],
            "local_source_intersections_per_contact_subject": {"synthetic-subject": [{"component_id": "synthetic-component"}]},
            "point_only_contact_evidence": [{"geometry_sha256": "synthetic-point-hash"}],
            "point_contact_fragments": [{"fragment_id": "synthetic-fragment"}],
        },
        "input_pins": {"frozen_inputs_sha256": "f" * 64, "range_manifest_sha256": "r" * 64, "tiff_ifd_range_sha256": "i" * 64, "source_coverage_sha256": "c" * 64, "source_geometry_run_one_sha256": "1" * 64, "source_geometry_run_two_sha256": "2" * 64, "source_geometry_uncompressed_bytes": 123, "source_geometry_uncompressed_sha256": "u" * 64},
        "component_results": [{"component_id": "synthetic-component"}],
    }
    expected = {"component_ids": {"synthetic-component"}, "subject_ids": {"synthetic-subject"}, "contact_pairs": {("synthetic-component", "synthetic-subject")}, "fragment_ids": {"synthetic-fragment"}, "original_source_contact_geometry_hashes": ["synthetic-point-hash"], "expected_input_pins": synthetic["input_pins"], "expected_producer_sha256": "p" * 64}
    with tempfile.TemporaryDirectory(prefix="worldcover-run-verifier-") as temporary:
        root = Path(temporary)
        one_dir, two_dir = root / "run-one", root / "run-two"
        producer.write_result_bundle(synthetic, one_dir, "one", producer_sha256="p" * 64)
        producer.write_result_bundle(synthetic, two_dir, "two", producer_sha256="p" * 64)
        report = verify_two_runs(one_dir, two_dir, expected)
        corrupted = root / "corrupted-run-one"
        shutil.copytree(one_dir, corrupted)
        component_path = corrupted / "component-results/0001.json"
        component_path.write_bytes(component_path.read_bytes() + b" ")
        try:
            audit_bundle(corrupted, "one", expected)
        except RuntimeError:
            pass
        else:
            raise RuntimeError("Verifier adverse control accepted a mutated shard")
    return {"result": "passed", "synthetic_two_run_reproducibility": report["result_files_sha256_equal"], "exact_roster_checks": "passed", "mutation_rejected": True, "source_pixels_read": False}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--controls-only", action="store_true", help="test the verifier against synthetic complete bundles; no raster data is read")
    args = parser.parse_args()
    if args.controls_only:
        print(json.dumps(controls_only(), sort_keys=True, indent=2))
        return
    report = verify_two_runs(BASE / "run-one", BASE / "run-two", expected_inventory(PACKET / "run-one/source-geometry-results.json.gz"))
    print(json.dumps(report, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
