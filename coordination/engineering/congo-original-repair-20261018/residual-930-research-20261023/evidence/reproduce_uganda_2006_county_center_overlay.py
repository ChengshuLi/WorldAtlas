#!/usr/bin/env python3
"""Reproduce the aggregate UBOS Uganda 2006 county overlay; no geometry is emitted."""
import argparse
import collections
import hashlib
import json
import math
import struct
import zipfile
from pathlib import Path

EXPECTED_ARCHIVE_SHA256 = "9857cf0088b578beccea29c467f9e1a1224b6341ebe944320c975cb9ca984921"
EXPECTED_ARCHIVE_BYTES = 8_325_415
EXPECTED_POLYGONS = 164
OWNER = 14568
TARGET_ID = "gb:COD:ADM2:63176286B75372177576839"


def parse_dbf(data):
    record_count = struct.unpack_from("<I", data, 4)[0]
    header_length = struct.unpack_from("<H", data, 8)[0]
    record_length = struct.unpack_from("<H", data, 10)[0]
    fields = []
    offset = 32
    while data[offset] != 0x0D:
        descriptor = data[offset:offset + 32]
        name = descriptor[:11].split(b"\0", 1)[0].decode("ascii", "replace")
        fields.append((name, descriptor[16]))
        offset += 32
    rows = []
    for index in range(record_count):
        record = data[header_length + index * record_length:
                      header_length + (index + 1) * record_length]
        cursor = 1
        row = {}
        for name, length in fields:
            row[name] = record[cursor:cursor + length].decode("latin1").strip()
            cursor += length
        rows.append(row)
    return rows


def parse_shp(data):
    polygons = []
    offset = 100
    while offset < len(data):
        _record_number, words = struct.unpack_from(">2i", data, offset)
        content = data[offset + 8:offset + 8 + words * 2]
        shape_type = struct.unpack_from("<i", content, 0)[0]
        if shape_type != 5:
            raise ValueError(f"Expected polygon shape type 5, found {shape_type}")
        xmin, ymin, xmax, ymax = struct.unpack_from("<4d", content, 4)
        part_count, point_count = struct.unpack_from("<2i", content, 36)
        parts = struct.unpack_from(f"<{part_count}i", content, 44)
        point_offset = 44 + 4 * part_count
        values = struct.unpack_from(f"<{2 * point_count}d", content, point_offset)
        points = list(zip(values[::2], values[1::2]))
        rings = []
        for index, start in enumerate(parts):
            end = parts[index + 1] if index + 1 < part_count else point_count
            rings.append(points[start:end])
        polygons.append((xmin, ymin, xmax, ymax, rings))
        offset += 8 + words * 2
    return polygons


def project_utm36n_custom(lon_deg, lat_deg):
    # WGS 84 ellipsoid; parameters copied from the archive's embedded .prj.
    a = 6_378_137.0
    e2 = 0.0066943799901413165
    ep2 = e2 / (1.0 - e2)
    k0 = 0.9996
    lon0 = math.radians(33.0)
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    tan_lat = math.tan(lat)
    n = a / math.sqrt(1.0 - e2 * sin_lat * sin_lat)
    t = tan_lat * tan_lat
    c = ep2 * cos_lat * cos_lat
    aa = cos_lat * (lon - lon0)
    m = a * (
        (1 - e2 / 4 - 3 * e2**2 / 64 - 5 * e2**3 / 256) * lat
        - (3 * e2 / 8 + 3 * e2**2 / 32 + 45 * e2**3 / 1024) * math.sin(2 * lat)
        + (15 * e2**2 / 256 + 45 * e2**3 / 1024) * math.sin(4 * lat)
        - (35 * e2**3 / 3072) * math.sin(6 * lat)
    )
    x = 500_000 + k0 * n * (
        aa + (1 - t + c) * aa**3 / 6
        + (5 - 18 * t + t**2 + 72 * c - 58 * ep2) * aa**5 / 120
    )
    y = 200_000 + k0 * (m + n * tan_lat * (
        aa**2 / 2
        + (5 - t + 9 * c + 4 * c**2) * aa**4 / 24
        + (61 - 58 * t + t**2 + 600 * c - 330 * ep2) * aa**6 / 720
    ))
    return x, y


