#!/usr/bin/env python3
"""Strict exact-identity recorder for complete corrected #1385 run vintages."""
from __future__ import annotations

import argparse
import gzip
import json
import os
import pathlib
import shutil
import stat
import subprocess
import sys

import reproduce
from evidence_core import BASE, HERE, OWNED, ROOT, Phase, canonical, deterministic_gzip, sha, source_lock, verify_code, secure_publish
from reproduce import EXPECTED_SUBJECTS, REGISTRY_PATH, SOURCE_PATHS, ATLAS_PATH, HIERARCHY_PATH, custody_phase, fragment_phase, pinmap
from safe_vintage import read_complete

RUN_FILES = {"custody-phase.json.gz", "fragment-phase.json.gz", "source-geometry-results.json.gz", "run-summary.json"}


def unpack(raw: bytes):
    return json.loads(gzip.decompress(raw))


def load_runs(one: str, two: str):
    phase = Phase("run-pair-and-prior-evidence", [], pin_map=pinmap())
    loaded = []
    for label, vintage in (("run-one", one), ("run-two", two)):
        receipt, files = read_complete(vintage, RUN_FILES)
        decoded = {}
        for name, raw in files.items():
            phase.admit(label + ":" + name, raw)
            data = gzip.decompress(raw) if name.endswith(".gz") else raw
            if name.endswith(".gz"):
                phase.admit(label + ":" + name + ":decoded", data)
            decoded[name] = data
        loaded.append({"label": label, "vintage": vintage, "receipt": receipt, "files": files, "decoded": decoded})
    return phase, loaded


def read_old_result(phase: Phase):
    pin = next(p for p in source_lock()["pins"] if p["id"] == "original_1244_10")
    raw = subprocess.check_output(["git", "-C", str(ROOT), "show", f'{pin["commit"]}:{pin["path"]}'])
    if len(raw) != pin["bytes"] or sha(raw) != pin["sha256"]:
        raise ValueError("Retained original successful measurement pin mismatch")
    phase.admit("retained-original-run-one", raw)
    decoded = gzip.decompress(raw)
    phase.admit("retained-original-run-one:decoded", decoded)
    return json.loads(decoded), {"path": pin["path"], "commit": pin["commit"], "bytes": len(raw), "sha256": sha(raw), "decoded_bytes": len(decoded), "decoded_sha256": sha(decoded)}


def expected_subject_records(phase: Phase, pmap: dict):
    paths = [*SOURCE_PATHS.values(), ATLAS_PATH, HIERARCHY_PATH, REGISTRY_PATH]
    source_phase = Phase("subject-identity-source", paths, pin_map=pmap)
    products = {}
    for code, path in SOURCE_PATHS.items():
        data = json.loads(source_phase.raw(path))
        found = {}
        for index, feature in enumerate(data["features"]):
            props = feature["properties"]
            if props.get("shapeGroup") != code or props.get("shapeType") != "ADM2":
                raise ValueError("Authenticated source has wrong neighboring administrative level")
            key = props.get("shapeID")
            if key in found:
                raise ValueError("Authenticated source feature ID is duplicated")
            found[key] = {"index": index, "feature": feature, "sha256": sha(canonical(feature))}
        products[code] = found
    atlas_features = json.loads(source_phase.raw(ATLAS_PATH))["features"]
    atlas = {row.get("id"): row for row in atlas_features}
    if len(atlas) != len(atlas_features):
        raise ValueError("Native Atlas feature identity is duplicated")
    hierarchy = json.loads(source_phase.raw(HIERARCHY_PATH))
    hierarchy_rows = {row["id"]: row for row in hierarchy}
    registry = json.loads(source_phase.raw(REGISTRY_PATH))
    expected = {}
    for subject_id, spec in EXPECTED_SUBJECTS.items():
        original = products[spec["country"]].get(spec["shapeID"])
        atlas_row = atlas.get(subject_id)
        if not original or not atlas_row:
            raise ValueError("Exact native source or Atlas subject absent")
        props = atlas_row.get("properties", {})
        if (original["feature"]["properties"].get("shapeName") != spec["name"]
                or props.get("id") != subject_id or props.get("parent_id") != spec["parent_id"]
                or spec["parent_id"] not in hierarchy_rows
                or hierarchy_rows[spec["parent_id"]].get("level") != "province"):
            raise ValueError("Pinned source-to-Atlas identity/parent contract changed")
        if props.get("metadata", {}).get("semantic_review", {}).get("status") != "open":
            raise ValueError("Expected open semantic status; research must not certify a parent")
        expected[subject_id] = {"country": spec["country"], "shapeID": spec["shapeID"], "name": spec["name"],
            "parent_id": spec["parent_id"], "source_feature_index": original["index"],
            "source_feature_sha256": original["sha256"], "atlas_feature_sha256": sha(canonical(atlas_row)),
            "source_geojson_sha256": source_phase.baseline.pins[SOURCE_PATHS[spec["country"]]]["sha256"],
            "source_geojson_bytes": source_phase.baseline.pins[SOURCE_PATHS[spec["country"]]]["bytes"],
            "source_geojson_path": SOURCE_PATHS[spec["country"]],
            "source_registry_sha256": registry["gb:" + spec["country"] + ":ADM2"]["sha256"]}
    source_phase_bytes = sum(source_phase.baseline.consumed.values())
    return expected, {"phase": "subject-identity-source", "inputs": source_phase.records,
                      "bytes": source_phase_bytes, "subjects_verified": len(expected)}


