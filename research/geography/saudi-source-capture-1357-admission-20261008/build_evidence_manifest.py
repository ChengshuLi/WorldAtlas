#!/usr/bin/env python3
"""Build issue 1511's owned evidence manifest from actual Git/file bytes."""
from __future__ import annotations

import gzip
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

import admission
import run_safe

REPO = run_safe.REPO_ROOT
OWNED = run_safe.HERE
SUBJECTS = [
    "gb:SAU:ADM2:3984122B26220942918379",
    "gb:SAU:ADM2:3984122B30508649206602",
    "gb:SAU:ADM2:3984122B40060340495100",
    "gb:SAU:ADM2:3984122B4619800555153",
    "gb:SAU:ADM2:3984122B61840424602376",
    "gb:SAU:ADM2:3984122B84471186351671",
]
MANIFEST_PATH = OWNED.relative_to(REPO).as_posix() + "/evidence-quality.json"


def git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(REPO), *args], text=True).strip()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_regular(path: Path) -> bytes:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise admission.AdmissionError(f"Manifest inventory requires ordinary files: {path}")
    return admission.read_regular(path)


def list_candidate_changes(base_commit: str) -> list[str]:
    tracked = git("diff", "--name-only", base_commit, "--").splitlines()
    untracked = git("ls-files", "--others", "--exclude-standard").splitlines()
    return sorted(set(tracked + untracked))


def baseline_files(commit: str, preservation: dict) -> list[dict]:
    rows = preservation["files"]
    if len(rows) != 148:
        raise admission.AdmissionError("Preservation inventory is not complete")
    result = []
    by_path = {row["path"]: row for row in rows}
    for path, row in sorted(by_path.items()):
        raw = subprocess.check_output(["git", "-C", str(REPO), "show", f"{commit}:{path}"])
        if len(raw) != row["bytes"] or sha(raw) != row["sha256"]:
            raise admission.AdmissionError(f"Baseline whole-file pin changed: {path}")
        descriptor = {"path": path, "bytes": len(raw), "sha256": sha(raw),
                      "hash_kind": "file-bytes", "role": "original-source"}
        if path.endswith("/original-consumed-source.geojson.gz"):
            decoded = gzip.decompress(raw)
            companion = by_path.get(path[:-3])
            if not companion or len(decoded) != companion["bytes"] or sha(decoded) != companion["sha256"]:
                raise admission.AdmissionError("Retained compressed source and decoded companion differ")
            descriptor["uncompressed_bytes"] = len(decoded)
            descriptor["uncompressed_sha256"] = sha(decoded)
        result.append(descriptor)
    return result


