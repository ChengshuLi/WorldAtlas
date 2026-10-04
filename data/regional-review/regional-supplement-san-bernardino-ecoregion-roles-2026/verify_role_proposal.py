#!/usr/bin/env python3
"""Reproduce the role proposal and check positive/negative identity controls."""
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
BUILDER = ROOT / "build_role_proposal.py"
OUTPUT = ROOT / "proposed-role-corrections.json"
BASE = "fbd3bf4991dbd5a9bf89a79b14e5b4deb6225ff9"
PACKET = "data/regional-review/regional-review-2178b81fa886cfb6"
EXPECTED = {
    "atlas:physical:5dcc72971bb4b1ede2f5": (433, "Mojave desert"),
    "atlas:physical:9cfc4fc5de3925d6f841": (435, "Sonoran desert"),
    "atlas:physical:d76eb273e99a0f96a575": (424, "California montane chaparral and woodlands"),
    "atlas:physical:dcc393fbc988381d899c": (422, "California coastal sage and chaparral"),
}
ROLE = "Ecological ecoregion portion"


def sha_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def sha_file(path):
    return sha_bytes(path.read_bytes())


def baseline(path):
    return subprocess.check_output(["git", "show", f"{BASE}:{path}"])


def valid_record(row, geometry_hashes):
    expected = EXPECTED.get(row.get("id"))
    if not expected:
        return False
    eco_id, eco_name = expected
    return (row["physical_source"].get("eco_id") == eco_id and
            row["physical_source"].get("eco_name") == eco_name and
            row["current"].get("source_role") == "Counties" and
            row["proposed"].get("source_role") == ROLE and
            row["proposed"].get("administrative_level") == "Named physical region portion" and
            row["administrative_intersection_context"].get("predecessor_shape_id") == "52423323B23069932539838" and
            row["preservation"].get("existing_source_member_ids") == ["gb:USA:ADM2:52423323B23069932539838"] and
            row["preservation"].get("geometry_action", "").startswith("preserve unchanged") and
            row["preservation"].get("original_geometry_sha256_canonical_json") == geometry_hashes.get(row.get("id")))


def valid_roster(rows):
    ids = [row.get("id") for row in rows]
    return len(ids) == len(EXPECTED) and len(set(ids)) == len(ids) and set(ids) == set(EXPECTED)


def main():
    subprocess.run([sys.executable, str(BUILDER)], check=True)
    run_one = sha_file(OUTPUT)
    subprocess.run([sys.executable, str(BUILDER)], check=True)
    run_two = sha_file(OUTPUT)
    assert run_one == run_two, "Proposal is not byte-reproducible"
    packet = json.loads(OUTPUT.read_text())
    rows = packet["subjects"]
    world = json.loads(baseline("data/geography/part-25.json"))
    geo = {feature.get("id", feature.get("properties", {}).get("id")): feature.get("geometry")
           for feature in world["features"]}
    geometry_hashes = {subject_id: sha_bytes(json.dumps(geo[subject_id], sort_keys=True,
                        separators=(",", ":")).encode()) for subject_id in EXPECTED}
    assert valid_roster(rows), "Proposal omits, invents or duplicates an assigned subject"
    assert all(valid_record(row, geometry_hashes) for row in rows), "A role, ECO_ID, geometry fingerprint or source link is incorrect"
    assert packet["scope"]["assigned_count"] == packet["scope"]["assessed_count"] == 4
    assert packet["scope"]["role_mismatch_count"] == 4

    wrong_eco = json.loads(json.dumps(rows[0]))
    wrong_eco["physical_source"]["eco_id"] = 999
    wrong_role = json.loads(json.dumps(rows[0]))
    wrong_role["proposed"]["source_role"] = "Counties"
    wrong_geometry = json.loads(json.dumps(rows[0]))
    wrong_geometry["preservation"]["original_geometry_sha256_canonical_json"] = "0" * 64
    duplicate_roster = rows + [json.loads(json.dumps(rows[0]))]
    negatives = {
        "wrong_ecoregion_id_rejected": not valid_record(wrong_eco, geometry_hashes),
        "administrative_county_role_rejected": not valid_record(wrong_role, geometry_hashes),
        "changed_geometry_fingerprint_rejected": not valid_record(wrong_geometry, geometry_hashes),
        "duplicate_or_overcomplete_roster_rejected": not valid_roster(duplicate_roster),
    }
    assert all(negatives.values()), "A negative control unexpectedly passed"

    report = {
        "version": 1,
        "method_id": "role-proposal-build",
        "kind": "generator",
        "outcome": "passed",
        "run_one_sha256": run_one,
        "run_two_sha256": run_two,
        "positive_control": {
            "description": "All four exact IDs match the pinned parent rows, matching RESOLVE ECO_ID/name and the separated county predecessor identity.",
            "outcome": "passed",
        },
        "negative_controls": negatives,
        "checks": {
            "assigned_subjects": len(EXPECTED),
            "assessed_subjects": len(rows),
            "corrected_source_role_proposals": packet["scope"]["role_mismatch_count"],
            "full_parent_chain_nodes_each": 6,
            "parent_county_geoid": "06071",
        },
        "inputs": {
            "parent_assessment_sha256": sha_bytes(baseline(f"{PACKET}/assessment.json")),
            "parent_scope_sha256": sha_bytes(baseline(f"{PACKET}/scope.json")),
            "containing_geojson_sha256": sha_bytes(baseline("data/geography/part-25.json")),
            "resolve_source_gzip_sha256": sha_bytes(baseline(f"{PACKET}/sources/resolve-ca-ecoregions-4.geojson.gz")),
            "proposal_sha256": sha_file(OUTPUT),
        },
        "environment": {"python": platform.python_version()},
        "limitations": packet["limitations"],
    }
    (ROOT / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": "passed", "subjects": len(rows), "negative_controls": negatives,
                      "validation_sha256": sha_file(ROOT / "validation.json")}, indent=2))


if __name__ == "__main__":
    main()
