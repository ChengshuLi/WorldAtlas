#!/usr/bin/env python3
"""Reproduce bounded source-comparison diagnostics for WorldAtlas issue #1061.

No network access. Reads retained NOAA CUSP and OSM extracts plus pinned Atlas
baseline, then writes one deterministic JSON result beside this script.
"""
from __future__ import annotations
import json
import platform
import io
import zipfile
from collections import Counter
from pathlib import Path

import shapefile
from shapely.geometry import LineString, Point, Polygon, shape as geo_shape, box
from shapely import __version__ as shapely_version
from shapely.ops import polygonize, unary_union
import pyproj

from evidence.geometry import land_area_m2, transform_point

ROOT = Path(__file__).resolve().parent
SUBJECTS = {
    "UMI-5171": ("Baker Island", (-176.53, 0.16, -176.43, 0.24)),
    "UMI-5172": ("Howland Island", (-176.66, 0.76, -176.58, 0.85)),
    "UMI-5173": ("Jarvis Island", (-160.06, -0.42, -159.94, -0.32)),
    "UMI-5178": ("Palmyra Atoll", (-162.13, 5.84, -162.03, 5.92)),
}
EXPECTED = {"UMI-5171", "UMI-5172", "UMI-5173", "UMI-5178"}


def area(g):
    return land_area_m2(g) if not g.is_empty and g.geom_type in ("Polygon", "MultiPolygon") else 0.0


def line_parts(shp):
    cuts = list(shp.parts) + [len(shp.points)]
    for a, b in zip(cuts, cuts[1:]):
        pts = shp.points[a:b]
        if len(pts) >= 2:
            yield LineString(pts)


def polygonized(lines):
    lines = [x for x in lines if x.length]
    if not lines:
        return []
    return [p for p in polygonize(unary_union(lines)) if p.is_valid and p.area > 0]


def bbox(g):
    return [round(float(x), 9) for x in g.bounds]


def inspect_atlas():
    path = ROOT.parents[2] / "data/geography/part-28.json"
    hierarchy_path = ROOT.parents[2] / "data/hierarchy.json"
    # ROOT parents: regional-review, data, work.
    obj = json.loads(path.read_text())
    features = {f["properties"]["id"]: f for f in obj["features"]
                if f.get("properties", {}).get("id") in EXPECTED}
    if set(features) != EXPECTED:
        raise AssertionError(f"Subject inventory mismatch: {sorted(features)}")
    hierarchy = {n["id"]: n for n in json.loads(hierarchy_path.read_text())}
    geometries, context = {}, {}
    for key in sorted(EXPECTED):
        feature = features[key]
        props = feature["properties"]
        parent_id = props.get("parent_id")
        parent = hierarchy.get(parent_id)
        metadata = props.get("metadata", {})
        area_id = parent.get("parent_id") if parent else None
        area = hierarchy.get(area_id)
        if props.get("reference_owner") != "United States Minor Outlying Islands" or not parent or not area:
            raise AssertionError(f"Unexpected ownership/geographic parent for {key}")
        geometries[key] = geo_shape(feature["geometry"])
        context[key] = {"id": key, "name": props["name"], "reference_owner": props["reference_owner"],
                        "reference_owner_id": metadata.get("reference_owner_id"),
                        "geographic_parent_id": parent_id, "geographic_parent_name": parent["name"],
                        "geographic_parent_level": parent["level"],
                        "physical_group_id": area_id, "physical_group_name": area["name"],
                        "physical_group_level": area["level"]}
    return geometries, context


