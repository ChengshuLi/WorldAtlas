#!/usr/bin/env python3
"""Build the exact issue-bound whole-file evidence manifest after reproductions."""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess

from safe_outputs import (
    EVALUATION_COMMIT, EVIDENCE_PATH, IMMUTABLE_PATH, IMMUTABLE_SHA256,
    ISSUE, ISSUE_SNAPSHOT, ORIGINAL_MERGE, OWNED_PATH, SOURCE_PINS, WORKER_ID,
    current_commit, git,
)

REPO = Path(__file__).resolve().parents[3]
MANIFEST_REL = OWNED_PATH + "evidence-quality.json"
RUN_ONE = EVIDENCE_PATH + "vintages/generator-integrity-erratum/runs/2026-10-07/run-1/assessments.json.gz"
RUN_TWO = EVIDENCE_PATH + "vintages/generator-integrity-erratum/runs/2026-10-07/run-2/assessments.json.gz"


def descriptor(path: str, commit: str, raw: bytes, *, role=None, decode_gzip=False):
    row = {"path": path, "bytes": len(raw),
           "sha256": hashlib.sha256(raw).hexdigest(), "hash_kind": "file-bytes"}
    if commit != "candidate":
        row["commit"] = commit
    if role:
        row["role"] = role
    if decode_gzip:
        unpacked = gzip.decompress(raw)
        if len(unpacked) > 32 * 1024 * 1024:
            raise ValueError("Decoded candidate exceeds the 32 MiB evidence-file limit")
        row.update(uncompressed_bytes=len(unpacked), uncompressed_sha256=hashlib.sha256(unpacked).hexdigest())
    return row


