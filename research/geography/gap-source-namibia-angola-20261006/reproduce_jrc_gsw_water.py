#!/usr/bin/env python3
"""Reproduce candidate-level pixel summaries from retained JRC GSW v1.5 tiles."""

from __future__ import annotations

import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path

import numpy as np
import rasterio
from rasterio.io import MemoryFile
from rasterio.mask import mask
from rasterio.transform import from_origin
from shapely.geometry import box, shape


ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "sources" / "jrc-gsw-2024"
INPUTS = ROOT / "inputs" / "original-components.geojson"
SOURCE_MANIFEST = SOURCE_DIR / "manifest.json"
INPUT_SET = ROOT / "jrc-gsw-analysis-input-set.json"
OUTPUT = ROOT / "jrc-gsw-water-analysis.json"
POSITIVE_CONTROL = ROOT / "validation-jrc-gsw-positive-control.json"
NEGATIVE_CONTROL = ROOT / "validation-jrc-gsw-negative-control.json"
NODATA = 255
CANDIDATE_SHA256 = "f99f334877c309101afafe56210e40ab2093948e686ec39f98d9c085a42622b9"
SOURCE_MANIFEST_SHA256 = "03e48ad181884b4533861972e078f8a24b762f7a2445fd59ec25fff0c7deb248"
INPUT_SET_SHA256 = "0a4ff34f74e23d667ff9f877ce53fa0188e31fc4cb5c8722b41a85d6c7a6a4a9"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def reconstruct(tile: dict, temp: Path) -> Path:
    target = temp / f"{tile['layer']}_{tile['tile']}.tif"
    digest = hashlib.sha256()
    size = 0
    with target.open("wb") as out:
        for part in tile["parts"]:
            path = SOURCE_DIR / part["path"]
            if path.stat().st_size != part["bytes"] or sha256(path) != part["sha256"]:
                raise ValueError(f"Source part pin mismatch: {path}")
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    out.write(block)
                    digest.update(block)
                    size += len(block)
    if size != tile["original_bytes"] or digest.hexdigest() != tile["original_sha256"]:
        raise ValueError(f"Reassembled source pin mismatch: {tile['layer']} {tile['tile']}")
    return target