def inspect_cusp():
    path = ROOT / "sources/noaa-ngs/CUSP-Pacific_Islands.zip"
    reader = shapefile.Reader(str(path))
    rows = list(reader.iterShapeRecords())
    results = {}
    for sid, (name, ext) in SUBJECTS.items():
        region = box(*ext)
        selected = [r for r in rows if r.shape.shapeType != shapefile.NULL
                    and box(*r.shape.bbox).intersects(region)]
        natural = [r for r in selected if r.record["ATTRIBUTE"].startswith("Natural.Mean High Water")]
        lines = [part for r in natural for part in line_parts(r.shape)]
        polys = polygonized(lines)
        footprint = unary_union(polys) if polys else Polygon()
        dates = Counter(r.record["SRC_DATE"] for r in natural)
        attrs = Counter(r.record["ATTRIBUTE"] for r in selected)
        src_ids = Counter(r.record["SOURCE_ID"] or "(blank)" for r in natural)
        results[sid] = {
            "name": name,
            "feature_records_intersecting_site_window": len(selected),
            "natural_mhw_line_records_intersecting_site_window": len(natural),
            "source_dates": dict(sorted(dates.items())),
            "source_ids": dict(sorted(src_ids.items())),
            "attributes": dict(sorted(attrs.items())),
            "mhw_line_part_count": len(lines),
            "polygonized_ring_component_count_diagnostic_only": len(polys),
            "polygonized_land_area_m2_diagnostic": round(area(footprint), 3),
            "mhw_extent_lonlat": bbox(unary_union(lines)) if lines else None,
            "footprint_geometry": footprint,
        }
    return results


def inspect_project_archives():
    codes = {"UMI-5171": "UM0502", "UMI-5172": "UM0503",
             "UMI-5173": "UM0504", "UMI-5178": "UM0501"}
    results = {}
    for sid, (name, ext) in SUBJECTS.items():
        code = codes[sid]
        path = ROOT / f"sources/noaa-ngs/{code}.zip"
        with zipfile.ZipFile(path) as archive:
            reader = shapefile.Reader(
                shp=io.BytesIO(archive.read("softcopyl1.shp")),
                shx=io.BytesIO(archive.read("softcopyl1.shx")),
                dbf=io.BytesIO(archive.read("softcopyl1.dbf")))
            region = box(*ext)
            selected = [r for r in reader.iterShapeRecords()
                        if r.record["CLASS"] == "SHORELINE"
                        and r.record["ATTRIBUTE"].startswith("Natural.Mean High Water")
                        and box(*r.shape.bbox).intersects(region)]
        lines = [part for r in selected for part in line_parts(r.shape)]
        polys = polygonized(lines)
        footprint = unary_union(polys) if polys else Polygon()
        dates = Counter(r.record["SRC_DATE"] for r in selected)
        results[sid] = {"project_code": code, "natural_mhw_records": len(selected),
                        "source_dates": dict(sorted(dates.items())),
                        "line_part_count": len(lines),
                        "polygonized_rings_diagnostic_only": len(polys),
                        "polygonized_area_m2_diagnostic": round(area(footprint), 3),
                        "extent_lonlat": bbox(unary_union(lines)) if lines else None,
                        "footprint_geometry": footprint}
    return results


def inspect_osm():
    data = json.loads((ROOT / "sources/openstreetmap-overpass-20261005.json").read_text())
    ways = {e["id"]: e for e in data["elements"] if e["type"] == "way"}
    nodes = [e for e in data["elements"] if e["type"] == "node"]
    relations = [e for e in data["elements"] if e["type"] == "relation"]
    result = {}
    for sid, (name, ext) in SUBJECTS.items():
        region = box(*ext)
        candidates, coast = [], []
        named_nodes = []
        for way in ways.values():
            tags = way.get("tags", {})
            coords = way.get("geometry", [])
            if len(coords) < 2:
                continue
            geom = LineString([(p["lon"], p["lat"]) for p in coords])
            if not geom.intersects(region):
                continue
            if (tags.get("place") in {"island", "islet", "atoll"}
                    or tags.get("natural") in {"island", "islet", "atoll"}):
                candidates.append(way)
            if tags.get("natural") == "coastline":
                coast.append(geom)
        for node in nodes:
            tags = node.get("tags", {})
            if (tags.get("place") in {"island", "islet"}
                    and region.covers(Point(node["lon"], node["lat"]))):
                named_nodes.append({"id": node["id"], "name": tags.get("name", ""),
                                    "version": node.get("version"), "timestamp": node.get("timestamp")})
        named_relations = [
            {"id": rel["id"], "name": rel.get("tags", {}).get("name", ""),
             "version": rel.get("version"), "timestamp": rel.get("timestamp"),
             "member_way_ids": [m.get("ref") for m in rel.get("members", []) if m.get("type") == "way"]}
            for rel in relations if rel.get("tags", {}).get("place") in {"island", "islet", "atoll"}
            and any(m.get("type") == "way" and m.get("ref") in ways
                    and LineString([(p["lon"], p["lat"]) for p in ways[m["ref"]].get("geometry", [])]).intersects(region)
                    for m in rel.get("members", []))]
        polys = polygonized(coast)
        footprint = unary_union(polys) if polys else Polygon()
        result[sid] = {
            "name": name,
            "named_way_count_screen_only": len(candidates),
            "named_way_ids": sorted(w["id"] for w in candidates),
            "named_nodes": sorted(named_nodes, key=lambda x: x["id"]),
            "named_node_count_screen_only": len(named_nodes),
            "named_relations": sorted(named_relations, key=lambda x: x["id"]),
            "named_way_objects": [{"id": w["id"], "name": w.get("tags", {}).get("name", ""),
                                   "version": w.get("version"), "timestamp": w.get("timestamp")}
                                  for w in sorted(candidates, key=lambda x: x["id"])],
            "coastline_way_count_screen_only": len(coast),
            "polygonized_coastline_components_diagnostic_only": len(polys),
            "polygonized_coastline_area_m2_diagnostic": round(area(footprint), 3),
            "footprint_geometry": footprint,
        }
    return result


