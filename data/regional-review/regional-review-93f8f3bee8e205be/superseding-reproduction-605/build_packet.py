#!/usr/bin/env python3
"""Reproduce #486 baseline snapshots from immutable inputs without touching originals."""
import argparse
import gzip
import hashlib
import json
import re
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OWNED = "data/regional-review/regional-review-93f8f3bee8e205be/"
OUT = ROOT / OWNED / "superseding-reproduction-605"
VINTAGE = "20261004-canonical-gzip"
SCOPE_PATH = OWNED + "superseding-reproduction-605/scope.json"
ORIGINAL = OWNED
SOURCE_SNAPSHOT_COMMIT = "276d72e1f316ad58d52c8fea7974a873c2ec9387"
BASELINE_COMMIT = "0ea5b92969a37e404daded7a5c1d8931bd74b19c"
HELPER_COMMIT = "2663a852ca911d059f4a764a7b84b70f94635d81"
OLD_FEATURE = ORIGINAL + "sources/current-scope-and-parents.geojson.gz"
OLD_CHAINS = ORIGINAL + "sources/current-parent-chains.json.gz"
OLD_RECEIPT = ORIGINAL + "baseline-extract-receipt.json"
OLD_REGISTRY = ORIGINAL + "sources.json"
WORLD_INDEX = "data/world-index.json"
HIERARCHY = "data/hierarchy.json"
INVENTORY = "data/macro-foundation/current-membership-inventory.json.gz"
MACRO = "data/macro-foundation/macro-certificate.json"
ENVELOPE_INDEX = "data/macro-foundation/envelopes-v5/envelope-index.json"

sys.path.insert(0, str(ROOT))
from scripts.evidence.immutable import Baseline, canonical_json, deterministic_gzip, descriptor, sha256, write_new_vintage  # noqa: E402


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], stderr=subprocess.PIPE)


def exact_commit(commit: str) -> None:
    if not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise ValueError("Expected an exact immutable commit")
    try:
        resolved = git("rev-parse", "--verify", "--end-of-options", commit + "^{commit}").decode().strip()
    except subprocess.CalledProcessError as exc:
        raise ValueError("Immutable commit is unavailable") from exc
    if resolved != commit:
        raise ValueError("Commit identity mismatch")


def ordinary_tree(commit: str, prefix: str) -> list[dict]:
    exact_commit(commit)
    rows = []
    output = git("ls-tree", "-rl", "--full-tree", commit, "--", prefix)
    for raw in output.splitlines():
        metadata, path = raw.split(b"\t", 1)
        mode, kind, oid, size = metadata.decode().split()
        if mode not in {"100644", "100755"} or kind != "blob":
            raise ValueError("Original packet must contain ordinary files: " + path.decode())
        name = path.decode()
        if name.endswith("/") or not name.startswith(prefix):
            raise ValueError("Unexpected original packet path")
        blob = git("cat-file", "blob", oid)
        rows.append({"path": name, "bytes": int(size), "sha256": sha256(blob), "hash_kind": "file-bytes"})
    if not rows:
        raise ValueError("Empty source packet tree")
    return sorted(rows, key=lambda x: x["path"])


def project_paths() -> list[str]:
    index = json.loads(git("show", f"{BASELINE_COMMIT}:{WORLD_INDEX}"))
    parts = index.get("parts")
    if not isinstance(parts, list) or len(parts) != 36 or len(parts) != len(set(parts)):
        raise ValueError("Unexpected exact world-index partition")
    paths = {WORLD_INDEX, HIERARCHY, INVENTORY, MACRO, ENVELOPE_INDEX}
    paths.update("data/" + part for part in parts)
    return sorted(paths)


def project_pins() -> list[dict]:
    return [descriptor(path, git("show", f"{BASELINE_COMMIT}:{path}")) for path in project_paths()]


