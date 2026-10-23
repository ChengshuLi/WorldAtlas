#!/usr/bin/env python3
"""Reproduce a geometry-only cell-center PIP diagnostic for the pinned MCO polygon."""

import argparse
import gzip
import hashlib
import json
import math
import platform
import subprocess
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


def ring_relation(px, py, ring):
    """Even-odd ray crossing; exact-float segment equality reports boundary."""
    inside = False
    for index in range(len(ring) - 1):
        x1, y1 = ring[index]
        x2, y2 = ring[index + 1]
        cross = (px - x1) * (y2 - y1) - (py - y1) * (x2 - x1)
        if (cross == 0 and min(x1, x2) <= px <= max(x1, x2)
                and min(y1, y2) <= py <= max(y1, y2)):
            return "boundary"
        if (y1 > py) != (y2 > py):
            crossing_x = x1 + (py - y1) * (x2 - x1) / (y2 - y1)
            if px < crossing_x:
                inside = not inside
    return "inside" if inside else "outside"


def polygon_relation(lon, lat, coordinates):
    """Apply GeoJSON Polygon exterior/hole semantics with even-odd rings."""
    exterior = ring_relation(lon, lat, coordinates[0])
    if exterior != "inside":
        return exterior
    for hole in coordinates[1:]:
        relation = ring_relation(lon, lat, hole)
        if relation == "boundary":
            return "boundary"
        if relation == "inside":
            return "outside"
    return "inside"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("/Users/chengshuli/world-atlas-workspace/WorldAtlas"))
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("mco-cellcenter-pip-addendum-v1.json"))
    args = parser.parse_args()

    artifact_root = Path(__file__).resolve().parent
    vector_path = artifact_root / "mco-selected-owner-input-vector-v1.json"
    vector_bytes = vector_path.read_bytes()
    assert sha(vector_bytes) == VECTOR_SHA256, "MCO owner-helper vector pin mismatch"
    vector = json.loads(vector_bytes)
    assert vector["accepted_main_commit"] == TARGET
    keys = vector["input_vector"]
    assert len(keys) == 37 and len({(k["y"], k["x"]) for k in keys}) == 37

    payload_path = args.repo_root / "coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-MCO-ADM1-000.bin.gz"
    payload = payload_path.read_bytes()
    assert sha(payload) == PAYLOAD_SHA256, "Pinned MCO source payload mismatch"
    decoded = gzip.decompress(payload)
    assert len(decoded) == 1094 and sha(decoded) == DECODED_SHA256, "Pinned MCO source metadata bytes mismatch"
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
    assert sha(manifest_bytes) == MANIFEST_SHA256, "Pinned current-main manifest bytes mismatch"
    assert git_blob_sha1(manifest_bytes) == MANIFEST_GIT_BLOB, "Pinned current-main manifest Git blob mismatch"
    manifest = json.loads(manifest_bytes)
    assert manifest["size"] == SIZE and manifest["coordinateBits"] == 19
    assert manifest["method"] == "native-linear-evenodd-first-owner-v1"

    results = []
    for key in keys:
        x, y = key["x"], key["y"]
        lon = (x + 0.5) / SIZE * 360.0 - 180.0
        lat = math.atan(math.sinh(math.pi * (1.0 - 2.0 * (y + 0.5) / SIZE))) * 180.0 / math.pi
        results.append({"x": x, "y": y, "cell_center_lon": lon, "cell_center_lat": lat,
                        "relation_to_pinned_source_polygon": polygon_relation(lon, lat, feature["geometry"]["coordinates"])})

    relations = {label: sum(row["relation_to_pinned_source_polygon"] == label for row in results)
                 for label in ("inside", "outside", "boundary")}
    output = {
        "schema": "worldatlas.mco-cellcenter-source-pip-geometry-only.v1",
        "scope": "Geometry-only classification of the 37 supplied native-grid cell centers against one pinned MCO source polygon.",
        "accepted_main_commit": TARGET,
        "inputs": {
            "owner_helper_vector": {"path": vector_path.name, "sha256": VECTOR_SHA256, "count": len(keys)},
            "source_payload": {"path": str(payload_path), "compressed_sha256": PAYLOAD_SHA256,
                               "compressed_bytes": len(payload), "decoded_sha256": DECODED_SHA256,
                               "decoded_bytes": len(decoded), "crs": collection["crs"]["properties"]["name"],
                               "source_identity": "gb:MCO:ADM1", "product": "2017 OSM/Wambacher geoBoundaries ADM1",
                               "license": "ODbL 1.0", "shape_id": SHAPE_ID},
            "grid_convention": {"path": str(manifest_path), "sha256": MANIFEST_SHA256,
                                "git_blob_sha1": MANIFEST_GIT_BLOB, "size": SIZE, "coordinate_bits": 19,
                                "method": "native-linear-evenodd-first-owner-v1"}
        },
        "algorithm": {
            "coordinate_convention": "For size N=262166, lon=-180+360*(x+0.5)/N; lat=atan(sinh(pi*(1-2*(y+0.5)/N)))*180/pi. Coordinates are cell centers in CRS84 longitude/latitude; y increases downward from the north.",
            "point_in_polygon": "Python binary64 arithmetic; GeoJSON Polygon exterior and hole semantics; even-odd horizontal ray crossing; exact-float segment equality is reported as boundary, with no epsilon or snapping.",
            "runtime": platform.python_version(),
            "classification_limit": "This reports only whether each computed cell center lies inside, outside, or on the boundary of the pinned polygon. It is not a whole-cell intersection test."
        },
        "results": results,
        "summary": relations,
        "interpretation_limits": [
            "No legal-boundary or sovereignty claim.",
            "No proof of whole-cell source contact, source qualification, native ownership, repair fitness, accepted unresolved credit, or clearance.",
            "All original holds remain unchanged."
        ]
    }
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(output, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"output": str(args.output.resolve()), "keys": len(results), "summary": relations,
                      "vector_sha256": VECTOR_SHA256, "source_sha256": PAYLOAD_SHA256,
                      "grid_manifest_blob": MANIFEST_GIT_BLOB}, sort_keys=True))


if __name__ == "__main__":
    main()
