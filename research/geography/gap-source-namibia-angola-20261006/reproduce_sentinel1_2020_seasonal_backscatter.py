#!/usr/bin/env python3
"""Extract calibrated Sentinel-1 backscatter samples for the gap-family AOIs.

This reports backscatter distributions and threshold sensitivities only. It does
not classify water, infer banks, or make a territorial/boundary determination.
"""

from __future__ import annotations

import hashlib
import json
import math
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from affine import Affine
from rasterio.features import rasterize
from shapely.geometry import Polygon, shape
from shapely.ops import transform as geometry_transform, unary_union


ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "sources" / "sentinel-1-aws"
XML_DIR = SOURCE_DIR / "safe-annotation"
INPUT_COMPONENTS = ROOT / "inputs" / "original-components.geojson"
INPUT_CONTACTS = ROOT / "inputs" / "source-contact-features.geojson"
STAC_FILES = {
    "2020-03": SOURCE_DIR / "search-2020-03.geojson",
    "2020-08": SOURCE_DIR / "search-2020-08.geojson",
}
RECEIPTS = SOURCE_DIR / "safe-annotation-receipts.json"
OUTPUT = ROOT / "sentinel1-2020-seasonal-backscatter.json"
SELECTED_GROUPS = {
    "wet": {87: "2020-03-19", 160: "2020-03-24"},
    "dry": {87: "2020-08-10", 160: "2020-08-15"},
}
POLARIZATIONS = ("vv", "vh")
THRESHOLDS_DB = (-25, -22, -20, -18, -15)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def canonical_s3_url(href: str) -> str:
    prefix = "s3://sentinel-s1-l1c/"
    if not href.startswith(prefix):
        raise ValueError(f"unexpected Sentinel-1 object URI: {href}")
    return "https://sentinel-s1-l1c.s3.amazonaws.com/" + href[len(prefix) :]


def http_head(url: str) -> dict:
    req = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(req, timeout=60) as response:
        return {
            "status": response.status,
            "content_length": int(response.headers.get("Content-Length", "0")),
            "etag": response.headers.get("ETag", "").strip('"'),
            "last_modified": response.headers.get("Last-Modified"),
            "content_type": response.headers.get("Content-Type"),
        }


def source_xml(item: dict, asset_key: str, receipts: dict) -> ET.Element:
    XML_DIR.mkdir(parents=True, exist_ok=True)
    href = item["assets"][asset_key]["href"]
    url = canonical_s3_url(href)
    filename = f"{item['id']}__{asset_key}.xml"
    path = XML_DIR / filename
    if not path.exists():
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=90) as response:
            data = response.read()
            response_headers = {
                "status": response.status,
                "content_length": response.headers.get("Content-Length"),
                "etag": response.headers.get("ETag", "").strip('"'),
                "last_modified": response.headers.get("Last-Modified"),
                "content_type": response.headers.get("Content-Type"),
            }
        path.write_bytes(data)
    data = path.read_bytes()
    receipt = {
        "item_id": item["id"],
        "asset_key": asset_key,
        "source_href": href,
        "source_https_url": url,
        "local_file": str(path.relative_to(SOURCE_DIR)),
        "bytes": len(data),
        "sha256": sha256_bytes(data),
        "http": response_headers if "response_headers" in locals() else http_head(url),
    }
    prior = receipts.get(filename)
    if prior and prior["sha256"] != receipt["sha256"]:
        raise ValueError(f"source XML changed after pinning: {filename}")
    receipts[filename] = receipt
    return ET.fromstring(data)


def parse_vectors(root: ET.Element, vector_tag: str, value_tag: str):
    vectors = []
    for vector in root.findall(f".//{vector_tag}"):
        line_text = vector.findtext("line")
        pixel_text = vector.findtext("pixel")
        value_text = vector.findtext(value_tag)
        if not line_text or not pixel_text or not value_text:
            continue
        pixels = np.fromstring(pixel_text, sep=" ", dtype=np.float64)
        values = np.fromstring(value_text, sep=" ", dtype=np.float64)
        if len(pixels) != len(values) or len(pixels) == 0:
            raise ValueError(f"inconsistent {vector_tag}/{value_tag} LUT vector")
        vectors.append((float(line_text), pixels, values))
    vectors.sort(key=lambda row: row[0])
    if len(vectors) < 2:
        raise ValueError(f"insufficient {vector_tag}/{value_tag} vectors")
    return vectors


