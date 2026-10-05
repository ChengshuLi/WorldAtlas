#!/usr/bin/env python3
"""Verify the additive #474 synthesis against its exact issue scope and prior evidence."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
scope = json.loads((ROOT / "issue-scope.json").read_text())
assessment = json.loads((ROOT / "assessment.json").read_text())
review = json.loads((ROOT / "completion-review.json").read_text())
index = json.loads((ROOT / "completion-review-index.json").read_text())
assert review["issue"] == 474
assert index["issue"] == 474 and index["current_main_base"] == "b0ade2e782003af8c9568ee98cb01582ef1bd13a"
for item in index["changed_outputs"] + index["retained_evidence"]["files"]:
    raw = Path(item["path"]).read_bytes()
    assert len(raw) == item["bytes"] and hashlib.sha256(raw).hexdigest() == item["sha256"]
assert review["frozen_issue_baseline"] == json.loads((ROOT / "baseline-inputs.json").read_text())["baseline_commit"]
assert review["created_from_current_main"] == "b0ade2e782003af8c9568ee98cb01582ef1bd13a"
expected = set(scope["member_location_ids"])
subjects = review["subjects"]
assert len(subjects) == len(expected) == 228
assert {r["id"] for r in subjects} == expected
assert len({r["id"] for r in subjects}) == 228
assert all(re.fullmatch(r"[0-9a-f]{64}", v) for v in review["source_hashes"].values())
assert all(r["classification"] == "insufficient-evidence" for r in subjects)
assert all(r["identity"]["baseline_feature_file"].startswith("data/geography/") for r in subjects)
assert all(r["source_profile"]["license_status"] for r in subjects)
assert all(r["source_profile"]["completeness"] for r in subjects)

classes = {}
for row in subjects:
    classes[row["source_class"]] = classes.get(row["source_class"], 0) + 1
assert classes == {
    "Niger 2012 ADM3 source unit": 204,
    "Mauritania 2020 ADM2 source unit": 13,
    "Mauritania RESOLVE ecoregion fragment": 10,
    "Niamey composite city": 1,
}

province_by_id = {r["id"]: r for r in review["provinces"]}
assert len(province_by_id) == 56 == len(assessment["provinces"])
province_members = [ident for r in province_by_id.values() for ident in r["scope_member_ids"]]
assert len(province_members) == len(set(province_members)) == 228
assert set(province_members) == expected
assert all(r["issue_classification"] == "insufficient-evidence" for r in review["provinces"])

for area in scope["area_scopes"]:
    row = next(r for r in review["areas"] if r["id"] == area["id"])
    assert len(row["scope_member_ids"]) == area["owned_member_location_count"]
    assert len(row["scope_member_ids"]) == row["owned_count"]
    assert row["full_count"] == area["full_area_location_count"]
assert len(review["areas"]) == 2
assert all(r["classification"] == "insufficient-evidence" for r in review["areas"])

known_followups = {"#801", "#804", "#806", "#833", "#834"}
assert all(set(r["followups"]) <= known_followups for r in subjects)
assert all(ref.startswith(("baseline/", "niger/", "geoboundaries/", "mauritania/", "resolve/")) for r in subjects for ref in r["cited_source_records"])
city = next(r for r in subjects if r["id"] == "atlas:city:NER-94")
assert city["followups"] == ["#806", "#834"]
new_parent = [r for r in subjects if "#833" in r["followups"]]
assert len(new_parent) == 31
assert sum(r["official_role_parent_crosswalk"]["resolution"] == "official-name-candidate-parent-unresolved" for r in new_parent) == 4
assert sum(r["boundary_screen"]["maximum_subject_area_overlap_fraction"] < 0.9 for r in new_parent) == 27
print(json.dumps({"result": "passed", "locations": 228, "provinces": 56, "areas": 2, "source_classes": classes, "niger_parent_child_subjects": len(new_parent), "unresolved_tibiri_rows": 4, "non_city_low_overlap_rows": 27}, sort_keys=True))