def validate_result(result: dict, custody: dict, fragments: dict, expected_subjects: dict):
    component_ids = custody["component_ids"]
    subject_ids = list(EXPECTED_SUBJECTS)
    if result.get("component_ids") != component_ids or len(set(result["component_ids"])) != 10:
        raise ValueError("Exact ten unique component IDs are required")
    rows = result.get("components")
    if not isinstance(rows, list) or len(rows) != 10 or len({row.get("component_id") for row in rows}) != 10:
        raise ValueError("Component rows must contain exactly ten unique identities")
    by_component = {row["component_id"]: row for row in rows}
    if set(by_component) != set(component_ids):
        raise ValueError("Missing, duplicate or fabricated component ID")
    for identity in component_ids:
        row = by_component[identity]
        original = custody["component_features"].get(identity)
        if not original or row.get("original_component_feature") != original or row.get("component_feature_sha256") != sha(canonical(original)):
            raise ValueError("Component feature identity or exact source record changed: " + identity)
        if row.get("component_id") != original.get("id") or row.get("administrative_assignment") is not None:
            raise ValueError("Component identity/territorial assignment contract changed")
    subjects = result.get("registered_subject_comparisons")
    if not isinstance(subjects, list) or len(subjects) != 4 or len({row.get("subject_id") for row in subjects}) != 4:
        raise ValueError("Subject comparisons must contain exactly four unique native identities")
    by_subject = {row["subject_id"]: row for row in subjects}
    if set(by_subject) != set(subject_ids):
        raise ValueError("Missing or fabricated native subject identity")
    for identity, expected in expected_subjects.items():
        row = by_subject[identity]
        for key, value in (("source_shapeID", expected["shapeID"]), ("source_name", expected["name"]),
                           ("source_feature_index", expected["source_feature_index"]),
                           ("source_feature_sha256", expected["source_feature_sha256"]),
                           ("atlas_feature_sha256", expected["atlas_feature_sha256"]),
                           ("atlas_parent_id", expected["parent_id"])):
            if row.get(key) != value:
                raise ValueError("False native source, feature or parent binding for " + identity + ": " + key)
    source_products = result.get("source_products", {})
    for code in ("ZMB", "ZWE"):
        rows = [expected for expected in expected_subjects.values() if expected["country"] == code]
        if not rows or len(rows) != (3 if code == "ZMB" else 1):
            raise ValueError("Exact subject-to-source country grouping changed")
        product = source_products.get(code, {})
        if (product.get("path") != rows[0]["source_geojson_path"]
                or product.get("bytes") != rows[0]["source_geojson_bytes"]
                or product.get("sha256") != rows[0]["source_geojson_sha256"]
                or product.get("registry", {}).get("sha256") != rows[0]["source_registry_sha256"]):
            raise ValueError("Fabricated or wrong-vintage full country source binding: " + code)
    contact = result.get("original_source_contacts", {})
    expected_contact = custody["original_contact_rows"]
    if (contact.get("input_path") != custody["contact_input"]["path"]
            or contact.get("input_sha256") != custody["contact_input"]["raw_sha256"]
            or contact.get("matched_rows") != expected_contact
            or len(expected_contact) != 1 or expected_contact[0].get("kind") != "point-only-ambiguous"):
        raise ValueError("Exact original point-only contact row/geometry contract failed")
    expected_component_fragments = [fragments["features"][i] for i in sorted(custody["component_fragment_ids"])]
    expected_contact_fragments = [fragments["features"][i] for i in sorted(custody["contact_fragment_ids"])]
    if result.get("original_fragment_features") != expected_component_fragments:
        raise ValueError("Original component-fragment membership/features differ from complete candidate family")
    if result.get("original_contact_fragment_features") != expected_contact_fragments:
        raise ValueError("Original contact-fragment membership/features differ from complete candidate family")
    return {"outcome": "passed", "component_ids": component_ids, "subject_ids": subject_ids,
            "exact_contact_row_sha256": sha(canonical(expected_contact[0])),
            "component_feature_hashes": {k: sha(canonical(custody["component_features"][k])) for k in component_ids},
            "contact_kind": expected_contact[0]["kind"], "contact_geometry": expected_contact[0].get("geometry")}