def main() -> None:
    if sha256(INPUTS) != CANDIDATE_SHA256:
        raise ValueError("Original candidate geometry input hash mismatch")
    if sha256(SOURCE_MANIFEST) != SOURCE_MANIFEST_SHA256 or sha256(INPUT_SET) != INPUT_SET_SHA256:
        raise ValueError("Reviewed raster source/input manifest hash mismatch")
    manifest = json.loads(SOURCE_MANIFEST.read_text())
    for item in manifest["supporting_files"]:
        path = SOURCE_DIR / item["path"]
        if path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
            raise ValueError(f"Supporting source pin mismatch: {path}")
    features = json.loads(INPUTS.read_text())["features"]
    with tempfile.TemporaryDirectory(prefix="jrc-gsw-") as temp_name:
        temp = Path(temp_name)
        datasets = {}
        for tile in manifest["tiles"]:
            path = reconstruct(tile, temp)
            ds = rasterio.open(path)
            datasets[(tile["layer"], tile["tile"])] = ds
            observed = {
                "crs": str(ds.crs),
                "bounds": [ds.bounds.left, ds.bounds.bottom, ds.bounds.right, ds.bounds.top],
                "resolution_degrees": list(ds.res),
                "width": ds.width,
                "height": ds.height,
                "dtype": ds.dtypes[0],
                "band_count": ds.count,
            }
            if observed != tile["raster_metadata"]:
                raise ValueError(f"Raster metadata differs from reviewed pin for {tile['layer']} {tile['tile']}")

        rows = []
        overall = Counter()
        for index, feature in enumerate(features):
            geom = shape(feature["geometry"])
            row = {
                "component_id": feature["id"],
                "fragment_ids": [x["id"] for x in feature["properties"].get("fragment_bindings", [])],
                "geometry_wkb_sha256": hashlib.sha256(geom.wkb).hexdigest(),
                "pixel_center_rule": "Only cells whose centers are inside the unchanged candidate geometry are counted; edge-only cells are excluded.",
                "layers": {},
            }
            for layer in ("occurrence", "seasonality"):
                values = []
                for lon_tile in ("10E_10S", "20E_10S"):
                    ds = datasets[(layer, lon_tile)]
                    inter = geom.intersection(box(*ds.bounds))
                    if inter.is_empty:
                        continue
                    array, _ = mask(ds, [inter.__geo_interface__], crop=True, all_touched=False, filled=False)
                    values.extend(int(value) for value in array[0].compressed())
                counts = Counter(values)
                no_data = counts.pop(NODATA, 0)
                valid = sum(counts.values())
                if layer == "occurrence":
                    water = sum(counts.get(v, 0) for v in range(1, 101))
                    row["layers"][layer] = {
                        "valid_pixel_centers": valid,
                        "nodata_pixel_centers": no_data,
                        "water_occurrence_gt_0": water,
                        "water_occurrence_gte_50": sum(counts.get(v, 0) for v in range(50, 101)),
                        "water_occurrence_gte_90": sum(counts.get(v, 0) for v in range(90, 101)),
                        "value_counts_0_to_100": {str(v): counts.get(v, 0) for v in range(101)},
                    }
                    overall.update({
                        "occurrence_valid_pixel_centers": valid,
                        "occurrence_nodata_pixel_centers": no_data,
                        "occurrence_water_gt_0": water,
                        "occurrence_water_gte_50": sum(counts.get(v, 0) for v in range(50, 101)),
                        "occurrence_water_gte_90": sum(counts.get(v, 0) for v in range(90, 101)),
                    })
                else:
                    water = sum(counts.get(v, 0) for v in range(1, 13))
                    row["layers"][layer] = {
                        "valid_pixel_centers": valid,
                        "nodata_pixel_centers": no_data,
                        "water_months_gt_0": water,
                        "value_counts_0_to_12": {str(v): counts.get(v, 0) for v in range(13)},
                    }
                    overall.update({
                        "seasonality_valid_pixel_centers": valid,
                        "seasonality_nodata_pixel_centers": no_data,
                        "seasonality_water_months_gt_0": water,
                    })
            rows.append(row)

        for ds in datasets.values():
            ds.close()

    # Small synthetic controls exercise the same center-inclusion and NoData rules.
    profile = {
        "driver": "GTiff", "height": 2, "width": 2, "count": 1,
        "dtype": "uint8", "crs": "EPSG:4326", "transform": from_origin(0, 2, 1, 1),
        "nodata": NODATA,
    }
    with MemoryFile() as memory:
        with memory.open(**profile) as ds:
            ds.write(np.array([[0, 80], [10, NODATA]], dtype="uint8"), 1)
            selected, _ = mask(ds, [box(0, 0, 2, 2).__geo_interface__], crop=True,
                               all_touched=False, filled=False)
            raw_selected = sorted(int(value) for value in selected[0].data.flatten())
            selected_values = sorted(int(value) for value in selected[0].compressed())
            masked_nodata = int(np.ma.getmaskarray(selected[0]).sum())
            if raw_selected != [0, 10, 80, NODATA] or selected_values != [0, 10, 80] or masked_nodata != 1:
                raise ValueError(f"Positive raster/NoData control failed: raw={raw_selected}, valid={selected_values}, masked={masked_nodata}")
            valid = [value for value in selected_values if value != NODATA]
            edge_only = box(0.01, 1.01, 0.49, 1.49)
            edge_selected, _ = mask(ds, [edge_only.__geo_interface__], crop=True,
                                   all_touched=False, filled=False)
            edge_values = sorted(int(value) for value in edge_selected[0].compressed())
            if edge_values:
                raise ValueError(f"Edge-only raster control selected a pixel center: {edge_values}")
            positive = {
                "method_id": "jrc-gsw-pixel-center-overlay",
                "kind": "positive-control",
                "outcome": "passed",
                "fixture": {"crs": "EPSG:4326", "grid": "2x2, 1-degree cells, origin (0,2)",
                            "values_by_row": [[0, 80], [10, 255]], "polygon": [0, 0, 2, 2]},
                "raw_selected_values_including_masked_nodata": raw_selected,
                "selected_values": selected_values,
                "valid_values_after_255_nodata_exclusion": valid,
                "masked_nodata_cells": masked_nodata,
                "expected": [0, 10, 80],
                "edge_only_case": {
                    "polygon": [0.01, 1.01, 0.49, 1.49],
                    "polygon_intersects_cell": True,
                    "contains_any_pixel_center": False,
                    "selected_values": edge_values,
                    "expected": [],
                },
            }
            POSITIVE_CONTROL.write_text(json.dumps(positive, indent=2) + "\n")
            outside = box(2.25, 0.25, 2.75, 0.75)
            if not outside.disjoint(box(*ds.bounds)):
                raise ValueError("Negative raster control geometry must be disjoint")
            try:
                mask(ds, [outside.__geo_interface__], crop=True, all_touched=False, filled=False)
            except ValueError:
                pass
            else:
                raise ValueError("Negative raster control unexpectedly selected a pixel")
            negative = {
                "method_id": "jrc-gsw-pixel-center-overlay",
                "kind": "negative-control",
                "outcome": "passed",
                "fixture": {"crs": "EPSG:4326", "grid": "2x2, 1-degree cells, origin (0,2)",
                            "values_by_row": [[0, 80], [10, 255]], "polygon": [2.25, 0.25, 2.75, 0.75]},
                "selected_values": [],
                "expected": [],
            }
            NEGATIVE_CONTROL.write_text(json.dumps(negative, indent=2) + "\n")

    report = {
        "version": 1,
        "source_manifest": "sources/jrc-gsw-2024/manifest.json",
        "candidate_input": "inputs/original-components.geojson",
        "input_set": "jrc-gsw-analysis-input-set.json",
        "method": {
            "coordinate_reference_system": "EPSG:4326",
            "grid_resolution_degrees": [0.00025, 0.00025],
            "nominal_product_resolution": "approximately 30 m",
            "mask_rule": "Rasterio geometry mask, all_touched=false; count pixel centers inside each original candidate geometry. No reprojection, geometry repair, buffering, or resampling.",
            "nodata_value": NODATA,
            "occurrence_values": "0 = not water; 1-100 = occurrence percentage; 255 = no data, per the retained JRC Data Users Guide.",
            "seasonality_values": "0 = not water; 1-12 = months with water in 2024; 255 = no data, per the retained JRC Data Users Guide.",
            "limits": [
                "Occurrence summarizes March 1984 through December 2024 and does not date individual detections.",
                "Seasonality is the single year 2024 and is not a historical channel or legal boundary record.",
                "The JRC release documents a spatially variable residual co-registration offset at its 2022 Landsat Collection 2 transition, typically sub-pixel but reaching or exceeding one 30 m pixel in some path/rows.",
                "A water-classified pixel within a candidate is physical-reference evidence only; it does not identify a bank, waterbody type, processing cause, territorial assignment, or boundary authority."
            ],
        },
        "aggregate": {
            **dict(overall),
            "component_count": len(rows),
            "components_with_occurrence_water_gt_0": sum(
                row["layers"]["occurrence"]["water_occurrence_gt_0"] > 0 for row in rows),
            "components_with_occurrence_water_gte_50": sum(
                row["layers"]["occurrence"]["water_occurrence_gte_50"] > 0 for row in rows),
            "components_with_occurrence_water_gte_90": sum(
                row["layers"]["occurrence"]["water_occurrence_gte_90"] > 0 for row in rows),
            "components_with_2024_seasonality_water": sum(
                row["layers"]["seasonality"]["water_months_gt_0"] > 0 for row in rows),
        },
        "components": rows,
    }
    OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"output": str(OUTPUT), "components": len(rows), "aggregate": report["aggregate"]}, indent=2))


if __name__ == "__main__":
    main()
