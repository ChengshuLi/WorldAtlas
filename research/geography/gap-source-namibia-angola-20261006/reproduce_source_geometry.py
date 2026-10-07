#!/usr/bin/env python3
"""Reproduce custody checks and planar overlays for the Namibia–Angola gap family."""
import gzip
import hashlib
import json
import subprocess
from pathlib import Path

from shapely.geometry import mapping, shape
from shapely.ops import unary_union
from shapely.strtree import STRtree


ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "inputs"
SOURCE = ROOT / "sources"
REPO = ROOT.parents[2]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


def read_geojson(path):
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob(commit, path):
    return subprocess.check_output(
        ["git", "show", f"{commit}:{path}"], cwd=REPO)


def dimension_counts(geometry):
    if geometry.is_empty:
        return {"area": 0, "line": 0, "point": 0}
    kind = geometry.geom_type
    if kind in ("Polygon", "MultiPolygon"):
        return {"area": 1, "line": 0, "point": 0}
    if kind in ("LineString", "LinearRing", "MultiLineString"):
        return {"area": 0, "line": 1, "point": 0}
    if kind in ("Point", "MultiPoint"):
        return {"area": 0, "line": 0, "point": 1}
    result = {"area": 0, "line": 0, "point": 0}
    for part in getattr(geometry, "geoms", []):
        for key, value in dimension_counts(part).items():
            result[key] += value
    return result


bindings = read_geojson(INPUT / "input-bindings.json")
components = read_geojson(INPUT / "original-components.geojson")["features"]
contacts = read_geojson(INPUT / "source-contact-features.geojson")["features"]
assert len(components) == bindings["component_count"] == 21
assert len(contacts) == len(bindings["contacts"]) == 10

component_bindings = {row["id"]: row for row in bindings["component_features"]}
contact_bindings = {row["source_id"]: row for row in bindings["contacts"]}
assert set(component_bindings) == {feature["id"] for feature in components}

# Re-read every issue-listed ordinary whole-file pin from its immutable commit.
whole_input_pins = json.loads((INPUT / "whole-input-pins.json").read_text())
whole_pin_checks = []
for pin in whole_input_pins:
    raw = git_blob(pin["commit"], pin["path"])
    assert sha(raw) == pin["sha256"]
    if pin.get("bytes") is not None:
        assert len(raw) == pin["bytes"]
    whole_pin_checks.append({
        "commit": pin["commit"],
        "path": pin["path"],
        "observed_bytes": len(raw),
        "observed_sha256": sha(raw),
        "expected_bytes": pin.get("bytes"),
        "expected_sha256": pin["sha256"],
        "verified": True,
    })

# Verify complete consumed products from their content-addressed repository capsules.
source_features = {}
source_receipts = []
for country in ("NAM", "AGO"):
    key = "gb:" + country + ":ADM2"
    descriptor = next(x for x in bindings["contact_source_products"]["whole_original_source_capsules"]
                      if x["registry_key"] == key)
    capsule = SOURCE / ("gb-" + country + "-ADM2-000.bin.gz")
    encoded = capsule.read_bytes()
    pinned_encoded = git_blob(descriptor["commit"], descriptor["encoded_path"])
    assert pinned_encoded == encoded
    assert len(encoded) == descriptor["encoded_bytes"]
    assert sha(encoded) == descriptor["encoded_sha256"]
    raw = gzip.decompress(encoded)
    assert len(raw) == descriptor["raw_bytes"]
    assert sha(raw) == descriptor["raw_sha256"]
    collection = json.loads(raw)
    features = collection["features"]
    assert len(features) == descriptor["feature_count"]
    by_id = {feature["properties"]["shapeID"]: feature for feature in features}
    assert len(by_id) == len(features)
    source_features[country] = features
    source_receipts.append({
        "registry_key": key,
        "capsule_path": "sources/" + capsule.name,
        "encoded_bytes": len(encoded),
        "encoded_sha256": sha(encoded),
        "decoded_bytes": len(raw),
        "decoded_sha256": sha(raw),
        "feature_count": len(features),
        "represented_year_claim": descriptor["represented_year_claim"],
        "recorded_consumed_url": descriptor["recorded_consumed_url"],
        "recorded_license": descriptor["recorded_license"],
    })