def validate_issue_capture(scope: dict) -> None:
    body = scope.get("issue_body", "")
    if scope.get("issue") != 605 or scope.get("owned_path") != OWNED:
        raise ValueError("Issue capture does not bind the accepted issue scope")
    if sha256(body.encode()) != scope.get("issue_body_sha256"):
        raise ValueError("Captured GitHub issue body hash changed")
    blocks = re.findall(r"<!-- worldatlas-work:v1\s*\n([\s\S]*?)\n-->", body)
    if len(blocks) != 1 or json.loads(blocks[0]) != scope.get("contract"):
        raise ValueError("Captured issue machine contract changed")
    if body.split("<!-- worldatlas-work:v1")[0] != scope.get("acceptance_text"):
        raise ValueError("Captured acceptance text differs from raw GitHub issue body")
    contract = scope.get("contract", {})
    if (contract.get("mode") != "geography" or contract.get("max_prs") != 1 or
            contract.get("owned_paths") != [OWNED] or contract.get("depends_on") != []):
        raise ValueError("Issue ownership or PR budget changed")
    if scope.get("original_packet_commit") != SOURCE_SNAPSHOT_COMMIT:
        raise ValueError("Original packet snapshot changed")
    if scope.get("original_baseline_commit") != BASELINE_COMMIT:
        raise ValueError("Original evaluation baseline changed")
    if sha256(json.dumps(sorted(scope.get("subject_ids", [])), separators=(",", ":")).encode()) != scope.get("subject_ids_sha256"):
        raise ValueError("Exact subject roster digest mismatch")
    if len(scope["subject_ids"]) != 211 or len(set(scope["subject_ids"])) != 211:
        raise ValueError("The inherited 211-location scope must remain exact")
    raw_scope = git("show", SOURCE_SNAPSHOT_COMMIT + ":" + ORIGINAL + "scope.json")
    raw_sources = git("show", SOURCE_SNAPSHOT_COMMIT + ":" + OLD_REGISTRY)
    raw_receipt = git("show", SOURCE_SNAPSHOT_COMMIT + ":" + OLD_RECEIPT)
    for raw, key in ((raw_scope, "original_scope_sha256"),
                     (raw_sources, "original_source_registry_sha256"),
                     (raw_receipt, "original_extract_receipt_sha256")):
        if sha256(raw) != scope[key]:
            raise ValueError("Changed original scope/source receipt: " + key)


def validate_registry_rows(registry: dict, source_rows: dict) -> set[str]:
    declared = registry.get("sources")
    if not isinstance(declared, list) or len(declared) != 24:
        raise ValueError("Original source registry inventory changed")
    seen = set()
    for row in declared:
        name = ORIGINAL + "sources/" + row["path"]
        if name in seen or name not in source_rows:
            raise ValueError("Retained source path is missing or duplicated: " + name)
        seen.add(name)
        actual = source_rows[name]
        if actual["bytes"] != row["bytes"] or actual["sha256"] != row["sha256"]:
            raise ValueError("Retained source whole-file hash differs from original registry: " + name)
    return seen


def verify_source_snapshot(scope: dict) -> tuple[Baseline, dict, dict]:
    files = ordinary_tree(SOURCE_SNAPSHOT_COMMIT, ORIGINAL)
    source_baseline = Baseline(ROOT, SOURCE_SNAPSHOT_COMMIT, files)
    registry = json.loads(source_baseline.read(OLD_REGISTRY))
    receipt = json.loads(source_baseline.read(OLD_RECEIPT))
    source_rows = {f["path"]: f for f in files}
    seen = validate_registry_rows(registry, source_rows)
    declared = registry["sources"]
    for name, expected in ((OLD_FEATURE, receipt["feature_data"]), (OLD_CHAINS, receipt["chain_data"])):
        actual = source_rows.get(name)
        if not actual or actual["bytes"] != expected["compressed_bytes"] or actual["sha256"] != expected["compressed_sha256"]:
            raise ValueError("Original compressed archive differs from its retained receipt: " + name)
    snapshot = {
        "version": 1,
        "issue": 605,
        "source_snapshot_commit": SOURCE_SNAPSHOT_COMMIT,
        "source_snapshot_tree": files,
        "original_source_registry": {
            "path": OLD_REGISTRY,
            "bytes": source_rows[OLD_REGISTRY]["bytes"],
            "sha256": source_rows[OLD_REGISTRY]["sha256"],
            "retained_source_file_count": len(declared),
            "retained_source_files": sorted(seen),
            "omitted_raw_source_hashes": registry["omitted_raw_source_hashes"],
        },
        "original_scope": {"path": ORIGINAL + "scope.json", "sha256": scope["original_scope_sha256"]},
        "original_extract_receipt": {"path": OLD_RECEIPT, "sha256": scope["original_extract_receipt_sha256"]},
        "original_extract_archives": [
            {"path": name, "compressed_bytes": source_rows[name]["bytes"],
             "compressed_sha256": source_rows[name]["sha256"],
             "uncompressed_bytes": receipt[key]["uncompressed_bytes"],
             "uncompressed_sha256": receipt[key]["uncompressed_sha256"]}
            for name, key in ((OLD_FEATURE, "feature_data"), (OLD_CHAINS, "chain_data"))
        ],
        "source_role_and_license_record": {
            "path": ORIGINAL + "README.md",
            "sha256": source_rows[ORIGINAL + "README.md"]["sha256"],
            "canonical_references_dates_licenses_roles_and_restoration": "Preserved verbatim in the original packet README and sources.json at the exact source snapshot commit; not freshly reassessed by this compression correction.",
        },
        "preservation": "All original issue #486 files and source bytes are read at the immutable source snapshot commit and remain unchanged. This correction adds separately identified new-vintage artifacts only.",
    }
    return source_baseline, registry, {"files": files, "manifest": snapshot, "receipt": receipt}


