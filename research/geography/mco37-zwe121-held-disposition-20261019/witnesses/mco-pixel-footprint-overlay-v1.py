#!/usr/bin/env python3
"""Reproduce MCO native-grid footprint/polygon overlay flags without owner calls."""

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path

TARGET = "1a137b1b2e8d5d655412c242a5950f3d39e95bbb"
SIZE = 262166
PAYLOAD_SHA256 = "1135297a3146d4e445dd6090f5a4812df9ea36249e21bf997b8fa53b6c4d3a23"
DECODED_SHA256 = "51a7b2da1c91213c6dc3b17675ddf0531cde50546fdc583b5aa568755e7e43d2"
SHAPE_ID = "64170238B96397749018979"
MANIFEST_SHA256 = "70204c43deefd1af97c898f120d3638d4b8a3953445df37036d5771a54d718cc"
MANIFEST_GIT_BLOB = "4bbbb83d6d7220b9ffafef3bfa240487fda7427b"
VECTOR_SHA256 = "a33ce346f7a9b564048c75ea5fedad7cc5184d7c936ac36bc1ee8958797102a2"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def latitude_edge(y, size):
    return math.atan(math.sinh(math.pi * (1.0 - 2.0 * y / size))) * 180.0 / math.pi


def point_ring_relation(px, py, ring):
    inside = False
    for i in range(len(ring) - 1):
        x1, y1 = ring[i]
        x2, y2 = ring[i + 1]
        cross = (px - x1) * (y2 - y1) - (py - y1) * (x2 - x1)
        if (cross == 0 and min(x1, x2) <= px <= max(x1, x2)
                and min(y1, y2) <= py <= max(y1, y2)):
            return "boundary"
        if (y1 > py) != (y2 > py):
            crossing_x = x1 + (py - y1) * (x2 - x1) / (y2 - y1)
            if px < crossing_x:
                inside = not inside
    return "inside" if inside else "outside"


def point_polygon_relation(px, py, rings):
    exterior = point_ring_relation(px, py, rings[0])
    if exterior != "inside":
        return exterior
    for ring in rings[1:]:
        relation = point_ring_relation(px, py, ring)
        if relation == "boundary":
            return relation
        if relation == "inside":
            return "outside"
    return "inside"


def clip_segment_to_rect(a, b, rect):
    """Liang-Barsky clip; rect is (xmin,xmax,ymin,ymax), all closed."""
    x0, y0 = a
    x1, y1 = b
    dx, dy = x1 - x0, y1 - y0
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x0 - rect[0]), (dx, rect[1] - x0),
                 (-dy, y0 - rect[2]), (dy, rect[3] - y0)):
        if p == 0:
            if q < 0:
                return None
            continue
        ratio = q / p
        if p < 0:
            if ratio > t1:
                return None
            t0 = max(t0, ratio)
        else:
            if ratio < t0:
                return None
            t1 = min(t1, ratio)
    if t0 > t1:
        return None
    return ((x0 + t0 * dx, y0 + t0 * dy), (x0 + t1 * dx, y0 + t1 * dy))


