#!/usr/bin/env python3
"""Reproduce a coarse area-size screen for the exact 34 issue-396 subjects.

Uses a spherical authalic approximation, not the repository's ellipsoidal
measurement helper. Areas are suitable for order-of-magnitude screening only.
"""
import hashlib
import json
import math
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[4]
PACKET = ROOT / "data/regional-review/regional-review-82307d5498a4432a"
BASELINE = "7f23b59fe66c0deb57d88115092f2126d6916505"
RADIUS_KM = 6371.0071809
OBLAST_REFERENCE_KM2 = 95500.0
PREFIX = "gb:RUS:ADM2:"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def git_blob(path):
    return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{BASELINE}:{path}"])


def ring_area_km2(ring):
    """Spherical longitude-latitude integral; ring direction-independent."""
    total = 0.0
    for first, second in zip(ring, ring[1:]):
        lon1, lat1 = map(math.radians, first[:2])
        lon2, lat2 = map(math.radians, second[:2])
        delta_lon = lon2 - lon1
        while delta_lon > math.pi:
            delta_lon -= 2 * math.pi
        while delta_lon < -math.pi:
            delta_lon += 2 * math.pi
        total += delta_lon * (math.sin(lat1) + math.sin(lat2))
    return abs(total) * RADIUS_KM * RADIUS_KM / 2


def geometry_area_km2(geometry):
    coordinates = geometry["coordinates"]
    if geometry["type"] == "Polygon":
        polygons = [coordinates]
    elif geometry["type"] == "MultiPolygon":
        polygons = coordinates
    else:
        raise ValueError(f"Unsupported geometry type: {geometry['type']}")
    area = 0.0
    for rings in polygons:
        if not rings:
            raise ValueError("Empty polygon")
        area += ring_area_km2(rings[0]) - sum(ring_area_km2(hole) for hole in rings[1:])
    if area < 0:
        raise ValueError("Hole areas exceed polygon area")
    return area


issue = json.loads((PACKET / "source/issue-396-api-response.json").read_text())
match = re.search(r"```json\s*(\{.*?\})\s*```", issue["body"], re.S)
if not match:
    raise SystemExit("Issue workload JSON was not found")
scope = json.loads(match.group(1))
subject_ids = scope["member_location_ids"]
if len(subject_ids) != 34 or len(set(subject_ids)) != 34:
    raise SystemExit("Issue 396 must contain exactly 34 unique subjects")

source_path = PACKET / "source/issue-396-scoped-geoboundaries-features.geojson"
source_raw = source_path.read_bytes()
source_collection = json.loads(source_raw)
source_by_id = {PREFIX + feature["properties"]["shapeID"]: feature for feature in source_collection["features"]}
if len(source_by_id) != 34 or set(source_by_id) != set(subject_ids):
    raise SystemExit("Retained source extract does not match the exact issue scope")

parts = {}
atlas_by_id = {}
for path in ["data/geography/part-20.json", "data/geography/part-21.json"]:
    raw = git_blob(path)
    parts[path] = {"bytes": len(raw), "sha256": digest(raw)}
    for feature in json.loads(raw)["features"]:
        feature_id = feature.get("id") or feature.get("properties", {}).get("id")
        if feature_id in subject_ids:
            if feature_id in atlas_by_id:
                raise SystemExit(f"Duplicate current-main subject: {feature_id}")
            atlas_by_id[feature_id] = feature
if set(atlas_by_id) != set(subject_ids):
    raise SystemExit("Current-main records do not match the exact issue scope")

rows = []
source_total_raw = 0.0
atlas_total_raw = 0.0
for subject_id in sorted(subject_ids):
    source_feature = source_by_id[subject_id]
    atlas_feature = atlas_by_id[subject_id]
    source_area = geometry_area_km2(source_feature["geometry"])
    atlas_area = geometry_area_km2(atlas_feature["geometry"])
    source_total_raw += source_area
    atlas_total_raw += atlas_area
    rows.append({
        "subject_id": subject_id,
        "source_name": source_feature["properties"].get("shapeName"),
        "source_geometry_type": source_feature["geometry"]["type"],
        "source_area_km2": round(source_area, 3),
        "atlas_area_km2": round(atlas_area, 3),
        "atlas_to_source_area_ratio": atlas_area / source_area,
        "absolute_area_difference_km2": round(atlas_area - source_area, 3),
        "relative_area_difference": (atlas_area - source_area) / source_area,
    })

largest = max(rows, key=lambda row: row["source_area_km2"])
largest_area_delta = max(rows, key=lambda row: abs(row["relative_area_difference"]))
source_total = round(source_total_raw, 3)
atlas_total = round(atlas_total_raw, 3)
result = {
    "version": 1,
    "issue": 396,
    "subject_count": len(subject_ids),
    "evaluation_commit": BASELINE,
    "inputs": {
        "source_extract": {"path": str(source_path.relative_to(ROOT)), "bytes": len(source_raw), "sha256": digest(source_raw)},
        "atlas_parts": parts,
    },
    "method": {
        "name": "Spherical authalic longitude-latitude ring integral",
        "radius_km": RADIUS_KM,
        "ring_policy": "Absolute outer-ring area less absolute hole-ring areas; sum MultiPolygon components.",
        "units": "square kilometres",
        "source_vintage": "geoBoundaries 2017; collection metadata only",
        "atlas_vintage": "Immutable PR-base Atlas geometries",
        "province_reference_km2": OBLAST_REFERENCE_KM2,
        "province_reference_source": "source/kemerovo-area-reference.json",
        "software": "Python standard library; no external geometry package",
    },
    "results": {
        "source_total_area_km2": source_total,
        "atlas_total_area_km2": atlas_total,
        "source_total_to_rounded_province_reference": source_total / OBLAST_REFERENCE_KM2,
        "largest_feature": largest,
        "largest_feature_to_rounded_province_reference": largest["source_area_km2"] / OBLAST_REFERENCE_KM2,
        "largest_absolute_relative_source_atlas_area_difference": largest_area_delta,
        "largest_absolute_relative_source_atlas_area_difference_magnitude": abs(largest_area_delta["relative_area_difference"]),
    },
    "rows": rows,
    "limits": [
        "Authalic-sphere results are approximate and are not geodesic measurements; use only as an area-size screen.",
        "The province area reference is rounded and undated; neither it nor summed feature areas proves coverage.",
        "No polygon union, pairwise overlap/gap, boundary-distance, legal-boundary, or adjacency test was performed.",
        "A source-to-Atlas area difference does not distinguish harmless generalization from a geographic error.",
        "The source role for individual features remains unresolved; area is not a semantic tier test.",
    ],
}
out = PACKET / "findings/area-screen.json"
out.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
print(json.dumps({
    "subjects": len(rows),
    "source_total_km2": result["results"]["source_total_area_km2"],
    "atlas_total_km2": result["results"]["atlas_total_area_km2"],
    "largest_source_feature": largest,
    "largest_source_atlas_relative_difference": largest_area_delta,
    "limits": len(result["limits"]),
}, ensure_ascii=False))
