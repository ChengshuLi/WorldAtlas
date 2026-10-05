#!/usr/bin/env python3
"""Build one explicit sourced assessment for each exact #467 location."""
import json
from pathlib import Path

PACKET = Path(__file__).resolve().parent
screen = json.loads((PACKET / "geographic-screen.json").read_text())
roster = json.loads((PACKET / "scope-source-inventory.json").read_text())
neighbors = json.loads((PACKET / "neighbor-granularity-screen.json").read_text())
roster_by_id = {row["id"]: row for row in roster["units"]}
neighbor_by_country = {row["country"]: row for row in neighbors["country_sources"]}

assessments = []
for finding in screen["subjects"]:
    source = roster_by_id[finding["id"]]
    country = "Benin" if finding["id"].startswith("gb:BEN:") else "Burkina Faso"
    parent_reason = (
        "The Benin 2007 commune polygon's highest overlap among the 2012 department polygons is the atlas-assigned parent, "
        "but a later-vintage comparison does not settle the exact shared boundary."
        if country == "Benin" else
        "The 2007 commune polygon falls within the atlas-assigned 2017 province polygon with a very high area share; the later reference is corroboration, not same-vintage proof."
    )
    reasons = []
    if finding["source_to_current_atlas_overlap_fraction"] < 0.95:
        reasons.append("Current published footprint differs materially from the retained 2007 source geometry; source-to-current area overlap is a screening lead, not proof of an error or correction.")
    if country == "Benin" and finding["expected_parent_overlap_fraction"] < 0.95:
        reasons.append("Expected parent layer overlap is below the documented 0.95 screening threshold; the 2012 parent reference is not contemporaneous with the 2007 commune source, and remains unresolved.")
    classification = "insufficient-evidence" if reasons else "justified"
    assessments.append({
        "id": finding["id"],
        "country": country,
        "classification": classification,
        "source_role": "commune / local municipal territory" if country == "Benin" else "commune (local municipality; distinct from the administrative 'department' term used in parallel in national records)",
        "source_role_basis": "Pinned 2007 geoBoundaries feature and metadata; for Burkina Faso, additionally the University of Texas/Stanford catalog's exact January 2007 commune layer record; for both, national statistical / administrative sources noted in source-research.md.",
        "source_id": finding["source_id"],
        "shape_id": source["id"].split(":")[-1],
        "source_name": source["source_name"],
        "atlas_name": finding["atlas_name"],
        "source_name_and_shape_id_match": finding["source_atlas_name_match"],
        "source_vintage": "2007",
        "source_license": "Public Domain, as recorded in the pinned source metadata and corroborated for the Burkina Faso source collection by the Stanford catalog record.",
        "parent": {
            "atlas_parent_id": finding["atlas_parent_id"],
            "atlas_parent_name": finding["atlas_parent_name"],
            "atlas_parent_tier": finding["atlas_parent_tier"],
            "comparison_parent_source": finding["parent_geometry_source_id"],
            "comparison_parent_vintage": finding["parent_geometry_vintage"],
            "expected_parent_overlap_fraction": finding["expected_parent_overlap_fraction"],
            "most_overlapped_parent_name": finding["maximum_parent_overlap_name"],
            "most_overlapped_parent_fraction": finding["maximum_parent_overlap_fraction"],
            "assessment": "insufficient-exact-boundary-evidence" if (country == "Benin" and finding["expected_parent_overlap_fraction"] < 0.95) else "supported-with-cross-vintage-limit",
            "rationale": parent_reason,
        },
        "geometry_screen": {
            "valid_polygon": finding["source_shape_valid"],
            "components": finding["source_component_count"],
            "source_land_area_m2": finding["source_land_area_m2"],
            "source_to_current_atlas_overlap_fraction": finding["source_to_current_atlas_overlap_fraction"],
            "current_atlas_from_source_overlap_fraction": finding["current_atlas_from_source_overlap_fraction"],
            "topology_reconciled_metadata": finding["topology_reconciled"],
            "topology_conflict_count_metadata": finding["topology_conflicts"],
        },
        "assessment_reasons": reasons,
        "evidence_limits": [
            "The names/IDs, source role, and geometry checks establish source crosswalks and screening observations, not surveyed ground truth.",
            "The parent layers are later-vintage reference geometries and cannot independently prove the exact 2007 boundary or source-to-parent membership.",
            "Area and feature counts alone do not establish semantic suitability, source completeness, or administrative correctness.",
        ],
    })

province_groups = {}
for unit in roster["units"]:
    key = (unit["atlas_parent_id"], unit["atlas_parent_name"], unit["reference_owner"])
    province_groups.setdefault(key, []).append(unit)
