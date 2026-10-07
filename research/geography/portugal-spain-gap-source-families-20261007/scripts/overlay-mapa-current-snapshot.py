#!/usr/bin/env python3
"""Overlay the 17 captured current MAPA polygons with all scoped components."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import MultiPolygon, Polygon, shape
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "research/geography/portugal-spain-gap-source-families-20261007"
COMPONENT_FILE = PACKAGE / "inputs/selected-70-component-geometries.geojson"
MAPA_FILE = PACKAGE / "sources/mapa/target-18-geometries-4258.json"
JOIN_FILE = PACKAGE / "sources/mapa/target-contact-feature-joins.json"
OUTPUT = PACKAGE / "outputs/mapa-current-snapshot-overlays.json"
AREA_CRS = "EPSG:6933"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def signed_area(ring: list[list[float]]) -> float:
    return sum(ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1] for i in range(len(ring) - 1)) / 2


def esri_rings_to_geometry(rings: list[list[list[float]]]):
    shells = []
    holes = []
    for ring in rings:
        area = signed_area(ring)
        polygon = Polygon(ring)
        if not polygon.is_valid or polygon.area == 0:
            raise ValueError("invalid or zero-area ring; no automatic repair was applied")
        (shells if area < 0 else holes).append(polygon)
    if not shells:
        raise ValueError("Esri polygon has no clockwise exterior ring")
    hole_groups = [[] for _ in shells]
    for hole in holes:
        point = hole.representative_point()
        containers = [(shell.area, i) for i, shell in enumerate(shells) if shell.covers(point)]
        if not containers:
            raise ValueError("counterclockwise ring is not contained in an exterior")
        hole_groups[min(containers)[1]].append(list(hole.exterior.coords))
    polygons = [Polygon(shell.exterior.coords, hole_groups[i]) for i, shell in enumerate(shells)]
    geom = MultiPolygon(polygons) if len(polygons) > 1 else polygons[0]
    if not geom.is_valid:
        raise ValueError("converted Esri polygon is invalid; no automatic repair was applied")
    return geom


def main() -> None:
    components = json.loads(COMPONENT_FILE.read_text())["features"]
    mapa = json.loads(MAPA_FILE.read_text())
    joins = json.loads(JOIN_FILE.read_text())["feature_joins"]
    if len(components) != 70 or len(mapa["features"]) != 17 or len(joins) != 18:
        raise SystemExit("exact 70/17/18 inputs are required")
    spatial = mapa["spatialReference"]
    srid = spatial.get("latestWkid", spatial.get("wkid"))
    if int(srid) != 4258:
        raise SystemExit(f"unexpected MAPA source CRS: {srid}")
    source_features = []
    for feature in mapa["features"]:
        attrs = feature["attributes"]
        geom = esri_rings_to_geometry(feature["geometry"]["rings"])
        source_features.append({"objectid": attrs["objectid"], "comarca_code": attrs["co_comarca"], "province_code": attrs["co_provinc"], "comarca_name": attrs["ds_comarca"], "province_name": attrs["ds_provinc"], "geometry": geom})
    contacts_by_code = {}
    for join in joins:
        attrs = join["source_feature"]
        contacts_by_code.setdefault(attrs["co_comarca"], []).append(join["contact_id"])

    to_area = Transformer.from_crs("EPSG:4258", AREA_CRS, always_xy=True).transform
    to_mapa = Transformer.from_crs("EPSG:4326", "EPSG:4258", always_xy=True).transform
    source_projected = [transform(to_area, row["geometry"]) for row in source_features]
    tree = STRtree(source_projected)
    result_components = []
    pair_count = 0
    for feature in components:
        geom = shape(feature["geometry"])
        component = transform(to_area, transform(to_mapa, geom))
        indices = tree.query(component, predicate="intersects")
        rows = []
        candidate_geoms = []
        for index in indices:
            i = int(index)
            source = source_features[i]
            intersection_area = component.intersection(source_projected[i]).area
            candidate_geoms.append(source_projected[i])
            rows.append({
                "contact_ids": contacts_by_code.get(source["comarca_code"], []),
                "source_objectid": source["objectid"],
                "comarca_code": source["comarca_code"],
                "comarca_name": source["comarca_name"],
                "province_code": source["province_code"],
                "province_name": source["province_name"],
                "intersects": True,
                "positive_area_overlap": intersection_area > 0,
                "intersection_area_m2_equal_area": intersection_area,
                "covers_component": source_projected[i].covers(component),
                "component_area_fraction": intersection_area / component.area if component.area else None,
            })
        union = unary_union(candidate_geoms) if candidate_geoms else None
        covered_area = component.intersection(union).area if union is not None else 0.0
        fraction = covered_area / component.area if component.area else None
        result_components.append({
            "component_id": feature["id"],
            "intersecting_current_source_feature_count": len(rows),
            "positive_area_source_feature_count": sum(r["positive_area_overlap"] for r in rows),
            "current_source_union_coverage_area_m2_equal_area": covered_area,
            "current_source_union_coverage_fraction": fraction,
            "features": sorted(rows, key=lambda r: r["source_objectid"]),
        })
        pair_count += len(rows)
    positive_control = next(((row["component_id"], feature) for row in result_components for feature in row["features"] if feature["positive_area_overlap"]), None)
    negative_control = next((row for row in result_components if row["intersecting_current_source_feature_count"] == 0), None)
    if positive_control is None or negative_control is None:
        raise SystemExit("required real MAPA current-snapshot positive/negative controls unavailable")
    result = {
        "schema": "worldatlas-mapa-current-snapshot-overlay-v1",
        "component_roster_sha256": json.loads((PACKAGE / "inputs/complete-input-index.json").read_text())["scope"]["component_ids_sha256"],
        "component_geometry_sha256": sha(COMPONENT_FILE),
        "source": {"layer_url": "https://sig.mapa.gob.es/arcgis/rest/services/25830/comunComarcasAgrarias/MapServer/2", "source_layer": 2, "spatial_reference": "EPSG:4258", "feature_count": len(source_features), "target_contact_joins": len(joins), "distinct_contact_ids": len({j["contact_id"] for j in joins}), "distinct_source_objectids": len({f["objectid"] for f in source_features}), "geometry_sha256": sha(MAPA_FILE), "join_sha256": sha(JOIN_FILE), "service_metadata_sha256": sha(PACKAGE / "sources/mapa/layer-metadata.json")},
        "method": "Esri JSON rings interpreted by documented winding: clockwise exteriors, counter-clockwise holes; polygons transformed to EPSG:6933 before intersection and area measurement.",
        "area_crs": AREA_CRS,
        "component_count": len(result_components),
        "components_intersecting_any_current_feature": sum(row["intersecting_current_source_feature_count"] > 0 for row in result_components),
        "positive_area_pair_count": sum(row["positive_area_source_feature_count"] for row in result_components),
        "intersecting_pair_count": pair_count,
        "controls": {
            "positive_control": {"component_id": positive_control[0], "source_objectid": positive_control[1]["source_objectid"], "positive_area_overlap": True, "intersection_area_m2_equal_area": positive_control[1]["intersection_area_m2_equal_area"]},
            "negative_control": {"component_id": negative_control["component_id"], "intersecting_current_source_feature_count": 0},
        },
        "components": result_components,
        "limits": ["Recent current service snapshot only; original historical Atlas-imported bytes remain absent for the 18 distinct contact IDs.", "The layer metadata does not establish the geometry payload's license or a source effective date.", "This agricultural comarca administrative layer is not a physical land/water, river, ice, or ownership source.", "Geometry intersections do not establish rightful province, cause, historical boundary, or an edit."],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"features": len(source_features), "components": len(result_components), "components_intersecting": result["components_intersecting_any_current_feature"], "pairs": pair_count, "sha256": sha(OUTPUT)}))


if __name__ == "__main__":
    main()
