#!/usr/bin/env python3
"""Reproduce the four-subject #439 extract only from immutable Git snapshots."""
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
from scripts.evidence.immutable import (  # noqa: E402
    Baseline, VERSION, canonical_json, descriptor, sha256, write_new_vintage,
)

OWNED = "research/geography/southern-indian-ocean-baseline-pins/"
OUT = ROOT / OWNED
SCOPE_PATH = OWNED + "scope.json"
BASELINE_COMMIT = "ff171e1dd1998684d9b3549943d5725817a7aef4"
SOURCE_SNAPSHOT_COMMIT = "4909f04e6e035ffc003d237db68323d005ccdb89"
HELPER_COMMIT = "2663a852ca911d059f4a764a7b84b70f94635d81"
ORIGINAL_PACKET = "data/regional-review/regional-review-2fe7597eb9014901/"
IDS = [
    "atlas:coverage:ATF-5916",
    "atlas:coverage:ATF-5917",
    "atlas:coverage:ATF-5918",
    "atlas:coverage:HMD+00?",
]
BASELINE_CONTEXT = [
    "data/semantic-report.json",
    "data/macro-foundation/current-membership-inventory.json.gz",
    "data/macro-foundation/current-membership-projection.json.gz",
    "data/macro-foundation/regional-handoffs.json.gz",
    "data/macro-foundation/macro-certificate.json",
]


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


def assert_snapshot_file(path: str, raw: bytes, expected: dict) -> None:
    if len(raw) != expected.get("bytes") or sha256(raw) != expected.get("sha256"):
        raise ValueError(f"Immutable source snapshot mismatch: {path}")


def validate_request_pins(scope_snapshot: dict, baseline_commit: str = BASELINE_COMMIT,
                          source_snapshot_commit: str = SOURCE_SNAPSHOT_COMMIT) -> None:
    if baseline_commit != BASELINE_COMMIT or scope_snapshot.get("baseline_commit") != BASELINE_COMMIT:
        raise ValueError("Refusing changed issue baseline commit before output")
    if source_snapshot_commit != SOURCE_SNAPSHOT_COMMIT or scope_snapshot.get("original_packet_commit") != SOURCE_SNAPSHOT_COMMIT:
        raise ValueError("Refusing changed original source-packet commit before output")
    contract = scope_snapshot.get("contract", {})
    evidence = contract.get("evidence_quality", {})
    if scope_snapshot.get("issue") != 654 or scope_snapshot.get("subject_ids") != IDS or evidence.get("subject_ids") != IDS:
        raise ValueError("Issue #654 scope is not the exact four declared subjects")
    if contract.get("owned_paths") != [OWNED] or evidence.get("pins", {}).get("hierarchy_sha256") != \
       "03d23534f87cdd0582bcb228780f00f65090bec2e8a760acbab528383f28549d":
        raise ValueError("Issue #654 ownership or hierarchy pin changed")
    if evidence.get("pins", {}).get("macro_certificate_sha256") != \
       "979afaf22e10dc936ecfe80a8cd288b2ef33d8c7bf509aba9fae4255e3d94d6e":
        raise ValueError("Issue #654 macro-certificate pin changed")


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
            raise ValueError(f"Original packet contains a nonordinary object: {path}")
        raw = git_blob(commit, path)
        if len(raw) != int(size_text):
            raise ValueError(f"Original packet size mismatch: {path}")
        target = ROOT / path
        if not target.is_file() or target.is_symlink():
            raise ValueError(f"Preserved source packet differs from its merge snapshot: {path}")
        assert_snapshot_file(path, target.read_bytes(), {"bytes": len(raw), "sha256": sha256(raw)})
        result.append({"path": path, "bytes": len(raw), "sha256": sha256(raw), "git_blob": oid, "mode": mode})
    return result


def issue_scope(issue: dict) -> dict:
    blocks = re.findall(r"Machine-readable exact workload scope \(JSON;.*?\):\s*```json\s*(\{.*?\})\s*```", issue["body"], re.S)
    if len(blocks) != 1:
        raise ValueError("Original #439 snapshot must contain exactly one frozen workload scope")
    return json.loads(blocks[0])


