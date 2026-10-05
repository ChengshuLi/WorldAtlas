#!/usr/bin/env python3
"""Build the fixed-scope triage ledgers from retained pins and comparison output."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = Path(__file__).resolve().parents[3]
scope = json.loads((ROOT / "scope.json").read_text())
pinned = json.loads((ROOT / "issue-scope-pinned.json").read_text())
comparison = json.loads((ROOT / "geometry-summary.json").read_text())
comparison_records = [json.loads(line) for line in (ROOT / "geometry-comparisons.jsonl").read_text().splitlines() if line]

features = {}
for part in ("data/geography/part-0.json", "data/geography/part-2.json"):
    for feature in json.loads((BASE / part).read_text())["features"]:
        if feature["id"] in scope["member_location_ids"]:
            features[feature["id"]] = feature
records = {r["id"]: r for r in comparison_records}
topology_flags = set(comparison["type_change_location_ids"])
iou_flags = set(comparison["iou_below_0_95_location_ids"])
explicit_chile_regions = {
    "Libertador General Bernardo O'Higgins", "Maule", "Valparaíso"
}
explicit_chile_names = {"Peñaflor", "Padre Hurtado"}
rows = []
for location_id in scope["member_location_ids"]:
    f = features[location_id]
    p = f["properties"]
    r = records[location_id]
    name = p["name"]
    region = r.get("current_region_name")
    if location_id.startswith("gb:ARG:"):
        if name == "Paso de los Indios":
            disposition = "insufficient-evidence"
            finding = "Current IGN calls the department Paso de Indios; authoritative sources inspected use both spellings. Resolve the gazetted/current official name before relabeling."
        elif name == "Pilnaniyeu":
            disposition = "correction-needed"
            finding = "Current IGN and other Argentina official sources use Pilcaniyeu; correct stable display name after source/vintage confirmation, without changing the identity or transferring facts."
        elif location_id in topology_flags or location_id in iou_flags:
            disposition = "correction-needed"
            finding = "Current IGN comparison flags disconnected-part topology and/or low simplified planar IoU; inspect the restored, unsimplified official source and identify island/geometry omissions before any replacement."
        else:
            disposition = "justified"
            finding = "Name, ADM2 department role, provincial assignment and generalized broad footprint align with the current IGN service; not a legal boundary or completeness certification."
    else:
        source_revision = region in explicit_chile_regions or name in explicit_chile_names
        if source_revision or location_id in topology_flags or location_id in iou_flags:
            disposition = "correction-needed"
            reasons = []
            if source_revision:
                reasons.append("Subdere 2023 change history identifies scoped communes in a documented regional/property-line update")
            if location_id in topology_flags:
                reasons.append("polygon/multipolygon part topology differs from baseline")
            if location_id in iou_flags:
                reasons.append("simplified planar IoU is below 0.95")
            finding = "; ".join(reasons) + "; restore/review the authorized source and map exact changes before proposing geometry."
        else:
            disposition = "justified"
            finding = "Exact current commune name (or documented Marchigüe/Marchihue alias), ADM3 commune role and province parent align with Subdere DPA 2023; broad comparison shows no listed triage flag. Not boundary certification."
    rows.append({
        "location_id": location_id, "name": name, "parent_id": p["parent_id"],
        "source_id": p.get("metadata", {}).get("source_id"),
        "baseline_role": p.get("metadata", {}).get("source_role"),
        "baseline_year": p.get("metadata", {}).get("reference_year"),
        "baseline_geometry_type": f["geometry"]["type"],
        "current_source_name": r.get("current_name"),
        "current_parent_name": r.get("current_parent_name"),
        "current_region_name": region,
        "current_geometry_type": r.get("current_geometry_type"),
        "current_multipart_count": r.get("current_multipart_count"),
        "simplified_iou_0_001_degrees": r.get("simplified_iou_0_001_degrees"),
        "disposition": disposition, "finding": finding,
        "follow_up": ("#938" if disposition == "correction-needed" and location_id.startswith("gb:CHL:") else
                      "#937" if disposition == "correction-needed" else
                      "#937" if disposition == "insufficient-evidence" else None)
    })

# Avoid hard-coded classifications going stale if upstream scope or comparison changes.
ids = [r["location_id"] for r in rows]
assert len(ids) == len(set(ids)) == scope["location_count"] == 230
assert set(ids) == set(scope["member_location_ids"])
assert len([r for r in rows if r["location_id"].startswith("gb:ARG:")]) == 53
assert len([r for r in rows if r["location_id"].startswith("gb:CHL:")]) == 177
assert sum(r["disposition"] == "justified" for r in rows) + sum(r["disposition"] == "correction-needed" for r in rows) + sum(r["disposition"] == "insufficient-evidence" for r in rows) == 230

parent_counts = {}
for r in rows:
    parent_counts[r["parent_id"]] = parent_counts.get(r["parent_id"], 0) + 1
province_by_id = {p["id"]: p for p in scope["province_scopes"]}
parents = []
for pid, count in sorted(parent_counts.items()):
    p = province_by_id[pid]
    duplicate_tdf = p["name"] == "Tierra del Fuego"
    parents.append({
        "parent_id": pid, "parent_name": p["name"], "child_count_in_this_packet": count,
        "full_parent_child_count_in_scope": p["full_province_locations"],
        "disposition": "correction-needed" if duplicate_tdf else "justified",
        "finding": ("Two distinct framework province parents share Tierra del Fuego and each has one scoped department child, while provincial Law 1186 places five departments under one province. Engineering must reconcile parent identity with stable crosswalks; do not edit hierarchy in this packet." if duplicate_tdf else
                    "Province name/child association aligns with the 2023 Subdere administrative division list for Chile or current IGN provincial assignment for Argentina; area purpose and region boundaries remain open."),
        "follow_up": "#937" if duplicate_tdf else None
    })
assert len(parents) == 29

summary = {
    "version": 1,
    "record_type": "summary",
    "issue": 444,
    "baseline_commit": pinned["snapshot_commit"],
    "issue_scope_file": "issue-scope-pinned.json",
    "location_count": len(rows),
    "dispositions": {k: sum(r["disposition"] == k for r in rows) for k in ("justified", "correction-needed", "insufficient-evidence")},
    "parent_count": len(parents),
    "follow_up_issues": {"argentina": 937, "chile": 938},
    "limits": [
        "Justified means identity, administrative source role, parent association and coarse comparison are supported only; it is not boundary, completeness, parent-purpose or region certification.",
        "Argentina IGN query uses generalized geometry (0.001 degree maximum offset, five decimal precision); original un-generalized service geometry was unavailable in reasonable time.",
        "Chile Subdere 2023 metadata gives no explicit redistribution license; source cache is not redistributed. Restore from the official archive only under applicable terms.",
        "Southern South America macro region and both area semantics remain open; Chile Central is split with issue #445; #446/#928 handles country-SPI."
    ],
}
(ROOT / "location-assessments.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in [{"record_type": "summary", **summary}, *[{"record_type": "location", **row} for row in rows], *[{"record_type": "parent", **row} for row in parents]]))
print(json.dumps({"locations": len(rows), "dispositions": summary["dispositions"], "parents": len(parents), "argentina_followup_ids": sum(r["follow_up"] == "#937" for r in rows), "chile_followup_ids": sum(r["follow_up"] == "#938" for r in rows)}, indent=2))
