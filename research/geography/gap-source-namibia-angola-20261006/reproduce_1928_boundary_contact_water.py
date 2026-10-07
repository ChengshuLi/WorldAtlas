#!/usr/bin/env python3
"""Bind the 1928 Kakeri survey record and JRC water observations to this scope.

The treaty record supplies historical boundary evidence, not a modern river
edge. Contact water summaries are pixel-center counts over each original
candidate/contact intersection, from the already retained JRC raster tiles.
"""

from __future__ import annotations

import hashlib
import json
import argparse
import sys
import tempfile
from collections import Counter
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import geometry_mask, geometry_window
from rasterio.io import MemoryFile
from shapely.geometry import box, shape
from shapely.ops import unary_union


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
PACKET = "research/geography/gap-source-namibia-angola-20261006/"
SOURCE = ROOT / "sources" / "jrc-gsw-2024"
COMPONENTS = ROOT / "inputs" / "original-components.geojson"
CONTACTS = ROOT / "inputs" / "source-contact-features.geojson"
JRC_ANALYSIS = ROOT / "jrc-gsw-water-analysis.json"
MANIFEST = SOURCE / "manifest.json"
LON_TREATY = ROOT / "sources" / "historical-boundary" / "lon-treaty-series-vol-129-1932.pdf"
IBS120 = ROOT / "sources" / "historical-boundary" / "ibs120-1972.pdf"
TREATY_1926 = ROOT / "sources" / "uk-treaty-series-1926-ts-29.pdf"
OUTPUT = ROOT / "historical-boundary-contact-water-assessment.json"
NODATA = 255
BASELINE_COMMIT = "adff87b88ae66de8f6afbbcb1c68bd8cbba82f45"
BASELINE_FILES = [
    {'path': 'research/geography/gap-source-namibia-angola-20261006/inputs/original-components.geojson', 'bytes': 23958, 'sha256': 'f99f334877c309101afafe56210e40ab2093948e686ec39f98d9c085a42622b9', 'hash_kind': 'file-bytes'},
    {'path': 'research/geography/gap-source-namibia-angola-20261006/inputs/source-contact-features.geojson', 'bytes': 46722, 'sha256': '472ee9003155eb62c9e9aa7bfdff0e28dfab13a8c1cc18b2a30ca6b705cc2f14', 'hash_kind': 'file-bytes'},
    {'path': 'research/geography/gap-source-namibia-angola-20261006/jrc-gsw-water-analysis.json', 'bytes': 74139, 'sha256': 'bc3a0002d6822ddf0ed12e010f52461fb27b28b028abab11673f254be64fd73c', 'hash_kind': 'file-bytes'},
    {'path': 'research/geography/gap-source-namibia-angola-20261006/sources/jrc-gsw-2024/manifest.json', 'bytes': 5317, 'sha256': '03e48ad181884b4533861972e078f8a24b762f7a2445fd59ec25fff0c7deb248', 'hash_kind': 'file-bytes'},
    {'path': 'research/geography/gap-source-namibia-angola-20261006/sources/uk-treaty-series-1926-ts-29.pdf', 'bytes': 195690, 'sha256': '120edb084074e033786cb544c4bc8d0046b3b8b001c7afdb80a47e1a972520de', 'hash_kind': 'file-bytes'},
    {'path': 'scripts/evidence/immutable.py', 'bytes': 17414, 'sha256': 'a3667cecd88b2862e61a3ce72778e179535d92fbf19b5cd7c5b112722926da46', 'hash_kind': 'file-bytes'},
    {'path': 'research/geography/gap-source-namibia-angola-20261006/sources/jrc-gsw-2024/occurrence_10E_10S.part-aa', 'bytes': 30000000, 'sha256': 'c7aa305b53357ae6ff043a91aaf197231094ce5369373d56ca9b216f9502e411', 'hash_kind': 'file-bytes'},
    {'path': 'research/geography/gap-source-namibia-angola-20261006/sources/jrc-gsw-2024/occurrence_10E_10S.part-ab', 'bytes': 6860540, 'sha256': 'acbf5c34e50f09a469f89831507afb5e457856aa5f0a209d42ddabdd35aaca31', 'hash_kind': 'file-bytes'},
    {'path': 'research/geography/gap-source-namibia-angola-20261006/sources/jrc-gsw-2024/occurrence_20E_10S.part-aa', 'bytes': 30000000, 'sha256': '4cc33eeb599e90f3b92d8ed2db5daa5640276517922dc95c9707d26e14cfc24b', 'hash_kind': 'file-bytes'},
    {'path': 'research/geography/gap-source-namibia-angola-20261006/sources/jrc-gsw-2024/occurrence_20E_10S.part-ab', 'bytes': 11757444, 'sha256': '079f0d1b30e1535c6d20a9ce0cb39b79cb3ef8095bdb4227006e2332d2e4a96c', 'hash_kind': 'file-bytes'},
    {'path': 'research/geography/gap-source-namibia-angola-20261006/sources/jrc-gsw-2024/seasonality_10E_10S.tif', 'bytes': 18621860, 'sha256': '222564e5f80e660c7122946f62ec92ca19219f1007ec9eb75471b779951934dc', 'hash_kind': 'file-bytes'},
    {'path': 'research/geography/gap-source-namibia-angola-20261006/sources/jrc-gsw-2024/seasonality_20E_10S.tif', 'bytes': 20100950, 'sha256': '08f6d1c0ad855034f24aa5c5f5b90cbcfd50450a38ff1a69bd327d6efda1801b', 'hash_kind': 'file-bytes'},
]
INPUT_HASHES = {
    "components": "f99f334877c309101afafe56210e40ab2093948e686ec39f98d9c085a42622b9",
    "contacts": "472ee9003155eb62c9e9aa7bfdff0e28dfab13a8c1cc18b2a30ca6b705cc2f14",
    "jrc_analysis": "bc3a0002d6822ddf0ed12e010f52461fb27b28b028abab11673f254be64fd73c",
    "jrc_manifest": "03e48ad181884b4533861972e078f8a24b762f7a2445fd59ec25fff0c7deb248",
    "lon_treaty": "a8790efad550c33786a75e26466a241a1858fac902678d8d2a7c2ffb02b0903f",
    "ibs120": "12a88517ffa94bd53307ee26a8fcfa9279c9e106fd031d993c38926e3d77e87e",
    "treaty_1926": "120edb084074e033786cb544c4bc8d0046b3b8b001c7afdb80a47e1a972520de",
}