def interpolate_lut(vectors, row: float, columns: np.ndarray) -> np.ndarray:
    lines = [vector[0] for vector in vectors]
    position = int(np.searchsorted(lines, row, side="right"))
    hi = min(max(position, 1), len(vectors) - 1)
    lo = hi - 1
    line0, pixels0, values0 = vectors[lo]
    line1, pixels1, values1 = vectors[hi]
    fraction = 0.0 if line1 == line0 else (row - line0) / (line1 - line0)
    value0 = np.interp(columns, pixels0, values0)
    value1 = np.interp(columns, pixels1, values1)
    return value0 * (1.0 - fraction) + value1 * fraction


class GeolocationGrid:
    def __init__(self, product_root: ET.Element):
        raw_points = product_root.findall(".//geolocationGridPoint")
        values = np.array(
            [
                [float(point.findtext(name)) for name in ("line", "pixel", "latitude", "longitude")]
                for point in raw_points
            ],
            dtype=np.float64,
        )
        self.lines = np.unique(values[:, 0])
        self.pixels = np.unique(values[:, 1])
        self.grid = np.full((len(self.lines), len(self.pixels), 4), np.nan, dtype=np.float64)
        line_index = {value: index for index, value in enumerate(self.lines)}
        pixel_index = {value: index for index, value in enumerate(self.pixels)}
        for value in values:
            self.grid[line_index[value[0]], pixel_index[value[1]]] = value
        if not np.isfinite(self.grid).all():
            raise ValueError("SAFE geolocation grid is not a complete rectangle")
        self.tiepoints = values
        boundary = np.concatenate(
            [
                self.grid[0, :, :][..., [3, 2]],
                self.grid[1:, -1, :][..., [3, 2]],
                self.grid[-1, -2::-1, :][..., [3, 2]],
                self.grid[-2:0:-1, 0, :][..., [3, 2]],
            ],
            axis=0,
        )
        self.footprint = Polygon(boundary)
        if not self.footprint.is_valid or self.footprint.area == 0:
            raise ValueError("SAFE geolocation tiepoint perimeter is invalid")

    def _inverse_one(self, lon: float, lat: float) -> tuple[float, float, float]:
        distances = (
            (self.tiepoints[:, 2] - lat) ** 2 * math.cos(math.radians(lat)) ** 2
            + (self.tiepoints[:, 3] - lon) ** 2
        )
        nearest = self.tiepoints[int(np.argmin(distances))]
        nearest_i = int(np.argmin(np.abs(self.lines - nearest[0])))
        nearest_j = int(np.argmin(np.abs(self.pixels - nearest[1])))
        target = np.array([lat, lon], dtype=np.float64)
        solutions = []
        candidate_cells = {
            (
                max(0, min(i, len(self.lines) - 2)),
                max(0, min(j, len(self.pixels) - 2)),
            )
            for i in (nearest_i - 1, nearest_i)
            for j in (nearest_j - 1, nearest_j)
        }
        for row_index, col_index in candidate_cells:
            nodes = self.grid[row_index : row_index + 2, col_index : col_index + 2, 2:4]
            u = v = 0.5
            for _ in range(15):
                estimate = (
                    (1 - u) * (1 - v) * nodes[0, 0]
                    + u * (1 - v) * nodes[0, 1]
                    + (1 - u) * v * nodes[1, 0]
                    + u * v * nodes[1, 1]
                )
                du = (1 - v) * (nodes[0, 1] - nodes[0, 0]) + v * (nodes[1, 1] - nodes[1, 0])
                dv = (1 - u) * (nodes[1, 0] - nodes[0, 0]) + u * (nodes[1, 1] - nodes[0, 1])
                try:
                    delta = np.linalg.solve(np.column_stack((du, dv)), target - estimate)
                except np.linalg.LinAlgError:
                    break
                u += delta[0]
                v += delta[1]
                if np.linalg.norm(delta) < 1e-10:
                    break
            error_m = np.linalg.norm(
                (estimate - target)
                * np.array([111_000.0, 111_000.0 * math.cos(math.radians(lat))])
            )
            if -0.01 <= u <= 1.01 and -0.01 <= v <= 1.01:
                column = self.pixels[col_index] + u * (self.pixels[col_index + 1] - self.pixels[col_index])
                row = self.lines[row_index] + v * (self.lines[row_index + 1] - self.lines[row_index])
                solutions.append((float(error_m), float(column), float(row)))
        if not solutions:
            raise ValueError(f"coordinate outside SAFE geolocation tiepoint grid: {lon},{lat}")
        error_m, column, row = min(solutions)
        return column, row, error_m

    def project(self, geometry):
        geometry = geometry.segmentize(0.00005)
        max_error = 0.0

        def map_coords(x, y, z=None):
            nonlocal max_error
            if np.isscalar(x):
                column, row, error = self._inverse_one(float(x), float(y))
                max_error = max(max_error, error)
                return (column, row) if z is None else (column, row, z)
            mapped = [self._inverse_one(float(lon), float(lat)) for lon, lat in zip(x, y)]
            if mapped:
                max_error = max(max_error, max(value[2] for value in mapped))
            columns = [value[0] for value in mapped]
            rows = [value[1] for value in mapped]
            return (columns, rows) if z is None else (columns, rows, z)

        pixel_geometry = geometry_transform(map_coords, geometry)
        return pixel_geometry, max_error


