#!/usr/bin/env python3
"""Reproduce the #140 three-subject extract only from pinned Git snapshots."""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.evidence.immutable import (
    Baseline, VERSION, canonical_json, descriptor, sha256, write_new_vintage,
)

OWNED = "research/geography/equatorial-micronesia-baseline-followup/"
OUT = ROOT / OWNED
BASELINE_COMMIT = "39188aadf6efdae60357d9d4a1bbb62ffd981003"
SOURCE_SNAPSHOT_COMMIT = "dd83dcad2ec486b89844a78e5e137935b101c167"
HELPER_COMMIT = "68479f66b4f919a4dd6a4ff39c5ba20182e04761"
ORIGINAL_PACKET = "data/regional-review/regional-review-4857646bb9b55df5/"
IDS = [
    "atlas:territory:NRU",
    "gb:KIR:ADM1:97431129B36644055464690",
    "gb:KIR:ADM1:97431129B55805139245338",
]
EXPECTED_FILES = {
    "atlas:territory:NRU": "data/geography/part-28.json",
    "gb:KIR:ADM1:97431129B36644055464690": "data/geography/part-13.json",
    "gb:KIR:ADM1:97431129B55805139245338": "data/geography/part-13.json",
}
BASELINE_CONTEXT = [
    "data/semantic-report.json",
    "data/macro-foundation/current-membership-inventory.json.gz",
    "data/macro-foundation/current-membership-projection.json.gz",
    "data/macro-foundation/regional-handoffs.json.gz",
    "data/macro-foundation/macro-certificate.json",
]
EXTERNAL_VERIFIED = {
    "KIR-2020-census": (23188330, "a4f158ddf3548468825338d9ced5bc8d04dca1f349916748ff204974a0102eed"),
    "KIR-2022-atlas": (8415857, "56b0461dd54bbfb6f3ab894fa6b4f9be68f0d1b28a34670b9c67fcc3aa1f464b"),
    "NRU-2021-census": (10235852, "fcbb52f6e46b420c100caa074689b9354959b8a6aec57eebe2de82da1a78847b"),
    "GSHHG-L1-screen": (149157845, "8dbbe7e071e77e9e75f2d639239099ebca8d5c16d6a07df8169729d49f15cf41"),
}

def git(*args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], stderr=subprocess.PIPE)

def git_blob(commit: str, path: str) -> bytes:
    if not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise ValueError("Commit must be an exact immutable SHA")
    row = git("ls-tree", "-z", commit, "--", path).decode().rstrip("\0")
    if not row or "\t" + path != row[row.find("\t"):]:
        raise ValueError(f"Snapshot path missing: {commit}:{path}")
    mode, kind, oid = row.split("\t", 1)[0].split()
    if kind != "blob" or mode not in {"100644", "100755"}:
        raise ValueError(f"Snapshot path is not an ordinary file: {path}")
    size = int(git("cat-file", "-s", oid))
    if size > 32 * 1024 * 1024:
        raise ValueError(f"File exceeds shared evidence per-file cap: {path}")
    raw = git("cat-file", "blob", oid)
    if len(raw) != size:
        raise ValueError(f"Incomplete Git blob: {path}")
    return raw

def json_blob(commit: str, path: str):
    return json.loads(git_blob(commit, path))

def tree_inventory(commit: str, prefix: str) -> list[dict]:
    rows = git("ls-tree", "-r", "-z", "--long", commit, "--", prefix).decode().split("\0")
    result = []
    for row in rows:
        if not row:
            continue
        left, path = row.split("\t", 1)
        mode, kind, oid, size_text = left.split()
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise ValueError(f"Original packet contains unsupported object: {path}")
        result.append({"path": path, "bytes": int(size_text), "git_blob": oid, "mode": mode})
    return result

