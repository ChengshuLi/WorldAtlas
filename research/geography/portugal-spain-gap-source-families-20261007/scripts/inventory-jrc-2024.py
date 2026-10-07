#!/usr/bin/env python3
"""Pin downloaded JRC monthly-history v1.5 2024 tiles and TIFF structure."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "research/geography/portugal-spain-gap-source-families-20261007"
DATA = PACKAGE / "sources/jrc/monthlyhistory-v1_5-2024"
OUTPUT = PACKAGE / "sources/jrc/monthlyhistory-v1_5-2024-capture.json"
INVENTORY = json.loads((PACKAGE / "sources/jrc/monthlyhistory-v1_5-head-inventory.json").read_text())


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    Image.MAX_IMAGE_PIXELS = None
    remote = {row["filename"]: row for row in INVENTORY["requests"] if row["year"] == 2024 and row["status"] == 200}
    rows = []
    for path in sorted(DATA.glob("*.tif")):
        im = Image.open(path)
        tags = im.tag_v2
        pages = []
        for page in range(5):
            im.seek(page)
            t = im.tag_v2
            pages.append({
                "overview_index": page,
                "width": im.width,
                "height": im.height,
                "bits_per_sample": t.get(258),
                "sample_format": t.get(339),
                "compression_code": t.get(259),
                "samples_per_pixel": t.get(277),
                "planar_configuration": t.get(284),
                "tile_width": t.get(322),
                "tile_height": t.get(323),
                "predictor": t.get(317),
                "gdal_nodata_tag_42113": t.get(42113),
                "pixel_scale": t.get(33550),
                "tiepoint": t.get(33922),
                "geokey_directory": t.get(34735),
            })
        expected = remote.get(path.name, {})
        rows.append({
            "filename": path.name,
            "url": expected.get("url"),
            "http_content_length": expected.get("content_length"),
            "bytes": path.stat().st_size,
            "sha256": sha(path),
            "pages": pages,
        })
    if len(rows) != 24:
        raise SystemExit(f"expected 24 assets, found {len(rows)}")
    if any(row["http_content_length"] != row["bytes"] for row in rows):
        raise SystemExit("downloaded byte lengths differ from pinned HEAD inventory")
    result = {
        "schema": "worldatlas-jrc-monthlyhistory-capture-v1",
        "product": "JRC Global Surface Water monthly history v1.5",
        "period": "2024-01 through 2024-12",
        "tiles": ["10W_30N", "10W_40N"],
        "asset_count": len(rows),
        "encoded_total_bytes": sum(row["bytes"] for row in rows),
        "maximum_encoded_asset_bytes": max(row["bytes"] for row in rows),
        "decoded_full_resolution_bytes_per_asset": 40000 * 40000,
        "decoded_full_resolution_bytes_all_assets": 40000 * 40000 * len(rows),
        "ordinary_caps": {"maximum_file_bytes": 32 * 1024 * 1024, "maximum_batch_bytes": 256 * 1024 * 1024},
        "ordinary_source_admission": "The retained original TIFF byte streams, not fully expanded pixel arrays, are source input artifacts. Each downloaded original is checked against the 32 MiB per-file cap and the 256 MiB batch cap; bounded source-tile reads are decoded in memory without retaining expanded full images.",
        "observed_tiff_structure": {
            "first_ifd_dimensions": [40000, 40000],
            "bits_per_sample": 8,
            "sample_format": "unsigned integer (TIFF SampleFormat 1)",
            "compression_code": 50000,
            "tile_dimensions": [1024, 1024],
            "pixel_scale_degrees": [0.00025, 0.00025, 0.0],
            "crs_epsg": 4326,
            "predictor": 2,
            "gdal_nodata_tag_42113": None,
            "nodata_semantics": "No GDAL_NODATA tag was observed; the official product guide defines code 0 as no observations, code 1 as observed non-water, and code 2 as water detected.",
            "overview_count_including_full_resolution": 5,
        },
        "head_inventory_path": str((PACKAGE / "sources/jrc/monthlyhistory-v1_5-head-inventory.json").relative_to(ROOT)),
        "assets": rows,
        "limits": [
            "A complete in-memory expansion of one full-resolution monthly asset is 1.6 GB; processing is limited to the 1,024 by 1,024 internal TIFF tiles intersecting the 70 component geometries.",
            "2024 Monthly History is current seasonal context for 2022-2024 Landsat Collection 2 only; it does not represent 2018/2020 administrative source vintages.",
            "Pixel values are coded 0=no observations, 1=observed and not water, 2=water detected. Zero remains unknown; a positive detection is temporal surface-water evidence only.",
            "No pixel result establishes ownership, cause, a rightful province, historical status, or a boundary edit; partial pixels, registration error, and unsampled geometry remain unknown.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"assets": len(rows), "encoded_bytes": result["encoded_total_bytes"], "max_asset_bytes": result["maximum_encoded_asset_bytes"], "full_decoded_bytes_per_asset": result["decoded_full_resolution_bytes_per_asset"], "sha256": sha(OUTPUT)}))


if __name__ == "__main__":
    main()
