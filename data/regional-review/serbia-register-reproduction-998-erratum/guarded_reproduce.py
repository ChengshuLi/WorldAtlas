#!/usr/bin/env python3
"""Fail-closed, additive reproduction for the Serbia #998 register crosswalk.

All 35 complete baseline/packet files and the exact issue snapshots are checked
before generation. Results are built in private staging and atomically published
only to a new caller-named output directory. No retained packet file is written.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Callable

ROOT = Path(__file__).resolve().parent
PIN_FILE = ROOT / "source" / "pinned-inputs.json"
ISSUE_FILE = ROOT / "source" / "issue-1175.json"
PIN_FILE_SHA256 = "d7fe852b5526594c609fef50ccb2223da6e4c84076c355da37958bd4a40b9a3c"
ISSUE_NUMBER = 1175
TARGET_PACKET = "data/regional-review/followup-serbia-422-admin-crosswalk-20261005"
PRIOR_PACKET = "data/regional-review/regional-review-3c4fe25a21fa428d"
EXPECTED_OUTPUTS = {
    "parent-completeness.csv",
    "parent-completeness.json",
    "parent-summary.json",
    "reproduction-summary.json",
    "scoped-city-urban-municipalities.csv",
    "sors-2017-roster-normalized.csv",
    "sors-current-roster-normalized.csv",
    "subject-crosswalk.csv",
}


class GuardError(RuntimeError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_contract(issue: dict) -> dict:
    match = re.search(r"<!-- worldatlas-work:v1\s*(\{.*?\})\s*-->", issue.get("body", ""), re.S)
    if not match:
        raise GuardError("issue is missing its worldatlas-work:v1 contract")
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise GuardError(f"issue contract is not valid JSON: {exc}") from exc


def issue_table_inputs(body: str) -> list[dict]:
    rows = []
    for line in body.splitlines():
        match = re.match(r"^\| \x60([0-9a-f]{40})\x60 \| \x60([^\x60]+)\x60 \| (\d+) \| \x60([0-9a-f]{64})\x60 \|$", line)
        if match:
            commit, path, size, digest = match.groups()
            rows.append({"commit": commit, "path": path, "bytes": int(size), "sha256": digest, "hash_kind": "file-bytes"})
    return rows


def validate_subject_list(actual: list[str], expected: list[str], description: str) -> None:
    if len(actual) != len(set(actual)):
        raise GuardError(f"{description} contains duplicate subject IDs")
    if actual != expected or len(actual) != 78:
        raise GuardError(f"{description} does not exactly match the ordered 78-subject scope")


def check_runtime() -> dict:
    try:
        import pandas
        import openpyxl
        import xlrd
    except ImportError as exc:
        raise GuardError(f"pinned reproduction dependency is unavailable: {exc}") from exc
    actual = {
        "python": sys.version.split()[0],
        "pandas": pandas.__version__,
        "xlrd": xlrd.__version__,
        "openpyxl": openpyxl.__version__,
    }
    actual["transitive"] = {
        name: importlib.metadata.version(name)
        for name in ("numpy", "python-dateutil", "pytz", "tzdata", "six", "et-xmlfile")
    }
    expected = {
        "python": "3.12.14", "pandas": "2.2.3", "xlrd": "2.0.2", "openpyxl": "3.1.5",
        "transitive": {"numpy": "2.5.3", "python-dateutil": "2.9.0.post0", "pytz": "2026.5",
                       "tzdata": "2026.5", "six": "1.17.0", "et-xmlfile": "2.0.0"},
    }
    if actual != expected:
        raise GuardError(f"reproduction runtime mismatch: expected {expected}, got {actual}")
    return actual


def load_pins(pin_bytes: bytes) -> dict:
    if sha256(pin_bytes) != PIN_FILE_SHA256:
        raise GuardError("pinned-inputs.json bytes differ from the guarded version")
    try:
        pins = json.loads(pin_bytes)
    except json.JSONDecodeError as exc:
        raise GuardError(f"pinned-inputs.json is invalid JSON: {exc}") from exc
    if pins.get("version") != 1 or len(pins.get("inputs", [])) != 35:
        raise GuardError("expected the immutable 35-file input inventory")
    if len(pins.get("subject_ids", [])) != 78 or len(set(pins["subject_ids"])) != 78:
        raise GuardError("pinned issue scope must contain exactly 78 unique subjects")
    if pins.get("baseline_commit") != "c944e017796005726150abef19763db9ffd07154":
        raise GuardError("unexpected immutable baseline commit")
    if pins.get("packet_commit") != "e5393834c715396a60967d366523712edd5d1b65":
        raise GuardError("unexpected immutable source packet commit")
    if len(pins.get("historical_outputs", [])) != 8:
        raise GuardError("expected all eight historical reproduction outputs")
    return pins


def git_blob(commit: str, path: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        raise GuardError(f"pinned Git object is unavailable: {commit}:{path}: {result.stderr.decode(errors='replace').strip()}")
    return result.stdout


def validate_snapshot(issue_bytes: bytes, pins: dict) -> dict:
    expected = pins["issue_snapshot"]
    if expected.get("number") != ISSUE_NUMBER or sha256(issue_bytes) != expected.get("sha256"):
        raise GuardError("captured #1175 issue bytes do not match the pinned snapshot")
    try:
        issue = json.loads(issue_bytes)
    except json.JSONDecodeError as exc:
        raise GuardError(f"captured #1175 issue is invalid JSON: {exc}") from exc
    if issue.get("number") != ISSUE_NUMBER or issue.get("state") != "open":
        raise GuardError("captured issue is not open #1175")
    label_names = {item["name"] for item in issue.get("labels", []) if isinstance(item, dict) and "name" in item}
    required = {"type:geography", "kind:work-item", "status:ready", "urgent"}
    if not required <= label_names:
        raise GuardError(f"captured issue is missing required labels: {sorted(required - label_names)}")
    contract = parse_contract(issue)
    if contract.get("mode") != "geography" or contract.get("depends_on") != [998]:
        raise GuardError("captured issue has unexpected mode or dependencies")
    if contract.get("owned_paths") != ["data/regional-review/serbia-register-reproduction-998-erratum/"]:
        raise GuardError("captured issue ownership differs from the reserved evidence path")
    validate_subject_list(contract.get("evidence_quality", {}).get("subject_ids", []), pins["subject_ids"], "captured #1175 roster")
    if issue_table_inputs(issue.get("body", "")) != pins["inputs"]:
        raise GuardError("captured issue input table differs from the immutable 35-file inventory")
    baseline_pins = contract.get("evidence_quality", {}).get("pins", {})
    for item in pins["inputs"]:
        if baseline_pins.get(f"{item['commit']}:{item['path']}") != item["sha256"]:
            raise GuardError(f"issue machine pins disagree for {item['commit']}:{item['path']}")
    return issue


def validate_issue_998(raw: bytes, target_ids: list[str], *, expected_state: str | None = None) -> dict:
    try:
        issue = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise GuardError(f"pinned #998 issue snapshot is invalid JSON: {exc}") from exc
    if issue.get("number") != 998:
        raise GuardError("source snapshot is not issue #998")
    if issue.get("state") not in {"open", "closed"} or (expected_state and issue.get("state") != expected_state):
        raise GuardError(f"issue #998 snapshot has unexpected state: {issue.get('state')}")
    contract = parse_contract(issue)
    if contract.get("mode") != "geography" or contract.get("depends_on") != [422]:
        raise GuardError("issue #998 has unexpected lane or dependency contract")
    original_ids = contract.get("evidence_quality", {}).get("subject_ids")
    if original_ids is None:
        original_ids = contract.get("subject_ids")
    validate_subject_list(original_ids or [], target_ids, "source #998 issue scope")
    return issue


def validate_subject_context(pins: dict, blobs: dict[str, bytes], target_ids: list[str]) -> None:
    assessment_path = f"{PRIOR_PACKET}/source/subject-assessments.json"
    geometry_path = f"{TARGET_PACKET}/sources/geoBoundaries-SRB-ADM2-2017.geojson"
    issue_path = f"{TARGET_PACKET}/source-issue-998.json"
    assessment = json.loads(blobs[assessment_path])
    geometry = json.loads(blobs[geometry_path])
    source_issue = json.loads(blobs[issue_path])
    validate_issue_998(blobs[issue_path], target_ids, expected_state="open")
    subjects = {row["location_id"]: row for row in assessment["subjects"]}
    if len(subjects) != len(assessment["subjects"]):
        raise GuardError("prior subject assessment contains duplicate location IDs")
    features = {}
    for feature in geometry.get("features", []):
        feature_id = feature.get("properties", {}).get("shapeID")
        if not feature_id or feature_id in features:
            raise GuardError("pinned source geometry has missing or duplicate shape IDs")
        features[feature_id] = feature
    if len(features) != 145:
        raise GuardError("pinned source geometry must contain exactly 145 unique features")
    if set(target_ids) - set(subjects):
        raise GuardError("exact #1175 scope contains subjects absent from the pinned prior assessment")
    for subject_id in target_ids:
        subject = subjects[subject_id]
        feature = features.get(subject["original_id"])
        if not feature or feature.get("properties", {}).get("shapeName") != subject["source_feature_name"]:
            raise GuardError(f"pinned source feature identity differs from prior evidence: {subject_id}")
    parent_ids = {subjects[subject_id]["parent_id"] for subject_id in target_ids}
    if len(parent_ids) != 13:
        raise GuardError(f"expected 13 Atlas parent contexts, got {len(parent_ids)}")
    source_metadata = json.loads(blobs[f"{PRIOR_PACKET}/source/gb/SRB-ADM2-geoBoundaries-SRB-ADM2-metaData.json"])
    if source_metadata.get("admUnitCount") != "145":
        raise GuardError("pinned geoBoundaries metadata count differs from the 145-feature collection")
    if not source_issue.get("body"):
        raise GuardError("pinned #998 issue body is empty")


def verify_all_inputs(
    pins: dict,
    reader: Callable[[str, str], bytes] = git_blob,
    issue_bytes: bytes | None = None,
) -> dict[str, bytes]:
    blobs: dict[str, bytes] = {}
    for item in pins["inputs"]:
        data = reader(item["commit"], item["path"])
        if len(data) != item["bytes"] or sha256(data) != item["sha256"]:
            raise GuardError(f"complete input hash/size mismatch: {item['commit']}:{item['path']}")
        blobs[item["path"]] = data
    # Use the shared immutable helper as a second check of the exact native
    # Atlas roster and its actual containing files across the pinned world index.
    repo_root = ROOT.parents[2]
    sys.path.insert(0, str(repo_root / "scripts"))
    from evidence.immutable import Baseline, VERSION as PREPARATION_HELPER_VERSION
    baseline_files = [
        {key: item[key] for key in ("path", "bytes", "sha256", "hash_kind")}
        for item in pins["inputs"] if item["commit"] == pins["baseline_commit"]
    ]
    baseline = Baseline(repo_root, pins["baseline_commit"], baseline_files)
    indexed, containing = baseline.subjects(pins["subject_ids"])
    expected_part = "data/geography/part-22.json"
    if set(indexed) != set(pins["subject_ids"]) or any(row["path"] != expected_part for row in containing.values()):
        raise GuardError("immutable world-index lookup disagrees with the declared 78-subject containing-file scope")
    if PREPARATION_HELPER_VERSION != "worldatlas-evidence-preparation-v1":
        raise GuardError("unexpected immutable-evidence helper version")
    generator = pins["original_generator"]
    code = reader(generator["commit"], generator["path"])
    if len(code) != generator["bytes"] or sha256(code) != generator["sha256"]:
        raise GuardError("pinned historical reproduction code hash/size mismatch")
    if issue_bytes is None:
        issue_bytes = ISSUE_FILE.read_bytes()
    issue = validate_snapshot(issue_bytes, pins)
    source_issue = validate_issue_998(
        blobs[f"{TARGET_PACKET}/source-issue-998.json"],
        pins["subject_ids"],
    )
    if issue.get("number") != ISSUE_NUMBER or source_issue.get("number") != 998:
        raise GuardError("issue identity check failed")
    dependency = pins["dependency_issue_snapshot"]
    current_issue_bytes = (ROOT / "source" / "current-issue-998.json").read_bytes()
    if dependency.get("number") != 998 or sha256(current_issue_bytes) != dependency.get("sha256"):
        raise GuardError("current dependency issue snapshot differs from its pinned bytes")
    validate_issue_998(current_issue_bytes, pins["subject_ids"], expected_state="closed")
    validate_subject_context(pins, blobs, pins["subject_ids"])
    check_runtime()
    return blobs


def historical_output_map(pins: dict) -> dict[str, dict]:
    prefix = f"{TARGET_PACKET}/sources/derived/"
    return {item["path"].removeprefix(prefix): item for item in pins["historical_outputs"]}


def run_reproduction(
    output_relative: str,
    *,
    reader: Callable[[str, str], bytes] = git_blob,
    pins_bytes: bytes | None = None,
    issue_bytes: bytes | None = None,
) -> dict:
    pins_raw = PIN_FILE.read_bytes() if pins_bytes is None else pins_bytes
    pins = load_pins(pins_raw)
    output = Path(output_relative)
    if (output.is_absolute() or ".." in output.parts or len(output.parts) != 2
            or output.parts[0] != "results" or not re.fullmatch(r"run-[a-z0-9-]+", output.parts[1])):
        raise GuardError("output must be a simple results/run-<id> path beneath this packet")
    final = ROOT / output
    if (final.exists() or final.is_symlink() or (ROOT / "results").is_symlink()
            or (ROOT / "results").exists() and not (ROOT / "results").is_dir()):
        raise GuardError(f"fresh exclusive output path already exists: {output}")
    blobs = verify_all_inputs(pins, reader, issue_bytes)

    scratch_parent = ROOT / ".scratch" / "guarded-runs"
    scratch_parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="stage-", dir=scratch_parent))
    try:
        stage_data = stage / "data" / "regional-review"
        job_root = stage_data / "followup-serbia-422-admin-crosswalk-20261005"
        prior_root = stage_data / "regional-review-3c4fe25a21fa428d"
        source_dir = job_root / "sources"
        (source_dir / "derived").mkdir(parents=True)
        (prior_root / "source" / "gb").mkdir(parents=True)
        generator = pins["original_generator"]
        content = dict(blobs)
        content[generator["path"]] = reader(generator["commit"], generator["path"])
        required = [
            generator["path"],
            f"{TARGET_PACKET}/source-issue-998.json",
            f"{TARGET_PACKET}/sources/sors-cities-municipalities-2017.xls",
            f"{TARGET_PACKET}/sources/sors-cities-municipalities-current-2026-10-05.xlsx",
            f"{TARGET_PACKET}/sources/geoBoundaries-SRB-ADM2-2017.geojson",
            f"{PRIOR_PACKET}/source/subject-assessments.json",
            f"{PRIOR_PACKET}/source/gb/SRB-ADM2-geoBoundaries-SRB-ADM2-metaData.json",
        ]
        for path in required:
            raw = content.get(path)
            if raw is None:
                raise GuardError(f"required generator input is not in the complete pin set: {path}")
            destination = stage / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)

        spec = importlib.util.spec_from_file_location("pinned_serbia_generator", job_root / "reproduce.py")
        if spec is None or spec.loader is None:
            raise GuardError("could not load the pinned historical generator")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.ROOT = job_root
        module.SOURCE = source_dir
        module.OUT = source_dir / "derived"
        module.BASELINE = prior_root / "source" / "subject-assessments.json"
        module.ISSUE = job_root / "source-issue-998.json"
        module.OLD_FILE = source_dir / "sors-cities-municipalities-2017.xls"
        module.CUR_FILE = source_dir / "sors-cities-municipalities-current-2026-10-05.xlsx"
        module.GB_FILE = source_dir / "geoBoundaries-SRB-ADM2-2017.geojson"
        module.GB_METADATA = prior_root / "source" / "gb" / "SRB-ADM2-geoBoundaries-SRB-ADM2-metaData.json"
        module.main()

        produced = {path.name for path in module.OUT.iterdir() if path.is_file()}
        if produced != EXPECTED_OUTPUTS:
            raise GuardError(f"historical generator output inventory changed: {sorted(produced)}")
        old_outputs = historical_output_map(pins)
        if set(old_outputs) != EXPECTED_OUTPUTS:
            raise GuardError("historical output pins do not list the complete eight-file set")
        for name in sorted(EXPECTED_OUTPUTS - {"reproduction-summary.json"}):
            if sha256((module.OUT / name).read_bytes()) != old_outputs[name]["sha256"]:
                raise GuardError(f"generated result differs from retained historical output: {name}")
        current_summary = json.loads((module.OUT / "reproduction-summary.json").read_bytes())
        historical_summary = json.loads(blobs[old_outputs["reproduction-summary.json"]["path"]])
        for key in ("python", "pandas"):
            historical_summary.pop(key, None)
            current_summary.pop(key, None)
        if current_summary != historical_summary:
            raise GuardError("reproduction summary findings differ from the retained historical result")

        stage_results = stage / "published"
        stage_results.mkdir()
        for name in sorted(EXPECTED_OUTPUTS):
            shutil.copyfile(module.OUT / name, stage_results / name)
        final.parent.mkdir(parents=True, exist_ok=True)
        os.replace(stage_results, final)
        file_records = []
        for path in sorted(final.iterdir()):
            data = path.read_bytes()
            file_records.append({"path": path.name, "bytes": len(data), "sha256": sha256(data)})
        return {"output": str(output), "files": file_records}
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="fresh exclusive result directory beneath results/")
    parser.add_argument("--validate-only", action="store_true", help="verify all pinned bytes and scope without output")
    args = parser.parse_args()
    pins = load_pins(PIN_FILE.read_bytes())
    if args.validate_only:
        verify_all_inputs(pins)
        print(json.dumps({"outcome": "passed", "validated_inputs": len(pins["inputs"]), "subjects": len(pins["subject_ids"]), "outputs_created": 0}, indent=2))
        return
    if not args.output:
        parser.error("--output is required unless --validate-only is supplied")
    result = run_reproduction(args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except GuardError as exc:
        print(f"guarded reproduction refused: {exc}", file=sys.stderr)
        raise SystemExit(2)