def compare_original_measurements(current: dict, original: dict):
    checks = []
    def same(label, left, right):
        if left != right:
            raise ValueError("Corrected output differs from retained independently verified measurement: " + label)
        checks.append(label)
    for code in ("ZMB", "ZWE"):
        new, old = current["source_products"][code], original["source_products"][code]
        for key in ("path", "bytes", "sha256", "feature_count"):
            same(f"source_products.{code}.{key}", new[key], old[key])
        new, old = current["local_country_union_comparisons"][code], original["local_country_union_comparisons"][code]
        for new_key, old_key in (("source_local_union", "source_local_union"), ("atlas_local_union", "atlas_local_union"),
                                 ("source_minus_atlas", "source_minus_atlas_local_union"),
                                 ("atlas_minus_source", "atlas_minus_source_local_union"),
                                 ("source_candidate_indices", "source_bbox_candidate_indices"),
                                 ("source_candidate_shapeIDs", "source_bbox_candidate_shapeIDs"),
                                 ("atlas_candidate_ids", "atlas_bbox_candidate_ids"), ("extent", "comparison_extent")):
            same(f"local_country_union.{code}.{new_key}", new[new_key], old[old_key])
    old_subjects = {row["subject_id"]: row for row in original["registered_subject_comparisons"]}
    new_subjects = {row["subject_id"]: row for row in current["registered_subject_comparisons"]}
    if set(new_subjects) != set(old_subjects) or len(new_subjects) != 4:
        raise ValueError("Exact original subject measurement roster differs")
    for identity in old_subjects:
        for key in ("source_feature_index", "source_feature_sha256", "atlas_feature_sha256", "source_shapeID", "source_name",
                    "source_minus_atlas", "atlas_minus_source", "source_intersection", "source_covers_atlas", "atlas_covers_source"):
            same(f"registered_subjects.{identity}.{key}", new_subjects[identity][key], old_subjects[identity][key])
    old_components = {row["component_id"]: row for row in original["components"]}
    new_components = {row["component_id"]: row for row in current["components"]}
    if set(new_components) != set(old_components) or len(new_components) != 10:
        raise ValueError("Exact original component measurement roster differs")
    for identity in old_components:
        for key in ("component_feature_sha256", "original_component_feature", "source_feature_intersections",
                    "whole_relevant_source_union", "source_union_intersection", "component_minus_source_union",
                    "source_covered_area_missing_from_local_atlas_union", "classification", "water_status", "cause_status",
                    "administrative_assignment", "coordinate_scope"):
            same(f"components.{identity}.{key}", new_components[identity][key], old_components[identity][key])
    for name in ("controls", "original_source_contacts", "independent_water_diagnostics", "area_helper"):
        same(name, current[name], original[name])
    old_fragments = original["original_fragment_inputs"]
    new_fragments = current["original_fragment_inputs"]
    if len(old_fragments) != 17 or len(new_fragments) != 17:
        raise ValueError("Complete seventeen-shard fragment evidence inventory is required")
    for old, new in zip(old_fragments, new_fragments):
        for key in ("path", "bytes", "sha256", "uncompressed_bytes", "uncompressed_sha256"):
            same("original_fragment_inputs." + old["path"] + "." + key, new[key], old[key])
    same("original_fragment_features", current["original_fragment_features"], original["original_fragment_features"])
    same("original_contact_fragment_features", current["original_contact_fragment_features"], original["original_contact_fragment_features"])
    return checks