def classify_footprint(rect, rings):
    xmin, xmax, ymin, ymax = rect
    corners = [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)]
    corner_relations = [point_polygon_relation(x, y, rings) for x, y in corners]
    boundary_intersects = False
    boundary_enters_interior = False
    boundary_vertex_inside = any(
        xmin < x < xmax and ymin < y < ymax
        for ring in rings for x, y in ring[:-1]
    )
    for ring in rings:
        for i in range(len(ring) - 1):
            clipped = clip_segment_to_rect(ring[i], ring[i + 1], rect)
            if clipped is None:
                continue
            boundary_intersects = True
            (x1, y1), (x2, y2) = clipped
            if x1 != x2 or y1 != y2:
                mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
                if xmin < mx < xmax and ymin < my < ymax:
                    boundary_enters_interior = True
    fully_contained = (
        all(relation != "outside" for relation in corner_relations)
        and not boundary_enters_interior
        and not boundary_vertex_inside
    )
    positive_area_overlap = (
        fully_contained
        or any(relation == "inside" for relation in corner_relations)
        or boundary_enters_interior
        or boundary_vertex_inside
    )
    return {
        "footprint_corners_lonlat": [[x, y] for x, y in corners],
        "corner_relations": corner_relations,
        "positive_area_overlap_with_polygon": positive_area_overlap,
        "footprint_fully_contained_in_polygon": fully_contained,
        "source_polygon_boundary_intersects_closed_footprint": boundary_intersects,
        "source_polygon_boundary_enters_footprint_interior": boundary_enters_interior,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("/Users/chengshuli/world-atlas-workspace/WorldAtlas"))
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("mco-pixel-footprint-overlay-addendum-v1.json"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parent

    vector_path = root / "mco-selected-owner-input-vector-v1.json"
    vector_bytes = vector_path.read_bytes()
    assert sha(vector_bytes) == VECTOR_SHA256
    vector = json.loads(vector_bytes)
    assert vector["accepted_main_commit"] == TARGET
    keys = vector["input_vector"]
    assert len(keys) == 37 and len({(k["y"], k["x"]) for k in keys}) == 37

    payload_path = args.repo_root / "coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-MCO-ADM1-000.bin.gz"
    payload = payload_path.read_bytes()
    assert sha(payload) == PAYLOAD_SHA256
    decoded = gzip.decompress(payload)
    assert sha(decoded) == DECODED_SHA256
    collection = json.loads(decoded)
    assert collection["crs"]["properties"]["name"] == "urn:ogc:def:crs:OGC:1.3:CRS84"
    features = [f for f in collection["features"] if f.get("properties", {}).get("shapeID") == SHAPE_ID]
    assert len(features) == 1
    feature = features[0]
    assert feature["properties"].get("shapeISO") == "MCO"
    assert feature["properties"].get("shapeType") == "ADM1"
    assert feature["geometry"]["type"] == "Polygon"

    manifest_path = args.repo_root / "data/native-ownership/repaired-v7/manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    assert sha(manifest_bytes) == MANIFEST_SHA256
    assert git_blob_sha1(manifest_bytes) == MANIFEST_GIT_BLOB
    manifest = json.loads(manifest_bytes)
    assert manifest["size"] == SIZE and manifest["coordinateBits"] == 19
    assert manifest["method"] == "native-linear-evenodd-first-owner-v1"

    results = []
    for key in keys:
        x, y = key["x"], key["y"]
        rect = (-180.0 + 360.0 * x / SIZE,
                -180.0 + 360.0 * (x + 1) / SIZE,
                latitude_edge(y + 1, SIZE), latitude_edge(y, SIZE))
        results.append({"x": x, "y": y, **classify_footprint(rect, feature["geometry"]["coordinates"])})

    summary = {
        "footprints": len(results),
        "positive_area_overlap": sum(r["positive_area_overlap_with_polygon"] for r in results),
        "fully_contained": sum(r["footprint_fully_contained_in_polygon"] for r in results),
        "partial_overlap": sum(r["positive_area_overlap_with_polygon"] and not r["footprint_fully_contained_in_polygon"] for r in results),
        "no_positive_area_overlap": sum(not r["positive_area_overlap_with_polygon"] for r in results),
        "polygon_boundary_intersects_closed_footprint": sum(r["source_polygon_boundary_intersects_closed_footprint"] for r in results),
    }
    output = {
        "schema": "worldatlas.mco-pixel-footprint-source-overlay-geometry-only.v1",
        "scope": "Geometry-only overlay of the 37 exact native-grid cell footprints against one pinned Monaco source polygon.",
        "accepted_main_commit": TARGET,
        "inputs": {
            "owner_helper_vector": {"path": vector_path.name, "sha256": VECTOR_SHA256, "count": len(keys)},
            "source_polygon": {"path": str(payload_path), "compressed_sha256": PAYLOAD_SHA256,
                               "decoded_sha256": DECODED_SHA256, "crs": collection["crs"]["properties"]["name"],
                               "source_identity": "gb:MCO:ADM1", "product": "2017 OSM/Wambacher geoBoundaries ADM1",
                               "license": "ODbL 1.0", "shape_id": SHAPE_ID, "geometry_type": "Polygon",
                               "ring_count": len(feature["geometry"]["coordinates"])},
            "grid_transform": {"path": str(manifest_path), "sha256": MANIFEST_SHA256,
                               "git_blob_sha1": MANIFEST_GIT_BLOB, "size": SIZE, "coordinate_bits": 19,
                               "method": "native-linear-evenodd-first-owner-v1"},
        },
        "algorithm": {
            "cell_footprint": "Closed axis-aligned EPSG:3857 square projected to CRS84. West/east longitude edges are -180+360*x/N and -180+360*(x+1)/N. North/south latitude edges are atan(sinh(pi*(1-2*y/N)))*180/pi and the same formula at y+1; y increases downward.",
            "overlay": "Python binary64; polygon-vs-rectangle segment clipping (Liang-Barsky), even-odd point-in-ring tests, no epsilon or snapping. Positive-area overlap is reported if a corner lies inside, a polygon boundary enters the footprint interior, or a polygon vertex lies strictly inside; full containment requires all corners inside/on and no polygon boundary enters the interior.",
            "boundary": "Closed-footprint boundary intersection means any source polygon boundary segment intersects the closed footprint; the separate enters-interior flag excludes mere edge/corner tangency.",
            "measurement_limit": "Planar topological classification in CRS84 coordinate space; no geodesic area or overlap-area magnitude is computed.",
        },
        "results": results,
        "summary": summary,
        "interpretation_limits": [
            "No legal-boundary or sovereignty claim.",
            "Geometry overlap is not source qualification, native ownership, accepted repair fitness, or map credit.",
            "No owner API call was made; no accepted owner tuples are inferred.",
            "All original holds remain unchanged.",
        ],
    }
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(output, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"output": str(args.output.resolve()), "summary": summary,
                      "source_sha256": PAYLOAD_SHA256, "vector_sha256": VECTOR_SHA256,
                      "grid_manifest_blob": MANIFEST_GIT_BLOB}, sort_keys=True))


if __name__ == "__main__":
    main()
