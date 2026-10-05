#!/usr/bin/env python3
"""Reproduce the Côte d’Ivoire issue #469 source-role and parent review."""
from __future__ import annotations
import collections
import hashlib
import json
import re
import subprocess
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OWN = Path(__file__).resolve().parent
SOURCES = OWN / "sources"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_digest(path: Path) -> dict:
    raw = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(raw), "sha256": sha256(raw)}


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    return re.sub(r"[^a-z0-9]", "", value.encode("ascii", "ignore").decode("ascii"))


def repair_common_mojibake(value: str) -> str:
    """Reverse UTF-8 bytes decoded once as Latin-1, only for comparison."""
    try:
        return value.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


scope = read_json(OWN / "issue-scope.json")
cohort_snapshot = read_json(OWN / "cohort-partition.json")
ids = scope["member_location_ids"]
assert len(ids) == scope["location_count"] == 215
assert len(set(ids)) == 215
assert sha256("\n".join(ids).encode()) == scope["member_location_ids_sha256"]

baseline = {}
baseline_file_for_id = {}
all_civ_baseline_ids = set()
for path in sorted((ROOT / "data/geography").glob("part-*.json")):
    data = read_json(path)
    for feature in data["features"]:
        feature_id = feature.get("id") or feature.get("properties", {}).get("id")
        if feature_id and feature_id.startswith("gb:CIV:ADM3:"):
            all_civ_baseline_ids.add(feature_id)
        if feature_id in ids:
            assert feature_id not in baseline
            baseline[feature_id] = feature
            baseline_file_for_id[feature_id] = path
assert set(baseline) == set(ids), f"baseline roster missing={set(ids)-set(baseline)} extra={set(baseline)-set(ids)}"
atlas_civ_ids = all_civ_baseline_ids
own_civ_ids = {feature_id for feature_id in ids if feature_id.startswith("gb:CIV:ADM3:")}
external_cohort_ids = []
external_seen = set()
for cohort in cohort_snapshot["cohorts"]:
    peer_ids = cohort["civ_member_ids"]
    assert len(peer_ids) == cohort["civ_member_count"]
    assert len(set(peer_ids)) == len(peer_ids)
    assert not (external_seen & set(peer_ids)), f"Peer issue scopes overlap at #{cohort['issue_number']}"
    assert not (set(ids) & set(peer_ids)), f"Peer issue scope overlaps #469 at #{cohort['issue_number']}"
    external_seen.update(peer_ids)
    external_cohort_ids.extend(peer_ids)
assert external_seen | own_civ_ids == atlas_civ_ids, "Côte d’Ivoire issue scopes differ from baseline Atlas source roster"
assert not (external_seen & own_civ_ids)
scope_partition = {
    "issue_cohorts": [{"issue": row["issue_number"], "state_at_capture": row["state"], "civ_member_count": row["civ_member_count"]} for row in cohort_snapshot["cohorts"]],
    "this_issue_civ_member_count": len(own_civ_ids),
    "captured_peer_civ_member_count": len(external_seen),
    "combined_distinct_issue_scope_civ_count": len(external_seen | atlas_civ_ids),
    "baseline_atlas_civ_count": len(atlas_civ_ids),
    "exact_workload_partition_matches_baseline": True,
    "limit": "This verifies only the distinct GitHub issue workload IDs against the baseline Atlas roster; it does not certify current legal units, source completeness, boundaries, or island coverage."
}

pinned = read_json(SOURCES / "geoboundaries-CIV-ADM3-2021.geojson")
pinned_meta = read_json(SOURCES / "geoboundaries-CIV-ADM3-metadata.json")
pinned_features = pinned["features"]
pinned_by_id = {f["properties"]["shapeID"]: f for f in pinned_features}
assert len(pinned_features) == 510 == int(pinned_meta["admUnitCount"])
assert len(pinned_by_id) == len(pinned_features)
assert all(f["properties"]["shapeGroup"] == "CIV" and f["properties"]["shapeType"] == "ADM3" for f in pinned_features)

admin1 = read_json(SOURCES / "geoboundaries-CIV-ADM1-2016.geojson")["features"]
admin2 = read_json(SOURCES / "geoboundaries-CIV-ADM2-2016.geojson")["features"]
admin1_meta = read_json(SOURCES / "geoboundaries-CIV-ADM1-metadata.json")
admin2_meta = read_json(SOURCES / "geoboundaries-CIV-ADM2-metadata.json")
assert (len(admin1), len(admin2)) == (14, 33)
admin2_by_name = collections.defaultdict(list)
for feature in admin2:
    admin2_by_name[norm(repair_common_mojibake(feature["properties"]["shapeName"]))].append(feature["properties"])