def mutate_result(result: dict, case: str):
    altered = json.loads(json.dumps(result))
    if case == "missing-subject":
        altered["registered_subject_comparisons"].pop()
    elif case == "duplicate-component":
        altered["components"] = [altered["components"][0] for _ in range(10)]
    elif case == "wrong-contact-kind":
        row = altered["original_source_contacts"]["matched_rows"][0]
        row["kind"] = "line-contact"
        row["geometry"] = {"type": "LineString", "coordinates": [[28.0, -17.0], [29.0, -17.0]]}
    elif case == "fabricated-source":
        altered["registered_subject_comparisons"][0]["source_shapeID"] = "FABRICATED-000000"
    elif case == "wrong-parent":
        altered["registered_subject_comparisons"][0]["atlas_parent_id"] = "framework:province:other:000000000000"
    elif case == "wrong-source-vintage":
        altered["source_products"]["ZMB"]["sha256"] = "0" * 64
    else:
        raise ValueError("Unknown altered complete-pair control")
    return altered


def write_pair_fixture(vintage: str, altered: dict, pmap: dict):
    raw = deterministic_gzip(canonical(altered))
    phase = Phase("complete-altered-pair-control", [], pin_map=pmap)
    phase.account_output("run-one.json.gz", raw)
    phase.account_output("run-two.json.gz", raw)
    receipt = secure_publish(vintage, ["run-one.json.gz", "run-two.json.gz"],
                             {"run-one.json.gz": raw, "run-two.json.gz": raw}, phase)
    return {"vintage": vintage, "result_bytes": len(raw), "result_sha256": sha(raw), "publication_sha256": sha(receipt)}