def window_for(geometry, width: int, height: int):
    min_col, min_row, max_col, max_row = geometry.bounds
    col0 = max(0, int(math.floor(min_col - 0.5)))
    row0 = max(0, int(math.floor(min_row - 0.5)))
    col1 = min(width, int(math.ceil(max_col + 0.5)) + 1)
    row1 = min(height, int(math.ceil(max_row + 0.5)) + 1)
    if col1 <= col0 or row1 <= row0:
        raise ValueError("projected target has an empty raster window")
    return row0, row1, col0, col1


def mask_for(geometry, row0, col0, row1, col1):
    return rasterize(
        [(geometry, 1)],
        out_shape=(row1 - row0, col1 - col0),
        transform=Affine.translation(col0 - 0.5, row0 - 0.5),
        all_touched=False,
        dtype="uint8",
    ).astype(bool)


def distribution(values: np.ndarray, selected: np.ndarray) -> dict:
    valid = selected & np.isfinite(values)
    samples = values[valid]
    if not len(samples):
        return {
            "valid_pixel_centers": 0,
            "backscatter_sigma0_db_quantiles": None,
            "fraction_below_db_threshold": {str(value): None for value in THRESHOLDS_DB},
        }
    quantiles = np.quantile(samples, [0, 0.1, 0.25, 0.5, 0.75, 0.9, 1])
    return {
        "valid_pixel_centers": int(len(samples)),
        "backscatter_sigma0_db_quantiles": {
            key: float(value)
            for key, value in zip(("min", "p10", "p25", "p50", "p75", "p90", "max"), quantiles)
        },
        "fraction_below_db_threshold": {
            str(threshold): float(np.mean(samples < threshold)) for threshold in THRESHOLDS_DB
        },
    }


def calibrate(dn: np.ma.MaskedArray, row0: int, col0: int, calibration, noise):
    rows = np.arange(row0, row0 + dn.shape[0], dtype=np.float64)
    columns = np.arange(col0, col0 + dn.shape[1], dtype=np.float64)
    sigma_lut = np.vstack([interpolate_lut(calibration, row, columns) for row in rows])
    noise_lut = np.vstack([interpolate_lut(noise, row, columns) for row in rows])
    power_numerator = dn.data.astype(np.float64) ** 2 - noise_lut
    noise_floor = (~np.ma.getmaskarray(dn)) & (power_numerator <= 0)
    sigma0 = np.maximum(power_numerator, 0) / (sigma_lut**2)
    sigma0_db = np.full(sigma0.shape, np.nan, dtype=np.float64)
    valid = (~np.ma.getmaskarray(dn)) & (~noise_floor)
    sigma0_db[valid] = 10 * np.log10(sigma0[valid])
    return sigma0_db, noise_floor


