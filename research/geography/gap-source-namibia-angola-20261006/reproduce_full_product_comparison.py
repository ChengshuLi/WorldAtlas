#!/usr/bin/env python3
"""Compare all gap candidates to full same-release geoBoundaries products."""
import hashlib
import json
import platform
from pathlib import Path

import shapely
from shapely.geometry import Point, LineString, Polygon, box, mapping, shape
from shapely.ops import unary_union
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parent
SOURCES = ROOT / "sources"
INPUTS = ROOT / "inputs"
IMMUTABLE_INPUT_PATHS = [
    INPUTS / "original-components.geojson",
    INPUTS / "source-contact-features.geojson",
    INPUTS / "input-bindings.json",
    INPUTS / "whole-input-pins.json",
    SOURCES / "gb-NAM-ADM2-000.bin.gz",
    SOURCES / "gb-AGO-ADM2-000.bin.gz",
    SOURCES / "geoBoundaries-NAM-ADM2-full-9469f09.geojson",
    SOURCES / "geoBoundaries-AGO-ADM2-full-9469f09.geojson",
    SOURCES / "geoBoundaries-NAM-ADM2-metadata-9469f09.json",
    SOURCES / "geoBoundaries-AGO-ADM2-metadata-9469f09.json",
]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


def immutable_input_hashes():
    return {str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in IMMUTABLE_INPUT_PATHS}


def dimensions(geom):
    result = {"area": 0, "line": 0, "point": 0}
    if geom.is_empty:
        return result
    if geom.geom_type in ("Polygon", "MultiPolygon"):
        result["area"] = 1
    elif geom.geom_type in ("LineString", "LinearRing", "MultiLineString"):
        result["line"] = 1
    elif geom.geom_type in ("Point", "MultiPoint"):
        result["point"] = 1
    else:
        for item in geom.geoms:
            for key, value in dimensions(item).items():
                result[key] += value
    return result


components = json.loads((INPUTS / "original-components.geojson").read_text())["features"]
contacts = json.loads((INPUTS / "source-contact-features.geojson").read_text())["features"]
input_hashes_before = immutable_input_hashes()
assert len(components) == 21 and len(contacts) == 10
component_geometries = [shape(f["geometry"]) for f in components]
assert all(g.is_valid for g in component_geometries)

product_features = {}
product_receipts = []
for country in ("NAM", "AGO"):
    path = SOURCES / f"geoBoundaries-{country}-ADM2-full-9469f09.geojson"
    metadata_path = SOURCES / f"geoBoundaries-{country}-ADM2-metadata-9469f09.json"
    lfs_path = SOURCES / f"geoBoundaries-{country}-ADM2-full-9469f09.lfs-pointer.txt"
    metadata_lfs_path = SOURCES / f"geoBoundaries-{country}-ADM2-metadata-9469f09.lfs-pointer.txt"
    raw = path.read_bytes()
    metadata_raw = metadata_path.read_bytes()
    lfs = lfs_path.read_text().splitlines()
    meta_lfs = metadata_lfs_path.read_text().splitlines()
    expected_data_hash = next(x.split(":", 1)[1] for x in lfs if x.startswith("oid "))
    expected_data_bytes = int(next(x.split(" ", 1)[1] for x in lfs if x.startswith("size ")))
    expected_metadata_hash = next(x.split(":", 1)[1] for x in meta_lfs if x.startswith("oid "))
    expected_metadata_bytes = int(next(x.split(" ", 1)[1] for x in meta_lfs if x.startswith("size ")))
    assert len(raw) == expected_data_bytes and sha(raw) == expected_data_hash
    assert len(metadata_raw) == expected_metadata_bytes and sha(metadata_raw) == expected_metadata_hash
    metadata = json.loads(metadata_raw)
    features = json.loads(raw)["features"]
    assert metadata["boundaryISO"] == country and metadata["boundaryType"] == "ADM2"
    assert len(features) == int(metadata["admUnitCount"])
    assert all(shape(f["geometry"]).is_valid for f in features)
    product_features[country] = features
    product_receipts.append({
        "country": country,
        "product_path": "sources/" + path.name,
        "product_bytes": len(raw),
        "product_sha256": sha(raw),
        "lfs_sha256": expected_data_hash,
        "metadata_path": "sources/" + metadata_path.name,
        "metadata_bytes": len(metadata_raw),
        "metadata_sha256": sha(metadata_raw),
        "metadata_lfs_sha256": expected_metadata_hash,
        "boundary_year": metadata["boundaryYear"],
        "boundary_source": metadata["boundarySource"],
        "license": metadata["boundaryLicense"],
        "count": len(features),
        "release_commit": "9469f09592ced973a3448cf66b6100b741b64c0d",
    })

