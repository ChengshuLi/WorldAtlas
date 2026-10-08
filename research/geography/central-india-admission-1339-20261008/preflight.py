"""Verify bounded admission facts without decoding or reproducing the source."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import admission

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "admission-assessment.json"
BASE_COMMIT = "41ed5e819702fde5cd89445eb09b6d4cefa07bf1"
DATA_COMMIT = "950eb2188e5b66d88ea47a679936a02fe3eb1c40"
EXECUTION_PATH = "research/geography/central-india-batch3-reproduction-erratum-2026/vintages/original-20261007-f/execution.json"
EXECUTION_SHA256 = "e584de2d73fc207d50da94947582600ec7cc6deb5ae9804b51bef72ddff4f52a"


def git_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{commit}:{path}"])


def hash_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def run() -> dict:
    execution_raw = git_bytes(BASE_COMMIT, EXECUTION_PATH)
    if hash_bytes(execution_raw) != EXECUTION_SHA256:
        raise ValueError("retained execution ledger changed from the issue pin")
    execution = json.loads(execution_raw)
    if execution.get("original_data_commit") != DATA_COMMIT:
        raise ValueError("execution ledger points at a different source commit")
    descriptors = execution.get("baseline_files")
    if not isinstance(descriptors, list) or len(descriptors) != 55:
        raise ValueError("expected exactly 55 retained baseline descriptors")

    rows = []
    raw_inputs = []
    seen_paths = set()
    seen_digests = set()
    for row in descriptors:
        path, expected_size, expected_digest = row["path"], row["bytes"], row["sha256"]
        if path in seen_paths:
            raise ValueError("duplicate baseline path: " + path)
        seen_paths.add(path)
        actual = git_bytes(DATA_COMMIT, path)
        actual_digest = hash_bytes(actual)
        if len(actual) != expected_size or actual_digest != expected_digest:
            raise ValueError("immutable baseline bytes disagree with retained descriptor: " + path)
        if expected_digest in seen_digests:
            raise ValueError("issue states all 55 encoded inputs are unique; duplicate digest: " + path)
        seen_digests.add(expected_digest)
        category = "source" if path.startswith("data/global-sources/") else (
            "code-runtime-input" if path.startswith("scripts/") or path.endswith("reproduce.py") else "geography-and-context")
        raw_inputs.append({"identity": "raw:" + path, "category": category,
                           "bytes": expected_size, "sha256": expected_digest, "authenticated": True})
        rows.append({"path": path, "bytes": len(actual), "sha256": actual_digest,
                     "descriptor_matched": True, "category": category})
        del actual

    source_path = "data/global-sources/IND-ADM3.geojson.gz"
    source_row = next(row for row in descriptors if row["path"] == source_path)
    compressed = git_bytes(DATA_COMMIT, source_path)
    if len(compressed) != source_row["bytes"] or hash_bytes(compressed) != source_row["sha256"]:
        raise ValueError("compressed source bytes disagree with source descriptor")
    footer_isize = admission.gzip_footer_isize(compressed)
    source_claim = execution["source"]
    chunk_rows = source_claim["decoded_chunks"]
    chunk_total = sum(row["decoded_bytes"] for row in chunk_rows)
    if len(chunk_rows) != 10 or chunk_total != 40_040_002 or footer_isize != 40_040_002:
        raise ValueError("retained size claims do not agree on the decoded byte count")
    if source_claim["decoded_sha256"] != "4ea6807d0a0c5aac0b46ee8e31ed7c30fbec273b44345bba1e4a2bb5f299f5fb":
        raise ValueError("retained decoded-source digest claim changed")

    runner_path = "research/geography/central-india-batch3-reproduction-erratum-2026/reproduce.py"
    runner_raw = git_bytes(BASE_COMMIT, runner_path)
    runner_text = runner_raw.decode("utf-8")
    reports_match = re.search(r"(?m)^RUN_REPORTS\s*=\s*\(([^)]*)\)", runner_text)
    outputs_match = re.search(r"(?m)^RESULT_NAMES\s*=\s*\(\*RUN_REPORTS,([^)]*)\)", runner_text)
    if not reports_match or not outputs_match:
        raise ValueError("pinned producer output inventory could not be read")
    run_reports = re.findall(r"['\"]([^'\"]+)['\"]", reports_match.group(1))
    result_names = run_reports + re.findall(r"['\"]([^'\"]+)['\"]", outputs_match.group(1))
    if result_names != ["report-run-1.json", "report-run-2.json", "comparison.json", "execution.json",
                        "positive-control.json", "negative-control.json", "reproducibility-control.json"]:
        raise ValueError("pinned producer output inventory changed or could not be read")
    output_reservations = [{"name": name, "max_bytes": admission.MAX_FILE_BYTES} for name in result_names]

    scope_path = "data/regional-review/regional-review-78f086631fc52a58/issue-scope.json"
    scope_raw = git_bytes(DATA_COMMIT, scope_path)
    scope = json.loads(scope_raw)["workload_scope"]
    subject_ids = scope["member_location_ids"]
    province_rows = scope["province_scopes"]
    province_ids = [identity for row in province_rows for identity in row["owned_location_ids"]]
    area_rows = {(row["name"], row["owned_member_location_count"], row["full_area_location_count"], row["partial"])
                 for row in scope["area_scopes"]}
    expected_areas = {("Madhya Pradesh", 144, 422, True), ("Uttar Pradesh", 85, 244, True)}
    if (len(subject_ids) != 229 or len(set(subject_ids)) != 229 or len(province_rows) != 35 or
            len(province_ids) != 229 or len(set(province_ids)) != 229 or set(province_ids) != set(subject_ids) or
            area_rows != expected_areas or set(subject_ids) != set(execution["subject_ids"])):
        raise ValueError("exact partial 229-subject/35-province issue scope does not reconcile")

    decoded_size = footer_isize
    decoded_digest = source_claim["decoded_sha256"]
    decoded_descriptor = {"identity": "decoded:" + source_path, "category": "decoded-source",
                          "bytes": decoded_size, "sha256": decoded_digest,
                          # Footer and historical receipts establish size agreement only.
                          "authenticated": False}
    expected_ids = [row["identity"] for row in raw_inputs] + [decoded_descriptor["identity"]]
    plan = admission.evaluate_phase(raw_inputs=raw_inputs, decoded_inputs=[decoded_descriptor],
                                    output_reservations=output_reservations, expected_input_identities=expected_ids,
                                    runtime_complete=False)
    if plan["status"] != "refused":
        raise AssertionError("known over-limit input closure was not refused")
    raw_bytes = sum(row["bytes"] for row in raw_inputs)
    if raw_bytes != 238_931_443 or raw_bytes + decoded_size != 278_971_445:
        raise ValueError("independent input total differs from the issue's minimum arithmetic")

    return {
        "version": 1,
        "assessment": "refused-before-full-reproduction",
        "retrieved_at": "2026-10-08",
        "base_commit": BASE_COMMIT,
        "original_data_commit": DATA_COMMIT,
        "execution_ledger": {"path": EXECUTION_PATH, "bytes": len(execution_raw), "sha256": hash_bytes(execution_raw)},
        "runner": {"path": runner_path, "sha256": hash_bytes(runner_raw),
                   "original_producer_path": "data/regional-review/regional-review-78f086631fc52a58/reproduce.py",
                   "original_producer_sha256": next(row["sha256"] for row in descriptors if row["path"] == "data/regional-review/regional-review-78f086631fc52a58/reproduce.py"),
                   "observed_separate_baselines_at_lines": [104, 153, 154],
                   "observed_chunkwise_decoded_admission_at_lines": [173, 187],
                   "observed_isolated_execution_at_lines": [379, 403],
                   "observed_output_writer_geography_only_at_lines": [418]},
        "raw_input_audit": {"count": len(rows), "distinct_paths": len(seen_paths),
                            "distinct_sha256": len(seen_digests), "bytes": raw_bytes,
                            "all_actual_git_bytes_match": all(row["descriptor_matched"] for row in rows),
                            "inputs": rows},
        "decoded_source_claim": {"path": source_path, "compressed_bytes": len(compressed),
                                 "compressed_sha256": hash_bytes(compressed), "gzip_footer_isize": footer_isize,
                                 "retained_chunk_count": len(chunk_rows), "retained_chunk_size_sum": chunk_total,
                                 "retained_chunk_hashes": chunk_rows, "retained_decoded_sha256_claim": decoded_digest,
                                 "decoded_body_authenticated": False,
                                 "decoded_content_crc_and_whole_digest_verified": False,
                                 "source_body_was_not_decompressed": True},
        "scope": {"subject_count": len(subject_ids), "subject_ids": sorted(subject_ids),
                  "subject_ids_sha256": hash_bytes(json.dumps(sorted(subject_ids), separators=(",", ":"), ensure_ascii=False).encode()),
                  "province_count": len(province_rows), "areas": [
                      {"name": name, "owned": owned, "full_area": full, "partial": partial}
                      for name, owned, full, partial in sorted(area_rows)],
                  "research_scope_only": True},
        "admission": {"minimum_raw_plus_decoded_bytes": raw_bytes + decoded_size,
                      "minimum_over_phase_cap_bytes": raw_bytes + decoded_size - admission.MAX_PHASE_BYTES,
                      "decoded_over_file_cap_bytes": decoded_size - admission.MAX_FILE_BYTES,
                      "output_reservations": output_reservations,
                      "output_reservation_bytes": sum(row["max_bytes"] for row in output_reservations),
                      "full_phase_plan": plan,
                      "outputs_reserved": True,
                      "runtime_closure_complete": False,
                      "full_reproduction_authorized": False},
        "source_context": {
            "url": "https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09/releaseData/gbOpen/IND/ADM3/geoBoundaries-IND-ADM3_simplified.geojson",
            "territorial_level": "Publisher metadata calls ADM3 Sub-District; this packet does not validate local legal units or parents.",
            "boundary_vintage": "2018",
            "metadata_vintage": "metadata updated 2023-01-19; built 2023-12-12",
            "retrieval_record": "The preserved source manifest records retrieval on 2026-10-06; the audit hashes repository Git bytes, not a new remote retrieval.",
            "declared_feature_count": 6836,
            "retained_chunk_receipt_feature_count": 6822,
            "completeness": "unresolved: 14-feature count discrepancy; decoded content was not authenticated.",
            "license": "Publisher metadata asserts ODbL 1.0; no independent legal confirmation is claimed.",
            "neighboring_granularity": "This source is the retained Sub-District/ADM3 tier; no boundary or hierarchy comparison is certified by this admission packet."
        },
        "method_limits": [
            "This is source-free admission evidence; no geography report or overlay was recomputed.",
            "No decoded-source CRC or full decoded SHA-256 was checked; retained chunk hashes and gzip footer are claims/size receipts only.",
            "No current legal boundary, parentage, source completeness, reuse-rights, or neighboring-granularity conclusion is established.",
            "Installed runtime/library closure is not authenticated. All seven declared outputs are conservatively reserved at the per-file ceiling, and the phase remains over limit even before any runtime-specific additions."
        ]
    }


def main(output_path: Path = OUT) -> None:
    result = run()
    # Exclusive creation preserves an existing assessment or caller sentinel.
    with output_path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"assessment": result["assessment"], "raw_input_count": result["raw_input_audit"]["count"],
                      "raw_bytes": result["raw_input_audit"]["bytes"],
                      "minimum_raw_plus_decoded_bytes": result["admission"]["minimum_raw_plus_decoded_bytes"],
                      "minimum_over_cap_bytes": result["admission"]["minimum_over_phase_cap_bytes"],
                      "scope_subject_count": result["scope"]["subject_count"],
                     "source_body_was_not_decompressed": result["decoded_source_claim"]["source_body_was_not_decompressed"]},
                     sort_keys=True, indent=2))


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else OUT)