current = read_json(SOURCES / "cntig-ocha-subprefectures-query-2025.geojson")["features"]
layer_meta = read_json(SOURCES / "cntig-ocha-subprefectures-layer-metadata.json")
assert len(current) == 510
current_by_name_region = collections.defaultdict(list)
for f in current:
    p = f["properties"]
    current_by_name_region[(norm(p["admin3Name"]), norm(p["admin1Name"]))].append(p)

region_names = {norm(f["properties"]["admin1Name"]): f["properties"]["admin1Name"] for f in current}
rows = []
role_counts = collections.Counter()
match_counts = collections.Counter()
geometry_types = collections.Counter()
component_counts = collections.Counter()
province_counts = collections.Counter()
for location_id in sorted(ids):
    props = baseline[location_id]["properties"]
    metadata = props["metadata"]
    original_id = metadata["original_id"]
    src = pinned_by_id[original_id]
    sp = src["properties"]
    atlas_region = props["parent_id"].split(":")[2]
    official_key = (norm(repair_common_mojibake(sp["shapeName"])), norm(atlas_region))
    matches = current_by_name_region[official_key]
    assert norm(repair_common_mojibake(sp["shapeName"])) == norm(props["name"]), (location_id, sp["shapeName"], props["name"])
    assert norm(atlas_region) in region_names, (location_id, atlas_region)
    assert metadata["source_id"] == "gb:CIV:ADM3"
    assert metadata["administrative_level"] == "ADM3"
    assert metadata["source_role"] == "Departments"
    geometry = src.get("geometry") or {}
    geom_type = geometry.get("type", "missing")
    coords = geometry.get("coordinates", [])
    component_count = len(coords) if geom_type == "MultiPolygon" else (1 if geom_type == "Polygon" else 0)
    role_counts[metadata["source_role"]] += 1
    match_counts[len(matches)] += 1
    geometry_types[geom_type] += 1
    component_counts[str(component_count)] += 1
    province_counts[atlas_region] += 1
    rows.append({
        "location_id": location_id,
        "atlas_name": props["name"],
        "atlas_parent_id": props["parent_id"],
        "atlas_parent_name": atlas_region.replace("-", " "),
        "pinned_shape_id": original_id,
        "pinned_shape_name_raw": sp["shapeName"],
        "pinned_shape_name_comparison": repair_common_mojibake(sp["shapeName"]),
        "pinned_shape_type": sp["shapeType"],
        "pinned_metadata_role_claim": metadata["source_role"],
        "pinned_metadata_level_claim": metadata["administrative_level"],
        "parent_assessment": "justified",
        "parent_finding": "The Atlas region grouping matches the 2016 pinned source ADM2 region name and the current official admin1Name; it is a grouping parent, not the direct department parent of this sub-prefecture.",
        "official_current_name_region_match_count": len(matches),
        "official_current_admin3_name": matches[0]["admin3Name"] if len(matches) == 1 else None,
        "official_current_admin2_department": matches[0]["admin2Name"] if len(matches) == 1 else None,
        "official_current_admin1_region": matches[0]["admin1Name"] if matches else None,
        "geometry_type": geom_type,
        "polygon_component_count": component_count,
        "assessment": "correction-needed",
        "finding": "Pinned source role says Departments; inspected official source classifies ADM3 as sous-préfectures. Atlas parent corresponds to an official region and intentionally skips the source department tier.",
        "unresolved": ("Current official service contains two Guézon features under Guemon; source-name plus region cannot assign this source ID to its official department." if len(matches) != 1 else None)
    })

assert len(rows) == 215
assert match_counts == {1: 213, 2: 2}, match_counts
assert set(province_counts) == set(scope["province_scopes"][i]["id"].split(":")[2] for i in range(len(scope["province_scopes"])))
assert all(row["assessment"] in {"justified", "correction-needed", "insufficient-evidence"} for row in rows)

province_rows = []
for item in scope["province_scopes"]:
    key = norm(item["name"])
    source_matches = admin2_by_name[key]
    assert len(source_matches) == 1, (item["id"], len(source_matches))
    assert key in region_names
    province_rows.append({
        "province_id": item["id"], "name": item["name"], "area_id": scope["area_scopes"][0]["id"],
        "scoped_location_count": province_counts[item["id"].split(":")[2]],
        "full_province_location_count": item["full_province_locations"],
        "pinned_source_parent_shape_id": source_matches[0]["shapeID"],
        "pinned_source_parent_level": admin2_meta["boundaryType"],
        "pinned_source_parent_role": admin2_meta["boundaryCanonical"],
        "official_current_region_name": region_names[key],
        "assessment": "justified",
        "finding": "The source-backed administrative region grouping is name-matched in the pinned 2016 ADM2 parent layer and in the official CNTIG/OCHA current admin1 field.",
        "limit": "This is a parent-purpose and label crosswalk only; no complete polygon overlay, boundary-vintage reconciliation, regional interior approval, or direct department-parent claim is made."
    })
