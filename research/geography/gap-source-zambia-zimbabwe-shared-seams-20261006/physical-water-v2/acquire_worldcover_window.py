#!/usr/bin/env python3
"""Retain the exact WorldCover COG blocks covering the complete #1234 extent.

This is byte acquisition only. It does not decode pixels or run GIS.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


BASE = Path(__file__).resolve().parent
SOURCE_DIR = BASE / "sources" / "worldcover-S18E027"
MANIFEST = BASE / "worldcover-source-ranges.json"
URL = (
    "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/"
    "ESA_WorldCover_10m_2021_v200_S18E027_Map.tif"
)
EXPECTED_ETAG = '"3b512e03391fd7d7f63b217a5a31e895-20"'
EXPECTED_LAST_MODIFIED = "Wed, 26 Oct 2022 12:46:55 GMT"
EXPECTED_OBJECT_BYTES = 161_671_883
EXPECTED_TIFF_HEADER_BYTES = 131_072
EXPECTED_TILE_COUNT = 1_296
EXPECTED_TILE_WIDTH = 1_024
EXPECTED_TILE_HEIGHT = 1_024
EXPECTED_TILE_COLUMNS = 36
EXPECTED_PIXEL_BYTES = 1
EXPECTED_COMPRESSION = 8  # Deflate
EXPECTED_PREDICTOR = 1
EXPECTED_PIXEL_SCALE = (1 / 12_000, 1 / 12_000, 0.0)
EXPECTED_TIEPOINT = (0.0, 0.0, 0.0, 27.0, -15.0, 0.0)
BBOX = (28.8483, -16.0782, 29.617694117647066, -15.64946701104665)
ORIGIN_X, ORIGIN_Y = 27.0, -15.0
PIXEL_DEGREES = 1 / 12_000


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def get(url: str, headers: dict[str, str], *, method: str = "GET"):
    request = Request(url, headers=headers, method=method)
    with urlopen(request, timeout=45) as response:
        body = response.read() if method != "HEAD" else b""
        return response.status, dict(response.headers.items()), body


def metadata_probe() -> dict:
    status, headers, _ = get(URL, {"User-Agent": "WorldAtlas-evidence/1"}, method="HEAD")
    observed = {
        "status": status,
        "etag": headers.get("ETag"),
        "last_modified": headers.get("Last-Modified"),
        "content_length": int(headers.get("Content-Length", "-1")),
        "accept_ranges": headers.get("Accept-Ranges"),
    }
    expected = {
        "status": 200,
        "etag": EXPECTED_ETAG,
        "last_modified": EXPECTED_LAST_MODIFIED,
        "content_length": EXPECTED_OBJECT_BYTES,
        "accept_ranges": "bytes",
    }
    if observed != expected:
        raise RuntimeError(f"COG object metadata changed: {observed!r}")
    return observed


def get_range(start: int, length: int) -> tuple[bytes, dict]:
    end = start + length - 1
    status, headers, body = get(
        URL,
        {
            "User-Agent": "WorldAtlas-evidence/1",
            "Range": f"bytes={start}-{end}",
            "If-Match": EXPECTED_ETAG,
        },
    )
    content_range = headers.get("Content-Range")
    expected_range = f"bytes {start}-{end}/{EXPECTED_OBJECT_BYTES}"
    if (
        status != 206
        or content_range != expected_range
        or headers.get("ETag") != EXPECTED_ETAG
        or headers.get("Last-Modified") != EXPECTED_LAST_MODIFIED
        or int(headers.get("Content-Length", "-1")) != length
        or len(body) != length
    ):
        raise RuntimeError(
            f"Range response mismatch for {start}-{end}: status={status}, "
            f"Content-Range={content_range!r}, ETag={headers.get('ETag')!r}, "
            f"bytes={len(body)}"
        )
    receipt = {
        "request_range": f"bytes={start}-{end}",
        "if_match": EXPECTED_ETAG,
        "status": status,
        "content_range": content_range,
        "etag": headers["ETag"],
        "last_modified": headers["Last-Modified"],
        "content_length": length,
        "sha256": sha256(body),
    }
    return body, receipt


TIFF_TYPE_SIZE = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8, 11: 4, 12: 8}


def parse_ifd(data: bytes) -> dict[int, tuple[int, int, bytes]]:
    if data[:4] != b"II*\x00":
        raise RuntimeError("Expected a little-endian classic TIFF header")
    ifd = struct.unpack_from("<I", data, 4)[0]
    count = struct.unpack_from("<H", data, ifd)[0]
    tags = {}
    for i in range(count):
        pos = ifd + 2 + 12 * i
        tag, typ, n = struct.unpack_from("<HHI", data, pos)
        size = TIFF_TYPE_SIZE.get(typ)
        if size is None:
            raise RuntimeError(f"Unsupported TIFF field type {typ} for tag {tag}")
        byte_count = size * n
        if byte_count <= 4:
            raw = data[pos + 8 : pos + 8 + byte_count]
        else:
            value_offset = struct.unpack_from("<I", data, pos + 8)[0]
            raw = data[value_offset : value_offset + byte_count]
        if len(raw) != byte_count:
            raise RuntimeError(f"TIFF tag {tag} extends outside the retained IFD range")
        tags[tag] = (typ, n, raw)
    return tags


def values(tags: dict, tag: int) -> tuple:
    typ, count, raw = tags[tag]
    formats = {3: "H", 4: "I", 12: "d"}
    if typ not in formats:
        raise RuntimeError(f"Unexpected TIFF type {typ} for numeric tag {tag}")
    return struct.unpack("<" + formats[typ] * count, raw)


def assert_source_metadata(header: bytes) -> dict:
    tags = parse_ifd(header)
    expected_tags = {
        256: 36_000,
        257: 36_000,
        259: EXPECTED_COMPRESSION,
        277: 1,
        258: 8,
        317: EXPECTED_PREDICTOR,
        322: EXPECTED_TILE_WIDTH,
        323: EXPECTED_TILE_HEIGHT,
    }
    for tag, expected in expected_tags.items():
        actual = values(tags, tag)
        actual = actual[0] if len(actual) == 1 else actual
        if actual != expected:
            raise RuntimeError(f"Unexpected TIFF tag {tag}: {actual!r} != {expected!r}")
    scale = values(tags, 33550)
    tiepoint = values(tags, 33922)
    if not all(math.isclose(a, b, rel_tol=0, abs_tol=1e-15) for a, b in zip(scale, EXPECTED_PIXEL_SCALE)):
        raise RuntimeError(f"Unexpected ModelPixelScale: {scale!r}")
    if not all(math.isclose(a, b, rel_tol=0, abs_tol=1e-12) for a, b in zip(tiepoint, EXPECTED_TIEPOINT)):
        raise RuntimeError(f"Unexpected ModelTiepoint: {tiepoint!r}")
    offsets, counts = values(tags, 324), values(tags, 325)
    if len(offsets) != EXPECTED_TILE_COUNT or len(counts) != EXPECTED_TILE_COUNT:
        raise RuntimeError("Unexpected TIFF tile table length")
    metadata = tags[42112][2].decode("ascii")
    required_metadata = [
        "algorithm_version\">V2.0.0",
        "product_crs\">EPSG:4326",
        "product_grid\">3x3 degree tiling grid",
        "product_tile\">S18E027",
        "time_start\">2021-01-01T00:00:00Z",
        "time_end\">2021-12-31T23:59:59Z",
        "license\">CC-BY 4.0",
        "80  Permanent water bodies",
        "90  Herbaceous wetland",
    ]
    for item in required_metadata:
        if item not in metadata:
            raise RuntimeError(f"Missing expected GDAL metadata item: {item}")
    return {"tags": tags, "offsets": offsets, "counts": counts, "metadata_xml": metadata}


def pixel_window() -> tuple[int, int, int, int]:
    west, south, east, north = BBOX
    col0 = math.floor((west - ORIGIN_X) / PIXEL_DEGREES)
    col1 = math.ceil((east - ORIGIN_X) / PIXEL_DEGREES)
    row0 = math.floor((ORIGIN_Y - north) / PIXEL_DEGREES)
    row1 = math.ceil((ORIGIN_Y - south) / PIXEL_DEGREES)
    if not (0 <= col0 < col1 <= 36_000 and 0 <= row0 < row1 <= 36_000):
        raise RuntimeError("Issue extent lies outside the retained WorldCover tile")
    return col0, col1, row0, row1


def main() -> None:
    if MANIFEST.exists() or SOURCE_DIR.exists():
        raise RuntimeError("Output already exists; preserve it and inspect instead of overwriting")
    head_before = metadata_probe()
    SOURCE_DIR.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc).isoformat()

    header, header_receipt = get_range(0, EXPECTED_TIFF_HEADER_BYTES)
    (SOURCE_DIR / "ifd-range-0-131071.bin").write_bytes(header)
    parsed = assert_source_metadata(header)
    offsets, counts = parsed["offsets"], parsed["counts"]
    col0, col1, row0, row1 = pixel_window()
    tile_col0, tile_col1 = col0 // EXPECTED_TILE_WIDTH, (col1 - 1) // EXPECTED_TILE_WIDTH
    tile_row0, tile_row1 = row0 // EXPECTED_TILE_HEIGHT, (row1 - 1) // EXPECTED_TILE_HEIGHT
    expected = [(r, c) for r in range(tile_row0, tile_row1 + 1) for c in range(tile_col0, tile_col1 + 1)]
    if len(expected) != 60:
        raise RuntimeError(f"Unexpected selected tile-block count: {len(expected)}")

    blocks = []
    for tile_row, tile_col in expected:
        index = tile_row * EXPECTED_TILE_COLUMNS + tile_col
        start, length = offsets[index], counts[index]
        payload, receipt = get_range(start, length)
        relative = f"block-r{tile_row:02d}-c{tile_col:02d}.bin"
        (SOURCE_DIR / relative).write_bytes(payload)
        blocks.append(
            {
                "tile_index": index,
                "tile_row": tile_row,
                "tile_column": tile_col,
                "pixel_rows": [tile_row * EXPECTED_TILE_HEIGHT, (tile_row + 1) * EXPECTED_TILE_HEIGHT],
                "pixel_columns": [tile_col * EXPECTED_TILE_WIDTH, (tile_col + 1) * EXPECTED_TILE_WIDTH],
                "file": f"sources/worldcover-S18E027/{relative}",
                "encoded_bytes": length,
                "decoded_bytes": EXPECTED_TILE_WIDTH * EXPECTED_TILE_HEIGHT * EXPECTED_PIXEL_BYTES,
                "sha256": receipt["sha256"],
                "http": receipt,
            }
        )

    head_after = metadata_probe()
    if head_before != head_after:
        raise RuntimeError("WorldCover COG metadata changed during range acquisition")
    manifest = {
        "version": 1,
        "acquisition_started_at": started,
        "acquisition_finished_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "id": "esa-worldcover-2021-v200-s18e027",
            "url": URL,
            "etag": EXPECTED_ETAG,
            "last_modified": EXPECTED_LAST_MODIFIED,
            "whole_object_bytes": EXPECTED_OBJECT_BYTES,
            "whole_object_sha256": None,
            "whole_object_sha256_note": "No whole-object digest was observed or computed; ETag is multipart and is not represented as a whole-file SHA-256.",
            "classification_period_utc": ["2021-01-01T00:00:00Z", "2021-12-31T23:59:59Z"],
            "product_version": "V2.0.0",
            "crs": "EPSG:4326",
            "pixel_scale_degrees": list(EXPECTED_PIXEL_SCALE),
            "pixel_origin_lonlat": [27.0, -15.0],
            "tile_bounds_lonlat": [27.0, -18.0, 30.0, -15.0],
            "tile_dimensions": [36_000, 36_000],
            "tile_pixels": "1-band 8-bit categorical map",
            "compression": "TIFF Deflate; Predictor=1",
            "class_80": "Permanent water bodies",
            "class_90": "Herbaceous wetland; not automatically treated as open water",
            "license": "CC BY 4.0",
            "metadata_xml_sha256": sha256(parsed["metadata_xml"].encode("ascii")),
            "metadata_xml": parsed["metadata_xml"],
        },
        "issue_extent_lonlat": list(BBOX),
        "complete_pixel_window": {
            "columns_half_open": [col0, col1],
            "rows_half_open": [row0, row1],
            "dimensions": [col1 - col0, row1 - row0],
            "decoded_bytes": (col1 - col0) * (row1 - row0) * EXPECTED_PIXEL_BYTES,
        },
        "tile_block_grid": {"dimensions": [EXPECTED_TILE_COLUMNS, 36], "block_dimensions": [EXPECTED_TILE_WIDTH, EXPECTED_TILE_HEIGHT]},
        "ifd_metadata_range": {**header_receipt, "file": "sources/worldcover-S18E027/ifd-range-0-131071.bin"},
        "head_before": head_before,
        "head_after": head_after,
        "selected_block_count": len(blocks),
        "selected_encoded_bytes": sum(row["encoded_bytes"] for row in blocks),
        "selected_decoded_bytes": sum(row["decoded_bytes"] for row in blocks),
        "blocks": blocks,
        "limits": [
            "The retained blocks cover the full issue bounding box and must still be checked against every complete component and contact geometry before classification.",
            "This retains the exact source byte ranges used for the bounded region, not the entire 3x3 degree COG or a whole-object checksum.",
            "The mapped class and its published accuracy are not candidate-specific shoreline or registration accuracy.",
            "Absence of permanent-water class does not prove dry land; herbaceous wetland remains a separate class.",
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    total_encoded = sum(row["encoded_bytes"] for row in blocks) + len(header)
    print(json.dumps({"status": "complete", "selected_blocks": len(blocks), "encoded_bytes_including_ifd": total_encoded, "decoded_selected_blocks": manifest["selected_decoded_bytes"], "candidate_window_pixels": manifest["complete_pixel_window"]["decoded_bytes"], "manifest": str(MANIFEST)}, indent=2))


if __name__ == "__main__":
    main()
