#!/usr/bin/env python3
"""Reproduce the scoped Côte d’Ivoire source/atlas assessment.

Reads immutable Atlas blobs from the pinned main commit and the retained
geoBoundaries originals. Writes only beneath this issue's owned directory.
This is an evidence screen, not an administrative-law or boundary certificate.
"""
from __future__ import annotations

import hashlib
import gzip
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

from shapely import union_all
from shapely.affinity import translate
from shapely.geometry import shape


ROOT = Path(__file__).resolve().parents[3]
OWNED = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))
from evidence.geometry import VERSION as GEOMETRY_HELPER_VERSION  # noqa: E402
from evidence.geometry import canonical_land, land_area_m2  # noqa: E402
BASELINE = "b0ade2e782003af8c9568ee98cb01582ef1bd13a"
SOURCE_ROOT = OWNED / "sources/geoboundaries-9469f09"
SCOPE_PATH = OWNED / "scope.json"
RECEIPTS_PATH = OWNED / "source-receipts.json"
OUTPUT_PATH = OWNED / "district-assessments.json"
GENERIC_NAME = re.compile(r"^(?:unknown|other|remainder|remaining|unassigned|inconnu|non[- ]affect[eé]|reste|autre)$", re.IGNORECASE)
ADMIN_REMAINDER_MARKER = re.compile(r"(?:chef[- ]?lieu|centre|center|remainder|remaining|unknown|inconnu|non[- ]affect[eé]|reste)", re.IGNORECASE)
ATLAS_AREA_ID = "framework:area:ivory-coast:86d2b1a53604"