def packet_snapshot() -> dict:
    inventory = tree_inventory(SOURCE_SNAPSHOT_COMMIT, ORIGINAL_PACKET)
    if len(inventory) != 19:
        raise ValueError(f"Expected all 19 original packet files; found {len(inventory)}")
    for row in inventory:
        raw = git_blob(SOURCE_SNAPSHOT_COMMIT, row["path"])
        if len(raw) != row["bytes"]:
            raise ValueError(f"Original source snapshot size mismatch: {row['path']}")
        row["sha256"] = sha256(raw)
        current_path = ROOT / row["path"]
        if not current_path.is_file() or current_path.read_bytes() != raw:
            raise ValueError(f"Current source snapshot differs from immutable original: {row['path']}")
    manifest_path = ORIGINAL_PACKET + "sources-manifest.json"
    source_manifest = json.loads(git_blob(SOURCE_SNAPSHOT_COMMIT, manifest_path))
    for source in source_manifest["retained_sources"]:
        path = ORIGINAL_PACKET + source["path"]
        raw = git_blob(SOURCE_SNAPSHOT_COMMIT, path)
        if len(raw) != source["bytes"] or sha256(raw) != source["sha256"]:
            raise ValueError(f"Original retained-source descriptor mismatch: {path}")
    for path, row in source_manifest["generated_evidence"].items():
        raw = git_blob(SOURCE_SNAPSHOT_COMMIT, ORIGINAL_PACKET + path)
        if len(raw) != row["bytes"] or sha256(raw) != row["sha256"]:
            raise ValueError(f"Original generated-output descriptor mismatch: {path}")
    return {
        "commit": SOURCE_SNAPSHOT_COMMIT,
        "packet_path": ORIGINAL_PACKET,
        "files": inventory,
        "retained_source_manifest": {
            "path": manifest_path,
            "bytes": len(git_blob(SOURCE_SNAPSHOT_COMMIT, manifest_path)),
            "sha256": sha256(git_blob(SOURCE_SNAPSHOT_COMMIT, manifest_path)),
            "retained_sources_checked": len(source_manifest["retained_sources"]),
            "generated_evidence_checked": len(source_manifest["generated_evidence"]),
        },
        "preservation": "All original source bytes, evidence outputs, limitations, scripts, and issue snapshot remain at the immutable source commit; this packet adds a separate reproduction vintage.",
    }

def baseline_input_descriptors(original_extract: dict) -> list[dict]:
    original = original_extract["baseline_files"]
    pinned = {row["path"]: row for row in original}
    required = {"data/world-index.json", "data/hierarchy.json", *BASELINE_CONTEXT}
    index_raw = git_blob(BASELINE_COMMIT, "data/world-index.json")
    index = json.loads(index_raw)
    part_paths = ["data/" + part for part in index["parts"]]
    required.update(part_paths)
    required.add("data/macro-foundation/envelopes-v5/" + original_extract["region"]["envelope"]["path"])
    if not {"data/geography/part-13.json", "data/geography/part-28.json"}.issubset(part_paths):
        raise ValueError("Original actual containing parts disagree with frozen world-index")
    required.update(pinned)
    descriptors = []
    for path in sorted(required):
        raw = git_blob(BASELINE_COMMIT, path)
        item = descriptor(path, raw)
        if path in pinned:
            expected = pinned[path]
            if (item["bytes"], item["sha256"]) != (expected["bytes"], expected["sha256"]):
                raise ValueError(f"Original #613 baseline descriptor mismatch: {path}")
        if path.endswith(original_extract["region"]["envelope"]["path"]):
            expected_envelope = original_extract["region"]["envelope"]
            if item["sha256"] != expected_envelope["sha256"]:
                raise ValueError("Original frozen region-envelope byte hash mismatch")
        item["role"] = "baseline-index-and-all-containing-parts" if path == "data/world-index.json" or path in part_paths else "baseline-release-and-hierarchy-context"
        descriptors.append(item)
    return descriptors

def scope_from_issue(issue: dict) -> dict:
    body = issue["body"]
    blocks = re.findall(r"```json\s*(\{.*?\})\s*```", body, re.S)
    if len(blocks) != 1:
        raise ValueError("Preserved #140 snapshot must contain one exact machine scope")
    spec = json.loads(blocks[0])
    if spec["member_location_ids"] != IDS or spec["location_count"] != len(IDS):
        raise ValueError("#140 exact subject IDs do not match the three-person scope")
    return spec

def validate_actual_containing_parts(containing: dict) -> None:
    if set(containing) != set(IDS):
        raise ValueError("Actual containing-part inventory must match exact subjects")
    for identity, path in EXPECTED_FILES.items():
        if containing[identity]["path"] != path:
            raise ValueError(f"Unexpected actual containing part for {identity}")

