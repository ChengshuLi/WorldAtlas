#!/usr/bin/env python3
"""Read-only source-fitness reconstruction for issue #1336.

This extracts retained candidate/source records and joins immutable routing and
numeric-scope records. It does not run geometry overlays, alter coordinates, or
infer physical, legal, or political authority.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
PKG = HERE
ROOT = HERE.parents[2]
BASELINE = "e3765802ba8a683c706aff8e3440ac21bcddcf4e"
ROUTING = "0198938719a5666b6726fb6a1e45779926eefeb2"
NUMERIC = "bec82842ad5d9cf07e38a78395df8d5e7a6f4591"
SOURCE = "1bf4bb01d76a76953d4a11308f5af2dd50fe3365"
RAW_SOURCE_SHA = "1a336a495dfcf3c369c5b5d05c205d7509610e0ab27ef1539140f8a8c763e335"
RAW_SOURCE_BYTES = 1481003
LIMIT = 32 * 1024 * 1024

sys.path.insert(0, str(PKG / "compat"))
import producer as legacy_producer  # noqa: E402
import immutable as legacy_immutable  # noqa: E402
import inputs as legacy_inputs  # noqa: E402


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value) -> bytes:
    return legacy_immutable.canonical_json(value)


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], stderr=subprocess.PIPE)


def git_blob(commit: str, path: str):
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Expected immutable lowercase Git commit")
    metadata = git("ls-tree", "-z", commit, "--", path).decode("utf-8").rstrip("\0")
    if not metadata or "\t" not in metadata:
        raise ValueError(f"Missing pinned Git input: {commit}:{path}")
    meta, actual_path = metadata.split("\t", 1)
    mode, kind, oid = meta.split()
    if actual_path != path or mode not in ("100644", "100755") or kind != "blob":
        raise ValueError(f"Input is not one ordinary file: {commit}:{path}")
    size = int(git("cat-file", "-s", oid))
    if size > LIMIT:
        raise ValueError(f"Encoded source input exceeds limit: {path}")
    raw = git("cat-file", "blob", oid)
    if len(raw) != size:
        raise ValueError(f"Git blob size changed: {path}")
    return raw, {"commit": commit, "path": path, "mode": mode, "oid": oid,
                 "bytes": len(raw), "sha256": sha(raw)}


def exact_blob(commit, path, expected_sha=None, expected_bytes=None):
    raw, pin = git_blob(commit, path)
    if expected_sha and pin["sha256"] != expected_sha:
        raise ValueError(f"Whole source hash mismatch: {path}")
    if expected_bytes is not None and pin["bytes"] != expected_bytes:
        raise ValueError(f"Whole source size mismatch: {path}")
    return raw, pin


def parse_issue():
    api = json.loads((PKG / "issue-1336-api.json").read_bytes())
    body = api["body"]
    contract_match = re.search(r"<!-- worldatlas-work:v1\s*(\{.*?\})\s*-->", body, re.S)
    if not contract_match:
        raise ValueError("Issue machine contract missing")
    contract = json.loads(contract_match.group(1))
    roster_start = body.find('```json\n{\n  "complete_family_ids"')
    if roster_start < 0:
        raise ValueError("Complete source subject roster missing from issue")
    content_start = body.index("\n", roster_start) + 1
    content_end = body.index("\n```", content_start)
    roster = json.loads(body[content_start:content_end])
    family_ids = roster["complete_family_ids"]
    components = roster["component_ids"]
    contacts = roster["contact_ids"]
    expected = contract["evidence_quality"]
    if (api["number"] != 1336 or len(family_ids) != 1 or len(components) != 49 or
            len(set(components)) != 49 or len(contacts) != 6 or len(set(contacts)) != 6 or
            set(contacts) != set(expected["subject_ids"]) or contract["mode"] != "geography"):
        raise ValueError("Issue roster or evidence contract is not complete #1336 scope")
    if contract["owned_paths"] != ["research/geography/saudi-fortynine-numeric-gap-family-source-fitness-20261007/"]:
        raise ValueError("Issue-owned path differs")
    pins = expected["pins"]
    required = {
        "audited_world_index": "a62d4a74f0f969e228dfcdeb2797bb689ce9836c2498cadd31ed622ad2c38c03",
        "delivered_routing_report": "2bf401f76aabc30cb9f0120aba958545146ebf37e304d8817d15eed800fa5265",
        "delivered_routing_input_config": "7623fa8a61b72c33a1560f0ab612e70c463e8c25beef930043c985fd6657f173",
        "delivered_numeric_report": "e47379a74c053b57781fec04aaedc702ecba24adb773b42bb8c75d142326647a",
        "original_source_encoded_transport": "4b6df9fca9398148271a451805f7a26af03d756ef5ceec7fba9ef581bdf8b8aa",
        "scoped_contact_part_0": "d7b850e9fd2e3cc49044aa10218351831acc1d159b6f5eb1ef67a2ddae9f46d7",
    }
    if any(pins.get(key) != val for key, val in required.items()):
        raise ValueError("Current issue pins differ from the accepted source preflight")
    return api, body, contract, roster


def issue_body_hash(body: str) -> str:
    return sha(body.encode("utf-8"))


def get_legacy_config():
    path = PKG / "inputs" / "legacy-input-config.json"
    value = json.loads(path.read_bytes())
    if value.get("candidate_delivery") != "c6a26e1caba54e1b81a89fbda3a64fff56da323d" or len(value.get("inputs", [])) != 44:
        raise ValueError("Unexpected preserved candidate input configuration")
    return value


def derive_source_closure(repo):
    api, body, contract, roster = parse_issue()
    cfg = get_legacy_config()
    cfg_bytes = (PKG / "inputs" / "legacy-input-config.json").read_bytes()
    artifacts = []

    def add_path(commit, path, expected_sha=None, expected_bytes=None, decoded=None):
        raw, pin = exact_blob(commit, path, expected_sha, expected_bytes)
        desc = dict(pin)
        if decoded is not None:
            unpacked = gzip.decompress(raw)
            if len(unpacked) > LIMIT or len(unpacked) != decoded["bytes"] or sha(unpacked) != decoded["sha256"]:
                raise ValueError(f"Decoded whole source mismatch: {path}")
            desc["uncompressed_bytes"] = len(unpacked)
            desc["uncompressed_sha256"] = sha(unpacked)
        artifacts.append(desc)
        return raw, desc

    # The original candidate loader consumes exactly the non-archive inputs in
    # this unchanged 44-row configuration. It only reconstructs retained output
    # records; it does not invoke a geometry operator.
    loader_inputs = [row for row in cfg["inputs"] if row["kind"] != "archive_part"]
    if len(loader_inputs) != 40:
        raise ValueError("Expected unchanged 40-input component-only source view")
    for row in loader_inputs:
        add_path(row["commit"], row["path"], row["sha256"], row["bytes"],
                 {"bytes": row["uncompressed_bytes"], "sha256": row["uncompressed_sha256"]}
                 if "uncompressed_bytes" in row else None)
    reconstructor = cfg["existing_reconstructor"]
    add_path(reconstructor["commit"], reconstructor["path"], reconstructor["sha256"])

    route_report_path = "coordination/engineering/global-actionability-routing-20261007/results/report.json"
    route_report_raw, route_report_pin = add_path(ROUTING, route_report_path,
        "2bf401f76aabc30cb9f0120aba958545146ebf37e304d8817d15eed800fa5265", 174829)
    route_report = json.loads(route_report_raw)
    route_entry = next(x for x in route_report["complete_whole_raw_bodies"] if x["name"] == "components")
    family_entry = next(x for x in route_report["complete_whole_raw_bodies"] if x["name"] == "families")
    for entry in (route_entry, family_entry):
        entry["expected_records"] = route_report["counts"][entry["name"]]
    for label, entry in (("components", route_entry), ("families", family_entry)):
        if not entry.get("parts"):
            raise ValueError(f"Missing complete routing {label} source parts")
        for part in entry["parts"]:
            path = "coordination/engineering/global-actionability-routing-20261007/results/" + part["path"]
            add_path(ROUTING, path, part["sha256"], part["bytes"],
                     {"bytes": part["uncompressed_bytes"], "sha256": part["uncompressed_sha256"]})

    route_config_path = "coordination/engineering/global-actionability-routing-20261007/input-config.json"
    _, route_config_pin = add_path(ROUTING, route_config_path,
        "7623fa8a61b72c33a1560f0ab612e70c463e8c25beef930043c985fd6657f173", 90091)
    numeric_report_path = "coordination/engineering/complete-numeric-closure-diagnosis-20261007/r1/report.json"
    _, numeric_report_pin = add_path(NUMERIC, numeric_report_path,
        "e47379a74c053b57781fec04aaedc702ecba24adb773b42bb8c75d142326647a", 178556)
    numeric_scope_path = "coordination/engineering/complete-numeric-closure-diagnosis-20261007/scope.json.gz"
    numeric_scope_raw, numeric_scope_pin = add_path(NUMERIC, numeric_scope_path,
        "ada2db15a78524cd28c7a5f924df7bbe0fe616cdead91c429dd2c04384a156e9", 8610767,
        {"bytes": 28911831, "sha256": "7f857e8c3c032ebfcedf3f602d96b1e563599d726834d2fd263dd4371ae70c9b"})
    numeric_scope = json.loads(gzip.decompress(numeric_scope_raw))
    if numeric_scope["routing_source"]["actual_merge"] != ROUTING:
        raise ValueError("Numeric scope points to another routing vintage")

    source_payload_path = "coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-SAU-ADM2-000.bin.gz"
    source_payload_raw, source_payload_pin = add_path(SOURCE, source_payload_path,
        "4b6df9fca9398148271a451805f7a26af03d756ef5ceec7fba9ef581bdf8b8aa", 407499,
        {"bytes": RAW_SOURCE_BYTES, "sha256": RAW_SOURCE_SHA})
    catalogue_path = "coordination/engineering/original-geography-source-corpus-20261006/catalogue.json"
    catalogue_raw, catalogue_pin = add_path(SOURCE, catalogue_path,
        "d3da799558be1fcbe7f3ea90ba7033d312a65690984983cb008f2d72e32765f9", 403376)
    attribution_path = "coordination/engineering/original-geography-source-corpus-20261006/individual-source-attribution.json"
    attribution_raw, attribution_pin = add_path(SOURCE, attribution_path,
        "7d8a3baf61f32e6e4398f24bec0d15bce32eafcd4309655edc2b12a2c33256bd", 806110)
    terms_path = "coordination/engineering/original-geography-source-corpus-20261006/CITATION-AND-USE-geoBoundaries-original.txt"
    terms_raw, terms_pin = add_path(SOURCE, terms_path,
        "f6ea7572bea6036c4cdcacf8c0ca7bf09098d4e600d19546d7432533e9a290d5", 4316)
    metadata_path = "data/administrative-sources.json"
    metadata_raw, metadata_pin = add_path(BASELINE, metadata_path,
        "ed0051d2956271c72f8917e7da0c6f53e5dfb595bee5920cac489a65a747d633", 661416)
    index_path = "data/world-index.json"
    index_raw, index_pin = add_path(BASELINE, index_path,
        "a62d4a74f0f969e228dfcdeb2797bb689ce9836c2498cadd31ed622ad2c38c03", 944)
    part_path = "data/geography/part-21.json"
    part_raw, part_pin = add_path(BASELINE, part_path,
        "d7b850e9fd2e3cc49044aa10218351831acc1d159b6f5eb1ef67a2ddae9f46d7", 6737781)

    # Validate complete source and current contact body identities before the
    # freeze. Parsing here only checks source bytes, not geographic truth.
    raw_geo = gzip.decompress(source_payload_raw)
    if len(raw_geo) != RAW_SOURCE_BYTES or sha(raw_geo) != RAW_SOURCE_SHA:
        raise ValueError("The complete decoded consumed source identity differs")
    original_geo = json.loads(raw_geo)
    if len(original_geo.get("features", [])) != 147:
        raise ValueError("Unexpected full original consumed feature count")
    contacts = set(roster["contact_ids"])
    current_index = json.loads(index_raw)
    current_part = json.loads(part_raw)
    current_by_id = {f.get("id", f.get("properties", {}).get("id")): f for f in current_part["features"]}
    if len(current_by_id) != len(current_part["features"]) or not contacts <= set(current_by_id):
        raise ValueError("Incomplete/duplicate current contact source")
    indexed_paths = set()
    if "geography/part-21.json" not in current_index.get("parts", []):
        raise ValueError("World index does not include the complete part-21 body")
    if not contacts <= set(current_by_id):
        raise ValueError("World index contact part does not hold all six contacts")

    # Freeze the exact executable and imported code bytes. No Python package
    # outside the standard library and these four pinned compatibility modules
    # participates in the producer.
    code_files = []
    for path in [HERE / "source_extract.py", HERE / "run_final.py", HERE / "compat" / "producer.py",
                 HERE / "compat" / "inputs.py", HERE / "compat" / "immutable.py",
                 HERE / "compat" / "transport.py", HERE / "compat" / "comparison.py",
                 HERE / "compat" / "ellipsoidal_area.py"]:
        raw = path.read_bytes()
        code_files.append({"path": str(path.relative_to(PKG)), "bytes": len(raw), "sha256": sha(raw)})
    if not (PKG / "run_final.py").is_file():
        raise ValueError("Missing frozen final-run wrapper")
    local_inputs = []
    for name, raw in (("issue-1336-api.json", (PKG / "issue-1336-api.json").read_bytes()),
                      ("inputs/legacy-input-config.json", cfg_bytes)):
        local_inputs.append({"path": name, "bytes": len(raw), "sha256": sha(raw)})

    # All real source blobs consumed by both executions are authenticated in
    # the frozen lock, sorted by (commit,path), with no hidden cache reference.
    unique = {(p["commit"], p["path"]): p for p in artifacts}
    source_blobs = sorted(unique.values(), key=lambda x: (x["commit"], x["path"]))
    return {
        "version": 1, "issue": 1336, "baseline_commit": BASELINE,
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "issue_body_sha256": issue_body_hash(body),
        "worker_id": "01a11550-a19b-7330-955c-e56e90985bf3",
        "code": code_files, "local_inputs": local_inputs,
        "python": {"executable": sys.executable, "version": sys.version,
                    "implementation": sys.implementation.name, "platform": sys.platform},
        "external_tools": [{"name": "git", "executable": subprocess.check_output(["which", "git"], text=True).strip(),
                            "version": subprocess.check_output(["git", "--version"], text=True).strip()}],
        "source_commits": {"routing": ROUTING, "numeric": NUMERIC, "source_corpus": SOURCE},
        "complete_component_count": 49, "complete_contact_count": 6,
        "original_source_raw_identity": {"bytes": RAW_SOURCE_BYTES, "sha256": RAW_SOURCE_SHA},
        "source_blobs": source_blobs,
        "source_blob_count": len(source_blobs),
        "source_blob_encoded_bytes": sum(x["bytes"] for x in source_blobs),
        "limits": {"per_encoded_or_decoded_input_bytes": LIMIT, "maximum_total_declared_bytes": 256 * 1024 * 1024},
        "statement": "The executable reads complete immutable source bodies and accepted existing results; no global overlay, numeric operator, physical classification, snapping, buffering, simplification, MakeValid, or fill is run."
    }


def verify_frozen_code(lock):
    for entry in lock["code"]:
        path = PKG / entry["path"]
        raw = path.read_bytes()
        if len(raw) != entry["bytes"] or sha(raw) != entry["sha256"]:
            raise ValueError(f"Frozen code changed after input freeze: {entry['path']}")
    for entry in lock["local_inputs"]:
        path = PKG / entry["path"]
        raw = path.read_bytes()
        if len(raw) != entry["bytes"] or sha(raw) != entry["sha256"]:
            raise ValueError(f"Frozen local input changed after input freeze: {entry['path']}")
    for pin in lock["source_blobs"]:
        raw, actual = git_blob(pin["commit"], pin["path"])
        for key in ("mode", "oid", "bytes", "sha256"):
            if actual[key] != pin[key]:
                raise ValueError(f"Frozen whole source body changed: {pin['path']} ({key})")


def checked_gzip_blob(commit, path, part):
    raw, pin = exact_blob(commit, path, part["sha256"], part["bytes"])
    decoded = legacy_inputs.checked_decoded(raw, dict(path=path, bytes=part["bytes"],
        sha256=part["sha256"], uncompressed_bytes=part["uncompressed_bytes"],
        uncompressed_sha256=part["uncompressed_sha256"]))
    return raw, decoded, pin


def scan_jsonl_body(repo, commit, entry, prefix):
    whole = hashlib.sha256()
    raw_bytes = 0
    count = 0
    pending = b""
    matches = []
    last_id = None
    part_pins = []
    for ordinal, part in enumerate(entry["parts"]):
        path = prefix + part["path"]
        _, decoded, pin = checked_gzip_blob(commit, path, part)
        part_pins.append(dict(pin, uncompressed_bytes=len(decoded), uncompressed_sha256=sha(decoded),
                              part_ordinal=ordinal))
        whole.update(decoded)
        raw_bytes += len(decoded)
        lines = (pending + decoded).split(b"\n")
        pending = lines.pop()
        for line in lines:
            if not line:
                raise ValueError(f"Empty row in complete {entry['name']} input")
            value = json.loads(line)
            identity = value.get("component") if entry["name"] == "components" else value.get("family")
            if identity is None:
                identity = value.get("id", value.get("family_id"))
            if identity is None and entry["name"] == "families":
                encoded = json.dumps(value, sort_keys=True)
                hits = [candidate for candidate in scan_jsonl_body.expected if candidate in encoded]
                if len(hits) == 1:
                    identity = hits[0]
            if identity is None:
                raise ValueError(f"Row identity missing in complete {entry['name']} input")
            if last_id is not None and identity <= last_id:
                raise ValueError(f"Duplicate/unsorted identity in complete {entry['name']} input")
            last_id = identity
            if identity in scan_jsonl_body.expected:
                matches.append({"record": value, "ordinal": count,
                                "line_sha256": sha(line + b"\n"), "part_ordinal": ordinal,
                                "part_path": path, "part_sha256": pin["sha256"]})
            count += 1
    if pending:
        raise ValueError(f"Unterminated line in complete {entry['name']} source")
    if raw_bytes != entry["bytes"] or whole.hexdigest() != entry["sha256"] or count != entry["expected_records"]:
        raise ValueError(f"Whole complete {entry['name']} source body failed closure")
    return matches, {"name": entry["name"], "records": count, "bytes": raw_bytes,
                     "sha256": whole.hexdigest(), "parts": part_pins}


def extract(repo: Path, output: Path, lock):
    api, body, contract, roster = parse_issue()
    cfg = get_legacy_config()
    component_ids = roster["component_ids"]
    contact_ids = roster["contact_ids"]
    families = roster["complete_family_ids"]
    expected_components = set(component_ids)
    expected_contacts = set(contact_ids)
    if len(expected_components) != 49 or len(expected_contacts) != 6:
        raise ValueError("Expected complete #1336 scope")

    # Reconstruct complete existing candidate records from the unchanged
    # source custody/config. This invokes the preserved row reconstructor only.
    component_view = dict(cfg, inputs=[row for row in cfg["inputs"] if row["kind"] != "archive_part"])
    current, lineage, source_receipts, reconstruction, audit = legacy_producer.load_candidates(repo, component_view)
    candidates_by_id = {row["id"]: row for row in current["components"]}
    if len(current["components"]) != 95173 or len(candidates_by_id) != 95173:
        raise ValueError("Existing candidate reconstruction did not produce the complete 95,173 roster")
    if not expected_components <= set(candidates_by_id):
        raise ValueError("Issue candidate roster missing from immutable candidate reconstruction")

    route_report_raw, route_report_pin = exact_blob(ROUTING,
        "coordination/engineering/global-actionability-routing-20261007/results/report.json",
        "2bf401f76aabc30cb9f0120aba958545146ebf37e304d8817d15eed800fa5265", 174829)
    route_report = json.loads(route_report_raw)
    component_entry = next(x for x in route_report["complete_whole_raw_bodies"] if x["name"] == "components")
    family_entry = next(x for x in route_report["complete_whole_raw_bodies"] if x["name"] == "families")
    for entry in (component_entry, family_entry):
        entry["expected_records"] = route_report["counts"][entry["name"]]
    scan_jsonl_body.expected = expected_components
    route_matches, route_receipt = scan_jsonl_body(repo, ROUTING, component_entry,
        "coordination/engineering/global-actionability-routing-20261007/results/")
    route_map = {row["record"]["component"]: row for row in route_matches}
    if len(route_map) != 49 or set(route_map) != expected_components:
        raise ValueError("Complete route rows do not exactly match all 49 issue subjects")
    full_components = []
    for identity in component_ids:
        route = route_map[identity]["record"]
        feature = candidates_by_id[identity]
        if route.get("family") != families[0]:
            raise ValueError("Candidate is foreign to the issue's complete family")
        if sha(canonical(feature)) != route["current_feature_sha256"]:
            raise ValueError(f"Complete feature/source binding mismatch: {identity}")
        if sha(canonical(feature["geometry"])) != route["current_geometry_sha256"]:
            raise ValueError(f"Complete pointset/source binding mismatch: {identity}")
        full_components.append(feature)

    # Extract exactly one whole family record from the complete accepted family
    # stream and reconcile any explicit member roster to the 49 issue subjects.
    scan_jsonl_body.expected = set(families)
    family_matches, family_receipt = scan_jsonl_body(repo, ROUTING, family_entry,
        "coordination/engineering/global-actionability-routing-20261007/results/")
    if len(family_matches) != 1:
        raise ValueError("Expected exactly one complete source family record")
    family_record = family_matches[0]["record"]
    def find_component_arrays(value):
        found = []
        if isinstance(value, dict):
            for key, child in value.items():
                if key in ("component_ids", "complete_component_ids", "members") and isinstance(child, list):
                    ids = [x for x in child if isinstance(x, str) and x.startswith("physical-component:")]
                    if ids:
                        found.append(ids)
                found.extend(find_component_arrays(child))
        elif isinstance(value, list):
            for child in value:
                found.extend(find_component_arrays(child))
        return found
    family_arrays = find_component_arrays(family_record)
    if family_arrays and not any(len(x) == 49 and set(x) == expected_components for x in family_arrays):
        raise ValueError("Complete family record's member roster differs from all 49 issue subjects")

    # Reuse the complete original/current body pointers and source metadata.
    _, source_payload_pin = exact_blob(SOURCE,
        "coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-SAU-ADM2-000.bin.gz",
        "4b6df9fca9398148271a451805f7a26af03d756ef5ceec7fba9ef581bdf8b8aa", 407499)
    source_raw, source_payload_pin = exact_blob(SOURCE, source_payload_pin["path"], source_payload_pin["sha256"], source_payload_pin["bytes"])
    source_decoded = gzip.decompress(source_raw)
    if len(source_decoded) != RAW_SOURCE_BYTES or sha(source_decoded) != RAW_SOURCE_SHA:
        raise ValueError("Actual full original consumed GeoJSON identity does not match both pins")
    original_geo = json.loads(source_decoded)
    if len(original_geo.get("features", [])) != 147:
        raise ValueError("Original simplified consumed source feature roster changed")
    original_by_shape = {f.get("properties", {}).get("shapeID"): f for f in original_geo["features"]}
    if len(original_by_shape) != 147 or None in original_by_shape:
        raise ValueError("Duplicate/missing source shape IDs in whole original GeoJSON")

    _, index_pin = exact_blob(BASELINE, "data/world-index.json",
        "a62d4a74f0f969e228dfcdeb2797bb689ce9836c2498cadd31ed622ad2c38c03", 944)
    index_value = json.loads(git("show", f"{BASELINE}:data/world-index.json"))
    part_raw, part_pin = exact_blob(BASELINE, "data/geography/part-21.json",
        "d7b850e9fd2e3cc49044aa10218351831acc1d159b6f5eb1ef67a2ddae9f46d7", 6737781)
    part_value = json.loads(part_raw)
    current_by_id = {f.get("id", f.get("properties", {}).get("id")): f for f in part_value["features"]}
    if len(current_by_id) != len(part_value["features"]) or not expected_contacts <= set(current_by_id):
        raise ValueError("Current whole part-21 source misses or duplicates issue contacts")
    owner_rows = []
    if "geography/part-21.json" not in index_value.get("parts", []):
        raise ValueError("Whole current index does not bind part-21")
    owner_rows = [{"id": identity, "dataFile": "data/geography/part-21.json"} for identity in contact_ids]

    admin_raw, admin_pin = exact_blob(BASELINE, "data/administrative-sources.json",
        "ed0051d2956271c72f8917e7da0c6f53e5dfb595bee5920cac489a65a747d633", 661416)
    admin = json.loads(admin_raw)
    metadata_row = admin["gb:SAU:ADM2"]
    metadata_row_sha = sha(canonical(metadata_row))
    catalogue_raw, catalogue_pin = exact_blob(SOURCE,
        "coordination/engineering/original-geography-source-corpus-20261006/catalogue.json",
        "d3da799558be1fcbe7f3ea90ba7033d312a65690984983cb008f2d72e32765f9", 403376)
    catalogue = json.loads(catalogue_raw)
    catalogue_row = next(x for x in catalogue.get("products", []) if x.get("key") == "gb:SAU:ADM2")
    if metadata_row_sha != "bd4894e24d233e261a5397e611c7f5d144a00dee1b404b88fb8a90b90901621d":
        raise ValueError("Original administrative metadata row hash differs from preflight")
    attribution_raw, attribution_pin = exact_blob(SOURCE,
        "coordination/engineering/original-geography-source-corpus-20261006/individual-source-attribution.json",
        "7d8a3baf61f32e6e4398f24bec0d15bce32eafcd4309655edc2b12a2c33256bd", 806110)
    attribution = json.loads(attribution_raw)
    citation_rows = [x for x in attribution.get("individual_source_citations", []) if x.get("id") == "gb:SAU:ADM2"]
    if len(citation_rows) != 1:
        raise ValueError("Missing unique individual-source attribution record")
    if catalogue_row.get("original_sha256") != RAW_SOURCE_SHA or catalogue_row.get("original_bytes") != RAW_SOURCE_BYTES:
        raise ValueError("Source catalogue does not bind the consumed decoded GeoJSON")
    if catalogue_row.get("recorded_consumed_url") != "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/SAU/ADM2/geoBoundaries-SAU-ADM2_simplified.geojson":
        raise ValueError("Recorded Saudi source URL changed")

    numeric_report_raw, numeric_report_pin = exact_blob(NUMERIC,
        "coordination/engineering/complete-numeric-closure-diagnosis-20261007/r1/report.json",
        "e47379a74c053b57781fec04aaedc702ecba24adb773b42bb8c75d142326647a", 178556)
    numeric_scope_raw, numeric_scope_pin = exact_blob(NUMERIC,
        "coordination/engineering/complete-numeric-closure-diagnosis-20261007/scope.json.gz",
        "ada2db15a78524cd28c7a5f924df7bbe0fe616cdead91c429dd2c04384a156e9", 8610767)
    numeric_scope_decoded = gzip.decompress(numeric_scope_raw)
    if len(numeric_scope_decoded) != 28911831 or sha(numeric_scope_decoded) != "7f857e8c3c032ebfcedf3f602d96b1e563599d726834d2fd263dd4371ae70c9b":
        raise ValueError("Whole accepted numerical scope source changed")
    numeric_scope = json.loads(numeric_scope_decoded)
    numeric_rows = {row["component"]: row for row in numeric_scope["rows"]}
    numeric_complement = set(numeric_scope["complement_ids"])
    numeric_status = []
    for identity in component_ids:
        row = numeric_rows.get(identity)
        if row is not None:
            numeric_status.append({"component_id": identity, "status": "in-selected-numeric-diagnosis-scope",
                                   "diagnosis_scope_row": row})
        elif identity in numeric_complement:
            numeric_status.append({"component_id": identity, "status": "in-explicit-numeric-complement; no clearance inferred"})
        else:
            raise ValueError(f"Numerical selected/complement source leaves family member unaccounted: {identity}")

    # Revalidate required controls against actual complete source bodies.
    def exact_roster(values, expected, label):
        if len(values) != len(expected) or len(set(values)) != len(values) or set(values) != set(expected):
            raise ValueError(f"{label} roster invalid")
    exact_roster([f["id"] for f in full_components], component_ids, "candidate")
    exact_roster([f.get("id", f.get("properties", {}).get("id")) for f in [current_by_id[x] for x in contact_ids]],
                 contact_ids, "current contact")
    route_bodies = [route_map[x]["record"] for x in component_ids]
    if len(route_bodies) != 49 or any(r["component"] not in expected_components for r in route_bodies):
        raise ValueError("Foreign/omitted/duplicate complete route source rows")
    if any(sha(canonical(candidates_by_id[r["component"]])) != r["current_feature_sha256"] or
           sha(canonical(candidates_by_id[r["component"]]["geometry"])) != r["current_geometry_sha256"] for r in route_bodies):
        raise ValueError("Complete source geometry binding changed")

    def must_reject(name, operation):
        try:
            operation()
        except (ValueError, KeyError, TypeError):
            return {"id": name, "outcome": "passed", "expected": "reject"}
        raise ValueError(f"Negative control did not reject: {name}")

    negative_controls = [
        must_reject("omitted-component", lambda: exact_roster(component_ids[1:], component_ids, "candidate")),
        must_reject("duplicate-component", lambda: exact_roster(component_ids + [component_ids[0]], component_ids, "candidate")),
        must_reject("foreign-subject", lambda: exact_roster(component_ids + ["physical-component:foreign-control"], component_ids, "candidate")),
        must_reject("source-body-hash", lambda: legacy_inputs.checked_encoded(source_raw[:-1] + bytes([source_raw[-1] ^ 1]),
            {"bytes": len(source_raw), "sha256": sha(source_raw)})),
        must_reject("geometry-binding", lambda: _reject_geometry(candidates_by_id[component_ids[0]], route_map[component_ids[0]]["record"])),
        must_reject("omitted-contact", lambda: exact_roster(contact_ids[1:], contact_ids, "contact")),
    ]

    output.mkdir(parents=True, exist_ok=False)
    (output / "original-consumed-source.geojson.gz").write_bytes(source_raw)
    (output / "original-consumed-source.geojson").write_bytes(source_decoded)
    (output / "original-source-features.geojson").write_bytes(canonical(original_geo) + b"\n")
    (output / "current-contact-containing-part-21.json").write_bytes(part_raw)
    (output / "current-world-index.json").write_bytes(index_pin and git("show", f"{BASELINE}:data/world-index.json"))
    (output / "current-contact-features.geojson").write_bytes(canonical({"type": "FeatureCollection", "features": [current_by_id[x] for x in contact_ids]}) + b"\n")
    (output / "candidate-component-features.geojson").write_bytes(canonical({"type": "FeatureCollection", "features": full_components}) + b"\n")
    (output / "candidate-routing-rows.jsonl").write_bytes(b"".join(json.dumps(route_map[x]["record"], sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n" for x in component_ids))
    (output / "complete-family-record.json").write_bytes(canonical(family_record) + b"\n")
    (output / "numeric-scope-family-rows.json").write_bytes(canonical({"selected_rows": numeric_status,
        "selected_count": sum(x["status"] == "in-selected-numeric-diagnosis-scope" for x in numeric_status),
        "complement_count": sum(x["status"].startswith("in-explicit-numeric-complement") for x in numeric_status),
        "scope_sha256": numeric_scope_pin["sha256"], "scope_commit": NUMERIC}) + b"\n")
    (output / "source-records.json").write_bytes(canonical({
        "original_source_metadata": metadata_row,
        "original_source_metadata_canonical_sha256": metadata_row_sha,
        "individual_source_attribution": citation_rows[0],
        "source_catalogue_record": catalogue_row,
        "source_geometry_feature_count": 147,
        "source_geometry_shape_ids": sorted(original_by_shape),
        "source_contact_features": [{"contact_id": identity, "source_shape_id": identity.split("gb:SAU:ADM2:", 1)[1],
                                      "whole_source_feature": original_by_shape.get(identity.split("gb:SAU:ADM2:", 1)[1])}
                                     for identity in contact_ids],
        "current_contact_feature_hashes": {x: sha(canonical(current_by_id[x])) for x in contact_ids},
        "current_world_index_owner_rows": [x for x in owner_rows if x.get("id") in expected_contacts],
        "original_encoded_source_pin": source_payload_pin,
        "original_decoded_source_identity": {"bytes": len(source_decoded), "sha256": sha(source_decoded)},
        "whole_current_index_pin": index_pin, "whole_current_contact_file_pin": part_pin,
        "whole_current_source_metadata_file_pin": admin_pin,
        "whole_source_catalogue_file_pin": catalogue_pin,
        "whole_individual_attribution_file_pin": attribution_pin,
        "routing_report_pin": route_report_pin, "numeric_report_pin": numeric_report_pin,
        "numeric_scope_pin": numeric_scope_pin,
        "source_records_are_byte_custody_only": True,
        "source_authority_and_legal_applicability": "unapproved and unresolved"
    }) + b"\n")
    (output / "control-results.json").write_bytes(canonical({
        "positive": {"id": "complete-source-candidate-contact-family-binding", "outcome": "passed",
                     "candidate_count": 49, "contact_count": 6,
                     "family_id": families[0], "source_feature_count": 147,
                     "whole_routing_component_rows": route_receipt["records"],
                     "whole_routing_family_rows": family_receipt["records"]},
        "negative": negative_controls
    }) + b"\n")
    (output / "reconstruction-receipts.json").write_bytes(canonical({
        "source_input_receipts": source_receipts,
        "existing_reconstruction": reconstruction,
        "existing_audit_report_sha256": sha(canonical(audit)),
        "full_current_component_count": len(current["components"]),
        "full_current_fragment_count": len(current["fragments"]),
        "full_current_contact_count": len(current["contacts"]),
        "full_current_residue_count": len(current["residues"]),
        "selected_full_component_ids": component_ids,
        "source_body_closure": {"routing_components": route_receipt, "routing_families": family_receipt},
    }) + b"\n")
    summary = {
        "issue": 1336, "issue_body_sha256": issue_body_hash(body), "baseline_commit": BASELINE,
        "family_ids": families, "component_count": len(full_components), "contact_count": len(contact_ids),
        "complete_original_source_features": 147,
        "source_raw_bytes": len(source_decoded), "source_raw_sha256": sha(source_decoded),
        "routing_component_rows": route_receipt["records"], "routing_family_rows": family_receipt["records"],
        "whole_route_raw_sha256": route_receipt["sha256"], "whole_family_raw_sha256": family_receipt["sha256"],
        "numeric_selected_count": sum(x["status"] == "in-selected-numeric-diagnosis-scope" for x in numeric_status),
        "numeric_complement_count": sum(x["status"].startswith("in-explicit-numeric-complement") for x in numeric_status),
        "all_source_and_legal_authority": "unapproved; no source-fit, shoreline, land/water, ownership, date, precision, or repair clearance inferred",
        "source_science_rerun": False,
        "output_files": []
    }
    for path in sorted(output.iterdir()):
        if path.is_file():
            raw = path.read_bytes()
            summary["output_files"].append({"path": path.name, "bytes": len(raw), "sha256": sha(raw)})
    (output / "summary.json").write_bytes(canonical(summary) + b"\n")
    return summary


def _reject_geometry(feature, route):
    value = json.loads(canonical(feature))
    def mutate(node):
        if isinstance(node, list):
            if node and isinstance(node[0], (int, float)):
                node[0] = float(node[0]) + 0.000001
                return True
            for child in node:
                if mutate(child):
                    return True
        return False
    if not mutate(value["geometry"]["coordinates"]):
        raise ValueError("Could not construct a pointset mutation")
    if sha(canonical(value["geometry"])) == route["current_geometry_sha256"]:
        raise ValueError("Geometry control mutation unexpectedly identical")
    try:
        if sha(canonical(value)) != route["current_feature_sha256"] or sha(canonical(value["geometry"])) != route["current_geometry_sha256"]:
            raise ValueError("changed pointset fails exact route binding")
    except ValueError:
        raise ValueError("changed pointset rejected by exact geometry binding")
    raise AssertionError("Geometry binding accepted a changed pointset")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--repo", default=str(ROOT))
    parser.add_argument("--run-id")
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.freeze:
        lock = derive_source_closure(Path(args.repo).resolve())
        lock_raw = canonical(lock) + b"\n"
        (PKG / "frozen-execution.json").write_bytes(lock_raw)
        print(json.dumps({"result": "FROZEN", "sha256": sha(lock_raw), "sources": lock["source_blob_count"],
                          "encoded_bytes": lock["source_blob_encoded_bytes"], "code_files": len(lock["code"])}))
        return
    if not args.run_id or not re.fullmatch(r"run-[12]", args.run_id) or not args.output:
        raise SystemExit("Use --run-id run-1|run-2 --output ABSENT_OUTPUT_DIRECTORY")
    lock = json.loads((PKG / "frozen-execution.json").read_bytes())
    verify_frozen_code(lock)
    result = extract(Path(args.repo).resolve(), Path(args.output).resolve(), lock)
    print(json.dumps({"result": "PASS", "run_id": args.run_id,
                      "output_sha256": sha(canonical(result["output_files"])),
                      "components": result["component_count"], "contacts": result["contact_count"]}))


if __name__ == "__main__":
    main()