def git_blob(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{BASELINE}:{path}"], cwd=ROOT)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def source_utf8_repair(value: str) -> str:
    """Return a reversible display repair for UTF-8 bytes misread as Latin-1."""
    try:
        return value.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def component_count(geometry) -> int:
    if geometry.geom_type == "Polygon":
        return 1
    if geometry.geom_type == "MultiPolygon":
        return len(geometry.geoms)
    raise ValueError(f"Unsupported polygon geometry: {geometry.geom_type}")


def polygonal_area_m2(geometry) -> float:
    if geometry.is_empty:
        return 0.0
    if geometry.geom_type in ("Polygon", "MultiPolygon"):
        return land_area_m2(geometry)
    if geometry.geom_type == "GeometryCollection":
        parts = []
        for item in geometry.geoms:
            if item.geom_type == "Polygon":
                parts.append(item)
            elif item.geom_type == "MultiPolygon":
                parts.extend(item.geoms)
        return land_area_m2(union_all(parts)) if parts else 0.0
    return 0.0


def main() -> None:
    scope_raw = SCOPE_PATH.read_bytes()
    scope = json.loads(scope_raw)
    requested = scope["member_location_ids"]
    if len(requested) != 215 or len(set(requested)) != 215:
        raise SystemExit("Issue scope must contain exactly 215 unique members")
    requested_set = set(requested)

    issue = read_json(OWNED / "issue-contract.json")
    if issue["baseline_commit"] != BASELINE:
        raise SystemExit("Update the pinned baseline only with a new dated evidence vintage")
    if sha256(scope_raw) != issue["scope_sha256"]:
        raise SystemExit("Saved issue scope bytes differ from the recorded API scope hash")

    receipt_doc = read_json(RECEIPTS_PATH)
    receipt_by_path = {row["path"]: row for row in receipt_doc["sources"]}
    retained_inputs = {}
    for rel in [
        "sources/geoboundaries-9469f09/CIV-ADM1/geoBoundaries-CIV-ADM1.geojson",
        "sources/geoboundaries-9469f09/CIV-ADM1/geoBoundaries-CIV-ADM1-metaData.json",
        "sources/geoboundaries-9469f09/CIV-ADM2/geoBoundaries-CIV-ADM2.geojson",
        "sources/geoboundaries-9469f09/CIV-ADM2/geoBoundaries-CIV-ADM2-metaData.json",
        "sources/geoboundaries-9469f09/CIV-ADM3/geoBoundaries-CIV-ADM3.geojson",
        "sources/geoboundaries-9469f09/CIV-ADM3/geoBoundaries-CIV-ADM3-metaData.json",
    ]:
        path = OWNED / rel
        raw = path.read_bytes()
        receipt = receipt_by_path[str(path.relative_to(ROOT))]
        if sha256(raw) != receipt["sha256"] or len(raw) != receipt["bytes"]:
            raise SystemExit(f"Retained source does not match receipt: {rel}")
        retained_inputs[str(path.relative_to(ROOT))] = receipt["sha256"]

    index_raw = git_blob("data/world-index.json")
    hierarchy_raw = git_blob("data/hierarchy.json")
    macro_handoffs_raw = git_blob("data/macro-foundation/regional-handoffs.json.gz")
    macro_handoffs_sha = sha256(macro_handoffs_raw)
    macro_handoffs = json.loads(gzip.decompress(macro_handoffs_raw))
    macro_region = next(
        row for row in macro_handoffs["regions"]
        if row["region_id"] == scope["region_id"]
    )
    if (
        macro_region["envelope"]["geometry_sha256"] != scope["frozen_region_geometry_sha256"]
        or macro_region["envelope"]["member_location_ids_sha256"] != scope["frozen_region_member_ids_sha256"]
        or macro_region["regional_interiors_approved"]
        or macro_region["location_attribute_imports_ready"]
    ):
        raise SystemExit("Pinned macro envelope or geography approval gate differs from the issue scope")
    index = json.loads(index_raw)
    hierarchy = {row["id"]: row for row in json.loads(hierarchy_raw)}
    atlas = {}
    atlas_files = {}
    atlas_file_hashes = {}
    for rel in index["parts"]:
        blob = git_blob("data/" + rel)
        atlas_file_hashes["data/" + rel] = sha256(blob)
        for feature in json.loads(blob)["features"]:
            props = feature.get("properties", {})
            if props.get("id") in requested_set:
                if props["id"] in atlas:
                    raise SystemExit(f"Duplicate Atlas identity: {props['id']}")
                atlas[props["id"]] = feature
                atlas_files[props["id"]] = "data/" + rel
    if set(atlas) != requested_set:
        raise SystemExit(f"Atlas scope mismatch: missing={len(requested_set-set(atlas))}")

    sources = {}
    features_by_level = {}
    for level in ("ADM1", "ADM2", "ADM3"):
        source_file = SOURCE_ROOT / f"CIV-{level}/geoBoundaries-CIV-{level}.geojson"
        data = read_json(source_file)
        features_by_level[level] = data["features"]
        sources[level] = {
            "path": str(source_file.relative_to(ROOT)),
            "sha256": sha256(source_file.read_bytes()),
            "feature_count": len(data["features"]),
        }
    source3_features = features_by_level["ADM3"]
    source3 = {}
    for feature in source3_features:
        key = "gb:CIV:ADM3:" + feature["properties"]["shapeID"]
        if key in source3:
            raise SystemExit(f"Duplicate source shapeID: {key}")
        source3[key] = feature
    if len(source3) != 510:
        raise SystemExit(f"Pinned ADM3 file no longer contains 510 features: {len(source3)}")
    if any(identity not in source3 for identity in requested):
        raise SystemExit("One or more exact issue IDs are absent from the pinned source")

    parent2 = []
    for feature in features_by_level["ADM2"]:
        geometry = canonical_land(shape(feature["geometry"]))
        parent2.append({
            "name_raw": feature["properties"]["shapeName"],
            "name": source_utf8_repair(feature["properties"]["shapeName"]),
            "geometry": geometry,
            "area_m2": land_area_m2(geometry),
        })

    rows = []
    parent_counts = Counter()
    parent_overlaps = defaultdict(list)
    source_name_counts = Counter(
        source_utf8_repair(feature["properties"]["shapeName"]).casefold()
        for feature in source3_features
    )
    for identity in sorted(requested):
        atlas_feature = atlas[identity]
        atlas_props = atlas_feature["properties"]
        atlas_meta = atlas_props.get("metadata", {})
        source_feature = source3[identity]
        source_props = source_feature["properties"]
        atlas_geometry = canonical_land(shape(atlas_feature["geometry"]))
        source_geometry = canonical_land(shape(source_feature["geometry"]))
        atlas_area = land_area_m2(atlas_geometry)
        source_area = land_area_m2(source_geometry)
        intersection_area = polygonal_area_m2(atlas_geometry.intersection(source_geometry))
        union_area = atlas_area + source_area - intersection_area
        iou = intersection_area / union_area if union_area else 0.0
        atlas_covered = intersection_area / atlas_area if atlas_area else 0.0
        source_covered = intersection_area / source_area if source_area else 0.0

        overlaps = []
        for parent in parent2:
            intersection = source_geometry.intersection(parent["geometry"])
            area = polygonal_area_m2(intersection)
            if area > 0:
                overlaps.append((area, parent))
        overlaps.sort(key=lambda item: (-item[0], item[1]["name"]))
        source_name = source_utf8_repair(source_props["shapeName"])
        declared_parent_id = atlas_props.get("parent_id")
        declared_parent = hierarchy.get(declared_parent_id, {})
        if not overlaps:
            raise SystemExit(f"No ADM2 source overlap for {identity}")
        top_area, top_parent = overlaps[0]
        top_share = top_area / source_area
        second_share = overlaps[1][0] / source_area if len(overlaps) > 1 else 0.0
        source_parts = component_count(shape(source_feature["geometry"]))
        atlas_parts = component_count(shape(atlas_feature["geometry"]))
        parent_counts[declared_parent_id] += 1
        parent_overlaps[declared_parent_id].append({
            "source_name": source_name,
            "top_source_adm2_name": top_parent["name"],
            "top_source_adm2_share": top_share,
        })

        row_classification = (
            "correction-needed"
            if source_name.casefold() == "brofodoumé" and atlas_meta.get("source_role") == "Departments"
            else "insufficient-evidence"
        )
        row_uncertainty = [
            "The retained ADM3 source has no per-feature administrative parent identifier.",
            "The 2016 ADM2 overlay is an older geometric comparison, not a 2021 legal parent crosswalk.",
            "The national source labels the 510-feature layer Departments, while official 2021 sources distinguish 111 departments from 510 sub-prefectures; this row's exact legal role is unresolved pending crosswalk.",
        ]
        if row_classification == "correction-needed":
            row_uncertainty.append(
                "ANStat's 2021 sous-préfecture API documentation lists Brofodoumé under Department Abidjan; current Atlas metadata calls this feature Departments. Correct the source-role assertion after the exact row-to-source crosswalk is independently reproduced."
            )
        rows.append({
            "id": identity,
            "atlas_name": atlas_props["name"],
            "source_shape_id": source_props["shapeID"],
            "source_name_raw": source_props["shapeName"],
            "source_name_utf8_repair": source_name,
            "source_name_matches_atlas_after_utf8_repair": source_name == atlas_props["name"],
            "source_name_repeated_in_national_source": source_name_counts[source_name.casefold()] > 1,
            "source_shape_type": source_props["shapeType"],
            "source_parent_field": source_props.get("shapeGroup"),
            "source_has_named_parent_id": any(k.lower() in ("parent", "parentid", "parent_id") for k in source_props),
            "atlas_declared_parent_id": declared_parent_id,
            "atlas_declared_parent_name": declared_parent.get("name"),
            "name_equals_declared_parent": source_name.casefold() == str(declared_parent.get("name", "")).casefold(),
            "source_name_generic_label_match": bool(GENERIC_NAME.fullmatch(source_name.strip())),
            "source_name_remainder_or_centre_marker": bool(ADMIN_REMAINDER_MARKER.search(source_name)),
            "atlas_source_role": atlas_meta.get("source_role"),
            "atlas_administrative_level": atlas_meta.get("administrative_level"),
            "source_component_count": source_parts,
            "atlas_component_count": atlas_parts,
            "source_area_m2": source_area,
            "atlas_area_m2": atlas_area,
            "source_atlas_iou": iou,
            "atlas_area_covered_by_source": atlas_covered,
            "source_area_covered_by_atlas": source_covered,
            "source_adm2_parent_candidate_2016": top_parent["name"],
            "source_adm2_parent_candidate_share": top_share,
            "second_source_adm2_parent_share": second_share,
            "source_adm2_parent_matches_declared_parent_name": (
                top_parent["name"].casefold() == str(declared_parent.get("name", "")).casefold()
            ),
            "source_adm2_parent_area_share": top_area / top_parent["area_m2"],
            "classification": row_classification,
            "uncertainty": row_uncertainty,
            "correction_handoff": "Review the role and intermediate parent path before changing shared Atlas hierarchy or release data." if row_classification == "correction-needed" else None,
        })

    # Controlled checks: identical geometry must score near 1; a distant
    # translation must not pass as a matching footprint.
    control_feature = source3[sorted(requested)[0]]
    control = canonical_land(shape(control_feature["geometry"]))
    positive_iou = polygonal_area_m2(control.intersection(control)) / land_area_m2(control.union(control))
    negative = canonical_land(translate(control, xoff=-120))
    negative_intersection = control.intersection(negative)
    negative_intersection_area = polygonal_area_m2(negative_intersection)
    negative_union = land_area_m2(control) + land_area_m2(negative) - negative_intersection_area
    negative_iou = negative_intersection_area / negative_union if negative_union else 0.0
    if positive_iou < 0.999999 or negative_iou > 0.01:
        raise SystemExit("Geometry controls did not separate identical and translated shapes")

    distinct_parents = []
    issue_provinces = {row["id"]: row for row in scope["province_scopes"]}
    if set(issue_provinces) != set(parent_counts):
        raise SystemExit("Actual Atlas parent IDs differ from the issue's exact 15 parent scopes")
    for parent_id in sorted(parent_counts):
        parent = hierarchy.get(parent_id, {})
        found = parent_overlaps[parent_id]
        shares = [item["top_source_adm2_share"] for item in found]
        province_scope = issue_provinces[parent_id]
        parent_meta = parent.get("metadata", {})
        parent_semantic = parent_meta.get("semantic_review", {})
        distinct_parents.append({
            "id": parent_id,
            "name": parent.get("name"),
            "atlas_level": parent.get("level"),
            "parent_id": parent.get("parent_id"),
            "framework_basis": parent_meta.get("basis"),
            "framework_status": parent_meta.get("framework_status"),
            "semantic_review_action": parent_semantic.get("action"),
            "semantic_boundary_status": parent_semantic.get("boundary_status"),
            "semantic_rationale": parent_semantic.get("rationale"),
            "semantic_remaining_reasons": parent_semantic.get("remaining_reasons", []),
            "semantic_evidence": parent_semantic.get("evidence", []),
            "scoped_subject_count": parent_counts[parent_id],
            "issue_pinned_full_parent_location_count": province_scope["full_province_locations"],
            "issue_scope_partial": province_scope["partial"],
            "scoped_subject_names": sorted(item["source_name"] for item in found),
            "source_adm2_top_overlap_min_share": min(shares),
            "all_source_adm2_top_overlaps_match_parent_name": all(
                item["top_source_adm2_name"].casefold() == str(parent.get("name", "")).casefold()
                for item in found
            ),
        })

    source3_meta = read_json(SOURCE_ROOT / "CIV-ADM3/geoBoundaries-CIV-ADM3-metaData.json")
    source2_meta = read_json(SOURCE_ROOT / "CIV-ADM2/geoBoundaries-CIV-ADM2-metaData.json")
    source1_meta = read_json(SOURCE_ROOT / "CIV-ADM1/geoBoundaries-CIV-ADM1-metaData.json")
    repeated_name_groups = {name: count for name, count in source_name_counts.items() if count > 1}
    largest_parent_share_row = max(rows, key=lambda row: row["source_adm2_parent_area_share"])
    result = {
        "version": 1,
        "issue": 470,
        "baseline_commit": BASELINE,
        "retrieved_at_utc": "2026-10-05T02:12:00Z",
        "scope_sha256": issue["scope_sha256"],
        "scope_member_count": len(requested),
        "scope_area": scope["area_scopes"],
        "atlas_source_parent_file_hashes": atlas_file_hashes,
        "atlas_inputs": {
            "data/world-index.json": sha256(index_raw),
            "data/hierarchy.json": sha256(hierarchy_raw),
            "data/macro-foundation/regional-handoffs.json.gz": macro_handoffs_sha,
        },
        "macro_region_gate": {
            "region_id": macro_region["region_id"],
            "envelope_geometry_sha256": macro_region["envelope"]["geometry_sha256"],
            "member_location_ids_sha256": macro_region["envelope"]["member_location_ids_sha256"],
            "regional_interiors_approved": macro_region["regional_interiors_approved"],
            "location_attribute_imports_ready": macro_region["location_attribute_imports_ready"],
        },
        "retained_source_inputs": retained_inputs,
        "source_metadata": {"ADM1": source1_meta, "ADM2": source2_meta, "ADM3": source3_meta},
        "counts": {
            "exact_issue_ids": len(requested),
            "unique_atlas_features": len(atlas),
            "unique_geoBoundaries_ADM3_features": len(source3),
            "source_names_match_after_reversible_utf8_repair": sum(
                row["source_name_matches_atlas_after_utf8_repair"] for row in rows
            ),
            "source_names_raw_byte_decoded_exact_match": sum(
                row["source_name_raw"] == row["atlas_name"] for row in rows
            ),
            "source_multipart_features": sum(row["source_component_count"] > 1 for row in rows),
            "atlas_multipart_features": sum(row["atlas_component_count"] > 1 for row in rows),
            "distinct_declared_parent_scopes": len(distinct_parents),
            "correction_needed": sum(row["classification"] == "correction-needed" for row in rows),
            "insufficient_evidence": sum(row["classification"] == "insufficient-evidence" for row in rows),
            "scoped_repeated_name_groups": len({row["source_name_utf8_repair"].casefold() for row in rows if row["source_name_repeated_in_national_source"]}),
            "source_names_equal_declared_parent": sum(row["name_equals_declared_parent"] for row in rows),
            "generic_name_labels": sum(row["source_name_generic_label_match"] for row in rows),
            "name_remainder_or_centre_marker_hits": sum(row["source_name_remainder_or_centre_marker"] for row in rows),
            "children_over_half_2016_ADM2_parent_area": sum(row["source_adm2_parent_area_share"] > 0.5 for row in rows),
            "largest_child_share_of_2016_ADM2_parent": {
                "id": largest_parent_share_row["id"],
                "name": largest_parent_share_row["atlas_name"],
                "share": largest_parent_share_row["source_adm2_parent_area_share"],
            },
            "declared_parent_matches_2016_ADM2_top_overlap_name": sum(
                row["source_adm2_parent_matches_declared_parent_name"] for row in rows
            ),
        },
        "measurements": {
            "method": "WGS84 straight-source-edge ellipsoidal area via scripts/evidence/geometry.py; intersection/union measured from canonical longitude-first EPSG:4326 polygons",
            "helper_version": GEOMETRY_HELPER_VERSION,
            "source_atlas_iou_min": min(row["source_atlas_iou"] for row in rows),
            "source_atlas_iou_max": max(row["source_atlas_iou"] for row in rows),
            "atlas_covered_by_source_min": min(row["atlas_area_covered_by_source"] for row in rows),
            "source_covered_by_atlas_min": min(row["source_area_covered_by_atlas"] for row in rows),
            "source_ADM3_to_2016_ADM2_top_parent_share_min": min(row["source_adm2_parent_candidate_share"] for row in rows),
            "source_ADM3_to_2016_ADM2_top_parent_share_all_at_least_95pct": all(row["source_adm2_parent_candidate_share"] >= 0.95 for row in rows),
            "source_ADM3_to_2016_ADM2_parent_area_share_max": max(row["source_adm2_parent_area_share"] for row in rows),
            "geometry_controls": {"identical_polygon_iou": positive_iou, "translated_polygon_iou": negative_iou},
        },
        "parent_scopes": distinct_parents,
        "repeated_source_names": repeated_name_groups,
        "classification_note": "One row (Brofodoumé) is correction-needed for the source-role assertion because ANStat's 2021 API documentation lists it as a sub-prefecture under Department Abidjan while Atlas metadata calls it a Department. The other 214 rows remain insufficient-evidence for legal role; all 215 remain unverified for same-vintage legal parentage and authoritative boundary truth.",
        "limits": [
            "ADM3 source shapeGroup identifies only CIV, not an individual legal parent.",
            "The 2016 ADM2 overlay provides spatial corroboration only; it is not a contemporaneous 2021 legal roster.",
            "Equal counts, exact names, source/Atlas overlap, and topological controls do not prove source completeness or legal units.",
            "The authoritative current ANStat list/API could not be retrieved from this environment; the exact URL/query and retrieval barrier are in SOURCES.md.",
        ],
        "rows": rows,
    }
    OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(OUTPUT_PATH.relative_to(ROOT)),
        "sha256": sha256(OUTPUT_PATH.read_bytes()),
        "counts": result["counts"],
        "measurements": result["measurements"],
        "parent_scopes": len(distinct_parents),
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