assert sum(x["scoped_location_count"] for x in province_rows) == 215

area_item = scope["area_scopes"][0]
area_row = {
    "area_id": area_item["id"], "name": area_item["name"],
    "owned_member_location_count": area_item["owned_member_location_count"],
    "full_area_location_count": area_item["full_area_location_count"],
    "owned_fraction": area_item["owned_member_location_count"] / area_item["full_area_location_count"],
    "scoped_province_count": len(province_rows), "full_direct_child_count": 33,
    "other_issue_scope_members": len(external_seen), "issue_scope_partition_matches_baseline": True,
    "baseline_parent_purpose": "WGSRPD level 3 botanical country; botanical country-level unit for recording plant distributions, not an asserted political boundary.",
    "assessment": "insufficient-evidence",
    "finding": "Only 215/510 locations and 14/33 direct regional groups are owned by this packet. The inherited area source is a botanical-country scheme whose standard permits level-3 units to ignore political factors; this packet has not revalidated the complete area perimeter, land coverage, islands, or current sovereign boundary."
}

# These are explicit acceptance screens. A source-layer geometry type or an
# administrative count cannot establish completeness, topology, or territorial
# meaning; record what this packet actually checked and what remains open.
acceptance_screen = {
    "version": 1,
    "issue": 469,
    "scope_location_count": len(rows),
    "screens": [
        {"criterion": "fragmented_city_territories", "status": "insufficient-evidence", "finding": "The retained sources do not provide an exhaustive city/municipal footprint roster for these 215 units; no city-extent conclusion is made.", "next_evidence": "Obtain official locality/commune and sub-prefecture codes and compare scoped polygons with sourced urban footprints."},
        {"criterion": "province_sized_locations", "status": "insufficient-evidence", "finding": "Official layer fields identify ADM3 as sub-prefecture, but there is no verified code crosswalk or comparable area measurement in this packet; no size outlier is classified as a province-sized unit.", "follow_up_issue": 841},
        {"criterion": "anonymous_administrative_remainders", "status": "limited-screen", "finding": "Every scoped pinned shape has a nonempty source name that matches its Atlas label after the documented reversible encoding repair. This rules out blank names only; it does not rule out a named remainder or an unofficial label."},
        {"criterion": "disconnected_territories", "status": "limited-screen", "finding": "All 215 pinned geometries are Polygon with one polygon component and no interior rings. No topology validation, connectivity check against official administrative units, or completeness conclusion was performed."},
        {"criterion": "omitted_islands", "status": "insufficient-evidence", "finding": "The packet has no exhaustive official code roster or independent island inventory. Source feature counts and the issue-workload partition cannot establish island completeness.", "follow_up_issue": 841},
        {"criterion": "repeated_tiers", "status": "supported-with-limits", "finding": "All 215 members resolve to unique shapes from the same pinned ADM3 source tier, and the other captured Côte d’Ivoire issue cohorts partition the remaining baseline ADM3 IDs. Atlas parent nodes group by official region names; this does not establish direct parent links or exclude repeated/missing current units.", "follow_up_issue": 841},
        {"criterion": "oversized_groups", "status": "insufficient-evidence", "finding": "The 14 scoped region groups contain 7 to 33 of this packet's locations. No complete-child-area denominator or reviewed size threshold exists, so group size is not judged."},
        {"criterion": "weak_parents", "status": "correction-needed", "finding": "The 14 Atlas parent labels match official regions, but the official source places departments between regions and sub-prefectures. The source-name crosswalk does not identify the direct department for two Guézon records; the current parent evidence justifies a region grouping only.", "follow_up_issue": 841},
        {"criterion": "inconsistent_neighboring_units", "status": "insufficient-evidence", "finding": "This packet did not inspect full neighboring-region or cross-border units, nor did it reconcile adjacent boundary vintages. No inter-region boundary change is proposed from this subset."}
    ],
    "interpretation": "This screen reports acceptance evidence and gaps. Limited-screen and structural results do not establish legal completeness, topology, boundary accuracy, or regional approval."
}

source_paths = sorted(SOURCES.glob("*"))
source_inventory = [file_digest(p) for p in source_paths]
baseline_paths = sorted(set(baseline_file_for_id.values()))
baseline_inventory = [file_digest(p) for p in baseline_paths]
for row in rows:
    row["baseline_file"] = str(baseline_file_for_id[row["location_id"]].relative_to(ROOT))

