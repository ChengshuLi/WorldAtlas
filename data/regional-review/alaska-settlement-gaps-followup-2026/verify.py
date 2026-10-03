#!/usr/bin/env python3
"""Requery Alaska DCRA locality points and test against the exact #486 polygons."""
import gzip
import hashlib
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

try:
    from shapely.geometry import shape
except ImportError as exc:
    raise SystemExit("Install Shapely 2.x in the active Python environment to run this check") from exc

ROOT = Path(__file__).resolve().parents[3]
PACKET = ROOT / "data/regional-review/alaska-settlement-gaps-followup-2026"
PARENT = ROOT / "data/regional-review/regional-review-93f8f3bee8e205be"
URL = (
    "https://maps.commerce.alaska.gov/server/rest/services/Community_Related/"
    "Community_Locations_and_Boundaries/MapServer/0/query"
)
PARAMS = {
    "where": "1=1",
    "geometry": json.dumps(
        {"xmin": -180, "ymin": 51, "xmax": -129, "ymax": 72,
         "spatialReference": {"wkid": 4326}}, separators=(",", ":")
    ),
    "geometryType": "esriGeometryEnvelope",
    "inSR": "4326",
    "spatialRel": "esriSpatialRelIntersects",
    "outFields": "*",
    "returnGeometry": "true",
    "outSR": "4326",
    "f": "geojson",
    "resultRecordCount": "2000",
}


def main():
    scope = json.loads((PACKET / "scope.json").read_text())
    assessment = json.loads((PACKET / "assessment.json").read_text())
    assert len(scope["subjects"]) == 8
    assert [x["id"] for x in assessment["subjects"]] == [x["id"] for x in scope["subjects"]]
    baseline_path = PARENT / "sources/current-scope-and-parents.geojson.gz"
    baseline_bytes = baseline_path.read_bytes()
    baseline = json.loads(gzip.decompress(baseline_bytes))
    wanted = {x["id"] for x in scope["subjects"]}
    polygons = {
        f["properties"]["id"]: shape(f["geometry"])
        for f in baseline["features"] if f["properties"]["id"] in wanted
    }
    assert set(polygons) == wanted, "the preserved parent scope must contain exactly the eight assigned geometries"

    request = urllib.request.Request(
        URL + "?" + urllib.parse.urlencode(PARAMS),
        headers={"User-Agent": "WorldAtlas geography evidence reproduction/1.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        raw = response.read()
    query = json.loads(raw)
    if "error" in query:
        raise RuntimeError(query["error"])
    features = query.get("features", [])
    if query.get("exceededTransferLimit"):
        raise RuntimeError("DCRA response exceeded transfer limit; use pagination before interpreting")
    hits = {key: [] for key in wanted}
    for feature in features:
        geom = feature.get("geometry")
        if not geom:
            continue
        point = shape(geom)
        for key, polygon in polygons.items():
            if polygon.intersects(point):
                props = feature.get("properties", {})
                hits[key].append({
                    "CommunityId": props.get("CommunityId"),
                    "CommunityName": props.get("CommunityName"),
                    "CommunityAreaTypeName": props.get("CommunityAreaTypeName"),
                    "CommunityTypeName": props.get("CommunityTypeName"),
                    "IsActive": props.get("IsActive"),
                })
    digest = hashlib.sha256(raw).hexdigest()
    print(json.dumps({
        "query_response_sha256": digest,
        "query_response_bytes": len(raw),
        "feature_count": len(features),
        "baseline_scope_sha256": hashlib.sha256(baseline_bytes).hexdigest(),
        "subject_hit_counts": {key: len(value) for key, value in hits.items()},
        "subject_hits": hits,
    }, indent=2, ensure_ascii=False))
    expected = {x["id"]: 0 for x in scope["subjects"]}
    if {key: len(value) for key, value in hits.items()} != expected:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