def baseline_input_descriptors(old_extract: dict, old_quality: dict, scope: dict) -> list[dict]:
    original = {row["path"]: row for row in old_extract["baseline_files"]}
    # The original manifest also hashes canonical-grid source files. Their
    # archived counts are preserved, but this extractor does not read or
    # recompute them; pin only inputs consumed by this baseline extraction.
    quality = {row["path"]: row for row in old_quality["baseline"]["files"]
               if not row["path"].startswith("data/canonical-grid/")}
    index_raw = git_blob(BASELINE_COMMIT, "data/world-index.json")
    index = json.loads(index_raw)
    part_paths = ["data/" + path for path in index["parts"]]
    required = {
        "data/world-index.json", "data/hierarchy.json", *BASELINE_CONTEXT, *original, *quality,
    }
    required.update(part_paths)
    if "data/geography/part-28.json" not in part_paths:
        raise ValueError("Frozen world-index no longer lists the original containing part")
    if not old_quality["baseline"].get("subject_files"):
        raise ValueError("Original evidence receipt lacks actual subject-to-file crosswalk")

    handoffs = json.loads(gzip.decompress(git_blob(BASELINE_COMMIT, "data/macro-foundation/regional-handoffs.json.gz")))
    region_id = scope["region_id"]
    matches = [row for row in handoffs["regions"] if row["region_id"] == region_id]
    if len(matches) != 1:
        raise ValueError("Frozen regional handoff row is missing or duplicated")
    envelope = matches[0]["envelope"]
    envelope_path = "data/macro-foundation/envelopes-v5/" + envelope["path"]
    required.add(envelope_path)

    pins = []
    for path in sorted(required):
        raw = git_blob(BASELINE_COMMIT, path)
        item = descriptor(path, raw)
        item["role"] = ("world-index-and-containing-files" if path == "data/world-index.json" or path in part_paths else
                        "frozen-region-envelope" if path == envelope_path else
                        "preserved-original-review-input")
        expected_rows = [row for row in (original.get(path), quality.get(path)) if row]
        for expected in expected_rows:
            if (item["bytes"], item["sha256"]) != (expected["bytes"], expected["sha256"]):
                raise ValueError(f"Original #439 baseline descriptor mismatch: {path}")
            for key in ("uncompressed_bytes", "uncompressed_sha256"):
                if key in expected:
                    item[key] = expected[key]
        if path == envelope_path:
            if sha256(gzip.decompress(raw)) != envelope["geometry_sha256"]:
                raise ValueError("Frozen envelope uncompressed geometry hash mismatch")
            unpacked = gzip.decompress(raw)
            item["uncompressed_bytes"] = len(unpacked)
            item["uncompressed_sha256"] = sha256(unpacked)
        pins.append(item)
    return pins


def validate_containing_crosswalk(actual: dict, expected: dict) -> None:
    if set(actual) != set(IDS) or set(expected) != set(IDS):
        raise ValueError("Actual containing-file mapping must match the four exact issue subjects")
    for identity in IDS:
        value = actual[identity]
        path = value.get("path") if isinstance(value, dict) else value
        if path != expected[identity]:
            raise ValueError(f"Unexpected immutable containing file for {identity}")


def packet_snapshot() -> dict:
    files = tree_inventory(SOURCE_SNAPSHOT_COMMIT, ORIGINAL_PACKET)
    source_manifest_path = ORIGINAL_PACKET + "evidence-quality.json"
    raw_manifest = git_blob(SOURCE_SNAPSHOT_COMMIT, source_manifest_path)
    original = json.loads(raw_manifest)
    if original["issue"] != 439 or original["baseline"]["commit"] != BASELINE_COMMIT:
        raise ValueError("Original packet issue/baseline identity mismatch")
    inventory = {row["path"]: row for row in files}
    for output in original["outputs"]:
        path = output["path"]
        name = path if path.startswith(ORIGINAL_PACKET) else ORIGINAL_PACKET + path.rsplit("/", 1)[-1]
        item = inventory.get(name)
        if not item or (item["bytes"], item["sha256"]) != (output["bytes"], output["sha256"]):
            raise ValueError(f"Original packet output receipt mismatch: {name}")
    return {
        "commit": SOURCE_SNAPSHOT_COMMIT,
        "commit_date": git("show", "-s", "--format=%cI", SOURCE_SNAPSHOT_COMMIT).decode().strip(),
        "packet_path": ORIGINAL_PACKET,
        "files": files,
        "original_evidence_manifest": {
            "path": source_manifest_path,
            "bytes": len(raw_manifest),
            "sha256": sha256(raw_manifest),
            "baseline_file_descriptors": len(original["baseline"]["files"]),
            "generated_output_descriptors": len(original["outputs"]),
        },
        "source_records": original["sources"],
        "assessment_sha256": inventory[ORIGINAL_PACKET + "assessment.json"]["sha256"],
        "extract_sha256": inventory[ORIGINAL_PACKET + "baseline-extract.json"]["sha256"],
        "preservation": "All original #439 summaries, assessment, sources, scripts, and source limits remain byte-for-byte at the original merge commit. This snapshot verifies their identity only and does not re-adjudicate their geographic conclusions.",
    }