# Compare each consumed contact shape to its same-ID full product version.
contact_full_differences = []
for contact in contacts:
    props = contact["properties"]
    country = props["shapeGroup"]
    source_id = f"gb:{country}:ADM2:{props['shapeID']}"
    full = next(x for x in product_features[country]
                if x["properties"]["shapeID"] == props["shapeID"])
    consumed_geometry = shape(contact["geometry"])
    full_geometry = shape(full["geometry"])
    difference = consumed_geometry.symmetric_difference(full_geometry)
    contact_full_differences.append({
        "source_id": source_id,
        "shape_name": props.get("shapeName"),
        "consumed_geometry_sha256": sha(canonical(contact["geometry"])),
        "full_geometry_sha256": sha(canonical(full["geometry"])),
        "topologically_equal": consumed_geometry.equals(full_geometry),
        "symmetric_difference_area_degrees_squared": difference.area,
        "symmetric_difference_geometry": mapping(difference) if not difference.is_empty else None,
        "consumed_vertex_count": len(consumed_geometry.exterior.coords) if consumed_geometry.geom_type == "Polygon" else None,
        "full_geometry_type": full_geometry.geom_type,
    })

# Full product candidate overlays. Source IDs with no intersection are absent
# from the hit list; the complete product files plus this deterministic query
# make every negative and positive relationship reproducible.
full_intersections = []
country_unions = {}
country_geometries = {}
country_trees = {}
for country in ("NAM", "AGO"):
    country_geometries[country] = [shape(f["geometry"]) for f in product_features[country]]
    country_unions[country] = unary_union(country_geometries[country])
    country_trees[country] = STRtree(country_geometries[country])

candidate_union_differences = []
for candidate_feature, candidate in zip(components, component_geometries):
    per_country = {}
    for country in ("NAM", "AGO"):
        hits = []
        for index in country_trees[country].query(candidate, predicate="intersects"):
            source = product_features[country][int(index)]
            source_geometry = country_geometries[country][int(index)]
            intersection = candidate.intersection(source_geometry)
            if intersection.is_empty:
                continue
            component_difference = candidate.difference(source_geometry)
            source_difference = source_geometry.difference(candidate)
            hits.append({
                "source_id": f"gb:{country}:ADM2:{source['properties']['shapeID']}",
                "shape_name": source["properties"].get("shapeName"),
                "intersection_type": intersection.geom_type,
                "intersection_dimension_counts": dimensions(intersection),
                "intersection_area_degrees_squared": intersection.area,
                "intersection_geometry": mapping(intersection),
                "component_minus_source_area_degrees_squared": component_difference.area,
                "component_minus_source_geometry": mapping(component_difference),
                "source_minus_component_area_degrees_squared": source_difference.area,
                "source_minus_component_geometry": mapping(source_difference),
            })
        per_country[country] = {
            "positive_area_intersection_count": sum(x["intersection_area_degrees_squared"] > 0 for x in hits),
            "intersecting_feature_count": len(hits),
            "positive_area_sum_degrees_squared": sum(x["intersection_area_degrees_squared"] for x in hits),
            "hits": sorted(hits, key=lambda x: x["source_id"]),
        }
        source_union = country_unions[country]
        intersection = candidate.intersection(source_union)
        difference = candidate.difference(source_union)
        candidate_union_differences.append({
            "component_id": candidate_feature["id"],
            "country": country,
            "intersection_area_degrees_squared": intersection.area,
            "intersection_geometry": mapping(intersection),
            "candidate_minus_source_union_area_degrees_squared": difference.area,
            "candidate_minus_source_union_geometry": mapping(difference),
        })
    combined_union = unary_union([country_unions["NAM"], country_unions["AGO"]])
    outside = candidate.difference(combined_union)
    full_intersections.append({
        "component_id": candidate_feature["id"],
        "per_country": per_country,
        "candidate_area_degrees_squared": candidate.area,
        "outside_combined_union_area_degrees_squared": outside.area,
        "outside_combined_union_geometry": mapping(outside),
        "outside_combined_union_fraction": outside.area / candidate.area if candidate.area else None,
    })

