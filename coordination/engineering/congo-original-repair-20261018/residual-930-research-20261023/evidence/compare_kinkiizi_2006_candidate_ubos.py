#!/usr/bin/env python3
"""Compare retained geoBoundaries Kinkiizi to UBOS's 2006 county polygon.

This reports source-representation overlap only. It does not test original
native cells or determine territorial applicability.
"""
import argparse
import gzip
import hashlib
import importlib.util
import json
import os
import subprocess
import zipfile
from pathlib import Path

SOURCE_COMMIT = "923e9c210b59836e069c182d68daf85439096381"
SOURCE_PATH = "coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-UGA-ADM2-000.bin.gz"
SOURCE_BYTES = 317239
SOURCE_SHA256 = "c16dc4723d4a48cbe5622bfe3f555cf46e0490a1a08324a22503696a5fc9389c"
DECODED_BYTES = 1021800
DECODED_SHA256 = "0a13e10b3bc6beeb02db4502c7f29a2ebbbb681a932307ccba4cd53e994feac7"
UBOS_BYTES = 8325415
UBOS_SHA256 = "9857cf0088b578beccea29c467f9e1a1224b6341ebe944320c975cb9ca984921"
GIT = Path("/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/git/bin/git")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--archive", type=Path, default=Path("/tmp/ubos-uganda-county-2006-sv534fc7879.zip"))
    args = parser.parse_args()
    helper_path = args.repo / "coordination/engineering/congo-original-repair-20261018/residual-930-research-20261023/evidence/compare_uganda_2006_candidate_county_polygons.py"
    spec = importlib.util.spec_from_file_location("retained_uganda_polygon_methods", helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    env = {**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_NO_REPLACE_OBJECTS": "1"}
    compressed = subprocess.run([str(GIT), "-C", str(args.repo), "show", f"{SOURCE_COMMIT}:{SOURCE_PATH}"],
        check=True, stdout=subprocess.PIPE, env=env).stdout
    decoded = gzip.decompress(compressed)
    archive = args.archive.read_bytes()
    if (len(compressed) != SOURCE_BYTES or hashlib.sha256(compressed).hexdigest() != SOURCE_SHA256
        or len(decoded) != DECODED_BYTES or hashlib.sha256(decoded).hexdigest() != DECODED_SHA256
        or len(archive) != UBOS_BYTES or hashlib.sha256(archive).hexdigest() != UBOS_SHA256):
        raise ValueError("a pinned source body differs")
    with zipfile.ZipFile(args.archive) as zf:
        polygons = helper.parse_shapefile(zf.read("Uganda_county2006.shp"))
        attributes = helper.parse_dbf(zf.read("Uganda_county2006.dbf"))
        prj = zf.read("Uganda_county2006.prj").decode("utf-8")
    if len(polygons) != 164 or len(attributes) != 164 or 'PARAMETER["False_Northing",200000.0]' not in prj:
        raise ValueError("unexpected UBOS feature count or projection definition")
    features = json.loads(decoded)["features"]
    feature = next(f for f in features if f["properties"].get("shapeName", "").casefold() == "kinkiizi")
    candidate = helper.project_geometry(feature["geometry"])
    if not candidate.is_valid or any(not polygon.is_valid for polygon in polygons):
        raise ValueError("invalid input polygon")
    overlaps = []
    for attr, polygon in zip(attributes, polygons):
        area = candidate.intersection(polygon).area
        if area > 0:
            overlaps.append({"ubos_county": attr["CNAME_2006"], "intersection_km2": round(area / 1_000_000, 3),
                "candidate_area_pct": round(100 * area / candidate.area, 3),
                "ubos_county_area_pct": round(100 * area / polygon.area, 3)})
    overlaps.sort(key=lambda x: (-x["intersection_km2"], x["ubos_county"]))
    print(json.dumps({"candidate_name": feature["properties"]["shapeName"],
        "candidate_source_id": feature["properties"]["shapeID"],
        "candidate_area_km2": round(candidate.area / 1_000_000, 3),
        "candidate_valid": candidate.is_valid, "ubos_polygon_count": len(polygons),
        "all_ubos_polygons_valid": all(polygon.is_valid for polygon in polygons),
        "intersections": overlaps,
        "method": "Reuse compare_uganda_2006_candidate_county_polygons.py parse/project methods; UBOS embedded WGS84 UTM36N custom 200000 m false northing; planar polygon intersection.",
        "limits": ["The UBOS ISO/ESRI metadata contains conflicting CRS declarations.",
            "This is a source-representation comparison, not an original-cell whole-cell test or a territorial-applicability decision."]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