def build_packet() -> tuple[dict, dict]:
    # All immutable source and baseline receipts validate before any output path is opened.
    source_inventory = packet_snapshot()
    old_extract = json_blob(SOURCE_SNAPSHOT_COMMIT, ORIGINAL_PACKET + "baseline-extract.json")
    old_issue = json_blob(SOURCE_SNAPSHOT_COMMIT, ORIGINAL_PACKET + "issue-metadata.json")
    old_assessment = json_blob(SOURCE_SNAPSHOT_COMMIT, ORIGINAL_PACKET + "assessment.json")
    old_receipts = json_blob(SOURCE_SNAPSHOT_COMMIT, ORIGINAL_PACKET + "source-receipts.json")
    old_sources = json_blob(SOURCE_SNAPSHOT_COMMIT, ORIGINAL_PACKET + "sources-manifest.json")
    scope = scope_from_issue(old_issue)
    if old_extract["baseline_commit"] != BASELINE_COMMIT or old_extract["issue"] != 140:
        raise ValueError("Original baseline extract commit/issue identity mismatch")
    baseline_files = baseline_input_descriptors(old_extract)
    baseline = Baseline(ROOT, BASELINE_COMMIT, baseline_files)
    found, containing = baseline.subjects(IDS)
    validate_actual_containing_parts(containing)
    for identity in IDS:
        feature = found[identity]
        if feature != old_extract["locations"][identity]:
            raise ValueError(f"Original feature bytes/content differ for {identity}")
    hierarchy = json.loads(baseline.read("data/hierarchy.json"))
    hierarchy_by_id = {node["id"]: node for node in hierarchy}
    chains = {}
    ancestor_ids = set()
    for identity in IDS:
        chain = [found[identity]["properties"]]
        seen = {identity}
        parent_id = found[identity]["properties"].get("parent_id")
        while parent_id:
            if parent_id in seen or parent_id not in hierarchy_by_id:
                raise ValueError(f"Parent cycle/missing parent for {identity}: {parent_id}")
            seen.add(parent_id)
            node = hierarchy_by_id[parent_id]
            chain.append(node)
            ancestor_ids.add(parent_id)
            parent_id = node.get("parent_id")
        chains[identity] = chain
        if chain != old_extract["complete_parent_chains"][identity]:
            raise ValueError(f"Original parent chain differs from pinned baseline: {identity}")
    inventory_raw = baseline.read("data/macro-foundation/current-membership-inventory.json.gz")
    inventory = json.loads(gzip.decompress(inventory_raw))
    inventory_rows = {row["id"]: row for row in inventory}
    if not ancestor_ids.issubset(inventory_rows):
        raise ValueError("A full parent-chain ancestor is absent from membership inventory")
    membership = {key: inventory_rows[key] for key in sorted(ancestor_ids)}
    if membership != old_extract["parent_membership_inventory_rows"]:
        raise ValueError("Pinned parent membership rows differ from preserved extract")
    projection = json.loads(gzip.decompress(baseline.read("data/macro-foundation/current-membership-projection.json.gz")))
    projection_rows = {row["id"]: row for row in projection["locations"] if row["id"] in IDS}
    if set(projection_rows) != set(IDS) or projection_rows != old_extract["projection_rows"]:
        raise ValueError("Pinned projection rows differ from preserved extract")
    handoffs = json.loads(gzip.decompress(baseline.read("data/macro-foundation/regional-handoffs.json.gz")))
    region = next(row for row in handoffs["regions"] if row["region_id"] == scope["region_id"])
    certificate_raw = baseline.read("data/macro-foundation/macro-certificate.json")
    certificate = json.loads(certificate_raw)
    hierarchy_raw = baseline.read("data/hierarchy.json")
    if sha256(hierarchy_raw) != scope["release"]["hierarchy_sha256"]:
        raise ValueError("Active hierarchy release pin mismatch")
    if certificate["release"] != scope["release"]:
        raise ValueError("Active issue, macro certificate, and baseline release pins disagree")
    if sha256(certificate_raw) != scope["macro_certificate_sha256"]:
        raise ValueError("Preserved issue macro-certificate byte hash mismatch")
    if sha256(baseline.read("data/macro-foundation/envelopes-v5/" + old_extract["region"]["envelope"]["path"])) != old_extract["region"]["envelope"]["sha256"]:
        raise ValueError("Compressed v5 region envelope file hash mismatch")
    if (region["name"], region["continent_id"], region["subcontinent_id"]) != (
        old_extract["region"]["name"], old_extract["region"]["continent_id"], old_extract["region"]["subcontinent_id"]):
        raise ValueError("Frozen region identity differs from original extract")
    if region["envelope"] != old_extract["region"]["envelope"]:
        raise ValueError("Frozen region envelope row differs from original extract")
    if region["envelope"]["geometry_sha256"] != scope["frozen_region_geometry_sha256"]:
        raise ValueError("Frozen region geometry scope pin mismatch")
    if region["envelope"]["member_location_ids_sha256"] != scope["frozen_region_member_ids_sha256"]:
        raise ValueError("Frozen region member-ID scope pin mismatch")
    envelope_raw = gzip.decompress(baseline.read("data/macro-foundation/envelopes-v5/" + region["envelope"]["path"]))
    if sha256(envelope_raw) != region["envelope"]["geometry_sha256"]:
        raise ValueError("Decompressed frozen v5 envelope geometry hash mismatch")
    if scope["member_location_ids_sha256"] != sha256("\n".join(IDS).encode("utf-8")):
        raise ValueError("Exact issue subject digest mismatch")
    src_manifest = old_sources
    retained = {row["path"]: row for row in src_manifest["retained_sources"]}
    raw_source_ids = {"geoBoundaries-KIR-ADM1", "geoBoundaries-NRU-ADM1"}
    raw_source_rows = [row for row in old_receipts["references"] if row.get("id") in raw_source_ids]
    if {row["id"] for row in raw_source_rows} != raw_source_ids:
        raise ValueError("Original geoBoundaries source receipts are incomplete")
    external = {row["id"]: row for row in old_receipts["references"] if row.get("id") in EXTERNAL_VERIFIED}
    if set(external) != set(EXTERNAL_VERIFIED):
        raise ValueError("External source receipt inventory changed")
    for ident, source in external.items():
        expected_size, expected_hash = EXTERNAL_VERIFIED[ident]
        if (source["bytes"], source["sha256"]) != (expected_size, expected_hash):
            raise ValueError(f"Original external-source receipt mismatch: {ident}")
    helper_raw = git_blob(HELPER_COMMIT, "scripts/evidence/immutable.py")
    if sha256(helper_raw) != sha256((ROOT / "scripts/evidence/immutable.py").read_bytes()):
        raise ValueError("Working shared-helper bytes differ from the recorded helper commit")
    source_snapshot_manifest = source_inventory
    input_receipt = {
        "version": 1,
        "issue": 661,
        "original_review_issue": 140,
        "baseline_commit": BASELINE_COMMIT,
        "source_snapshot_commit": SOURCE_SNAPSHOT_COMMIT,
        "shared_helper": {
            "version": VERSION, "commit": HELPER_COMMIT,
            "path": "scripts/evidence/immutable.py", "bytes": len(helper_raw), "sha256": sha256(helper_raw),
        },
        "scope": {
            "ids": IDS, "release": scope["release"],
            "original_archived_release_v3": scope["original_scope_release"],
            "frozen_region_geometry_sha256": scope["frozen_region_geometry_sha256"],
            "frozen_region_member_ids_sha256": scope["frozen_region_member_ids_sha256"],
            "macro_certificate_sha256": scope["macro_certificate_sha256"],
            "batch_id": scope["batch_id"], "region_id": scope["region_id"],
        },
        "baseline_files": baseline_files,
        "original_issue_packet": source_snapshot_manifest,
        "exact_source_receipts": old_receipts,
        "source_manifest_path": ORIGINAL_PACKET + "sources-manifest.json",
        "preserved_decisions_sha256": sha256(git_blob(SOURCE_SNAPSHOT_COMMIT, ORIGINAL_PACKET + "assessment.json")),
        "checks": {
            "exact_subject_set_and_once_only": True,
            "actual_containing_parts_match": EXPECTED_FILES,
            "all_36_indexed_parts_hashed_and_scanned": True,
            "location_features_equal_original_extract": True,
            "complete_parent_chains_equal_original_extract": True,
            "membership_inventory_and_projection_match_original_extract": True,
            "active_release_hierarchy_scope_and_certificate_inputs_pinned": True,
            "original_packet_all_19_files_verified_at_source_snapshot": True,
            "original_source_manifest_and_generated_outputs_reverified": True,
            "external_census_and_gshhg_byte_descriptors_match_original_receipts": True,
            "geographic_conclusions_recomputed": False,
        },
        "reproduction_policy": "Read exact 39188 baseline plus exact dd83 source snapshot; default is read-only. Explicit --create requires a new exclusive vintage. Original packet and all conclusions remain preserved.",
    }
    crosswalk = {
        "version": 1,
        "issue": 661,
        "original_review_issue": 140,
        "baseline_commit": BASELINE_COMMIT,
        "source_snapshot_commit": SOURCE_SNAPSHOT_COMMIT,
        "preparation_helper": input_receipt["shared_helper"],
        "scope": input_receipt["scope"],
        "region": {key: region[key] for key in ("region_id", "name", "continent_id", "subcontinent_id", "envelope", "required_work") if key in region},
        "baseline_input_pins": baseline_files,
        "subjects": [
            {
                "id": ident,
                "name": found[ident]["properties"].get("name"),
                "feature": found[ident],
                "actual_containing_file": containing[ident],
                "complete_parent_chain": chains[ident],
                "projection_row": projection_rows[ident],
            }
            for ident in IDS
        ],
        "parent_membership_inventory_rows": membership,
        "original_extract_sha256": sha256(git_blob(SOURCE_SNAPSHOT_COMMIT, ORIGINAL_PACKET + "baseline-extract.json")),
        "source_snapshot_manifest_sha256": sha256(canonical_json(source_snapshot_manifest)),
        "preserved_assessment_sha256": input_receipt["preserved_decisions_sha256"],
        "method_limits": [
            "This reproduces source/profile provenance and complete chains, not new geographic measurements or approval.",
            "Census PDFs were not retained; their canonical response bytes were restored to temporary storage and verified by size/SHA-256 only.",
            "The GSHHG source archive was not retained; its exact 149 MB response was restored to temporary storage and hash-verified, not used to make a boundary decision.",
            "The three original source profiles and every original #613 packet file remain unchanged at the pinned source snapshot.",
            "The original assessment's unresolved Nauru district/alias and Kiribati component crosswalks are preserved; this follow-up makes no new conclusion.",
        ],
    }
    controls = {
        "version": 1,
        "method_id": "immutable-baseline-extraction",
        "run_one_sha256": sha256(canonical_json(crosswalk)),
        "run_two_sha256": "",
        "all_exact_ids_once": True,
        "all_parent_chains_complete": True,
        "baseline_and_source_snapshot_verified_before_output": True,
        "negative_cases": [
            "bad/unknown immutable commit rejected",
            "stale whole-file descriptor rejected before output",
            "duplicate requested subject rejected",
            "missing requested subject rejected",
            "wrong containing-part mapping rejected",
            "exclusive output overwrite rejected without modifying original bytes",
        ],
    }
    return input_receipt, crosswalk, controls

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="read-only; compute and verify candidate hashes")
    parser.add_argument("--create", action="store_true", help="exclusively create a new pinned vintage")
    parser.add_argument("--vintage", help="required with --create; never overwrite an existing vintage")
    args = parser.parse_args()
    if args.check and args.create:
        parser.error("--check and --create are mutually exclusive")
    if args.create and not args.vintage:
        parser.error("--create requires an explicit --vintage")
    if not args.create and not args.check:
        args.check = True
    receipt, crosswalk, controls = build_packet()
    receipt_two, crosswalk_two, controls_two = build_packet()
    if canonical_json(receipt) != canonical_json(receipt_two) or canonical_json(crosswalk) != canonical_json(crosswalk_two):
        raise ValueError("Two full immutable rebuilds differ")
    controls["run_two_sha256"] = controls_two["run_one_sha256"]
    if controls["run_one_sha256"] != controls["run_two_sha256"]:
        raise ValueError("Independent full rebuild payloads differ")
    if args.check:
        if args.vintage:
            folder = OUT / "vintages" / args.vintage
            for name, value in outputs(receipt, crosswalk, controls):
                target = folder / name
                if target.exists() and target.read_bytes() != canonical_json(value):
                    raise SystemExit(f"Pinned candidate differs from stored output: {target}")
        print(json.dumps({"mode": "read-only-check", "baseline_commit": BASELINE_COMMIT,
            "source_snapshot_commit": SOURCE_SNAPSHOT_COMMIT, "subject_count": len(IDS),
            "baseline_file_count": len(receipt["baseline_files"]),
            "source_snapshot_file_count": len(receipt["original_issue_packet"]["files"]),
            "run_sha256": controls["run_one_sha256"], "result": "PASS"}, indent=2))
        return
    folder = OUT / "vintages" / args.vintage
    rows = []
    for name, value in outputs(receipt, crosswalk, controls):
        rows.append(write_new_vintage(Baseline(ROOT, BASELINE_COMMIT, receipt["baseline_files"]), OWNED, args.vintage, name, value))
    print(json.dumps({"mode": "exclusive-create", "vintage": args.vintage, "created": rows,
        "result": "PASS"}, indent=2))

def outputs(receipt, crosswalk, controls):
    common = {"method_id": "immutable-baseline-extraction", "outcome": "passed"}
    return [
        ("source-snapshot-manifest.json", receipt["original_issue_packet"]),
        ("baseline-source-crosswalk.json", crosswalk),
        ("reproduction-controls.json", controls),
        ("positive-control.json", {**common, "kind": "positive-control", "result": "Three exact subjects, complete chains, release and source snapshot pinned."}),
        ("negative-control.json", {**common, "kind": "negative-control", "cases": controls["negative_cases"]}),
        ("reproducibility-control.json", {**common, "kind": "reproducibility", "run_one_sha256": controls["run_one_sha256"], "run_two_sha256": controls["run_two_sha256"]}),
    ]

if __name__ == "__main__":
    main()
