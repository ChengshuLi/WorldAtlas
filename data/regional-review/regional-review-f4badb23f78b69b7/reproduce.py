#!/usr/bin/env python3
"""Rebuild row-level ID/name and geometry summaries for issue #412.

Run from repository root:
  python3 data/regional-review/regional-review-f4badb23f78b69b7/reproduce.py

This reproduces source joins and structural summaries only. It does not certify
territorial meaning, boundary accuracy, source completeness, or license status.
"""
from __future__ import annotations

import collections
import csv
import hashlib
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path("data/regional-review/regional-review-f4badb23f78b69b7")


def normalized(value: str) -> str:
    plain = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", plain.lower())


def geometry_summary(geometry: dict) -> tuple[int, int, int]:
    kind, coordinates = geometry["type"], geometry["coordinates"]
    polygons = [coordinates] if kind == "Polygon" else coordinates if kind == "MultiPolygon" else []
    vertices = 0
    closed_rings = 0
    for polygon in polygons:
        for ring in polygon:
            vertices += len(ring)
            if ring and ring[0] == ring[-1]:
                closed_rings += 1
    return len(polygons), vertices, closed_rings


def load_atlas_features() -> dict[str, dict]:
    atlas = {}
    for part in (16, 28):
        with open(f"data/geography/part-{part}.json", encoding="utf-8") as stream:
            for feature in json.load(stream)["features"]:
                atlas[feature["properties"]["id"]] = feature
    return atlas


