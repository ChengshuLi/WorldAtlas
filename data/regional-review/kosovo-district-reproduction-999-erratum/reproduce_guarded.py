#!/usr/bin/env python3
"""Guarded, additive reproduction for the exact #999 Kosovo packet."""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

OWNED = Path("data/regional-review/kosovo-district-reproduction-999-erratum")
PIN_FILE = OWNED / "pinned-inputs.json"
PIN_FILE_SHA256 = "5fe937bbd7ff6d2dafe0d8dd84757a79e0a55171e4e281b36fdc081b2af6285a"
EXPECTED_REPORT = "7339a45153c1a7e6f7c594b6c87be2f8b6294e7407ec63ab2598c839bb4cc5e7"
OLD_SCRIPT = Path("data/regional-review/followup-kosovo-422-district-source-20261005/reproduce.py")
KAS_PATH = Path("data/regional-review/followup-kosovo-422-district-source-20261005/kas-statistical-regions.json")
PACKET = Path("data/regional-review/followup-kosovo-422-district-source-20261005")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def pinned_descriptors() -> list[dict]:
    raw = PIN_FILE.read_bytes()
    if sha(raw) != PIN_FILE_SHA256:
        raise ValueError("pinned input descriptor file changed")
    doc = json.loads(raw)
    if doc.get("issue") != 1170 or doc.get("source_issue") != 999 or len(doc.get("inputs", [])) != 23:
        raise ValueError("wrong packet or incomplete pinned descriptor set")
    return doc["inputs"]


def read_inputs(repo: Path, overrides: dict[str, bytes] | None = None,
                descriptor_mutation: dict | None = None) -> dict[str, bytes]:
    descriptors = pinned_descriptors()
    if descriptor_mutation:
        descriptors = [dict(x, **descriptor_mutation) if x["path"] == descriptor_mutation.get("target") else x for x in descriptors]
    inputs: dict[str, bytes] = {}
    for item in descriptors:
        key = f'{item["commit"]}:{item["path"]}'
        if item["path"] in (overrides or {}):
            raw = overrides[item["path"]]
        else:
            try:
                raw = subprocess.check_output(["git", "show", key], cwd=repo, stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError as exc:
                raise ValueError(f"pinned baseline unavailable: {key}") from exc
        if len(raw) != item["bytes"] or sha(raw) != item["sha256"]:
            raise ValueError(f"pinned input mismatch: {key}")
        inputs[item["path"]] = raw
    if len(inputs) != 23 or str(OLD_SCRIPT) not in inputs:
        raise ValueError("wrong packet input set")
    return inputs


def reproduce(repo: Path, output: Path, overrides: dict[str, bytes] | None = None,
              descriptor_mutation: dict | None = None) -> dict:
    repo = repo.resolve()
    output = output.resolve()
    owned_abs = (repo / OWNED).resolve()
    if owned_abs not in output.parents:
        raise ValueError("output must be within the issue-owned path")
    if output.exists():
        raise FileExistsError(f"refusing existing output: {output}")
    # Complete byte validation precedes any output creation.
    inputs = read_inputs(repo, overrides, descriptor_mutation)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".kosovo-999-guard-", dir=repo) as tmp:
        stage = Path(tmp)
        for rel, raw in inputs.items():
            dest = stage / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
        # Run the exact hash-verified historical implementation only in this
        # private staging tree. git show resolves the pinned original commit in
        # the enclosing worktree; historical paths here are never writable.
        subprocess.run(["python3", str(OLD_SCRIPT), "--root", str(stage)], cwd=stage, check=True, capture_output=True, text=True)
        report = stage / PACKET / "source-crosswalk.json"
        raw_report = report.read_bytes()
        if len(raw_report) != 10417 or sha(raw_report) != EXPECTED_REPORT:
            original = inputs[str(PACKET / "source-crosswalk.json")]
            diff = "".join(list(difflib.unified_diff(original.decode().splitlines(True), raw_report.decode().splitlines(True)))[:30])
            raise ValueError(f"historical report differs from immutable bytes: {len(raw_report)} bytes sha256 {sha(raw_report)}\n{diff}")
        # Exclusive create makes overwrites impossible; output remains issue-owned.
        with output.open("xb") as f:
            f.write(raw_report)
    return {"output": str(output.relative_to(repo)), "bytes": len(raw_report), "sha256": sha(raw_report),
            "pinned_input_count": len(inputs), "staged_baseline": "96f2a6d201236ba62f471535db240b123de60c09",
            "source_feature_count": 7, "issue_999_subject_count": 3, "issue_1008_context_count": 4,
            "kas_statistical_region_count": 7, "kas_municipality_name_count": 38,
            "interpretation": "name correspondence only; no geometry equivalence or legal/reuse approval"}