def verify_context(baseline: Baseline, scope: dict) -> dict:
    index = json.loads(baseline.read(WORLD_INDEX))
    hierarchy_raw = baseline.read(HIERARCHY)
    macro_raw = baseline.read(MACRO)
    envelope_index_raw = baseline.read(ENVELOPE_INDEX)
    # The original scope supplies the v5 release pins; the issue contract itself has no evidence pins.
    original_scope = json.loads(git("show", SOURCE_SNAPSHOT_COMMIT + ":" + ORIGINAL + "scope.json"))
    if sha256(hierarchy_raw) != original_scope["release"]["hierarchy_sha256"]:
        raise ValueError("Pinned v5 hierarchy differs from exact evaluation baseline")
    if sha256(macro_raw) != original_scope["macro_certificate_sha256"]:
        raise ValueError("Pinned macro certificate differs from exact evaluation baseline")
    envelope_index = json.loads(envelope_index_raw)
    macro = json.loads(macro_raw)
    region_id = original_scope["region_id"]
    envelope = next((row for row in envelope_index["groups"] if row["id"] == region_id), None)
    certificate = next((row for row in macro["groups"] if row["id"] == region_id), None)
    if not envelope or not certificate:
        raise ValueError("Pinned region missing from frozen envelope/certificate")
    if (envelope["geometry_sha256"] != original_scope["frozen_region_geometry_sha256"] or
            envelope["member_location_ids_sha256"] != original_scope["frozen_region_member_ids_sha256"] or
            certificate["member_location_ids_sha256"] != original_scope["frozen_region_member_ids_sha256"]):
        raise ValueError("Frozen region geometry/member scope changed")
    envelope_path = "data/macro-foundation/envelopes-v5/" + envelope["path"]
    envelope_raw = baseline.read(envelope_path)
    if sha256(envelope_raw) != envelope["sha256"]:
        raise ValueError("Frozen region envelope byte hash differs from index")
    inventory_raw = baseline.read(INVENTORY)
    inventory = json.loads(gzip.decompress(inventory_raw))
    units = {row["id"]: row for row in inventory}
    region = units.get(region_id)
    if not region or region["member_location_ids"] is None:
        raise ValueError("Frozen region member roster missing")
    if not set(scope["subject_ids"]).issubset(region["member_location_ids"]):
        raise ValueError("Exact issue subjects are not all inside the frozen region member roster")
    return {
        "hierarchy_sha256": sha256(hierarchy_raw),
        "macro_certificate_sha256": sha256(macro_raw),
        "world_index_sha256": sha256(baseline.read(WORLD_INDEX)),
        "world_index_parts": list(index["parts"]),
        "world_index_part_count": len(index["parts"]),
        "membership_inventory_sha256": sha256(inventory_raw),
        "region_id": region_id,
        "region_geometry_sha256": envelope["geometry_sha256"],
        "region_member_location_ids_sha256": envelope["member_location_ids_sha256"],
        "region_envelope_path": envelope_path,
        "region_envelope_sha256": sha256(envelope_raw),
        "checks": {
            "assigned_subjects_within_frozen_region": True,
            "issue_scope_is_exact_original_211_subjects": True,
            "original_v5_hierarchy_pin_matches": True,
            "original_macro_certificate_pin_matches": True,
            "frozen_region_geometry_and_member_pins_match": True,
            "shared_geography_changed": False,
            "geographic_conclusions_recomputed": False,
        },
    }


def encoded_output(name: str, value) -> bytes:
    raw = canonical_json(value)
    return deterministic_gzip(raw) if name.endswith(".gz") else raw


