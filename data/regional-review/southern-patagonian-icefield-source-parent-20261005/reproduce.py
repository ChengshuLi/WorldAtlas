#!/usr/bin/env python3
"""Reproduce the exact issue-pinned roster, parent, and Natural Earth candidate checks."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKET = Path(__file__).resolve().parent
BASELINE = "27be77596f23304de6a720735538427e6d23e242"
SUBJECT = "country-SPI"
PINS = {
    "baseline-world-index": ("data/world-index.json", "a62d4a74f0f969e228dfcdeb2797bb689ce9836c2498cadd31ed622ad2c38c03"),
    "baseline-hierarchy": ("data/hierarchy.json", "568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b"),
    "baseline-administrative-sources": ("data/administrative-sources.json", "ed0051d2956271c72f8917e7da0c6f53e5dfb595bee5920cac489a65a747d633"),
    "baseline-macro-publication": ("data/validation/macro-publication-v5.json", "aae3967fde4f5bf92b3cb0b42c490c6c6a5921c7421dcdc9533f242afbd6a674"),
    "baseline-icefield-subject": ("data/geography/part-28.json", "2aab2f36aeeb651ee8e6cc656e9541ad14e2ced2ea8160e8700ad4dc950c379d"),
}
CANDIDATE = PACKET / "sources/ne_10m_admin_0_map_units-v5.1.0.geojson"
EXPECTED_CANDIDATE_SHA = "57da82be755f4afccd8f3b14251bb2752f5df1395f47d2d86f817470c4a48862"
EXPECTED_LICENSE_PAGE_SHA = "22c3ffc04b4ccae8e99129fa6c5a546a2709c61af54d6304682da7fa1884a291"
EXPECTED_ORIGINAL_GEOMETRY_SHA = "285e80dadd61de9903bf3070b7a594e4009034d8b67adc304111328da53468ce"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical_sha(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha(raw)


def git_file(commit, path):
    return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{commit}:{path}"])


def features(collection, subject):
    return [f for f in collection.get("features", []) if f.get("properties", {}).get("id") == subject]


def exact_one(rows, predicate):
    found = [row for row in rows if predicate(row)]
    if len(found) != 1:
        raise ValueError(f"expected exactly one source row, found {len(found)}")
    return found[0]


def rejected_control(rows, predicate):
    try:
        exact_one(rows, predicate)
    except ValueError:
        return True
    return False


def main():
    checks = []
    baseline_data = {}
    for name, (path, expected) in PINS.items():
        raw = git_file(BASELINE, path)
        observed = sha(raw)
        checks.append({"id": f"pin:{name}", "passed": observed == expected, "expected_sha256": expected, "observed_sha256": observed, "bytes": len(raw)})
        baseline_data[path] = json.loads(raw)

    issue_subjects = [SUBJECT]
    subject_hash = sha(json.dumps(sorted(issue_subjects), separators=(",", ":")).encode())
    checks.append({"id": "issue:exact-subject-roster", "passed": subject_hash == "49549fc841215235fa4fb67326624f100a76a138fd2052cb73236c5b752b1de5", "subjects": issue_subjects, "subjects_sha256": subject_hash})

    base_collection = baseline_data["data/geography/part-28.json"]
    base_subjects = features(base_collection, SUBJECT)
    checks.append({"id": "baseline:subject-occurrence", "passed": len(base_subjects) == 1, "count": len(base_subjects)})
    if len(base_subjects) != 1:
        raise SystemExit("Pinned subject must resolve exactly once")
    base_feature = base_subjects[0]
    base_properties = base_feature["properties"]
    parent_id = base_properties["parent_id"]
    base_hierarchy = json.loads(git_file(BASELINE, "data/hierarchy.json"))
    base_parents = [entry for entry in base_hierarchy if entry.get("id") == parent_id]
    checks.append({"id": "baseline:parent-occurrence", "passed": len(base_parents) == 1, "count": len(base_parents), "parent_id": parent_id})
    if len(base_parents) != 1:
        raise SystemExit("Pinned parent must resolve exactly once")
    parent = base_parents[0]
    child_count = parent.get("metadata", {}).get("child_count")
    checks.append({"id": "baseline:one-child-parent", "passed": child_count == 1, "child_count": child_count, "level": parent.get("level"), "kind": parent.get("metadata", {}).get("kind"), "semantic_action": parent.get("metadata", {}).get("semantic_review", {}).get("action")})

    candidate_raw = CANDIDATE.read_bytes()
    candidate_hash = sha(candidate_raw)
    checks.append({"id": "candidate:whole-file-sha256", "passed": candidate_hash == EXPECTED_CANDIDATE_SHA, "expected_sha256": EXPECTED_CANDIDATE_SHA, "observed_sha256": candidate_hash, "bytes": len(candidate_raw)})
    source_inventory = json.loads((PACKET / "source-inventory.json").read_bytes())
    license_records = [s for s in source_inventory["sources"] if s.get("source_id") == "natural-earth-public-domain-terms"]
    checks.append({"id": "candidate:license-terms-retrieval-pin", "passed": len(license_records) == 1 and license_records[0].get("sha256") == EXPECTED_LICENSE_PAGE_SHA and license_records[0].get("retained") is False, "expected_sha256": EXPECTED_LICENSE_PAGE_SHA, "source_records": len(license_records)})
    candidate_collection = json.loads(candidate_raw)
    candidate_rows = [f for f in candidate_collection.get("features", []) if f.get("properties", {}).get("ADM0_A3") == "SPI"]
    checks.append({"id": "candidate:SPI-row-occurrence", "passed": len(candidate_rows) == 1, "count": len(candidate_rows)})
    if len(candidate_rows) != 1:
        raise SystemExit("Dated source candidate must contain exactly one ADM0_A3 SPI row")
    candidate = candidate_rows[0]
    candidate_properties = candidate["properties"]
    candidate_geometry_hash = canonical_sha(candidate["geometry"])
    original_hash = base_properties.get("metadata", {}).get("original_geometry_sha256")
    candidate_matches_original = original_hash == candidate_geometry_hash
    checks.append({"id": "candidate:original-geometry-hash-match", "passed": not candidate_matches_original, "recorded_original_geometry_sha256": original_hash, "candidate_geometry_sha256": candidate_geometry_hash, "match": candidate_matches_original})

    current_part = json.loads((ROOT / "data/geography/part-28.json").read_bytes())
    current_subjects = features(current_part, SUBJECT)
    checks.append({"id": "current:stable-subject-id", "passed": len(current_subjects) == 1, "count": len(current_subjects)})
    current_parent_id = current_subjects[0]["properties"].get("parent_id") if current_subjects else None
    checks.append({"id": "current:stable-parent-reference", "passed": current_parent_id == parent_id, "baseline_parent_id": parent_id, "current_parent_id": current_parent_id})

    controls = []
    for name, rows, predicate in [
        ("duplicate-baseline-subject", base_subjects + [base_subjects[0]], lambda f: f.get("properties", {}).get("id") == SUBJECT),
        ("missing-baseline-subject", [], lambda f: f.get("properties", {}).get("id") == SUBJECT),
        ("duplicate-Natural-Earth-SPI-row", candidate_rows + [candidate_rows[0]], lambda f: f.get("properties", {}).get("ADM0_A3") == "SPI"),
        ("missing-Natural-Earth-SPI-row", [], lambda f: f.get("properties", {}).get("ADM0_A3") == "SPI"),
    ]:
        rejected = rejected_control(rows, predicate)
        controls.append({"id": name, "expected": "reject zero or duplicate identities", "rejected": rejected})
        checks.append({"id": f"negative-control:{name}", "passed": rejected})
    if not all(check["passed"] for check in checks):
        raise SystemExit("One or more baseline, roster, source, or stability checks failed")

    output = {
        "version": 1,
        "baseline_commit": BASELINE,
        "exact_subject_ids": issue_subjects,
        "subject_ids_sha256": subject_hash,
        "metrics": [
            {"id": "scope_subject_count", "value": len(issue_subjects), "unit": "features", "input_sha256": PINS["baseline-icefield-subject"][1], "evaluation_commit": BASELINE, "vintage": "baseline"},
            {"id": "province_parent_child_count", "value": child_count, "unit": "children", "input_sha256": PINS["baseline-hierarchy"][1], "evaluation_commit": BASELINE, "vintage": "baseline"},
        ],
        "candidate": {
            "release_commit": "117488dc884bad03366ff727eca013e434615127",
            "properties": {key: candidate_properties.get(key) for key in ["NAME", "ADM0_A3", "NE_ID", "TYPE", "NOTE_ADM0", "NOTE_BRK", "ISO_A3"]},
            "geometry_sha256": candidate_geometry_hash,
            "exterior_ring_coordinates": len(candidate["geometry"]["coordinates"][0]),
            "recorded_original_geometry_sha256": original_hash,
            "matches_recorded_original_geometry": candidate_matches_original,
        },
        "baseline_subject": {
            "id": SUBJECT,
            "name": base_properties.get("name"),
            "parent_id": parent_id,
            "source_name": base_properties.get("metadata", {}).get("source_name"),
            "source_id": base_properties.get("metadata", {}).get("source_id"),
            "reference_year": base_properties.get("metadata", {}).get("reference_year"),
            "recorded_original_geometry_sha256": original_hash,
            "display_geometry_sha256": canonical_sha(base_feature.get("geometry")),
            "display_exterior_ring_coordinates": len(base_feature["geometry"]["coordinates"][0]),
        },
        "parent": {"id": parent_id, "name": parent.get("name"), "level": parent.get("level"), "kind": parent.get("metadata", {}).get("kind"), "child_count": child_count, "semantic_action": parent.get("metadata", {}).get("semantic_review", {}).get("action"), "parent_id": parent.get("parent_id")},
        "checks": checks,
        "negative_controls": controls,
        "limits": [
            "The Natural Earth 5.1.0 SPI row is a dated identity and map-unit candidate but does not match the Atlas-recorded original geometry hash.",
            "The official DGA IPG2022 shape package and complete current IANIGLA regional vector set were not retrieved or crosswalked.",
            "The latest specific Chilean Section A/Section B demarcation statement found was dated 2018; current completion status is unknown.",
            "No legal/administrative parent or sovereign owner is inferred from a glacier outline or inventory.",
        ],
    }
    (PACKET / "reproduction-results.json").write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "passed", "results_path": str((PACKET / "reproduction-results.json").relative_to(ROOT)), "check_count": len(checks), "negative_control_count": len(controls), "failed": 0, "subject_ids": issue_subjects, "candidate_geometry_matches_original": candidate_matches_original, "parent_level": parent.get("level"), "parent_child_count": child_count}, indent=2))


if __name__ == "__main__":
    main()
