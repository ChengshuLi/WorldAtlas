#!/usr/bin/env python3
"""Bounded Sechura source-product comparison for issue #1379.

Consumes only the exact retained whole PER ADM2 simplified/unsimplified
products, one physical-gap component and one current Atlas contact. Does not
invoke or regenerate any global producer.
"""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform, unary_union
from shapely.validation import explain_validity

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
FAMILY_ID = "gap-source-batch:5344ddbbdcc5dac52d0580aa"
COMPONENT_ID = "physical-component:d15872b646c35d39fa1f0cc1bda6edc9775a46edd3c2c5278690d770ef211708"
CONTACT_ID = "gb:PER:ADM2:86281439B13089313750619"
SHAPE_ID = "86281439B13089313750619"
SIMPLIFIED_PATH = Path("coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-PER-ADM2-000.bin.gz")
UNSIMPLIFIED_PATH = Path("data/regional-review/regional-review-d2dae235991eaa49/sources/geoboundaries-PER-ADM2-2020.geojson.gz")
CURRENT_PATH = Path("data/geography/part-18.json")
COMPONENT_PATH = Path("coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1/payloads/9c6a122c31a5cc535fbe49ea827fc02c605b4a268abf23ac31f7d0c48f9be156.bin")
FAMILY_DIR = Path("coordination/engineering/global-actionability-routing-20261007/results")
PHYSICAL_PATH = Path("coordination/engineering/global-physical-comparison-20261006/results/components-057.jsonl.gz")
METADATA_COPY = Path("inputs/upstream/geoboundaries-PER-ADM2-metadata.json.gz")

def raw(path: Path) -> bytes:
    return (ROOT / path).read_bytes()

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def load_gzip_json(path: Path):
    return json.loads(gzip.decompress(raw(path)))

def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def coord_count(geometry):
    def walk(value):
        if isinstance(value, list):
            if len(value) >= 2 and all(isinstance(n, (int, float)) for n in value[:2]):
                return 1
            return sum(walk(item) for item in value)
        return 0
    return walk(geometry["coordinates"])

def geometry_facts(feature):
    geom = shape(feature["geometry"])
    return {
        "type": geom.geom_type,
        "coordinate_count": coord_count(feature["geometry"]),
        "valid": bool(geom.is_valid),
        "validity_reason": "valid" if geom.is_valid else explain_validity(geom),
        "bounds": [float(v) for v in geom.bounds],
    }

def canonical_feature(feature):
    return json.loads(json.dumps(feature, sort_keys=True, ensure_ascii=False, separators=(",", ":")))

