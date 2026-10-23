#!/usr/bin/env python3
"""Aggregate nearest-line context for the 112 original Irumu residual centers.

No source geometry or per-key coordinates are emitted. The WRI linework is
contextual evidence only; this does not reconstruct polygons or decide borders.
"""
import argparse
import collections
import hashlib
import json
import math
import struct
import zipfile
from pathlib import Path

from reproduce_uganda_2006_county_center_overlay import (
    parse_dbf as parse_county_dbf,
    parse_shp as parse_county_shp,
    point_in_rings,
    project_utm36n_custom,
)

EXPECTED_ARCHIVE_BYTES = 1_646_436
EXPECTED_ARCHIVE_SHA256 = "be2f3ed89101fd68a909f20bc69fc1f097fcb203254ce06ad584588bf4284de5"
EXPECTED_FEATURES = 5_767
EXPECTED_COUNTY_ARCHIVE_BYTES = 8_325_415
EXPECTED_COUNTY_ARCHIVE_SHA256 = "9857cf0088b578beccea29c467f9e1a1224b6341ebe944320c975cb9ca984921"
EXPECTED_COUNTY_POLYGONS = 164
OWNER = 14_568
TARGET_ID = "gb:COD:ADM2:63176286B75372177576839"


def parse_dbf(data):
    count = struct.unpack_from("<I", data, 4)[0]
    header_length = struct.unpack_from("<H", data, 8)[0]
    record_length = struct.unpack_from("<H", data, 10)[0]
    fields = []
    offset = 32
    while data[offset] != 0x0D:
        descriptor = data[offset:offset + 32]
        name = descriptor[:11].split(b"\0", 1)[0].decode("ascii", "replace")
        fields.append((name, descriptor[11], descriptor[16]))
        offset += 32
    rows = []
    for index in range(count):
        record = data[header_length + index * record_length:
                      header_length + (index + 1) * record_length]
        cursor = 1
        row = {}
        for name, field_type, length in fields:
            value = record[cursor:cursor + length].decode("latin1").strip()
            cursor += length
            if field_type in (ord("N"), ord("F")) and value:
                value = float(value) if "." in value else int(value)
            row[name] = value
        rows.append(row)
    return rows, [field[0] for field in fields]


def parse_shp(data):
    records = []
    offset = 100
    while offset < len(data):
        record_number, content_words = struct.unpack_from(">2i", data, offset)
        content = data[offset + 8:offset + 8 + content_words * 2]
        shape_type = struct.unpack_from("<i", content, 0)[0]
        if shape_type not in (3, 13, 23):
            raise ValueError(f"Expected polyline shape, received type {shape_type}")
        part_count, point_count = struct.unpack_from("<2i", content, 36)
        starts = struct.unpack_from(f"<{part_count}i", content, 44)
        point_offset = 44 + 4 * part_count
        values = struct.unpack_from(f"<{2 * point_count}d", content, point_offset)
        points = list(zip(values[::2], values[1::2]))
        parts = []
        for index, start in enumerate(starts):
            end = starts[index + 1] if index + 1 < part_count else point_count
            if end - start >= 2:
                parts.append([project_utm36n_custom(*point) for point in points[start:end]])
        all_x = [point[0] for part in parts for point in part]
        all_y = [point[1] for part in parts for point in part]
        records.append({
            "record_index_zero_based": len(records),
            "record_number_header": record_number,
            "parts": parts,
            "bbox": (min(all_x), min(all_y), max(all_x), max(all_y)),
        })
        offset += 8 + content_words * 2
    return records


def nearest_segment(point, parts):
    px, py = point
    best = None
    for part in parts:
        for (x1, y1), (x2, y2) in zip(part, part[1:]):
            dx, dy = x2 - x1, y2 - y1
            length_squared = dx * dx + dy * dy
            if not length_squared:
                continue
            fraction = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / length_squared))
            qx, qy = x1 + fraction * dx, y1 + fraction * dy
            distance = math.hypot(px - qx, py - qy)
            if best is None or distance < best[0]:
                cross = dx * (py - qy) - dy * (px - qx)
                side = "left" if cross > 0 else "right" if cross < 0 else "on"
                best = (distance, side)
    return best