def main() -> None:
    components_doc = load_json(INPUT_COMPONENTS)
    contacts_doc = load_json(INPUT_CONTACTS)
    components = [(feature["id"], shape(feature["geometry"])) for feature in components_doc["features"]]
    contacts = [
        (feature["properties"]["shapeID"], feature["properties"]["shapeName"], shape(feature["geometry"]))
        for feature in contacts_doc["features"]
    ]
    if len(components) != 21 or len(contacts) != 10:
        raise ValueError("original input family must contain 21 components and 10 contacts")
    stac = {}
    for month, path in STAC_FILES.items():
        for item in load_json(path)["features"]:
            stac[item["id"]] = item
    groups = {}
    for season, by_orbit in SELECTED_GROUPS.items():
        for orbit, day in by_orbit.items():
            month = day[:7]
            items = [
                item
                for item in stac.values()
                if item["properties"].get("datetime", "").startswith(day)
                and item["properties"].get("sat:relative_orbit") == orbit
            ]
            if not items:
                raise ValueError(f"no retained STAC items for {season}/{day}/orbit-{orbit}")
            groups[(season, orbit)] = items

    component_orbits = {}
    for component_id, component in components:
        eligible = []
        for orbit in (87, 160):
            unions = []
            for season in ("wet", "dry"):
                footprints = [shape(item["geometry"]) for item in groups[(season, orbit)]]
                unions.append(unary_union(footprints))
            if all(union.covers(component) for union in unions):
                eligible.append(orbit)
        if not eligible:
            raise ValueError(f"no consistent wet/dry orbit-footprint coverage for {component_id}")
        component_orbits[component_id] = 87 if 87 in eligible else 160

    receipts = load_json(RECEIPTS) if RECEIPTS.exists() else {}
    scenes = []
    observations = []
    cog_receipts = {}
    scene_footprints_by_group = {}
    data_access = rasterio.Env(
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tiff",
        GDAL_HTTP_MULTIRANGE="YES",
        GDAL_CACHEMAX=128,
    )
    with data_access:
        for (season, orbit), items in sorted(groups.items()):
            selected_components = [
                (component_id, geometry)
                for component_id, geometry in components
                if component_orbits[component_id] == orbit
            ]
            for item in items:
                source_xml(item, "safe-manifest", receipts)
                product_root = source_xml(item, "schema-product-vv", receipts)
                geolocation = GeolocationGrid(product_root)
                scene_footprints_by_group.setdefault((season, orbit), []).append(geolocation.footprint)
                scene_record = {
                    "season": season,
                    "acquisition_datetime": item["properties"]["datetime"],
                    "relative_orbit": orbit,
                    "safe_mission_id": product_root.findtext(".//missionId"),
                    "item_id": item["id"],
                    "geolocation_grid_points": int(len(geolocation.tiepoints)),
                    "geolocation_grid_shape_lines_pixels": [len(geolocation.lines), len(geolocation.pixels)],
                    "geolocation_grid_footprint_valid": bool(geolocation.footprint.is_valid),
                    "processed_targets": 0,
                }
                band_sources = {}
                band_luts = {}
                for polarization in POLARIZATIONS:
                    calibration_root = source_xml(item, f"schema-calibration-{polarization}", receipts)
                    noise_root = source_xml(item, f"schema-noise-{polarization}", receipts)
                    band_luts[polarization] = (
                        parse_vectors(calibration_root, "calibrationVector", "sigmaNought"),
                        parse_vectors(noise_root, "noiseRangeVector", "noiseRangeLut"),
                    )
                    href = item["assets"][polarization]["href"]
                    url = canonical_s3_url(href)
                    cog_receipts.setdefault(url, {"item_id": item["id"], "polarization": polarization, **http_head(url)})
                    band_sources[polarization] = url

                for component_id, component in selected_components:
                    component_part = component.intersection(geolocation.footprint)
                    if component_part.is_empty or component_part.area <= 0:
                        continue
                    try:
                        component_px, transform_error = geolocation.project(component_part)
                    except ValueError:
                        continue
                    windows = [
                        window_for(component_px, 25972, 16853)
                    ]
                    row0, row1, col0, col1 = windows[0]
                    component_mask = mask_for(component_px, row0, col0, row1, col1)
                    if not component_mask.any():
                        continue
                    bands = {}
                    band_arrays = {}
                    for polarization in POLARIZATIONS:
                        with rasterio.open("/vsicurl/" + band_sources[polarization]) as dataset:
                            dn = dataset.read(
                                1,
                                window=((row0, row1), (col0, col1)),
                                masked=True,
                            )
                        sigma_vectors, noise_vectors = band_luts[polarization]
                        calibrated, noise_floor = calibrate(dn, row0, col0, sigma_vectors, noise_vectors)
                        unmasked_count = int((~np.ma.getmaskarray(dn) & component_mask).sum())
                        band_result = distribution(calibrated, component_mask)
                        band_result["input_valid_pixel_centers"] = unmasked_count
                        band_result["nodata_pixel_centers"] = int(component_mask.sum()) - unmasked_count
                        band_result["noise_floor_pixel_centers"] = int((noise_floor & component_mask).sum())
                        bands[polarization] = band_result
                        band_arrays[polarization] = (dn, calibrated, noise_floor)

                    component_contacts = []
                    for contact_id, contact_name, contact in contacts:
                        overlap = component.intersection(contact)
                        if overlap.is_empty or overlap.area <= 0:
                            continue
                        overlap_part = overlap.intersection(geolocation.footprint)
                        if overlap_part.is_empty or overlap_part.area <= 0:
                            continue
                        try:
                            overlap_px, _ = geolocation.project(overlap_part)
                        except ValueError:
                            continue
                        overlap_mask = mask_for(overlap_px, row0, col0, row1, col1) & component_mask
                        if not overlap_mask.any():
                            continue
                        overlap_bands = {}
                        for polarization in POLARIZATIONS:
                            dn, calibrated, noise_floor = band_arrays[polarization]
                            unmasked_count = int((~np.ma.getmaskarray(dn) & overlap_mask).sum())
                            result = distribution(calibrated, overlap_mask)
                            result["input_valid_pixel_centers"] = unmasked_count
                            result["nodata_pixel_centers"] = int(overlap_mask.sum()) - unmasked_count
                            result["noise_floor_pixel_centers"] = int((noise_floor & overlap_mask).sum())
                            overlap_bands[polarization] = result
                        component_contacts.append(
                            {
                                "contact_shape_id": contact_id,
                                "contact_name": contact_name,
                                "valid_pixel_center_count": max(
                                    overlap_bands["vv"]["valid_pixel_centers"],
                                    overlap_bands["vh"]["valid_pixel_centers"],
                                ),
                                "bands": overlap_bands,
                            }
                        )
                    observations.append(
                        {
                            "season": season,
                            "acquisition_datetime": item["properties"]["datetime"],
                            "relative_orbit": orbit,
                            "platform": item["properties"].get("platform"),
                            "pixel_spacing_range_m": item["properties"].get("sar:pixel_spacing_range"),
                            "pixel_spacing_azimuth_m": item["properties"].get("sar:pixel_spacing_azimuth"),
                            "resolution_range_m": item["properties"].get("sar:resolution_range"),
                            "resolution_azimuth_m": item["properties"].get("sar:resolution_azimuth"),
                            "item_id": item["id"],
                            "component_id": component_id,
                            "scene_component_fraction_planar_deg2": float(component_part.area / component.area),
                            "geolocation_inverse_solver_max_residual_m": float(transform_error),
                            "selected_pixel_centers": int(component_mask.sum()),
                            "bands": bands,
                            "candidate_contact_intersections": component_contacts,
                        }
                    )
                    scene_record["processed_targets"] += 1
                scenes.append(scene_record)
                print(
                    json.dumps(
                        {
                            "season": season,
                            "item_id": item["id"],
                            "processed_targets": scene_record["processed_targets"],
                            "observations_so_far": len(observations),
                        }
                    ),
                    flush=True,
                )

    RECEIPTS.write_text(json.dumps(receipts, indent=2, ensure_ascii=False) + "\n")
    group_footprint_unions = {
        group: unary_union(footprints) for group, footprints in scene_footprints_by_group.items()
    }
    component_footprint_coverage = []
    for component_id, component in components:
        orbit = component_orbits[component_id]
        row = {"component_id": component_id, "relative_orbit": orbit}
        for season in ("wet", "dry"):
            footprint = group_footprint_unions[(season, orbit)]
            fraction = component.intersection(footprint).area / component.area
            row[f"{season}_planar_footprint_coverage_fraction"] = float(fraction)
            row[f"{season}_fully_covered_by_tiepoint_footprint_union"] = bool(footprint.covers(component))
        component_footprint_coverage.append(row)
    positive_pairs = []
    all_pairs = []
    for component_id, component in components:
        for contact_id, contact_name, contact in contacts:
            overlap_area = component.intersection(contact).area
            pair = {
                "component_id": component_id,
                "contact_shape_id": contact_id,
                "contact_name": contact_name,
                "positive_area_intersection": overlap_area > 0,
                "planar_intersection_area_deg2": float(overlap_area),
            }
            if overlap_area > 0:
                orbit = component_orbits[component_id]
                for season in ("wet", "dry"):
                    footprint = group_footprint_unions[(season, orbit)]
                    overlap = component.intersection(contact)
                    pair[f"{season}_planar_footprint_coverage_fraction"] = float(
                        overlap.intersection(footprint).area / overlap.area
                    )
                    pair[f"{season}_fully_covered_by_tiepoint_footprint_union"] = bool(
                        footprint.covers(overlap)
                    )
                positive_pairs.append(pair)
            all_pairs.append(pair)
    result = {
        "version": 1,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "method": {
            "purpose": "dated, calibrated C-band SAR backscatter distribution screen within unchanged candidate geometries and their source-contact overlaps",
            "date_windows": SELECTED_GROUPS,
            "polarizations": list(POLARIZATIONS),
            "calibration": "sigma0 linear power = max(DN^2 - noiseRangeLut, 0) / sigmaNought^2; noise subtraction uses ESA Level-1 product specification relation; values are summarized in dB",
            "geolocation": "inverse piecewise-bilinear mapping through the retained SAFE geolocationGridPoint lattice; targets clipped to the outer tiepoint polygon and rasterized at SAR pixel centers",
            "sampling": "only COG windows around candidate and candidate/contact geometries were range-read; full scene objects were not downloaded",
                "thresholds_db": list(THRESHOLDS_DB),
                "threshold_interpretation": "sensitivity summaries only; no value threshold is treated as a water classifier",
            "native_pixel_spacing_m": {"range": 10, "azimuth": 10},
            "nominal_ground_resolution_m": {"range": 20, "azimuth": 22},
            "limits": [
                "No DEM-based terrain correction, radiometric terrain normalization, speckle filtering, or independent ground truth was applied.",
                "The COGs have no embedded CRS/geotransform; geographic placement uses the SAFE annotation tiepoint grid. Absolute registration uncertainty at candidate scale has not been independently measured.",
                "The candidate/contact mask is restricted to the retained input geometry intersected with the scene geolocation-grid footprint.",
                "Adjacent slice overlaps may contribute duplicated centers in per-scene records; do not sum per-scene counts as unique ground pixels.",
                "Two acquisitions represent wet-season and dry-season snapshots only; they do not establish channel persistence, historic course, legal boundary, or bank position.",
                "Backscatter sensitivity thresholds expose distributions and are not water classifications.",
                "For all selected S1B scenes, the measurement COG TIFF ImageDescription tag says Sentinel-1A; STAC product identity and SAFE annotation say Sentinel-1B. This internal metadata conflict is retained and unresolved.",
            ],
        },
        "inputs": {
            "components_file": str(INPUT_COMPONENTS.relative_to(ROOT)),
            "components_sha256": sha256_file(INPUT_COMPONENTS),
            "component_count": len(components),
            "contacts_file": str(INPUT_CONTACTS.relative_to(ROOT)),
            "contacts_sha256": sha256_file(INPUT_CONTACTS),
            "contact_count": len(contacts),
            "contact_pair_count": len(all_pairs),
            "positive_area_contact_pair_count": len(positive_pairs),
        },
        "source_catalog_queries": {
            month: {
                "file": str(path.relative_to(ROOT)),
                "sha256": sha256_file(path),
            }
            for month, path in STAC_FILES.items()
        },
        "source_asset_receipts_file": str(RECEIPTS.relative_to(ROOT)),
        "cog_header_metadata": {
            "file": "sources/sentinel-1-aws/cog-header-metadata.json",
            "sha256": sha256_file(SOURCE_DIR / "cog-header-metadata.json"),
        },
        "cog_object_head_receipts": list(cog_receipts.values()),
        "scenes": scenes,
        "component_orbit_assignment": component_orbits,
        "component_tiepoint_footprint_coverage": component_footprint_coverage,
        "component_observations": observations,
        "candidate_contact_pairs": all_pairs,
        "summary": {
            "component_count": len(components),
            "components_with_wet_season_observation": len(
                {row["component_id"] for row in observations if row["season"] == "wet"}
            ),
            "components_with_dry_season_observation": len(
                {row["component_id"] for row in observations if row["season"] == "dry"}
            ),
            "positive_area_contact_pairs": len(positive_pairs),
            "positive_area_contact_pairs_with_any_wet_season_samples": sum(
                any(
                    row["season"] == "wet"
                    and any(
                        c["contact_shape_id"] == pair["contact_shape_id"] and c["valid_pixel_center_count"] > 0
                        for c in row["candidate_contact_intersections"]
                    )
                    for row in observations
                    if row["component_id"] == pair["component_id"]
                )
                for pair in positive_pairs
            ),
            "positive_area_contact_pairs_with_any_dry_season_samples": sum(
                any(
                    row["season"] == "dry"
                    and any(
                        c["contact_shape_id"] == pair["contact_shape_id"] and c["valid_pixel_center_count"] > 0
                        for c in row["candidate_contact_intersections"]
                    )
                    for row in observations
                    if row["component_id"] == pair["component_id"]
                )
                for pair in positive_pairs
            ),
        },
    }
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
