#!/usr/bin/env python3
"""Validate concrete positive/negative source controls and complete scope closure."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image
from shapely import contains_xy
from shapely.geometry import shape

ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "research/geography/portugal-spain-gap-source-families-20261007"
INDEX = PACKAGE / "inputs/complete-input-index.json"
ADMIN = PACKAGE / "outputs/administrative-source-overlays.json"
APA = PACKAGE / "outputs/apa-wfd-line-overlays.json"
MAPA = PACKAGE / "outputs/mapa-current-snapshot-overlays.json"
JRC = PACKAGE / "outputs/jrc-2024-component-month-summary.json"
MATRIX = PACKAGE / "outputs/source-status-matrix.json"
OUTPUT = PACKAGE / "outputs/validation-controls.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def read_jrc_control(control: dict, zstd: str) -> int:
    path = PACKAGE / "sources/jrc/monthlyhistory-v1_5-2024" / control["source_asset"]
    Image.MAX_IMAGE_PIXELS = None
    image = Image.open(path)
    tags = image.tag_v2
    row, col = control["pixel_row"], control["pixel_column"]
    tile_row, tile_col = row // 1024, col // 1024
    tile_index = tile_row * 40 + tile_col
    with path.open("rb") as stream:
        stream.seek(tags[324][tile_index])
        compressed = stream.read(tags[325][tile_index])
    raw = subprocess.run([zstd, "-d", "-c"], input=compressed, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout
    if len(raw) != 1024 * 1024:
        raise SystemExit("raster control did not decode to exactly one full-resolution TIFF tile")
    differential = np.frombuffer(raw, dtype=np.uint8).reshape((1024, 1024))
    values = np.cumsum(differential, axis=1, dtype=np.uint16).astype(np.uint8)
    source_value = int(values[row % 1024, col % 1024])
    lon, lat = control["pixel_center_lonlat"]
    expected_lon = -10 + (col + 0.5) * 0.00025
    north = 40 if control["tile"] == "10W_30N" else 50
    expected_lat = north - (row + 0.5) * 0.00025
    if abs(lon - expected_lon) > 1e-12 or abs(lat - expected_lat) > 1e-12:
        raise SystemExit("raster control pixel-center coordinates do not match TIFF geotransform")
    geometries = {f["id"]: shape(f["geometry"]) for f in load(PACKAGE / "inputs/selected-70-component-geometries.geojson")["features"]}
    if not contains_xy(geometries[control["component_id"]], lon, lat):
        raise SystemExit("raster control pixel center is outside its pinned component")
    return source_value


def main() -> None:
    index, admin, apa, mapa, jrc, matrix = map(load, (INDEX, ADMIN, APA, MAPA, JRC, MATRIX))
    if index["scope"]["family_count"] != 52 or index["scope"]["component_count"] != 70 or index["scope"]["contact_count"] != 57:
        raise SystemExit("scope roster counts failed")
    if admin["component_count"] != 70 or len(admin["source_products"]) != 2 or apa["component_count"] != 70 or mapa["component_count"] != 70 or jrc["component_count"] != 70 or jrc["family_count"] != 52:
        raise SystemExit("one or more complete-scope outputs are incomplete")
    checks = []
    for product in admin["source_products"]:
        controls = product["controls"]
        positive, negative = controls["positive_control"], controls["negative_control"]
        coverage = controls["coverage_predicate"]
        if not positive["positive_area_overlap"] or positive["intersection_area_m2_equal_area"] <= 0:
            raise SystemExit(f"administrative positive control failed: {product['source_product']}")
        if negative["intersects"] or negative["distance_m_equal_area"] <= 0:
            raise SystemExit(f"administrative negative control failed: {product['source_product']}")
        if coverage["crs"] != "EPSG:6933" or not coverage["positive_control"]["covered"] or coverage["negative_control"]["covered"]:
            raise SystemExit(f"administrative per-feature coverage predicate controls failed: {product['source_product']}")
        checks.append({"method": "full-simplified-admin-overlay", "source_product": product["source_product"], "positive": positive, "negative": negative, "coverage_predicate": coverage})

    positive, negative = apa["controls"]["positive_control"], apa["controls"]["negative_control"]
    if not positive["intersects"] or positive["line_length_inside_component_m"] <= 0 or negative["intersects"] or negative["line_length_inside_component_m"] != 0:
        raise SystemExit("APA WFD positive/negative line controls failed")
    checks.append({"method": "complete-APA-WFD-line-overlay", "positive": positive, "negative": negative})

    positive, negative = mapa["controls"]["positive_control"], mapa["controls"]["negative_control"]
    if not positive["positive_area_overlap"] or positive["intersection_area_m2_equal_area"] <= 0 or negative["intersecting_current_source_feature_count"] != 0:
        raise SystemExit("MAPA current-snapshot positive/negative geometry controls failed")
    checks.append({"method": "MAPA-current-snapshot-overlay", "positive": positive, "negative": negative})

    controls = jrc["raster_controls"]
    expected = {"positive_water_detection": 2, "observed_non_detection": 1, "no_observation": 0}
    zstd = shutil.which("zstd")
    if not zstd:
        raise SystemExit("zstd CLI is required to check source-grid controls")
    for key, code in expected.items():
        control = controls[key]
        source = PACKAGE / "sources/jrc/monthlyhistory-v1_5-2024" / control["source_asset"]
        actual = read_jrc_control(control, zstd)
        if control["expected_source_code"] != code or actual != code or sha(source) != control["source_asset_sha256"]:
            raise SystemExit(f"JRC source-grid control failed: {key}")
    checks.append({"method": "JRC-monthly-history-source-codes", "positive_water_detection": controls["positive_water_detection"], "observed_non_detection": controls["observed_non_detection"], "no_observation_unknown": controls["no_observation"]})

    if len(matrix["families"]) != 52 or len(matrix["components"]) != 70:
        raise SystemExit("source-status matrix scope incomplete")
    if any(f["cause_status"] != "unknown" or f["water_status"] != "unknown" for f in matrix["families"]):
        raise SystemExit("family unknown classifications were changed")
    if any(c["water_status"] != "unknown" or c["ice_status"] != "unknown" or c["ownership_status"] != "unknown" or c["historical_status"] != "unknown" or c["boundary_edit"] is not False for c in matrix["components"]):
        raise SystemExit("component unknown classifications or no-edit condition failed")
    checks.append({"method": "whole-scope-unknown-preservation", "families": 52, "components": 70, "boundary_edits": 0})

    result = {
        "schema": "worldatlas-source-controls-v1",
        "status": "passed",
        "scope": {"families": 52, "components": 70, "contacts": 57, "family_roster_sha256": index["scope"]["family_ids_sha256"], "component_roster_sha256": index["scope"]["component_ids_sha256"], "contact_roster_sha256": index["scope"]["contact_ids_sha256"]},
        "input_hashes": {"complete_input_index": sha(INDEX), "admin_source_overlays": sha(ADMIN), "apa_wfd_overlays": sha(APA), "mapa_current_overlays": sha(MAPA), "jrc_summary": sha(JRC), "source_status_matrix": sha(MATRIX)},
        "checks": checks,
        "limits": ["Controls exercise actual source-positive and source-negative comparisons and the three monthly-history codes; they do not certify source truth or classify any component.", "The no-observation control remains unknown, and a monthly non-detection is not a whole-component land conclusion."],
    }
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    receipts = []
    for row in checks:
        if row["method"] == "full-simplified-admin-overlay":
            slug = row["source_product"].replace(":", "-")
            positive_evidence = dict(row["positive"])
            positive_evidence["coverage_predicate_control"] = row["coverage_predicate"]["positive_control"]
            positive_evidence["coverage_predicate_crs"] = row["coverage_predicate"]["crs"]
            negative_evidence = dict(row["negative"])
            negative_evidence["coverage_predicate_control"] = row["coverage_predicate"]["negative_control"]
            negative_evidence["coverage_predicate_crs"] = row["coverage_predicate"]["crs"]
            receipts.extend([
                (f"admin-{slug}", "positive-control", positive_evidence),
                (f"admin-{slug}", "negative-control", negative_evidence),
            ])
        elif row["method"] == "complete-APA-WFD-line-overlay":
            receipts.extend([
                ("apa-wfd-lines", "positive-control", row["positive"]),
                ("apa-wfd-lines", "negative-control", row["negative"]),
            ])
        elif row["method"] == "MAPA-current-snapshot-overlay":
            receipts.extend([
                ("mapa-current-snapshot", "positive-control", row["positive"]),
                ("mapa-current-snapshot", "negative-control", row["negative"]),
            ])
        elif row["method"] == "JRC-monthly-history-source-codes":
            receipts.extend([
                ("jrc-monthly-history", "positive-control", row["positive_water_detection"]),
                ("jrc-monthly-history", "negative-control", row["observed_non_detection"]),
            ])
    for method_id, kind, evidence in receipts:
        receipt = {"method_id": method_id, "kind": kind, "outcome": "passed", "evidence": evidence}
        path = PACKAGE / "outputs" / f"control-{method_id}-{kind}.json"
        path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "checks": len(checks), "sha256": sha(OUTPUT)}))


if __name__ == "__main__":
    main()
