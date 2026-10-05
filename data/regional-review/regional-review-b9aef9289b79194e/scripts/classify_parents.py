#!/usr/bin/env python3
"""Record a separate territorial-role result for every scoped province group."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINDINGS = ROOT / "findings"
scope = json.loads((ROOT / "source/issue-scope.json").read_text())
roster = [json.loads(line) for line in (FINDINGS / "subject-roster.jsonl").read_text().splitlines()]
bad_names = {"Cacadu", "Caprivi", "Kavango", "Karas"}
records = []
for group in scope["province_scopes"]:
    children = [row for row in roster if row["parent_id"] == group["id"]]
    names = {row["name"].casefold() for row in children}
    reasons = []
    status = "insufficient-evidence"
    if group["name"] in bad_names:
        status = "correction-needed"
        reasons.append("current-official-parent-name-or-boundary-supersedes-scoped-name")
    if group["name"].casefold() in names:
        status = "correction-needed"
        reasons.append("same-name-parent-and-location-repeat-a-geographic-tier")
    owner = children[0]["reference_owner"] if children else None
    if not reasons:
        if owner == "Botswana":
            status = "justified"
            reasons.append("2022-official-census-source-lists-the-administrative-parent-and-its-subdistrict-authorities")
        elif owner == "Eswatini":
            status = "justified"
            reasons.append("official-government-sources-confirm-four-administrative-regions-and-their-tinkhundla-structure")
        elif owner == "South Africa":
            status = "justified"
            reasons.append("current-mdb-and-government-registers-confirm-the-district-or-metro-parent-identity")
        else:
            reasons.append("current-parent-to-child-boundary-crosswalk-not-demonstrated-by-retained-authoritative-polygons")
    records.append({
        "id": group["id"],
        "name": group["name"],
        "scope_count": group["full_province_locations"],
        "scope_is_partial": group["partial"],
        "member_ids": [row["id"] for row in children],
        "member_names": [row["name"] for row in children],
        "assessment": status,
        "reason_codes": reasons,
        "owner": owner,
        "parent_boundary_correctness_certified": False,
    })
out = FINDINGS / "parent-assessments.jsonl"
out.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records))
from collections import Counter
print(json.dumps({"parents": len(records), "status_counts": dict(Counter(row["assessment"] for row in records)), "same_name_parent_child_groups": sum("same-name-parent-and-location-repeat-a-geographic-tier" in row["reason_codes"] for row in records)}, indent=2, sort_keys=True))