def main():
    issue = json.loads((REPO / ISSUE_SNAPSHOT).read_bytes())
    work = re.search(r"<!-- worldatlas-work:v1\s*(\{[\s\S]*?\})\s*-->", issue["body"])
    if issue.get("number") != ISSUE or not work:
        raise ValueError("Issue snapshot lacks the exact #1485 work contract")
    contract = json.loads(work.group(1))
    quality = contract["evidence_quality"]
    ids = quality["subject_ids"]
    expected_pins = quality["pins"]
    origin_main = git(REPO, "rev-parse", "origin/main").decode().strip()
    branch_head = current_commit(REPO)
    if git(REPO, "merge-base", origin_main, branch_head).decode().strip() != origin_main:
        raise ValueError("The packet branch must descend from the verified origin/main base")
    validation = json.loads((REPO / OWNED_PATH / "validation/adversarial-controls-head088ab2.json").read_bytes())
    if (validation.get("repository_head") != origin_main or
            validation.get("output_safety_baseline") != origin_main):
        raise ValueError("Final reproduction must be tied to the current origin/main base")
    commit = origin_main
    if contract.get("owned_paths") != [OWNED_PATH] or contract.get("max_prs") != 2:
        raise ValueError("Current issue path or PR allowance differs from the reviewed contract")

    # Bind the issue contract pins to the original #1319 merge and independently
    # verify their exact current PR-base copies consumed by the new runner.
    files = []
    seen = set()
    pin_files = {}
    pins = dict(expected_pins)
    for path, expected in expected_pins.items():
        historical = git(REPO, "show", f"{ORIGINAL_MERGE}:{path}")
        current = git(REPO, "show", f"{commit}:{path}")
        if any(hashlib.sha256(raw).hexdigest() != expected for raw in (historical, current)):
            raise ValueError(f"Issue pin drift at its original/current whole-file vintage: {path}")
        for revision, raw in ((ORIGINAL_MERGE, historical), (commit, current)):
            key = (revision, path)
            if key not in seen:
                seen.add(key)
                files.append(descriptor(path, revision, raw, role="original-source"))
        pin_files[path] = {"path": path, "commit": ORIGINAL_MERGE}

    # The exact evidence helper and source inputs used by the new adapters are
    # pinned independently to the reviewed PR-base/source-evaluation vintages.
    additional = {IMMUTABLE_PATH: (commit, IMMUTABLE_SHA256)}
    for path, (revision, expected) in additional.items():
        raw = git(REPO, "show", f"{revision}:{path}")
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError(f"Additional exact source/helper pin drift: {revision}:{path}")
        key = (revision, path)
        if key not in seen:
            seen.add(key)
            files.append(descriptor(path, revision, raw, role="original-source"))
        pins[path] = expected
        pin_files[path] = {"path": path, "commit": revision}

    for path, expected in SOURCE_PINS.items():
        for revision in (EVALUATION_COMMIT, commit):
            raw = git(REPO, "show", f"{revision}:{path}")
            if hashlib.sha256(raw).hexdigest() != expected:
                raise ValueError(f"Source input differs across its actual vintages: {revision}:{path}")
            key = (revision, path)
            if key not in seen:
                seen.add(key)
                files.append(descriptor(path, revision, raw, role="original-source"))
        pins[path] = expected
        pin_files[path] = {"path": path, "commit": EVALUATION_COMMIT}

    # Bind the complete original evaluated file set at its true historical
    # commit; encoded files are checked whole. The oversized decoded source is
    # intentionally not unpacked or described as byte-verified here.
    eval_path = EVIDENCE_PATH + "vintages/generator-integrity-erratum/evaluation-inputs.json"
    eval_bytes = git(REPO, "show", f"{ORIGINAL_MERGE}:{eval_path}")
    eval_spec = json.loads(eval_bytes)
    if eval_spec.get("evaluation_commit") != EVALUATION_COMMIT:
        raise ValueError("Original evaluation manifest points to a different commit")
    for input_file in eval_spec["inputs"]:
        path = input_file["path"]
        raw = git(REPO, "show", f"{EVALUATION_COMMIT}:{path}")
        if len(raw) != input_file["bytes"] or hashlib.sha256(raw).hexdigest() != input_file["sha256"]:
            raise ValueError(f"Original complete evaluation input mismatch: {path}")
        key = (EVALUATION_COMMIT, path)
        if key not in seen:
            seen.add(key)
            files.append(descriptor(path, EVALUATION_COMMIT, raw, role="original-source"))

    # Exact current-base IDs in geographic part files are the identity custody
    # source; the original source/crosswalk conclusions themselves remain those
    # of the preserved retained report.
    by_subject = {}
    subject_paths = [f"data/geography/part-{n}.json" for n in (30, 31, 32, 33)]
    for path in subject_paths:
        raw = git(REPO, "show", f"{EVALUATION_COMMIT}:{path}")
        file_descriptor = next((item for item in files if item["path"] == path and item["commit"] == EVALUATION_COMMIT), None)
        if file_descriptor is None or file_descriptor["sha256"] != hashlib.sha256(raw).hexdigest():
            raise ValueError(f"Subject containing file not in the exact historical input inventory: {path}")
        rows = json.loads(raw).get("features", [])
        for feature in rows:
            identity = feature.get("id") or feature.get("properties", {}).get("id")
            if identity in ids:
                if identity in by_subject:
                    raise ValueError(f"Duplicate scoped subject occurs in two parts: {identity}")
                by_subject[identity] = {"path": path, "commit": EVALUATION_COMMIT}
        current_raw = git(REPO, "show", f"{commit}:{path}")
        current_key = (commit, path)
        if current_key not in seen:
            seen.add(current_key)
            files.append(descriptor(path, commit, current_raw, role="original-source"))
    if set(by_subject) != set(ids):
        raise ValueError(f"Subject roster differs: found {len(by_subject)} of {len(ids)}")

    outputs = []
    output_paths = []
    for path in sorted((REPO / OWNED_PATH).rglob("*")):
        if not path.is_file() or path.is_symlink() or path.resolve() != path:
            continue
        relative = path.relative_to(REPO).as_posix()
        if relative == MANIFEST_REL:
            continue
        raw = path.read_bytes()
        outputs.append(descriptor(relative, "candidate", raw, decode_gzip=relative.endswith(".gz")))
        output_paths.append(relative)
    if not outputs:
        raise ValueError("No candidate outputs found")

    # Results are historical measurements over a preserved report; they are
    # explicitly labeled archived and tied to the retained corrected result.
    run_descriptor = next(item for item in files if item["path"] == RUN_ONE and item["commit"] == ORIGINAL_MERGE)
    metrics = [
        {"id": "retained_subjects", "value": 224, "unit": "subjects", "vintage": "archived",
         "input_sha256": run_descriptor["sha256"], "evaluation_commit": ORIGINAL_MERGE,
         "input_file": {"path": RUN_ONE, "commit": ORIGINAL_MERGE}},
        {"id": "retained_province_groups", "value": 27, "unit": "groups", "vintage": "archived",
         "input_sha256": run_descriptor["sha256"], "evaluation_commit": ORIGINAL_MERGE,
         "input_file": {"path": RUN_ONE, "commit": ORIGINAL_MERGE}},
        {"id": "corrected_fields", "value": 16, "unit": "fields", "vintage": "archived",
         "input_sha256": run_descriptor["sha256"], "evaluation_commit": ORIGINAL_MERGE,
         "input_file": {"path": RUN_ONE, "commit": ORIGINAL_MERGE}},
        {"id": "source_metadata_count_difference", "value": 14, "unit": "units", "vintage": "archived",
         "input_sha256": pins["data/global-sources/IND-ADM3-metadata.json"],
         "evaluation_commit": EVALUATION_COMMIT,
         "input_file": {"path": "data/global-sources/IND-ADM3-metadata.json", "commit": EVALUATION_COMMIT}},
    ]
    summaries = [{"metric_id": row["id"], "value": row["value"], "unit": row["unit"]} for row in metrics]
    binding_base = OWNED_PATH + "vintages/controls-head088ab2-one/summary.json"
    metric_bindings = [
        {"metric_id": "retained_subjects", "path": binding_base, "json_pointer": "/subjects"},
        {"metric_id": "retained_province_groups", "path": binding_base, "json_pointer": "/province_groups"},
        {"metric_id": "corrected_fields", "path": binding_base, "json_pointer": "/corrected_fields"},
        {"metric_id": "source_metadata_count_difference", "path": binding_base, "json_pointer": "/geoboundaries_count_difference"},
    ]
    method_id = "safe-output-admission"
    manifest = {
        "version": 1, "issue": ISSUE, "lane": "geography", "worker_id": WORKER_ID,
        "subject_ids": ids, "subject_ids_sha256": hashlib.sha256(json.dumps(sorted(ids), separators=(",", ":")).encode()).hexdigest(),
        "baseline": {"version": 2, "commit": commit, "files": files, "pins": pins,
                     "pin_files": pin_files, "subject_files": by_subject},
        "sources": [
            {"id": "geoBoundaries-IND-ADM3-2018", "url": "https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09/releaseData/gbOpen/IND/ADM3/geoBoundaries-IND-ADM3_simplified.geojson",
             "role": "Retained source identity and report context only; no new geometry analysis in this erratum",
             "vintage": "2018 boundary representation; metadata update 2023-01-19, build 2023-12-12; original inventory",
             "retrieved_at": "2026-10-08 (pinned repository inventory rechecked; no upstream retrieval)",
             "license": {"status": "unknown", "terms": "Original inventory declares ODbL 1.0 and attribution to Pathways Data Pvt. Ltd. and LG Directory; this erratum did not independently assess applicable release/reuse terms."},
             "retention": "restoration-only", "verification": "unverified", "temporal_status": "unknown",
             "restoration": f"Use the exact original compressed source at {EVALUATION_COMMIT}:data/global-sources/IND-ADM3.geojson.gz (SHA-256 {SOURCE_PINS['data/global-sources/IND-ADM3.geojson.gz']}) and its pinned metadata; no new source capture was made.",
             "limit": "Territorial meaning, legal/current boundary correspondence, neighboring granularity, completeness and reuse terms were not re-adjudicated. Declared decoded source size is 40,040,002 bytes, above the 32 MiB limit, so no fresh geometry replay was performed."},
            {"id": "igod-agar-malwa-current-admin-roster-2026-10-05", "url": "https://igod.gov.in/district/7Tg3tXQBW7DqAzx4Vryt/sub_districts",
             "role": "Administrative names crosswalk underlying four retained Agar roster bindings; not polygon or jurisdiction evidence",
             "vintage": "2026-10-05 capture recorded in original source inventory",
             "retrieved_at": "2026-10-05",
             "license": {"status": "unknown", "terms": "Original inventory records that no page-specific reuse terms were identified; raw HTML was not retained."},
             "retention": "restoration-only", "verification": "unverified", "temporal_status": "unknown",
             "restoration": "Use the exact URL and capture hash recorded in the pinned original current-admin-rosters.json and source-inventory.json; the retained assessment rows preserve the four linked names. Request a lawful current export before any new source use.",
             "limit": "The retained names do not establish current jurisdiction, polygon membership, full district roster completeness or legal boundaries."},
        ],
        "outputs": outputs,
        "methods": [
            {"id": method_id, "kind": "generator", "helper_version": "worldatlas-evidence-preparation-v1",
             "description": "Complete output-set preflight plus immutable shared-helper publication and receipt-last control. The producer CLI republishes complete retained report bytes only; the control CLI independently compares every retained subject row and province assessment.",
             "software": "Python 3.12.14; pinned scripts/evidence/immutable.py SHA-256 " + IMMUTABLE_SHA256,
             "units": "whole-file bytes, SHA-256 digests, 224 subject rows, 27 province groups and changed fields"},
            {"id": "retained-row-comparison", "kind": "code",
             "description": "Complete join of the retained original and corrected 224-row reports, preserving row order and all 27 province-level assessments; no geometry or source-currentness inference.",
             "software": "Python 3.12.14; control_writer.py", "units": "rows, groups and field values"},
        ],
        "metrics": metrics, "summaries": summaries,
        "metric_bindings": metric_bindings,
        "validation": [
            {"method_id": method_id, "kind": "positive-control", "outcome": "passed",
             "evidence_path": OWNED_PATH + "vintages/controls-head088ab2-one/positive-control.json"},
            {"method_id": method_id, "kind": "negative-control", "outcome": "passed",
             "evidence_path": OWNED_PATH + "vintages/controls-head088ab2-one/negative-control.json"},
            {"method_id": method_id, "kind": "reproducibility", "outcome": "passed",
             "evidence_path": OWNED_PATH + "vintages/controls-head088ab2-one/reproducibility.json"},
        ],
        "change_receipts": ([{"path": path, "status": "added"} for path in output_paths] +
                             [{"path": MANIFEST_REL, "status": "added"}]),
        "rendered_tables": [],
        "conclusions": [
            {"text": "The output-safety repair has fresh, exclusive retained-report vintages with complete final receipts; it does not freshly reproduce the original geometry calculation.",
             "status": "supported", "source_ids": ["geoBoundaries-IND-ADM3-2018"]},
            {"text": "The 2018 subdistrict data boundary meaning, current legal correspondence, completeness, reuse applicability and adjacent granularity remain unresolved.",
             "status": "unresolved", "source_ids": ["geoBoundaries-IND-ADM3-2018"]},
            {"text": "The four Agar IGOD name bindings remain administrative crosswalk evidence; they do not establish polygon membership or jurisdiction, and page reuse terms remain unestablished.",
             "status": "unresolved", "source_ids": ["igod-agar-malwa-current-admin-roster-2026-10-05"]},
            {"text": "Sheopur remains without a retained current roster source; the 6,822/6,836 source-feature discrepancy remains unresolved.",
             "status": "unresolved", "source_ids": ["geoBoundaries-IND-ADM3-2018"]},
        ],
        "stages": {"research": "partial", "implementation": "not-proposed", "geographic_approval": "unapproved"},
        "commands": [
            "python3.12 -B research/geography/madhya-pradesh-output-preservation-1319-20261008/producer_republish.py --run-id producer-head088ab2-one",
            "python3.12 -B research/geography/madhya-pradesh-output-preservation-1319-20261008/producer_republish.py --run-id producer-head088ab2-two",
            "python3.12 -B research/geography/madhya-pradesh-output-preservation-1319-20261008/control_writer.py --run-id controls-head088ab2-one",
            "python3.12 -B research/geography/madhya-pradesh-output-preservation-1319-20261008/control_writer.py --run-id controls-head088ab2-two",
            "python3.12 -B research/geography/madhya-pradesh-output-preservation-1319-20261008/test_output_safety.py --tag head088ab2",
            "node scripts/evidence-quality.mjs research/geography/madhya-pradesh-output-preservation-1319-20261008/evidence-quality.json",
        ],
    }

    output = REPO / MANIFEST_REL
    raw = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    output.write_bytes(raw)
    print(json.dumps({"manifest": MANIFEST_REL, "bytes": len(raw), "subjects": len(ids),
                      "baseline_files": len(files), "outputs": len(outputs), "pins": len(pins)}, sort_keys=True))


if __name__ == "__main__":
    main()