# Each complete contact feature must be identical to its row in the whole product.
contact_checks = []
seen_contacts = set()
for feature in contacts:
    props = feature["properties"]
    country = props["shapeGroup"]
    source_id = f"gb:{country}:ADM2:{props['shapeID']}"
    expected = contact_bindings[source_id]
    found = next(x for x in source_features[country]
                 if x["properties"]["shapeID"] == props["shapeID"])
    feature_hash = sha(canonical(feature))
    geometry_hash = sha(canonical(feature["geometry"]))
    assert canonical(feature) == canonical(found)
    assert feature_hash == expected["canonical_feature_sha256"]
    assert geometry_hash == expected["geometry_sha256"]
    seen_contacts.add(source_id)
    contact_checks.append({
        "source_id": source_id,
        "shapeName": props.get("shapeName"),
        "canonical_feature_sha256": feature_hash,
        "geometry_sha256": geometry_hash,
        "whole_product_feature_equal": True,
    })
assert seen_contacts == set(contact_bindings)

# Verify each candidate against its content-addressed original ordinary payload.
payload_proofs = []
candidate_lookup = {}
for alias in bindings["component_source_aliases"]:
    # Resolve from the repository checkout, independent of current process cwd.
    repo = ROOT.parents[2]
    encoded = git_blob(alias["custody_commit"], alias["actual_payload_path"])
    assert len(encoded) == alias["encoded_bytes"]
    assert sha(encoded) == alias["encoded_sha256"]
    raw = gzip.decompress(encoded)
    assert len(raw) == alias["decoded_bytes"]
    assert sha(raw) == alias["decoded_sha256"]
    rows = json.loads(raw)["features"]
    for row in rows:
        if row["id"] in alias["component_ids"]:
            candidate_lookup[row["id"]] = row
    payload_proofs.append({
        "logical_original_path": alias["logical_original_path"],
        "custody_commit": alias["custody_commit"],
        "actual_payload_path": alias["actual_payload_path"],
        "encoded_bytes": len(encoded),
        "encoded_sha256": sha(encoded),
        "decoded_bytes": len(raw),
        "decoded_sha256": sha(raw),
        "component_ids": alias["component_ids"],
    })
assert set(candidate_lookup) == set(component_bindings)

candidate_checks = []
for feature in components:
    expected = component_bindings[feature["id"]]
    source_feature = candidate_lookup[feature["id"]]
    canonical_hash = sha(canonical(feature))
    geometry_hash = sha(canonical(feature["geometry"]))
    assert canonical(feature) == canonical(source_feature)
    assert canonical_hash == expected["canonical_feature_sha256"]
    assert geometry_hash == expected["geometry_sha256"]
    assert feature["properties"]["fragment_bindings"] == expected["fragment_bindings"]
    properties = feature["properties"]
    candidate_checks.append({
        "component_id": feature["id"],
        "canonical_feature_sha256": canonical_hash,
        "geometry_sha256": geometry_hash,
        "fragment_bindings": expected["fragment_bindings"],
        "ordinary_payload_feature_equal": True,
        "valid": shape(feature["geometry"]).is_valid,
        "source_diagnostics": {
            name: properties.get(name) for name in (
                "administrative_assignment", "water_status", "touches_reference_shore",
                "touches_domain_boundary", "touches_blocked_tile", "dateline_connected",
                "positive_area_input_overlap", "measured_fragment_count",
                "measured_fragment_area_sum_m2", "unmeasured_fragment_ids",
                "diagnostic_nearby_locations",
            )
        },
    })

# Unmodified, planar longitude/latitude overlay. Areas are degrees squared; no
# projection, snapping, buffering, repair, or administrative assignment occurs.
source_geometries = {
    country: [shape(feature["geometry"]) for feature in features]
    for country, features in source_features.items()
}
source_trees = {country: STRtree(geometries)
                for country, geometries in source_geometries.items()}
source_unions = {country: unary_union(geometries)
                 for country, geometries in source_geometries.items()}
