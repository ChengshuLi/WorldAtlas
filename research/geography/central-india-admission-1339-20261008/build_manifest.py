"""Build the packet's v1 evidence receipt from the pinned admission audit."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
PACKET = Path(__file__).resolve().parent
OWNED = "research/geography/central-india-admission-1339-20261008/"
BASE = "41ed5e819702fde5cd89445eb09b6d4cefa07bf1"
DATA = "950eb2188e5b66d88ea47a679936a02fe3eb1c40"
EXEC_PATH = "research/geography/central-india-batch3-reproduction-erratum-2026/vintages/original-20261007-f/execution.json"


def git_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{commit}:{path}"])


def descriptor(path: str, raw: bytes) -> dict:
    return {"path": path, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "hash_kind": "file-bytes"}


def main() -> None:
    audit = json.loads((PACKET / "admission-assessment.json").read_text())
    execution = json.loads(git_bytes(BASE, EXEC_PATH))
    source_path = "data/global-sources/IND-ADM3.geojson.gz"
    metadata_path = "data/global-sources/IND-ADM3-metadata.json"
    issue_scope_path = "data/regional-review/regional-review-78f086631fc52a58/issue-scope.json"
    report_path = "data/regional-review/regional-review-78f086631fc52a58/reproduction-results.json"
    helper_path = "scripts/evidence/immutable.py"
    runner_path = "research/geography/central-india-batch3-reproduction-erratum-2026/reproduce.py"
    producer_path = "data/regional-review/regional-review-78f086631fc52a58/reproduce.py"

    files = [{**row, "commit": DATA} for row in execution["baseline_files"]]
    execution_descriptor = {**descriptor(EXEC_PATH, git_bytes(BASE, EXEC_PATH)), "commit": BASE}
    runner_descriptor = {**descriptor(runner_path, git_bytes(BASE, runner_path)), "commit": BASE}
    files.extend([execution_descriptor, runner_descriptor])
    pins = {
        "execution-ledger": execution_descriptor["sha256"],
        "native-source-compressed": next(row["sha256"] for row in execution["baseline_files"] if row["path"] == source_path),
        "native-source-metadata": next(row["sha256"] for row in execution["baseline_files"] if row["path"] == metadata_path),
        "issue-scope": next(row["sha256"] for row in execution["baseline_files"] if row["path"] == issue_scope_path),
        "scoped-reproducer": runner_descriptor["sha256"],
        "original-producer": next(row["sha256"] for row in execution["baseline_files"] if row["path"] == producer_path),
        "original-report": next(row["sha256"] for row in execution["baseline_files"] if row["path"] == report_path),
        "pinned-output-helper": next(row["sha256"] for row in execution["baseline_files"] if row["path"] == helper_path),
    }
    pin_paths = {
        "execution-ledger": {"path": EXEC_PATH, "commit": BASE},
        "native-source-compressed": {"path": source_path, "commit": DATA},
        "native-source-metadata": {"path": metadata_path, "commit": DATA},
        "issue-scope": {"path": issue_scope_path, "commit": DATA},
        "scoped-reproducer": {"path": runner_path, "commit": BASE},
        "original-producer": {"path": producer_path, "commit": DATA},
        "original-report": {"path": report_path, "commit": DATA},
        "pinned-output-helper": {"path": helper_path, "commit": DATA},
    }
    subject_files = {identity: {"path": path, "commit": DATA}
                     for identity, path in execution["subject_files"].items()}

    candidate_names = ["README.md", "admission.py", "run_controls.py", "preflight.py", "guarded_reproduce.py",
                       "build_manifest.py", "admission-controls.json", "admission-assessment.json"]
    outputs = [descriptor(OWNED + name, (ROOT / OWNED / name).read_bytes()) for name in candidate_names]

    source_ids = ["geoBoundaries IND ADM3 2018", "Original Central India admission ledger",
                  "GZIP File Format Specification (RFC 1952)", "Python gzip library documentation"]
    sources = [
        {"id": source_ids[0],
         "url": "https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09/releaseData/gbOpen/IND/ADM3/geoBoundaries-IND-ADM3_simplified.geojson",
         "role": "retained historical administrative source referenced only for admission limits",
         "vintage": "2018 boundary vintage; metadata updated 2023-01-19; built 2023-12-12",
         "retrieved_at": "2026-10-06",
         "license": {"status": "unknown", "terms": "Publisher metadata asserts ODbL 1.0. This packet does not independently confirm legal terms or obligations."},
         "retention": "restoration-only", "verification": "unverified", "temporal_status": "unknown",
         "restoration": f"Read {source_path} at {DATA}; verify compressed SHA-256 {pins['native-source-compressed']}. The bytes are preserved by prior evidence; this packet did not copy or decompress them.",
         "limit": "Publisher calls ADM3 Sub-District; 6,822 retained feature receipts differ from the 6,836 metadata declaration. Current legal boundaries, parentage, completeness, rights and neighboring-tier correspondence remain unresolved."},
        {"id": source_ids[1],
         "url": f"https://github.com/ChengshuLi/WorldAtlas/blob/{BASE}/{EXEC_PATH}",
         "role": "immutable ledger for the exact 55 source/input descriptors, prior decoded chunk receipts, scope and reproduction controls",
         "vintage": f"retained execution ledger at {BASE}", "retrieved_at": "2026-10-08",
         "license": {"status": "unknown", "terms": "Repository audit evidence; no separate redistribution rights are asserted."},
         "retention": "restoration-only", "verification": "verified", "temporal_status": "reference",
         "restoration": f"Read {EXEC_PATH} at {BASE}, SHA-256 {pins['execution-ledger']}; verify each of its 55 path/size/hash descriptors against commit {DATA}.",
         "limit": "The chunk hashes and declared decoded hash are historical receipts; the full decoded gzip body was not re-authenticated."},
        {"id": source_ids[2], "url": "https://www.rfc-editor.org/rfc/rfc1952.html",
         "role": "gzip member/trailer format definition, including CRC32 and ISIZE fields",
         "vintage": "RFC 1952, May 1996", "retrieved_at": "2026-10-08",
         "license": {"status": "unknown", "terms": "No copied RFC text is included in this packet."},
         "retention": "restoration-only", "verification": "verified", "temporal_status": "reference",
         "restoration": "Read the authoritative RFC Editor HTML at the cited URL. ISIZE is the uncompressed size modulo 2^32, and the trailer includes CRC32; reading ISIZE alone does not validate the body or CRC.",
         "limit": "The packet reads the final four bytes as a size claim only; no gzip decompressor ran on the retained source."},
        {"id": source_ids[3], "url": "https://docs.python.org/3/library/gzip.html",
         "role": "Python standard-library gzip behavior reference for bounded fixture controls",
         "vintage": "Python 3 library documentation accessed 2026-10-08", "retrieved_at": "2026-10-08",
         "license": {"status": "unknown", "terms": "No documentation text is copied into the evidence files."},
         "retention": "restoration-only", "verification": "verified", "temporal_status": "reference",
         "restoration": "Read the Python gzip library documentation at the cited URL; its GzipFile interface supports bounded reads and multi-member gzip streams.",
         "limit": "Synthetic controls exercise local Python behavior only; they do not authenticate the historical source body or runtime closure."},
    ]

    ledger_hash = pins["execution-ledger"]
    audit_hash = next(row["sha256"] for row in outputs if row["path"].endswith("/admission-assessment.json"))
    metrics = [
        {"id": "complete_encoded_input_bytes", "input_sha256": ledger_hash, "input_file": {"path": EXEC_PATH, "commit": BASE}, "evaluation_commit": BASE, "vintage": "baseline", "value": 238931443, "unit": "bytes"},
        {"id": "retained_decoded_source_size_claim", "input_sha256": ledger_hash, "input_file": {"path": EXEC_PATH, "commit": BASE}, "evaluation_commit": BASE, "vintage": "baseline", "value": 40040002, "unit": "bytes"},
        {"id": "minimum_raw_plus_decoded_bytes", "input_sha256": ledger_hash, "input_file": {"path": EXEC_PATH, "commit": BASE}, "evaluation_commit": BASE, "vintage": "baseline", "value": 278971445, "unit": "bytes"},
        {"id": "seven_output_reservations", "input_sha256": pins["scoped-reproducer"], "input_file": {"path": runner_path, "commit": BASE}, "evaluation_commit": BASE, "vintage": "baseline", "value": 7, "unit": "output files"},
        {"id": "output_reservation_bytes", "input_sha256": pins["scoped-reproducer"], "input_file": {"path": runner_path, "commit": BASE}, "evaluation_commit": BASE, "vintage": "baseline", "value": 234881024, "unit": "bytes"},
        {"id": "complete_phase_reserved_bytes", "input_sha256": ledger_hash, "input_file": {"path": EXEC_PATH, "commit": BASE}, "evaluation_commit": BASE, "vintage": "baseline", "value": 513856565, "unit": "bytes"},
        {"id": "complete_phase_limit", "input_sha256": audit_hash, "input_file": {"path": OWNED + "admission-assessment.json", "commit": "candidate"}, "evaluation_commit": BASE, "vintage": "baseline", "value": 268435456, "unit": "bytes"},
        {"id": "phase_limit_overage_before_outputs", "input_sha256": ledger_hash, "input_file": {"path": EXEC_PATH, "commit": BASE}, "evaluation_commit": BASE, "vintage": "baseline", "value": 10535989, "unit": "bytes"},
        {"id": "whole_source_body_file_limit", "input_sha256": audit_hash, "input_file": {"path": OWNED + "admission-assessment.json", "commit": "candidate"}, "evaluation_commit": BASE, "vintage": "baseline", "value": 33554432, "unit": "bytes"},
        {"id": "exact_scoped_subjects", "input_sha256": pins["issue-scope"], "input_file": {"path": issue_scope_path, "commit": DATA}, "evaluation_commit": BASE, "vintage": "baseline", "value": 229, "unit": "subjects"},
        {"id": "scoped_provinces", "input_sha256": pins["issue-scope"], "input_file": {"path": issue_scope_path, "commit": DATA}, "evaluation_commit": BASE, "vintage": "baseline", "value": 35, "unit": "provinces"},
        {"id": "partial_madhya_pradesh_subjects", "input_sha256": pins["issue-scope"], "input_file": {"path": issue_scope_path, "commit": DATA}, "evaluation_commit": BASE, "vintage": "baseline", "value": 144, "unit": "subjects"},
        {"id": "partial_uttar_pradesh_subjects", "input_sha256": pins["issue-scope"], "input_file": {"path": issue_scope_path, "commit": DATA}, "evaluation_commit": BASE, "vintage": "baseline", "value": 85, "unit": "subjects"},
        {"id": "retained_source_feature_receipt", "input_sha256": ledger_hash, "input_file": {"path": EXEC_PATH, "commit": BASE}, "evaluation_commit": BASE, "vintage": "baseline", "value": 6822, "unit": "features"},
        {"id": "metadata_declared_feature_count", "input_sha256": pins["native-source-metadata"], "input_file": {"path": metadata_path, "commit": DATA}, "evaluation_commit": BASE, "vintage": "baseline", "value": 6836, "unit": "features"},
    ]
    summaries = [{"metric_id": row["id"], "value": row["value"], "unit": row["unit"]} for row in metrics]
    conclusions = [
        {"status": "supported", "source_ids": [source_ids[1]], "text": "All 55 distinct encoded baseline path identities were re-read from immutable Git commit 950eb2188e5b66d88ea47a679936a02fe3eb1c40 and their bytes and SHA-256 values matched the retained run ledger; their sum is 238,931,443 bytes."},
        {"status": "supported", "source_ids": [source_ids[0], source_ids[1], source_ids[2]], "text": "The compressed source footer and ten retained chunk byte receipts both claim a 40,040,002-byte decoded body. Under RFC 1952, ISIZE is a modulo-2^32 size field, so these records establish a size claim only; the decoded body digest and CRC were not rechecked."},
        {"status": "supported", "source_ids": [source_ids[1]], "text": "The input-only minimum of 278,971,445 bytes exceeds the 268,435,456-byte phase ceiling by 10,535,989 bytes before outputs and completion receipt; the bounded assessment therefore refuses the original full reproduction."},
        {"status": "supported", "source_ids": [source_ids[1]], "text": "The pinned producer declares seven outputs. Reserving all seven at 33,554,432 bytes each and the 4,096-byte completion receipt produces a conservative complete-phase reservation of 513,856,565 bytes; runtime closure also remains incomplete."},
        {"status": "supported", "source_ids": [source_ids[1]], "text": "The issue-scope partition remains exactly 229 unique subjects across 35 provinces: 144/422 partial Madhya Pradesh and 85/244 partial Uttar Pradesh. This verifies the declared work roster only."},
        {"status": "unresolved", "source_ids": [source_ids[0], source_ids[1]], "text": "The decoded original source, whole-body CRC and SHA-256, effective legal boundaries, parentage, source completeness, rights and neighboring-tier correspondence remain unresolved; no geographic correctness or approval is claimed."},
    ]
    manifest = {
        "version": 1, "issue": 1497, "lane": "geography", "worker_id": "01a10948-7d38-75d0-bc01-4cc28ea41f49",
        "subject_ids": sorted(execution["subject_ids"]),
        "subject_ids_sha256": audit["scope"]["subject_ids_sha256"],
        "baseline": {"version": 2, "commit": BASE, "files": files, "pins": pins, "pin_files": pin_paths,
                     "subject_files": subject_files},
        "sources": sources, "outputs": outputs,
        "methods": [{"id": "whole-input-admission-and-source-free-audit",
                     "description": "Re-read each declared encoded input by immutable Git path and hash; use only gzip trailer size and retained chunk receipt sizes for decoded-body arithmetic; run fail-closed synthetic input, aggregate, identity, output and preservation controls. The original gzip body is not decoded.",
                     "software": "Python standard library 3.x; Node.js evidence-quality validator at the checked repository head", "units": "bytes and scoped administrative record counts", "kind": "measurement"}],
        "metrics": metrics, "summaries": summaries, "conclusions": conclusions,
        "stages": {"research": "partial", "implementation": "proposed", "geographic_approval": "unapproved"},
        "commands": ["python3 research/geography/central-india-admission-1339-20261008/run_controls.py",
                      "python3 research/geography/central-india-admission-1339-20261008/preflight.py",
                      "python3 research/geography/central-india-admission-1339-20261008/guarded_reproduce.py",
                      "python3 research/geography/central-india-admission-1339-20261008/build_manifest.py",
                      "node scripts/evidence-quality.mjs research/geography/central-india-admission-1339-20261008/evidence-quality.json"]
    }
    (PACKET / "evidence-quality.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
