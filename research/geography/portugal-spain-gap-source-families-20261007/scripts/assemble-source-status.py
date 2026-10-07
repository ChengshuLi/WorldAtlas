#!/usr/bin/env python3
"""Join bounded source observations to the complete pinned 52/70 scope."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "research/geography/portugal-spain-gap-source-families-20261007"
INDEX_PATH = PACKAGE / "inputs/complete-input-index.json"
SUMMARY_PATH = PACKAGE / "outputs/jrc-2024-component-month-summary.json"
MAPA_JOIN_PATH = PACKAGE / "sources/mapa/target-contact-feature-joins.json"
ADMIN_OVERLAY_PATH = PACKAGE / "outputs/administrative-source-overlays.json"
MAPA_OVERLAY_PATH = PACKAGE / "outputs/mapa-current-snapshot-overlays.json"
APA_OVERLAY_PATH = PACKAGE / "outputs/apa-wfd-line-overlays.json"
APA_CAPABILITIES_PATH = PACKAGE / "sources/apa-wfd/capabilities.xml"
APA_SCHEMA_PATH = PACKAGE / "sources/apa-wfd/schema.xsd"
APA_CATALOG_API_PATH = PACKAGE / "sources/apa-wfd/license-catalog-api.json"
OUTPUT = PACKAGE / "outputs/source-status-matrix.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    index = json.loads(INDEX_PATH.read_text())
    jrc = json.loads(SUMMARY_PATH.read_text())
    mapa_joins = json.loads(MAPA_JOIN_PATH.read_text())
    admin = json.loads(ADMIN_OVERLAY_PATH.read_text())
    mapa = json.loads(MAPA_OVERLAY_PATH.read_text())
    apa = json.loads(APA_OVERLAY_PATH.read_text())
    scope = index["scope"]
    family_rows = {row["id"]: row for row in scope["family_component_contact_rows"]}
    component_rows = {row["component_id"]: row for row in jrc["components"]}
    admin_rows = {row["component_id"]: row for row in admin["components"]}
    mapa_rows = {row["component_id"]: row for row in mapa["components"]}
    apa_rows = {row["component_id"]: row for row in apa["components"]}
    if len(family_rows) != 52 or len(component_rows) != 70:
        raise SystemExit("full 52-family / 70-component scope is required")
    contact_mapa = {row["contact_id"]: row for row in mapa_joins["feature_joins"]}
    mapa_scope_ids = sorted(cid for cid in scope["contact_ids"] if cid.startswith("atlas:district:ESP-"))
    mapa_scope_features = {contact_mapa[cid]["source_feature"]["objectid"] for cid in mapa_scope_ids if cid in contact_mapa}
    families = []
    assigned = set()
    for fid, row in sorted(family_rows.items()):
        comp_ids = row["component_ids"]
        assigned.update(comp_ids)
        members = [component_rows[cid] for cid in comp_ids]
        admin_members = [admin_rows[cid] for cid in comp_ids]
        mapa_members = [mapa_rows[cid] for cid in comp_ids]
        apa_members = [apa_rows[cid] for cid in comp_ids]
        mapa_ids = [cid for cid in row["contact_ids"] if cid.startswith("atlas:district:ESP-")]
        current_mapa = [contact_mapa[cid] for cid in mapa_ids if cid in contact_mapa]
        families.append({
            "family_id": fid,
            "component_ids": comp_ids,
            "contact_ids": row["contact_ids"],
            "source_families": row.get("grouping", {}).get("source_families", []),
            "edge_neighbor_ids": row.get("edge_neighbor_ids", []),
            "existing_related_issues": row.get("existing_related_issues", []),
            "cause_status": "unknown",
            "component_count": len(comp_ids),
            "2024_jrc_context": {
                "components_with_any_water_detection": sum(m["source_grid_pixel_centers_with_water_detected_in_any_2024_month"] > 0 for m in members),
                "component_month_pixel_center_codes": {str(code): sum(int(m["component_month_code_counts"][str(code)]) for m in members) for code in (0, 1, 2)},
            },
            "consumed_admin_source_overlays": {
                product: {
                    "components_intersecting_source_union": sum(any(p["source_product"] == product and p["intersecting_source_feature_count"] > 0 for p in admin_members[i]["product_results"]) for i in range(len(admin_members))),
                    "components_covered_by_source_union": sum(next(p for p in admin_members[i]["product_results"] if p["source_product"] == product)["fully_covered_by_source_product_union"] for i in range(len(admin_members))),
                }
                for product in ("gb:ESP:ADM3", "gb:PRT:ADM2")
            },
            "apa_wfd_line_context": {"components_intersecting_wfd_river_lines": sum(r["intersecting_wfd_line_feature_count"] > 0 for r in apa_members), "intersecting_line_feature_count_sum": sum(r["intersecting_wfd_line_feature_count"] for r in apa_members)},
            "mapa_current_snapshot_context": {"components_intersecting_current_features": sum(r["intersecting_current_source_feature_count"] > 0 for r in mapa_members), "intersecting_pair_count_sum": sum(r["intersecting_current_source_feature_count"] for r in mapa_members), "maximum_current_source_union_coverage_fraction": max((r["current_source_union_coverage_fraction"] or 0) for r in mapa_members)},
            "mapa_current_snapshot": {
                "historical_source_contact_references_in_family": len(mapa_ids),
                "current_service_feature_joins": current_mapa,
                "limits": ["Current service capture is a recent, undated reference snapshot; it does not reconstruct the missing historical Atlas-imported bytes or vintage.", "Service metadata does not establish a license for the geometry payload."],
            },
            "other_source_status": {
                "esp_adm3_2018_simplified": "accepted original consumed input pinned; current diagnostic comparison only",
                "prt_adm2_2020_simplified": "accepted original consumed input pinned; current diagnostic comparison only",
                "apa_wfd_river_lines": "1,428 response features captured in full border envelope; WFD planning lines (2015-2021), not water surfaces or a complete wet-area inventory; current catalog API says license not specified, while capabilities say no access restrictions",
                "miteco_phc_2022_2027_vectors": "official download page captured; actual vector products not acquired because official endpoint returned a challenge form",
                "jrc_monthlyhistory_2024": "current seasonal context summarized where source-grid pixel centers intersect; non-detection and unsampled remainder do not close the source gap",
            },
            "water_status": "unknown",
            "ice_status": "unknown",
            "ownership_status": "unknown",
            "historical_status": "unknown",
            "boundary_edit": False,
        })
    if assigned != set(scope["component_ids"]):
        raise SystemExit(f"family matrix component mismatch: {len(assigned)} assigned")
    components = []
    for cid, row in sorted(component_rows.items()):
        components.append({
            "component_id": cid,
            "family_ids": row["source_family_ids"],
            "contact_ids": row["source_contact_ids"],
            "jrc_2024_pixel_centers": row["source_grid_pixel_centers_sampled_per_month_sum"],
            "jrc_2024_any_month_water_detected_pixel_centers": row["source_grid_pixel_centers_with_water_detected_in_any_2024_month"],
            "jrc_2024_codes_across_component_months": row["component_month_code_counts"],
            "consumed_admin_source_comparison": admin_rows[cid]["product_results"],
            "apa_wfd_line_context": apa_rows[cid],
            "mapa_current_snapshot_context": mapa_rows[cid],
            "water_status": "unknown",
            "ice_status": "unknown",
            "ownership_status": "unknown",
            "historical_status": "unknown",
            "boundary_edit": False,
        })
    result = {
        "schema": "worldatlas-source-gap-status-matrix-v1",
        "scope": {"families": len(families), "components": len(components), "contacts": scope["contact_count"], "family_roster_sha256": scope["family_ids_sha256"], "component_roster_sha256": scope["component_ids_sha256"], "contact_roster_sha256": scope["contact_ids_sha256"]},
        "mapa_scope": {"distinct_contacts_missing_historical_source_bytes": len(mapa_scope_ids), "distinct_contact_ids": mapa_scope_ids, "current_snapshot_contact_join_count": len([cid for cid in mapa_scope_ids if cid in contact_mapa]), "current_snapshot_unique_source_features": len(mapa_scope_features), "note": "Family rows repeat contact references. These are 18 distinct historical byte gaps in the full scope and 17 joined current features; the current snapshot does not restore historical import bytes or vintage."},
        "input_hashes": {"complete_input_index_sha256": sha(INDEX_PATH), "jrc_component_month_summary_sha256": sha(SUMMARY_PATH), "mapa_current_feature_joins_sha256": sha(MAPA_JOIN_PATH), "administrative_source_overlays_sha256": sha(ADMIN_OVERLAY_PATH), "mapa_current_snapshot_overlays_sha256": sha(MAPA_OVERLAY_PATH), "apa_wfd_line_overlays_sha256": sha(APA_OVERLAY_PATH), "apa_wfd_capabilities_sha256": sha(APA_CAPABILITIES_PATH), "apa_wfd_schema_sha256": sha(APA_SCHEMA_PATH), "apa_wfd_catalog_api_sha256": sha(APA_CATALOG_API_PATH)},
        "source_captures": {
            "jrc_2024_tile_capture_manifest": "sources/jrc/monthlyhistory-v1_5-2024-capture.json",
            "jrc_data_users_guide": "sources/jrc/DataUsersGuidev2024_v5.pdf",
            "mapa_layer_metadata": "sources/mapa/layer-metadata.json",
            "mapa_current_feature_joins": "sources/mapa/target-contact-feature-joins.json",
            "apa_wfd_full_envelope_capture": "sources/apa-wfd/pagination.json",
            "apa_wfd_capabilities": "sources/apa-wfd/capabilities.xml",
            "apa_wfd_schema": "sources/apa-wfd/schema.xsd",
            "apa_wfd_catalog_api": "sources/apa-wfd/license-catalog-api.json",
            "apa_wfd_line_overlay": "outputs/apa-wfd-line-overlays.json",
            "administrative_source_overlays": "outputs/administrative-source-overlays.json",
            "mapa_current_snapshot_overlays": "outputs/mapa-current-snapshot-overlays.json",
            "miteco_official_download_page": "sources/miteco/official-phc-download-page.html",
        },
        "limits": ["Source feature joins, area overlaps, river-line crossings, and water observations are diagnostics. They do not certify a rightful province, land/water class, historical ownership, or a boundary change.", "No cause, water, ice, ownership, or historical status is inferred; each remains unknown across all 70 components and 52 families.", "The 18 missing historical MAPA originals remain missing even where a recent current-service feature can be joined.", "APA WFD river-line intersections do not provide water-surface area or a complete physical water reference.", "The 2024 JRC raster covers 2022-2024 monthly history and is not a historical replacement for the 2018/2020 administrative products.", "The single component with no pixel center sampled at this resolution retains all of its geometry as unknown; no sampled component is fully classified by raster codes."],
        "families": families,
        "components": components,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"families": len(families), "components": len(components), "contacts": scope["contact_count"], "families_unknown": sum(f["cause_status"] == "unknown" for f in families), "components_unknown": sum(c["water_status"] == "unknown" and c["ownership_status"] == "unknown" for c in components), "sha256": sha(OUTPUT)}))


if __name__ == "__main__":
    main()
