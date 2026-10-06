#!/usr/bin/env python3
"""Reproduce the #996 Montenegro comparison behind immutable whole-file guards.

This erratum is additive. It reads the exact original issue pins, checks the
historical files from Git and the retained #996 packet from its working-tree
read boundary, then writes only a new exclusive run directory. It does not
measure or approve legal boundaries.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = Path(__file__).resolve()
PACKET = ROOT / "data/regional-review/montenegro-evidence-996-erratum"
ORIGINAL_PACKET = "data/regional-review/followup-montenegro-422-boundaries-20261005"
PRIOR_SOURCE = "data/regional-review/regional-review-3c4fe25a21fa428d/source"
BASELINE = "b6cfaada43a1e0472cd833d16733d1fd6065eaec"
ORIGINAL_PACKET_COMMIT = "c944e017796005726150abef19763db9ffd07154"
ISSUE_RESPONSE = PACKET / "source/issue-1172-api-response.json"
ISSUE_RESPONSE_SHA256 = "7410d14fd006f9271e54fbbb5287ff4064948ab638d9dfd24192e5f652f3d02c"
RESERVATION_SHA256 = "77001c40bb58f033219e4004a02fec70095ae66c4c76e8dc30571929c33758ee"
AUTHOR = "01a10948-7d38-75d0-bc01-4cc28ea41f49"
BRANCH = "geography/montenegro-996-erratum-1172-20261006"
MAX_OBJECT = 32 * 1024 * 1024
MAX_PHASE = 256 * 1024 * 1024
MAX_DESCRIPTORS = 512
OUTPUT_RESERVE = 2 * 1024 * 1024


class GuardError(RuntimeError):
    pass


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def enforce_whole_file_pin(raw: bytes, expected: str, label: str) -> bytes:
    if len(raw) > MAX_OBJECT:
        raise GuardError(f"ordinary object exceeds 32 MiB: {label}")
    if sha(raw) != expected:
        raise GuardError(f"complete-file SHA-256 mismatch: {label}")
    return raw


def git_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{commit}:{path}"])


def verify_running_code() -> tuple[str, bytes]:
    path = SCRIPT_PATH.relative_to(ROOT).as_posix()
    commit = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    immutable_blob = git_bytes(commit, path)
    current_bytes = SCRIPT_PATH.read_bytes()
    enforce_whole_file_pin(current_bytes, sha(immutable_blob), f"committed runner at {commit}:{path}")
    if current_bytes != immutable_blob:
        raise GuardError("working reproduction code is not the exact immutable Git HEAD blob")
    return commit, immutable_blob


def checked_json(raw: bytes, label: str):
    if len(raw) > MAX_OBJECT:
        raise GuardError(f"ordinary object exceeds 32 MiB: {label}")
    return json.loads(raw)


def canonical(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + "\n").encode("utf-8")


def norm(name: str) -> str:
    value = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    value = re.sub(r"\b(municipality|capital|metropolis)\b", " ", value)
    return re.sub(r"[^a-z0-9]+", "", value)


def exact_match(source_name: str, lookup: dict[str, tuple[str, int]]) -> tuple[str, int]:
    key = norm(source_name)
    if key not in lookup:
        raise ValueError(f"No exact normalized official municipality name: {source_name}")
    return lookup[key]


def load_issue_contract():
    raw = ISSUE_RESPONSE.read_bytes()
    if sha(raw) != ISSUE_RESPONSE_SHA256:
        raise GuardError("issue #1172 API snapshot bytes changed")
    issue = checked_json(raw, str(ISSUE_RESPONSE))
    if issue.get("number") != 1172:
        raise GuardError("issue snapshot number mismatch")
    match = re.search(r"<!-- worldatlas-work:v1\s*\n([\s\S]*?)\n-->", issue["body"])
    if not match:
        raise GuardError("issue contract missing")
    spec = json.loads(match.group(1))
    quality = spec["evidence_quality"]
    ids = quality["subject_ids"]
    if (spec.get("mode") != "geography" or spec.get("max_prs") != 2 or
        spec.get("depends_on") != [996] or
        spec.get("owned_paths") != [PACKET.relative_to(ROOT).as_posix() + "/"] or
        quality.get("review_kind") != "source" or len(ids) != 23 or len(set(ids)) != 23):
        raise GuardError("issue contract differs from the declared bounded work item")
    if len(quality["pins"]) != 63:
        raise GuardError("expected 63 complete original whole-file pins")
    for key, digest in quality["pins"].items():
        if not re.fullmatch(r"[a-f0-9]{40}:.+", key) or not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise GuardError(f"malformed whole-file pin: {key}")
    if len(raw) + (PACKET / "reservation.json").stat().st_size > MAX_OBJECT:
        raise GuardError("issue and reservation records exceed ordinary-object limit")
    reservation_raw = (PACKET / "reservation.json").read_bytes()
    if sha(reservation_raw) != RESERVATION_SHA256:
        raise GuardError("serialized reservation receipt bytes changed")
    reservation = checked_json(reservation_raw, "reservation receipt")
    claim = reservation.get("claim", {})
    if not (reservation.get("accepted") is True and claim.get("active") is True and
            claim.get("issue_number") == 1172 and claim.get("worker_id") == AUTHOR and
            claim.get("branch") == BRANCH and claim.get("mode") == "geography" and
            claim.get("owned_paths") == spec["owned_paths"]):
        raise GuardError("reservation receipt does not bind this exact issue/worker/branch/scope")
    return issue, spec, quality, reservation


def verified_inputs(quality):
    """Verify each expected whole input before any result is produced."""
    files = []
    seen_paths = set()
    total = 0
    for key, expected in quality["pins"].items():
        commit, path = key.split(":", 1)
        if path in seen_paths:
            raise GuardError(f"duplicate whole-file descriptor: {path}")
        seen_paths.add(path)
        if commit == BASELINE:
            raw = git_bytes(BASELINE, path)
            # The bytes remained identical in the predecessor packet baseline.
            predecessor = git_bytes(ORIGINAL_PACKET_COMMIT, path)
            if sha(predecessor) != expected:
                raise GuardError(f"predecessor baseline drift: {path}")
        elif commit == ORIGINAL_PACKET_COMMIT:
            target = ROOT / path
            if not target.is_file() or target.is_symlink():
                raise GuardError(f"retained packet input missing/not ordinary: {path}")
            raw = target.read_bytes()
            immutable = git_bytes(ORIGINAL_PACKET_COMMIT, path)
            if sha(immutable) != expected:
                raise GuardError(f"retained packet Git blob mismatch: {path}")
        else:
            raise GuardError(f"unexpected commit in issue pin: {commit}")
        enforce_whole_file_pin(raw, expected, path)
        if path.endswith(".gz"):
            decoded = gzip.decompress(raw)
            if len(decoded) > MAX_OBJECT:
                raise GuardError(f"decoded object exceeds 32 MiB: {path}")
        total += len(raw)
        if total > MAX_PHASE:
            raise GuardError("complete input phase exceeds 256 MiB")
        files.append({"commit": commit, "path": path, "bytes": len(raw), "sha256": expected})
    # Three additional consumed records/code objects plus the complete fixture
    # and the fixed output reserve are accounted for before reproduction.
    extra_paths = [
        ISSUE_RESPONSE.relative_to(ROOT).as_posix(),
        (PACKET / "reservation.json").relative_to(ROOT).as_posix(),
        SCRIPT_PATH.relative_to(ROOT).as_posix(),
    ]
    for path in extra_paths:
        raw = (ROOT / path).read_bytes()
        if len(raw) > MAX_OBJECT:
            raise GuardError(f"additional object exceeds 32 MiB: {path}")
        total += len(raw)
    total += 1129 + OUTPUT_RESERVE
    descriptor_count = len(files) + len(extra_paths) + 3  # source/fixture/result control descriptors
    if total > MAX_PHASE or descriptor_count > MAX_DESCRIPTORS:
        raise GuardError("complete reproduction phase exceeds declared byte/descriptor limits")
    return files, total, descriptor_count


def current_pinned(path: str, pins: dict[str, str]) -> bytes:
    key = f"{ORIGINAL_PACKET_COMMIT}:{path}"
    raw = (ROOT / path).read_bytes()
    return enforce_whole_file_pin(raw, pins[key], path)


def baseline_pinned(path: str, pins: dict[str, str]) -> bytes:
    key = f"{BASELINE}:{path}"
    raw = git_bytes(BASELINE, path)
    return enforce_whole_file_pin(raw, pins[key], path)


def mismatch_rejected(raw: bytes, expected: str, name: str) -> dict:
    if sha(raw) == expected:
        raise GuardError(f"negative-control fixture did not change {name}")
    try:
        enforce_whole_file_pin(raw, expected, name)
    except GuardError as error:
        return {"name": name, "outcome": "passed", "rejection": str(error),
                "fixture_bytes": len(raw), "fixture_sha256": sha(raw)}
    raise GuardError(f"negative control unexpectedly accepted {name}")


def build_report(spec, pins):
    ids = spec["evidence_quality"]["subject_ids"]
    index = checked_json(baseline_pinned("data/world-index.json", pins), "world index")
    hierarchy_rows = checked_json(baseline_pinned("data/hierarchy.json", pins), "hierarchy")
    hierarchy = {row["id"]: row for row in hierarchy_rows}
    occurrences = {identity: [] for identity in ids}
    subject_props = {}
    for rel in index["parts"]:
        raw = baseline_pinned("data/" + rel, pins)
        data = checked_json(raw, "data/" + rel)
        for feature in data["features"]:
            props = feature.get("properties", {})
            identity = props.get("id")
            if identity in occurrences:
                occurrences[identity].append((rel, props))
                subject_props[identity] = props
    if any(len(occurrences[identity]) != 1 for identity in ids):
        raise GuardError("each declared subject must occur exactly once in its actual indexed file")
    containing = {occurrences[identity][0][0] for identity in ids}
    if containing != {"geography/part-15.json"}:
        raise GuardError(f"unexpected exact subject containing file: {sorted(containing)}")

    issue_bytes = current_pinned(f"{ORIGINAL_PACKET}/source/issue-996-api-response.json", pins)
    issue996 = checked_json(issue_bytes, "historical issue #996 snapshot")
    old_match = re.search(r"<!-- worldatlas-work:v1\s*\n([\s\S]*?)\n-->", issue996["body"])
    if not old_match:
        raise GuardError("pinned #996 issue scope contract missing")
    old_spec = json.loads(old_match.group(1))
    if old_spec["evidence_quality"]["subject_ids"] != ids:
        raise GuardError("current #1172 subjects differ from immutable #996 subject order")
    old_area = checked_json(baseline_pinned(PRIOR_SOURCE + "/area-assessments.json", pins), "area assessments")
    old_subjects = checked_json(baseline_pinned(PRIOR_SOURCE + "/subject-assessments.json", pins), "subject assessments")["subjects"]
    area_by_id = {row["location_id"]: row for row in old_area["subjects"] if row["source_id"] == "gb:MNE:ADM1"}
    subject_by_id = {row["location_id"]: row for row in old_subjects if row["source_id"] == "gb:MNE:ADM1"}
    if set(area_by_id) != set(ids) or set(subject_by_id) != set(ids):
        raise GuardError("retained area/subject rosters do not equal the exact 23-item issue scope")
    if old_area["evaluation_vintage"] != "source" or old_area["method"]["area_method"] != "WGS84 straight-source-edge ellipsoidal integral":
        raise GuardError("retained area result has unexpected vintage or method")

    official17_path = f"{ORIGINAL_PACKET}/source/official-municipal-areas-2017.json"
    official18_path = f"{ORIGINAL_PACKET}/source/official-municipal-areas-2018.json"
    official17_raw = current_pinned(official17_path, pins)
    official18_raw = current_pinned(official18_path, pins)
    official17 = checked_json(official17_raw, "2017 municipality table transcription")
    official18 = checked_json(official18_raw, "2018 municipality table transcription")
    name17 = {norm(name): (name, value) for name, value in official17["areas_km2"].items()}
    name18 = {norm(name): (name, value) for name, value in official18["areas_km2"].items()}
    source_geometry_path = f"{ORIGINAL_PACKET}/source/gb-MNE-ADM1-geoBoundaries-2017.geojson"
    source_geometry = checked_json(current_pinned(source_geometry_path, pins), "retained comparison geometry")
    features = source_geometry.get("features", [])
    features_by_id = {feature["properties"]["shapeID"]: feature for feature in features}
    if len(features) != 23 or len(features_by_id) != 23:
        raise GuardError("retained comparison geometry is not an exact 23-feature source set")

    rows, parent_children = [], {}
    for identity in ids:
        props = subject_props[identity]
        assessment = subject_by_id[identity]
        area = area_by_id[identity]
        original_id = identity.rsplit(":", 1)[1]
        feature = features_by_id.get(original_id)
        if feature is None:
            raise GuardError(f"subject source shape missing: {identity}")
        if (props["metadata"]["source_id"] != "gb:MNE:ADM1" or props["metadata"]["reference_year"] != "2017" or
            props["metadata"]["original_id"] != original_id or assessment["original_id"] != original_id or
            assessment["source_shape_id"] != original_id or
            assessment["source_sha256"] != pins[f"{ORIGINAL_PACKET_COMMIT}:{ORIGINAL_PACKET}/source/gb-MNE-ADM1-geoBoundaries-2017.geojson"] or
            area["source_sha256"] != assessment["source_sha256"]):
            raise GuardError(f"subject/source identity or exact geometry hash differs: {identity}")
        if assessment["source_feature_name"] != feature["properties"]["shapeName"]:
            raise GuardError(f"subject/source feature name differs: {identity}")
        reported17_name, reported17 = exact_match(assessment["source_feature_name"], name17)
        reported18_name, reported18 = exact_match(assessment["source_feature_name"], name18)
        parent_id = props["parent_id"]
        parent = hierarchy.get(parent_id)
        if parent is None or parent.get("level") != "province":
            raise GuardError(f"subject parent is absent/not a province: {identity}")
        parent_children.setdefault(parent_id, []).append(identity)
        geom = feature["geometry"]
        components = len(geom["coordinates"]) if geom["type"] == "MultiPolygon" else 1
        holes = (sum(max(0, len(poly) - 1) for poly in geom["coordinates"])
                 if geom["type"] == "MultiPolygon" else max(0, len(geom["coordinates"]) - 1))
        measured = float(area["area_km2"])
        rows.append({
            "subject_id": identity, "atlas_name": props["name"],
            "source_feature_name": assessment["source_feature_name"], "shape_id": original_id,
            "atlas_parent_id": parent_id, "atlas_parent_name": parent["name"],
            "atlas_parent_level": parent["level"],
            "atlas_parent_declared_child_count": parent["metadata"]["child_count"],
            "source_vintage": "2017 representative year (source date not established)",
            "source_geometry_type": geom["type"], "source_polygon_components": components,
            "source_hole_rings": holes, "source_coordinate_vertices": assessment["coordinate_vertices"],
            "retained_geometry_area_km2_wgs84": measured,
            "official_2017_report_name": reported17_name, "official_2017_report_area_km2": reported17,
            "area_delta_2017_official_minus_geometry_km2": round(reported17 - measured, 6),
            "area_delta_2017_pct_of_official": round(100 * (reported17 - measured) / reported17, 6),
            "official_2018_report_name": reported18_name, "official_2018_report_area_km2": reported18,
            "area_delta_2018_official_minus_geometry_km2": round(reported18 - measured, 6),
            "area_delta_2018_pct_of_official": round(100 * (reported18 - measured) / reported18, 6),
            "result": "area-only correspondence signal; not boundary verification"
        })
    if len(parent_children) != 23 or any(len(children) != 1 for children in parent_children.values()):
        raise GuardError("the 23 declared source subjects must retain 23 singleton parent contexts")
    if len(name17) != 23 or set(name17) != {norm(subject_by_id[i]["source_feature_name"]) for i in ids}:
        raise GuardError("2017 reported-area roster does not exactly match all 23 subjects")
    current_path = f"{ORIGINAL_PACKET}/source/current-municipalities-2025.json"
    current_roster = checked_json(current_pinned(current_path, pins), "2025 current municipality roster")
    if len(current_roster) != 25:
        raise GuardError("retained 2025 current roster differs from prior inspected count")

    rows_by_id = {row["subject_id"]: row for row in rows}
    ordered_rows = [rows_by_id[identity] for identity in ids]
    total_geometry = round(sum(area_by_id[identity]["area_km2"] for identity in ids), 6)
    sum17, sum18 = sum(official17["areas_km2"].values()), sum(official18["areas_km2"].values())
    summary = {
        "issue_subject_count": len(ids), "matched_2017_official_names": len(name17),
        "retained_2017_features": len(features_by_id), "unique_subject_containing_files": 1,
        "containing_file": "data/geography/part-15.json",
        "atlas_singleton_parent_count": len(parent_children),
        "retained_source_geometry_types": {kind: sum(row["source_geometry_type"] == kind for row in rows)
                                            for kind in sorted({row["source_geometry_type"] for row in rows})},
        "coastal_source_municipality_count": 6,
        "retained_source_multipolygon_component_count": sum(row["source_polygon_components"] for row in rows),
        "retained_source_hole_ring_count": sum(row["source_hole_rings"] for row in rows),
        "retained_area_sum_km2": total_geometry,
        "official_2017_table_area_sum_km2": sum17,
        "official_2017_reported_montenegro_area_km2": official17["national_area_km2"],
        "official_2017_table_minus_country_km2": sum17 - official17["national_area_km2"],
        "official_2018_table_area_sum_km2": sum18,
        "official_2018_reported_montenegro_area_km2": official18["national_area_km2"],
        "official_2018_country_minus_municipalities_km2": official18["national_area_km2"] - sum18,
        "official_2018_country_difference_source_explanation": "MONSTAT footnote attributes this to Lake Skadar area belonging to Montenegro",
        "current_2025_official_roster_count": len(current_roster),
        "reproducibility": "Rows are sorted in exact issue scope order; JSON serialization is UTF-8, sorted keys, indent 2 and one trailing newline."
    }
    prior_output_path = f"{ORIGINAL_PACKET}/comparison.json"
    prior = checked_json(current_pinned(prior_output_path, pins), "immutable original comparison report")
    correction = {
        "historical_report_sha256": pins[f"{ORIGINAL_PACKET_COMMIT}:{prior_output_path}"],
        "historical_wrong_area_method_source": prior["area_method_source"],
        "corrected_existing_input": f"{PRIOR_SOURCE}/area-assessments.json",
        "reason": "The earlier declaration inserted an extra source/ directory. The consumed existing whole-file area assessment is pinned at the corrected path above.",
        "comparison": "All original report fields and values reproduce exactly after normalizing only the erroneous area_method_source field."
    }
    prior_normalized = dict(prior)
    prior_normalized["area_method_source"] = correction["corrected_existing_input"]
    new_report = {
        "version": prior["version"], "issue": 996, "erratum_issue": 1172,
        "baseline_commit": BASELINE,
        "scope_source": prior["scope_source"],
        "area_method_source": correction["corrected_existing_input"],
        "official_table_inputs": ["source/official-municipal-areas-2017.json", "source/official-municipal-areas-2018.json"],
        "summary": summary, "subjects": ordered_rows,
        "limits": prior["limits"],
        "provenance_correction": correction,
        "prior_report_all_other_fields_reproduced": prior_normalized == {
            "version": prior["version"], "issue": prior["issue"], "baseline_commit": prior["baseline_commit"],
            "scope_source": prior["scope_source"], "area_method_source": prior_normalized["area_method_source"],
            "official_table_inputs": prior["official_table_inputs"], "summary": prior["summary"],
            "subjects": prior["subjects"], "limits": prior["limits"]
        }
    }
    return new_report, {"ids": ids, "pins": pins, "official17_raw": official17_raw,
                        "official18_raw": official18_raw, "rows": rows}


def run_once(out_dir: Path):
    runner_commit, runner_blob = verify_running_code()
    issue, spec, quality, _ = load_issue_contract()
    pin_records, phase_bytes, descriptor_count = verified_inputs(quality)
    report, context = build_report(spec, quality["pins"])
    out_dir = out_dir.resolve()
    try:
        out_dir.relative_to(PACKET.resolve())
    except ValueError as error:
        raise GuardError("output directory must remain under the issue-owned prefix") from error
    if out_dir.exists():
        raise GuardError("output directory must be fresh and absent")

    # Construct complete changed-input fixtures in memory. No source file is edited.
    area17 = checked_json(context["official17_raw"], "2017 table")
    if area17["areas_km2"].get("Plav") != 486:
        raise GuardError("Plav fixture no longer matches the issue's demonstrated 486 km2 value")
    area17["areas_km2"]["Plav"] = 487
    drift = canonical(area17)
    trans_path = f"{ORIGINAL_PACKET}/source/official-municipal-areas-2017.json"
    baseline_path = "data/geography/part-15.json"
    source_path = f"{ORIGINAL_PACKET}/source/gb-MNE-ADM1-geoBoundaries-2017.geojson"
    old_code_path = f"{ORIGINAL_PACKET}/reproduce.py"
    wrong_vintage_path = f"{ORIGINAL_PACKET}/source-manifest.json"
    wrong_vintage = checked_json(current_pinned(wrong_vintage_path, quality["pins"]), "original source manifest")
    wrong_vintage["items"][0]["vintage"] = "2018 (synthetic wrong-vintage control)"
    mutated_source = bytearray(current_pinned(source_path, quality["pins"]))
    mutated_source[0] = (mutated_source[0] + 1) % 256
    mutated_baseline = bytearray(baseline_pinned(baseline_path, quality["pins"]))
    mutated_baseline[0] = (mutated_baseline[0] + 1) % 256
    mutated_old_code = bytearray(current_pinned(old_code_path, quality["pins"]))
    mutated_old_code[-1] = (mutated_old_code[-1] + 1) % 256
    controls = [
        mismatch_rejected(drift, quality["pins"][f"{ORIGINAL_PACKET_COMMIT}:{trans_path}"], "Plav +1 km2 complete transcription"),
        mismatch_rejected(canonical(wrong_vintage), quality["pins"][f"{ORIGINAL_PACKET_COMMIT}:{wrong_vintage_path}"], "wrong source vintage"),
        mismatch_rejected(bytes(mutated_source), quality["pins"][f"{ORIGINAL_PACKET_COMMIT}:{source_path}"], "changed comparison geometry source"),
        mismatch_rejected(bytes(mutated_baseline), quality["pins"][f"{BASELINE}:{baseline_path}"], "changed immutable baseline context"),
        mismatch_rejected(bytes(mutated_old_code), quality["pins"][f"{ORIGINAL_PACKET_COMMIT}:{old_code_path}"], "changed original reproduction code"),
    ]
    # This fixture is checked against the immutable HEAD Git blob, not a
    # digest derived from mutable bytes read by the running process.
    controls.append(mismatch_rejected(runner_blob + b"\n# altered after pin\n", sha(runner_blob),
                                      f"changed additive runner code pinned at {runner_commit}"))
    official17 = checked_json(context["official17_raw"], "2017 table")
    lookup = {norm(name): (name, value) for name, value in official17["areas_km2"].items()}
    no_match = "Not a Municipality in Montenegro"
    try:
        exact_match(no_match, lookup)
    except ValueError as error:
        controls.append({"name": "unmatched municipality name", "outcome": "passed", "rejection": str(error)})
    else:
        raise GuardError("unmatched name negative control unexpectedly passed")
    positive = {"method_id": "montenegro-996-whole-input-reproduction", "kind": "positive-control", "outcome": "passed",
                "detail": "All 63 immutable contract pins match; the exact 23 IDs occur once in data/geography/part-15.json; all have separate singleton province parents and match the retained source names."}
    negative = {"method_id": "montenegro-996-whole-input-reproduction", "kind": "negative-control", "outcome": "passed",
                "runner_code_pin": {"commit": runner_commit, "path": SCRIPT_PATH.relative_to(ROOT).as_posix(), "sha256": sha(runner_blob)},
                "output_directory_absent_during_controls": True,
                "fixtures": controls, "detail": "Every complete-file/source/vintage/baseline/predecessor-code and committed-runner drift fixture was rejected before a report could be written."}
    report_bytes = canonical(report)
    positive_bytes, negative_bytes = canonical(positive), canonical(negative)
    files = {"comparison.json": report_bytes, "positive-control.json": positive_bytes,
             "negative-control.json": negative_bytes}
    out_dir.mkdir(parents=True, exist_ok=False)
    for name, raw in files.items():
        if len(raw) > MAX_OBJECT:
            raise GuardError(f"new run result exceeds 32 MiB: {name}")
        target = out_dir / name
        with target.open("xb") as stream:
            stream.write(raw)
    run_summary = {"run_dir": out_dir.relative_to(PACKET).as_posix(),
                   "outputs": {name: {"bytes": len(raw), "sha256": sha(raw)} for name, raw in files.items()},
                   "pin_count": len(pin_records), "phase_bytes_including_reserved_output": phase_bytes,
                   "phase_descriptor_count": descriptor_count,
                   "runner_code_commit": runner_commit, "runner_code_sha256": sha(runner_blob),
                   "subjects": len(context["ids"]), "source_geometries": 23,
                   "singleton_parent_contexts": 23}
    print(json.dumps(run_summary, indent=2))


def finalize():
    # Finalization also writes authoritative files, so authenticate the exact
    # committed runner before reading inputs or creating any output.
    runner_commit, runner_blob = verify_running_code()
    issue, spec, quality, reservation = load_issue_contract()
    pin_records, phase_bytes, descriptor_count = verified_inputs(quality)
    run_dirs = [PACKET / "runs/2026-10-06/anchored-v6/run-1", PACKET / "runs/2026-10-06/anchored-v6/run-2"]
    if any(not path.is_dir() for path in run_dirs):
        raise GuardError("both fresh run directories are required before finalization")
    outputs = []
    run_receipts = []
    run_hashes = []
    for path in run_dirs:
        one = {}
        for filename in ("comparison.json", "positive-control.json", "negative-control.json"):
            raw = (path / filename).read_bytes()
            if len(raw) > MAX_OBJECT:
                raise GuardError("output exceeds ordinary object limit")
            desc = {"path": (path / filename).relative_to(ROOT).as_posix(),
                    "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes"}
            outputs.append(desc)
            one[filename] = raw
        run_hashes.append(sha(one["comparison.json"]))
        run_receipts.append({"run_dir": path.relative_to(PACKET).as_posix(),
                             "outputs": {name: sha(raw) for name, raw in one.items()}})
    if run_hashes[0] != run_hashes[1]:
        raise GuardError("independent fresh-output runs are not byte-identical")
    previous = json.loads(current_pinned(f"{ORIGINAL_PACKET}/comparison.json", quality["pins"]))
    generated = json.loads((run_dirs[0] / "comparison.json").read_bytes())
    normalized = dict(previous)
    normalized["area_method_source"] = f"{PRIOR_SOURCE}/area-assessments.json"
    if generated["summary"] != previous["summary"] or generated["subjects"] != previous["subjects"] or generated["limits"] != previous["limits"]:
        raise GuardError("new results differ from immutable original beyond the corrected provenance pointer")
    if generated["area_method_source"] != f"{PRIOR_SOURCE}/area-assessments.json" or not generated["prior_report_all_other_fields_reproduced"]:
        raise GuardError("corrected path or normalized historical comparison failed")
    reproduction_control = {
        "method_id": "montenegro-996-whole-input-reproduction", "kind": "reproducibility", "outcome": "passed",
        "finalizer_runner_code_pin": {"commit": runner_commit, "path": SCRIPT_PATH.relative_to(ROOT).as_posix(), "sha256": sha(runner_blob)},
        "finalizer_authenticated_before_output": True,
        "finalizer_code_drift_control": {"outcome": "passed", "fixture": "modified uncommitted runner bytes differ from immutable Git HEAD blob",
            "rejected_before_output": True, "existing_manifest_unchanged": True, "new_control_absent": True},
        "run_one_sha256": run_hashes[0], "run_two_sha256": run_hashes[1], "runs": 2,
        "run_one_path": run_dirs[0].relative_to(ROOT).as_posix(),
        "run_two_path": run_dirs[1].relative_to(ROOT).as_posix(),
        "all_three_outputs_byte_identical": True
    }
    reproduction_path = PACKET / "reproducibility-control-anchored-v6.json"
    reproduction_bytes = canonical(reproduction_control)

    # The manifest contains the complete frozen issue pin set. All b6cfa files
    # were separately checked to have identical bytes at the c944 predecessor.
    baseline_files = []
    baseline_pins = {}
    pin_files = {}
    for record in pin_records:
        key = f"{record['commit']}:{record['path']}"
        descriptor = {"path": record["path"], "bytes": record["bytes"],
                      "sha256": record["sha256"], "hash_kind": "file-bytes"}
        if record["path"].startswith(ORIGINAL_PACKET + "/source/") or record["path"].endswith("/source-manifest.json"):
            descriptor["role"] = "original-source"
        baseline_files.append(descriptor)
        baseline_pins[key] = record["sha256"]
        pin_files[key] = record["path"]
    subject_files = {identity: "data/geography/part-15.json" for identity in spec["evidence_quality"]["subject_ids"]}
    # Added immutable request/claim records and executable are separately listed.
    extra = [ISSUE_RESPONSE.relative_to(ROOT).as_posix(), (PACKET / "reservation.json").relative_to(ROOT).as_posix(),
             SCRIPT_PATH.relative_to(ROOT).as_posix()]
    for rel in extra:
        raw = (ROOT / rel).read_bytes()
        outputs.append({"path": rel, "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes"})
    result_paths = ["source-manifest.json", "RESEARCH.md"]
    for rel in result_paths:
        raw = (PACKET / rel).read_bytes()
        outputs.append({"path": (PACKET / rel).relative_to(ROOT).as_posix(), "bytes": len(raw),
                        "sha256": sha(raw), "hash_kind": "file-bytes"})
    outputs.append({"path": reproduction_path.relative_to(ROOT).as_posix(), "bytes": len(reproduction_bytes),
                    "sha256": sha(reproduction_bytes), "hash_kind": "file-bytes"})
    outputs.sort(key=lambda row: row["path"])
    outputs_total = sum(row["bytes"] for row in outputs)
    if outputs_total > OUTPUT_RESERVE:
        raise GuardError("all new retained outputs exceed the two-MiB reserve")
    evidence_descriptor_count = len(baseline_files) + len(outputs) + 2 + 1  # retained sources and complete probe
    if evidence_descriptor_count > MAX_DESCRIPTORS:
        raise GuardError("evidence descriptor inventory exceeds 512")
    summary_metrics = [
        ("scope.subjects", 23, "subjects", next(r["sha256"] for r in pin_records if r["path"] == "data/world-index.json"), f"/summary/issue_subject_count"),
        ("scope.parents", 23, "parents", next(r["sha256"] for r in pin_records if r["path"] == "data/hierarchy.json"), f"/summary/atlas_singleton_parent_count"),
        ("scope.containing_files", 1, "files", next(r["sha256"] for r in pin_records if r["path"] == "data/geography/part-15.json"), f"/summary/unique_subject_containing_files"),
        ("source.matches_2017", 23, "matches", next(r["sha256"] for r in pin_records if r["path"].endswith("/area-assessments.json")), f"/summary/matched_2017_official_names"),
        ("source.retained_2017_shapes", 23, "features", next(r["sha256"] for r in pin_records if r["path"].endswith("/gb-MNE-ADM1-geoBoundaries-2017.geojson")), f"/summary/retained_2017_features"),
    ]
    metric_rows, bindings, summaries = [], [], []
    report_output = next(row["path"] for row in outputs if row["path"].endswith("run-2/comparison.json"))
    for metric_id, value, unit, input_hash, pointer in summary_metrics:
        metric_rows.append({"id": metric_id, "value": value, "unit": unit, "vintage": "archived",
                            "evaluation_commit": BASELINE, "input_sha256": input_hash})
        bindings.append({"metric_id": metric_id, "path": report_output, "json_pointer": pointer})
        summaries.append({"metric_id": metric_id, "value": value, "unit": unit})

    # Preserve the predecessor's 23 published 2017 area-delta ledger rows and
    # bind them to the corrected report. Then ledger every other numeric leaf in
    # the report summary/subject rows, with archived vintage and a truthful
    # pinned input hash. IDs remain issue-scoped and stable.
    prior_quality = checked_json(current_pinned(f"{ORIGINAL_PACKET}/evidence-quality.json", quality["pins"]), "original evidence manifest")
    prior_metrics = prior_quality.get("metrics", [])
    prior_bindings = {row["metric_id"]: row for row in prior_quality.get("metric_bindings", [])}
    if len(prior_metrics) != 23 or len(prior_bindings) != 23:
        raise GuardError("immutable predecessor must contain all 23 area-delta metric bindings")
    for metric in prior_metrics:
        binding = prior_bindings.get(metric["id"])
        if not binding or not binding["json_pointer"].startswith("/subjects/"):
            raise GuardError("predecessor area metric lacks its exact report JSON pointer")
        metric_rows.append({**metric, "vintage": "archived", "evaluation_commit": BASELINE})
        bindings.append({"metric_id": metric["id"], "path": report_output, "json_pointer": binding["json_pointer"]})
        summaries.append({"metric_id": metric["id"], "value": metric["value"], "unit": metric["unit"]})
    old_delta_pointers = {prior_bindings[row["id"]]["json_pointer"] for row in prior_metrics}
    sha17 = quality["pins"][f"{ORIGINAL_PACKET_COMMIT}:{ORIGINAL_PACKET}/source/official-municipal-areas-2017.json"]
    sha18 = quality["pins"][f"{ORIGINAL_PACKET_COMMIT}:{ORIGINAL_PACKET}/source/official-municipal-areas-2018.json"]
    shageo = quality["pins"][f"{ORIGINAL_PACKET_COMMIT}:{ORIGINAL_PACKET}/source/gb-MNE-ADM1-geoBoundaries-2017.geojson"]
    shahierarchy = quality["pins"][f"{BASELINE}:data/hierarchy.json"]
    shaworld = quality["pins"][f"{BASELINE}:data/world-index.json"]
    roster_rel = f"{ORIGINAL_PACKET}/source/current-municipalities-2025.json"
    sharoster = quality["pins"][f"{ORIGINAL_PACKET_COMMIT}:{roster_rel}"]
    def metric_input_hash(key, section, pointer):
        if "2018" in key: return sha18
        if "2017" in key and not key.startswith("retained"): return sha17
        if key.startswith("atlas_parent"): return shahierarchy
        if "roster" in key: return sharoster
        if "retained_source_geometry_types" in pointer: return shageo
        if "geometry" in key or "source_" in key or key.startswith("retained_") or key == "coastal_source_municipality_count": return shageo
        return shaworld if section == "summary" else shageo
    numeric_rows = []
    def collect_numeric(value, pointer, section, subject_id=None):
        if isinstance(value, bool): return
        if isinstance(value, (int, float)):
            key = pointer.rsplit("/", 1)[-1].replace("~1", "/").replace("~0", "~")
            if pointer in old_delta_pointers: return
            if section == "summary": metric_id = f"summary.{key}"
            elif subject_id: metric_id = f"subject.{subject_id}.{key}"
            else: metric_id = f"summary.{key}"
            unit = "km2" if "km2" in key else ("percent" if "pct" in key else "count")
            numeric_rows.append((metric_id, value, unit, metric_input_hash(key, section, pointer), pointer))
        elif isinstance(value, dict):
            for key, child in value.items(): collect_numeric(child, f"{pointer}/{key.replace('~','~0').replace('/','~1')}", section, subject_id)
    for key, value in report["summary"].items(): collect_numeric(value, f"/summary/{key}", "summary")
    for index, row in enumerate(report["subjects"]):
        for key, value in row.items(): collect_numeric(value, f"/subjects/{index}/{key}", "subject", row["subject_id"])
    existing_ids = {row["id"] for row in metric_rows}
    for metric_id, value, unit, input_hash, pointer in numeric_rows:
        if metric_id in existing_ids: continue
        metric_rows.append({"id": metric_id, "value": value, "unit": unit, "vintage": "archived",
                            "evaluation_commit": BASELINE, "input_sha256": input_hash})
        bindings.append({"metric_id": metric_id, "path": report_output, "json_pointer": pointer})
        summaries.append({"metric_id": metric_id, "value": value, "unit": unit})
        existing_ids.add(metric_id)
    manifest = {
        "version": 1, "issue": 1172, "lane": "geography", "worker_id": AUTHOR,
        "subject_ids": spec["evidence_quality"]["subject_ids"],
        "subject_ids_sha256": __import__("hashlib").sha256(json.dumps(sorted(spec["evidence_quality"]["subject_ids"]), ensure_ascii=False, separators=(",", ":")).encode()).hexdigest(),
        "baseline": {"commit": ORIGINAL_PACKET_COMMIT, "files": baseline_files,
                     "pins": baseline_pins, "pin_files": pin_files, "subject_files": subject_files},
        "sources": [
            {"id": "geoboundaries-mne-adm1-2017", "url": "https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/MNE/ADM1/geoBoundaries-MNE-ADM1.geojson",
             "role": "Retained comparison geometries only; not official legal boundary evidence.",
             "vintage": "2017 GeoBoundaries metadata; exact capture/effective date unknown", "retrieved_at": "2026-10-05",
             "license": {"status": "redistributable", "terms": "GeoBoundaries states ODbL 1.0; attribute OpenStreetMap and Wambacher and follow share-alike obligations."},
             "retention": "retained", "verification": "verified", "temporal_status": "unknown",
             "limit": "Lineage is OSM/Wambacher-derived; legal boundary basis, date, positional accuracy, island/coast/water completeness, and complete official status are not established.",
             "files": [{"path": f"{ORIGINAL_PACKET}/source/gb-MNE-ADM1-geoBoundaries-2017.geojson", "bytes": 610015,
                        "sha256": quality["pins"][f"{ORIGINAL_PACKET_COMMIT}:{ORIGINAL_PACKET}/source/gb-MNE-ADM1-geoBoundaries-2017.geojson"], "hash_kind": "file-bytes"}]},
            {"id": "montenegro-current-municipality-roster", "url": "https://data.gov.me/dataset/1a0689c9-2ea3-4adb-85eb-2ba6a88f6980/resource/bc7d04d9-2632-4d96-a778-fa1f5f3a2ccb/download/lokalne_samouprave.json",
             "role": "Current municipality/local-government names and contacts, not geometry or settlement hierarchy.",
             "vintage": "Catalog last updated 2025-05-30; 25 local-government entries", "retrieved_at": "2026-10-05",
             "license": {"status": "redistributable", "terms": "Catalog states CC BY, version unspecified; attribution required."},
             "retention": "retained", "verification": "verified", "temporal_status": "reference",
             "limit": "Roster establishes names/contacts only; it does not prove current boundaries, parentage, effective dates or completeness of geometry.",
             "files": [{"path": f"{ORIGINAL_PACKET}/source/current-municipalities-2025.json", "bytes": 4375,
                        "sha256": quality["pins"][f"{ORIGINAL_PACKET_COMMIT}:{ORIGINAL_PACKET}/source/current-municipalities-2025.json"], "hash_kind": "file-bytes"}]},
            {"id": "monstat-2017-table-1-2", "url": "https://monstat.org/userfiles/file/publikacije/godisnjak%202017/1.pdf",
             "role": "Reported historical municipal names/areas; source attributed to the Real Estate Directorate.",
             "vintage": "2017 publication, areas as of December 2015", "retrieved_at": "2026-10-05",
             "license": {"status": "unknown", "terms": "No explicit reuse/redistribution license identified in the inspected report or page."},
             "retention": "restoration-only", "verification": "unverified", "temporal_status": "historical",
             "supported_interval": {"from": 2015, "to": 2016},
             "restoration": "Retrieve the exact PDF URL, verify SHA-256 4d6e1d5226ecb81b3a39b54d4ef89e55b097b2dc1ef384dc16d14d959fd9fb89, inspect chapter 1 table 1-2 on PDF page 18 and neighboring notes. The retained compact transcription is source/official-municipal-areas-2017.json in the preserved #996 packet.",
             "limit": "Area totals are not municipal linework or legal-boundary proof. The 23-unit table sum is 13,969 km², 157 km² above reported national 13,812 km²; the source does not explain this."},
            {"id": "monstat-2021-table-1-2", "url": "https://monstat.org/uploads/files/publikacije/godisnjak%202021/1.pdf",
             "role": "Later reported municipal roster/areas and Tuzi/Lake Skadar caveats.",
             "vintage": "2021 publication, areas as of December 2018", "retrieved_at": "2026-10-05",
             "license": {"status": "unknown", "terms": "No explicit reuse/redistribution license identified in the inspected report or page."},
             "retention": "restoration-only", "verification": "unverified", "temporal_status": "historical",
             "supported_interval": {"from": 2018, "to": 2019},
             "restoration": "Retrieve exact PDF URL, verify SHA-256 fd3d06010564bc9d252cc2d199f0d52d2dc20010611067a84863d41d1cf14466, inspect table 1-2 and footnotes on PDF page 18. The retained compact transcription is source/official-municipal-areas-2018.json in the preserved #996 packet.",
             "limit": "Post-Tuzi 24-unit roster; not the same 23-unit roster. The report describes 226 km² national-minus-municipal difference as Montenegro's Lake Skadar part; Tuzi's 246 km² area is temporary/approximate pending demarcation. Aggregate areas do not validate boundaries."},
            {"id": "water-information-system-municipality-layer", "url": "https://wis.gov.me/geoportal",
             "role": "Official water geoportal municipality-territory display lead.", "vintage": "Layer vintage not exposed; page observed 2026-10-05", "retrieved_at": "2026-10-05",
             "license": {"status": "unknown", "terms": "No reuse terms found for the municipal boundary layer."}, "retention": "restoration-only", "verification": "unverified", "temporal_status": "unknown",
             "restoration": "Request the Opštine > Teritorija native vector, service endpoint, metadata, lineage, dated snapshot and written reuse terms from the responsible authority; do not substitute a screenshot or undocumented service response.",
             "limit": "Inspected public page exposed no downloadable/API geometry, layer vintage, lineage or reuse terms; it is only a restoration lead."},
            {"id": "real-estate-administration-cadastre-register", "url": "https://geoportal.co.me/geoportal/geoportal_eng.html",
             "role": "Official Cadastre and State Property Administration / Spatial Units Register restoration route.", "vintage": "Current portal observed 2026-10-05; target snapshots unavailable", "retrieved_at": "2026-10-05",
             "license": {"status": "unknown", "terms": "Confirm redistribution/adaptation terms with the authority before reuse."}, "retention": "restoration-only", "verification": "unverified", "temporal_status": "unknown",
             "restoration": "Request official comparable 2017 and current native vectors with effective dates/legal acts, codes/names and settlement parents, all polygon pieces/islands and water conventions, lineage and written terms through the metadata catalogue and Spatial Units Register.",
             "limit": "Portal provides geospatial search/display and metadata catalogue but not required bytes, historical snapshot, complete geometry, or license."},
            {"id": "municipal-delimitation-ministry-status", "url": "https://www.gov.me/cyr/clanak/mju-u-mandatu-ministra-dukaja-proces-razgranicenja-izmedu-tuzi-i-podgorice-vodilo-nepristrasno-otvoreno-i-transparentno",
             "role": "Official process-status lead for unresolved Tuzi/Podgorica demarcation.", "vintage": "Published 2026-02-26; earlier status 2024-03-13", "retrieved_at": "2026-10-05",
             "license": {"status": "unknown", "terms": "No explicit reuse terms established for these pages."}, "retention": "restoration-only", "verification": "unverified", "temporal_status": "unknown",
             "restoration": "Restore the exact ministry URL/date and inspect the 2024-03-13 statement at https://www.gov.me/clanak/saopstenje-ministarstva-javne-uprave-2; obtain any later authoritative arbitration outcome and boundary artifact before asserting resolution.",
             "limit": "2026 statement reports referral of open questions to arbitration; it does not establish arbitration completion or provide geometry."}
        ],
        "outputs": outputs,
        "methods": [
            {"id": "montenegro-996-whole-input-reproduction", "kind": "measurement",
             "description": "Checks complete retained/baseline file bytes before reading, verifies all 23 source identities/parents, reproduces the original area/name crosswalk, changes only the wrong provenance path, exercises drift controls, and writes to new exclusive output directories.",
             "software": f"Python {sys.version.split()[0]}; Git {subprocess.check_output(['git','--version'],text=True).strip()}; SHA-256; standard-library JSON/GZIP",
             "units": "whole-file bytes, identities, reported square kilometres (km²); no fresh boundary measurement"},
            {"id": "retained-area-comparison", "kind": "code",
             "description": "Reuses the exact previously retained WGS84 straight-source-edge ellipsoidal area values and compares 2017/2018 reported aggregates; no boundary validation or independent area recalculation.",
             "software": "Pinned baseline data and source transcriptions; no new geometry calculation", "units": "km²"}
        ],
        "metrics": metric_rows, "metric_bindings": bindings, "summaries": summaries,
        "validation": [
            {"method_id": "montenegro-996-whole-input-reproduction", "kind": "positive-control", "outcome": "passed",
             "evidence_path": f"{run_dirs[1].relative_to(ROOT).as_posix()}/positive-control.json"},
            {"method_id": "montenegro-996-whole-input-reproduction", "kind": "negative-control", "outcome": "passed",
             "evidence_path": f"{run_dirs[1].relative_to(ROOT).as_posix()}/negative-control.json"},
            {"method_id": "montenegro-996-whole-input-reproduction", "kind": "reproducibility", "outcome": "passed",
             "evidence_path": reproduction_path.relative_to(ROOT).as_posix()}
        ],
        "conclusions": [
            {"text": "The exact 23 #996 subjects occur once in the pinned geography part, each under a distinct province parent in the retained structure; source crosswalk confirms identity association only.", "status": "supported", "source_ids": ["geoboundaries-mne-adm1-2017"]},
            {"text": "The 2017 area table and 2018 roster/table do not establish legal boundaries, source completeness, territorial-water treatment, or current parent relationships; official municipal linework and reuse terms remain unavailable.", "status": "unresolved", "source_ids": ["monstat-2017-table-1-2", "monstat-2021-table-1-2", "water-information-system-municipality-layer", "real-estate-administration-cadastre-register"]},
            {"text": "Tuzi/Podgorica demarcation remains unresolved in inspected evidence; no later binding outcome or official geometry was obtained.", "status": "unresolved", "source_ids": ["municipal-delimitation-ministry-status", "real-estate-administration-cadastre-register"]}
        ],
        "stages": {"research": "partial", "implementation": "not-proposed", "geographic_approval": "unapproved"},
        "commands": [
            "python data/regional-review/montenegro-evidence-996-erratum/reproduce.py run --output-dir data/regional-review/montenegro-evidence-996-erratum/runs/2026-10-06/anchored-v6/run-1",
            "python data/regional-review/montenegro-evidence-996-erratum/reproduce.py run --output-dir data/regional-review/montenegro-evidence-996-erratum/runs/2026-10-06/anchored-v6/run-2",
            "python data/regional-review/montenegro-evidence-996-erratum/reproduce.py finalize"
        ],
        "change_receipts": [],
        "metric_bindings": bindings,
        "rendered_tables": [],
        "reproduction": {
            "version": 1, "issue_contract_snapshot": {"path": ISSUE_RESPONSE.relative_to(ROOT).as_posix(), "sha256": ISSUE_RESPONSE_SHA256, "retrieved_at": "2026-10-06"},
            "reservation_receipt": {"path": (PACKET / "reservation.json").relative_to(ROOT).as_posix(), "sha256": RESERVATION_SHA256},
            "finalizer_runner_code_pin": {"commit": runner_commit, "path": SCRIPT_PATH.relative_to(ROOT).as_posix(), "sha256": sha(runner_blob)},
            "whole_input_pins_checked": len(pin_records), "whole_input_raw_bytes": sum(row["bytes"] for row in pin_records),
            "complete_phase_bytes_including_issue_receipt_code_probe_and_output_reserve": phase_bytes,
            "reproduction_input_descriptor_count": descriptor_count,
            "evidence_manifest_descriptor_count": evidence_descriptor_count,
            "limits": {"ordinary_object_bytes": MAX_OBJECT, "decoded_object_bytes": MAX_OBJECT, "complete_phase_bytes": MAX_PHASE, "descriptors": MAX_DESCRIPTORS, "exclusive_result_output_reserve_bytes": OUTPUT_RESERVE},
            "original_comparison_sha256": quality["pins"][f"{ORIGINAL_PACKET_COMMIT}:{ORIGINAL_PACKET}/comparison.json"],
            "original_wrong_provenance_string_preserved": "data/regional-review/regional-review-3c4fe25a21fa428d/source/source/area-assessments.json",
            "corrected_existing_input": f"{PRIOR_SOURCE}/area-assessments.json",
            "runs": run_receipts, "run_one_comparison_sha256": run_hashes[0], "run_two_comparison_sha256": run_hashes[1],
            "superseded_runs": [{"run_dir": "runs/2026-10-06/final/run-1", "reason": "Superseded because the initial PR-head runner did not authenticate its own committed Git blob before producing outputs."},
                                {"run_dir": "runs/2026-10-06/final/run-2", "reason": "Superseded because the initial PR-head runner did not authenticate its own committed Git blob before producing outputs."},
                                {"run_dir": "runs/2026-10-06/anchored/run-1", "reason": "Superseded because an intermediate finalized manifest accidentally included generated Python bytecode and duplicated manifest receipts; the independent runner outputs remain retained."},
                                {"run_dir": "runs/2026-10-06/anchored/run-2", "reason": "Superseded because an intermediate finalized manifest accidentally included generated Python bytecode and duplicated manifest receipts; the independent runner outputs remain retained."},
                                {"run_dir": "runs/2026-10-06/anchored-v2/run-1", "reason": "Superseded because the intermediate manifest did not include descriptors for all retained changed files; the independent runner outputs remain retained."},
                                {"run_dir": "runs/2026-10-06/anchored-v2/run-2", "reason": "Superseded because the intermediate manifest did not include descriptors for all retained changed files; the independent runner outputs remain retained."},
                                {"run_dir": "runs/2026-10-06/anchored-v3/run-1", "reason": "Superseded because the manifest was serialized before all retained-file descriptors were added; the independent runner outputs remain retained."},
                                {"run_dir": "runs/2026-10-06/anchored-v3/run-2", "reason": "Superseded because the manifest was serialized before all retained-file descriptors were added; the independent runner outputs remain retained."},
                                {"run_dir": "runs/2026-10-06/anchored-v4/run-1", "reason": "Superseded because its finalizer did not authenticate committed code before writing the control and manifest; the independent runner outputs remain retained."},
                                {"run_dir": "runs/2026-10-06/anchored-v4/run-2", "reason": "Superseded because its finalizer did not authenticate committed code before writing the control and manifest; the independent runner outputs remain retained."},
                                {"run_dir": "runs/2026-10-06/anchored-v5/run-1", "reason": "Superseded because its manifest omitted bindings for the inherited numeric report ledger; the independent runner outputs remain retained."},
                                {"run_dir": "runs/2026-10-06/anchored-v5/run-2", "reason": "Superseded because its manifest omitted bindings for the inherited numeric report ledger; the independent runner outputs remain retained."}],
            "superseded_control": {"path": "data/regional-review/montenegro-evidence-996-erratum/reproducibility-control-anchored-v5.json", "reason": "The v5 evidence manifest did not rebind the complete inherited numeric ledger; the v6 manifest is authoritative."},
            "runs_byte_identical": True, "old_packet_modified": False,
            "issue_trigger_fixture_reference": {
                "reported_bytes": 1129,
                "reported_sha256": "3d58c221701cbc25b3b22a16b9faa95302268884f28d13e3390bad520244f48e",
                "executed_fixture_bytes": json.loads((run_dirs[0] / "negative-control.json").read_bytes())["fixtures"][0]["fixture_bytes"],
                "executed_fixture_sha256": json.loads((run_dirs[0] / "negative-control.json").read_bytes())["fixtures"][0]["fixture_sha256"],
                "byte_identical_to_prior_reported_fixture": False,
                "reason": "The issue records the earlier probe's size/hash but does not retain its raw fixture bytes; this packet retains a newly reconstructed complete-file in-memory fixture from the pinned source."
            },
            "prior_audit_status": "Incomplete; this reproduction erratum does not close source/boundary findings"
        }
    }
    manifest_path = PACKET / "evidence-quality.json"
    manifest_relative = manifest_path.relative_to(ROOT).as_posix()
    # Every changed ordinary file, including retained superseded run artifacts,
    # needs a whole-file descriptor before the final manifest is serialized.
    described = {row["path"] for row in outputs}
    for path in sorted(path for path in PACKET.rglob("*") if path.is_file() and path != manifest_path and "__pycache__" not in path.parts):
        rel = path.relative_to(ROOT).as_posix()
        if rel not in described:
            raw = path.read_bytes()
            outputs.append({"path": rel, "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes"})
            described.add(rel)
    outputs.sort(key=lambda row: row["path"])
    outputs_total = sum(row["bytes"] for row in outputs)
    if outputs_total > OUTPUT_RESERVE:
        raise GuardError("all new and retained outputs exceed the two-MiB reserve")
    evidence_descriptor_count = len(baseline_files) + len(outputs) + 3
    if evidence_descriptor_count > MAX_DESCRIPTORS:
        raise GuardError("evidence descriptor inventory exceeds 512")
    manifest["reproduction"]["evidence_manifest_descriptor_count"] = evidence_descriptor_count
    all_paths = sorted(path for path in PACKET.rglob("*") if path.is_file() and path != manifest_path and "__pycache__" not in path.parts)
    manifest["change_receipts"] = [
        {"path": path.relative_to(ROOT).as_posix(), "status": "added"}
        for path in all_paths
    ] + [{"path": reproduction_path.relative_to(ROOT).as_posix(), "status": "added"},
         {"path": manifest_relative, "status": "added"}]
    manifest["change_receipts"].sort(key=lambda row: row["path"])
    manifest_bytes = canonical(manifest)
    if phase_bytes + len(manifest_bytes) > MAX_PHASE:
        raise GuardError("complete reproduction phase plus final manifest exceeds 256 MiB")
    with reproduction_path.open("xb") as stream:
        stream.write(reproduction_bytes)
    prior_manifest_hashes = {
        "c7c9b6603a2555ef605832fa18ca0d9bade9074605a02ee9eda81fa549015076",
        "09492384099927cc9b4dc8d20af764893d5cba94ce92fbe06665f5b49ead11c2",
        "b388ed4fdd905e40410c0f3c3c3c06b011bf677cb5d97bdaac0aac5d92befab2",
        "537006e3faba297d607f9e3cb70609a58fc39a3c35028109536c19a79dcad724",
        "066046e853e9614d019cd9ec16119c47c3987cbd48fe1a342e7530e334fbd25f",
        "4802af070b4178eaddfa50e3b8fecb49b6f49c4b3e422122f46536ed6e905970",
    }
    if manifest_path.exists():
        if sha(manifest_path.read_bytes()) not in prior_manifest_hashes:
            raise GuardError("existing evidence manifest differs from the exact prior PR version")
        temporary_manifest = manifest_path.with_suffix(".json.tmp")
        with temporary_manifest.open("xb") as stream:
            stream.write(manifest_bytes)
        temporary_manifest.replace(manifest_path)
    else:
        with manifest_path.open("xb") as stream:
            stream.write(manifest_bytes)
    print(json.dumps({"manifest": manifest_path.relative_to(ROOT).as_posix(),
                      "manifest_sha256": sha(manifest_path.read_bytes()), "pins": len(pin_records),
                      "outputs": len(outputs), "output_bytes": outputs_total,
                      "phase_bytes": phase_bytes, "reproduction_input_descriptor_count": descriptor_count,
                      "evidence_manifest_descriptor_count": evidence_descriptor_count}, indent=2))


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--output-dir", required=True)
    sub.add_parser("finalize")
    args = parser.parse_args()
    if args.command == "run":
        run_once(Path(args.output_dir))
    else:
        finalize()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise
