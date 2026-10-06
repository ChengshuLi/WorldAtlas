#!/usr/bin/env python3
"""Reproduce the Turkey packet-vs-region pin correction from immutable inputs."""
from pathlib import Path
import gzip
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
PR_COMMIT = "b7aab8b8d353eb3510cf7323da7bc2dcde10147b"
PR_HEAD = "81b3ddee2043a9b7e539c3d85d8a157dfad3f7ee"
EXPECTED_PACKET_HASH = "50597f85cd48e244f864325a474f44013c1212375e977196cfd53812edba9d14"
EXPECTED_REGION_HASH = "c192f338b815c029ea0c8338cbf153686a11bfd5e102d733272417f290ae85eb"
EXPECTED_MANIFEST_HASH = "dfcd4696b6c63deeee2cc1e693537b86afccc9ef3ae873dd2390b143a78e906a"
EXPECTED_FILES = {
    "original-acceptance-review": "data/regional-review/regional-review-96597060edbd6143/acceptance-review.json",
    "original-scope": "data/regional-review/regional-review-96597060edbd6143/scope.json",
    "original-assessments": "data/regional-review/regional-review-96597060edbd6143/district-assessments.json",
    "original-evidence-manifest": "data/regional-review/regional-review-96597060edbd6143/evidence-quality.json",
    "atlas-subjects-part24": "data/geography/part-24.json",
    "macro-region-handoffs": "data/macro-foundation/regional-handoffs.json.gz",
}
EXPECTED_BASELINE = "cbb829672d18801e4310c30896a7ddb13a79b451"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


snapshot = load(ROOT / "sources/issue-snapshot.json")
body = snapshot["body"]
assert digest(body.encode("utf-8")) == snapshot["body_sha256"]
contract_match = re.search(r"<!-- worldatlas-work:v1\s*(\{.*?\})\s*-->", body, re.S)
assert contract_match
contract = json.loads(contract_match.group(1))
assert contract == snapshot["work_spec"]
assert contract["owned_paths"] == ["data/regional-review/turkey-229-acceptance-pin-correction-863/"]
assert contract["max_prs"] == 1 and contract["mode"] == "geography"
quality = contract["evidence_quality"]
ids = sorted(quality["subject_ids"])
assert len(ids) == 229 and len(set(ids)) == 229
assert snapshot["issue"] == 1088 and snapshot["state"] == "open"

scope_path = REPO / EXPECTED_FILES["original-scope"]
acceptance_path = REPO / EXPECTED_FILES["original-acceptance-review"]
assessment_path = REPO / EXPECTED_FILES["original-assessments"]
old_manifest_path = REPO / EXPECTED_FILES["original-evidence-manifest"]
scope = load(scope_path)
acceptance = load(acceptance_path)
assessment = load(assessment_path)
old_manifest = load(old_manifest_path)
actual_hashes = {key: file_sha(REPO / path) for key, path in EXPECTED_FILES.items()}
for key, expected in quality["pins"].items():
    assert actual_hashes[key] == expected, f"Pinned input changed: {key}"

assert scope["region_id"] == "atlas:macro-foundation:region:anatolia-eastern-mediterranean"
assert scope["location_count"] == 229
assert scope["member_location_ids"] == ids
packet_hash = digest("\n".join(ids).encode("utf-8"))
assert packet_hash == EXPECTED_PACKET_HASH == scope["member_location_ids_sha256"]
assert assessment["scope"]["subject_ids_sha256"] == packet_hash
assert assessment["scope"]["subject_count"] == len(ids)

# The older evidence-quality manifest uses a different, explicitly sorted JSON-array hash.
manifest_ids = sorted(old_manifest["subject_ids"])
manifest_hash = digest(json.dumps(manifest_ids, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
assert manifest_ids == ids
assert manifest_hash == EXPECTED_MANIFEST_HASH == old_manifest["subject_ids_sha256"]

assert acceptance["scope"]["path"] == EXPECTED_FILES["original-scope"]
assert acceptance["scope"]["sha256"] == actual_hashes["original-scope"]
wrong_acceptance_hash = acceptance["scope"]["member_ids_sha256"]
assert wrong_acceptance_hash == EXPECTED_REGION_HASH

with gzip.open(REPO / EXPECTED_FILES["macro-region-handoffs"], "rt", encoding="utf-8") as stream:
    macro = json.load(stream)
regions = [row for row in macro["regions"] if row.get("envelope", {}).get("id") == scope["region_id"]]
assert len(regions) == 1
region = regions[0]["envelope"]
assert region["locations"] == 939 and region["member_location_ids_sha256"] == EXPECTED_REGION_HASH
assert scope["frozen_region_member_ids_sha256"] == region["member_location_ids_sha256"]
assert macro["release"]["version"] == 6

# Verify all issue subjects are actually present once in the pinned containing file.
part24 = load(REPO / EXPECTED_FILES["atlas-subjects-part24"])
feature_ids = [feature.get("id", feature.get("properties", {}).get("id")) for feature in part24["features"]]
assert all(feature_ids.count(subject) == 1 for subject in ids)

rows = assessment["findings"]
assert len(rows) == 229 and {row["id"] for row in rows} == set(ids)
assert all(row["classification"] == "insufficient-evidence" for row in rows)
assert assessment["counts"]["rows_insufficient_evidence"] == 229

positive = {
    "version": 1,
    "method_id": "packet-region-pin-comparison",
    "kind": "positive-control",
    "outcome": "passed",
    "control": "The exact 229 sorted packet IDs, newline-joined without a trailing newline, reproduce the packet digest.",
    "packet_subject_count": len(ids),
    "computed_packet_hash": packet_hash,
    "scope_member_location_ids_sha256": scope["member_location_ids_sha256"],
    "assessment_subject_ids_sha256": assessment["scope"]["subject_ids_sha256"],
    "all_three_packet_values_equal": True,
}
negative = {
    "version": 1,
    "method_id": "packet-region-pin-comparison",
    "kind": "negative-control",
    "outcome": "passed",
    "control": "Substituting the frozen macro-region digest for the 229-member packet digest is rejected.",
    "candidate_packet_hash": wrong_acceptance_hash,
    "expected_packet_hash": packet_hash,
    "candidate_equals_packet": wrong_acceptance_hash == packet_hash,
    "candidate_matches_frozen_region": wrong_acceptance_hash == region["member_location_ids_sha256"],
    "frozen_region_id": region["id"],
    "frozen_region_member_count": region["locations"],
    "substitution_rejected": wrong_acceptance_hash != packet_hash and wrong_acceptance_hash == region["member_location_ids_sha256"],
}
assert positive["all_three_packet_values_equal"]
assert negative["substitution_rejected"]

record = {
    "version": 1,
    "issue": 1088,
    "recorded_at_utc": snapshot["retrieved_at_utc"],
    "issue_body_sha256": snapshot["body_sha256"],
    "baseline_commit": EXPECTED_BASELINE,
    "originating_pr": {
        "number": 863,
        "url": "https://github.com/ChengshuLi/WorldAtlas/pull/863",
        "head_sha": PR_HEAD,
        "merge_commit": PR_COMMIT,
        "merged_at": "2026-10-05T04:34:55Z",
    },
    "inputs": [
        {"pin": key, "path": EXPECTED_FILES[key], "sha256": actual_hashes[key]}
        for key in EXPECTED_FILES
    ],
    "packet_scope": {
        "path": EXPECTED_FILES["original-scope"],
        "location_count": len(ids),
        "member_location_ids_sha256": packet_hash,
        "hash_method": "SHA-256 of UTF-8 member IDs sorted lexically and joined with LF, with no final LF.",
        "matching_assessment_path": EXPECTED_FILES["original-assessments"],
        "matching_assessment_pointer": "/scope/subject_ids_sha256",
    },
    "prior_evidence_manifest_subject_digest": {
        "path": EXPECTED_FILES["original-evidence-manifest"],
        "subject_ids_sha256": manifest_hash,
        "hash_method": "SHA-256 of the UTF-8 compact JSON array of sorted IDs; a different, unchanged field and canonicalization.",
    },
    "frozen_macro_region": {
        "id": region["id"],
        "name": region["name"],
        "location_count": region["locations"],
        "member_location_ids_sha256": region["member_location_ids_sha256"],
        "envelope_geometry_sha256": region["geometry_sha256"],
        "handoffs_path": EXPECTED_FILES["macro-region-handoffs"],
        "handoffs_file_sha256": actual_hashes["macro-region-handoffs"],
        "release": macro["release"],
    },
    "prior_acceptance_summary": {
        "path": EXPECTED_FILES["original-acceptance-review"],
        "sha256": actual_hashes["original-acceptance-review"],
        "field": "/scope/member_ids_sha256",
        "value": wrong_acceptance_hash,
        "error": "This field used the frozen 939-member regional digest where a 229-member packet digest was intended.",
    },
    "controls": {
        "positive": "validation/positive-control.json",
        "negative": "validation/negative-control.json",
    },
    "preservation": {
        "original_packet_files_modified": False,
        "original_assessment_rows": len(rows),
        "insufficient_evidence_rows": assessment["counts"]["rows_insufficient_evidence"],
        "all_original_rows_remain_insufficient_evidence": True,
        "geography_or_legal_crosswalk_reviewed": False,
        "regional_approval_or_import_authority_created": False,
    },
    "disposition": "Corrective provenance record only. It separates three distinct digest conventions and does not repin IDs, rewrite the historical acceptance summary, validate legal boundaries, or certify geography.",
}

write_json("corrective-record.json", record)
write_json("validation/positive-control.json", positive)
write_json("validation/negative-control.json", negative)
print(json.dumps({
    "issue": 1088,
    "baseline_commit": EXPECTED_BASELINE,
    "packet_subjects": len(ids),
    "packet_scope_hash": packet_hash,
    "evidence_manifest_json_array_hash": manifest_hash,
    "frozen_region_members": region["locations"],
    "frozen_region_hash": region["member_location_ids_sha256"],
    "assessments_preserved": len(rows),
    "positive_control": positive["outcome"],
    "negative_control": negative["outcome"],
}, indent=2))