def main() -> None:
    scope = json.loads((ROOT / "scope.json").read_text(encoding="utf-8"))
    inventory = json.loads((ROOT / "source-inventory.json").read_text(encoding="utf-8"))
    for source in inventory["source_files"]:
        source_path = ROOT / source["path"]
        digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
        if digest != source["sha256"] or source_path.stat().st_size != source["bytes"]:
            raise SystemExit(f"source byte hash/length mismatch: {source['path']}")
    atlas = load_atlas_features()
    pinned = {}
    for country in ("MOZ", "ZMB"):
        path = ROOT / f"source/geoboundaries/{country}/geoBoundaries-{country}-ADM2.geojson"
        document = json.loads(path.read_text(encoding="utf-8"))
        pinned[country] = {f["properties"]["shapeID"]: f for f in document["features"]}

    with open(ROOT / "source/zambia-grid3-2022/zambia-administrative-boundaries-2022.geojson", encoding="utf-8") as stream:
        zambia = json.load(stream)
    current_zambia = collections.defaultdict(list)
    for feature in zambia["features"]:
        properties = feature["properties"]
        current_zambia[normalized(properties.get("DISTRICT", ""))].append(properties)
    zambia_names = [normalized(f["properties"].get("DISTRICT", "")) for f in zambia["features"]]
    pinned_zambia_names = [normalized(f["properties"].get("shapeName", "")) for f in pinned["ZMB"].values()]
    if len(zambia_names) != 116 or len(set(zambia_names)) != 116:
        raise SystemExit("official Zambia source must contain 116 unique district names")
    if len(pinned_zambia_names) != 116 or len(set(pinned_zambia_names)) != 116 or set(zambia_names) != set(pinned_zambia_names):
        raise SystemExit("full Zambia 2022-to-pinned-source district name crosswalk failed")
    if len(pinned["MOZ"]) != 159 or len(pinned["ZMB"]) != 116:
        raise SystemExit("pinned source feature counts differ from the retained metadata/issue source claims")

    columns = (
        "location_id", "country", "location_name", "atlas_parent_id", "source_feature_id",
        "source_name", "normalized_name_match", "source_match_count", "atlas_geometry_type",
        "atlas_polygon_parts", "atlas_vertex_count", "atlas_closed_ring_count", "source_geometry_type",
        "source_polygon_parts", "source_vertex_count", "source_closed_ring_count",
        "zambia_2022_name_match_count", "zambia_2022_province_field", "zambia_2022_prov_code",
        "zambia_2022_dist_code", "parent_review_status", "semantic_classification", "classification_basis",
        "boundary_evidence_status", "assessment_note",
    )
    rows = []
    for location_id in scope["member_location_ids"]:
        _, country, _, original_id = location_id.split(":", 3)
        feature = atlas[location_id]
        props = feature["properties"]
        source = pinned[country].get(original_id)
        source_name = source["properties"].get("shapeName", "") if source else ""
        atlas_parts, atlas_vertices, atlas_closed = geometry_summary(feature["geometry"])
        if source:
            source_parts, source_vertices, source_closed = geometry_summary(source["geometry"])
            source_type = source["geometry"]["type"]
        else:
            source_parts, source_vertices, source_closed, source_type = 0, 0, 0, ""

        z_matches = current_zambia.get(normalized(props["name"]), []) if country == "ZMB" else []
        province, province_code, district_code = "", "", ""
        if country == "MOZ":
            parent_status = "atlas_parent_only_no_redistributable_row_level_INE_confirmation"
            note = "Exact stable-ID/normalized-name join only. INE reports 161 districts; the 2019 geoBoundaries/OCHA source has 159. Roster, vintage and license remain unresolved."
            classification = "insufficient-evidence"
            basis = "The source labels ADM2 as districts, but 159-versus-161 completeness, current parent membership, and license chain are unresolved."
        elif len(z_matches) == 1:
            current = z_matches[0]
            province = current.get("PROVINCE", "")
            province_code = current.get("PROV_CODE", "")
            district_code = current.get("DIST_CODE", "")
            parent_status = "matches_2022_PROVINCE" if normalized(props["name"]) not in {normalized(n) for n in ("Chama", "Chirundu", "Itezhi-Tezhi")} else "conflicting_official_fields_and_sources"
            note = "Exact stable-ID/name join; province and code fields are not authoritative proof of geometry or legal parentage."
            if normalized(props["name"]) == normalized("Chama"):
                parent_status = "current_official_sources_support_Eastern_but_codes_conflict"
                note = "Sourced current-parent correction candidate (Eastern); preserve ID/geometry pending current licensed ADM1 linework and code reconciliation. #413 independently documents the cross-packet handoff."
                classification = "correction-needed"
                basis = "ZamStats 2022 and 2023–2047 Eastern Province rosters and current Eastern Province Administration list Chama in Eastern; Chama District Council's 2025 plan says it returned there in 2021. Atlas still assigns Muchinga. 2022 OSG/GRID3 PROV_CODE/DIST_CODE conflict with the PROVINCE name, so the current ADM1 linework/date still needs engineering confirmation."
            elif normalized(props["name"]) == normalized("Chirundu"):
                parent_status = "2021_official_transfer_and_2022_PROVINCE_support_Southern_codes_conflict"
                note = "Sourced current-parent correction candidate (Southern); preserve ID/geometry pending current licensed ADM1 linework and code reconciliation."
                classification = "correction-needed"
                basis = "Chirundu Town Council reports the district moved from Lusaka to Southern in 2021 and current Southern official listings place it there; the 2022 layer PROVINCE also says Southern. Atlas still assigns Lusaka. The 2022 PROV_CODE/DIST_CODE disagree with its PROVINCE field, so retain the parent handoff and resolve code/linework vintage before engineering changes."
            elif normalized(props["name"]) == normalized("Itezhi-Tezhi"):
                parent_status = "insufficient-evidence"
                note = "Exact ID/name join; current parent conflicts across dated narratives and 2022 PROVINCE/PROV_CODE/DIST_CODE fields. Preserve as unresolved."
                classification = "insufficient-evidence"
                basis = "Itezhi-Tezhi has contradictory current province narratives and 2022 province/code values, with historical transfer to Central in 2012 but later official Southern listings. Current legal parent is unresolved."
            else:
                classification = "justified"
                basis = "Unique name crosswalk to a 2022 official DISTRICT feature; its PROVINCE field matches the Atlas parent and the official census reports the national 10-province/116-district tier. This justifies administrative tier/parent only, not boundary accuracy."
        else:
            parent_status = "missing_or_nonunique_2022_name_match"
            note = "Name crosswalk to the 2022 official layer is missing or non-unique; investigate before correcting."
            classification = "insufficient-evidence"
            basis = "The current official district name crosswalk is missing or non-unique."

        rows.append({
            "location_id": location_id,
            "country": country,
            "location_name": props["name"],
            "atlas_parent_id": props["parent_id"],
            "source_feature_id": original_id,
            "source_name": source_name,
            "normalized_name_match": str(normalized(props["name"]) == normalized(source_name)).lower(),
            "source_match_count": int(source is not None),
            "atlas_geometry_type": feature["geometry"]["type"],
            "atlas_polygon_parts": atlas_parts,
            "atlas_vertex_count": atlas_vertices,
            "atlas_closed_ring_count": atlas_closed,
            "source_geometry_type": source_type,
            "source_polygon_parts": source_parts,
            "source_vertex_count": source_vertices,
            "source_closed_ring_count": source_closed,
            "zambia_2022_name_match_count": len(z_matches) if country == "ZMB" else "",
            "zambia_2022_province_field": province,
            "zambia_2022_prov_code": province_code,
            "zambia_2022_dist_code": district_code,
            "parent_review_status": parent_status,
            "semantic_classification": classification,
            "classification_basis": basis,
            "boundary_evidence_status": "insufficient-evidence",
            "assessment_note": note,
        })

    if len(rows) != scope["location_count"] or len({row["location_id"] for row in rows}) != len(rows):
        raise SystemExit("scope count or uniqueness check failed")
    if any(row["source_match_count"] != 1 or row["normalized_name_match"] != "true" for row in rows):
        raise SystemExit("pinned source ID/name join check failed")
    if any(row["semantic_classification"] not in {"justified", "correction-needed", "insufficient-evidence"} for row in rows):
        raise SystemExit("scoped row lacks an allowed semantic classification")
    parent_groups = collections.defaultdict(list)
    for row in rows:
        parent_groups[(row["country"], row["atlas_parent_id"])].append(row)
    for province in scope["province_scopes"]:
        country = "MOZ" if any(row["country"] == "MOZ" and row["atlas_parent_id"] == province["id"] for row in rows) else "ZMB"
        actual_count = len(parent_groups[(country, province["id"])])
        if actual_count != province["full_province_locations"]:
            raise SystemExit(f"issue scope parent count mismatch for {province['id']}: {actual_count} != {province['full_province_locations']}")
    with open(ROOT / "location-assessments.csv", "w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    with open(ROOT / "province-review.csv", "w", encoding="utf-8", newline="") as stream:
        fields = ("country", "atlas_parent_id", "scoped_location_count", "issue_declared_full_parent_count", "2022_zambia_source_province_field_counts", "unresolved_parent_rows")
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for (country, parent_id), members in sorted(parent_groups.items()):
            scoped_by_source_province = collections.Counter(row["zambia_2022_province_field"] for row in members if row["zambia_2022_province_field"])
            unresolved = [row["location_name"] for row in members if row["parent_review_status"] in ("conflicting_official_fields_and_sources", "missing_or_nonunique_2022_name_match")]
            writer.writerow({
                "country": country,
                "atlas_parent_id": parent_id,
                "scoped_location_count": len(members),
                "issue_declared_full_parent_count": next((p["full_province_locations"] for p in scope["province_scopes"] if p["id"] == parent_id), ""),
                "2022_zambia_source_province_field_counts": "; ".join(f"{name}={count}" for name, count in sorted(scoped_by_source_province.items())),
                "unresolved_parent_rows": "; ".join(unresolved),
            })
    print(f"PASS: {len(rows)} unique scoped IDs join to one pinned ADM2 feature with normalized name match")
    print("PASS: Zambia's full 116-name 2022 official to pinned geoBoundaries crosswalk is one-to-one")
    print(f"PASS: all {len(inventory['source_files'])} retained source/metadata files match recorded SHA-256 and byte length")
    print(f"PASS: Mozambique {sum(row['country'] == 'MOZ' for row in rows)} rows; Zambia {sum(row['country'] == 'ZMB' for row in rows)} rows")
    classes = collections.Counter(row["semantic_classification"] for row in rows)
    print("PASS: row-level semantic classifications: " + ", ".join(f"{name}={classes[name]}" for name in ("justified", "correction-needed", "insufficient-evidence")))
    print("LIMIT: structural joins do not establish territorial meaning, completeness, license, boundaries, or legal parentage")


if __name__ == "__main__":
    main()
