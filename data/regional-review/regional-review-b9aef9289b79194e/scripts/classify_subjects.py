#!/usr/bin/env python3
"""Emit one evidence assessment row per exact #435 member location."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINDINGS = ROOT / "findings"
roster = [json.loads(line) for line in (FINDINGS / "subject-roster.jsonl").read_text().splitlines()]
geometry = {row["id"]: row for row in (
    json.loads(line) for line in (FINDINGS / "pinned-source-reconciliation.jsonl").read_text().splitlines()
)}

def classify(row):
    shape = geometry[row["id"]]
    reasons = []
    status = "insufficient-evidence"
    if row["source_id"].startswith("resolve:"):
        status = "correction-needed"
        reasons.append("ecoregion-overlay-is-not-an-administrative-unit")
    if row["area_name"] == "Caprivi Strip":
        status = "correction-needed"
        reasons.append("legacy-area-and-parent-need-current-region-crosswalk")
    if row["name"] == "Arandis":
        status = "correction-needed"
        reasons.append("official-erongo-source-contradicts-caprivi-parent-and-pinned-location-bounds")
    if row["parent_name"] == "Cacadu":
        status = "correction-needed"
        reasons.append("stale-cacadu-parent-name")
    if row["name"].casefold() == row["parent_name"].casefold():
        status = "correction-needed"
        reasons.append("location-repeats-identical-parent-name-at-adjacent-tier")
    if row["source_id"] == "gb:SWZ:ADM2":
        status = "correction-needed"
        reasons.append("2017-source-roster-has-53-versus-conflicting-official-government-counts-of-55-and-59")
    if row["source_id"] == "gb:NAM:ADM2" and shape["comparison"].get("intersection_over_union", 1) < 0.95:
        status = "correction-needed"
        reasons.append("material-atlas-versus-pinned-2007-geometry-difference-needs-disposition")
    if not shape["atlas_geometry_valid_before_repair_for_comparison"]:
        status = "correction-needed"
        reasons.append("invalid-atlas-polygon-needs-geometry-disposition")

    source = row["source_id"]
    if source == "gb:LSO:ADM1":
        tier = "justified-as-administrative-district-tier; source geometry is OSM/Wambacher 2017, not legal cadastral proof"
    elif source == "gb:SWZ:ADM2":
        tier = "justified-as-local-Inkhundla/Tinkhundla-tier; current official roster is six units larger"
    elif source == "gb:ZAF:ADM3":
        tier = "justified-as-local-municipality-tier; pinned 2020 geometry is not the latest legal MDB footprint"
    elif source == "gb:BWA:ADM2":
        tier = "provisional subdistrict/census-unit role; official census districts are not consistently equivalent to administrative districts"
    elif source == "gb:NAM:ADM2":
        tier = "2007 administrative/constituency source identity only; post-2013 legal and 2023 census geography needs reconciliation"
    else:
        tier = "not a local administrative unit; derived portion combines a named administrative source with one RESOLVE ecological region"

    if not reasons:
        reasons.append("primary-current-boundary-evidence-not-retained-or-not-licensed-for-reuse")
    assessment = {
        "id": row["id"],
        "name": row["name"],
        "area_id": row["area_id"],
        "area_name": row["area_name"],
        "parent_id": row["parent_id"],
        "parent_name": row["parent_name"],
        "source_id": source,
        "source_original_id": row.get("source_original_id"),
        "source_role": row.get("source_role"),
        "source_reference_year": row.get("source_reference_year"),
        "source_license": row.get("source_license"),
        "source_feature_name": shape["source_feature_name"],
        "polygon_component_count": row.get("polygon_component_count"),
        "assessment": status,
        "semantic_tier_assessment": tier,
        "reason_codes": reasons,
        "geometry_evidence": shape["comparison"],
        "geometry_valid_before_repair_for_area_comparison": shape["atlas_geometry_valid_before_repair_for_comparison"],
        "evidence_ids": ["GB-" + source.split(":")[1] + "-PINNED" if source.startswith("gb:") else "RESOLVE-2017", "ATLAS-V5-CROSSWALK"],
        "boundary_correctness_certified": False,
    }
    return assessment

assessments = [classify(row) for row in roster]
out = FINDINGS / "subject-assessments.jsonl"
out.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in assessments))
from collections import Counter
summary = {
    "version": 1,
    "scope_ids_sha256": json.loads((ROOT / "source/issue-scope.json").read_text())["member_location_ids_sha256"],
    "assessments": len(assessments),
    "assessment_counts": dict(Counter(row["assessment"] for row in assessments)),
    "semantic_tier_note": "Each row separately records tier evidence; overall insufficient-evidence means present-day territorial boundaries or completeness are not proved.",
    "full_boundary_certification": False,
}
(FINDINGS / "subject-assessments-summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
print(json.dumps(summary, indent=2, sort_keys=True))
