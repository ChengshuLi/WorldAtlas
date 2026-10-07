#!/usr/bin/env python3
"""Read COG headers only for the Sentinel-1 seasonal scenes used in the packet."""

from __future__ import annotations

import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import rasterio


ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "sources" / "sentinel-1-aws"
PERIODS = ("2020-03", "2020-08")
OUTPUT = SOURCE_DIR / "cog-header-metadata.json"
SCENES = {
    "2020-03-19",
    "2020-03-24",
    "2020-08-10",
    "2020-08-15",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    items = {}
    inputs = {}
    for period in PERIODS:
        path = SOURCE_DIR / f"search-{period}.geojson"
        inputs[period] = {"file": path.name, "sha256": sha256(path)}
        for item in json.loads(path.read_text())["features"]:
            if item["properties"].get("datetime", "")[:10] in SCENES:
                items[item["id"]] = item

    rows = []
    safe_missions = {}
    for item_id in sorted(items):
        xml_path = SOURCE_DIR / "safe-annotation" / f"{item_id}__schema-product-vv.xml"
        if not xml_path.exists():
            raise FileNotFoundError(f"retained SAFE product annotation missing: {xml_path}")
        safe_missions[item_id] = {
            "mission_id": ET.parse(xml_path).findtext(".//missionId"),
            "annotation_sha256": sha256(xml_path),
            "annotation_file": str(xml_path.relative_to(SOURCE_DIR)),
        }
    with rasterio.Env(
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tiff",
        GDAL_HTTP_MULTIRANGE="YES",
        GDAL_CACHEMAX=64,
    ):
        for item_id, item in sorted(items.items()):
            for polarization in ("vv", "vh"):
                asset = item["assets"][polarization]
                url = "https://sentinel-s1-l1c.s3.amazonaws.com/" + asset["href"].split(
                    "sentinel-s1-l1c/", 1
                )[1]
                with rasterio.open("/vsicurl/" + url) as dataset:
                    rows.append(
                        {
                            "item_id": item_id,
                            "datetime": item["properties"].get("datetime"),
                            "platform": item["properties"].get("platform"),
                            "polarization": polarization,
                            "asset_href": asset["href"],
                            "stac_asset_type": asset.get("type"),
                            "stac_raster_bands": asset.get("raster:bands"),
                            "rasterio": {
                                "width": dataset.width,
                                "height": dataset.height,
                                "count": dataset.count,
                                "crs": dataset.crs.to_string() if dataset.crs else None,
                                "transform": list(dataset.transform)[:6],
                                "bounds": list(dataset.bounds),
                                "nodata": dataset.nodata,
                                "dtype": list(dataset.dtypes),
                                "scales": list(dataset.scales),
                                "offsets": list(dataset.offsets),
                                "block_shapes": [list(value) for value in dataset.block_shapes],
                                "tags": dataset.tags(),
                            },
                        }
                    )
    result = {
        "version": 1,
        "purpose": "Header-only metadata inspection; no COG pixel values are read by this script.",
        "rasterio_version": rasterio.__version__,
        "stac_inputs": inputs,
        "scene_item_count": len(items),
        "safe_annotation_mission_ids": safe_missions,
        "asset_count": len(rows),
        "assets": rows,
        "metadata_conflict": {
            "stac_platform": "sentinel-1b",
            "safe_annotation_mission_ids": sorted(
                {entry["mission_id"] for entry in safe_missions.values()}
            ),
            "cog_tifftag_imagedescription_values": sorted(
                {row["rasterio"]["tags"].get("TIFFTAG_IMAGEDESCRIPTION", "") for row in rows}
            ),
            "disposition": "Unresolved internal disagreement; preserve as a source-quality limitation. Do not silently treat the TIFF tag as proof of a different spacecraft or as harmless.",
        },
    }
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