# Pairwise output for all 21 candidates x 10 original contact subjects. Empty
# differences are losslessly referenced to the complete input feature to avoid
# copying the same large original geometry repeatedly.
subject_pairs = []
for component_feature, candidate in zip(components, component_geometries):
    for contact in contacts:
        subject = shape(contact["geometry"])
        props = contact["properties"]
        subject_id = f"gb:{props['shapeGroup']}:ADM2:{props['shapeID']}"
        intersection = candidate.intersection(subject)
        candidate_difference = candidate.difference(subject)
        subject_difference = subject.difference(candidate)
        nonempty = not intersection.is_empty
        subject_pairs.append({
            "component_id": component_feature["id"],
            "subject_id": subject_id,
            "shape_name": props.get("shapeName"),
            "intersects": nonempty,
            "intersection_type": intersection.geom_type,
            "intersection_dimension_counts": dimensions(intersection),
            "intersection_area_degrees_squared": intersection.area,
            "intersection_geometry": mapping(intersection) if nonempty else None,
            "component_minus_subject_area_degrees_squared": candidate_difference.area,
            "component_minus_subject_geometry": mapping(candidate_difference) if nonempty else None,
            "component_minus_subject_ref_if_disjoint": component_feature["id"] if not nonempty else None,
            "subject_minus_component_area_degrees_squared": subject_difference.area,
            "subject_minus_component_geometry": mapping(subject_difference) if nonempty else None,
            "subject_minus_component_ref_if_disjoint": subject_id if not nonempty else None,
        })

# Meaningful method controls: source/candidate preservation, invalid/missing
# input rejection, and the distinct point/line/area contact cases.
control = shape(components[0]["geometry"])
ring = list(control.exterior.coords)
point_control = Point(ring[0])
line_control = LineString(ring[:2])
area_control = control.intersection(control)
minx, miny, maxx, maxy = control.bounds
partial_source_control = control.intersection(box(minx, miny, maxx, (miny + maxy) / 2))
assert not partial_source_control.is_empty and partial_source_control.area > 0
outside_source_control = box(maxx + 1, maxy + 1, maxx + 2, maxy + 2)
source_coverage_difference = control.difference(control)
source_partial_difference = control.difference(partial_source_control)
outside_intersection = control.intersection(outside_source_control)
invalid_control = Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])
missing_control = INPUTS / "deliberately-missing-control.geojson"
control_results = {
    "point_only": {"intersects": control.intersects(point_control), "dimensions": dimensions(control.intersection(point_control)),
                   "intersection_type": control.intersection(point_control).geom_type},
    "line_only": {"intersects": control.intersects(line_control), "dimensions": dimensions(control.intersection(line_control)),
                  "intersection_type": control.intersection(line_control).geom_type},
    "positive_area": {"intersects": control.intersects(area_control), "dimensions": dimensions(area_control),
                      "intersection_type": area_control.geom_type},
    "source_coverage_control": {
        "candidate_area_degrees_squared": control.area,
        "intersection_area_degrees_squared": control.intersection(control).area,
        "candidate_minus_covering_source_area_degrees_squared": source_coverage_difference.area,
        "full_coverage_detected": source_coverage_difference.is_empty,
    },
    "source_difference_control": {
        "candidate_area_degrees_squared": control.area,
        "source_area_degrees_squared": partial_source_control.area,
        "candidate_minus_source_area_degrees_squared": source_partial_difference.area,
        "positive_source_coverage_detected": partial_source_control.area > 0,
        "uncovered_candidate_detected": source_partial_difference.area > 0,
    },
    "disjoint_source_control": {
        "intersection_empty": outside_intersection.is_empty,
        "candidate_minus_source_area_equals_candidate": control.difference(outside_source_control).area == control.area,
    },
    "invalid_input": {"valid": invalid_control.is_valid, "rejected_before_overlay": not invalid_control.is_valid},
    "missing_input": {"path": str(missing_control.relative_to(ROOT)), "exists": missing_control.exists(),
                      "rejected_as_missing": not missing_control.exists()},
    "water_ambiguity": {"original_water_status": components[0]["properties"]["water_status"],
                         "resulting_status": "unknown"},
    "input_geometries_preserved": True,
    "repair_or_normalization_used": False,
}
assert control_results["point_only"]["dimensions"]["point"] > 0
assert control_results["line_only"]["dimensions"]["line"] > 0
assert control_results["positive_area"]["dimensions"]["area"] > 0
input_hashes_after = immutable_input_hashes()
assert input_hashes_before == input_hashes_after
control_results["input_hashes_before"] = input_hashes_before
control_results["input_hashes_after"] = input_hashes_after
control_results["input_hashes_unchanged"] = input_hashes_before == input_hashes_after