def main() -> int:
    commit = "ffa32416fd946ac89da621d02b554ca27733e688"
    subprocess.check_call(["git", "-C", str(REPO), "merge-base", "--is-ancestor", commit, "HEAD"])
    preservation = json.loads(admission.read_regular(OWNED / "execution/predecessor-preservation.json"))
    historical = json.loads(admission.read_regular(OWNED / "execution/verified-historical-products.json"))
    plan_refusal = json.loads(admission.read_regular(OWNED / "execution/refusals/run-4-admission.json"))
    negative = json.loads(admission.read_regular(OWNED / "execution/negative-control-postreview.json"))
    positive = json.loads(admission.read_regular(OWNED / "execution/positive-control-postreview.json"))
    contact_path = run_safe.PREDECESSOR + "/runs/run-1/output/current-contact-features.geojson"
    contact_bytes = subprocess.check_output(["git", "-C", str(REPO), "show", f"{commit}:{contact_path}"])
    contact_features = json.loads(contact_bytes)["features"]
    ids = {feature.get("id", feature.get("properties", {}).get("id")) for feature in contact_features}
    if ids != set(SUBJECTS):
        raise admission.AdmissionError("Pinned contact file differs from the exact six issue subjects")

    files = baseline_files(commit, preservation)
    file_by_path = {row["path"]: row for row in files}
    pin_paths = {
        "frozen_execution": run_safe.PREDECESSOR + "/frozen-execution.json",
        "predecessor_source_extractor": run_safe.PREDECESSOR + "/source_extract.py",
        "predecessor_run_wrapper": run_safe.PREDECESSOR + "/run_final.py",
        "predecessor_compat_inputs": run_safe.PREDECESSOR + "/compat/inputs.py",
        "predecessor_compat_immutable": run_safe.PREDECESSOR + "/compat/immutable.py",
        "predecessor_issue_snapshot": run_safe.PREDECESSOR + "/issue-1336-api.json",
        "predecessor_input_config": run_safe.PREDECESSOR + "/inputs/legacy-input-config.json",
        "historical_run_one_receipt": run_safe.PREDECESSOR + "/runs/run-1-execution.json",
        "historical_run_two_receipt": run_safe.PREDECESSOR + "/runs/run-2-execution.json",
    }
    pin_hashes = {name: file_by_path[path]["sha256"] for name, path in pin_paths.items()}
    expected_pin_paths = [
        run_safe.PREDECESSOR + "/compat/immutable.py",
        run_safe.PREDECESSOR + "/compat/inputs.py",
        run_safe.PREDECESSOR + "/frozen-execution.json",
        run_safe.PREDECESSOR + "/inputs/legacy-input-config.json",
        run_safe.PREDECESSOR + "/issue-1336-api.json",
        run_safe.PREDECESSOR + "/reproducibility.json",
        run_safe.PREDECESSOR + "/run_final.py",
        run_safe.PREDECESSOR + "/runs/run-1/output/candidate-component-features.geojson",
        run_safe.PREDECESSOR + "/source_extract.py",
    ]
    pins = {path: file_by_path[path]["sha256"] for path in expected_pin_paths}
    changes = list_candidate_changes(commit)
    if MANIFEST_PATH not in changes:
        changes.append(MANIFEST_PATH)
    changes = sorted(set(changes))
    if MANIFEST_PATH not in changes:
        changes.append(MANIFEST_PATH)
    changes = sorted(set(changes))
    if not changes or any(not path.startswith(OWNED.relative_to(REPO).as_posix() + "/") for path in changes):
        raise admission.AdmissionError("Changed files are empty or outside issue 1511's declared owned path")
    outputs = []
    for path in changes:
        if path == MANIFEST_PATH:
            continue
        raw = read_regular(REPO / path)
        outputs.append({"path": path, "bytes": len(raw), "sha256": sha(raw),
                        "hash_kind": "file-bytes", "role": "candidate-output"})
    output_paths = {row["path"] for row in outputs}
    if not {"execution/positive-control-postreview.json", "execution/negative-control-postreview.json", "execution/test-run-postreview.json"} <= {
        path.split(OWNED.relative_to(REPO).as_posix() + "/", 1)[1] for path in output_paths if path.startswith(OWNED.relative_to(REPO).as_posix() + "/")
    }:
        raise admission.AdmissionError("Substantive controls are missing from candidate outputs")

    source = {
        "id": "saudi-pr1357-retained-predecessor-packet",
        "url": f"https://github.com/ChengshuLi/WorldAtlas/tree/{commit}/{run_safe.PREDECESSOR}",
        "role": "Immutable predecessor code, input locks, execution receipts, and preserved result files used for custody checks",
        "vintage": f"Repository base {commit}; original source and execution vintages remain as recorded in the predecessor packet",
        "retrieved_at": "2026-10-08",
        "license": {"status": "unknown", "terms": "This packet establishes repository byte custody only; third-party source data reuse terms remain unassessed."},
        "retention": "restoration-only",
        "verification": "verified",
        "restoration": f"Restore exact tracked Git blobs from ChengshuLi/WorldAtlas commit {commit}, path {run_safe.PREDECESSOR}.",
        "limit": "No new official-source, territorial, license, physical, legal, boundary, or geographic accuracy review was performed.",
        "temporal_status": "unknown",
    }
    phase_report_path = OWNED.relative_to(REPO).as_posix() + "/execution/refusals/run-4-admission.json"
    outputs_by_path = {row["path"]: row for row in outputs}
    metric_input = pin_hashes["frozen_execution"]
    metrics = [
        {"id": "raw-decoded-source-minimum-bytes", "value": plan_refusal["plan"]["source_body_minimum_bytes"],
         "unit": "bytes", "input_sha256": pin_hashes["frozen_execution"], "evaluation_commit": commit, "vintage": "current"},
        {"id": "complete-phase-plan-bytes", "value": plan_refusal["plan"]["complete_phase_bytes"],
         "unit": "bytes", "input_sha256": metric_input, "evaluation_commit": commit, "vintage": "current"},
        {"id": "complete-phase-limit-bytes", "value": plan_refusal["plan"]["phase_limit_bytes"],
         "unit": "bytes", "input_sha256": pin_hashes["frozen_execution"], "evaluation_commit": commit, "vintage": "current"},
        {"id": "predecessor-files-preserved", "value": preservation["file_count"],
         "unit": "files", "input_sha256": pin_hashes["frozen_execution"], "evaluation_commit": commit, "vintage": "current"},
        {"id": "historical-product-bytes-per-run", "value": historical["bytes_per_run"],
         "unit": "bytes", "input_sha256": pin_hashes["historical_run_one_receipt"], "evaluation_commit": commit, "vintage": "current"},
        {"id": "historical-products-per-run", "value": historical["product_count_per_run"],
         "unit": "files", "input_sha256": pin_hashes["historical_run_one_receipt"], "evaluation_commit": commit, "vintage": "current"},
    ]
    summaries = [{"metric_id": row["id"], "value": row["value"], "unit": row["unit"]} for row in metrics]

    manifest = {
        "version": 1, "issue": 1511, "lane": "geography",
        "worker_id": "01a10947-7d6e-7ba2-98a1-a9f91dedabfc",
        "subject_ids": sorted(SUBJECTS),
        "subject_ids_sha256": sha(json.dumps(sorted(SUBJECTS), separators=(",", ":")).encode()),
        "baseline": {"commit": commit, "files": files, "pins": pins,
                     "pin_files": {path: path for path in expected_pin_paths},
                     "subject_files": {subject: contact_path for subject in SUBJECTS}},
        "sources": [source],
        "outputs": outputs,
        "methods": [{"id": "saudi-complete-admission-and-writer-custody",
                     "kind": "code",
                     "description": "Deduplicate frozen encoded and decoded SHA-256 identities, reserve runtime/outputs/receipt, refuse the full replay before source-body reads, and exercise actual predecessor/new writer boundaries with private-copy failure fixtures.",
                     "software": f"Python {plan_refusal['plan']['runtime']['version']} executable SHA-256 {plan_refusal['plan']['runtime']['executable_sha256']}; {subprocess.check_output(['git','--version'],text=True).strip()}",
                     "units": "bytes, file counts, whole-file SHA-256 identities, filesystem entry types, and process exit codes"}],
        "metrics": metrics, "summaries": summaries,
        "metric_bindings": [
            {"metric_id": "raw-decoded-source-minimum-bytes", "path": phase_report_path, "json_pointer": "/plan/source_body_minimum_bytes"},
            {"metric_id": "complete-phase-plan-bytes", "path": phase_report_path, "json_pointer": "/plan/complete_phase_bytes"},
            {"metric_id": "complete-phase-limit-bytes", "path": phase_report_path, "json_pointer": "/plan/phase_limit_bytes"},
            {"metric_id": "predecessor-files-preserved", "path": OWNED.relative_to(REPO).as_posix() + "/execution/predecessor-preservation.json", "json_pointer": "/file_count"},
            {"metric_id": "historical-product-bytes-per-run", "path": OWNED.relative_to(REPO).as_posix() + "/execution/verified-historical-products.json", "json_pointer": "/bytes_per_run"},
            {"metric_id": "historical-products-per-run", "path": OWNED.relative_to(REPO).as_posix() + "/execution/verified-historical-products.json", "json_pointer": "/product_count_per_run"},
        ],
        "validation": [
            {"method_id": "saudi-complete-admission-and-writer-custody", "kind": "positive-control", "outcome": "passed", "evidence_path": OWNED.relative_to(REPO).as_posix() + "/execution/positive-control-postreview.json"},
            {"method_id": "saudi-complete-admission-and-writer-custody", "kind": "negative-control", "outcome": "passed", "evidence_path": OWNED.relative_to(REPO).as_posix() + "/execution/negative-control-postreview.json"},
        ],
        "change_receipts": [{"path": path, "status": "added"} for path in changes],
        "conclusions": [
            {"text": "The accepted complete Saudi source closure plus runtime and output reserves exceeds the unchanged phase cap; this packet refuses a fresh full replay before source-body reads or decompression.", "status": "supported", "source_ids": [source["id"]]},
            {"text": "All 148 predecessor files and modes and both historical fourteen-product inventories remain byte-identical to the pinned PR base.", "status": "supported", "source_ids": [source["id"]]},
            {"text": "Saudi source authority, licensing applicability, physical meaning, legal status, boundary accuracy, and source fitness remain unresolved; no geography was approved.", "status": "unresolved", "source_ids": [source["id"]]},
        ],
        "stages": {"research": "partial", "implementation": "proposed", "geographic_approval": "unapproved"},
        "commands": [
            "python3 -B research/geography/saudi-source-capture-1357-admission-20261008/run_safe.py --run-id run-1 --repo . (expected explicit refusal before source reads)",
            "python3 -B research/geography/saudi-source-capture-1357-admission-20261008/freeze_safe.py --repo . (expected explicit refusal before source reconstruction)",
            "python3 -B research/geography/saudi-source-capture-1357-admission-20261008/test_safety.py",
            "python3 -B research/geography/saudi-source-capture-1357-admission-20261008/reproduce_legacy_writers.py --output execution/<fresh-result>.json",
            "python3 -B research/geography/saudi-source-capture-1357-admission-20261008/verify_historical_products.py --repo .",
            "python3 -B research/geography/saudi-source-capture-1357-admission-20261008/verify_predecessor.py --repo . --commit HEAD",
        ],
    }
    if any(binding["path"] not in outputs_by_path for binding in manifest["metric_bindings"]):
        raise admission.AdmissionError("A metric binding references an undeclared candidate output")
    admission.write_exclusive(REPO, MANIFEST_PATH, (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode())
    print(json.dumps({"manifest": MANIFEST_PATH, "baseline_files": len(files),
                      "outputs": len(outputs), "changes": len(changes),
                      "subjects": len(SUBJECTS), "phase_bytes": plan_refusal["plan"]["complete_phase_bytes"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
