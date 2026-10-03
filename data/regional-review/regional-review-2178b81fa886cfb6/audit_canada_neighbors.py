#!/usr/bin/env /usr/bin/python3
"""Screen assigned Pacific counties for current Canadian county/municipality contacts."""
import json
from pathlib import Path
from osgeo import ogr, osr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ogr.UseExceptions()

def load(path):
    return json.loads(Path(path).read_text())

def bbox(geometry):
    points = []
    todo = [geometry["coordinates"]]
    while todo:
        item = todo.pop()
        if isinstance(item, list) and len(item) == 2 and isinstance(item[0], (int, float)) and isinstance(item[1], (int, float)):
            points.append((item[0], item[1]))
        elif isinstance(item, list):
            todo.extend(item)
    return min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points)

def overlap(a, b):
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])

scope = load(HERE / "scope.json")
features = {}
for part in load(ROOT / "data/world-index.json")["parts"]:
    for f in load(ROOT / "data" / part)["features"]:
        features[f["properties"]["id"]] = f
assigned = [features[i] for i in scope["member_location_ids"]]
canada = [f for f in features.values() if f["properties"].get("id", "").startswith("gb:CAN:")]
candidate_pairs = [(a, c) for a in assigned for c in canada if overlap(bbox(a["geometry"]), bbox(c["geometry"]))]

src = osr.SpatialReference(); src.ImportFromEPSG(4326); src.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
dst = osr.SpatialReference(); dst.ImportFromEPSG(5070); dst.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
transform = osr.CoordinateTransformation(src, dst)

def raw_geometry(feature):
    geom = ogr.CreateGeometryFromJson(json.dumps(feature["geometry"], separators=(",", ":")))
    geom.AssignSpatialReference(src)
    return geom

def line_length(geom):
    kind = geom.GetGeometryName().upper()
    if kind in {"LINESTRING", "LINEARRING"}:
        return geom.Length()
    if kind in {"MULTILINESTRING", "GEOMETRYCOLLECTION"}:
        return sum(line_length(geom.GetGeometryRef(i)) for i in range(geom.GetGeometryCount()))
    return 0.0

hits = []
for a, c in candidate_pairs:
    ga, gc = raw_geometry(a), raw_geometry(c)
    intersection = ga.Intersection(gc)
    projected_intersection = intersection.Clone()
    projected_intersection.Transform(transform)
    line_m = line_length(projected_intersection)
    distance_deg = ga.Distance(gc)
    overlap_deg2 = intersection.GetArea()
    if line_m > 1 or distance_deg < 1e-10 or overlap_deg2 > 0:
        ap, cp = a["properties"], c["properties"]
        hits.append({"assigned_id": ap["id"], "assigned_name": ap["name"], "assigned_source_id": ap.get("metadata", {}).get("source_id"), "assigned_vintage": ap.get("metadata", {}).get("reference_year"), "assigned_license": ap.get("metadata", {}).get("license"), "assigned_original_geometry_sha256": ap.get("metadata", {}).get("original_geometry_sha256"), "neighbor_id": cp["id"], "neighbor_name": cp["name"], "neighbor_parent_id": cp.get("parent_id"), "neighbor_source_id": cp.get("metadata", {}).get("source_id"), "neighbor_source_role": cp.get("metadata", {}).get("source_role"), "neighbor_vintage": cp.get("metadata", {}).get("reference_year"), "neighbor_license": cp.get("metadata", {}).get("license"), "neighbor_original_geometry_sha256": cp.get("metadata", {}).get("original_geometry_sha256"), "neighbor_topology_conflicts": cp.get("metadata", {}).get("topology_conflicts"), "raw_inputs_valid": {"assigned": bool(ga.IsValid()), "neighbor": bool(gc.IsValid())}, "intersection_geometry_type": intersection.GetGeometryName(), "shared_line_m": round(line_m, 3), "raw_polygon_overlap_deg2": round(overlap_deg2, 14), "raw_geometry_distance_degrees": round(distance_deg, 14), "interpretation": "Current county/municipality features share a line in the pinned current geometry; this is not bilateral international-boundary validation or a political ownership claim."})

report = {"issue": 487, "method": "BBox-screen every exact assigned current polygon against all current Canadian source-ID features, then compare candidate boundaries in temporary EPSG:5070; count linear shared boundary only (not vertex contact).", "current_scope_count": len(assigned), "canadian_current_features_screened": len(canada), "bbox_candidate_pair_count": len(candidate_pairs), "near_or_touching_pairs": hits, "limitations": ["This current-index contact screen is not a comparison of bilateral authoritative international boundary evidence.", "A point contact between different administrative tiers does not establish a shared administrative line, an inconsistency, or a political claim.", "Any future line review should use official bilateral boundary evidence and coordinate both affected scoped packets; no shared geometry was edited."]}
(HERE / "neighbor-canada-screen.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"bbox_candidates": len(candidate_pairs), "near_or_touching": len(hits)}, indent=2))