province_assessments = []
for (parent_id, parent_name, country), units in sorted(province_groups.items()):
    if country == "Benin":
        source = "benin-tbs-2011"
        classification = "insufficient-evidence" if parent_id in {
            "framework:province:atakora:167d1c8e020b",
            "framework:province:atlanique:de71c1be64ff",
            "framework:province:kouffo:b9df90330619",
            "framework:province:oueme:ee7fc244e72e",
        } else "justified"
        basis = "Official INSAE evidence identifies the 12-department / 77-commune grouping; pinned commune names and the later department reference support this group crosswalk."
        if classification == "insufficient-evidence":
            basis += " Display spelling needs an engineering alias/name decision. Low-overlap child boundaries also lack a same-vintage official crosswalk."
    else:
        source = "burkina-insd-2007-and-geoboundaries-adm2-2017"
        classification = "justified"
        basis = "Official INSD 2007 tables distinguish communes by province; the later 2017 province reference cross-check agrees with the scoped child parent assignments. This is 18 of 45 province groups, not complete national coverage."
    province_assessments.append({
        "id": parent_id, "name": parent_name, "country": country,
        "classification": classification, "scoped_child_count": len(units),
        "scoped_child_names": sorted({u["name"] for u in units}),
        "source_ids": sorted({u["source_id"] for u in units}),
        "evidence_source_ids": [source], "finding": basis,
        "limits": ["This scoped assessment does not certify the complete national area or the entire West Africa region.",
                   "Reference-layer overlap is a diagnostic crosswalk, not legal boundary authority."],
    })

result = {
    "version": 1,
    "issue": 467,
    "scope_location_count": len(assessments),
    "classification_counts": {
        key: sum(row["classification"] == key for row in assessments)
        for key in ("justified", "correction-needed", "insufficient-evidence")
    },
    "correction_needed_count": 0,
    "corrective_findings": [
        {
            "kind": "source-vintage-crosswalk",
            "subject_ids": [row["id"] for row in assessments if row["country"] == "Benin" and row["parent"]["expected_parent_overlap_fraction"] < 0.95],
            "finding": "Benin's 2007 commune polygons and the retained 2012 department parent layer disagree spatially for a bounded subset, although each subset member's dominant 2012 department name agrees with its current atlas parent. Exact same-vintage parent source and crosswalk remain to be established.",
            "action": "Create a bounded geography follow-up to restore/verify a same-vintage official 2007 commune-to-department source crosswalk and adjudicate the exact boundary mismatches. Do not alter IDs or geometry without independent evidence.",
        },
        {
            "kind": "current-geometry-provenance",
            "subject_ids": [row["id"] for row in assessments if row["geometry_screen"]["source_to_current_atlas_overlap_fraction"] < 0.95],
            "finding": "Five source/current polygons have under 95% source-to-current overlap; the Atlas records topology reconciliation, but this packet does not reproduce the entire publication geometry-transformation history.",
            "action": "Keep these subjects in the same-vintage crosswalk follow-up for Benin and a bounded topology/provenance verification for Burkina Faso; do not call them incorrect solely from this area screen.",
        },
    ],
    "parent_name_handoff": [
        {"id": "framework:province:atakora:167d1c8e020b", "atlas_name": "Atakora", "official_department_name": "Atacora", "note": "Confirm preferred spelling and alias policy; preserve identity."},
        {"id": "framework:province:atlanique:de71c1be64ff", "atlas_name": "Atlanique", "official_department_name": "Atlantique", "note": "Apparent dropped 't'; confirm and correct label/crosswalk without changing membership or ID."},
        {"id": "framework:province:kouffo:b9df90330619", "atlas_name": "Kouffo", "official_department_name": "Couffo", "note": "Confirm spelling and alias policy; preserve identity."},
        {"id": "framework:province:oueme:ee7fc244e72e", "atlas_name": "Oueme", "official_department_name": "Ouémé", "note": "Accent omitted in ASCII label; confirm house style and retain the official form as an alias if appropriate."},
    ],
    "subjects": assessments,
    "province_assessment_count": len(province_assessments),
    "provinces": province_assessments,
    "interpretation": "This packet supports commune-level territorial identities and high-level parent group assignments where stated. It does not approve a region or permit imports. Rows classified insufficient-evidence remain unresolved until their source-vintage and geometry follow-ups are completed.",
}
out = PACKET / "subject-assessments.json"
out.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
print(json.dumps({"output": str(out), "scope_location_count": len(assessments), "classification_counts": result["classification_counts"], "followups": [len(item["subject_ids"]) for item in result["corrective_findings"]]}, ensure_ascii=False, indent=2))
