#!/usr/bin/env python3
"""Compare the two registered UGA ADM2 candidates to UBOS 2006 county polygons.

This reports aggregate geometry overlap only. It does not emit source geometry,
test cell coverage, or decide territorial applicability.
"""
import argparse
import gzip
import hashlib
import json
import math
import struct
import subprocess
import zipfile
from pathlib import Path

from shapely.geometry import Polygon, Point
from shapely.ops import unary_union

SOURCE_COMMIT = "923e9c210b59836e069c182d68daf85439096381"
SOURCE_PATH = "coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-UGA-ADM2-000.bin.gz"
SOURCE_BLOB = "1f8672d7303051dd6425dc822598dd935bc3c61f"
SOURCE_BYTES = 317239
SOURCE_SHA256 = "c16dc4723d4a48cbe5622bfe3f555cf46e0490a1a08324a22503696a5fc9389c"
SOURCE_DECODED_BYTES = 1021800
SOURCE_DECODED_SHA256 = "0a13e10b3bc6beeb02db4502c7f29a2ebbbb681a932307ccba4cd53e994feac7"
COUNTY_BYTES = 8325415
COUNTY_SHA256 = "9857cf0088b578beccea29c467f9e1a1224b6341ebe944320c975cb9ca984921"


def git_blob_oid(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def project_utm36n_custom(lon_deg, lat_deg):
    """Project WGS84 coordinates using the archive's embedded .prj parameters."""
    a, e2, k0 = 6378137.0, 0.0066943799901413165, 0.9996
    ep2, lon0 = e2 / (1.0 - e2), math.radians(33.0)
    lat, lon = math.radians(lat_deg), math.radians(lon_deg)
    sin_lat, cos_lat, tan_lat = math.sin(lat), math.cos(lat), math.tan(lat)
    n = a / math.sqrt(1.0 - e2 * sin_lat * sin_lat)
    t, c, aa = tan_lat * tan_lat, ep2 * cos_lat * cos_lat, cos_lat * (lon - lon0)
    m = a * ((1 - e2 / 4 - 3 * e2**2 / 64 - 5 * e2**3 / 256) * lat
        - (3 * e2 / 8 + 3 * e2**2 / 32 + 45 * e2**3 / 1024) * math.sin(2 * lat)
        + (15 * e2**2 / 256 + 45 * e2**3 / 1024) * math.sin(4 * lat)
        - (35 * e2**3 / 3072) * math.sin(6 * lat))
    x = 500000 + k0 * n * (aa + (1 - t + c) * aa**3 / 6
        + (5 - 18 * t + t**2 + 72 * c - 58 * ep2) * aa**5 / 120)
    y = 200000 + k0 * (m + n * tan_lat * (aa**2 / 2
        + (5 - t + 9 * c + 4 * c**2) * aa**4 / 24
        + (61 - 58 * t + t**2 + 600 * c - 330 * ep2) * aa**6 / 720))
    return x, y


def project_ring(ring):
    return [project_utm36n_custom(*point[:2]) for point in ring]


def project_geometry(geometry):
    kind, coordinates = geometry["type"], geometry["coordinates"]
    if kind == "Polygon":
        return Polygon(project_ring(coordinates[0]), [project_ring(ring) for ring in coordinates[1:]])
    if kind == "MultiPolygon":
        return unary_union([Polygon(project_ring(poly[0]), [project_ring(ring) for ring in poly[1:]])
                            for poly in coordinates])
    raise ValueError(f"unsupported geometry type {kind}")


def signed_area(ring):
    return sum(ring[i][0] * ring[(i + 1) % len(ring)][1]
        - ring[(i + 1) % len(ring)][0] * ring[i][1] for i in range(len(ring))) / 2


def parse_shapefile(data):
    polygons, offset = [], 100
    while offset < len(data):
        _, words = struct.unpack_from(">2i", data, offset)
        content = data[offset + 8:offset + 8 + words * 2]
        shape_type = struct.unpack_from("<i", content, 0)[0]
        if shape_type != 5:
            raise ValueError(f"expected polygon geometry, got type {shape_type}")
        part_count, point_count = struct.unpack_from("<2i", content, 36)
        starts = struct.unpack_from(f"<{part_count}i", content, 44)
        point_offset = 44 + 4 * part_count
        values = struct.unpack_from(f"<{2 * point_count}d", content, point_offset)
        points = list(zip(values[::2], values[1::2]))
        rings = [points[start:starts[i + 1] if i + 1 < part_count else point_count]
                 for i, start in enumerate(starts)]
        outers = [ring for ring in rings if signed_area(ring) < 0]
        holes = [ring for ring in rings if signed_area(ring) > 0]
        if not outers:
            raise ValueError("polygon record has no clockwise outer ring")
        outer_polygons = [Polygon(ring) for ring in outers]
        assignments = [[] for _ in outers]
        for hole in holes:
            point = Point(hole[0])
            matches = [i for i, outer in enumerate(outer_polygons) if outer.covers(point)]
            if matches:
                assignments[min(matches, key=lambda i: outer_polygons[i].area)].append(hole)
        geometry = unary_union([Polygon(outer, assignments[i]) for i, outer in enumerate(outers)])
        polygons.append(geometry)
        offset += 8 + words * 2
    return polygons


def parse_dbf(data):
    count = struct.unpack_from("<I", data, 4)[0]
    header_length, record_length = struct.unpack_from("<HH", data, 8)
    fields, offset = [], 32
    while data[offset] != 0x0D:
        descriptor = data[offset:offset + 32]
        fields.append((descriptor[:11].split(b"\0", 1)[0].decode("ascii"), descriptor[16]))
        offset += 32
    records = []
    for i in range(count):
        raw, cursor, row = data[header_length + i * record_length:header_length + (i + 1) * record_length], 1, {}
        for name, size in fields:
            row[name] = raw[cursor:cursor + size].decode("latin1").strip()
            cursor += size
        records.append(row)
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--archive", type=Path, required=True)
    args = parser.parse_args()
    compressed = subprocess.run(["git", "-C", str(args.repo), "show", f"{SOURCE_COMMIT}:{SOURCE_PATH}"],
        check=True, stdout=subprocess.PIPE, env={**__import__("os").environ,
            "GIT_NO_LAZY_FETCH": "1", "GIT_NO_REPLACE_OBJECTS": "1"}).stdout
    decoded = gzip.decompress(compressed)
    if (len(compressed) != SOURCE_BYTES or hashlib.sha256(compressed).hexdigest() != SOURCE_SHA256
        or git_blob_oid(compressed) != SOURCE_BLOB or len(decoded) != SOURCE_DECODED_BYTES
        or hashlib.sha256(decoded).hexdigest() != SOURCE_DECODED_SHA256):
        raise ValueError("pinned geoBoundaries source body differs")
    raw_archive = args.archive.read_bytes()
    if len(raw_archive) != COUNTY_BYTES or hashlib.sha256(raw_archive).hexdigest() != COUNTY_SHA256:
        raise ValueError("pinned UBOS county archive differs")
    with zipfile.ZipFile(args.archive) as zf:
        counties = parse_shapefile(zf.read("Uganda_county2006.shp"))
        attributes = parse_dbf(zf.read("Uganda_county2006.dbf"))
        prj = zf.read("Uganda_county2006.prj").decode("utf-8")
    if len(counties) != 164 or len(attributes) != 164 or 'PARAMETER["False_Northing",200000.0]' not in prj:
        raise ValueError("unexpected UBOS county records or embedded projection")
    if any(not geometry.is_valid for geometry in counties):
        raise ValueError("invalid UBOS county polygon geometry")
    by_name = {feature["properties"]["shapeName"]: feature for feature in json.loads(decoded)["features"]}
    result = []
    for name in ("Ntoroko", "Bughendra"):
        feature = by_name[name]
        candidate = project_geometry(feature["geometry"])
        if not candidate.is_valid:
            raise ValueError(f"invalid candidate geometry for {name}")
        overlaps = []
        for attributes_row, county in zip(attributes, counties):
            intersection_area = candidate.intersection(county).area
            if intersection_area > 0:
                overlaps.append({"county": attributes_row["CNAME_2006"],
                    "intersection_km2": round(intersection_area / 1_000_000, 2),
                    "candidate_pct": round(100 * intersection_area / candidate.area, 3),
                    "county_pct": round(100 * intersection_area / county.area, 3)})
        overlaps.sort(key=lambda row: (-row["intersection_km2"], row["county"]))
        result.append({"candidate_name": name, "candidate_source_id": feature["properties"]["shapeID"],
            "candidate_area_km2": round(candidate.area / 1_000_000, 2),
            "intersecting_ubos_county_count": len(overlaps), "overlaps": overlaps})
    print(json.dumps({"kind": "cod-uga-2006-candidate-vs-ubos-county-polygon-overlap-v1",
        "status": "research-only; source geometry overlap, no key disposition",
        "scope": {"residual_package": "gb-COD-ADM2--repair-evaluation", "owner": 14568,
            "target_source_id": "gb:COD:ADM2:63176286B75372177576839", "target_name": "Irumu",
            "candidate_centers": 112, "candidate_center_labels": {"Ntoroko": 66, "Bughendra": 46}},
        "inputs": {"geoboundaries_source_commit": SOURCE_COMMIT, "geoboundaries_source_path": SOURCE_PATH,
            "geoboundaries_git_blob_oid": SOURCE_BLOB, "geoboundaries_archive_sha256": SOURCE_SHA256,
            "geoboundaries_decoded_bytes": SOURCE_DECODED_BYTES, "geoboundaries_decoded_sha256": SOURCE_DECODED_SHA256,
            "ubos_archive_bytes": COUNTY_BYTES, "ubos_archive_sha256": COUNTY_SHA256,
            "ubos_counties": 164, "ubos_coordinate_reference": "embedded .prj WGS 84 UTM 36N, custom false northing 200000 m",
            "comparison_crs": "same UTM 36N custom-200000 m projection; candidate WGS 84 coordinates were forward projected"},
        "result": result,
        "limits": ["Area comparisons are planar in the dataset's embedded custom UTM projection.",
            "The UBOS archive has conflicting ISO/ESRI projection metadata; results follow its embedded .prj.",
            "The geoBoundaries candidate source is recorded as 2006 Counties / Public Domain and cites geoBoundaries/Wikimedia; UBOS is the separate 2006 county source.",
            "Different polygon extents show source disagreement, not which source applies to the 2019 OCHA Irumu target.",
            "No native cell was tested; no target source row, owner, hold, patch, credit, or package status changed."]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