def point_in_rings(x, y, rings):
    inside = False
    for ring in rings:
        previous = len(ring) - 1
        for index, (xi, yi) in enumerate(ring):
            xj, yj = ring[previous]
            if ((yi > y) != (yj > y)) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                inside = not inside
            previous = index
    return inside


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument(
        "--evidence-dir", type=Path,
        default=Path(__file__).resolve().parent,
    )
    args = parser.parse_args()
    archive_bytes = args.archive.read_bytes()
    digest = hashlib.sha256(archive_bytes).hexdigest()
    if len(archive_bytes) != EXPECTED_ARCHIVE_BYTES or digest != EXPECTED_ARCHIVE_SHA256:
        raise ValueError("UBOS source archive size or SHA-256 does not match the recorded pin")
    with zipfile.ZipFile(args.archive) as source_zip:
        shapes = parse_shp(source_zip.read("Uganda_county2006.shp"))
        counties = parse_dbf(source_zip.read("Uganda_county2006.dbf"))
        prj = source_zip.read("Uganda_county2006.prj").decode("utf-8")
    if len(shapes) != EXPECTED_POLYGONS or len(counties) != EXPECTED_POLYGONS:
        raise ValueError("Unexpected UBOS polygon/attribute record count")
    if 'PARAMETER["False_Northing",200000.0]' not in prj:
        raise ValueError("Embedded .prj no longer has the recorded custom false northing")

    context = json.loads((args.evidence_dir / "target-context-recovery-116.json").read_text())
    overlay = json.loads((args.evidence_dir / "complete-537-feature-center-overlay.json").read_text())
    centers = {tuple(row["key"]): row["center"]
               for row in overlay["result"]["per_key"]}
    rows = [row for row in context["rows"] if row["key"][0] == OWNER]
    if len(rows) != 112 or any(row["target"]["target_id"] != TARGET_ID for row in rows):
        raise ValueError("Irumu input key roster or target identity changed")

    matrix = collections.Counter()
    candidate_counts = collections.Counter()
    for row in rows:
        key = tuple(row["key"])
        if key not in centers:
            raise ValueError(f"Missing retained center for {key}")
        candidate_labels = [hit["name"] for hit in row["full_537_feature_center_hits"]
                            if hit.get("family_key") == "gb:UGA:ADM2"]
        if len(candidate_labels) != 1:
            raise ValueError(f"Expected one UGA ADM2 candidate label for {key}")
        label = candidate_labels[0]
        candidate_counts[label] += 1
        x, y = project_utm36n_custom(*centers[key])
        hits = []
        for polygon, attrs in zip(shapes, counties):
            xmin, ymin, xmax, ymax, rings = polygon
            if xmin <= x <= xmax and ymin <= y <= ymax and point_in_rings(x, y, rings):
                hits.append(attrs["CNAME_2006"])
        matrix[(label, tuple(hits))] += 1

    compact = []
    for label in sorted(candidate_counts):
        relevant = sorted((hits, count) for (candidate, hits), count in matrix.items()
                          if candidate == label)
        for hits, count in relevant:
            compact.append({"candidate_label": label, "ubos_2006_county_hits": list(hits),
                            "keys": count})
    result = {
        "candidate_label_counts": dict(sorted(candidate_counts.items())),
        "ubos_county_containment_cross_tab": compact,
        "totals": {
            "keys": len(rows),
            "inside_Ntoroko": sum(n for (label, hits), n in matrix.items() if hits == ("NTOROKO",)),
            "inside_Bughendera": sum(n for (label, hits), n in matrix.items() if hits == ("BUGHENDERA",)),
            "inside_Bwamba": sum(n for (label, hits), n in matrix.items() if hits == ("BWAMBA",)),
            "outside_all_164_county_polygons": sum(n for (label, hits), n in matrix.items() if not hits),
        },
        "archive_sha256": digest,
        "archive_bytes": len(archive_bytes),
        "projection_note": "Counts use embedded .prj UTM 36N custom 200000 m false northing; the archive has conflicting ISO/ESRI projection metadata.",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