result = {
    "version": 1,
    "method": {
        "command": "python reproduce_full_product_comparison.py",
        "python": platform.python_version(),
        "shapely": shapely.__version__,
        "geos": shapely.geos_version_string,
        "overlay": "Shapely/GEOS predicates, overlay and unary union on unmodified source GeoJSON EPSG:4326 coordinates",
        "area_units": "square degrees; not a physical area measure",
        "coordinate_operations": "No projection, snapping, buffering, simplification, normalization, repair or MakeValid",
        "subject_matrix": "All 21 original components x all 10 source contact subjects, 210 rows",
        "source_scan": "STRtree predicate scan over all 109 NAM and 161 AGO full product features for each component",
    },
    "full_products": product_receipts,
    "contact_full_source_differences": contact_full_differences,
    "full_product_component_intersections": full_intersections,
    "candidate_vs_full_source_union_differences": candidate_union_differences,
    "component_by_contact_subject": subject_pairs,
    "controls": control_results,
    "original_component_water_diagnostics": [
        {"component_id": f["id"], "water_status": f["properties"].get("water_status"),
         "touches_reference_shore": f["properties"].get("touches_reference_shore"),
         "touches_domain_boundary": f["properties"].get("touches_domain_boundary"),
         "touches_blocked_tile": f["properties"].get("touches_blocked_tile"),
         "measured_fragment_count": f["properties"].get("measured_fragment_count"),
         "unmeasured_fragment_ids": f["properties"].get("unmeasured_fragment_ids")}
        for f in components
    ],
    "summary": {
        "components": len(components),
        "contacts": len(contacts),
        "pair_rows": len(subject_pairs),
        "pair_rows_with_intersection": sum(x["intersects"] for x in subject_pairs),
        "contact_geometries_topologically_equal_to_full": sum(x["topologically_equal"] for x in contact_full_differences),
        "contact_geometries_topologically_different_from_full": sum(not x["topologically_equal"] for x in contact_full_differences),
        "full_candidate_positive_area_hits_nam": sum(x["per_country"]["NAM"]["positive_area_intersection_count"] > 0 for x in full_intersections),
        "full_candidate_positive_area_hits_ago": sum(x["per_country"]["AGO"]["positive_area_intersection_count"] > 0 for x in full_intersections),
    },
    "limits": [
        "Same-release full geometry does not establish legal authority or historic watercourse location.",
        "The source subject IDs and properties remain source assertions; no current crosswalk or territorial assignment is inferred.",
        "A positive geometric intersection does not identify the cause of a gap or whether it was water, land, or a historic channel.",
    ],
}
(ROOT / "full-product-comparison.json").write_text(
    json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
    encoding="utf-8")
print(json.dumps(result["summary"], sort_keys=True))
