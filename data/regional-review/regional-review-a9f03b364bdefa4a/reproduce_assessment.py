#!/usr/bin/env python3
"""Rebuild the issue #457 subject ledger from its pinned baseline and sources."""
import hashlib
import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKET = Path(__file__).resolve().parent
DATA = ROOT / "data"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decompressed_sha(path):
    return hashlib.sha256(gzip.decompress(path.read_bytes())).hexdigest()


def canonical_ring(points):
    # Round to six decimal degrees, then remove ring start/direction dependence.
    ring = [(round(float(point[0]), 6), round(float(point[1]), 6)) for point in points[:-1]]
    if not ring:
        return ()

    def rotate_min(values):
        start = min(range(len(values)), key=lambda i: values[i:] + values[:i])
        return tuple(values[start:] + values[:start])

    return min(rotate_min(ring), rotate_min(list(reversed(ring))))


def canonical_polygons(geometry):
    polygons = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
    return sorted(tuple(sorted(canonical_ring(ring) for ring in polygon)) for polygon in polygons)


def geometry_inventory(geometry):
    polygons = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
    points = []
    for polygon in polygons:
        for ring in polygon:
            points.extend(ring)
    return {
        "component_count": len(polygons),
        "ring_count": sum(len(polygon) for polygon in polygons),
        "hole_ring_count": sum(max(0, len(polygon) - 1) for polygon in polygons),
        "vertex_count": len(points),
        "bbox_degrees": [min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points)] if points else None,
    }