combined_union = unary_union([source_unions["NAM"], source_unions["AGO"]])
source_intersections = []
for feature in components:
    candidate = shape(feature["geometry"])
    intersections = []
    per_country = {}
    for country in ("NAM", "AGO"):
        indices = source_trees[country].query(candidate, predicate="intersects")
        hits = []
        for index in indices:
            source_feature = source_features[country][int(index)]
            source_geometry = source_geometries[country][int(index)]
            intersection = candidate.intersection(source_geometry)
            if intersection.is_empty:
                continue
            dimensions = dimension_counts(intersection)
            hit = {
                "source_id": f"gb:{country}:ADM2:{source_feature['properties']['shapeID']}",
                "shapeName": source_feature["properties"].get("shapeName"),
                "intersection_type": intersection.geom_type,
                "area_degrees_squared": intersection.area,
                "has_positive_area": intersection.area > 0,
                "dimension_counts": dimensions,
                "intersection_geometry": mapping(intersection),
                "candidate_minus_source_area_degrees_squared": candidate.difference(source_geometry).area,
                "candidate_minus_source_geometry": mapping(candidate.difference(source_geometry)) if not candidate.difference(source_geometry).is_empty else None,
                "source_minus_candidate_area_degrees_squared": source_geometry.difference(candidate).area,
                "source_minus_candidate_geometry": mapping(source_geometry.difference(candidate)) if not source_geometry.difference(candidate).is_empty else None,
            }
            hits.append(hit)
            intersections.append({"country": country, **hit})
        per_country[country] = {
            "intersecting_source_feature_count": len(hits),
            "positive_area_intersection_count": sum(h["has_positive_area"] for h in hits),
            "positive_area_intersection_sum_degrees_squared": sum(
                h["area_degrees_squared"] for h in hits),
            "source_ids": sorted(h["source_id"] for h in hits),
        }
    outside = candidate.difference(combined_union)
    source_intersections.append({
        "component_id": feature["id"],
        "candidate_area_degrees_squared": candidate.area,
        "per_country": per_country,
        "intersections": sorted(intersections, key=lambda x: (x["country"], x["source_id"])),
        "outside_union_area_degrees_squared": outside.area,
        "outside_union_fraction": outside.area / candidate.area if candidate.area else None,
        "outside_union_geometry": mapping(outside) if not outside.is_empty else None,
        "covered_by_combined_source_union": candidate.covered_by(combined_union),
    })

output = {
    "version": 1,
    "method": {
        "overlay": "Shapely GEOS predicates/intersections and unary union on unmodified EPSG:4326 coordinates",
        "area_units": "square degrees; not suitable as physical area",
        "prohibited_operations_used": [],
        "dimensions": "positive area means polygonal intersection; line/point dimensions retained per hit",
        "assignment_or_authority_inference": False,
    },
    "source_products": source_receipts,
    "whole_input_pin_checks": whole_pin_checks,
    "source_contact_checks": sorted(contact_checks, key=lambda x: x["source_id"]),
    "ordinary_component_payloads": payload_proofs,
    "component_checks": candidate_checks,
    "component_source_intersections": source_intersections,
    "summary": {
        "candidate_count": len(components),
        "namibia_feature_count": len(source_features["NAM"]),
        "angola_feature_count": len(source_features["AGO"]),
        "candidate_count_intersecting_namibia_by_positive_area": sum(
            x["per_country"]["NAM"]["positive_area_intersection_count"] > 0
            for x in source_intersections),
        "candidate_count_intersecting_angola_by_positive_area": sum(
            x["per_country"]["AGO"]["positive_area_intersection_count"] > 0
            for x in source_intersections),
        "candidate_count_covered_by_combined_source_union": sum(
            x["covered_by_combined_source_union"] for x in source_intersections),
    },
    "limits": [
        "The consumed products are simplified ADM2 sources labeled 2007/2018 and are not exact physical shorelines or boundary authority.",
        "Area measures are unprojected square degrees.",
        "Overlay intersections cannot distinguish source-processing error from historical water, ice, or authoritative boundary placement.",
        "No geometry assignment, repair, or legal conclusion is made.",
    ],
}
(ROOT / "source-geometry-comparison.json").write_text(
    json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
    encoding="utf-8")
print(json.dumps(output["summary"], sort_keys=True))