def public_result(private, archive, atlas, osm, context):
    out = {}
    for sid, (name, _) in SUBJECTS.items():
        a = atlas[sid]
        c = private[sid]["footprint_geometry"]
        original = archive[sid]["footprint_geometry"]
        o = osm[sid]["footprint_geometry"]
        cmp = {}
        for label, g in (("noaa_cusp", c), ("osm", o)):
            overlap = area(a.intersection(g)) if not g.is_empty else 0.0
            denom = area(g)
            union = area(a.union(g)) if not g.is_empty else area(a)
            cmp[label] = {
                "atlas_area_m2": round(area(a), 3),
                "source_area_m2": round(denom, 3),
                "intersection_area_m2": round(overlap, 3),
                "source_coverage_by_atlas_fraction": round(overlap / denom, 9) if denom else None,
                "intersection_over_union": round(overlap / union, 9) if union else None,
            }
        cpub = {k: v for k, v in private[sid].items() if k != "footprint_geometry"}
        apub = {k: v for k, v in archive[sid].items() if k != "footprint_geometry"}
        opub = {k: v for k, v in osm[sid].items()
                if k not in {"footprint_geometry", "_named_node_coordinates"}}
        archive_overlap = area(c.intersection(original)) if not c.is_empty and not original.is_empty else 0.0
        archive_area = area(original)
        out[sid] = {"subject_context": context[sid], "current_atlas_geometry_bbox": bbox(a),
                    "noaa_project_archive": apub,
                    "noaa_cusp_vs_project_archive": {
                        "project_area_m2": round(archive_area, 3),
                        "cusp_area_m2": round(area(c), 3),
                        "intersection_area_m2": round(archive_overlap, 3),
                        "project_area_covered_by_cusp_fraction": round(archive_overlap / archive_area, 9) if archive_area else None},
                    "noaa_cusp": cpub,
                    "openstreetmap_screen": opub, "area_overlay_diagnostics": cmp}
        if sid == "UMI-5178":
            land = private[sid]["footprint_geometry"]
            label_matches = [
                {**node, "inside_polygonized_cusp_land_diagnostic": bool(
                    land.covers(Point(node["lon"], node["lat"]))) if not land.is_empty else False}
                for node in osm[sid]["_named_node_coordinates"]
            ]
            out[sid]["osm_named_point_to_noaa_screen"] = {
                "inside_polygonized_cusp_count_diagnostic": sum(
                    row["inside_polygonized_cusp_land_diagnostic"] for row in label_matches),
                "outside_polygonized_cusp_names_screen_only": [row["name"] for row in label_matches
                    if not row["inside_polygonized_cusp_land_diagnostic"]],
                "labels": label_matches,
            }
    return out


