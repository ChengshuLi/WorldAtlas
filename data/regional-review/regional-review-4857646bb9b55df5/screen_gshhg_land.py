#!/usr/bin/env python3
"""Screen the issue's location footprints against GSHHG high-resolution L1 land.

Usage: python screen_gshhg_land.py /path/to/GSHHS_f_L1.shp
The full upstream archive is not distributed in this packet; see source-receipts.json.
"""
import hashlib
import json
import sys
from pathlib import Path

import shapefile
from pyproj import Transformer
from shapely.geometry import box, shape
from shapely.ops import transform, unary_union

OUT = Path(__file__).resolve().parent
baseline = json.loads((OUT / "baseline-extract.json").read_text(encoding="utf-8"))
ids = [
    "atlas:territory:NRU",
    "gb:KIR:ADM1:97431129B36644055464690",
    "gb:KIR:ADM1:97431129B55805139245338",
]
features = {k: shape(baseline["locations"][k]["geometry"]) for k in ids}
trans = Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True).transform
project = lambda g: transform(trans, g)
features_m = {k: project(g) for k, g in features.items()}
gilbert_area = unary_union([features[ids[1]], features[ids[2]]])
gilbert_area_m = project(gilbert_area)

# Boxes cover every assigned land unit and the three adjacent Kiribati named
# groups, plus immediate oceanic neighbors for a consistency screen.
windows = [
    {"id": "gilbert-nauru", "bbox": [165.0, -5.0, 180.0, 5.0]},
    {"id": "phoenix-neighbor", "bbox": [-180.0, -5.0, -168.0, 5.0]},
    {"id": "line-neighbor", "bbox": [-162.0, 0.0, -155.0, 6.0]},
]
window_geometries = [(w["id"], box(*w["bbox"])) for w in windows]

def in_windows(bb):
    return [w["id"] for w in windows if bb[0] <= w["bbox"][2] and bb[2] >= w["bbox"][0] and bb[1] <= w["bbox"][3] and bb[3] >= w["bbox"][1]]

def roundn(x):
    return round(float(x), 8)

src = Path(sys.argv[1])
r = shapefile.Reader(str(src))
rows = []
candidate_geometries = []
for index, sr in enumerate(r.iterShapeRecords()):
    props = sr.record.as_dict()
    if props.get("level") != 1:
        continue
    bb = list(sr.shape.bbox)
    possible_windows = in_windows(bb)
    if not possible_windows:
        continue
    geom = shape(sr.shape.__geo_interface__)
    win_ids = [wid for wid, window in window_geometries if wid in possible_windows and geom.intersects(window)]
    if not win_ids:
        continue
    geom_m = project(geom)
    intersections = {}
    for ident, loc in features_m.items():
        a = geom_m.intersection(loc).area
        if a > 100:
            intersections[ident] = roundn(a / 1e6)
    area_km2 = geom_m.area / 1e6
    distances = {ident: roundn(geom_m.distance(loc) / 1000) for ident, loc in features_m.items()}
    parts = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
    candidate_geometries.append(geom)
    rows.append({
        "feature_index": index,
        "gshhg_id": props.get("id"),
        "level": props.get("level"),
        "source": props.get("source"),
        "parent_id": props.get("parent_id"),
        "sibling_id": props.get("sibling_id"),
        "source_area_km2": props.get("area"),
        "equal_area_geometry_km2": roundn(area_km2),
        "bbox": [roundn(x) for x in bb],
        "window_ids": win_ids,
        "geometry_sha256_wkb": hashlib.sha256(geom.wkb).hexdigest(),
        "vertices": len(sr.shape.points),
        "rings": len(sr.shape.parts),
        "parts": len(parts),
        "positive_land_overlap_km2_by_location": intersections,
        "distance_to_location_km": distances,
        "distance_to_gilbert_area_km": roundn(geom_m.distance(gilbert_area_m) / 1000),
        # GSHHG land are physical coastlines; they do not decide sovereignty.
    })

land_union_m = project(unary_union(candidate_geometries)) if candidate_geometries else None
overlap_rows = [x for x in rows if x["positive_land_overlap_km2_by_location"]]
nearby_unmatched = {}
for ident in ids:
    nearest = [x for x in rows if ident not in x["positive_land_overlap_km2_by_location"]]
    nearest.sort(key=lambda x: (x["distance_to_location_km"][ident], x["bbox"]))
    nearby_unmatched[ident] = nearest[:5]
summary = {
    "source": {
        "product": "GSHHG 2.3.7 high-resolution shapefile land level 1",
        "resolution": "full/highest",
        "land_polygon_count_scanned": len(r),
        "candidate_land_records_in_declared_windows": len(rows),
        "candidate_land_records_intersecting_any_assigned_location": len(overlap_rows),
        "windows": windows,
        "archive_restoration": "See source-receipts.json; extract GSHHS_shp/f/GSHHS_f_L1.shp, .shx, and .dbf from the verified official archive.",
    },
    "location_stats": {
        k: {
            "current_geometry_km2": roundn(project(features[k]).area / 1e6),
            "land_intersection_km2": roundn(features_m[k].intersection(land_union_m).area / 1e6) if land_union_m else 0,
            "bbox": [roundn(x) for x in features[k].bounds],
            "parts": len(features[k].geoms) if features[k].geom_type == "MultiPolygon" else 1,
        } for k in ids
    },
    "candidate_land_features_intersecting_assigned_locations": sorted(overlap_rows, key=lambda x: (x["window_ids"], x["bbox"])),
    "nearest_unmatched_candidate_land_by_location": {k: v[:5] for k, v in nearby_unmatched.items()},
    "uncertainty": [
        "GSHHG L1 is a generalized physical land/coastline source; it is not a legal or administrative boundary.",
        "The global source may omit or misregister very small reefs/islets and may include generalized rings or lagoons.",
        "Distance/overlap screens locate candidate land and source coverage differences only; the census atlas notes its small-island maps use visibility buffers.",
    ],
}
path = OUT / "gshhg-land-screen.json"
path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps({"feature_records": len(rows), "rows_with_overlaps": sum(bool(x["positive_land_overlap_km2_by_location"]) for x in rows), "location_stats": summary["location_stats"], "candidate_feature_count": len(rows), "output_bytes": path.stat().st_size}, indent=2))