def build_packet() -> tuple[Baseline, dict]:
    scope = json.loads((ROOT / SCOPE_PATH).read_text())
    validate_issue_capture(scope)
    source_baseline, registry, source_data = verify_source_snapshot(scope)
    files = project_pins()
    baseline = Baseline(ROOT, BASELINE_COMMIT, files)
    context = verify_context(baseline, scope)
    features, containing = baseline.subjects(scope["subject_ids"], index=WORLD_INDEX)
    inventory = json.loads(gzip.decompress(baseline.read(INVENTORY)))
    units = {row["id"]: row for row in inventory}
    hierarchy = {row["id"]: row for row in json.loads(baseline.read(HIERARCHY))}
    feature_rows, chain_rows = [], []
    for identity in scope["subject_ids"]:
        feature = features[identity]
        props = feature.get("properties", {})
        if props.get("id") != identity:
            raise ValueError("Assigned identity must be read from properties.id: " + identity)
        feature_rows.append(feature)
        chain = [props]
        parent = props.get("parent_id")
        seen = {identity}
        tier_ids = {props.get("level", props.get("type"))}
        while parent:
            if parent in seen:
                raise ValueError("Parent cycle: " + identity)
            seen.add(parent)
            row = units.get(parent)
            if not row:
                raise ValueError("Missing parent inventory record: " + parent)
            definition = hierarchy.get(parent, {})
            chain.append({
                "id": row["id"], "name": row["name"], "level": row["level"],
                "parent_id": row["parent_id"],
                "member_location_ids": row["member_location_ids"] if row["level"] in ("province", "area") else None,
                "metadata": definition.get("metadata", {}),
            })
            tier_ids.add(row["level"])
            if row["level"] in ("province", "area") and identity not in row["member_location_ids"]:
                raise ValueError("Location absent from actual parent membership: " + identity)
            parent = row["parent_id"]
        if len(chain) < 6 or not {"province", "area", "region", "subcontinent", "continent"}.issubset(tier_ids):
            raise ValueError("Incomplete full parent chain: " + identity)
        chain_rows.append({"id": identity, "parent_chain": chain})
    feature_payload = {"type": "FeatureCollection", "features": feature_rows}
    old_feature_raw = source_baseline.read(OLD_FEATURE)
    old_chain_raw = source_baseline.read(OLD_CHAINS)
    original_receipt = source_data["receipt"]
    old_feature_uncompressed = gzip.decompress(old_feature_raw)
    old_chain_uncompressed = gzip.decompress(old_chain_raw)
    if (sha256(old_feature_raw) != original_receipt["feature_data"]["compressed_sha256"] or
            sha256(old_chain_raw) != original_receipt["chain_data"]["compressed_sha256"]):
        raise ValueError("Original archive hash changed")
    if (sha256(old_feature_uncompressed) != original_receipt["feature_data"]["uncompressed_sha256"] or
            sha256(old_chain_uncompressed) != original_receipt["chain_data"]["uncompressed_sha256"]):
        raise ValueError("Original uncompressed payload hash changed")
    if json.loads(old_feature_uncompressed) != feature_payload or json.loads(old_chain_uncompressed) != chain_rows:
        raise ValueError("Immutable baseline rebuild differs from preserved original extract")
    canonical_feature = canonical_json(feature_payload)
    canonical_chain = canonical_json(chain_rows)
    feature_gzip = deterministic_gzip(canonical_feature)
    chain_gzip = deterministic_gzip(canonical_chain)
    if struct.unpack("<I", feature_gzip[4:8])[0] != 0 or struct.unpack("<I", chain_gzip[4:8])[0] != 0:
        raise ValueError("New gzip must use fixed zero mtime")
    if feature_gzip[3] & 8 or chain_gzip[3] & 8 or feature_gzip[9] != 255 or chain_gzip[9] != 255:
        raise ValueError("New gzip must use an empty filename and fixed helper OS header")
    snapshot = source_data["manifest"]
    source_digest = sha256(canonical_json(snapshot))
    crosswalk = {
        "version": 1, "issue": 605,
        "baseline_commit": BASELINE_COMMIT,
        "source_snapshot_commit": SOURCE_SNAPSHOT_COMMIT,
        "scope_sha256": scope["original_scope_sha256"],
        "subject_ids_sha256": scope["subject_ids_sha256"],
        "subject_count": len(scope["subject_ids"]),
        "subject_inventory": [
            {"id": identity, "actual_containing_file": containing[identity]["path"],
             "containing_file_bytes": containing[identity]["bytes"],
             "containing_file_sha256": containing[identity]["sha256"]}
            for identity in scope["subject_ids"]
        ],
        "unique_subject_occurrences": len(features),
        "parent_chains": {"count": len(chain_rows), "all_complete": True,
                           "all_province_area_membership_checks_passed": True},
        "inputs": {"baseline_files": files, "source_snapshot_files": source_data["files"]},
        "frozen_scope_context": context,
        "original_archives": {
            "feature": {"path": OLD_FEATURE, "compressed_sha256": sha256(old_feature_raw),
                        "uncompressed_sha256": sha256(old_feature_uncompressed),
                        "uncompressed_bytes": len(old_feature_uncompressed)},
            "parent_chains": {"path": OLD_CHAINS, "compressed_sha256": sha256(old_chain_raw),
                              "uncompressed_sha256": sha256(old_chain_uncompressed),
                              "uncompressed_bytes": len(old_chain_uncompressed)},
            "preserved_unchanged": True,
        },
        "new_canonical_artifacts": {
            "feature": {"uncompressed_sha256": sha256(canonical_feature), "uncompressed_bytes": len(canonical_feature),
                        "compressed_sha256": sha256(feature_gzip), "compressed_bytes": len(feature_gzip),
                        "mtime": 0, "filename_header": "empty"},
            "parent_chains": {"uncompressed_sha256": sha256(canonical_chain), "uncompressed_bytes": len(canonical_chain),
                              "compressed_sha256": sha256(chain_gzip), "compressed_bytes": len(chain_gzip),
                              "mtime": 0, "filename_header": "empty"},
            "canonical_json": "UTF-8 JSON with sorted keys, compact separators, no non-finite values and one trailing newline",
            "compression": "gzip level 9; deterministic zero mtime; empty filename; Python GzipFile OS header 255",
            "original_uncompressed_payloads_semantically_equal": True,
            "compressed_bytes_are_new_vintage_not_represented_as_original": True,
        },
        "source_snapshot_manifest_sha256": source_digest,
        "method": {
            "helper_version": "worldatlas-evidence-preparation-v1",
            "source_verification": "All ordinary files in the original #486 source-packet Git tree are whole-file hash-checked; every retained source descriptor in sources.json is checked against its exact whole-file bytes before output.",
            "baseline_extraction": "All 36 exact world-index parts at BASELINE_COMMIT are scanned for the 211 exact scoped IDs; each ID is located once in an actual containing file, then complete parent chains and province/area memberships are rebuilt from the same immutable baseline inventory/hierarchy.",
            "uncertainty": "No external facts, source reuse terms, old assessment values, land, settlement, boundary, ownership or region approval are re-adjudicated. Original sources that were omitted are represented only by their prior hashes/restoration URLs.",
        },
    }
    notice = {
        "version": 1, "issue": 605, "status": "superseding-reproduction-notice",
        "original_packet_commit": SOURCE_SNAPSHOT_COMMIT,
        "original_baseline_commit": BASELINE_COMMIT,
        "original_packet_path": ORIGINAL,
        "corrective_finding": "The original extractor used gzip.open(..., 'wb') without fixed mtime or filename, so identical uncompressed JSON produced different compressed hashes on later runs. It also read mutable checkout files and overwrote the original outputs without first verifying whole-file baseline/source pins.",
        "correction": "Rebuild the exact 211-location snapshots from Git blobs at the recorded original baseline, validate all project and source-packet file hashes before output, and create separately identified deterministic gzip artifacts with canonical uncompressed SHA-256 values.",
        "preservation": "Original packet files, assessment, source bytes, scope and original compressed outputs are read from their immutable source commit and are never rewritten.",
        "geographic_effect": "None. This correction is a reproduction/provenance repair; it does not revise the regional findings or shared geographic data.",
        "imports_or_approval": "No regional approval, certificate update, historical import or live action is authorized.",
    }
    receipt = {
        "version": 1, "issue": 605,
        "baseline_commit": BASELINE_COMMIT,
        "source_snapshot_commit": SOURCE_SNAPSHOT_COMMIT,
        "subject_count": 211,
        "world_index_part_count": 36,
        "baseline_pin_count": len(files),
        "source_snapshot_file_count": len(source_data["files"]),
        "retained_sources_verified": len(registry["sources"]),
        "original_feature_compressed_sha256": sha256(old_feature_raw),
        "original_parent_chains_compressed_sha256": sha256(old_chain_raw),
        "original_feature_uncompressed_sha256": sha256(old_feature_uncompressed),
        "original_parent_chains_uncompressed_sha256": sha256(old_chain_uncompressed),
        "new_feature_compressed_sha256": sha256(feature_gzip),
        "new_parent_chains_compressed_sha256": sha256(chain_gzip),
        "new_feature_uncompressed_sha256": sha256(canonical_feature),
        "new_parent_chains_uncompressed_sha256": sha256(canonical_chain),
        "sources_manifest_sha256": source_digest,
        "original_files_modified": False,
    }
    base_outputs = [
        ("source-snapshot-manifest.json", snapshot),
        ("baseline-source-crosswalk.json", crosswalk),
        ("superseding-notice.json", notice),
        ("baseline-extract-receipt.json", receipt),
        ("current-scope-and-parents.json.gz", feature_payload),
        ("current-parent-chains.json.gz", chain_rows),
    ]
    output_digest = sha256(canonical_json([
        {"name": name, "bytes": len(encoded_output(name, value)),
         "sha256": sha256(encoded_output(name, value))} for name, value in base_outputs
    ]))
    controls = {
        "version": 1, "method_id": "issue486-immutable-baseline-deterministic-compression",
        "run_one_sha256": output_digest, "run_two_sha256": output_digest,
        "all_211_exact_subjects_found_once": True,
        "all_36_indexed_parts_scanned": True,
        "complete_parent_chains_and_parent_membership_verified": True,
        "source_snapshot_files_and_24_retained_source_hashes_verified": True,
        "original_compressed_archives_unchanged": True,
        "new_gzip_mtime_zero_and_filename_empty": True,
        "new_uncompressed_payloads_match_original_json_semantics": True,
        "shared_geography_or_assessment_changed": False,
    }
    final = base_outputs + [
        ("reproducibility-control.json", controls),
        ("positive-control.json", {"result": "passed", "method_id": controls["method_id"],
                                    "baseline_commit": BASELINE_COMMIT, "source_snapshot_commit": SOURCE_SNAPSHOT_COMMIT,
                                    "subject_count": 211, "world_index_parts": 36}),
    ]
    return baseline, {"outputs": final, "crosswalk": crosswalk, "controls": controls,
                      "run_sha256": output_digest, "baseline_files": files,
                      "source_files": source_data["files"], "scope": scope}


