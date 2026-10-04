#!/usr/bin/env python3
"""Reproduce the OCHA COD-AB comparison from #482's immutable input pins."""
import gzip
import json
import re
import unicodedata

from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform as shapely_transform, unary_union
from shapely.strtree import STRtree

from reproduction_common import (
    HIERARCHY as H,
    PACKET_COMMIT,
    BASELINE,
    FEATURES as cur,
    SCOPE as S,
    metric as pinned_metric,
    pinned_bytes,
    repaired_areal,
    unique_mapping,
    write_candidate,
)

INPUT = "data/regional-review/regional-review-4f180b98473f1071/"


def load(filename):
    raw = pinned_bytes(INPUT + "sources/" + filename, "issue_packet")
    return json.loads(gzip.decompress(raw))["features"]


def norm(value):
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", text)


project_coordinates = Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True).transform


def eq(feature):
    return shapely_transform(project_coordinates, transformer_geometry(feature))


def transformer_geometry(feature):
    return shape(feature["geometry"])


def metric(a, b):
    source_valid, current_valid = a.is_valid, b.is_valid
    result = pinned_metric(a, b)
    return {
        "source_area_km2": result["source_area_km2"],
        "current_area_km2": result["current_area_km2"],
        "symmetric_difference_percent": result["symmetric_difference_of_union_percent"],
        "relative_area_change_percent": result["relative_area_change_percent"],
        "source_valid": source_valid,
        "current_valid": current_valid,
        "source_valid_original": source_valid,
        "current_valid_original": current_valid,
        "source_repair_applied": result["source_repair_applied"],
        "current_repair_applied": result["current_repair_applied"],
    }


new2 = load("mdg-COD-AB-ADM2-2026-reviewed.geojson.gz")
new1 = load("mdg-COD-AB-ADM1-2026-reviewed.geojson.gz")
current2 = [feature for ident, feature in cur.items() if ident.startswith("gb:MDG:ADM2:")]
by_name = unique_mapping(new2, lambda f: norm(f["properties"]["adm2_name"]), "COD-AB ADM2 normalized name")
new2geoms = {key: eq(feature) for key, feature in by_name.items()}

rows = []
for feature in current2:
    props = feature["properties"]
    name = props["name"]
    normalized = norm(name)
    source = by_name.get(normalized)
    if source is None:
        rows.append({"atlas_id": feature["id"], "atlas_name": name, "match": False})
        continue
    source_props = source["properties"]
    rows.append({
        "atlas_id": feature["id"], "atlas_name": name,
        "CODAB_ADM2_PCODE": source_props["adm2_pcode"],
        "CODAB_ADM1_name": source_props["adm1_name"],
        "CODAB_ADM1_PCODE": source_props["adm1_pcode"],
        "match": True, **metric(new2geoms[normalized], eq(feature)),
    })

current_names = {norm(feature["properties"]["name"]) for feature in current2}
missing = [feature for feature in new2 if norm(feature["properties"]["adm2_name"]) not in current_names]
impact = []
for source in missing:
    geom = eq(source)
    hits = []
    for feature in current2:
        intersection = geom.intersection(eq(feature)).area / 1e6
        if intersection > 0.01:
            hits.append({
                "atlas_id": feature["id"], "atlas_name": feature["properties"]["name"],
                "intersection_km2": intersection,
                "intersection_of_new_unit_percent": 100 * (intersection * 1e6) / geom.area if geom.area else 0,
            })
    props = source["properties"]
    impact.append({
        "source_name": props["adm2_name"], "source_pcode": props["adm2_pcode"],
        "source_parent": props["adm1_name"], "area_km2": repaired_areal(geom).area / 1e6,
        "source_valid_original": geom.is_valid, "source_repair_applied": not geom.is_valid,
        "overlapping_current_locations": sorted(hits, key=lambda row: row["intersection_km2"], reverse=True),
    })

current_parent = {}
for ident, feature in cur.items():
    if ident.startswith("gb:MDG:ADM2:"):
        parent_id = feature["properties"]["parent_id"]
        current_parent.setdefault(parent_id, H.get(parent_id, {}).get("name"))
new1_by_norm = unique_mapping(new1, lambda f: norm(f["properties"]["adm1_name"]), "COD-AB ADM1 normalized name")
new1_names = {key: feature["properties"]["adm1_name"] for key, feature in new1_by_norm.items()}
old_current = sorted(set(current_parent.values()), key=str.casefold)

report = {
    "source": "OCHA COD-AB Madagascar current resource package version 01; dataset was reviewed 2026-07-06, administrative limits stated valid from 2018-08-10; CC BY-IGO",
    "source_adm2_count": len(new2), "current_assigned_mdg_adm2_count": len(current2),
    "current_named_adm2_matches": sum(row["match"] for row in rows),
    "new_unmatched_source_adm2": impact, "per_matched_location": rows,
    "current_old_parent_names": old_current, "source_adm1_count": len(new1),
    "source_adm1_names": sorted(feature["properties"]["adm1_name"] for feature in new1),
    "current_parent_name_count": len(old_current),
    "current_parent_names_missing_in_CODAB_normalized": [name for name in old_current if norm(name) not in new1_names],
    "CODAB_adm1_names_missing_from_current_parent_normalized": [name for name in sorted(new1_names.values()) if norm(name) not in {norm(x) for x in old_current}],
    "method": {
        "projection": "EPSG:6933 equal-area",
        "comparison": "Name-matched COD-AB ADM2 polygons versus the 119 pinned current Madagascar member geometries. Raw validity is retained before shapely.make_valid is applied to ephemeral comparison copies; unsupported repair outputs fail closed. New unmatched source units are intersected with all scoped Madagascar locations as diagnostic leads.",
        "limits": "OCHA metadata states the source was reviewed in 2026 but its limits are valid from 2018-08-10. Count, naming, and geometric differences support source-history reconciliation, not legal-boundary updates or political ownership.",
    },
}

