#!/usr/bin/env python3
"""Reproduce #1356's bounded integrity correction without touching #393 outputs.

The original producer scripts are executed from their pinned source bytes after
two exact, reviewed path/field substitutions. All data validation is performed
before output admission. The immutable PR #1130 merge is the evidence baseline;
current checkout changes in unrelated geography parts are not silently read.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
PACKET = ROOT / "research/geography/east-siberia-assessment-integrity-1130-erratum"
PIN_FILE = PACKET / "source/input-pins.json"
ISSUE_FILE = PACKET / "source/github-issue-1356.json"
BASELINE = "90d5309c6497073a039099241360ba807d0c3722"
ISSUE_SNAPSHOT_SHA256 = "89b7f94c153ab14cfc3fe95d130f7c3ce1e9ed7281efe4ebe1208b957880421f"
ORIGINAL_PACKET = Path("data/regional-review/regional-review-5cf69eed7fdff0b5")
ANALYZER = ORIGINAL_PACKET / "reproduction/analyze-geography.py"
RENDERER = ORIGINAL_PACKET / "reproduction/render-review-table.py"
INVENTORY = ORIGINAL_PACKET / "reproduction/scope-inventory.run-1.json"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def git_hashes_and_contract() -> tuple[dict[str, dict[str, Any]], dict[str, Any], dict[str, Any]]:
    pins = json.loads(PIN_FILE.read_text(encoding="utf-8"))
    issue_bytes = ISSUE_FILE.read_bytes()
    if digest(issue_bytes) != ISSUE_SNAPSHOT_SHA256 or digest(issue_bytes) != pins.get("issue_contract_sha256"):
        raise ValueError("captured GitHub issue contract bytes changed")
    issue = json.loads(issue_bytes)
    if issue.get("number") != 1356:
        raise ValueError("issue snapshot is not #1356")
    match = re.search(r"<!-- worldatlas-work:v1\s*(\{.*?\})\s*-->", issue["body"], re.S)
    if not match:
        raise ValueError("issue's machine-readable work contract is missing")
    contract = json.loads(match.group(1))
    if contract["owned_paths"] != ["research/geography/east-siberia-assessment-integrity-1130-erratum/"]:
        raise ValueError("issue-owned output path changed")
    evidence = contract["evidence_quality"]
    if sorted(evidence["subject_ids"]) != pins["subject_ids"]:
        raise ValueError("issue subject roster differs from pinned roster")
    if evidence["pins"] != {item["path"]: item["sha256"] for item in pins["files"]}:
        raise ValueError("issue pin set differs from immutable input ledger")
    if pins["baseline_commit"] != BASELINE:
        raise ValueError("unexpected immutable evidence baseline")
    actual: dict[str, dict[str, Any]] = {}
    for item in pins["files"]:
        blob = git_blob(BASELINE, item["path"])
        record = {"path": item["path"], "bytes": len(blob), "sha256": digest(blob)}
        if record["sha256"] != item["sha256"] or record["bytes"] != item["bytes"]:
            raise ValueError(f"immutable baseline pin mismatch: {item['path']}")
        actual[item["path"]] = record
    return actual, pins, contract


def json_bytes(data: bytes, label: str) -> Any:
    try:
        return json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid JSON in {label}: {error}") from error


def assert_inventory_matches_baseline(inventory_data: bytes, pins: dict[str, Any],
                                      contract: dict[str, Any]) -> dict[str, Any]:
    expected_inventory = next(x for x in pins["files"] if x["path"] == str(INVENTORY))
    if digest(inventory_data) != expected_inventory["sha256"]:
        raise ValueError("scope inventory bytes differ from the independently pinned issue input")
    inventory = json_bytes(inventory_data, "scope inventory")
    expected_ids = pins["subject_ids"]
    rows = inventory.get("subjects")
    if not isinstance(rows, list) or len(rows) != 207:
        raise ValueError("scope inventory must contain exactly 207 rows")
    ids = [row.get("id") for row in rows]
    if len(set(ids)) != 207 or sorted(ids) != expected_ids:
        raise ValueError("scope inventory identities are not the exact unique issue roster")

    baseline_commit = pins["baseline_commit"]
    index_path = "data/world-index.json"
    index = json_bytes(git_blob(baseline_commit, index_path), index_path)
    expected_parts = {f"geography/part-{i}.json" for i in range(34)} | {
        "geography/source-restoration-additions.json", "geography/macro-loose-ends-v5-additions.json"
    }
    if len(index.get("parts", [])) != 36 or set(index["parts"]) != expected_parts:
        raise ValueError("pinned world index does not enumerate all 34 indexed parts and two additions")
    target = set(expected_ids)
    features: dict[str, tuple[dict[str, Any], str]] = {}
    for part in index["parts"]:
        path = f"data/{part}"
        collection = json_bytes(git_blob(baseline_commit, path), path)
        for feature in collection.get("features", []):
            props = feature.get("properties", {})
            identity = feature.get("id") or props.get("id")
            if identity not in target:
                continue
            if identity in features:
                raise ValueError(f"duplicate pinned feature identity {identity}")
            features[identity] = (feature, path)
    if set(features) != target:
        missing = sorted(target - set(features))
        raise ValueError(f"pinned complete source scan found {len(features)}/207 subjects; missing={missing[:4]}")

    hierarchy_path = "data/hierarchy.json"
    hierarchy = {row["id"]: row for row in json_bytes(git_blob(baseline_commit, hierarchy_path), hierarchy_path)}
    by_id = {row["id"]: row for row in rows}
    mismatches: list[str] = []
    for identity in expected_ids:
        row = by_id[identity]
        feature, path = features[identity]
        props = feature.get("properties", {})
        metadata = props.get("metadata", {})
        parent = hierarchy.get(props.get("parent_id"))
        actual_fields = {
            "current_name": props.get("name"),
            "current_parent_id": props.get("parent_id"),
            "current_parent_name": parent.get("name") if parent else None,
            "feature_path": path,
            "source_id": metadata.get("source_id"),
            "source_name": metadata.get("source_name"),
            "source_url": metadata.get("source_url"),
            "source_license": metadata.get("license"),
            "source_reference_year": metadata.get("reference_year"),
            "source_role": metadata.get("source_role"),
            "source_level": metadata.get("administrative_level"),
            "source_original_id": metadata.get("original_id"),
            "source_member_ids": metadata.get("source_member_ids", []),
            "location_basis": metadata.get("location_basis"),
            "selection_reason": metadata.get("selection_reason"),
        }
        for key, value in actual_fields.items():
            if row.get(key) != value:
                mismatches.append(f"{identity}: {key}")
        if props.get("parent_id") and parent is None:
            mismatches.append(f"{identity}: parent missing from pinned hierarchy")
    if mismatches:
        raise ValueError("inventory/source binding mismatch: " + ", ".join(mismatches[:8]))

    # Every source-member ID is required to resolve to the pinned 185-feature
    # source extract or its exact eight-feature support extract.
    source_dir = ORIGINAL_PACKET / "source"
    direct = json_bytes((source_dir / "geoboundaries-rus-adm2-2017-scope-185-original-features.geojson").read_bytes(), "GeoBoundaries ADM2 scope")
    support = json_bytes((source_dir / "geoboundaries-rus-adm2-2017-adaptation-base-8-original-features.geojson").read_bytes(), "GeoBoundaries support features")
    direct_by_id = {f.get("properties", {}).get("shapeID"): f for f in direct.get("features", [])}
    support_by_id = {f.get("properties", {}).get("shapeID"): f for f in support.get("features", [])}
    if len(direct_by_id) != 185 or len(support_by_id) != 8:
        raise ValueError("pinned GeoBoundaries direct/support source identities are not unique and complete")
    resolve_data = json_bytes((source_dir / "resolve-ecoregions-east-siberia-query.json").read_bytes(), "RESOLVE source")
    resolve_by_id = {}
    for feature in resolve_data.get("features", []):
        eco_id = str(int(feature.get("properties", {}).get("ECO_ID")))
        if eco_id in resolve_by_id:
            raise ValueError(f"duplicate pinned RESOLVE identity: {eco_id}")
        resolve_by_id[eco_id] = feature
    lakes = json_bytes((source_dir / "ne_10m_lakes-pinned-source.geojson").read_bytes(), "Natural Earth source")
    lake_matches = [f for f in lakes.get("features", []) if str(f.get("properties", {}).get("ne_id")) == "1159113127"]
    if len(lake_matches) != 1:
        raise ValueError("pinned Natural Earth source does not resolve Lake Baikal exactly once")
    for row in rows:
        source_id = row.get("source_id") or ""
        original_id = row.get("source_original_id")
        members = row.get("source_member_ids", [])
        if source_id == "gb:RUS:ADM2":
            source = direct_by_id.get(original_id)
            if source is None or source.get("properties", {}).get("shapeName") != row.get("current_name"):
                raise ValueError(f"administrative name/identity join failed: {row['id']}")
        elif source_id.startswith("resolve:"):
            eco_id = source_id.split(":", 1)[1]
            admin_id = support_by_id.get(original_id)
            if eco_id not in resolve_by_id or admin_id is None:
                raise ValueError(f"ecological feature/member join failed: {row['id']}")
            if members != [f"gb:RUS:ADM2:{original_id}"]:
                raise ValueError(f"ecological source member binding failed: {row['id']}")
        elif source_id == "natural-earth:lake:1159113127":
            if original_id not in support_by_id or members != [f"gb:RUS:ADM2:{original_id}"]:
                raise ValueError(f"lake source member binding failed: {row['id']}")
        else:
            raise ValueError(f"unsupported source identity for issue subject {row['id']}: {source_id}")
    return inventory


def verify_current_consumed_bytes(pin_map: dict[str, dict[str, Any]],
                                  overrides: dict[str, bytes] | None = None) -> None:
    # Only these two world parts contain the 207 subjects; the complete 34-part
    # identity scan above reads the immutable Git blobs at BASELINE.
    consumed = [
        str(ANALYZER), str(RENDERER), str(INVENTORY),
        "data/world-index.json", "data/hierarchy.json",
        "data/macro-foundation/regional-handoffs.json.gz",
        "data/geography/part-20.json", "data/geography/part-21.json",
    ]
    consumed.extend(path for path in pin_map if path.startswith(str(ORIGINAL_PACKET / "source/")))
    for path in consumed:
        expected = pin_map.get(path)
        if expected is None:
            raise ValueError(f"consumed input lacks a declared issue pin: {path}")
        current = (overrides or {}).get(path, (ROOT / path).read_bytes())
        if digest(current) != expected["sha256"]:
            raise ValueError(f"working-tree consumed input differs from issue pin: {path}")


def load_control_overrides(values: list[str]) -> dict[str, bytes]:
    overrides: dict[str, bytes] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("byte override must be REPOSITORY_PATH=PACKET_FILE")
        repository_path, fixture = value.split("=", 1)
        fixture_path = (ROOT / fixture).resolve(strict=True)
        if not fixture_path.is_relative_to(PACKET.resolve()):
            raise ValueError("byte-override fixture must be inside the issue-owned packet")
        if repository_path in overrides:
            raise ValueError(f"duplicate byte override for {repository_path}")
        overrides[repository_path] = fixture_path.read_bytes()
    return overrides


def safe_fresh_directory(relative: Path) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("output directory must be a relative issue-owned path")
    target = ROOT / relative
    try:
        local = target.relative_to(PACKET)
    except ValueError as error:
        raise ValueError("output directory escapes the issue-owned packet") from error
    if PACKET.is_symlink():
        raise ValueError("output directory escapes the issue-owned packet")
    cursor = PACKET
    for index, component in enumerate(local.parts):
        cursor = cursor / component
        if cursor.is_symlink():
            raise ValueError(f"output path contains a symlink: {cursor}")
        final = index == len(local.parts) - 1
        if final and cursor.exists():
            raise FileExistsError(f"output path already exists: {cursor}")
        if cursor.exists() and not cursor.is_dir():
            raise ValueError(f"output parent is not a directory: {cursor}")
    target.mkdir(parents=True, exist_ok=False)
    return target


def run_producers(outdir: Path, run_name: str) -> dict[str, Any]:
    pin_map, pins, contract = git_hashes_and_contract()
    inventory = assert_inventory_matches_baseline(git_blob(BASELINE, str(INVENTORY)), pins, contract)
    verify_current_consumed_bytes(pin_map)

    # Admit the entire two-file output set before the first producer write.
    assessment_out = outdir / "geography-assessment.json"
    table_out = outdir / "subject-assessments.tsv"
    if assessment_out.exists() or assessment_out.is_symlink() or table_out.exists() or table_out.is_symlink():
        raise FileExistsError("fresh output set is not empty")

    analyzer_source = (ROOT / ANALYZER).read_text(encoding="utf-8")
    analyzer_source, replaced = analyzer_source.replace(
        "'current_source_level': feature['properties']['metadata'].get('source_level'),",
        "'current_source_level': feature['properties']['metadata'].get('administrative_level'),",
    ), analyzer_source.count("'current_source_level': feature['properties']['metadata'].get('source_level'),")
    if replaced != 1:
        raise ValueError("pinned analyzer field correction anchor is not unique")
    old_out = "OUT = OWNED / 'reproduction' / 'geography-assessment.json'"
    if analyzer_source.count(old_out) != 1:
        raise ValueError("pinned analyzer output path anchor is not unique")
    analyzer_source = analyzer_source.replace(old_out, f"OUT = Path({str(assessment_out)!r})")
    old_write = "OUT.write_text(json.dumps(output, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\\n', encoding='utf-8')"
    if analyzer_source.count(old_write) != 1:
        raise ValueError("pinned analyzer output writer anchor is not unique")
    analyzer_source = analyzer_source.replace(old_write,
        "with OUT.open('x', encoding='utf-8') as stream: stream.write(json.dumps(output, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\\n')")
    analysis_globals = {"__name__": "__main__", "__file__": str(ROOT / ANALYZER)}
    exec(compile(analyzer_source, str(ROOT / ANALYZER), "exec"), analysis_globals)
    if not assessment_out.is_file() or assessment_out.is_symlink():
        raise ValueError("analysis producer did not create the admitted regular assessment file")

    renderer_source = (ROOT / RENDERER).read_text(encoding="utf-8")
    old_assessment = "assessment = json.loads((root / 'reproduction/geography-assessment.json').read_text(encoding='utf-8'))"
    old_table = "output = root / 'reproduction/subject-assessments.tsv'"
    old_table_writer = "with output.open('w', encoding='utf-8', newline='') as stream:"
    if renderer_source.count(old_assessment) != 1 or renderer_source.count(old_table) != 1 or renderer_source.count(old_table_writer) != 1:
        raise ValueError("pinned renderer path anchors are not unique")
    renderer_source = renderer_source.replace(old_assessment,
        f"assessment = json.loads(Path({str(assessment_out)!r}).read_text(encoding='utf-8'))")
    renderer_source = renderer_source.replace(old_table, f"output = Path({str(table_out)!r})")
    renderer_source = renderer_source.replace(old_table_writer, "with output.open('x', encoding='utf-8', newline='') as stream:")
    renderer_globals = {"__name__": "__main__", "__file__": str(ROOT / RENDERER)}
    exec(compile(renderer_source, str(ROOT / RENDERER), "exec"), renderer_globals)
    if not table_out.is_file() or table_out.is_symlink():
        raise ValueError("table renderer did not create the admitted regular TSV file")

    result = json.loads(assessment_out.read_text(encoding="utf-8"))
    subjects = result["subjects"]
    if len(subjects) != 207 or len({row["id"] for row in subjects}) != 207:
        raise ValueError("actual producer output does not preserve exact 207 identities")
    source_level_counts = Counter(row.get("current_source_level") for row in subjects)
    if source_level_counts != Counter({"ADM2": 185, "Named physical region portion": 22}):
        raise ValueError(f"actual source-level values are not independently joined: {source_level_counts}")
    return {
        "run": run_name,
        "assessment": {"path": str(assessment_out.relative_to(ROOT)), "bytes": assessment_out.stat().st_size,
                       "sha256": digest(assessment_out.read_bytes())},
        "table": {"path": str(table_out.relative_to(ROOT)), "bytes": table_out.stat().st_size,
                  "sha256": digest(table_out.read_bytes())},
        "subjects": len(subjects),
        "source_level_counts": dict(sorted(source_level_counts.items())),
        "preserved_assessment_statuses": dict(sorted(Counter(x["classification"] for x in subjects).items())),
        "province_rows": len(result["provinces"]),
        "baseline_commit": BASELINE,
        "current_consumed_features": ["data/geography/part-20.json", "data/geography/part-21.json"],
        "inventory_join": "all 15 consumed current/source fields matched each pinned feature and parent record",
        "scope_scan": "all 36 immutable indexed feature files scanned; each declared subject found exactly once",
        "outputs_fresh_before_run": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vintage", default="2026-10-08-integrity-v4")
    parser.add_argument("--preflight-inventory", help="Adverse-control inventory fixture; a changed fixture must fail before output admission.")
    parser.add_argument("--preflight-byte-override", action="append", default=[], metavar="REPOSITORY_PATH=PACKET_FILE",
                        help="Adverse-control consumed input bytes; a changed fixture must fail before output admission.")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", args.vintage):
        raise ValueError("vintage must be a short safe path component")
    # Recheck all inputs and reserve both run directories plus the receipt
    # before the first producer output is written.
    pin_map, pins, contract = git_hashes_and_contract()
    if args.preflight_inventory:
        inventory_fixture = (ROOT / args.preflight_inventory).resolve(strict=True)
        if not inventory_fixture.is_relative_to(PACKET.resolve()):
            raise ValueError("inventory control fixture must be inside the issue-owned packet")
        inventory_bytes = inventory_fixture.read_bytes()
    else:
        inventory_bytes = git_blob(BASELINE, str(INVENTORY))
    assert_inventory_matches_baseline(inventory_bytes, pins, contract)
    overrides = load_control_overrides(args.preflight_byte_override)
    verify_current_consumed_bytes(pin_map, overrides)
    if args.preflight_inventory or overrides:
        raise ValueError("adverse-control override unexpectedly passed pinned-input preflight")
    version_dir = safe_fresh_directory(PACKET.relative_to(ROOT) / "vintages" / args.vintage)
    run_dirs = [version_dir / "run-1", version_dir / "run-2"]
    receipt_path = version_dir / "reproducibility.json"
    if any(path.exists() or path.is_symlink() for path in run_dirs) or receipt_path.exists() or receipt_path.is_symlink():
        raise FileExistsError("the complete new output set is not fresh")
    for path in run_dirs:
        path.mkdir(exist_ok=False)
    reports = [run_producers(run_dirs[0], "run-1"), run_producers(run_dirs[1], "run-2")]
    first = reports[0]
    second = reports[1]
    for key in ("assessment", "table"):
        left = (ROOT / first[key]["path"]).read_bytes()
        right = (ROOT / second[key]["path"]).read_bytes()
        if left != right:
            raise ValueError(f"two fresh actual producer runs differ: {key}")
    receipt = {
        "version": 1,
        "issue": 1356,
        "work_item_scope": "mechanical provenance-field, consumed-input and safe-output correction for #393's exact 207 subjects",
        "status": "reproduced-with-limits",
        "runs": reports,
        "pairwise_identical": True,
        "limits": [
            "The pinned GeoBoundaries 2017 administrative-role and completeness limits in the #393 packet remain unresolved.",
            "The 185+8 source extraction lineage is not reauthenticated against the unavailable 120,489,189-byte country source.",
            "Constitution Article 65 and Rosstat primary bytes remain unverified; this correction makes no legal, boundary, or semantic approval.",
        ],
    }
    if receipt_path.exists() or receipt_path.is_symlink():
        raise FileExistsError(f"reproducibility receipt already exists: {receipt_path}")
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