def main():
    scope = json.loads((PACKET / "scope.json").read_text())
    index = json.loads((DATA / "world-index.json").read_text())
    units = {u["id"]: u for u in json.loads((DATA / "hierarchy.json").read_text())}
    features = {}
    part_hashes = {}
    for part in index["parts"]:
        path = DATA / part
        part_hashes[part] = sha(path)
        for feature in json.loads(path.read_text())["features"]:
            features[feature["id"]] = (feature, part)

    aafc_doc = json.loads((PACKET / "sources/aafc-terrestrial-ecoregions-v2.2.geojson").read_text())
    aafc = {str(f["properties"]["ECOREGION_ID"]): f["properties"] for f in aafc_doc["features"]}
    layer_doc = json.loads((PACKET / "sources/aafc-baseline-arcgis-layer0.geojson").read_text())
    layer_groups, v22_groups = {}, {}
    for feature in layer_doc["features"]:
        layer_groups.setdefault(str(feature["properties"]["ECOREGION_ID"]), []).append(feature)
    for feature in aafc_doc["features"]:
        v22_groups.setdefault(str(feature["properties"]["ECOREGION_ID"]), []).append(feature)
    if set(layer_groups) != set(v22_groups):
        raise SystemExit("AAFC source editions have different ecoregion ID sets")
    if any(any(f["properties"]["ECOREGION_NAME_EN"] != aafc[key]["ECOREGION_NAME_EN"] for f in layer_groups[key] + v22_groups[key]) for key in aafc):
        raise SystemExit("AAFC source editions have different English ecoregion names")
    equivalent_at_screen_precision = sum(
        sorted(canonical_polygons(f["geometry"]) for f in layer_groups[key]) ==
        sorted(canonical_polygons(f["geometry"]) for f in v22_groups[key]) for key in aafc
    )
    if equivalent_at_screen_precision != len(aafc):
        raise SystemExit("AAFC geometries differ at six-decimal-degree ring-normalized screening precision")
    gb_doc = json.loads((PACKET / "sources/geoboundaries-GRL-ADM1-9469f09.geojson").read_text())
    gb_by_id = {f["properties"]["shapeID"]: f for f in gb_doc["features"]}
    rows = []
    for location_id in scope["member_location_ids"]:
        if location_id not in features:
            raise SystemExit("Pinned ID missing from baseline: " + location_id)
        feature, part = features[location_id]
        props = feature["properties"]
        metadata = props.get("metadata", {})
        chain, parent = [], props.get("parent_id")
        while parent and parent not in [item["id"] for item in chain]:
            unit = units.get(parent)
            if not unit:
                chain.append({"id": parent, "missing": True})
                break
            chain.append({"id": parent, "name": unit.get("name"), "type": unit.get("type", unit.get("level"))})
            parent = unit.get("parent_id")
        source = metadata.get("source_id")
        source_row = aafc.get(source.rsplit(":", 1)[-1]) if source and source.startswith("aafc:ecoregion:") else None
        gb_row = gb_by_id.get(metadata.get("original_id")) if source == "gb:GRL:ADM1" else None
        geometry_bytes = json.dumps(feature.get("geometry"), sort_keys=True, separators=(",", ":")).encode()
        rows.append({
            "id": location_id,
            "name": props.get("name"),
            "reference_owner": props.get("reference_owner"),
            "geometry_type": feature.get("geometry", {}).get("type"),
            "geometry_inventory": geometry_inventory(feature["geometry"]) if feature.get("geometry") else None,
            "geometry_sha256": hashlib.sha256(geometry_bytes).hexdigest(),
            "baseline_part": part,
            "baseline_part_sha256": part_hashes[part],
            "source_id": source,
            "source_name": metadata.get("source_name"),
            "source_url": metadata.get("source_url"),
            "license": metadata.get("license"),
            "reference_year": metadata.get("reference_year"),
            "administrative_level": metadata.get("administrative_level"),
            "source_role": metadata.get("source_role"),
            "location_basis": metadata.get("location_basis"),
            "original_id": metadata.get("original_id"),
            "source_member_ids": metadata.get("source_member_ids", []),
            "geoBoundaries_source_name": gb_row["properties"]["shapeName"] if gb_row else None,
            "geoBoundaries_source_geometry_inventory": geometry_inventory(gb_row["geometry"]) if gb_row else None,
            "geoBoundaries_name_matches": props.get("name") == gb_row["properties"]["shapeName"] if gb_row else None,
            "geoBoundaries_geometry_matches_screen": canonical_polygons(feature["geometry"]) == canonical_polygons(gb_row["geometry"]) if gb_row else None,
            "parent_overlap_claim": metadata.get("hierarchy_overlap"),
            "reference_territory_overlap_claim": metadata.get("geographic_overlap"),
            "parent_chain": chain,
            "aafc_current_name_en": source_row.get("ECOREGION_NAME_EN") if source_row else None,
            "aafc_ecozone_id": source_row.get("ECOZONE_ID") if source_row else None,
            "aafc_ecoprovince_id": source_row.get("ECOPROVINCE_ID") if source_row else None,
            "aafc_current_source_feature_present": bool(source_row),
            "classification": "insufficient-evidence",
            "source_identity_finding": "supported" if source else "missing source identity",
            "assessment": "source lineage identified; boundary, completeness, named-subdivision semantics, and neighboring granularity remain unverified",
            "confidence": "insufficient evidence for geographic correctness",
        })

    ids = scope["member_location_ids"]
    if len(ids) != 125 or len(set(ids)) != 125:
        raise SystemExit("Scope must contain exactly 125 unique IDs")
    if hashlib.sha256("\n".join(sorted(ids)).encode()).hexdigest() != scope["member_location_ids_sha256"]:
        raise SystemExit("Pinned member ID digest mismatch")
    if len(rows) != len(ids):
        raise SystemExit("Incomplete subject audit")
    if any(not row["aafc_current_source_feature_present"] for row in rows if row["source_id"].startswith("aafc:")):
        raise SystemExit("AAFC source ID missing from official current dataset")
    gb_rows = [row for row in rows if row["source_id"] == "gb:GRL:ADM1"]
    if len(gb_rows) != 2 or any(not row["geoBoundaries_name_matches"] for row in gb_rows):
        raise SystemExit("The two scoped Greenland geoBoundaries records did not match their pinned source identities")

    province_members = {}
    for row in rows:
        for parent in row["parent_chain"]:
            if parent.get("type") == "province" or ":province:" in parent["id"]:
                province_members.setdefault(parent["id"], {"name": parent["name"], "location_ids": []})["location_ids"].append(row["id"])
                break
    province_assessment = [{
        "id": unit_id,
        "name": entry["name"],
        "scoped_location_count": len(entry["location_ids"]),
        "location_ids": sorted(entry["location_ids"]),
        "classification": "insufficient-evidence",
        "finding": "The parent label is traceable in the pinned hierarchy; its geographic definition, boundary, completeness, distinctness from neighboring provinces, and suitability beneath the area require source-level review.",
    } for unit_id, entry in sorted(province_members.items())]
    area_assessment = [{
        "id": area["id"], "name": area["name"],
        "owned_scope_count": area["owned_member_location_count"],
        "full_current_area_count": area["full_area_location_count"],
        "partial_scope": area["partial"],
        "classification": "insufficient-evidence",
        "finding": "This packet reviews the pinned area portion only; full-area completeness and parent approval remain open. For the partial Greenland scope, do not infer the unowned members from this packet.",
    } for area in scope["area_scopes"]]

    assessment = {
        "scope_member_ids_sha256": scope["member_location_ids_sha256"],
        "baseline_commit": "4215fda0a40697bbdc4f9f0a229fffe7764aac55",
        "baseline_world_index_sha256": sha(DATA / "world-index.json"),
        "baseline_hierarchy_sha256": sha(DATA / "hierarchy.json"),
        "scope_count": len(ids),
        "assessed_count": len(rows),
        "assessment_method": "Pinned-ID join to baseline geography parts and hierarchy; source attributes cross-checked against retained official AAFC 2.2 GeoJSON. Geometry hashes are SHA-256 of compact sorted-key JSON serialization, not canonicalized geometric equivalence hashes.",
        "aafc_source_comparison": {
            "baseline_item_layer_feature_count": len(layer_doc["features"]),
            "official_v2_2_feature_count": len(aafc_doc["features"]),
            "unique_ecoregion_id_count_in_each": len(aafc),
            "source_feature_count_equal_for_each_id": all(len(layer_groups[key]) == len(v22_groups[key]) for key in aafc),
            "id_sets_equal": True,
            "english_names_equal_for_all_ids": True,
            "geometries_equal_after_ring_order_and_direction_normalization_at_1e_6_degree_rounding": equivalent_at_screen_precision,
            "method": "Compare polygon rings after rounding coordinates to six decimal degrees, normalizing ring start vertex and direction, and sorting rings/polygons. This is a source-edition screening comparison only; it is not a geodetic error bound, legal-boundary test, or validation of atlas territory clipping.",
            "baseline_layer_metadata_sha256": decompressed_sha(PACKET / "sources/aafc-arcgis-layer-metadata.json.gz"),
            "baseline_layer_response_sha256": sha(PACKET / "sources/aafc-baseline-arcgis-layer0.geojson"),
            "official_v2_2_sha256": sha(PACKET / "sources/aafc-terrestrial-ecoregions-v2.2.geojson"),
        },
        "areas": area_assessment,
        "provinces": province_assessment,
        "subjects": rows,
    }
    result = json.dumps(assessment, indent=2, ensure_ascii=False) + "\n"
    if "--write" in __import__("sys").argv:
        (PACKET / "subject-assessment.json").write_text(result)
    elif result != (PACKET / "subject-assessment.json").read_text():
        raise SystemExit("subject-assessment.json differs; run with --write to refresh after reviewing input changes")
    print("PASS: reproduced 125/125 subject rows and matched subject-assessment.json")


if __name__ == "__main__":
    main()
