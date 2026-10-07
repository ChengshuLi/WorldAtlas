#!/usr/bin/env python3
"""Compare the pinned component geometries with the public BIG KSP ADM2 layer.

The service response is not retained in this packet because the layer declares
no open redistribution license. The script accepts a local copy of the exact
response or fetches the recorded public query, then requires its pinned hash.
Only identifiers and topological intersection classifications are emitted.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import urllib.request
import urllib.parse
from pathlib import Path

from shapely.geometry import shape

PACKET = Path(__file__).resolve().parents[2]
RUN = PACKET / "vintages/run-thirty-eight/intersections.geojson.gz"
URL = (
    "https://kspservices.big.go.id/satupeta/rest/services/PUBLIK/"
    "BATAS_WILAYAH/MapServer/2/query?"
    "objectIds=57%2C402%2C403%2C358%2C366%2C369%2C376%2C377%2C378%2C387%2C490%2C491"
    "&outFields=%2A&returnGeometry=true&outSR=4326&f=geoJSON"
)
SOURCE_SHA256 = "d45aedf8f0f70031804a2666e1a6061cb5c67c1a36add6fee51ed3dd273ee94e"
SOURCE_IDS = {57, 358, 366, 369, 376, 377, 378, 387, 402, 403, 490, 491}
SELECTION_IDS = [57, 402, 403, 358, 366, 369, 376, 377, 378, 387, 490, 491]
SELECTION_ENVELOPE = [116.25791778895884, -2.2215, 119.011729, 2.318793]
SELECTION_RESPONSE_SHA256 = "f270c1c04cf8a53bf48ec5c9b632d6642680ce67c3f07b3a0b0f47477a0e517c"
LIMIT = 32 * 1024 * 1024


def read_source(path: Path | None) -> bytes:
    if path:
        raw = path.read_bytes()
    else:
        request = urllib.request.Request(URL, headers={"User-Agent": "WorldAtlas-source-assessment/1.0"})
        with urllib.request.urlopen(request, timeout=90) as response:
            if response.status != 200:
                raise ValueError(f"BIG query returned HTTP {response.status}")
            raw = response.read(LIMIT + 1)
    if not raw or len(raw) > LIMIT:
        raise ValueError("BIG response is empty or exceeds 32 MiB")
    actual = hashlib.sha256(raw).hexdigest()
    if actual != SOURCE_SHA256:
        raise ValueError(f"BIG response hash changed: expected {SOURCE_SHA256}, got {actual}")
    return raw


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-file", type=Path, help="Local exact BIG GeoJSON response; otherwise fetch the pinned query")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    raw = read_source(args.source_file)
    source = json.loads(raw)
    source_rows = source.get("features")
    if not isinstance(source_rows, list) or {row["properties"]["objectid"] for row in source_rows} != SOURCE_IDS:
        raise ValueError("BIG response feature identities differ from the pinned query")
    big = [(row["properties"], shape(row["geometry"])) for row in source_rows]

    with gzip.open(RUN, "rt", encoding="utf-8") as stream:
        run = json.load(stream)
    components = [row for row in run["features"] if row["properties"].get("role") == "original_pinned_component"]
    if len(components) != 45 or len({row["properties"]["component_id"] for row in components}) != 45:
        raise ValueError("Pinned complete component roster is not present exactly once")
    component_geometries = [shape(row["geometry"]) for row in components]
    actual_envelope = [
        min(geometry.bounds[0] for geometry in component_geometries),
        min(geometry.bounds[1] for geometry in component_geometries),
        max(geometry.bounds[2] for geometry in component_geometries),
        max(geometry.bounds[3] for geometry in component_geometries),
    ]
    if actual_envelope != SELECTION_ENVELOPE:
        raise ValueError("Pinned component envelope differs from the recorded BIG query envelope")
    selection_params = {
        "where": "1=1",
        "geometry": json.dumps({"xmin": actual_envelope[0], "ymin": actual_envelope[1], "xmax": actual_envelope[2], "ymax": actual_envelope[3], "spatialReference": {"wkid": 4326}}, separators=(",", ":")),
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "returnIdsOnly": "true",
        "f": "pjson",
    }
    selection_url = "https://kspservices.big.go.id/satupeta/rest/services/PUBLIK/BATAS_WILAYAH/MapServer/2/query?" + urllib.parse.urlencode(selection_params)
    selection_request = urllib.request.Request(selection_url, headers={"User-Agent": "WorldAtlas-source-assessment/1.0"})
    with urllib.request.urlopen(selection_request, timeout=45) as response:
        selection_raw = response.read(1024 * 1024)
    if hashlib.sha256(selection_raw).hexdigest() != SELECTION_RESPONSE_SHA256:
        raise ValueError("BIG spatial query selection response hash changed")
    if json.loads(selection_raw).get("objectIds") != SELECTION_IDS:
        raise ValueError("BIG spatial query selected feature identities changed")

    pair_count = 0
    relation_counts = {"positive_area": 0, "positive_length": 0, "point_only": 0}
    component_rows = []
    for feature in sorted(components, key=lambda row: row["properties"]["component_id"]):
        component_id = feature["properties"]["component_id"]
        geometry = shape(feature["geometry"])
        intersections = []
        for properties, source_geometry in big:
            pair_count += 1
            if not geometry.intersects(source_geometry):
                continue
            overlap = geometry.intersection(source_geometry)
            if overlap.is_empty:
                continue
            if overlap.area > 0:
                relation = "positive_area"
            elif overlap.length > 0:
                relation = "positive_length"
            else:
                relation = "point_only"
            relation_counts[relation] += 1
            intersections.append({
                "big_objectid": properties["objectid"],
                "name": properties.get("namobj"),
                "province": properties.get("wadmpr"),
                "admin_code": properties.get("kdpkab"),
                "relation": relation,
            })
        component_rows.append({
            "component_id": component_id,
            "intersection_count": len(intersections),
            "intersections": sorted(intersections, key=lambda row: row["big_objectid"]),
        })

    result = {
        "version": 1,
        "source": {
            "product": "BIG KSP 2022 Peta Wilayah Administrasi Kabupaten/Kota (Area)",
            "layer_url": "https://kspservices.big.go.id/satupeta/rest/services/PUBLIK/BATAS_WILAYAH/MapServer/2",
            "query_url": URL,
            "feature_selection": {
                "method": "Official service envelope intersection with the bounds of the 45 exact pinned component geometries; returnIdsOnly=true.",
                "envelope_wgs84": SELECTION_ENVELOPE,
                "ids_response_sha256": SELECTION_RESPONSE_SHA256,
                "selected_objectids": SELECTION_IDS,
                "retrieved_utc": "2026-10-07T13:46:42.975446+00:00",
            },
            "query_response_sha256": SOURCE_SHA256,
            "query_response_bytes": len(raw),
            "source_feature_count": len(big),
            "out_spatial_reference": 4326,
            "geometry_retained_in_packet": False,
            "license_status": "unknown",
        },
        "method": "Direct, unbuffered Shapely intersections in WGS84; no repair; classifications only, no area measurements.",
        "scope": {"component_count": len(components), "source_feature_count": len(big), "candidate_pair_count": pair_count},
        "summary": {
            "components_with_intersection": sum(bool(row["intersections"]) for row in component_rows),
            "components_without_intersection": sum(not row["intersections"] for row in component_rows),
            "intersection_count_by_relation": relation_counts,
        },
        "component_results": component_rows,
        "limits": [
            "The public service's layer metadata has empty copyrightText and states no open redistribution license; raw BIG geometry is not included.",
            "This geometric correspondence check does not establish legal boundary authority, effective date, completeness, positional accuracy, or physical land/water status.",
            "Two components have no polygon intersection in this returned source subset; this does not establish whether they are outside official territory or reflect a source/coverage gap.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