def bbox_distance(point, bbox):
    x, y = point
    xmin, ymin, xmax, ymax = bbox
    dx = max(xmin - x, 0.0, x - xmax)
    dy = max(ymin - y, 0.0, y - ymax)
    return math.hypot(dx, dy)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--county-archive", required=True, type=Path)
    parser.add_argument("--evidence-dir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    archive = args.archive.read_bytes()
    digest = hashlib.sha256(archive).hexdigest()
    if len(archive) != EXPECTED_ARCHIVE_BYTES or digest != EXPECTED_ARCHIVE_SHA256:
        raise ValueError("WRI archive size or SHA-256 does not match the retained source pin")
    with zipfile.ZipFile(args.archive) as source_zip:
        base = "Ug_District-boundaries2006/Ug_District-boundaries2006"
        shp = source_zip.read(base + ".shp")
        dbf = source_zip.read(base + ".dbf")
        prj = source_zip.read(base + ".prj").decode("utf-8")
    attributes, field_names = parse_dbf(dbf)
    records = parse_shp(shp)
    if len(records) != EXPECTED_FEATURES or len(attributes) != EXPECTED_FEATURES:
        raise ValueError("Unexpected WRI feature/attribute count")
    if "GCS_WGS_1984" not in prj or field_names != ["LEFT_FID", "RIGHT_FID"]:
        raise ValueError("WRI spatial reference or adjacency fields changed")
    county_archive = args.county_archive.read_bytes()
    county_digest = hashlib.sha256(county_archive).hexdigest()
    if (len(county_archive) != EXPECTED_COUNTY_ARCHIVE_BYTES
            or county_digest != EXPECTED_COUNTY_ARCHIVE_SHA256):
        raise ValueError("UBOS county archive size or SHA-256 does not match the retained pin")
    with zipfile.ZipFile(args.county_archive) as county_zip:
        county_shapes = parse_county_shp(county_zip.read("Uganda_county2006.shp"))
        county_attributes = parse_county_dbf(county_zip.read("Uganda_county2006.dbf"))
    if len(county_shapes) != EXPECTED_COUNTY_POLYGONS or len(county_attributes) != EXPECTED_COUNTY_POLYGONS:
        raise ValueError("Unexpected UBOS county polygon/attribute count")

    context = json.loads((args.evidence_dir / "target-context-recovery-116.json").read_text())
    overlay = json.loads((args.evidence_dir / "complete-537-feature-center-overlay.json").read_text())
    centers = {tuple(row["key"]): row["center"] for row in overlay["result"]["per_key"]}
    targets = [row for row in context["rows"] if row["key"][0] == OWNER]
    if len(targets) != 112 or any(row["target"]["target_id"] != TARGET_ID for row in targets):
        raise ValueError("Irumu original key roster or target identity changed")

    nearest_records = collections.Counter()
    side_counts = collections.Counter()
    distance_values = []
    winning_attributes = collections.Counter()
    cross_source_count = collections.Counter()
    for row in targets:
        key = tuple(row["key"])
        if key not in centers:
            raise ValueError(f"Missing retained center for original key {key}")
        x, y = project_utm36n_custom(*centers[key])
        point = (x, y)
        best = None
        for record in records:
            if best is not None and bbox_distance(point, record["bbox"]) > best[0]:
                continue
            candidate = nearest_segment(point, record["parts"])
            if candidate is not None and (best is None or candidate[0] < best[0]):
                best = (candidate[0], candidate[1], record)
        if best is None:
            raise ValueError(f"No WRI line segment found for original key {key}")
        distance, side, record = best
        nearest_records[(record["record_index_zero_based"], record["record_number_header"])] += 1
        side_counts[side] += 1
        distance_values.append(distance)
        attrs = attributes[record["record_index_zero_based"]]
        winning_attributes[(attrs["LEFT_FID"], attrs["RIGHT_FID"])] += 1
        county_hits = []
        for polygon, county in zip(county_shapes, county_attributes):
            xmin, ymin, xmax, ymax, rings = polygon
            if (xmin <= x <= xmax and ymin <= y <= ymax
                    and point_in_rings(x, y, rings)):
                county_hits.append(county)
        if len(county_hits) > 1:
            raise ValueError(f"Overlapping UBOS counties for key {key}; do not infer a single district")
        county_name = county_hits[0]["CNAME_2006"] if county_hits else "outside_all_counties"
        district_name = county_hits[0]["DNAME_2006"] if county_hits else "outside_all_counties"
        cross_source_count[(side, county_name, district_name)] += 1

    ordered_distances = sorted(distance_values)
    median = (ordered_distances[len(ordered_distances) // 2 - 1]
              + ordered_distances[len(ordered_distances) // 2]) / 2
    result = {
        "kind": "cod-residual-930-uganda-2006-district-line-overlay-v1",
        "status": "context-only-no-key-disposition",
        "source_archive_bytes": len(archive),
        "source_archive_sha256": digest,
        "source_feature_count": len(records),
        "county_source_archive_bytes": len(county_archive),
        "county_source_archive_sha256": county_digest,
        "county_polygon_count": len(county_shapes),
        "target_id": TARGET_ID,
        "owner_id": OWNER,
        "target_center_count": len(targets),
        "nearest_line_records": [
            {"zero_based_index": index, "shapefile_record_number": header_number, "centers": count}
            for (index, header_number), count in sorted(nearest_records.items())
        ],
        "nearest_record_adjacency": [
            {"left_fid": left, "right_fid": right, "centers": count}
            for (left, right), count in sorted(winning_attributes.items())
        ],
        "nearest_segment_side_counts": dict(sorted(side_counts.items())),
        "nearest_line_distance_m": {
            "minimum": round(min(distance_values), 3),
            "median": round(median, 3),
            "maximum": round(max(distance_values), 3),
        },
        "cross_source_center_join": [
            {"wri_line_side": side, "ubos_county_2006": county,
             "ubos_district_2006": district, "centers": count}
            for (side, county, district), count in sorted(cross_source_count.items())
        ],
        "fid_identity_assessment": "A bounded spatial join maps the 62 right-side centers (RIGHT_FID=61) to UBOS 2006 counties Ntoroko (31), Bughendera (1), and Bwamba (30); all three UBOS rows name DNAME_2006=BUNDIBUGYO. The other 50 centers are left of the WRI line with LEFT_FID=-1 and fall outside all 164 UBOS counties. This supports identifying FID 61 as Bundibugyo for this local overlap, but is not a direct WRI FID-to-name table or a legal boundary determination.",
        "method": "Parsed WRI polyline/DBF records; projected WGS84 coordinates to UTM zone 36N with the retained UBOS .prj false northing; selected nearest segment by Euclidean distance and assigned side by directed-segment cross product. Only aggregate counts and distances are emitted.",
        "limits": [
            "WRI records contain numeric LEFT_FID/RIGHT_FID values but no district names in the shipped DBF.",
            "The name association uses an independently pinned UBOS 2006 county spatial join and is limited to the inspected Irumu area.",
            "The WRI metadata disclaims accuracy warranties and says the data are not for litigation.",
            "Nearest-line side is not reconstructed into a polygon and does not establish territorial or legal applicability.",
            "This does not resolve the 2006 source discrepancy, the later selected COD geometry disagreement, whole-cell qualification, or the full 930-key disposition.",
        ],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
