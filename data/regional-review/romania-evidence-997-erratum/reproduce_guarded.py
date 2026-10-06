#!/usr/bin/env python3
"""Guard and reproduce the retained Romania #997 crosswalk without overwrites."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

PACKET = Path("data/regional-review/romania-evidence-997-erratum")
PRIOR = "data/regional-review/followup-romania-422-county-roles-20261005"
ORIGINAL_SOURCE = "data/regional-review/regional-review-3c4fe25a21fa428d/source"
METHOD = "romania-42-unit-source-and-parent-crosswalk"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fail(message: str):
    raise ValueError(message)


def under_owned_packet(repo: Path, target: Path):
    packet = (repo / PACKET).resolve()
    resolved = target.resolve()
    if os.path.commonpath([str(packet), str(resolved)]) != str(packet):
        fail("Writes must stay within the issue-owned packet")


def git_blob(repo: Path, commit: str, rel: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(repo), "show", f"{commit}:{rel}"])


def parse_json(data: bytes, label: str):
    try:
        return json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"Invalid JSON for {label}: {exc}")


def load_snapshot(repo: Path):
    packet = repo / PACKET
    manifest_bytes = (packet / "input-manifest.json").read_bytes()
    manifest = parse_json(manifest_bytes, "input manifest")
    snapshot_bytes = (packet / "github-issue-1177.json").read_bytes()
    snapshot = parse_json(snapshot_bytes, "issue 1177 snapshot")
    body = snapshot.get("body", "")
    if sha(body.encode()) != manifest["contract_sha256"]:
        fail("Issue 1177 body differs from the captured contract hash")
    match = re.search(r"<!-- worldatlas-work:v1\s*(\{.*?\})\s*-->", body, re.S)
    if not match:
        fail("Issue 1177 machine contract is missing")
    contract = json.loads(match.group(1))
    if snapshot.get("number") != 1177 or snapshot.get("title") != "Correct Romania #997 restoration provenance and guard retained reproduction":
        fail("Issue 1177 identity changed")
    if contract.get("mode") != "geography" or contract.get("max_prs") != 2:
        fail("Issue 1177 work mode or PR budget changed")
    if contract.get("depends_on") != [997] or contract.get("owned_paths") != [f"{PACKET.as_posix()}/"]:
        fail("Issue 1177 dependency or owned path changed")
    quality = contract["evidence_quality"]
    subject_ids = quality["subject_ids"]
    if len(subject_ids) != 42 or len(set(subject_ids)) != 42:
        fail("Issue 1177 must contain exactly 42 unique native subjects")
    descriptors = manifest["pins"]
    contract_pins = quality["pins"]
    declared = {f"{item['commit']}:{item['path']}": item["sha256"] for item in descriptors}
    if declared != contract_pins or len(descriptors) != 27:
        fail("The 27 retained input descriptors differ from the issue contract")
    if manifest.get("issue") != 1177 or manifest.get("subject_ids") != subject_ids:
        fail("Input manifest scope differs from issue 1177")
    return manifest, snapshot, contract, manifest_bytes


def read_pinned(repo: Path, manifest, overrides=None):
    overrides = overrides or {}
    blobs = {}
    for item in manifest["pins"]:
        key = f"{item['commit']}:{item['path']}"
        data = overrides.get(key, git_blob(repo, item["commit"], item["path"]))
        if len(data) != item["bytes"] or sha(data) != item["sha256"]:
            fail(f"Immutable whole-file input pin mismatch: {key}")
        blobs[key] = data
    return blobs


def by_path(blobs, rel, commit=None):
    found = [data for key, data in blobs.items() if key.endswith(":" + rel) and (commit is None or key.startswith(commit + ":"))]
    if len(found) != 1:
        fail(f"Expected one pinned input for {rel}, found {len(found)}")
    return found[0]


def work_contract(blobs):
    data = parse_json(by_path(blobs, f"{PRIOR}/github-issue-contract.json"), "original #997 issue contract")
    match = re.search(r"<!-- worldatlas-work:v1\s*(\{.*?\})\s*-->", data["body"], re.S)
    if not match:
        fail("Pinned #997 machine contract is missing")
    return json.loads(match.group(1))


def validate_context_against_catalog(neighbors, catalog, metadata):
    expected_ids = {
        "gb:HUN:ADM1", "gb:BGR:ADM1", "gb:SRB:ADM1", "gb:SRB:ADM2",
        "gb:MDA:ADM1", "gb:UKR:ADM1", "gb:ROU:ADM1",
    }
    if neighbors.get("catalog_path") != "data/administrative-sources.json":
        fail("Neighbor context names a different catalog")
    rows = neighbors.get("rows", [])
    if len(rows) != 7 or {row.get("id") for row in rows} != expected_ids:
        fail("Neighbor context must contain the exact seven catalog IDs")
    field_map = {
        "layer": "boundaryType", "canonical_label": "boundaryCanonical",
        "vintage": "boundaryYearRepresented", "source": "boundarySource",
        "license_label": "boundaryLicense", "source_url": "boundarySourceURL",
    }
    for row in rows:
        source_id = row["id"]
        if source_id not in catalog:
            fail(f"Neighbor row is absent from pinned catalog: {source_id}")
        source = catalog[source_id]
        for context_field, catalog_field in field_map.items():
            if row.get(context_field) != source.get(catalog_field):
                fail(f"Neighbor context/catalog mismatch: {source_id}.{context_field}")
        try:
            if int(row["count"]) != int(source["admUnitCount"]):
                fail(f"Neighbor context/catalog count mismatch: {source_id}")
        except (KeyError, TypeError, ValueError):
            fail(f"Invalid neighbor unit count: {source_id}")
        if not re.fullmatch(r"[0-9a-f]{64}", row.get("metadata_sha256", "")):
            fail(f"Malformed retained metadata digest: {source_id}")
    rou_rows = [row for row in rows if row["id"] == "gb:ROU:ADM1"]
    raw_meta = metadata
    if len(rou_rows) != 1 or raw_meta.get("boundaryYear") != "2017" or raw_meta.get("admUnitCount") != "42":
        fail("Romania source context no longer aligns with its pinned 2017/42 metadata")
    # The seven copied metadata digest strings do not bind the retained source
    # objects in this scope. Do not present them as independently recomputed.


def prepare(repo: Path, overrides=None):
    manifest, snapshot, issue_contract, manifest_bytes = load_snapshot(repo)
    blobs = read_pinned(repo, manifest, overrides)
    original_work = work_contract(blobs)
    q = original_work["evidence_quality"]
    expected = q["subject_ids"]
    if len(expected) != 42 or set(expected) != set(issue_contract["evidence_quality"]["subject_ids"]):
        fail("Pinned #997 subject set differs from the exact #1177 scope")
    if original_work["mode"] != "geography" or original_work["owned_paths"] != [f"{PRIOR}/"]:
        fail("Pinned original #997 contract ownership or mode changed")

    catalog = parse_json(by_path(blobs, "data/administrative-sources.json"), "administrative source catalog")
    metadata = parse_json(by_path(blobs, f"{ORIGINAL_SOURCE}/gb/ROU-ADM1-geoBoundaries-ROU-ADM1-metaData.json"), "ROU source metadata")
    neighbors = parse_json(by_path(blobs, f"{PRIOR}/neighbor-source-context.json"), "neighbor source context")
    validate_context_against_catalog(neighbors, catalog, metadata)

    source_manifest = parse_json(by_path(blobs, f"{ORIGINAL_SOURCE}/source-manifest.json"), "source manifest")
    source_row = next(row for row in source_manifest["sources"] if row["source_id"] == "gb:ROU:ADM1")
    source_geo = parse_json(by_path(blobs, f"{ORIGINAL_SOURCE}/gb/gb-ROU-ADM1.geojson"), "ROU source geometry")
    source_sha = sha(by_path(blobs, f"{ORIGINAL_SOURCE}/gb/gb-ROU-ADM1.geojson"))
    if source_row["sha256"] != source_sha or source_row["features"] != 42 or source_row["scope_members"] != 42:
        fail("Retained source manifest does not match the pinned 42-feature ROU input")

    prior_scope = parse_json(by_path(blobs, f"{ORIGINAL_SOURCE}/scope-subjects.json"), "prior scope")
    if {location_id for location_id in prior_scope["member_location_ids"] if location_id.startswith("gb:ROU:ADM1:")} != set(expected):
        fail("Pinned source scope does not contain the exact 42 issue subjects")
    roster = parse_json(by_path(blobs, f"{PRIOR}/official-county-roster.json"), "retained county roster transcription")
    atlas_part = parse_json(by_path(blobs, "data/geography/part-20.json"), "pinned Atlas partition")
    hierarchy = parse_json(by_path(blobs, "data/hierarchy.json"), "pinned hierarchy")
    assessments = parse_json(by_path(blobs, f"{ORIGINAL_SOURCE}/subject-assessments.json"), "subject assessments")["subjects"]
    official_roles = {"county": len(roster["county_names_from_law_annex"]), "bucharest": 1}

    code_bytes = by_path(blobs, f"{PRIOR}/reproduce.py")
    namespace = {"__name__": "pinned_romania_reproduce"}
    exec(compile(code_bytes, "<pinned #1015 reproduce.py>", "exec"), namespace)
    built_inputs = {
        "work": original_work, "quality": q, "expected": expected,
        "source_manifest": source_manifest, "source_row": source_row,
        "source_meta": metadata, "source_geo": source_geo,
        "source_geo_sha256": source_sha, "prior_scope": prior_scope,
        "assessments": assessments, "atlas_part": atlas_part,
        "hierarchy": hierarchy, "neighbors": neighbors,
        "official_roster": roster,
    }
    result = namespace["build_crosswalk"](built_inputs)
    generated = (json.dumps(result, ensure_ascii=False, indent=2).encode() + b"\n")
    historical = by_path(blobs, f"{PRIOR}/source-crosswalk.json")
    if generated != historical:
        fail("Guarded regeneration differs from the immutable original crosswalk bytes")
    metrics = {
        "subject_count": len(result["rows"]),
        "singleton_parent_count": result["same_name_singleton_province_parent_count"],
        "distinct_parent_ids": len({row["parent_id"] for row in result["rows"]}),
        "neighbor_catalog_row_count": len(neighbors["rows"]),
        "county_transcription_match_count": result["county_member_count"],
        "bucharest_transcription_match_count": result["bucharest_municipality_count"],
        "source_geometry_vertices": sum(row["source_geometry_vertices"] for row in result["rows"]),
        "atlas_geometry_vertices": sum(row["atlas_geometry_vertices"] for row in result["rows"]),
        "exact_geometry_json_matches": result["exact_source_atlas_geometry_matches"],
        "official_polygon_comparison_performed": False,
    }
    if metrics["subject_count"] != 42 or metrics["singleton_parent_count"] != 42 or metrics["distinct_parent_ids"] != 42 or metrics["neighbor_catalog_row_count"] != 7:
        fail("Scoped subject, parent, or neighboring context cardinality changed")
    return manifest, manifest_bytes, blobs, generated, metrics, source_sha


def write_exclusive_run(repo: Path, output_dir: Path):
    manifest, manifest_bytes, blobs, generated, metrics, source_sha = prepare(repo)
    runner_sha = sha(Path(__file__).read_bytes())
    old_generator_sha = sha(by_path(blobs, f"{PRIOR}/reproduce.py"))
    target = output_dir if output_dir.is_absolute() else repo / output_dir
    under_owned_packet(repo, target)
    stored_output = gzip.compress(generated, mtime=0)
    payloads = {
        "source-crosswalk.json.gz": stored_output,
        "positive-control.json": (json.dumps({
            "method_id": METHOD, "kind": "positive-control", "outcome": "passed",
            "scope": "exact 42 issue subjects, their 42 same-name singleton parents, and seven read-only catalog context rows",
            "metrics": metrics, "source_sha256": source_sha,
            "input_descriptor_count": len(manifest["pins"]),
            "historical_output_sha256": sha(by_path(blobs, f"{PRIOR}/source-crosswalk.json")),
            "limit": "Agreement with retained bytes and roster transcription is not legal-source authentication or boundary accuracy.",
        }, ensure_ascii=False, indent=2).encode() + b"\n"),
        "run-manifest.json": (json.dumps({
            "version": 1, "method_id": METHOD, "issue": 1177,
            "input_manifest_sha256": sha(manifest_bytes),
            "runner_sha256": runner_sha, "pinned_historical_generator_sha256": old_generator_sha,
            "input_count": len(manifest["pins"]),
            "source_crosswalk_sha256": sha(generated),
            "stored_output_path": "source-crosswalk.json.gz",
            "stored_output_bytes": len(stored_output),
            "stored_output_sha256": sha(stored_output),
            "uncompressed_output_bytes": len(generated),
            "uncompressed_output_sha256": sha(generated), "source_sha256": source_sha,
            "metrics": metrics,
        }, ensure_ascii=False, indent=2).encode() + b"\n"),
    }
    target.mkdir(parents=True, exist_ok=False)
    for name, data in payloads.items():
        with (target / name).open("xb") as handle:
            handle.write(data)
    print(json.dumps({"output_dir": str(target), "source_crosswalk_sha256": sha(generated), "metrics": metrics}, ensure_ascii=False))


def run_negative_controls(repo: Path, report_path: Path):
    manifest, snapshot, contract, manifest_bytes = load_snapshot(repo)
    baseline = read_pinned(repo, manifest)
    packet = repo / PACKET
    specs = [
        ("neighbor-context-byte-drift", f"{PRIOR}/neighbor-source-context.json"),
        ("roster-byte-change", f"{PRIOR}/official-county-roster.json"),
        ("original-contract-byte-change", f"{PRIOR}/github-issue-contract.json"),
        ("original-code-byte-change", f"{PRIOR}/reproduce.py"),
        ("baseline-byte-change", "data/hierarchy.json"),
        ("source-byte-change", f"{ORIGINAL_SOURCE}/gb/gb-ROU-ADM1.geojson"),
    ]
    results = []
    for name, rel in specs:
        key = next(key for key in baseline if key.endswith(":" + rel))
        changed = dict(baseline)
        changed[key] = baseline[key] + b" "
        rejected = False
        reason = ""
        try:
            prepare(repo, overrides=changed)
        except (ValueError, subprocess.CalledProcessError) as exc:
            rejected, reason = True, str(exc)
        if not rejected:
            fail(f"Negative control was accepted: {name}")
        results.append({"id": name, "outcome": "rejected-before-generation", "reason": reason})

    # Reproduce the previously demonstrated HUN ADM1 20 -> 21 drift and show
    # that both the immutable file pin and the semantic catalog comparison stop it.
    neighbor_key = next(key for key in baseline if key.endswith(":" + f"{PRIOR}/neighbor-source-context.json"))
    neighbors = parse_json(baseline[neighbor_key], "pinned neighbor context")
    hun = next(row for row in neighbors["rows"] if row["id"] == "gb:HUN:ADM1")
    hun["count"] = 21
    catalog = parse_json(by_path(baseline, "data/administrative-sources.json"), "pinned catalog")
    metadata = parse_json(by_path(baseline, f"{ORIGINAL_SOURCE}/gb/ROU-ADM1-geoBoundaries-ROU-ADM1-metaData.json"), "pinned ROU metadata")
    semantic_rejected = False
    try:
        validate_context_against_catalog(neighbors, catalog, metadata)
    except ValueError:
        semantic_rejected = True
    if not semantic_rejected:
        fail("The demonstrated HUN count drift passed semantic catalog validation")
    results.append({"id": "hun-adm1-count-20-to-21", "outcome": "rejected-before-generation", "guard": "immutable whole-file pin and explicit catalog value match"})

    output_missing = packet / "runs" / "negative-control-must-not-exist"
    if output_missing.exists():
        fail("Negative-control output path already exists")
    try:
        prepare(repo, overrides={neighbor_key: json.dumps(neighbors).encode()})
        fail("Changed neighbor transcription passed immutable input validation")
    except ValueError:
        pass
    if output_missing.exists():
        fail("A rejected negative control emitted output")

    with tempfile.TemporaryDirectory(prefix="romania-existing-output-", dir=packet / "runs") as temp:
        existing = Path(temp) / "occupied"
        existing.mkdir()
        sentinel = existing / "sentinel.txt"
        sentinel.write_text("preserve\n")
        before = sentinel.read_bytes()
        try:
            write_exclusive_run(repo, existing)
            fail("Existing output path was overwritten")
        except FileExistsError:
            pass
        if sentinel.read_bytes() != before or sorted(p.name for p in existing.iterdir()) != ["sentinel.txt"]:
            fail("Existing output contents changed")
    results.append({"id": "existing-output-directory", "outcome": "rejected-without-overwrite"})

    report = {
        "version": 1, "method_id": METHOD, "issue": 1177,
        "input_manifest_sha256": sha(manifest_bytes), "outcome": "passed",
        "tests": results,
        "assertions": {
            "all_wrong_inputs_rejected_before_generation": True,
            "existing_output_preserved": True,
            "rejected_controls_emitted_no_output": True,
            "original_source_files_modified": False,
        },
        "limits": "Byte-pin tests prove changed inputs are rejected; the explicit HUN count check also proves catalog disagreement is rejected after parsing. They do not validate legal meaning or geometry accuracy.",
    }
    under_owned_packet(repo, report_path)
    with report_path.open("xb") as handle:
        handle.write(json.dumps(report, ensure_ascii=False, indent=2).encode() + b"\n")
    print(json.dumps({"negative_controls": len(results), "report": str(report_path)}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--negative-controls", type=Path)
    args = parser.parse_args()
    repo = args.root.resolve()
    if args.output_dir and args.negative_controls:
        raise SystemExit("Choose --output-dir or --negative-controls")
    if args.output_dir:
        write_exclusive_run(repo, args.output_dir)
    elif args.negative_controls:
        path = args.negative_controls if args.negative_controls.is_absolute() else repo / args.negative_controls
        run_negative_controls(repo, path)
    else:
        parser.error("one of --output-dir or --negative-controls is required")


if __name__ == "__main__":
    main()
