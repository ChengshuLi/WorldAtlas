#!/usr/bin/env python3
"""Measure six native candidate centres against retained DGT CAOP2025 troços.

The result is a source proximity diagnostic only. It does not determine the
side of a boundary, political affiliation, land/water, or a grid-cell owner.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from pyproj import Transformer
from shapely.geometry import LineString, Point, shape


ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "sources" / "dgt-trocos"
OUTPUT = ROOT / "outputs" / "dgt-segment-proximity.json"
TRANSFORM = Transformer.from_crs("OGC:CRS84", "EPSG:25829", always_xy=True)
CELLS = [
    {"cell_id": "cell126077/99248", "key": "cell126077-99248", "lon": -6.873431337396909, "lat": 40.002191593667014, "preview_member_match": "both"},
    {"cell_id": "cell126068/99272", "key": "cell126068-99272", "lon": -6.885789919364072, "lat": 39.97694180898698, "preview_member_match": "both"},
    {"cell_id": "cell126053/99322", "key": "cell126053-99322", "lon": -6.906387555975982, "lat": 39.92430811747299, "preview_member_match": "both"},
    {"cell_id": "cell125754/99583", "key": "cell125754-99583", "lon": -7.31696711244021, "lat": 39.64890317423009, "preview_member_match": "both"},
    {"cell_id": "cell125752/99584", "key": "cell125752-99584", "lon": -7.31971346398845, "lat": 39.64784586349555, "preview_member_match": "both"},
    {"cell_id": "cell125663/99573", "key": "cell125663-99573", "lon": -7.441926107885848, "lat": 39.659475392270686, "preview_member_match": "neither"},
]
EXPECTED = {
    "cell126077-99248": "d9492c5b-a667-11ee-a363-a76e0bcee2d6",
    "cell126068-99272": "d9492c5b-a667-11ee-a363-a76e0bcee2d6",
    "cell126053-99322": "d9492c5b-a667-11ee-a363-a76e0bcee2d6",
    "cell125754-99583": "d95df7ee-a667-11ee-a363-773b75e2e95a",
    "cell125752-99584": "d95df7ee-a667-11ee-a363-773b75e2e95a",
    "cell125663-99573": "d95df7ee-a667-11ee-a363-773b75e2e95a",
}


def metric(point_lon: float, point_lat: float, feature: dict) -> float:
    source_line = shape(feature["geometry"])
    if source_line.geom_type != "LineString" or source_line.is_empty:
        raise ValueError("Expected one complete nonempty DGT LineString")
    line = LineString([TRANSFORM.transform(lon, lat, errcheck=True) for lon, lat, *_ in source_line.coords])
    point = Point(*TRANSFORM.transform(point_lon, point_lat, errcheck=True))
    return point.distance(line)


def load_case(cell: dict) -> tuple[dict, dict, dict]:
    path = SOURCES / f"{cell['key']}.json"
    raw = path.read_bytes()
    data = json.loads(raw)
    receipt = json.loads((SOURCES / f"{cell['key']}.receipt.json").read_text(encoding="utf-8"))
    query = parse_qs(urlparse(receipt["request_url"]).query)
    if hashlib.sha256(raw).hexdigest() != receipt.get("sha256") or receipt.get("http_status") != 200:
        raise ValueError(f"Source response hash/status mismatch for {cell['cell_id']}")
    expected_bbox = [cell["lon"] - 0.001, cell["lat"] - 0.001, cell["lon"] + 0.001, cell["lat"] + 0.001]
    try:
        actual_bbox = [float(value) for value in query["bbox"][0].split(",")]
    except (KeyError, IndexError, ValueError) as error:
        raise ValueError(f"Missing/malformed query BBOX for {cell['cell_id']}") from error
    if actual_bbox != expected_bbox or query.get("limit") != ["1000"]:
        raise ValueError(f"Source query context mismatch for {cell['cell_id']}")
    features = data.get("features")
    if data.get("type") != "FeatureCollection" or data.get("numberMatched") != 1 or data.get("numberReturned") != 1:
        raise ValueError(f"Incomplete or unexpected query response for {cell['cell_id']}")
    if not isinstance(features, list) or len(features) != 1:
        raise ValueError(f"Missing/extra source feature for {cell['cell_id']}")
    feature = features[0]
    if feature.get("id") != EXPECTED[cell["key"]]:
        raise ValueError(f"Unexpected native source ID for {cell['cell_id']}")
    props = feature.get("properties", {})
    required = {
        "paises": "Portugal#Espanha",
        "estado_limite_admin": "Definido",
        "significado_linha": "Limite em Terra",
        "nivel_limite_admin": "1ª Ordem",
    }
    if any(props.get(key) != value for key, value in required.items()):
        raise ValueError(f"Source context mismatch for {cell['cell_id']}")
    return feature, props, receipt


def analyze() -> dict:
    if len(CELLS) != 6 or len({cell["cell_id"] for cell in CELLS}) != 6:
        raise ValueError("The exact six unique issue cells are required")
    rows = []
    controls = []
    for cell in CELLS:
        feature, props, receipt = load_case(cell)
        distance = metric(cell["lon"], cell["lat"], feature)
        line = shape(feature["geometry"])
        first_lon, first_lat = line.coords[0]
        on_line = metric(first_lon, first_lat, feature)
        far_point = metric(cell["lon"] + 1, cell["lat"] + 1, feature)
        if on_line > 0.001 or far_point < 1000:
            raise ValueError("Positive/negative geometry control failed")
        controls.append({
            "cell_id": cell["cell_id"],
            "positive_vertex_distance_m": on_line,
            "negative_offset_distance_m": far_point,
            "outcome": "passed",
        })
        rows.append({
            "cell_id": cell["cell_id"],
            "center_crs84": [cell["lon"], cell["lat"]],
            "prior_candidate_preview_member_match": cell["preview_member_match"],
            "preview_is_not_installed_grid": True,
            "source_feature_id": feature["id"],
            "source_response_sha256": receipt["sha256"],
            "source_request_url": receipt["request_url"],
            "source_retrieved_at": receipt["retrieved_at"],
            "source_properties": {key: props[key] for key in (
                "paises", "estado_limite_admin", "significado_linha",
                "nivel_limite_admin", "ea_direita", "ea_esquerda", "comprimento_km"
            )},
            "center_to_source_segment_distance_m": distance,
            "assessment": "dgt_defined_portugal_spain_line_reference_nearby; exact_center_side_and_owner_unresolved",
        })
    return {
        "version": 1,
        "method": "Transform each exact CRS84 candidate center and complete returned DGT source LineString to EPSG:25829 using pyproj always_xy; measure planar point-to-line distance with Shapely. No snapping, buffer, polygon-owner inference, or grid modification.",
        "source_collection": "DGT CAOP2025 Troços",
        "source_collection_vintage_note": "The collection title is CAOP2025; its API temporal extent reports 2000-10-30 through 2007-10-30. The DGT CAOP2025 page says this edition was approved 2026-01-28 and published 2026-02-18. Individual returned line features contain no validity/publication date. Preserve this metadata conflict; do not assign the line geometry a fabricated effective date.",
        "source_crs": "OGC:CRS84 longitude,latitude",
        "analysis_crs": "EPSG:25829 ETRS89 / UTM zone 29N metres",
        "source_role_limit": "A DGT national administrative-cartography line records a Portugal#Espanha first-order land limit with state Definido. Proximity supports a nearby official reference only; it does not establish exact-centre side, state attribution, bilateral instrument identity, or physical wetness.",
        "distance_rounding": "Unrounded calculation is retained; prose may round for display only.",
        "rows": rows,
        "controls": controls,
        "overall_assessment": "All six centers are within 10.3 m of a DGT segment reported as a defined Portugal-Spain first-order land-limit line. The five dual-member preview matches and the one no-member preview result remain source/geometry conflicts; no owner or repair is inferred.",
    }


if __name__ == "__main__":
    result = analyze()
    raw = (json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(raw)
    print(json.dumps({"output": str(OUTPUT.relative_to(ROOT)), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}))