# The League of Nations Treaty Series scan (vol. 129, printed pp. 161-166)
# gives beacon 47 as 17°23′23.7″ S, 18°25′06.2″ E. Methods and the missing
# datum are described in the source record; these values are used only for a
# coarse bounding-box relation, not as a precision transformation.
BEACON_47 = {
    "number": 47,
    "latitude_dms": "17 23 23.7 S",
    "longitude_dms": "18 25 06.2 E",
    "latitude_decimal": -(17 + 23 / 60 + 23.7 / 3600),
    "longitude_decimal": 18 + 25 / 60 + 6.2 / 3600,
    "description": "On limestone ridge 240 metres west of the west bank of the Okavango River",
    "source_pdf_page": 166,
    "source_printed_page": 165,
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_original(path: Path, expected_hash: str, baseline) -> dict:
    rel = str(path.relative_to(REPO))
    raw = baseline.materialized_bytes(rel)
    if hashlib.sha256(raw).hexdigest() != expected_hash:
        raise ValueError(f"original input hash mismatch: {path.name}")
    return json.loads(raw)


def reconstruct(tile: dict, work: Path, baseline) -> Path:
    target = work / f"{tile['layer']}_{tile['tile']}.tif"
    h = hashlib.sha256()
    size = 0
    with target.open("wb") as out:
        for part in tile["parts"]:
            path = SOURCE / part["path"]
            raw = baseline.materialized_bytes(str(path.relative_to(REPO)))
            if len(raw) != part["bytes"] or hashlib.sha256(raw).hexdigest() != part["sha256"]:
                raise ValueError(f"JRC part pin mismatch: {path}")
            out.write(raw)
            h.update(raw)
            size += len(raw)
    if size != tile["original_bytes"] or h.hexdigest() != tile["original_sha256"]:
        raise ValueError(f"JRC reassembly pin mismatch: {tile['layer']} {tile['tile']}")
    return target


def pixel_center_values(dataset, geom) -> list[int]:
    """Read raw source values only for pixel centers inside a geometry.

    Returning raw values preserves source NoData codes. Rasterio masked-array
    ``compressed()`` would remove those values before they could be counted.
    """
    piece = geom.intersection(box(*dataset.bounds))
    if piece.is_empty:
        return []
    window = geometry_window(dataset, [piece.__geo_interface__])
    raw = dataset.read(window=window, masked=False)[0]
    selected = geometry_mask(
        [piece.__geo_interface__],
        out_shape=raw.shape,
        transform=dataset.window_transform(window),
        all_touched=False,
        invert=True,
    )
    return [int(value) for value in raw[selected]]


def run_mask_controls() -> tuple[dict, dict]:
    """Exercise the same center-selection helper used for retained rasters."""
    fixture_values = np.array([[0, 80], [10, NODATA]], dtype=np.uint8)
    profile = {
        "driver": "GTiff", "height": 2, "width": 2, "count": 1,
        "dtype": "uint8", "crs": "EPSG:4326",
        "transform": rasterio.transform.from_origin(0, 2, 1, 1),
        "nodata": NODATA,
    }
    with MemoryFile() as memory:
        with memory.open(**profile) as dataset:
            dataset.write(fixture_values, 1)
            positive_geom = box(0, 0, 2, 2)
            raw_values = pixel_center_values(dataset, positive_geom)
            valid_values = [value for value in raw_values if value != NODATA]
            edge_geom = box(0.01, 1.01, 0.49, 1.49)
            edge_values = pixel_center_values(dataset, edge_geom)
            disjoint_values = pixel_center_values(dataset, box(2.25, 0.25, 2.75, 0.75))

    positive_passed = (
        raw_values == [0, 80, 10, NODATA]
        and valid_values == [0, 80, 10]
        and len(raw_values) == 4
        and len(valid_values) == 3
        and edge_values == []
    )
    negative_passed = disjoint_values == []
    if not positive_passed or not negative_passed:
        raise ValueError("production pixel-center helper failed its raster controls")
    positive = {
        "method_id": "kakeri-boundary-contact-jrc-water",
        "kind": "positive-control",
        "outcome": "passed",
        "fixture": {"crs": "EPSG:4326", "transform": [1, 0, 0, 0, -1, 2],
                    "values_by_row": [[0, 80], [10, NODATA]], "nodata": NODATA,
                    "polygon_bounds": [0, 0, 2, 2]},
        "selected_raw_values": raw_values,
        "selected_center_count": len(raw_values),
        "nodata_center_count": raw_values.count(NODATA),
        "valid_values_after_nodata_exclusion": valid_values,
        "valid_center_count": len(valid_values),
        "expected_raw_values": [0, 80, 10, NODATA],
        "expected_nodata_center_count": 1,
        "edge_only_case": {"bounds": [0.01, 1.01, 0.49, 1.49],
                           "selected_values": edge_values, "expected": []},
    }
    negative = {
        "method_id": "kakeri-boundary-contact-jrc-water",
        "kind": "negative-control",
        "outcome": "passed",
        "fixture": {"crs": "EPSG:4326", "transform": [1, 0, 0, 0, -1, 2],
                    "values_by_row": [[0, 80], [10, NODATA]], "nodata": NODATA,
                    "polygon_bounds": [2.25, 0.25, 2.75, 0.75]},
        "selected_values": disjoint_values,
        "expected": [],
    }
    return positive, negative


def values_in_geometry(datasets: dict, geom) -> dict:
    counts = Counter()
    for tile_name in ("10E_10S", "20E_10S"):
        ds = datasets[tile_name]
        vals = pixel_center_values(ds, geom)
        counts.update(vals)
    center_count = sum(counts.values())
    no_data = counts.pop(NODATA, 0)
    return {
        "pixel_centers": center_count,
        "valid_pixel_centers": center_count - no_data,
        "nodata_pixel_centers": no_data,
        "water_pixels_gt_0": sum(counts.get(v, 0) for v in range(1, 101)),
        "water_pixels_gte_50": sum(counts.get(v, 0) for v in range(50, 101)),
        "water_pixels_gte_90": sum(counts.get(v, 0) for v in range(90, 101)),
        "value_counts_0_to_100": {str(v): counts.get(v, 0) for v in range(101)},
    }


def build_report(baseline) -> dict:
    components_doc = read_original(COMPONENTS, INPUT_HASHES["components"], baseline)
    contacts_doc = read_original(CONTACTS, INPUT_HASHES["contacts"], baseline)
    jrc_analysis_raw = baseline.materialized_bytes(str(JRC_ANALYSIS.relative_to(REPO)))
    if hashlib.sha256(jrc_analysis_raw).hexdigest() != INPUT_HASHES["jrc_analysis"]:
        raise ValueError("retained JRC analysis hash mismatch")
    manifest_raw = baseline.materialized_bytes(str(MANIFEST.relative_to(REPO)))
    if hashlib.sha256(manifest_raw).hexdigest() != INPUT_HASHES["jrc_manifest"]:
        raise ValueError("retained JRC manifest hash mismatch")
    for name, path in (("lon_treaty", LON_TREATY), ("ibs120", IBS120)):
        if path.is_symlink() or sha256(path) != INPUT_HASHES[name]:
            raise ValueError(f"historical boundary document hash mismatch: {path.name}")
    treaty_raw = baseline.materialized_bytes(str(TREATY_1926.relative_to(REPO)))
    if hashlib.sha256(treaty_raw).hexdigest() != INPUT_HASHES["treaty_1926"]:
        raise ValueError("historical boundary document hash mismatch: uk-treaty-series-1926-ts-29.pdf")
    manifest = json.loads(manifest_raw)

    components = components_doc["features"]
    contacts = contacts_doc["features"]
    if len(components) != 21 or len(contacts) != 10:
        raise ValueError("original scope must contain 21 components and 10 contacts")
    for feature in components + contacts:
        g = shape(feature["geometry"])
        if not g.is_valid:
            raise ValueError(f"invalid immutable input geometry: {feature.get('id')}")

    with tempfile.TemporaryDirectory(prefix="na-boundary-water-") as tmp:
        work = Path(tmp)
        datasets = {"occurrence": {}, "seasonality": {}}
        for tile in manifest["tiles"]:
            path = reconstruct(tile, work, baseline)
            ds = rasterio.open(path)
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
                raise ValueError(f"JRC raster metadata mismatch: {tile['layer']} {tile['tile']}")
            datasets[tile["layer"]][tile["tile"]] = ds

        component_geometry = {f["id"]: shape(f["geometry"]) for f in components}
        contact_geometry = {
            "gb:" + f["properties"]["shapeGroup"] + ":ADM2:" + f["properties"]["shapeID"]: shape(f["geometry"])
            for f in contacts
        }
        component_rows = []
        pair_rows = []
        pieces_by_contact = {key: [] for key in contact_geometry}
        beacon_lat = BEACON_47["latitude_decimal"]
        beacon_lon = BEACON_47["longitude_decimal"]

        jrc_existing = json.loads(jrc_analysis_raw)
        prior_rows = {x["component_id"]: x for x in jrc_existing["components"]}
        for f in components:
            geom = component_geometry[f["id"]]
            minx, miny, maxx, maxy = geom.bounds
            prior = prior_rows[f["id"]]
            component_rows.append({
                "component_id": f["id"],
                "fragment_ids": [x["id"] for x in f["properties"].get("fragment_bindings", [])],
                "geometry_wkb_sha256": hashlib.sha256(geom.wkb).hexdigest(),
                "bounds_epsg4326": [minx, miny, maxx, maxy],
                "coarse_position_vs_beacon_47": {
                    "entire_bbox_east_of_beacon_47": minx > beacon_lon,
                    "entire_bbox_south_of_beacon_47": maxy < beacon_lat,
                    "beacon_47_coordinate_method_limit": "The published record mixes astronomical/geodetic determinations and states no datum; bbox comparison is only descriptive and is not a geodetic overlay.",
                },
                "jrc_occurrence": {
                    "valid_pixel_centers": prior["layers"]["occurrence"]["valid_pixel_centers"],
                    "nodata_pixel_centers": prior["layers"]["occurrence"]["nodata_pixel_centers"],
                    "water_occurrence_gt_0": prior["layers"]["occurrence"]["water_occurrence_gt_0"],
                    "water_occurrence_gte_50": prior["layers"]["occurrence"]["water_occurrence_gte_50"],
                    "water_occurrence_gte_90": prior["layers"]["occurrence"]["water_occurrence_gte_90"],
                },
                "jrc_2024_seasonality": {
                    "valid_pixel_centers": prior["layers"]["seasonality"]["valid_pixel_centers"],
                    "nodata_pixel_centers": prior["layers"]["seasonality"]["nodata_pixel_centers"],
                    "water_months_gt_0": prior["layers"]["seasonality"]["water_months_gt_0"],
                },
                "physical_status": "Surface-water classifications occur within the unchanged candidate mask; exact bank, channel, wetland/land identity and historic course remain unresolved.",
                "boundary_authority_status": "The treaty chain describes a watercourse-sector boundary east of the 1928 beacon line, but this candidate's exact relation to the historic/current Okavango median line is unresolved.",
            })

        for component_id, geom in component_geometry.items():
            for contact_id, contact_geom in contact_geometry.items():
                inter = geom.intersection(contact_geom)
                area = inter.area if not inter.is_empty else 0.0
                dimension = ("area" if area > 0 else
                             "line" if not inter.is_empty and inter.length > 0 else
                             "point" if not inter.is_empty else "disjoint")
                if dimension == "area":
                    pieces_by_contact[contact_id].append(inter)
                pair_rows.append({
                    "component_id": component_id,
                    "contact_id": contact_id,
                    "intersection_dimension": dimension,
                    "intersection_area_degrees_squared": area,
                    "candidate_contact_pair_jrc_mask": "included in contact-level dissolved-union mask" if dimension == "area" else "not masked",
                })

        contact_rows = []
        for contact_id, pieces in pieces_by_contact.items():
            union = unary_union(pieces) if pieces else None
            if union is None:
                occurrence = {"pixel_centers": 0, "valid_pixel_centers": 0, "nodata_pixel_centers": 0,
                              "water_pixels_gt_0": 0, "water_pixels_gte_50": 0, "water_pixels_gte_90": 0}
                seasonality = {"pixel_centers": 0, "valid_pixel_centers": 0, "nodata_pixel_centers": 0,
                               "water_months_gt_0": 0}
                overlap_ids = []
            else:
                occurrence = values_in_geometry(datasets["occurrence"], union)
                seasonality_values = Counter()
                center_count = 0
                for tile_name in ("10E_10S", "20E_10S"):
                    ds = datasets["seasonality"][tile_name]
                    piece = union.intersection(box(*ds.bounds))
                    if piece.is_empty:
                        continue
                    vals = pixel_center_values(ds, union)
                    seasonality_values.update(vals)
                    center_count += len(vals)
                no_data = seasonality_values.pop(NODATA, 0)
                seasonality = {
                    "pixel_centers": center_count,
                    "valid_pixel_centers": center_count - no_data,
                    "nodata_pixel_centers": no_data,
                    "water_months_gt_0": sum(seasonality_values.get(v, 0) for v in range(1, 13)),
                    "value_counts_0_to_12": {str(v): seasonality_values.get(v, 0) for v in range(13)},
                }
                overlap_ids = [r["component_id"] for r in pair_rows
                               if r["contact_id"] == contact_id and r["intersection_dimension"] == "area"]
            contact_rows.append({
                "contact_id": contact_id,
                "positive_area_candidate_count": len(overlap_ids),
                "component_ids": overlap_ids,
                "intersection_union_wkb_sha256": hashlib.sha256(union.wkb).hexdigest() if union is not None else None,
                "jrc_occurrence": occurrence,
                "jrc_2024_seasonality": seasonality,
                "aggregation_note": "Each contact masks the dissolved union of its positive-area candidate intersections, so pixels are not double-counted within that contact. Contact rows across countries/source units can overlap and are not additive.",
            })

        for group in datasets.values():
            for ds in group.values():
                ds.close()

    boundary_sources = {
        "primary_final_act": {
            "id": "League of Nations Treaty Series No. 2960, volume 129 (1932), Final Act signed Kakeri 1928-09-23 and Schedule",
            "retained_file": "sources/historical-boundary/lon-treaty-series-vol-129-1932.pdf",
            "sha256": INPUT_HASHES["lon_treaty"],
            "bytes": LON_TREATY.stat().st_size,
            "pdf_pages": [161, 162, 163, 164, 165, 166],
            "printed_pages": [158, 159, 160, 161, 162, 163, 164, 165],
            "findings": [
                "The joint commission declared that the land boundary had been demarcated by chords joining 47 main beacons selected after observations and calculations.",
                "Beacon 47 is described as on a limestone ridge 240 m west of the west bank of the Okavango River; the printed coordinate is 17°23′23.7″ S, 18°25′06.2″ E.",
                "The schedule lists positions and distances for the 47 main beacons; the published note says latitude observations were astronomical except beacons 17 and 47, and longitude methods varied by beacon.",
                "The act states boundary works were completed except clearing between beacon 28 and the Okavango, which was planned for the next rainy season; it also provides for annual joint inspection and maintenance.",
                "The 1931 exchange of notes records both governments' acceptance of the Kakeri demarcation and description as correct and recognizes the boundary indicated by erected beacons.",
            ],
            "scope_limit": "The record supports the historic survey and demarcation framework and terminal point. It does not include a current georeferenced bank/thalweg line across the 21 candidate footprints or establish present physical shoreline/course.",
        },
        "primary_1926_agreement": {
            "id": "UK Treaty Series No. 29 (1926), Cmd. 2777, South Africa-Portugal Agreement signed 1926-06-22",
            "retained_file": "sources/uk-treaty-series-1926-ts-29.pdf",
            "sha256": INPUT_HASHES["treaty_1926"],
            "bytes": TREATY_1926.stat().st_size,
            "pdf_pages": [2, 3, 4],
            "findings": [
                "Article 2 identifies the agreed Kunene Falls and describes the Kunene boundary as the middle line equidistant from both banks to the latitude-parallel point.",
                "Article 3 sends the parallel east to the middle line of the Okavango (Cubango), then refers to the 1886 Lisbon treaty.",
                "Articles 4 and 6 provide for joint demarcation, astronomical correction, beaconing and the middle line where the boundary follows a river.",
            ],
            "scope_limit": "The agreement specifies a legal framework, not modern high-resolution river-bank geometry for the candidate polygons.",
        },
        "official_secondary_study": {
            "id": "U.S. Department of State, International Boundary Study No. 120, Angola–Namibia (South-West Africa) Boundary, 1972-03-24",
            "retained_file": "sources/historical-boundary/ibs120-1972.pdf",
            "sha256": INPUT_HASHES["ibs120"],
            "bytes": IBS120.stat().st_size,
            "findings": [
                "The study summarizes the boundary as the median line of the Kunene to Ruacana Falls, then a straight segment to the Okavango and the median line of the Okavango onward.",
                "It lists the 1928 beacon schedule and describes the 1926, 1928 and 1931 instruments.",
            ],
            "scope_limit": "Official secondary compilation, not an executed boundary instrument or a georeferenced modern river line.",
        },
    }
    aggregate_metrics = {
        "components_entire_bbox_east_and_south_of_beacon_47": sum(
            x["coarse_position_vs_beacon_47"]["entire_bbox_east_of_beacon_47"]
            and x["coarse_position_vs_beacon_47"]["entire_bbox_south_of_beacon_47"]
            for x in component_rows
        ),
        "positive_area_candidate_contact_pairs": sum(
            x["intersection_dimension"] == "area" for x in pair_rows
        ),
        "contacts_with_jrc_occurrence_pixels": sum(
            x["jrc_occurrence"]["water_pixels_gt_0"] > 0 for x in contact_rows
        ),
        "contacts_with_jrc_2024_seasonal_pixels": sum(
            x["jrc_2024_seasonality"]["water_months_gt_0"] > 0 for x in contact_rows
        ),
        "summed_contact_union_valid_occurrence_pixel_centers_non_additive": sum(
            x["jrc_occurrence"]["valid_pixel_centers"] for x in contact_rows
        ),
        "summed_contact_union_occurrence_water_pixels_gt_0_non_additive": sum(
            x["jrc_occurrence"]["water_pixels_gt_0"] for x in contact_rows
        ),
        "summed_contact_union_occurrence_nodata_pixel_centers_non_additive": sum(
            x["jrc_occurrence"]["nodata_pixel_centers"] for x in contact_rows
        ),
        "summed_contact_union_2024_water_month_centers_non_additive": sum(
            x["jrc_2024_seasonality"]["water_months_gt_0"] for x in contact_rows
        ),
    }
    positive_control, negative_control = run_mask_controls()
    report = {
        "version": 1,
        "scope": {"component_count": len(component_rows), "contact_count": len(contact_rows),
                  "pair_count": len(pair_rows), "candidate_contact_positive_area_pairs": sum(
                      x["intersection_dimension"] == "area" for x in pair_rows)},
        "aggregate_metrics": aggregate_metrics,
        "method": {
            "historical_position": "Coordinate-bounds comparison to beacon 47 only; the source coordinate datum is unspecified, so no precise geodetic overlay, distance, snapping, or boundary reconstruction is claimed.",
            "contact_surface_water": "For each original source contact, dissolve the positive-area intersections with the unchanged original candidates, then count JRC pixel centers with Rasterio all_touched=false on each retained original tile. Exclude 255 NoData. No reprojection, resampling, or geometry repair.",
            "jrc_limits": [
                "Occurrence summarizes 1984-03 through 2024-12 and does not date individual detections.",
                "Seasonality covers 2024 only; it is not historic-channel evidence.",
                "The JRC release documents spatially variable residual co-registration error at the Landsat Collection 2 transition, including locations at or above one 30 m pixel.",
                "Classified surface water does not identify the exact bank, median/thalweg, waterbody type, processing cause, territory, or legal boundary.",
                "Per-contact counts are not additive across source units because contact geometries may overlap.",
            ],
        },
        "boundary_sources": boundary_sources,
        "beacon_47": BEACON_47,
        "candidate_assessments": component_rows,
        "candidate_contact_intersections": pair_rows,
        "contact_assessments": contact_rows,
        "validation_controls": {
            "positive": {"path": "validation-kakeri-positive-control.json",
                         "sha256": hashlib.sha256(json.dumps(positive_control, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode() + b"\n").hexdigest()},
            "negative": {"path": "validation-kakeri-negative-control.json",
                         "sha256": hashlib.sha256(json.dumps(negative_control, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode() + b"\n").hexdigest()},
        },
        "disposition": "Historical legal-survey evidence is materially stronger than a catalogue lead: the 1928 joint final act and 1931 exchange are retained, with the 1926 agreement. Candidate footprints lie east/south of beacon 47 by coordinate-bounds comparison and need assessment against the Okavango river-sector description. No candidate-specific current or historical bank/median line is established here; all territorial attribution, exact boundary location, processing cause and waterbody type remain unresolved.",
    }
    return report, positive_control, negative_control


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="recompute and compare without writing")
    group.add_argument("--create", action="store_true", help="publish to a fresh owned vintage")
    parser.add_argument("--vintage", help="fresh run name required with --create")
    args = parser.parse_args()
    if args.create and not args.vintage:
        parser.error("--create requires --vintage")
    if not args.create and args.vintage:
        parser.error("--vintage is only valid with --create")
    sys.path.insert(0, str(REPO))
    from scripts.evidence import immutable

    helper_path = REPO / "scripts" / "evidence" / "immutable.py"
    helper_pin = next(item for item in BASELINE_FILES if item["path"] == "scripts/evidence/immutable.py")
    if sha256(helper_path) != helper_pin["sha256"]:
        raise ValueError("working-tree immutable helper differs from pinned baseline code")
    baseline = immutable.Baseline(REPO, BASELINE_COMMIT, BASELINE_FILES)
    publication = None
    if args.create:
        publication = immutable.NewVintage(
            baseline, PACKET, args.vintage,
            ["historical-boundary-contact-water-assessment.json",
             "validation-kakeri-positive-control.json",
             "validation-kakeri-negative-control.json"],
        )
    report, positive_control, negative_control = build_report(baseline)
    if publication is not None:
        records = publication.publish({
            "historical-boundary-contact-water-assessment.json": report,
            "validation-kakeri-positive-control.json": positive_control,
            "validation-kakeri-negative-control.json": negative_control,
        })
        print(json.dumps({"mode": "exclusive-create", "vintage": args.vintage,
                          "created": records, "result": "PASS"}, indent=2))
        return
    if not OUTPUT.is_file() or OUTPUT.is_symlink():
        raise ValueError("retained assessment output is missing or not an ordinary file")
    retained = json.loads(OUTPUT.read_bytes())
    if immutable.canonical_json(retained) != immutable.canonical_json(report):
        raise ValueError("recomputed assessment differs from retained output")
    for name, expected in (("validation-kakeri-positive-control.json", positive_control),
                           ("validation-kakeri-negative-control.json", negative_control)):
        path = ROOT / name
        if not path.is_file() or path.is_symlink() or immutable.canonical_json(json.loads(path.read_bytes())) != immutable.canonical_json(expected):
            raise ValueError(f"retained production control differs from executed helper: {name}")
    print(json.dumps({"mode": "read-only-check", "baseline_commit": BASELINE_COMMIT,
                      "components": len(report["candidate_assessments"]),
                      "contacts": len(report["contact_assessments"]),
                      "pairs": len(report["candidate_contact_intersections"]),
                      "result": "PASS"}, indent=2))


if __name__ == "__main__":
    main()
