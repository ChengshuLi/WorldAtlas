#!/usr/bin/env python3
"""Reproduce packet scope and evidence joins without downloading global source."""
import hashlib
import json
import pathlib

packet = pathlib.Path(__file__).resolve().parents[1]
issue = json.loads((packet / "source/issue-396-api-response.json").read_text())
import re
match = re.search(r"```json\s*(\{.*?\})\s*```", issue["body"], re.S)
if not match:
    raise SystemExit("issue workload JSON was not found")
scope = json.loads(match.group(1))
ids = scope["member_location_ids"]
features = json.loads((packet / "source/issue-396-scoped-geoboundaries-features.geojson").read_text())["features"]
source_ids = ["gb:RUS:ADM2:" + f["properties"]["shapeID"] for f in features]
roster = json.loads((packet / "findings/source-roster.json").read_text())
roster_ids = [r["subject_id"] for r in roster["rows"]]
joined = json.loads((packet / "findings/current-main-subject-join.json").read_text())
assessment = json.loads((packet / "findings/individual-assessment.json").read_text())
checks = {
    "issue_scope_count": len(ids) == 34 == scope["location_count"] and len(set(ids)) == 34,
    "source_extract_exact_scope": set(source_ids) == set(ids) and len(source_ids) == 34,
    "source_roster_exact_scope": set(roster_ids) == set(ids) and len(roster_ids) == 34,
    "current_main_exact_scope": set(r["subject_id"] for r in joined["rows"]) == set(ids) and joined["matched_count"] == 34 and not joined["missing_ids"],
    "individual_decisions_exact_scope": set(r["id"] for r in assessment["rows"]) == set(ids) and assessment["scope_count"] == 34,
    "all_decisions_explicit": len(assessment["rows"]) == 34 and all(r["decision"] in {"justified", "correction-needed", "insufficient-evidence"} for r in assessment["rows"]),
    "no_approval_claim": all(r["semantic_review_status_current_main"] == "open" for r in assessment["rows"]),
}
print(json.dumps({"checks": checks, "passed": all(checks.values()), "scope_sha256": scope["member_location_ids_sha256"]}, sort_keys=True))
if not all(checks.values()):
    raise SystemExit(1)