def main():
    simplified_bytes = raw(SIMPLIFIED_PATH)
    simplified_raw = gzip.decompress(simplified_bytes)
    simplified = json.loads(simplified_raw)
    unsimplified_bytes = raw(UNSIMPLIFIED_PATH)
    unsimplified_raw = gzip.decompress(unsimplified_bytes)
    unsimplified = json.loads(unsimplified_raw)
    current_bytes = raw(CURRENT_PATH)
    current = json.loads(current_bytes)
    component_bytes = raw(COMPONENT_PATH)
    component_collection = json.loads(gzip.decompress(component_bytes))
    metadata_bytes = (OUT / METADATA_COPY).read_bytes()
    metadata_raw = gzip.decompress(metadata_bytes)
    metadata = json.loads(metadata_raw)

    simple_rows = [f for f in simplified["features"] if f.get("properties", {}).get("shapeID") == SHAPE_ID]
    full_rows = [f for f in unsimplified["features"] if f.get("properties", {}).get("shapeID") == SHAPE_ID]
    atlas_rows = [f for f in current["features"] if f.get("id") == CONTACT_ID]
    component_rows = [f for f in component_collection["features"] if f.get("id") == COMPONENT_ID]
    if [len(simple_rows), len(full_rows), len(atlas_rows), len(component_rows)] != [1, 1, 1, 1]:
        raise ValueError(f"Selected feature cardinalities were {[len(simple_rows),len(full_rows),len(atlas_rows),len(component_rows)]}")
    simple_contact, full_contact, atlas_contact, candidate = simple_rows[0], full_rows[0], atlas_rows[0], component_rows[0]

    # Keep complete selected feature bodies as exact, deterministic evidence.
    selected = {
        "candidate-component.geojson": candidate,
        "current-atlas-contact.geojson": atlas_contact,
        "simplified-source-contact.geojson": simple_contact,
        "unsimplified-source-contact.geojson": full_contact,
    }
    for name, feature in selected.items():
        write_json(OUT / "inputs" / name, feature)
    (OUT / "inputs" / "upstream" / "geoboundaries-PER-ADM2-metadata.json").write_bytes(metadata_raw)

    # A local UTM projection is used only for this component near 81.1 W,
    # 6.07 S. Predicate evaluation remains on the original lon/lat geometries.
    to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32717", always_xy=True).transform
    candidate_geo = shape(candidate["geometry"])
    candidate_utm = transform(to_utm, candidate_geo)

    def one_product(name, collection):
        contacts = []
        intersection_geometries = []
        invalid = []
        for feature in collection["features"]:
            geom = shape(feature["geometry"])
            fid = feature.get("properties", {}).get("shapeID")
            if not geom.is_valid:
                invalid.append(fid)
            if not geom.intersects(candidate_geo):
                continue
            intersection = geom.intersection(candidate_geo)
            intersection_geometries.append(intersection)
            intersection_utm = transform(to_utm, intersection)
            contacts.append({
                "shapeID": fid,
                "shapeName": feature.get("properties", {}).get("shapeName"),
                "geometry_type": geom.geom_type,
                "intersects_in_original_lonlat": True,
                "covers_candidate": bool(geom.covers(candidate_geo)),
                "positive_area_intersection": bool(intersection_utm.area > 0),
                "intersection_area_utm17s_m2": float(intersection_utm.area),
                "source_geometry_valid": bool(geom.is_valid),
                "source_geometry_coordinate_count": coord_count(feature["geometry"]),
            })
        union = unary_union(intersection_geometries) if intersection_geometries else None
        union_area = float(transform(to_utm, union).area) if union is not None else 0.0
        return {
            "product": name,
            "feature_count": len(collection["features"]),
            "invalid_feature_count_whole_product": len(invalid),
            "invalid_shapeIDs_whole_product": invalid,
            "candidate_intersection_feature_count": len(contacts),
            "candidate_intersection_contacts": sorted(contacts, key=lambda row: str(row["shapeID"])),
            "candidate_area_utm17s_m2": float(candidate_utm.area),
            "union_intersection_area_utm17s_m2": union_area,
            "union_candidate_coverage_fraction": min(1.0, union_area / candidate_utm.area) if candidate_utm.area else None,
        }

    simple_result = one_product("simplified PER ADM2 product actually consumed by pinned baseline recipe", simplified)
    full_result = one_product("unsimplified PER ADM2 product retained and reviewed in #496", unsimplified)
    current_result = one_product("single current Atlas Sechura feature", {"features": [atlas_contact]})

    def pairwise(left, right):
        a, b = shape(left["geometry"]), shape(right["geometry"])
        au, bu = transform(to_utm, a), transform(to_utm, b)
        return {
            "left_coordinate_count": coord_count(left["geometry"]),
            "right_coordinate_count": coord_count(right["geometry"]),
            "left_equals_right_topologically": bool(a.equals(b)),
            "left_equals_right_exact_coordinates": bool(a.equals_exact(b, 0.0)),
            "left_covers_right": bool(a.covers(b)),
            "right_covers_left": bool(b.covers(a)),
            "intersection_area_utm17s_m2": float(au.intersection(bu).area),
            "left_minus_right_area_utm17s_m2": float(au.difference(bu).area),
            "right_minus_left_area_utm17s_m2": float(bu.difference(au).area),
            "symmetric_difference_area_utm17s_m2": float(au.symmetric_difference(bu).area),
            "left_valid": bool(a.is_valid),
            "right_valid": bool(b.is_valid),
        }

    # Family shards are raw slices, not independently parseable files. Join
    # every ordered decompressed part before parsing records.
    family_parts = sorted((ROOT / FAMILY_DIR).glob("families-*.bin.gz"))
    if not family_parts:
        raise ValueError("No pinned family shards found")
    family_bytes = b"".join(gzip.decompress(path.read_bytes()) for path in family_parts)
    family_rows = [json.loads(line) for line in family_bytes.splitlines() if line.strip()]
    family = [row for row in family_rows if row.get("id") == FAMILY_ID]
    if len(family) != 1:
        raise ValueError(f"Expected exactly one complete family row; found {len(family)}")
    physical_rows = [json.loads(line) for line in gzip.decompress(raw(PHYSICAL_PATH)).splitlines() if line.strip()]
    physical = [row for row in physical_rows if row.get("component_id") == COMPONENT_ID]
    if len(physical) != 1:
        raise ValueError(f"Expected exactly one physical comparison row; found {len(physical)}")

    input_receipts = []
    for path, content in [
        (SIMPLIFIED_PATH, simplified_bytes), (UNSIMPLIFIED_PATH, unsimplified_bytes),
        (CURRENT_PATH, current_bytes), (COMPONENT_PATH, component_bytes),
        (PHYSICAL_PATH, raw(PHYSICAL_PATH)),
    ]:
        input_receipts.append({"path": path.as_posix(), "bytes": len(content), "sha256": digest(content)})
    input_receipts.append({"path": "inputs/upstream/geoboundaries-PER-ADM2-metadata.json.gz", "bytes": len(metadata_bytes), "sha256": digest(metadata_bytes), "source_path": "data/regional-review/regional-review-d2dae235991eaa49/sources/geoboundaries-PER-ADM2-metadata.json.gz", "source_git_blob_oid": "8d4a9cd7727fa1057c2a94fd241fa97590570db2"})
    input_receipts.append({"path": "inputs/upstream/geoboundaries-PER-ADM2-metadata.json", "bytes": len(metadata_raw), "sha256": digest(metadata_raw), "derived_from": "inputs/upstream/geoboundaries-PER-ADM2-metadata.json.gz"})
    for path in family_parts:
        content = path.read_bytes()
        input_receipts.append({"path": path.relative_to(ROOT).as_posix(), "bytes": len(content), "sha256": digest(content)})
    output = {
        "version": 1,
        "scope": {"family_id": FAMILY_ID, "component_id": COMPONENT_ID, "contact_id": CONTACT_ID},
        "source_identity": {
            "simplified_product": {"raw_bytes": len(simplified_raw), "raw_sha256": digest(simplified_raw), "feature_count": len(simplified["features"])},
            "unsimplified_product": {"raw_bytes": len(unsimplified_raw), "raw_sha256": digest(unsimplified_raw), "feature_count": len(unsimplified["features"])},
            "shapeID": SHAPE_ID,
            "simplified_feature": geometry_facts(simple_contact),
            "unsimplified_feature": geometry_facts(full_contact),
            "current_atlas_feature": geometry_facts(atlas_contact),
            "candidate_component": geometry_facts(candidate),
            "current_feature_recorded_source_url": atlas_contact.get("properties", {}).get("metadata", {}).get("source_url"),
        },
        "source_product_metadata": {
            "source_metadata_compressed_bytes": len(metadata_bytes),
            "source_metadata_compressed_sha256": digest(metadata_bytes),
            "source_metadata_raw_bytes": len(metadata_raw),
            "source_metadata_raw_sha256": digest(metadata_raw),
            "recorded_boundary_id": metadata.get("boundaryID"),
            "recorded_boundary_year": metadata.get("boundaryYear"),
            "recorded_boundary_type": metadata.get("boundaryType"),
            "recorded_boundary_canonical": metadata.get("boundaryCanonical"),
            "recorded_boundary_source": metadata.get("boundarySource"),
            "recorded_boundary_license": metadata.get("boundaryLicense"),
            "recorded_license_source": metadata.get("licenseSource"),
            "recorded_source_data_update_date": metadata.get("sourceDataUpdateDate"),
            "recorded_build_date": metadata.get("buildDate"),
            "recorded_administrative_unit_count": metadata.get("admUnitCount"),
            "metadata_limits": ["These are publisher/registry metadata claims; represented year and acquisition/build dates do not independently establish effective dates, authority, positional accuracy or license applicability."],
        },
        "whole_input_receipts": input_receipts,
        "selected_family_row_sha256": digest(next(line for line in family_bytes.splitlines() if FAMILY_ID.encode() in line)),
        "complete_family_shard_count": len(family_parts),
        "product_comparisons": {"simplified": simple_result, "unsimplified": full_result, "current_atlas_contact": current_result},
        "feature_geometry_comparisons": {
            "current_atlas_vs_simplified": pairwise(atlas_contact, simple_contact),
            "current_atlas_vs_unsimplified": pairwise(atlas_contact, full_contact),
            "simplified_vs_unsimplified": pairwise(simple_contact, full_contact),
        },
        "existing_global_accounting": {
            "source_fitness": family[0].get("source_fitness"),
            "physical_status": physical[0].get("status"),
            "physical_observation_status": physical[0].get("physical_status"),
            "physical_authority": physical[0].get("physical_authority"),
            "physical_source_vintage": physical[0].get("source_vintage"),
            "existing_mapped_land_support_area_m2": physical[0].get("complete_support", {}).get("mapped_land_support", {}).get("area_m2"),
            "existing_mapped_inland_water_support_area_m2": physical[0].get("complete_support", {}).get("mapped_inland_water_support", {}).get("area_m2"),
            "current_contact_ids": family[0].get("original_fine_family", {}).get("contact_ids"),
            "component_ids": family[0].get("original_fine_family", {}).get("component_ids"),
            "cause_status": family[0].get("original_fine_family", {}).get("cause_status"),
            "source_fitness_required_role": family[0].get("original_fine_family", {}).get("responsible_role"),
        },
        "method_limits": [
            "Original lon/lat geometries are used for topological predicates; no snapping, repair or normalization is applied.",
            "Areas use local EPSG:32717 planar measurements for this single candidate; they are source-relative diagnostics, not survey accuracy or a physical/legal partition.",
            "Full versus simplified products are kept separate. Registry dates, licensing, source authority and the cause of Atlas geometry differences remain claims or unknowns unless independently supported.",
            "Existing GSHHG centroid screening is not complete dry-land or coastline evidence; absent water evidence is not dry land.",
            "No global component, source, water, numeric, hierarchy or release producer is rerun.",
        ],
    }
    write_json(OUT / "analysis.json", output)

if __name__ == "__main__":
    main()