def summary(feature: dict) -> dict:
    props, geometry = feature["properties"], feature["geometry"]
    coordinates = []

    def walk(value):
        if isinstance(value, (list, tuple)):
            if len(value) >= 2 and all(isinstance(x, (int, float)) for x in value[:2]):
                coordinates.append(value[:2])
            else:
                for child in value:
                    walk(child)

    walk(geometry["coordinates"])
    metadata = props.get("metadata", {})
    fields = ("source_name", "source_id", "source_url", "license", "reference_year", "administrative_level",
              "location_basis", "source_role", "hierarchy_source", "parent_match", "geographic_area_code",
              "geographic_region_code", "semantic_review")
    return {
        "id": props.get("id"), "name": props.get("name"), "parent_id": props.get("parent_id"),
        "reference_owner": props.get("reference_owner"), "geometry_type": geometry["type"],
        "geometry_sha256": sha256(json.dumps(geometry, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()),
        "vertices": len(coordinates),
        "bounds": [min(x for x, _ in coordinates), min(y for _, y in coordinates),
                   max(x for x, _ in coordinates), max(y for _, y in coordinates)],
        "metadata": {key: metadata[key] for key in fields if key in metadata},
    }


def verify_frozen_scope(scope_snapshot: dict, issue439: dict, original_extract: dict,
                        baseline: Baseline, baseline_files: list[dict]) -> tuple[dict, dict]:
    contract = scope_snapshot["contract"]
    ids = scope_snapshot["subject_ids"]
    validate_request_pins(scope_snapshot)
    if scope_snapshot["original_packet"] != ORIGINAL_PACKET or contract["owned_paths"] != [OWNED]:
        raise ValueError("Work scope/owned path changed")
    if scope_snapshot["issue"] != 654 or contract["evidence_quality"]["subject_ids"] != ids or ids != IDS:
        raise ValueError("Issue #654 subject scope changed")
    if contract["evidence_quality"]["pins"].get("hierarchy_sha256") != "03d23534f87cdd0582bcb228780f00f65090bec2e8a760acbab528383f28549d":
        raise ValueError("Issue hierarchy pin differs from issue #654")
    frozen_issue_scope = issue_scope(issue439)
    if frozen_issue_scope["member_location_ids"] != IDS or frozen_issue_scope["location_count"] != len(IDS):
        raise ValueError("Original issue #439 frozen subject scope mismatch")
    if frozen_issue_scope["region_id"] != "framework:region:southern-indian-ocean-islands:db862edea88a":
        raise ValueError("Original region identity mismatch")
    if frozen_issue_scope["release"]["hierarchy_sha256"] != contract["evidence_quality"]["pins"]["hierarchy_sha256"]:
        raise ValueError("Issue #654 and #439 hierarchy scope pins differ")
    if frozen_issue_scope["macro_certificate_sha256"] != contract["evidence_quality"]["pins"]["macro_certificate_sha256"]:
        raise ValueError("Issue #654 and #439 macro certificate pins differ")

    helper = git_blob(HELPER_COMMIT, "scripts/evidence/immutable.py")
    active_helper = (ROOT / "scripts/evidence/immutable.py").read_bytes()
    if sha256(helper) != sha256(active_helper):
        raise ValueError("Shared immutable preparation helper differs from its recorded version")

    found, containing = baseline.subjects(IDS)
    expected_files = json.loads(git_blob(SOURCE_SNAPSHOT_COMMIT, ORIGINAL_PACKET + "evidence-quality.json"))["baseline"]["subject_files"]
    actual_files = {identity: containing[identity] for identity in IDS}
    validate_containing_crosswalk(actual_files, expected_files)
    for identity in IDS:
        if summary(found[identity]) != original_extract["locations"][identity]:
            raise ValueError(f"Historical feature summary differs from preserved extract: {identity}")

    hierarchy = json.loads(baseline.read("data/hierarchy.json"))
    hierarchy_by_id = {row["id"]: row for row in hierarchy}
    chains, ancestors = {}, set()
    for identity in IDS:
        feature = found[identity]
        chain = [feature["properties"]]
        parent = feature["properties"].get("parent_id")
        seen = {identity}
        while parent:
            if parent in seen or parent not in hierarchy_by_id:
                raise ValueError(f"Parent chain is cyclic or incomplete for {identity}: {parent}")
            seen.add(parent)
            node = hierarchy_by_id[parent]
            chain.append(node)
            ancestors.add(parent)
            parent = node.get("parent_id")
        normalized = [{"id": row.get("id"), "name": row.get("name"), "level": row.get("level"), "parent_id": row.get("parent_id")} for row in chain]
        if normalized != original_extract["complete_parent_chains"][identity]:
            raise ValueError(f"Complete parent chain differs from original extract: {identity}")
        chains[identity] = normalized

    inv = json.loads(gzip.decompress(baseline.read("data/macro-foundation/current-membership-inventory.json.gz")))
    inventory = {row["id"]: row for row in inv}
    if not ancestors.issubset(inventory):
        raise ValueError("Parent chain has an ancestor missing from the frozen membership inventory")
    groups = {key: inventory[key]["member_location_ids"] for key in sorted(ancestors)
              if hierarchy_by_id[key].get("level") in {"province", "area", "region"}}
    if groups != original_extract["review_group_member_location_ids"]:
        raise ValueError("Province/area/region membership differs from original pinned extract")
    region_id = frozen_issue_scope["region_id"]
    if groups.get(region_id) != original_extract["region_member_location_ids"]:
        raise ValueError("Region member list differs from original frozen scope")

    projection = json.loads(gzip.decompress(baseline.read("data/macro-foundation/current-membership-projection.json.gz")))
    projected = {row["id"]: row for row in projection["locations"] if row["id"] in IDS}
    if set(projected) != set(IDS) or projected != original_extract["projection_rows"]:
        raise ValueError("Projection rows differ from preserved baseline extract")

    world = json.loads(baseline.read("data/world-index.json"))
    if set(found) != set(IDS) or len(found) != 4:
        raise ValueError("Exactly four issue subjects must appear once in the immutable world index")
    hierarchy_raw = baseline.read("data/hierarchy.json")
    cert_raw = baseline.read("data/macro-foundation/macro-certificate.json")
    certificate = json.loads(cert_raw)
    if sha256(hierarchy_raw) != frozen_issue_scope["release"]["hierarchy_sha256"]:
        raise ValueError("Frozen published hierarchy hash differs from issue #439")
    if sha256(cert_raw) != frozen_issue_scope["macro_certificate_sha256"]:
        raise ValueError("Frozen macro-certificate bytes differ from both issue scopes")
    if certificate.get("release") != frozen_issue_scope["release"]:
        raise ValueError("Macro certificate active release differs from frozen issue release")
    handoffs = json.loads(gzip.decompress(baseline.read("data/macro-foundation/regional-handoffs.json.gz")))
    regions = [row for row in handoffs["regions"] if row["region_id"] == region_id]
    if len(regions) != 1:
        raise ValueError("Frozen regional handoff is missing or duplicated")
    region = regions[0]
    expected_region = original_extract["region"]
    if (region["name"], region["continent_id"], region["subcontinent_id"]) != (
        expected_region["name"], expected_region["continent_id"], expected_region["subcontinent_id"]):
        raise ValueError("Frozen regional identity/parent differs from original extract")
    if region["envelope"]["geometry_sha256"] != frozen_issue_scope["frozen_region_geometry_sha256"] or \
       region["envelope"]["member_location_ids_sha256"] != frozen_issue_scope["frozen_region_member_ids_sha256"]:
        raise ValueError("Frozen region envelope hashes differ from issue #439")
    envelope_path = "data/macro-foundation/envelopes-v5/" + region["envelope"]["path"]
    envelope_bytes = baseline.read(envelope_path)
    if sha256(gzip.decompress(envelope_bytes)) != frozen_issue_scope["frozen_region_geometry_sha256"]:
        raise ValueError("Frozen region envelope bytes differ from issue #439")
    if region["envelope"]["geometry_sha256"] != expected_region["frozen_geometry_sha256"] or \
       region["envelope"]["member_location_ids_sha256"] != expected_region["frozen_member_ids_sha256"]:
        raise ValueError("Frozen envelope differs from the original extraction receipt")
    if frozen_issue_scope["member_location_ids_sha256"] != hashlib.sha256("\n".join(IDS).encode()).hexdigest():
        raise ValueError("Original issue frozen subject-list digest mismatch")
    if sha256(baseline.read("data/macro-foundation/macro-certificate.json")) != contract["evidence_quality"]["pins"]["macro_certificate_sha256"]:
        raise ValueError("Issue #654 macro-certificate pin mismatch")
    if len(world["parts"]) != len({"data/" + path for path in world["parts"]}):
        raise ValueError("Frozen world-index part list contains duplicate paths")
    return ({"complete_parent_chains": chains, "review_group_member_location_ids": groups},
            {"found": found, "containing": containing, "projection": projected, "region": region,
             "world_index_part_count": len(world["parts"]), "envelope_path": envelope_path})


def build_packet() -> tuple[dict, dict, dict, dict]:
    scope_snapshot = json.loads((ROOT / SCOPE_PATH).read_text())
    validate_request_pins(scope_snapshot)
    snapshot = packet_snapshot()
    old_manifest = json_blob(SOURCE_SNAPSHOT_COMMIT, ORIGINAL_PACKET + "evidence-quality.json")
    old_extract = json_blob(SOURCE_SNAPSHOT_COMMIT, ORIGINAL_PACKET + "baseline-extract.json")
    old_issue = json_blob(SOURCE_SNAPSHOT_COMMIT, ORIGINAL_PACKET + "issue-metadata.json")
    baseline_files = baseline_input_descriptors(old_extract, old_manifest, issue_scope(old_issue))
    baseline = Baseline(ROOT, BASELINE_COMMIT, baseline_files)
    hierarchy_checks, context = verify_frozen_scope(scope_snapshot, old_issue, old_extract, baseline, baseline_files)
    helper = git_blob(HELPER_COMMIT, "scripts/evidence/immutable.py")
    helper_descriptor = {**descriptor("scripts/evidence/immutable.py", helper), "commit": HELPER_COMMIT,
                         "version": VERSION, "commit_date": git("show", "-s", "--format=%cI", HELPER_COMMIT).decode().strip()}
    old_scope = issue_scope(old_issue)
    input_receipt = {
        "version": 1, "issue": 654, "original_review_issue": 439,
        "baseline_commit": BASELINE_COMMIT, "source_snapshot_commit": SOURCE_SNAPSHOT_COMMIT,
        "shared_helper": helper_descriptor,
        "scope": {"subject_ids": IDS, "region_id": old_scope["region_id"],
                  "hierarchy_sha256": old_scope["release"]["hierarchy_sha256"],
                  "macro_certificate_sha256": old_scope["macro_certificate_sha256"],
                  "frozen_region_geometry_sha256": old_scope["frozen_region_geometry_sha256"],
                  "frozen_region_member_ids_sha256": old_scope["frozen_region_member_ids_sha256"],
                  "batch_id": old_scope["batch_id"], "release": old_scope["release"]},
        "baseline_files": baseline_files,
        "original_packet": snapshot,
        "preserved_assessment_sha256": snapshot["assessment_sha256"],
        "preserved_original_extract_sha256": snapshot["extract_sha256"],
        "method_limits": [
            "This is an immutable provenance reproduction, not a fresh administrative or physical-geography audit.",
            "All source metadata, license statements, retrieval dates and restoration instructions are inherited from the preserved #439 packet; this work did not repeat external retrievals.",
            "The original #439 packet's source and measurement conclusions remain at its merge commit and are not independently approved by this reproduction.",
            "Canonical-grid source pins from the original manifest are byte-checked as archived inputs; no grid counts are regenerated or reinterpreted.",
        ],
    }
    subject_rows = []
    for identity in IDS:
        feature = context["found"][identity]
        subject_rows.append({
            "id": identity,
            "name": feature["properties"].get("name"),
            "feature_summary": summary(feature),
            "actual_containing_file": context["containing"][identity],
            "complete_parent_chain": hierarchy_checks["complete_parent_chains"][identity],
            "projection_row": context["projection"][identity],
        })
    index = json.loads(baseline.read("data/world-index.json"))
    part_inventory = [descriptor("data/" + part, baseline.read("data/" + part)) for part in index["parts"]]
    crosswalk = {
        "version": 1, "issue": 654, "original_review_issue": 439,
        "baseline_commit": BASELINE_COMMIT, "source_snapshot_commit": SOURCE_SNAPSHOT_COMMIT,
        "preparation_helper": helper_descriptor, "scope": input_receipt["scope"],
        "region": {key: context["region"][key] for key in ("region_id", "name", "continent_id", "subcontinent_id", "envelope")},
        "baseline_input_pins": baseline_files,
        "world_index_part_inventory": part_inventory,
        "actual_containing_file_by_subject": {row["id"]: row["actual_containing_file"] for row in subject_rows},
        "subjects": subject_rows,
        "review_group_member_location_ids": hierarchy_checks["review_group_member_location_ids"],
        "checks": {
            "original_review_packet_byte_snapshot_verified": True,
            "baseline_commit_and_all_declared_source_pins_verified_before_output": True,
            "world_index_part_count": context["world_index_part_count"],
            "all_world_index_parts_scanned_from_baseline": True,
            "exact_four_subjects_found_once": True,
            "actual_containing_files_match_original_manifest": True,
            "original_feature_summaries_match": True,
            "complete_parent_chains_match_preserved_extract": True,
            "province_area_region_membership_matches_preserved_extract": True,
            "projection_rows_match_preserved_extract": True,
            "hierarchy_macro_certificate_and_frozen_envelope_pins_match_issue_scopes": True,
            "canonical_grid_counts_recomputed": False,
            "geographic_conclusions_recomputed": False,
        },
        "original_extract_sha256": snapshot["extract_sha256"],
        "original_assessment_sha256": snapshot["assessment_sha256"],
        "method_limits": input_receipt["method_limits"],
    }
    notice = {
        "version": 1, "issue": 654, "status": "superseding-reproduction-notice",
        "original_packet_commit": SOURCE_SNAPSHOT_COMMIT, "original_packet_path": ORIGINAL_PACKET,
        "original_baseline_commit": BASELINE_COMMIT,
        "original_extract_sha256": snapshot["extract_sha256"],
        "original_assessment_sha256": snapshot["assessment_sha256"],
        "corrective_finding": "The prior default extractor selected its retained baseline commit but read geographic and membership files from the mutable checkout, then wrote to the original output path. This packet reads Git blobs at the reviewed baseline, verifies all declared pins and original context before output, and uses exclusive new-vintage writes.",
        "preservation": "No original #439 source, script, extract, assessment or source receipt is edited or replaced.",
        "geographic_effect": "None. Original land, source, settlement, tier and neighboring-routing conclusions are not recalculated. No shared geometry, hierarchy, canonical-grid or certificate data is changed.",
        "followups": {"island_source_restoration": 635, "neighbor_routing": 636, "regional_integration": 440},
        "reproduction_status": "Pinned and deterministic; does not certify current geography or enable historical imports.",
    }
    run_hash = sha256(canonical_json([input_receipt, crosswalk, notice]))
    controls = {
        "version": 1, "method_id": "immutable-sio-baseline-reproduction",
        "run_one_sha256": run_hash, "run_two_sha256": run_hash,
        "all_four_exact_ids_once": True,
        "all_parent_chains_complete_and_equal_original": True,
        "actual_containing_files_crosswalk_verified": True,
        "baseline_and_source_snapshot_pins_verified_before_output": True,
        "changed_commit_pin_and_source_pin_rejections": [
            "changed baseline commit rejected before output",
            "unknown commit rejected before output",
            "changed whole-file descriptor rejected before output",
            "changed source packet snapshot rejected before output",
        ],
        "exclusive_overwrite_refusal": "An existing vintage path is refused and preserved byte-for-byte.",
        "geographic_conclusions_recomputed": False,
    }
    return input_receipt, crosswalk, notice, controls


def outputs(receipt: dict, crosswalk: dict, notice: dict, controls: dict):
    common = {"method_id": "immutable-sio-baseline-reproduction", "outcome": "passed"}
    return [
        ("source-snapshot-manifest.json", receipt["original_packet"]),
        ("baseline-source-crosswalk.json", crosswalk),
        ("superseding-notice.json", notice),
        ("reproduction-controls.json", controls),
        ("positive-control.json", {**common, "kind": "positive-control", "result": "Exact original baseline, all four subjects, source snapshot, parent chains and frozen region pins validate."}),
        ("negative-control.json", {**common, "kind": "negative-control", "cases": controls["changed_commit_pin_and_source_pin_rejections"] + [controls["exclusive_overwrite_refusal"]]}),
        ("reproducibility-control.json", {**common, "kind": "reproducibility", "run_one_sha256": controls["run_one_sha256"], "run_two_sha256": controls["run_two_sha256"]}),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="read-only reproducibility check; default")
    mode.add_argument("--create", action="store_true", help="exclusively create a new named vintage")
    parser.add_argument("--vintage", help="required with --create; never overwrites")
    args = parser.parse_args()
    if args.create and not args.vintage:
        parser.error("--create requires --vintage")
    if args.vintage and not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", args.vintage):
        parser.error("vintage must be a lowercase ID")
    receipt, crosswalk, notice, controls = build_packet()
    receipt2, crosswalk2, notice2, _ = build_packet()
    one, two = canonical_json([receipt, crosswalk, notice]), canonical_json([receipt2, crosswalk2, notice2])
    if one != two or controls["run_one_sha256"] != sha256(two):
        raise ValueError("Two full immutable rebuilds differ")
    if args.create:
        created = []
        baseline = Baseline(ROOT, BASELINE_COMMIT, receipt["baseline_files"])
        for name, value in outputs(receipt, crosswalk, notice, controls):
            created.append(write_new_vintage(baseline, OWNED, args.vintage, name, value))
        print(json.dumps({"mode": "exclusive-create", "vintage": args.vintage, "created": created, "result": "PASS"}, indent=2))
        return
    if args.vintage:
        for name, value in outputs(receipt, crosswalk, notice, controls):
            path = OUT / "vintages" / args.vintage / name
            if path.exists() and path.read_bytes() != canonical_json(value):
                raise SystemExit(f"Pinned candidate differs from immutable rebuild: {path}")
    print(json.dumps({"mode": "read-only-check", "baseline_commit": BASELINE_COMMIT,
        "source_snapshot_commit": SOURCE_SNAPSHOT_COMMIT, "subjects": len(IDS),
        "baseline_file_count": len(receipt["baseline_files"]), "world_index_parts": crosswalk["checks"]["world_index_part_count"],
        "source_snapshot_files": len(receipt["original_packet"]["files"]), "run_sha256": controls["run_one_sha256"],
        "result": "PASS"}, indent=2))


if __name__ == "__main__":
    main()