def main():
    atlas, subject_context = inspect_atlas()
    cusp = inspect_cusp()
    archive = inspect_project_archives()
    osm = inspect_osm()
    # Positive/negative controls exercise polygonization and ellipsoidal area.
    ctrl = Polygon([(0, 0), (0.01, 0), (0.01, 0.01), (0, 0.01), (0, 0)])
    assert area(ctrl) > 1_000_000
    assert polygonized([LineString([(0, 0), (1, 0)]), LineString([(1, 0), (1, 1)]),
                        LineString([(1, 1), (0, 1)]), LineString([(0, 1), (0, 0)])])
    assert not polygonized([LineString([(0, 0), (1, 0)]), LineString([(1, 0), (1, 1)])])
    osm_raw = json.loads((ROOT / "sources/openstreetmap-overpass-20261005.json").read_text())
    # Keep node coordinates in the geometry join output only; OSM identity tags
    # remain available in the retained licensed raw extract.
    raw_nodes = {e["id"]: e for e in osm_raw["elements"] if e["type"] == "node"}
    for sid in osm:
        osm[sid]["_named_node_coordinates"] = [
            {"id": n["id"], "name": n["name"], "lon": raw_nodes[n["id"]]["lon"],
             "lat": raw_nodes[n["id"]]["lat"], "version": n["version"], "timestamp": n["timestamp"]}
            for n in osm[sid]["named_nodes"]]
    result = {
        "version": 1,
        "purpose": "Diagnostic source coverage comparison only; not a completeness or boundary certification",
        "baseline_commit": "947b991690a5720b48b9a664b34cba3f5e4a515d",
        "software": {"python": platform.python_version(), "shapely": shapely_version,
                     "pyproj": pyproj.__version__, "pyshp": shapefile.__version__},
        "subject_ids": sorted(EXPECTED),
        "method": {
            "geometry_helper": "worldatlas-evidence-geometry-v1",
            "axis_order": "longitude-latitude", "crs": "EPSG:4326",
            "area_method": "WGS84 straight-source-edge ellipsoidal integral",
            "area_units": "m2",
            "line_method": "select natural mean-high-water line records in fixed per-site windows, unary-union/node, polygonize; retain only valid positive-area polygons; no implicit geometry repair",
            "overlay_limit": "polygonized line interiors depend on source line closure/connectivity; line and polygon component counts do not establish feature completeness",
        },
        "controls": {
            "positive": "Known 0.01-degree WGS84 square has positive area; four-edge ring polygonizes.",
            "negative": "Open two-edge line does not polygonize.",
            "status": "passed",
        },
        "sites": public_result(cusp, archive, atlas, osm, subject_context),
        "uncertainty": [
            "NOAA CUSP is a regional best-available product, not guaranteed continuous; source rows at these remote sites may retain old vintages.",
            "Polygonizing shoreline lines is a coverage diagnostic, not proof of all dry land, islets or lagoons.",
            "OpenStreetMap is community-maintained and subject to ODbL; it is an independent screen, not authoritative truth.",
            "FWS public descriptive islet counts conflict across vintages and do not provide a complete named roster or reusable vertices.",
            "Refuge and monument boundaries include extensive submerged lands/waters and are not territorial dry-land outlines.",
        ],
    }
    validation = ROOT / "validation"
    validation.mkdir(exist_ok=True)
    (validation / "positive-control.json").write_text(json.dumps({
        "method_id": "site-outline-comparison", "kind": "positive-control", "outcome": "passed",
        "known_square_area_m2": round(area(ctrl), 3), "closed_ring_polygonized": True,
        "longitude_latitude_web_mercator_control": [round(x, 6) for x in transform_point(10, 45, "EPSG:3857")]
    }, sort_keys=True, separators=(",", ":")) + "\n")
    (validation / "negative-control.json").write_text(json.dumps({
        "method_id": "site-outline-comparison", "kind": "negative-control", "outcome": "passed",
        "open_two_edge_line_polygon_count": 0
    }, sort_keys=True, separators=(",", ":")) + "\n")
    output = ROOT / "results.json"
    output.write_text(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n")
    print(output)


if __name__ == "__main__":
    main()