parent_groups = {}
for ident, feature in cur.items():
    if ident.startswith("gb:MDG:ADM2:"):
        parent_groups.setdefault(feature["properties"]["parent_id"], []).append(feature)
parent_unions = {
    parent_id: unary_union([eq(feature) for feature in features])
    for parent_id, features in parent_groups.items()
}
parent_rows = []
for name, source in sorted(new1_by_norm.items()):
    source_geom = eq(source)
    hits = []
    for parent_id, current_geom in parent_unions.items():
        source_fixed, current_fixed = repaired_areal(source_geom), repaired_areal(current_geom)
        intersection = source_fixed.intersection(current_fixed).area
        if intersection > 10000:
            hits.append({
                "current_province_id": parent_id, "current_province_name": H[parent_id]["name"],
                "intersection_km2": intersection / 1e6,
                "percent_of_source_region": 100 * intersection / source_fixed.area if source_fixed.area else 0,
                "percent_of_current_parent": 100 * intersection / current_fixed.area if current_fixed.area else 0,
            })
    source_fixed = repaired_areal(source_geom)
    parent_rows.append({
        "source_name": source["properties"]["adm1_name"],
        "source_pcode": source["properties"]["adm1_pcode"],
        "valid_on": source["properties"]["valid_on"],
        "source_geometry_area_km2": source_fixed.area / 1e6,
        "source_valid_original": source_geom.is_valid,
        "source_repair_applied": not source_geom.is_valid,
        "normalized_exact_current_name_match": next((H[parent_id]["name"] for parent_id in parent_groups if norm(H[parent_id]["name"]) == name), None),
        "spatial_intersections_with_current_parent_descendant_unions": sorted(hits, key=lambda row: row["intersection_km2"], reverse=True),
    })
report["region_parent_source_crosswalk"] = {
    "source_admin1_count": len(new1), "current_scoped_parent_count": len(parent_unions),
    "records": parent_rows,
    "interpretation": "Intersection matrix is a diagnostic crosswalk for all source and current parent groups. It does not select a replacement parent, infer legal authority or mutate the location-determined hierarchy.",
}

current_union = unary_union([eq(feature) for feature in current2])
source2_union = unary_union([new2geoms[norm(feature["properties"]["adm2_name"])] for feature in new2])
source1_geoms = [eq(feature) for feature in new1]
source1_union = unary_union(source1_geoms)
current1_union = unary_union(list(parent_unions.values()))


def union_metric(source, current):
    source_valid, current_valid = source.is_valid, current.is_valid
    source, current = repaired_areal(source), repaired_areal(current)
    union = source.union(current).area
    return {
        "source_union_area_km2": source.area / 1e6, "current_union_area_km2": current.area / 1e6,
        "intersection_percent_of_source_union": 100 * source.intersection(current).area / source.area if source.area else None,
        "symmetric_difference_percent": 100 * source.symmetric_difference(current).area / union if union else 0,
        "relative_area_change_percent": 100 * (current.area - source.area) / source.area if source.area else None,
        "source_valid": source_valid, "current_valid": current_valid,
        "source_valid_original": source_valid, "current_valid_original": current_valid,
        "source_repair_applied": not source_valid, "current_repair_applied": not current_valid,
        "source_component_count": len(source.geoms) if hasattr(source, "geoms") else 1,
        "current_component_count": len(current.geoms) if hasattr(current, "geoms") else 1,
    }


def overlaps(geoms, labels, threshold_km2=0.001):
    tree = STRtree(geoms)
    result = []
    for i, geom in enumerate(geoms):
        for jx in tree.query(geom):
            j = int(jx)
            if j <= i:
                continue
            area = geom.intersection(geoms[j]).area / 1e6
            if area > threshold_km2:
                result.append({"a": labels[i], "b": labels[j], "intersection_km2": area})
    return result


report["partition_integrity"] = {
    "source_ADM2_feature_count": len(new2),
    "source_ADM2_feature_component_count_sum": sum(len(shape(f["geometry"]).geoms) if shape(f["geometry"]).geom_type == "MultiPolygon" else 1 for f in new2),
    "current_ADM2_feature_count": len(current2),
    "current_ADM2_feature_component_count_sum": sum(len(shape(f["geometry"]).geoms) if shape(f["geometry"]).geom_type == "MultiPolygon" else 1 for f in current2),
    "source_ADM2_interior_overlaps_over_0_001_km2": overlaps([new2geoms[norm(f["properties"]["adm2_name"])] for f in new2], [f["properties"]["adm2_name"] for f in new2]),
    "source_ADM1_interior_overlaps_over_0_001_km2": overlaps(source1_geoms, [f["properties"]["adm1_name"] for f in new1]),
    "all_120_ADM2_union_vs_current_119_member_union": union_metric(source2_union, current_union),
    "all_24_ADM1_union_vs_current_22_parent_descendant_union": union_metric(source1_union, current1_union),
    "method": "Pairwise administrative source overlaps over 0.001 km2 are reported as review leads. Areas use equal-area EPSG:6933. Sub-threshold overlaps, holes, offshore completeness, and legal status require separate inspection.",
}
report["baseline_commit"] = BASELINE
report["source_commit"] = PACKET_COMMIT
write_candidate("madagascar-current-COD-AB-review.json", report)
print("reproduced ADM2/ADM1:", len(new2), len(new1), "matched", sum(row["match"] for row in rows))