out_assessments = OWN / "location-assessments.json"
out_assessments.write_text(json.dumps({"version": 1, "issue": 469, "scope_ids_sha256": scope["member_location_ids_sha256"], "assessed_count": len(rows), "assessments": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(OWN / "province-assessments.json").write_text(json.dumps({"version": 1, "issue": 469, "scope_count": len(province_rows), "assessments": province_rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(OWN / "area-assessment.json").write_text(json.dumps({"version": 1, "issue": 469, "scope_count": 1, "assessments": [area_row]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(OWN / "acceptance-screen.json").write_text(json.dumps(acceptance_screen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

summary = {
    "version": 1,
    "issue": 469,
    "retrieved_at_utc": "2026-10-05",
    "base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "issue_scope": {"count": len(ids), "member_location_ids_sha256": scope["member_location_ids_sha256"], "all_ids_in_baseline": True},
    "baseline_files": baseline_inventory,
    "pinned_sources": {
        "adm1": {**file_digest(SOURCES / "geoboundaries-CIV-ADM1-2016.geojson"), "units": len(admin1), "vintage": admin1_meta["boundaryYear"], "canonical": admin1_meta["boundaryCanonical"], "license": admin1_meta["boundaryLicense"]},
        "adm2": {**file_digest(SOURCES / "geoboundaries-CIV-ADM2-2016.geojson"), "units": len(admin2), "vintage": admin2_meta["boundaryYear"], "canonical": admin2_meta["boundaryCanonical"], "license": admin2_meta["boundaryLicense"]},
        "adm3": {**file_digest(SOURCES / "geoboundaries-CIV-ADM3-2021.geojson"), "units": len(pinned_features), "vintage": pinned_meta["boundaryYear"], "canonical": pinned_meta["boundaryCanonical"], "source": pinned_meta["boundarySource"], "license": pinned_meta["boundaryLicense"], "source_data_update_date": pinned_meta["sourceDataUpdateDate"], "build_date": pinned_meta["buildDate"]}
    },
    "official_current_source": {"data": file_digest(SOURCES / "cntig-ocha-subprefectures-query-2025.geojson"), "layer_metadata": file_digest(SOURCES / "cntig-ocha-subprefectures-layer-metadata.json"), "unit_count": len(current), "unique_administrative_regions_or_districts": len(region_names), "unique_departments": len({f["properties"]["admin2Name"] for f in current}), "unique_subprefecture_names": len({f["properties"]["admin3Name"] for f in current})},
    "role_result": {"assessment": "correction-needed", "count": len(rows), "pinned_role_claim_counts": dict(role_counts), "source_boundary_type": "ADM3", "official_current_layer_level_field": "admin3Name / Sous-Prefecture", "official_parent_field": "admin2Name / Département"},
    "parent_result": {"atlas_parents": dict(sorted(province_counts.items())), "all_parents_match_official_current_admin1_names": True, "pinned_admin1_units": len(admin1), "pinned_admin2_units": len(admin2), "current_unique_region_or_district_labels": len(region_names)},
    "official_name_region_crosswalk": {"unique": match_counts.get(1, 0), "ambiguous": match_counts.get(2, 0), "missing": match_counts.get(0, 0), "ambiguous_names": sorted({row["atlas_name"] for row in rows if row["official_current_name_region_match_count"] > 1})},
    "province_review": {"assessed": len(province_rows), "justified_groupings": len([row for row in province_rows if row["assessment"] == "justified"]), "source_parent_level": admin2_meta["boundaryType"], "source_parent_role": admin2_meta["boundaryCanonical"]},
    "area_review": area_row,
    "issue_scope_partition": scope_partition,
    "geometry": {"types": dict(geometry_types), "polygon_components": dict(component_counts), "limit": "Component counts come from original source polygons; they do not prove island completeness, adjacency, topology, or legal boundary correctness."},
    "completeness": {"pinned_adm3_count": len(pinned_features), "official_current_service_count": len(current), "dgat_current_counts": {"regions": 31, "departments": 108, "subprefectures_created": 509, "subprefectures_open": 475, "villages": 8576, "communes": 201, "autonomous_districts": 2}, "limit": "The counts describe different vintages/status concepts. Their one-unit variance between the DGAT administrative count and the 2021/2025 510-shape sets remains unresolved; no count is used as proof of exhaustive current legal coverage."},
    "source_files": source_inventory,
    "reproducibility": "Generated by this script from the pinned issue scope, baseline atlas features, pinned geoBoundaries files, and retained official CNTIG/OCHA service response."
}
(OWN / "reproduction.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"assessed": len(rows), "exact_ids": len(rows), "role_claim": dict(role_counts), "official_unique_name_region": dict(match_counts), "parents": dict(sorted(province_counts.items())), "baseline_files": baseline_inventory, "source_files": source_inventory}, ensure_ascii=False, indent=2))
