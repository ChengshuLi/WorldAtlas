#!/usr/bin/env python3
"""Summarize only source-grid pixel centers inside the pinned 70 components."""

from __future__ import annotations

import collections
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image
from shapely.geometry import box, shape
from shapely import contains_xy


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "research/geography/portugal-spain-gap-source-families-20261007"
DATA = PACKAGE / "sources/jrc/monthlyhistory-v1_5-2024"
GEOMETRY_FILE = PACKAGE / "inputs/selected-70-component-geometries.geojson"
PLAN_FILE = PACKAGE / "inputs/jrc-2024-window-plan.json"
OUTPUT = PACKAGE / "outputs/jrc-2024-component-month-summary.json"
PIXEL = 0.00025
SIZE = 40000
BLOCK = 1024


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def file_name(tile: str, month: int) -> Path:
    return DATA / f"monthlyhistory_{tile}_v1_5_2024_{month:02d}.tif"


def decode_tile(path: Path, row: int, col: int, zstd: str) -> np.ndarray:
    Image.MAX_IMAGE_PIXELS = None
    image = Image.open(path)
    tags = image.tag_v2
    index = row * 40 + col
    offsets = tags.get(324)
    bytecounts = tags.get(325)
    if offsets is None or bytecounts is None:
        raise RuntimeError(f"missing full-resolution tile index in {path.name}")
    with path.open("rb") as stream:
        stream.seek(offsets[index])
        compressed = stream.read(bytecounts[index])
    result = subprocess.run([zstd, "-d", "-c"], input=compressed, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    if len(result.stdout) != BLOCK * BLOCK:
        raise RuntimeError(f"unexpected tile expansion in {path.name}: {len(result.stdout)} bytes")
    differential = np.frombuffer(result.stdout, dtype=np.uint8).reshape((BLOCK, BLOCK))
    # TIFF Predictor 2: byte-wise horizontal differencing for this 8-bit,
    # single-sample band. Modulo-256 cumulative sum reconstructs source codes.
    return np.cumsum(differential, axis=1, dtype=np.uint16).astype(np.uint8)


def main() -> None:
    zstd = shutil.which("zstd")
    if not zstd:
        raise SystemExit("zstd command is required to decode TIFF compression code 50000")
    plan = json.loads(PLAN_FILE.read_text())
    index = json.loads((PACKAGE / "inputs/complete-input-index.json").read_text())
    geoms = {f["id"]: shape(f["geometry"]) for f in json.loads(GEOMETRY_FILE.read_text())["features"]}
    if len(geoms) != 70 or plan["scope_component_count"] != 70:
        raise SystemExit("exact 70-component input required")
    unique_tiles = sorted({tuple(tile) for row in plan["components"] for tile in row["candidate_full_resolution_tiles"]})
    month_rows = []
    component_positive = {fid: set() for fid in geoms}
    component_sampled = collections.Counter()
    component_total_codes = collections.defaultdict(collections.Counter)
    component_families = collections.defaultdict(set)
    component_contacts = collections.defaultdict(set)
    raster_controls = {}
    family_rows = {row["id"]: row for row in index["scope"]["family_component_contact_rows"]}
    for family_id, family in family_rows.items():
        for fid in family["component_ids"]:
            component_families[fid].add(family_id)
            component_contacts[fid].update(family["contact_ids"])

    for month in range(1, 13):
        for north, tr, tc in unique_tiles:
            tile_name = "10W_30N" if north == 40 else "10W_40N"
            path = file_name(tile_name, month)
            values = decode_tile(path, tr, tc, zstd)
            west = -10 + tc * BLOCK * PIXEL
            north_edge = north - tr * BLOCK * PIXEL
            for fid, geom in geoms.items():
                minx, miny, maxx, maxy = geom.bounds
                left = max(0, int(np.floor((minx - west) / PIXEL)))
                right = min(BLOCK, int(np.ceil((maxx - west) / PIXEL)))
                top = max(0, int(np.floor((north_edge - maxy) / PIXEL)))
                bottom = min(BLOCK, int(np.ceil((north_edge - miny) / PIXEL)))
                if left >= right or top >= bottom:
                    continue
                x = west + (np.arange(left, right) + 0.5) * PIXEL
                y = north_edge - (np.arange(top, bottom) + 0.5) * PIXEL
                xx, yy = np.meshgrid(x, y)
                mask = contains_xy(geom, xx, yy)
                if not mask.any():
                    continue
                block = values[top:bottom, left:right]
                samples = block[mask]
                counts = collections.Counter(map(int, samples))
                for code, label in ((2, "positive_water_detection"), (1, "observed_non_detection"), (0, "no_observation")):
                    if label not in raster_controls and counts.get(code, 0):
                        rel_rows, rel_cols = np.nonzero(mask & (block == code))
                        rel_r, rel_c = int(rel_rows[0]), int(rel_cols[0])
                        pixel_row = tr * BLOCK + top + rel_r
                        pixel_col = tc * BLOCK + left + rel_c
                        north = int(north)
                        raster_controls[label] = {
                            "component_id": fid,
                            "month": f"2024-{month:02d}",
                            "tile": tile_name,
                            "pixel_row": pixel_row,
                            "pixel_column": pixel_col,
                            "pixel_center_lonlat": [-10 + (pixel_col + 0.5) * PIXEL, north - (pixel_row + 0.5) * PIXEL],
                            "expected_source_code": code,
                            "source_asset": path.name,
                            "source_asset_sha256": sha(path),
                        }
                component_sampled[fid] += len(samples)
                component_total_codes[fid].update(counts)
                for code, count in counts.items():
                    if code == 2:
                        rr, cc = np.nonzero(mask & (block == 2))
                        for r, c in zip(rr, cc):
                            source_row = int((90 - north) / PIXEL) + tr * BLOCK + top + int(r)
                            source_col = tc * BLOCK + left + int(c)
                            component_positive[fid].add(source_row * SIZE + source_col)
                month_rows.append({
                    "month": f"2024-{month:02d}",
                    "component_id": fid,
                    "raster_tile": tile_name,
                    "internal_tile_row": tr,
                    "internal_tile_column": tc,
                    "source_grid_pixel_centers": len(samples),
                    "codes": {str(code): counts.get(code, 0) for code in sorted(set(counts) | {0, 1, 2, 255})},
                })

    unexpected = {fid: {str(code): n for code, n in codes.items() if code not in (0, 1, 2)} for fid, codes in component_total_codes.items()}
    unexpected = {fid: v for fid, v in unexpected.items() if v}
    if unexpected:
        raise SystemExit(f"unexpected monthly-history classes found: {json.dumps(unexpected)[:1000]}")
    if set(raster_controls) != {"positive_water_detection", "observed_non_detection", "no_observation"}:
        raise SystemExit(f"required real raster controls are unavailable: {sorted(raster_controls)}")
    per_component = []
    for fid in sorted(geoms):
        codes = component_total_codes[fid]
        per_component.append({
            "component_id": fid,
            "source_family_ids": sorted(component_families[fid]),
            "source_contact_ids": sorted(component_contacts[fid]),
            "source_grid_pixel_centers_sampled_per_month_sum": component_sampled[fid],
            "source_grid_pixel_centers_with_water_detected_in_any_2024_month": len(component_positive[fid]),
            "component_month_code_counts": {str(code): codes.get(code, 0) for code in (0, 1, 2)},
            "month_rows": [r for r in month_rows if r["component_id"] == fid],
            "interpretation": "Code 2 is a positive monthly water detection; code 1 is observed non-water for that month; code 0 is no observation and remains unknown. Counts are pixel centers, not area or classification of the whole component.",
        })
    per_family = []
    for family_id, family in sorted(family_rows.items()):
        members = [row for row in per_component if family_id in row["source_family_ids"]]
        per_family.append({
            "family_id": family_id,
            "source_contact_ids": family["contact_ids"],
            "component_ids": family["component_ids"],
            "component_count": len(members),
            "components_with_any_2024_water_detection": sum(row["source_grid_pixel_centers_with_water_detected_in_any_2024_month"] > 0 for row in members),
            "component_month_pixel_code_counts": {str(code): sum(int(row["component_month_code_counts"][str(code)]) for row in members) for code in (0, 1, 2)},
            "cause_status": family.get("cause_status", "unknown"),
            "interpretation": "Family totals aggregate dated pixel-center observations for diagnostics; they do not classify the family, components, ownership, cause, or historical state.",
        })
    result = {
        "schema": "worldatlas-jrc-2024-component-month-summary-v1",
        "component_roster_sha256": plan["component_roster_sha256"],
        "geometry_input_sha256": plan["selected_geometry_file"]["sha256"],
        "raster_capture_manifest_sha256": sha(PACKAGE / "sources/jrc/monthlyhistory-v1_5-2024-capture.json"),
        "months": [f"2024-{m:02d}" for m in range(1, 13)],
        "unique_internal_full_resolution_tiles": len(unique_tiles),
        "bounded_decoded_tile_blocks": len(unique_tiles) * 12,
        "bounded_decoded_tile_bytes": len(unique_tiles) * 12 * BLOCK * BLOCK,
        "decoder": {"name": "Zstandard CLI", "version": subprocess.run([zstd, "--version"], check=True, text=True, capture_output=True).stdout.strip()},
        "component_count": len(per_component),
        "family_count": len(per_family),
        "component_month_tile_row_count": len(month_rows),
        "raster_controls": raster_controls,
        "families": per_family,
        "components": per_component,
        "limits": [
            "Only internal TIFF tiles intersecting the target geometries were decoded; no full 40,000 by 40,000 raster was expanded.",
            "Pixel-center inclusion is a sampling rule. Partial cell intersections, geometry between centers, and unsampled remainder stay unknown.",
            "Monthly water detection is dated observational context only. Non-detection in one month does not establish dry ground; no result establishes ownership, cause, rightful province, historical status, or a boundary edit.",
            "The 2024 product does not match the 2018 and 2020 administrative source vintages, and Landsat Collection 1/2 co-registration can vary spatially."
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"component_count": len(per_component), "component_month_rows": len(month_rows), "decoded_blocks": result["bounded_decoded_tile_blocks"], "decoded_bytes": result["bounded_decoded_tile_bytes"], "components_with_2024_water_detection": sum(bool(v) for v in component_positive.values()), "sha256": sha(OUTPUT)}))


if __name__ == "__main__":
    main()
