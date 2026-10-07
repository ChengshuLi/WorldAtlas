#!/usr/bin/env python3
"""Overlay the complete captured APA WFD river-line response on all 70 components."""

from __future__ import annotations

import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import LineString, MultiLineString, shape
from shapely.ops import transform
from shapely.strtree import STRtree


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "research/geography/portugal-spain-gap-source-families-20261007"
GEOMETRY_PATH = PACKAGE / "inputs/selected-70-component-geometries.geojson"
INPUTS = [PACKAGE / "sources/apa-wfd/full-border-envelope-page-0.xml", PACKAGE / "sources/apa-wfd/full-border-envelope-page-1.xml"]
OUTPUT = PACKAGE / "outputs/apa-wfd-line-overlays.json"
AREA_CRS = "EPSG:6933"
NS = {"wfs": "http://www.opengis.net/wfs/2.0", "gml": "http://www.opengis.net/gml/3.2"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def parse_feature(feature: ET.Element) -> tuple[dict, MultiLineString]:
    props = {}
    geometry = None
    for child in feature:
        name = local(child)
        if name == "shape":
            geometry = child.find("gml:MultiCurve", NS)
        elif name not in ("boundedBy",):
            props[name] = child.text
    if geometry is None:
        raise ValueError(f"missing MultiCurve geometry for {feature.attrib.get('{http://www.opengis.net/gml/3.2}id')}")
    lines = []
    for poslist in geometry.findall(".//gml:posList", NS):
        values = [float(x) for x in (poslist.text or "").split()]
        if len(values) < 4 or len(values) % 2:
            raise ValueError("unexpected WFS posList dimensionality")
        # The source uses EPSG:4326 GML axis order (latitude, longitude).
        lines.append(LineString([(values[i + 1], values[i]) for i in range(0, len(values), 2)]))
    if not lines:
        raise ValueError("empty APA line geometry")
    return props, MultiLineString(lines)


def main() -> None:
    source = {}
    feature_records = []
    total_bytes = 0
    for path in INPUTS:
        total_bytes += path.stat().st_size
        root = ET.parse(path).getroot()
        for member in root.findall("wfs:member", NS):
            feature = list(member)[0]
            gml_id = feature.attrib.get("{http://www.opengis.net/gml/3.2}id")
            props, geom = parse_feature(feature)
            oid = str(props.get("objectid"))
            if oid in source:
                raise SystemExit(f"duplicate APA objectid across pages: {oid}")
            source[oid] = True
            feature_records.append({"id": oid, "gml_id": gml_id, "properties": props, "geometry": geom})
    if len(feature_records) != 1428:
        raise SystemExit(f"expected 1,428 complete-envelope records, found {len(feature_records)}")
    components = json.loads(GEOMETRY_PATH.read_text())["features"]
    if len(components) != 70:
        raise SystemExit("exact 70-component geometry input is required")
    project = Transformer.from_crs("EPSG:4326", AREA_CRS, always_xy=True).transform
    projected_lines = [transform(project, rec["geometry"]) for rec in feature_records]
    tree = STRtree(projected_lines)
    results = []
    unique_hit_ids = set()
    for feature in components:
        component = transform(project, shape(feature["geometry"]))
        indices = tree.query(component, predicate="intersects")
        hits = []
        total_inside_length = 0.0
        for idx0 in indices:
            idx = int(idx0)
            rec = feature_records[idx]
            intersection = component.intersection(projected_lines[idx])
            length = intersection.length
            hits.append({"objectid": rec["id"], "gml_id": rec["gml_id"], "codigo": rec["properties"].get("codigo"), "nome": rec["properties"].get("nome"), "categoria": rec["properties"].get("categoria"), "line_length_inside_component_m": length})
            unique_hit_ids.add(rec["id"])
            total_inside_length += length
        results.append({"component_id": feature["id"], "intersecting_wfd_line_feature_count": len(hits), "combined_line_length_inside_component_m": total_inside_length, "features": sorted(hits, key=lambda x: x["objectid"])})
    positive_control = next(((row["component_id"], feature) for row in results for feature in row["features"] if feature["line_length_inside_component_m"] > 0), None)
    if positive_control is None:
        raise SystemExit("no positive APA line-intersection control found")
    negative_control = None
    for row in results:
        component = transform(project, shape(next(f["geometry"] for f in components if f["id"] == row["component_id"])))
        if not row["features"]:
            continue
        hits = {f["objectid"] for f in row["features"]}
        for i, record in enumerate(feature_records):
            if record["id"] not in hits and not component.intersects(projected_lines[i]):
                negative_control = {"component_id": row["component_id"], "objectid": record["id"], "gml_id": record["gml_id"], "intersects": False, "line_length_inside_component_m": 0.0}
                break
        if negative_control:
            break
    if negative_control is None:
        raise SystemExit("no negative APA line-intersection control found")
    catalog_path = PACKAGE / "sources/apa-wfd/license-catalog-api.json"
    catalog = json.loads(catalog_path.read_text())
    if catalog.get("license") != "notspecified" or not any("WFSServer" in r.get("url", "") for r in catalog.get("resources", [])):
        raise SystemExit("current APA WFS catalog identity/license metadata did not match the captured record")
    result = {
        "schema": "worldatlas-apa-wfd-line-overlay-v1",
        "component_roster_sha256": json.loads((PACKAGE / "inputs/complete-input-index.json").read_text())["scope"]["component_ids_sha256"],
        "geometry_sha256": hashlib.sha256(GEOMETRY_PATH.read_bytes()).hexdigest(),
        "source": {"url": "https://inspire.apambiente.pt/getogc/services/INSPIRE/AM_WaterBodyForWFD_WFDRiver/MapServer/WFSServer", "type": "INSPIRE_AM_WaterBodyForWFD_WFDRiver:AM.WaterBodyForWFD", "srs": "EPSG:4326; GML axis order lat,lon converted to conventional x=lon,y=lat", "captured_features": len(feature_records), "captured_feature_xml_bytes": total_bytes, "captured_pages": [{"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size, "sha256": sha(p)} for p in INPUTS], "page_2_exhaustion_sha256": sha(PACKAGE / "sources/apa-wfd/full-border-envelope-page-2-exhaustion.xml"), "second_hit_count_sha256": sha(PACKAGE / "sources/apa-wfd/full-border-envelope-second-hits.xml"), "service_capabilities": {"path": str((PACKAGE / "sources/apa-wfd/capabilities.xml").relative_to(ROOT)), "sha256": sha(PACKAGE / "sources/apa-wfd/capabilities.xml"), "fees": "Sem restrições", "access_constraints": "Sem restrições"}, "feature_schema": {"path": str((PACKAGE / "sources/apa-wfd/schema.xsd").relative_to(ROOT)), "sha256": sha(PACKAGE / "sources/apa-wfd/schema.xsd")}, "reuse_terms": {"catalog_record_id": catalog.get("id"), "catalog_last_update": catalog.get("last_update"), "catalog_license": catalog.get("license"), "catalog_api_path": str(catalog_path.relative_to(ROOT)), "catalog_api_sha256": sha(catalog_path), "interpretation": "Current machine-readable catalog says license not specified; WFS capability access constraints are not treated as a reuse license."}},
        "area_crs_for_length": AREA_CRS,
        "component_count": len(results),
        "components_with_any_line_intersection": sum(r["intersecting_wfd_line_feature_count"] > 0 for r in results),
        "distinct_wfd_features_intersecting_any_component": len(unique_hit_ids),
        "controls": {
            "positive_control": {"component_id": positive_control[0], "objectid": positive_control[1]["objectid"], "gml_id": positive_control[1]["gml_id"], "intersects": True, "line_length_inside_component_m": positive_control[1]["line_length_inside_component_m"]},
            "negative_control": negative_control,
        },
        "components": results,
        "limits": ["APA WFD records are river water-body planning lines (2015–2021 context), not shoreline polygons, wetted widths, observed 2024 water, or a complete land/water source.", "A line intersection is not an area or water-status conclusion. No intersection is not evidence of dry land.", "Separate WFS pages and hit-count requests were not transactional; source row count closure is only conditional on IDs and captured exhaustion response.", "No result establishes owner, rightful province, cause, historical boundary, or an edit."],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"features": len(feature_records), "components": len(results), "components_with_line_intersection": result["components_with_any_line_intersection"], "distinct_features_hit": len(unique_hit_ids), "sha256": sha(OUTPUT)}))


if __name__ == "__main__":
    main()