def run_drift_controls(vintage_prefix: str):
    pmap = pinmap()
    fixture_dir = HERE / "controls" / "drift-fixtures"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    path = SOURCE_PATHS["ZMB"]
    pin = pmap[path]
    raw = subprocess.check_output(["git", "-C", str(ROOT), "show", f'{BASE}:{path}'])
    altered = bytearray(raw)
    altered[-1] ^= 1
    input_fixture = fixture_dir / "altered-zmb-source.bin"
    if input_fixture.exists():
        if input_fixture.is_symlink() or input_fixture.read_bytes() != bytes(altered):
            raise ValueError("Existing altered-input control fixture changed; preserve and inspect it")
    else:
        input_fixture.write_bytes(altered)
    input_vintage = vintage_prefix + "-input-drift"
    proc = subprocess.run([sys.executable, str(HERE / "reproduce.py"), "--vintage", input_vintage,
                           "--input-override", path + "=controls/drift-fixtures/altered-zmb-source.bin"],
                          cwd=ROOT, text=True, capture_output=True)
    input_exists = (ROOT / OWNED / "vintages" / input_vintage).exists()
    input_case = {"method": "actual-corrected-producer-entrypoint-with-altered-bytes-for-an-actually-consumed-pinned-source",
        "path": path, "expected_sha256": pin["sha256"], "altered_bytes": len(altered), "altered_sha256": sha(bytes(altered)),
        "exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr, "output_vintage_created": input_exists}
    if proc.returncode == 0 or input_exists or "Actually consumed immutable input drift detected" not in proc.stderr:
        raise ValueError("Altered consumed source bytes were not refused before output")

    producer_path = HERE / "reproduce.py"
    original = producer_path.read_bytes()
    code_vintage = vintage_prefix + "-code-drift"
    try:
        producer_path.write_bytes(original + b"\n# actual code drift negative-control fixture\n")
        proc = subprocess.run([sys.executable, str(producer_path), "--vintage", code_vintage], cwd=ROOT, text=True, capture_output=True)
    finally:
        producer_path.write_bytes(original)
    code_exists = (ROOT / OWNED / "vintages" / code_vintage).exists()
    code_case = {"method": "actual-corrected-producer-entrypoint-with-mutated-consumed-project-code",
        "path": OWNED + "reproduce.py", "expected_sha256": sha(original), "altered_sha256": sha(original + b"\n# actual code drift negative-control fixture\n"),
        "exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr, "output_vintage_created": code_exists}
    verify_code()
    if proc.returncode == 0 or code_exists or "Actually executed candidate code differs" not in proc.stderr:
        raise ValueError("Altered actually consumed project code was not refused before output")
    return {"outcome": "passed", "input": input_case, "project_code": code_case,
            "preserved_input_fixture": {"path": str(input_fixture.relative_to(ROOT)), "bytes": len(altered), "sha256": sha(bytes(altered))}}


def run_publication_safety_controls(vintage_prefix: str):
    pmap = pinmap()
    base = ROOT / OWNED / "vintages"
    base.mkdir(parents=True, exist_ok=True)
    sample_name = "payload.json"
    payload = {sample_name: b'{"sample":"new evidence"}\n'}
    results = []

    def attempt(case, run_name, setup, expected_exception):
        directory = base / run_name
        setup(directory)
        before = {str(path.relative_to(base)): ("symlink:" + os.readlink(path) if path.is_symlink() else
                    sha(path.read_bytes()) if path.is_file() else "directory") for path in [directory, *directory.rglob("*")]}
        phase = Phase("publication-refusal-control", [], pin_map=pmap)
        try:
            secure_publish(run_name, [sample_name], payload, phase)
            raise AssertionError("Unsafe destination unexpectedly admitted: " + case)
        except expected_exception as error:
            pass
        after = {str(path.relative_to(base)): ("symlink:" + os.readlink(path) if path.is_symlink() else
                   sha(path.read_bytes()) if path.is_file() else "directory") for path in [directory, *directory.rglob("*")]}
        if before != after:
            raise ValueError("Refused destination changed: " + case)
        results.append({"case": case, "outcome": "refused-without-mutation", "before": before, "after": after})
        if directory.is_symlink() or directory.is_file():
            directory.unlink()
        elif directory.exists():
            shutil.rmtree(directory)

    def ordinary_file(directory):
        directory.mkdir()
        (directory / sample_name).write_bytes(b"ordinary-file-sentinel\n")

    def broken_link(directory):
        directory.mkdir()
        (directory / sample_name).symlink_to("missing-target.bin")

    def occupied(directory):
        directory.mkdir()
        (directory / "foreign-sentinel.bin").write_bytes(b"occupied-directory-owner\n")

    attempt("preexisting ordinary output file", vintage_prefix + "-existing-file", ordinary_file, FileExistsError)
    attempt("preexisting broken symlink output", vintage_prefix + "-broken-link", broken_link, ValueError)
    attempt("preexisting occupied directory", vintage_prefix + "-occupied-dir", occupied, FileExistsError)

    escaped = "../" + vintage_prefix + "-escaped"
    try:
        secure_publish(escaped, [sample_name], payload, Phase("escaped-path-control", [], pin_map=pmap))
        raise AssertionError("Escaped evidence destination unexpectedly admitted")
    except ValueError as error:
        results.append({"case": "escaped destination", "outcome": "refused-before-mutation", "reason": str(error), "destination": escaped})

    run_name = vintage_prefix + "-replacement-race"
    displaced_name = run_name + "-displaced"
    foreign_data = b"replacement-owner-sentinel\n"
    multi = {"first.json": b'{"first":true}\n', "second.json": b'{"second":true}\n'}
    phase = Phase("parent-replacement-control", [], pin_map=pmap)
    for name, raw in multi.items():
        phase.account_output(name, raw)
    replacement_happened = False
    def replace_after_first(stage, parent_fd, run_fd, name, index):
        nonlocal replacement_happened
        if stage == "after-output" and index == 0:
            os.rename(name, displaced_name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
            os.mkdir(name, mode=0o755, dir_fd=parent_fd)
            foreign_fd = os.open(name, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0), dir_fd=parent_fd)
            try:
                descriptor = os.open("foreign-sentinel.bin", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644, dir_fd=foreign_fd)
                try:
                    os.write(descriptor, foreign_data)
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
            finally:
                os.close(foreign_fd)
            replacement_happened = True
    try:
        secure_publish(run_name, list(multi), multi, phase, failure_hook=replace_after_first)
        raise AssertionError("Replacement race unexpectedly published")
    except RuntimeError as error:
        if "replaced" not in str(error):
            raise
    displaced = base / displaced_name
    replacement = base / run_name
    sentinel = replacement / "foreign-sentinel.bin"
    partial = displaced / "first.json"
    if (not replacement_happened or not sentinel.is_file() or sha(sentinel.read_bytes()) != sha(foreign_data)
            or not partial.is_file() or sha(partial.read_bytes()) != sha(multi["first.json"])
            or (replacement / "publication.json").exists() or (displaced / "publication.json").exists()):
        raise ValueError("Replacement/foreign ownership or partial-failure preservation failed")
    results.append({"case": "ancestor/vintage replacement during partial output", "outcome": "aborted-without-touching-replacement-owner",
        "error": "writer detected changed directory identity before the next output",
        "partial_writer_output": {"path": str(partial.relative_to(ROOT)), "bytes": partial.stat().st_size, "sha256": sha(partial.read_bytes())},
        "preserved_replacement_sentinel": {"path": str(sentinel.relative_to(ROOT)), "bytes": sentinel.stat().st_size, "sha256": sha(sentinel.read_bytes())},
        "success_receipt_present": False})
    return {"version": 1, "method_id": "exclusive-owned-vintage-admission", "kind": "negative-control",
            "outcome": "passed", "cases": results, "replacement_owner_preserved": True,
            "partial_failure_preserved_without_success_receipt": True}


def run_controls(one: str, two: str, vintage: str):
    code = verify_code()
    pmap = pinmap()
    pair_phase, runs = load_runs(one, two)
    first, second = runs
    for name in RUN_FILES:
        if first["files"][name] != second["files"][name]:
            raise ValueError("Two complete producer runs are not byte-identical: " + name)
    result_one = json.loads(first["decoded"]["source-geometry-results.json.gz"])
    result_two = json.loads(second["decoded"]["source-geometry-results.json.gz"])
    if result_one != result_two:
        raise ValueError("Two decoded producer results differ")

    custody = custody_phase(reproduce.ids()[0], pmap)
    fragments = fragment_phase(custody, pmap)
    custody_one = unpack(first["files"]["custody-phase.json.gz"])
    custody_two = unpack(second["files"]["custody-phase.json.gz"])
    fragments_one = unpack(first["files"]["fragment-phase.json.gz"])
    fragments_two = unpack(second["files"]["fragment-phase.json.gz"])
    if custody_one != custody_two or custody_one != custody or fragments_one != fragments_two or fragments_one != fragments:
        raise ValueError("Actual runs do not preserve exact independently re-read custody and complete fragment phases")
    run_summary = json.loads(first["decoded"]["run-summary.json"])
    if json.loads(second["decoded"]["run-summary.json"]) != run_summary:
        raise ValueError("Two actual run summaries differ")
    for name, obj in (("custody", custody_one), ("fragments", fragments_one), ("source-and-geometry", result_one)):
        filename = {"custody": "custody-phase.json.gz", "fragments": "fragment-phase.json.gz",
                    "source-and-geometry": "source-geometry-results.json.gz"}[name]
        encoded = first["files"][filename]
        decoded = first["decoded"][filename]
        required = obj["phase_accounting"]["input_bytes"] + len(encoded) + len(decoded)
        if run_summary["phase_bytes"].get(name) != required or required > 256 * 1024 * 1024:
            raise ValueError("Reported complete semantic phase bytes do not reconcile: " + name)
    if (run_summary.get("phase_bytes", {}).get("source-contract", 0) > 256 * 1024 * 1024
            or set(run_summary["phase_bytes"]) != {"source-contract", "custody", "fragments", "source-and-geometry"}):
        raise ValueError("Source-contract phase limits or inventory changed")

    subject_expected, subject_phase = expected_subject_records(pair_phase, pmap)
    identity = validate_result(result_one, custody, fragments, subject_expected)
    original, original_receipt = read_old_result(pair_phase)
    measurement_checks = compare_original_measurements(result_one, original)

    fixture_receipts, negative_cases = [], []
    for case in ("missing-subject", "duplicate-component", "wrong-contact-kind", "fabricated-source", "wrong-parent", "wrong-source-vintage"):
        altered = mutate_result(result_one, case)
        fixture_name = vintage + "-false-" + case
        fixture = write_pair_fixture(fixture_name, altered, pmap)
        fixture_receipts.append(fixture)
        _, files = read_complete(fixture_name, {"run-one.json.gz", "run-two.json.gz"})
        failed_results = [json.loads(gzip.decompress(files[n])) for n in ("run-one.json.gz", "run-two.json.gz")]
        if failed_results[0] != failed_results[1]:
            raise ValueError("Adverse fixture pair must be complete, coherent and identical")
        try:
            validate_result(failed_results[0], custody, fragments, subject_expected)
            raise ValueError("False-pass fixture unexpectedly passed: " + case)
        except (ValueError, KeyError, TypeError) as error:
            if str(error).startswith("False-pass fixture unexpectedly passed"):
                raise
            negative_cases.append({"case": case, "outcome": "rejected", "reason": str(error), **fixture})

    drift = run_drift_controls(vintage + "-drift")
    publication_safety = run_publication_safety_controls(vintage + "-safety")
    run_hashes = {row["label"]: {name: sha(row["files"][name]) for name in sorted(RUN_FILES)} for row in runs}
    control_outputs = {
        "geography-positive-control.json": {"version": 1, "method_id": "zmb-zwe-exact-identity-contact",
            "kind": "positive-control", "outcome": "passed", "checked_component_rows": identity["component_ids"],
            "checked_native_subjects": identity["subject_ids"], "contact": {"kind": identity["contact_kind"],
            "exact_row_sha256": identity["exact_contact_row_sha256"], "geometry": identity["contact_geometry"]},
            "complete_custody_phase_reproduced": True, "complete_fragment_family_reproduced": True,
            "independently_checked_source_parents": subject_expected, "source_phase": subject_phase,
            "scope": "Exact identity preservation only; no parent/territorial approval."},
        "geography-negative-control.json": {"version": 1, "method_id": "zmb-zwe-false-pair-rejection",
            "kind": "negative-control", "outcome": "passed", "actual_complete_equal_pairs_rejected": negative_cases},
        "generator-positive-control.json": {"version": 1, "method_id": "zmb-zwe-whole-producer-runs",
            "kind": "positive-control", "outcome": "passed", "run_file_sha256": run_hashes,
            "two_actual_runs_byte_identical": True, "measurement_comparison": measurement_checks,
            "retained_original_result": original_receipt, "per_run_phase_limits_checked": True},
        "generator-negative-control.json": {"version": 1, "method_id": "zmb-zwe-actual-input-code-drift",
            "kind": "negative-control", "outcome": "passed", "drift_controls": drift,
            "whole_vintage_publication_safety": publication_safety},
        "reproducibility.json": {"version": 1, "method_id": "zmb-zwe-complete-run-reproducibility",
            "kind": "reproducibility", "outcome": "passed", "run_one_vintage": one, "run_two_vintage": two,
            "run_one_sha256": sha(first["files"]["source-geometry-results.json.gz"]),
            "run_two_sha256": sha(second["files"]["source-geometry-results.json.gz"]),
            "all_phase_files_equal": True, "retained_measurement_checks": len(measurement_checks),
            "exact_altered_pair_cases_rejected": len(negative_cases), "complete_altered_fixtures": fixture_receipts},
    }
    out_phase = Phase("controls-whole-output", [], pin_map=pmap)
    for name, value in control_outputs.items():
        out_phase.account_output(name, canonical(value))
    receipt = secure_publish(vintage, list(control_outputs), {k: canonical(v) for k, v in control_outputs.items()}, out_phase)
    return {"vintage": vintage, "publication_sha256": sha(receipt), "outputs": list(control_outputs),
            "read_phase_bytes": sum(pair_phase.baseline.consumed.values()),
            "independent_custody_phase_bytes": custody["phase_accounting"]["input_bytes"] + len(deterministic_gzip(canonical(custody))) + len(canonical(custody)),
            "independent_fragment_phase_bytes": fragments["phase_accounting"]["input_bytes"] + len(deterministic_gzip(canonical(fragments))) + len(canonical(fragments)),
            "subject_identity_phase_bytes": subject_phase["bytes"],
            "control_output_phase_bytes": sum(out_phase.baseline.consumed.values()),
            "negative_case_count": len(negative_cases), "measurement_check_count": len(measurement_checks)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-one", required=True)
    parser.add_argument("--run-two", required=True)
    parser.add_argument("--vintage", required=True)
    args = parser.parse_args()
    print(json.dumps(run_controls(args.run_one, args.run_two, args.vintage), sort_keys=True))


if __name__ == "__main__":
    main()
