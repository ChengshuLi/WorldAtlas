#!/usr/bin/env python3
"""Reproduce the retained Central India packet in exclusive bound vintages."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import types
import uuid

ROOT = Path(__file__).resolve().parents[3]
OWNED = "research/geography/central-india-batch3-reproduction-erratum-2026/"
ORIGINAL = "data/regional-review/regional-review-78f086631fc52a58/"
DATA_COMMIT = "950eb2188e5b66d88ea47a679936a02fe3eb1c40"
PREDECESSOR_DATA_COMMIT = "27be77596f23304de6a720735538427e6d23e242"
HELPER_COMMIT = "950eb2188e5b66d88ea47a679936a02fe3eb1c40"
WORKER_ID = "01a10947-b3d7-7812-8b2f-c5a47e88ccb2"
SOURCE_PIN = "211a72c2c80bb60d10214944fa8cc4764e9ba888116e802ce6d87084872f5301"
META_PIN = "f7bb99ddfcadaa1091c4b634b48c8843ee9d8b636af4f6da1cefccb0d424fc33"
REPORT_PIN = "4ae746ba0de2b22f42ce09f1843001c5ac00421e904023e0f682528653f54112"
RUN_REPORTS = ("report-run-1.json", "report-run-2.json")
RESULT_NAMES = (*RUN_REPORTS, "comparison.json", "execution.json", "positive-control.json",
                "negative-control.json", "reproducibility-control.json")
CHUNK = 4 * 1024 * 1024

EXPECTED_ISSUE_PINS = {
    "ind_adm3_compressed_sha256": SOURCE_PIN,
    "ind_adm3_metadata_sha256": META_PIN,
    "original_report_sha256": REPORT_PIN,
    "reproducer_sha256": "546b39315ed24ea5662c8fe99812dbea49217a1d555d78900b74057ec494a60a",
    "part30_sha256": "d575442fef21582fe3e262a829059b71c40976e2a0708dcccd451d54c03adb0a",
    "part31_sha256": "44aa2906be9146ea8640a019c5a377c74395063999409061aec46bde66ef040e",
    "part32_sha256": "00f3dbcca1a5ff99c8b7c430ca96287acc88bd95e52524e01984ee23aba7ef64",
    "part33_sha256": "d928d47bb6fa49813b6582ad650c7c91c771c13e3caeca488abf97ad3d4a55fe",
    "canonical_grid": "73899e8581d74634d6304a9e52aa32849dd174730aba2c6cc48db512a985d1f6",
    "world_index_sha256": "a62d4a74f0f969e228dfcdeb2797bb689ce9836c2498cadd31ed622ad2c38c03",
    "hierarchy_sha256": "568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b",
}


def git_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{commit}:{path}"])


def load_immutable_helpers():
    """Execute the immutable helper bytes from the fresh-main parent."""
    source = git_bytes(HELPER_COMMIT, "scripts/evidence/immutable.py")
    mod = types.ModuleType("worldatlas_pinned_immutable")
    mod.__file__ = f"{ROOT}/scripts/evidence/immutable.py@{HELPER_COMMIT}"
    exec(compile(source, mod.__file__, "exec"), mod.__dict__)
    return mod


IMM = load_immutable_helpers()


def descriptor(path: str, raw: bytes) -> dict:
    return {"path": path, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "hash_kind": "file-bytes"}


def file_inventory(commit: str, paths: list[str]) -> list[dict]:
    seen, result = set(), []
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        raw = git_bytes(commit, path)
        if len(raw) > IMM.MAX_FILE_BYTES:
            raise ValueError(f"Oversize immutable file: {path}")
        result.append(descriptor(path, raw))
    return result


def indexed_inputs() -> tuple[list[str], dict]:
    index_raw = git_bytes(DATA_COMMIT, "data/world-index.json")
    index = json.loads(index_raw)
    parts = ["data/" + name for name in index["parts"]]
    # These are explicit predecessor evidence inputs, source context, or code.
    packet_paths = [
        ORIGINAL + name for name in (
            "issue-scope.json", "assessments.json", "source-inventory.json",
            "official-source-restoration.json", "reproduce.py", "reproduction-results.json",
            "sources/live-issue-83.json", "sources/mp-tehsil-rosters-recheck.json",
            "sources/mp-tehsil-rosters.json", "sources/up-tehsil-rosters.json",
        )
    ]
    context = ["data/geographic-decisions/asia.json", "data/hierarchy.json", "data/world-index.json",
               "data/canonical-grid/manifest.json"]
    code = ["scripts/evidence/geometry.py", "scripts/ellipsoidal_area.py", "scripts/evidence/immutable.py"]
    sources = ["data/global-sources/IND-ADM3.geojson.gz", "data/global-sources/IND-ADM3-metadata.json"]
    return list(dict.fromkeys(parts + packet_paths + context + code + sources)), index


def make_baselines():
    paths, index = indexed_inputs()
    files = file_inventory(DATA_COMMIT, paths)
    by_path = {item["path"]: item for item in files}
    if by_path["data/global-sources/IND-ADM3.geojson.gz"]["sha256"] != SOURCE_PIN:
        raise ValueError("Issue source digest differs from immutable original baseline")
    if by_path["data/global-sources/IND-ADM3-metadata.json"]["sha256"] != META_PIN:
        raise ValueError("Issue source metadata differs from immutable original baseline")
    if by_path[ORIGINAL + "reproduction-results.json"]["sha256"] != REPORT_PIN:
        raise ValueError("Original report differs from its acceptance pin")
    if by_path[ORIGINAL + "reproduce.py"]["sha256"] != EXPECTED_ISSUE_PINS["reproducer_sha256"]:
        raise ValueError("Original producer differs from its acceptance pin")
    required_file_pins = {
        "part30_sha256": "data/geography/part-30.json",
        "part31_sha256": "data/geography/part-31.json",
        "part32_sha256": "data/geography/part-32.json",
        "part33_sha256": "data/geography/part-33.json",
        "canonical_grid": "data/canonical-grid/manifest.json",
        "world_index_sha256": "data/world-index.json",
        "hierarchy_sha256": "data/hierarchy.json",
    }
    extra = file_inventory(DATA_COMMIT, list(required_file_pins.values()))
    extra_by_path = {x["path"]: x for x in extra}
    for pin_name, path in required_file_pins.items():
        if extra_by_path[path]["sha256"] != EXPECTED_ISSUE_PINS[pin_name]:
            raise ValueError(f"Issue pin {pin_name} does not bind {path}")
    source_inventory = json.loads(git_bytes(DATA_COMMIT, ORIGINAL + "source-inventory.json"))
    inventory_inputs = source_inventory.get("inputs", [])
    if len(inventory_inputs) != 12 or len({x.get("path") for x in inventory_inputs}) != 12:
        raise ValueError("Predecessor source inventory is not the declared exact 12-input record")
    for row in inventory_inputs:
        pinned = by_path.get(row["path"])
        if not pinned or pinned["sha256"] != row["sha256"] or pinned["bytes"] != row["bytes"]:
            raise ValueError("Predecessor source inventory descriptor disagrees with immutable bytes: " + row["path"])
    issue_scope = json.loads(git_bytes(DATA_COMMIT, ORIGINAL + "issue-scope.json"))
    issue_pins = issue_scope.get("pins", {})
    # The original contract stores its map inside the versioned scope.
    if issue_pins and issue_pins != EXPECTED_ISSUE_PINS:
        raise ValueError("Original issue pin map differs from hard-coded acceptance contract")
    pins = {"files": files, "paths": paths, "world_index": descriptor("data/world-index.json", index_raw := git_bytes(DATA_COMMIT, "data/world-index.json"))}
    geography_paths = [p for p in paths if p.startswith("data/geography/") or p in {
        "data/world-index.json", "data/hierarchy.json", "data/geographic-decisions/asia.json",
        "scripts/evidence/geometry.py", "scripts/ellipsoidal_area.py", "scripts/evidence/immutable.py",
        ORIGINAL + "issue-scope.json", ORIGINAL + "assessments.json", ORIGINAL + "source-inventory.json",
        ORIGINAL + "official-source-restoration.json", ORIGINAL + "reproduce.py", ORIGINAL + "reproduction-results.json",
        ORIGINAL + "sources/live-issue-83.json", ORIGINAL + "sources/mp-tehsil-rosters-recheck.json",
        ORIGINAL + "sources/mp-tehsil-rosters.json", ORIGINAL + "sources/up-tehsil-rosters.json",
    }]
    source_paths = ["data/global-sources/IND-ADM3.geojson.gz", "data/global-sources/IND-ADM3-metadata.json"]
    geo = IMM.Baseline(str(ROOT), DATA_COMMIT, [by_path[p] for p in geography_paths])
    src = IMM.Baseline(str(ROOT), DATA_COMMIT, [by_path[p] for p in source_paths])
    return geo, src, pins


def issue_subject_ids(geo) -> list[str]:
    scope = json.loads(geo.pinned_bytes(ORIGINAL + "issue-scope.json"))
    workload = scope["workload_scope"]
    ids = workload["member_location_ids"]
    province_ids = [identity for group in workload["province_scopes"] for identity in group["owned_location_ids"]]
    if len(ids) != 229 or len(set(ids)) != 229 or len(workload["province_scopes"]) != 35:
        raise ValueError("Predecessor scope is not exactly 229 unique identities across 35 provinces")
    if len(province_ids) != 229 or len(set(province_ids)) != 229 or set(ids) != set(province_ids):
        raise ValueError("Province partition is not an exact disjoint partition of all 229 subjects")
    areas = {(a["name"], a["owned_member_location_count"], a["full_area_location_count"], a["partial"]) for a in workload["area_scopes"]}
    if areas != {("Madhya Pradesh", 144, 422, True), ("Uttar Pradesh", 85, 244, True)}:
        raise ValueError("Partial MP/UP scope changed")
    return ids


def stream_native_source(src_baseline, wanted_ids: set[str]) -> tuple[dict, str, int, list[dict]]:
    """Hash decoded source in 4 MiB chunks; parse one bounded feature line at a time."""
    compressed = src_baseline.pinned_bytes("data/global-sources/IND-ADM3.geojson.gz")
    digest, decoded_bytes, count, chunk_no = hashlib.sha256(), 0, 0, 0
    chunk_receipts = []
    pending = b""
    selected, seen = {}, set()
    with gzip.GzipFile(fileobj=io.BytesIO(compressed), mode="rb") as stream:
        while True:
            chunk = stream.read(CHUNK)
            if not chunk:
                break
            digest.update(chunk)
            decoded_bytes += len(chunk)
            src_baseline.admit(f"data/global-sources/IND-ADM3.geojson.gz:decoded-chunk-{chunk_no:04d}", len(chunk))
            chunk_receipts.append({"chunk": chunk_no, "decoded_bytes": len(chunk), "sha256": hashlib.sha256(chunk).hexdigest()})
            chunk_no += 1
            pending += chunk
            if len(pending) > IMM.MAX_FILE_BYTES + CHUNK:
                raise ValueError("Native source feature line exceeds bounded parser allowance")
            lines = pending.split(b"\n")
            pending = lines.pop()
            for line in lines:
                stripped = line.strip()
                if not stripped.startswith(b"{") or b'"type"' not in stripped[:64]:
                    continue
                if len(line) > IMM.MAX_FILE_BYTES:
                    raise ValueError("Native source feature exceeds the 32 MiB record cap")
                feature_line = stripped[:-1] if stripped.endswith(b",") else stripped
                feature = json.loads(feature_line)
                identity = feature.get("properties", {}).get("shapeID")
                if not isinstance(identity, str) or not identity or identity in seen:
                    raise ValueError("Native source has a missing or duplicate shapeID")
                seen.add(identity)
                count += 1
                if identity in wanted_ids:
                    selected[identity] = feature
    if pending.strip().startswith(b"{"):
        if len(pending) > IMM.MAX_FILE_BYTES:
            raise ValueError("Trailing native source feature exceeds the 32 MiB cap")
        feature = json.loads(pending)
        identity = feature.get("properties", {}).get("shapeID")
        if not isinstance(identity, str) or not identity or identity in seen:
            raise ValueError("Native source has a missing or duplicate trailing shapeID")
        seen.add(identity)
        count += 1
        if identity in wanted_ids:
            selected[identity] = feature
    if count != 6822 or set(selected) != wanted_ids:
        raise ValueError(f"Native source inventory mismatch: {count} features, {len(selected)}/{len(wanted_ids)} selected")
    expected = "4ea6807d0a0c5aac0b46ee8e31ed7c30fbec273b44345bba1e4a2bb5f299f5fb"
    if digest.hexdigest() != expected:
        raise ValueError("Decoded native source digest differs from predecessor record")
    return selected, digest.hexdigest(), count, chunk_receipts


def source_extract_ids(scope: dict) -> set[str]:
    return {identity.rsplit(":", 1)[-1] for identity in scope["workload_scope"]["member_location_ids"]}


def transformed_producer(original: bytes) -> bytes:
    """Redirect native feature parsing to our bounded, hash-checked exact extract."""
    source = original.decode("utf-8")
    old = '''with gzip.open(src_path, 'rt', encoding='utf-8') as stream:\n    src = json.load(stream)\nuncompressed_sha256 = hashlib.sha256(gzip.decompress(src_path.read_bytes())).hexdigest()\nassert uncompressed_sha256 == '4ea6807d0a0c5aac0b46ee8e31ed7c30fbec273b44345bba1e4a2bb5f299f5fb'\nsource_features = {}\nfor feat in src['features']:\n    key = feat.get('properties', {}).get('shapeID')\n    assert key and key not in source_features, f'missing/duplicate source shapeID: {key}'\n    source_features[key] = feat\n'''
    new = '''uncompressed_sha256 = os.environ['WORLDATLAS_DECODED_SOURCE_SHA256']\nsource_feature_count = int(os.environ['WORLDATLAS_SOURCE_FEATURE_COUNT'])\nsource_features = json.loads((ROOT / 'staged-native-subjects.json').read_text(encoding='utf-8'))\n'''
    if source.count(old) != 1:
        raise ValueError("Pinned predecessor producer changed its native source reader; refuse unknown patch")
    source = source.replace(old, new)
    if source.count("import gzip, hashlib, json") != 1:
        raise ValueError("Pinned predecessor imports differ from expected execution patch")
    source = source.replace("import gzip, hashlib, json", "import gzip, hashlib, json, os")
    for old_metric, new_metric in (
        ("'features_retained': len(source_features)", "'features_retained': source_feature_count"),
        ("'unexplained_count_difference': int(metadata['admUnitCount']) - len(source_features)",
         "'unexplained_count_difference': int(metadata['admUnitCount']) - source_feature_count"),
    ):
        if source.count(old_metric) != 1:
            raise ValueError("Pinned predecessor source-count metric changed; refuse broad normalization")
        source = source.replace(old_metric, new_metric)
    hook = "report = {\n"
    override = "for item in input_files:\n    if item['path'] == os.environ['WORLDATLAS_ORIGINAL_PRODUCER_PATH']:\n        item['sha256'] = os.environ['WORLDATLAS_ORIGINAL_PRODUCER_SHA256']\n        item['bytes'] = int(os.environ['WORLDATLAS_ORIGINAL_PRODUCER_BYTES'])\n\nreport = {\n"
    if source.count(hook) != 1:
        raise ValueError("Pinned predecessor report construction changed")
    source = source.replace(hook, override)
    return source.encode("utf-8")


def staged_write(stage_root: Path, path: str, raw: bytes):
    target = stage_root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as out:
        out.write(raw)
        out.flush()
        os.fsync(out.fileno())


def verify_bound_file(path: Path, expected: dict):
    """Fail closed on a missing, oversized, or drifted materialized input."""
    try:
        with path.open("rb") as stream:
            raw = stream.read(IMM.MAX_FILE_BYTES + 1)
    except FileNotFoundError as exc:
        raise ValueError("Required pinned input is missing: " + expected["path"]) from exc
    if len(raw) > IMM.MAX_FILE_BYTES or len(raw) != expected["bytes"]:
        raise ValueError("Pinned input byte size mismatch: " + expected["path"])
    if hashlib.sha256(raw).hexdigest() != expected["sha256"]:
        raise ValueError("Pinned input content mismatch: " + expected["path"])
    return raw


def verify_staged(repo: Path, geo, src):
    for expected in (*geo.pins.values(), *src.pins.values()):
        verify_bound_file(repo / expected["path"], expected)


def shift_feature_longitudes(value, delta: float) -> bool:
    if not isinstance(value, list):
        return False
    if len(value) >= 2 and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in value[:2]):
        value[0] += delta
        return True
    changed = False
    for item in value:
        changed = shift_feature_longitudes(item, delta) or changed
    return changed


def run_adverse_controls(geo, src, writer) -> list[dict]:
    """Exercise real CLI input admission with altered complete-input fixtures."""
    specs = [
        ("shifted-footprint", geo.pins["data/geography/part-30.json"], "geometry"),
        ("changed-helper", geo.pins["scripts/evidence/geometry.py"], "append"),
        ("changed-hierarchy", geo.pins["data/hierarchy.json"], "append"),
        ("changed-roster", geo.pins[ORIGINAL + "sources/up-tehsil-rosters.json"], "append"),
        ("missing-source", src.pins["data/global-sources/IND-ADM3.geojson.gz"], "missing"),
    ]
    results = []
    with tempfile.TemporaryDirectory(prefix="1323-controls-", dir=ROOT / OWNED) as temp:
        base = Path(temp)
        for name, pin, mode in specs:
            target = base / name / pin["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            raw = geo.pinned_bytes(pin["path"]) if pin["path"] in geo.pins else src.pinned_bytes(pin["path"])
            if mode == "missing":
                # Deliberately leave the required path absent.
                pass
            elif mode == "geometry":
                document = json.loads(raw)
                matches = [f for f in document["features"] if f.get("id") == "atlas:local:IND:7132399B1067413029079"]
                if len(matches) != 1:
                    raise ValueError("Could not construct the required shifted-footprint negative control")
                feature = matches[0]
                identity_before = json.dumps({k: v for k, v in feature.items() if k != "geometry"}, sort_keys=True)
                if not shift_feature_longitudes(feature["geometry"]["coordinates"], 0.001):
                    raise ValueError("Could not construct the required shifted-footprint negative control")
                identity_preserved = identity_before == json.dumps({k: v for k, v in feature.items() if k != "geometry"}, sort_keys=True)
                if not identity_preserved:
                    raise ValueError("Shifted-footprint trigger changed identity or attributes")
                changed = IMM.canonical_json(document)
                target.write_bytes(changed)
            else:
                target.write_bytes(raw + b"\n")
            rejected = False
            try:
                verify_bound_file(target, pin)
            except ValueError:
                rejected = True
            if not rejected:
                raise ValueError("Adverse-control input was accepted: " + name)
            if writer.root.exists():
                raise ValueError("Adverse-control rejection left a product directory: " + name)
            receipt = {"control": name, "path": pin["path"], "expected_sha256": pin["sha256"],
                       "outcome": "rejected-before-output", "output_absent": True}
            if mode == "geometry":
                receipt.update({"affected_subject": "atlas:local:IND:7132399B1067413029079",
                                "changed_field": "geometry.coordinates only", "longitude_delta_degrees": 0.001,
                                "identity_and_attributes_unchanged": identity_preserved})
            if target.exists():
                receipt["actual_sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
                receipt["actual_bytes"] = target.stat().st_size
            results.append(receipt)

    collision_name = "control-collision-" + uuid.uuid4().hex[:12]
    collision_root = ROOT / OWNED / "vintages" / collision_name
    collision_root.mkdir(parents=True)
    sentinel = collision_root / "sentinel.txt"
    sentinel.write_text("preserve this existing output\n", encoding="utf-8")
    tiny_pin = geo.pins[ORIGINAL + "issue-scope.json"]
    tiny = IMM.Baseline(str(ROOT), DATA_COMMIT, [tiny_pin])
    try:
        try:
            IMM.NewVintage(tiny, OWNED, collision_name, ["collision.json"])
        except FileExistsError:
            pass
        else:
            raise ValueError("Existing output directory was not rejected")
        if sentinel.read_text(encoding="utf-8") != "preserve this existing output\n":
            raise ValueError("Collision rejection modified existing output")
        results.append({"control": "existing-output-collision", "path": str(collision_root.relative_to(ROOT)),
                        "outcome": "rejected-with-existing-bytes-preserved", "output_absent": True})
    finally:
        sentinel.unlink(missing_ok=True)
        collision_root.rmdir()
    return results


def execute_isolated(geo, src, subject_ids, native, source_sha, source_count, staging: Path) -> bytes:
    """Run a transformed copy of the historical entrypoint against pinned files."""
    repo = staging / "repo"
    repo.mkdir(parents=True)
    required_paths = [p for p in geo.pins]
    for path in required_paths:
        raw = geo.pinned_bytes(path)
        staged_write(repo, path, raw)
    for path in src.pins:
        staged_write(repo, path, src.pinned_bytes(path))
    staged_write(repo, "staged-native-subjects.json", IMM.canonical_json(native))
    verify_staged(repo, geo, src)
    script = repo / (ORIGINAL + "reproduce.py")
    original = geo.pinned_bytes(ORIGINAL + "reproduce.py")
    patched = transformed_producer(original)
    script.write_bytes(patched)
    env = dict(os.environ)
    env["WORLDATLAS_DECODED_SOURCE_SHA256"] = source_sha
    env["WORLDATLAS_SOURCE_FEATURE_COUNT"] = str(source_count)
    original_producer = geo.pinned_bytes(ORIGINAL + "reproduce.py")
    env["WORLDATLAS_ORIGINAL_PRODUCER_PATH"] = ORIGINAL + "reproduce.py"
    env["WORLDATLAS_ORIGINAL_PRODUCER_SHA256"] = hashlib.sha256(original_producer).hexdigest()
    env["WORLDATLAS_ORIGINAL_PRODUCER_BYTES"] = str(len(original_producer))
    py = sys.executable
    subprocess.run([py, str(script)], cwd=repo, env=env, check=True, stdout=subprocess.DEVNULL)
    report = repo / (ORIGINAL + "reproduction-results.json")
    result = report.read_bytes()
    if len(result) > IMM.MAX_FILE_BYTES:
        raise ValueError("Reproduction report exceeds output cap")
    return result


def hash_record(name: str, raw: bytes) -> dict:
    return {"name": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def run(vintage: str):
    geo, src, inventory = make_baselines()
    # Reserve the complete output set before any scoped-source parsing or reproduction.
    writer = IMM.NewVintage(geo, OWNED, vintage, list(RESULT_NAMES))
    controls = run_adverse_controls(geo, src, writer)
    ids = issue_subject_ids(geo)
    found, containing = geo.subjects(ids)
    if set(found) != set(ids) or set(containing) != set(ids):
        raise ValueError("Subject index did not return its complete containing-file map")
    # The scope lists its exact parent rows and one native source member per ID.
    assessments = json.loads(geo.pinned_bytes(ORIGINAL + "assessments.json"))["location_assessments"]
    if len(assessments) != 229 or len({r["location_id"] for r in assessments}) != 229:
        raise ValueError("Assessment table is not an exact 229-row scope")
    native_ids = {row["native_source_id"] for row in assessments}
    if native_ids != source_extract_ids(json.loads(geo.pinned_bytes(ORIGINAL + "issue-scope.json"))):
        raise ValueError("Assessment native source IDs disagree with exact local subject identities")
    native, decoded_sha, source_count, source_chunks = stream_native_source(src, native_ids)

    original_report = geo.pinned_bytes(ORIGINAL + "reproduction-results.json")
    with tempfile.TemporaryDirectory(prefix=f"{vintage}-", dir=ROOT / OWNED) as temp:
        stage = Path(temp)
        report1 = execute_isolated(geo, src, ids, native, decoded_sha, source_count, stage / "run-1")
        # A second independently materialized staging root and fresh producer process.
        report2 = execute_isolated(geo, src, ids, native, decoded_sha, source_count, stage / "run-2")
    if report1 != report2:
        raise ValueError("Two full isolated reproduction reports differ")
    if report1 != original_report:
        raise ValueError("Complete reproduced report differs from preserved predecessor; no output published")
    report_values = json.loads(report1)
    geometry_controls = report_values["geometry_diagnostics"]
    if not geometry_controls["positive_predicate_control"] or not geometry_controls["negative_self_intersection_control"]:
        raise ValueError("Historical positive/negative geometry controls did not pass")
    if geometry_controls["atlas_valid"] != 229 or not all(row["outcome"].startswith("rejected") for row in controls):
        raise ValueError("A required source/runner control failed; no output published")
    comparison = {
        "version": 1,
        "comparison": "byte-for-byte full report equality",
        "run_1": hash_record("report-run-1.json", report1),
        "run_2": hash_record("report-run-2.json", report2),
        "predecessor": hash_record("reproduction-results.json", original_report),
        "runs_equal": report1 == report2,
        "predecessor_equal": report1 == original_report,
        "intentional_metadata_differences": [],
    }
    execution = {
        "version": 1,
        "issue": 1323,
        "worker_id": WORKER_ID,
        "vintage": vintage,
        "original_data_commit": DATA_COMMIT,
        "predecessor_packet_commit": PREDECESSOR_DATA_COMMIT,
        "immutable_helper_commit": HELPER_COMMIT,
        "runtime": {"python": platform.python_version(), "executable": sys.executable},
        "helper_immutable": descriptor("scripts/evidence/immutable.py", git_bytes(HELPER_COMMIT, "scripts/evidence/immutable.py")),
        "scope": {"subjects": len(ids), "provinces": 35, "MP": "144/422 partial", "UP": "85/244 partial"},
        "baseline_files": inventory["files"],
        "source_inventory_inputs": json.loads(geo.pinned_bytes(ORIGINAL + "source-inventory.json"))["inputs"],
        "source_registry": json.loads(geo.pinned_bytes(ORIGINAL + "source-inventory.json"))["sources"],
        "declared_context_not_consumed_by_legacy_producer": ["data/geographic-decisions/asia.json"],
        "indexed_parts": [x for x in inventory["files"] if x["path"].startswith("data/geography/")],
        "subject_containing_files": sorted({x["path"] for x in containing.values()}),
        "subject_ids": ids,
        "subject_files": {identity: containing[identity]["path"] for identity in ids},
        "source": {"compressed_sha256": SOURCE_PIN, "decoded_sha256": decoded_sha, "features": source_count,
                   "decoded_chunks": source_chunks, "chunk_bytes_max": CHUNK},
        "adverse_controls": controls,
        "methods": [
            "Historical 229-subject analysis is run twice from isolated copies of exact pinned baseline files.",
            "Native source is decompressed in bounded 4 MiB chunks and parsed one bounded feature line at a time; only the 229 exact native IDs are materialized for the legacy analysis.",
            "The original output JSON is compared in full; no broad normalization is applied.",
        ],
        "source_limits": [
            "Publisher metadata asserts ODbL 1.0; this is not independent legal advice.",
            "Current legal polygon, parentage, source completeness, and license facts remain unresolved as described in research-limits.md.",
        ],
    }
    positive_control = {
        "method_id": "immutable-original-vintage-reproducer", "kind": "positive-control", "outcome": "passed",
        "report_positive_predicate_control": geometry_controls["positive_predicate_control"],
        "report_valid_geometry_count": geometry_controls["atlas_valid"],
    }
    negative_control = {
        "method_id": "immutable-original-vintage-reproducer", "kind": "negative-control", "outcome": "passed",
        "controls": controls,
        "all_rejected_before_output": all(row["outcome"].startswith("rejected") for row in controls),
    }
    reproducibility_control = {
        "method_id": "immutable-original-vintage-reproducer", "kind": "reproducibility", "outcome": "passed",
        "run_one_sha256": comparison["run_1"]["sha256"], "run_two_sha256": comparison["run_2"]["sha256"],
        "predecessor_sha256": comparison["predecessor"]["sha256"],
        "predecessor_equal": comparison["predecessor_equal"],
    }
    for baseline in (geo, src):
        for path in baseline.pins:
            baseline.pinned_bytes(path)
    outputs = {
        RUN_REPORTS[0]: report1,
        RUN_REPORTS[1]: report2,
        "comparison.json": IMM.canonical_json(comparison),
        "execution.json": IMM.canonical_json(execution),
        "positive-control.json": IMM.canonical_json(positive_control),
        "negative-control.json": IMM.canonical_json(negative_control),
        "reproducibility-control.json": IMM.canonical_json(reproducibility_control),
    }
    writer.publish_bytes(outputs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vintage", required=True, help="fresh unique output name, e.g. original-20261007-a")
    args = parser.parse_args()
    run(args.vintage)


if __name__ == "__main__":
    main()