def self_test(repo: Path) -> dict:
    base = read_inputs(repo)
    issue_doc = json.loads(base[str(PACKET / "github-issue-contract.json")])
    match = re.search(r"<!-- worldatlas-work:v1\s*\n([\s\S]*?)\n-->", issue_doc["body"])
    if not match:
        raise AssertionError("pinned #999 contract block is absent")
    subject_ids = set(json.loads(match.group(1))["evidence_quality"]["subject_ids"])
    related_ids = set(json.loads(base[str(PACKET / "related-scope-1008.json")])["subject_ids"])
    report_doc = json.loads(base[str(PACKET / "source-crosswalk.json")])
    actual_ids = {row["source_id"] if "source_id" in row else f"gb:XKX:ADM1:{row['shape_id']}"
                  for row in report_doc["features"]}
    if len(subject_ids) != 3 or len(related_ids) != 4 or subject_ids & related_ids or subject_ids | related_ids != actual_ids or len(actual_ids) != 7:
        raise AssertionError("the exact three-plus-four issue partition does not match the seven source IDs")
    if report_doc["source_feature_count"] != 7 or report_doc["issue_subject_count"] != 3:
        raise AssertionError("pinned crosswalk metrics disagree with exact subject partition")
    cases = {}
    for label, path, mutate in [
        ("changed_transcription", str(KAS_PATH), lambda b: b.replace(b"Gllogoc", b"AUDITOR_SYNTHETIC_MUNICIPALITY", 1)),
        ("changed_runner_code", str(OLD_SCRIPT), lambda b: b + b"\n# drift\n"),
        ("transcription_name_drift", str(KAS_PATH), lambda b: b.replace(b"Gllogoc", b"Glogovac", 1)),
    ]:
        altered = dict(base)
        altered[path] = mutate(altered[path])
        try:
            read_inputs(repo, altered)
            raise AssertionError(f"{label} unexpectedly passed")
        except ValueError as exc:
            if "pinned input mismatch" not in str(exc):
                raise
            cases[label] = {"rejected": True, "before_output": True, "reason": str(exc)}
    try:
        read_inputs(repo, descriptor_mutation={"target": str(OLD_SCRIPT), "commit": "0" * 40})
        raise AssertionError("wrong baseline unexpectedly passed")
    except ValueError as exc:
        cases["wrong_baseline"] = {"rejected": True, "before_output": True, "reason": str(exc)}
    try:
        read_inputs(repo, descriptor_mutation={"target": str(KAS_PATH), "path": str(PACKET / "REPLACED-KAS.json")})
        raise AssertionError("wrong packet path unexpectedly passed")
    except ValueError as exc:
        cases["wrong_packet_path"] = {"rejected": True, "before_output": True, "reason": str(exc)}
    # Recreate the documented complete-file boundary change without editing any input.
    synthetic = base[str(KAS_PATH)].replace(b"Gllogoc", b"AUDITOR_SYNTHETIC_MUNICIPALITY", 1)
    with tempfile.TemporaryDirectory(prefix=".kosovo-999-drift-", dir=repo) as tmp:
        stage = Path(tmp)
        for rel, raw in base.items():
            dest = stage / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(synthetic if rel == str(KAS_PATH) else raw)
        old_copy = stage / OLD_SCRIPT
        subprocess.run(["python3", str(old_copy), "--root", str(stage)], cwd=stage, check=True, capture_output=True, text=True)
        drift_output = json.loads((stage / PACKET / "source-crosswalk.json").read_bytes())
        drift_names = [name for region in drift_output["kas_regions"] for name in region["municipalities"]]
        if "AUDITOR_SYNTHETIC_MUNICIPALITY" not in drift_names or len(drift_names) != 38:
            raise AssertionError("historical reproducer no longer demonstrates the documented drift")
        cases["historical_runner_accepts_name_drift"] = {"accepted_by_old_runner": True,
            "emitted_synthetic_name": True, "municipality_name_count": len(drift_names),
            "private_output_sha256": sha((stage / PACKET / "source-crosswalk.json").read_bytes())}
    fd, destination_name = tempfile.mkstemp(prefix=".control-existing-", dir=repo / OWNED)
    destination = Path(destination_name)
    try:
        with os.fdopen(fd, "wb") as existing:
            existing.write(b"preserve me")
        try:
            reproduce(repo, destination)
            raise AssertionError("existing output unexpectedly passed")
        except FileExistsError:
            cases["existing_output"] = {"rejected": True, "preserved_sha256": sha(destination.read_bytes())}
    finally:
        destination.unlink()
    return {"scope_accounting": {"issue_999_subject_ids": sorted(subject_ids),
            "issue_1008_read_only_context_ids": sorted(related_ids), "source_feature_ids": sorted(actual_ids),
            "partition_verified": True}, "controls": cases, "synthetic_fixture": {"bytes": len(synthetic), "sha256": sha(synthetic),
            "changed_name": "AUDITOR_SYNTHETIC_MUNICIPALITY", "original_name": "Gllogoc",
            "issue_receipt": {"bytes": 2340, "sha256": "34ed4c2393dbea07e64cfe00728eccf69611f7137cc86c24d5c49f121a18effd"},
            "receipt_note": "The issue provides the prior complete-probe size/hash but not the complete fixture bytes; this fixture applies the specified one-name replacement to the pinned transcription."}}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    repo = args.root.resolve()
    if args.self_test:
        print(json.dumps(self_test(repo), indent=2))
    print(json.dumps(reproduce(repo, args.output, overrides=None), indent=2))


if __name__ == "__main__":
    main()