def full_bytes(values: dict) -> bytes:
    packed = []
    for name, value in values["outputs"]:
        encoded = encoded_output(name, value)
        packed.append({"path": name, "bytes": len(encoded), "sha256": sha256(encoded)})
    return canonical_json(packed)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="read-only check; default")
    group.add_argument("--create", action="store_true", help="create an exclusive new vintage")
    parser.add_argument("--vintage", default=VINTAGE)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", args.vintage):
        parser.error("vintage must be a lowercase ID")
    baseline, packet = build_packet()
    baseline2, packet2 = build_packet()
    if full_bytes(packet) != full_bytes(packet2) or packet["run_sha256"] != packet2["run_sha256"]:
        raise ValueError("Two independent immutable rebuilds differ")
    if args.create:
        created = []
        for name, value in packet["outputs"]:
            created.append(write_new_vintage(baseline, OWNED, args.vintage, name, value))
        print(json.dumps({"mode": "exclusive-create", "vintage": args.vintage,
                          "created": created, "run_sha256": packet["run_sha256"], "result": "PASS"}, indent=2))
        return
    if args.vintage:
        for name, value in packet["outputs"]:
            path = ROOT / OWNED / "vintages" / args.vintage / name
            if path.exists():
                expected = encoded_output(name, value)
                if path.read_bytes() != expected:
                    raise SystemExit("Candidate differs from immutable rebuild: " + str(path))
    print(json.dumps({"mode": "read-only-check", "baseline_commit": BASELINE_COMMIT,
                      "source_snapshot_commit": SOURCE_SNAPSHOT_COMMIT, "subjects": 211,
                      "world_index_parts": 36, "baseline_file_count": len(packet["baseline_files"]),
                      "source_snapshot_files": len(packet["source_files"]),
                      "run_sha256": packet["run_sha256"], "result": "PASS"}, indent=2))


if __name__ == "__main__":
    main()
