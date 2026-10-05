#!/usr/bin/env python3
"""Screen the #467 native source polygons, exact subject IDs and tier parents."""
from __future__ import annotations

import gzip
import hashlib
import json
import platform
from collections import Counter
from pathlib import Path

import pyproj
import shapely
from shapely.geometry import box, shape

from geometry import METHOD, VERSION, land_area_m2

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[2]
SOURCE_ROOT = PACKET / "sources/geoboundaries-9469f09"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def source(country: str, level: str):
    stem = f"geoBoundaries-{country}-{level}"
    folder = SOURCE_ROOT / f"{country}-{level}"
    geo = read_json(folder / f"{stem}.geojson")
    meta = read_json(folder / f"{stem}-metaData.json")
    return geo, meta


def area_ratio(intersection, denominator):
    if intersection.is_empty:
        return 0.0
    if intersection.geom_type in ("Polygon", "MultiPolygon"):
        polygonal = intersection
    elif intersection.geom_type == "GeometryCollection":
        pieces = [item for item in intersection.geoms if item.geom_type in ("Polygon", "MultiPolygon")]
        if not pieces:
            return 0.0
        from shapely import union_all
        polygonal = union_all(pieces)
    else:
        return 0.0
    return land_area_m2(polygonal) / land_area_m2(denominator)


issue = read_json(PACKET / "issue-467-snapshot.json")
body = issue["body"]
scope_start = body.index("```json\n") + len("```json\n")
scope_end = body.index("\n```", scope_start)
scope = json.loads(body[scope_start:scope_end])
subject_ids = scope["member_location_ids"]
assert len(subject_ids) == 224
assert hashlib.sha256("\n".join(subject_ids).encode()).hexdigest() == scope["member_location_ids_sha256"]
subject_set = set(subject_ids)

inventory_path = ROOT / "data/macro-foundation/current-membership-inventory.json.gz"
inventory = json.loads(gzip.decompress(inventory_path.read_bytes()))
hierarchy = read_json(ROOT / "data/hierarchy.json")
parents = {row["id"]: row for row in hierarchy}

atlas = {}
containing_files = {}
for relative in read_json(ROOT / "data/world-index.json")["parts"]:
    path = ROOT / "data" / relative
    for feature in read_json(path)["features"]:
        feature_id = feature["properties"]["id"]
        if feature_id in subject_set:
            assert feature_id not in atlas, f"duplicate baseline subject: {feature_id}"
            atlas[feature_id] = feature
            containing_files[feature_id] = str(path.relative_to(ROOT))
assert set(atlas) == subject_set

country_specs = {
    "BEN": {"location_level": "ADM2", "parent_level": "ADM1"},
    "BFA": {"location_level": "ADM3", "parent_level": "ADM2"},
}
rows = []
source_counts = {}
for country, spec in country_specs.items():
    location_source, location_meta = source(country, spec["location_level"])
    parent_source, parent_meta = source(country, spec["parent_level"])
    source_counts[country] = {
        "location_features": len(location_source["features"]),
        "metadata_feature_count": int(location_meta["admUnitCount"]),
        "parent_features": len(parent_source["features"]),
        "location_boundary_year": location_meta["boundaryYear"],
        "location_boundary_type": location_meta["boundaryType"],
        "location_boundary_canonical": location_meta.get("boundaryCanonical", ""),
        "location_license": location_meta["boundaryLicense"],
        "parent_boundary_year": parent_meta["boundaryYear"],
        "parent_boundary_type": parent_meta["boundaryType"],
        "parent_boundary_canonical": parent_meta.get("boundaryCanonical", ""),
        "parent_license": parent_meta["boundaryLicense"],
    }
    parent_geometries = {
        item["properties"]["shapeName"]: shape(item["geometry"])
        for item in parent_source["features"]
    }
    feature_by_id = {
        f"gb:{country}:{spec['location_level']}:{item['properties']['shapeID']}": item
        for item in location_source["features"]
    }
    for subject_id in subject_ids:
        if not subject_id.startswith(f"gb:{country}:"):
            continue
        source_feature = feature_by_id[subject_id]
        source_geometry = shape(source_feature["geometry"])
        atlas_feature = atlas[subject_id]
        atlas_props = atlas_feature["properties"]
        atlas_geometry = shape(atlas_feature["geometry"])
        parent_record = parents[atlas_props["parent_id"]]
        parent_name = parent_record["name"]
        source_name = source_feature["properties"]["shapeName"]
        parent_geometry = parent_geometries[parent_name]
        overlaps = {
            name: area_ratio(source_geometry.intersection(geometry), source_geometry)
            for name, geometry in parent_geometries.items()
        }
        winning_parent = max(overlaps, key=overlaps.get)
        expected_parent_ratio = overlaps.get(parent_name, 0.0)
        current_source_ratio = area_ratio(source_geometry.intersection(atlas_geometry), source_geometry)
        atlas_from_source_ratio = area_ratio(source_geometry.intersection(atlas_geometry), atlas_geometry)
        source_area = land_area_m2(source_geometry)
        atlas_area = land_area_m2(atlas_geometry)
        metadata = atlas_props["metadata"]
        rows.append({
            "id": subject_id,
            "baseline_file": containing_files[subject_id],
            "source_id": metadata["source_id"],
            "source_name": source_name,
            "atlas_name": atlas_props["name"],
            "source_atlas_name_match": source_name == atlas_props["name"],
            "source_shape_type": source_feature["geometry"]["type"],
            "source_shape_valid": source_geometry.is_valid,
            "source_component_count": len(source_geometry.geoms) if hasattr(source_geometry, "geoms") else 1,
            "source_land_area_m2": round(source_area, 3),
            "atlas_land_area_m2": round(atlas_area, 3),
            "source_to_current_atlas_overlap_fraction": round(current_source_ratio, 8),
            "current_atlas_from_source_overlap_fraction": round(atlas_from_source_ratio, 8),
            "atlas_parent_id": atlas_props["parent_id"],
            "atlas_parent_name": parent_name,
            "atlas_parent_tier": parent_record["level"],
            "expected_parent_overlap_fraction": round(expected_parent_ratio, 8),
            "maximum_parent_overlap_name": winning_parent,
            "maximum_parent_overlap_fraction": round(overlaps[winning_parent], 8),
            "parent_geometry_vintage": parent_meta["boundaryYear"],
            "parent_geometry_source_id": f"gb:{country}:{spec['parent_level']}",
            "source_role": metadata.get("source_role"),
            "selection_reason": metadata.get("selection_reason"),
            "reference_year": metadata.get("reference_year"),
            "topology_conflicts": metadata.get("topology_conflicts"),
            "topology_reconciled": metadata.get("topology_reconciled"),
        })

