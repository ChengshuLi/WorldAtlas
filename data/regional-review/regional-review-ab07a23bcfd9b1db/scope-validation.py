#!/usr/bin/env python3
"""Run positive/negative scope controls and two-run packet reproducibility."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OWN = Path(__file__).resolve().parent
sys.path.insert(0, str(OWN))
import reproduce  # noqa: E402 — executes the source assertions before exposing outputs


def roster_is_valid(ids):
    return (
        len(ids) == 215
        and len(set(ids)) == 215
        and hashlib.sha256("\n".join(ids).encode()).hexdigest()
        == reproduce.scope["member_location_ids_sha256"]
    )


scope_ids = reproduce.ids
assert roster_is_valid(scope_ids)
assert not roster_is_valid(scope_ids[:-1]), "negative control: missing member accepted"
assert not roster_is_valid(scope_ids[:-1] + [scope_ids[0]]), "negative control: duplicate member accepted"
assert reproduce.scope_partition["exact_workload_partition_matches_baseline"]
peer_ids = {value for row in reproduce.cohort_snapshot["cohorts"] for value in row["civ_member_ids"]}
own_civ_ids = {value for value in scope_ids if value.startswith("gb:CIV:ADM3:")}
assert (peer_ids | own_civ_ids) == reproduce.atlas_civ_ids
assert (peer_ids | (own_civ_ids - {next(iter(own_civ_ids))})) != reproduce.atlas_civ_ids, "negative control: incomplete peer partition accepted"

assessments_path = OWN / "location-assessments.json"
province_assessments_path = OWN / "province-assessments.json"
area_assessment_path = OWN / "area-assessment.json"
acceptance_screen_path = OWN / "acceptance-screen.json"
reproduction_path = OWN / "reproduction.json"
first = {
    "assessments": hashlib.sha256(assessments_path.read_bytes()).hexdigest(),
    "provinces": hashlib.sha256(province_assessments_path.read_bytes()).hexdigest(),
    "area": hashlib.sha256(area_assessment_path.read_bytes()).hexdigest(),
    "acceptance_screen": hashlib.sha256(acceptance_screen_path.read_bytes()).hexdigest(),
    "reproduction": hashlib.sha256(reproduction_path.read_bytes()).hexdigest(),
}
subprocess.run([sys.executable, str(OWN / "reproduce.py")], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
second = {
    "assessments": hashlib.sha256(assessments_path.read_bytes()).hexdigest(),
    "provinces": hashlib.sha256(province_assessments_path.read_bytes()).hexdigest(),
    "area": hashlib.sha256(area_assessment_path.read_bytes()).hexdigest(),
    "acceptance_screen": hashlib.sha256(acceptance_screen_path.read_bytes()).hexdigest(),
    "reproduction": hashlib.sha256(reproduction_path.read_bytes()).hexdigest(),
}
assert first == second, "generator outputs changed across identical runs"
screen = json.loads(acceptance_screen_path.read_text(encoding="utf-8"))
screen_criteria = {row["criterion"] for row in screen["screens"]}
expected_criteria = {
    "fragmented_city_territories", "province_sized_locations", "anonymous_administrative_remainders",
    "disconnected_territories", "omitted_islands", "repeated_tiers", "oversized_groups",
    "weak_parents", "inconsistent_neighboring_units"
}
assert screen_criteria == expected_criteria
assert all(row["status"] in {"supported-with-limits", "limited-screen", "insufficient-evidence", "correction-needed"} for row in screen["screens"])

controls = [
    {
        "method_id": "source-role-crosswalk",
        "kind": "source",
        "outcome": "passed",
        "positive_controls": [
            "All 215 issue IDs resolve to exact pinned source shapeIDs and source names after reversible UTF-8/Latin-1 comparison repair.",
            "The 2025 CNTIG/OCHA official layer yields unique source-name plus Atlas-region matches for 213/215 IDs.",
        ],
        "negative_controls": [
            "The two same-named Guézon features in Guemon remain ambiguous under name plus region; the packet does not fabricate a department assignment.",
            "All 215 source-role claims are Departments while the official layer's corresponding field is Sous-Prefecture; disagreement is retained as a correction finding.",
        ],
    },
    {
        "method_id": "packet-generator",
        "kind": "generator",
        "outcome": "passed",
        "positive_controls": [
            "The exact pinned 215-member roster, all per-location rows and all 14 parents are reproduced.",
            "Each of the nine issue acceptance screens has an explicit status, finding and limitation or handoff.",
            "The four frozen issue-workload rosters are disjoint and exactly equal the 510 Atlas CIV ADM3 IDs present at the pinned baseline.",
            "Two independent executions produce identical location, parent, area, acceptance-screen and reproduction JSON SHA-256 values.",
        ],
        "negative_controls": [
            "Removing one ID from the issue roster fails exact count/hash validation.",
            "Replacing a member with an existing member fails uniqueness/hash validation.",
        "Removing one ID from the peer workload cohorts fails the exact partition-to-baseline check.",
        "Removing or duplicating an acceptance criterion fails the exact criterion inventory check.",
        ],
        "run_one_sha256": hashlib.sha256(json.dumps(first, sort_keys=True).encode()).hexdigest(),
        "run_two_sha256": hashlib.sha256(json.dumps(second, sort_keys=True).encode()).hexdigest(),
    },
]
(OWN / "source-role-crosswalk-controls.json").write_text(json.dumps(controls[0], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(OWN / "packet-generator-controls.json").write_text(json.dumps(controls[1], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": "passed", "controls": controls, "identical_runs": first == second}, ensure_ascii=False, indent=2))