rows.sort(key=lambda row: row["id"])
assert len(rows) == len(subject_ids) == 224

# Independent controls for the WGS84 intersection area method.
control = box(1.0, 10.0, 2.0, 11.0)
positive = area_ratio(control.intersection(control), control)
negative_other = box(10.0, 10.0, 11.0, 11.0)
negative = area_ratio(control.intersection(negative_other), control)
assert abs(positive - 1.0) < 1e-12 and negative == 0.0

summary = {}
for country in country_specs:
    local = [row for row in rows if row["id"].startswith(f"gb:{country}:")]
    sorted_areas = sorted(row["source_land_area_m2"] for row in local)
    parent_names = Counter(row["atlas_parent_name"] for row in local)
    parent_name_disagreements = [row["id"] for row in local if row["maximum_parent_overlap_name"] != row["atlas_parent_name"]]
    expected_under_95 = [row["id"] for row in local if row["expected_parent_overlap_fraction"] < 0.95]
    source_overlap_under_95 = [row["id"] for row in local if row["source_to_current_atlas_overlap_fraction"] < 0.95]
    summary[country] = {
        "scoped_location_count": len(local),
        "source_feature_count": source_counts[country]["location_features"],
        "source_id_name_matches": sum(row["source_atlas_name_match"] for row in local),
        "valid_source_geometries": sum(row["source_shape_valid"] for row in local),
        "multipart_source_geometries": sum(row["source_component_count"] > 1 for row in local),
        "unique_atlas_parents": len(parent_names),
        "members_by_parent": dict(sorted(parent_names.items())),
        "parent_name_disagreement_subject_ids": parent_name_disagreements,
        "expected_parent_overlap_under_95_subject_ids": expected_under_95,
        "source_to_current_overlap_under_95_subject_ids": source_overlap_under_95,
        "source_area_m2_min": sorted_areas[0],
        "source_area_m2_median": sorted_areas[len(sorted_areas) // 2],
        "source_area_m2_max": sorted_areas[-1],
    }

result = {
    "version": 1,
    "issue": 467,
    "retrieved_at": "2026-10-04",
    "baseline_commit": "fdab75892d979b995a1d20f311006aeeddb770b5",
    "method": {
        "kind": "geography",
        "helper_version": VERSION,
        "method": METHOD,
        "overlay_software": {"shapely": shapely.__version__, "pyproj": pyproj.__version__, "python": platform.python_version()},
        "overlay_method": "Shapely 2.1.2 planar lon/lat polygon intersection; each resulting polygon numerator and source-polygon denominator measured with the shared WGS84 straight-source-edge ellipsoidal area helper. This is a diagnostic overlay and not a survey-grade or same-vintage boundary proof.",
        "controls": {"positive_identical_polygon_overlap": positive, "negative_disjoint_polygon_overlap": negative},
    },
    "source_inventory": source_counts,
    "country_summary": summary,
    "subjects": rows,
    "interpretation": [
        "Source-name and stable-ID match is a source crosswalk check; it does not by itself establish territorial role.",
        "Parent overlap compares source-vintage location polygons with separate national parent layers (Benin 2012, Burkina Faso 2017); it does not establish historical boundary truth.",
        "Source-to-current-atlas overlap compares 2007 source polygons with the currently published release geometry; differences are leads for review, not automatic errors.",
        "No area/count/topology result certifies the region, original source completeness, or import readiness.",
    ],
}
out = PACKET / "geographic-screen.json"
out.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"output": str(out.relative_to(ROOT)), "subjects": len(rows), "summary": summary, "controls": result["method"]["controls"]}, ensure_ascii=False, indent=2))
