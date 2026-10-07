#!/usr/bin/env python3
"""Reproduce candidate-scale water-label and treaty-coordinate screens.

This script reads only the immutable source/input files under this issue scope.
It does not infer whole-component water status, legal boundary applicability,
geographic ownership, cause, or permission to repair.
"""
import argparse
import hashlib
import json
import math
import platform
from pathlib import Path

import numpy as np
import rasterio
import shapely
import pyproj
from affine import Affine
from pyproj import Transformer
from rasterio.windows import Window
from shapely import contains_xy
from shapely.geometry import LineString, box, mapping, shape
from shapely.ops import transform as transform_geometry


ROOT = Path(__file__).resolve().parents[3]
PACKET = ROOT / "research/geography/gap-source-angola-drc-boundary-water-followup-20261007"
INPUT = PACKET / "inputs"
SOURCES = PACKET / "sources"
OUTPUT = PACKET / "outputs"

WORLD_COVER = {
    "2020-v100": {
        "year": 2020,
        "tiles": {
            "S09E015": SOURCES / "worldcover/v100-2020-S09E015.tif",
            "S09E018": SOURCES / "worldcover/v100-2020-S09E018.tif",
        },
    },
    "2021-v200": {
        "year": 2021,
        "tiles": {
            "S09E015": SOURCES / "worldcover/v200-2021-S09E015.tif",
            "S09E018": SOURCES / "worldcover/v200-2021-S09E018.tif",
        },
    },
}
AMBIGUOUS_SCL_CLASSES = (0, 1, 2, 3, 7, 8, 9, 10, 11)

SCL_SCENES = {
    "MBS": {
        "scene": "S2A_34MBS_20200812_1_L2A",
        "date": "2020-08-12",
        "epsg": "EPSG:32734",
        "path": SOURCES / "sentinel-2/native-scl/S2A_34MBS_20200812_1_L2A-SCL-20m.jp2",
        "components": [1, 2],
    },
    "MYM": {
        "scene": "S2B_33MYM_20260727_0_L2A",
        "date": "2026-07-27",
        "epsg": "EPSG:32733",
        "path": SOURCES / "sentinel-2/native-scl/S2B_33MYM_20260727_0_L2A-SCL-20m.jp2",
        "components": [3, 8],
    },
    "MZM": {
        "scene": "S2A_33MZM_20260525_0_L2A",
        "date": "2026-05-25",
        "epsg": "EPSG:32733",
        "path": SOURCES / "sentinel-2/native-scl/S2A_33MZM_20260525_0_L2A-SCL-20m.jp2",
        "components": [4, 9],
    },
    "MCS": {
        "scene": "S2A_34MCS_20260902_1_L2A",
        "date": "2026-09-02",
        "epsg": "EPSG:32734",
        "path": SOURCES / "sentinel-2/native-scl/S2A_34MCS_20260902_1_L2A-SCL-20m.jp2",
        "components": [5, 6, 7, 10],
    },
}

TREATY_REFERENCES = [
    {"id": "parallel_8S", "latitude": -8.0, "text": "Along the eighth parallel between the named river endpoints.", "kind": "parallel_with_unlocated_endpoints"},
    {"id": "parallel_7_55S", "latitude": -7.916666666666667, "text": "Kwengo to the eighth parallel, then the parallel to Luita; later, Lucaia thalweg to 7°55′S and the parallel to Kwengo.", "kind": "parallel_with_unlocated_endpoints"},
    {"id": "approx_8_7_40S", "latitude": -8.127777777777778, "text": "Approximate latitude at Tungila mouth; point reference, not a boundary parallel.", "kind": "approximate_junction_latitude_only"},
    {"id": "approx_8_5_40S", "latitude": -8.094444444444445, "text": "Approximate latitude near the Komba/Lola reference; point reference, not a boundary parallel.", "kind": "approximate_junction_latitude_only"},
    {"id": "approx_7_34S", "latitude": -7.566666666666666, "text": "Approximate latitude at the Kama Bomba/Kangulungu reference; point reference, not a boundary parallel.", "kind": "approximate_junction_latitude_only"},
    {"id": "parallel_7S", "latitude": -7.0, "text": "Parallel to 7°S, with named river endpoints not georeferenced in the text.", "kind": "parallel_with_unlocated_endpoints"},
    {"id": "parallel_6_55S", "latitude": -6.916666666666667, "text": "Parallel to 6°55′S, with a named river endpoint not georeferenced in the text.", "kind": "parallel_with_unlocated_endpoints"},
    {"id": "parallel_7_17S", "latitude": -7.283333333333333, "text": "Parallel to 7°17′S, with a named river endpoint not georeferenced in the text.", "kind": "parallel_with_unlocated_endpoints"},
]

SCL_CLASS_NAMES = {
    0: "NO_DATA",
    1: "SATURATED_OR_DEFECTIVE",
    2: "DARK_OR_CAST_SHADOW_VERSION_DEPENDENT",
    3: "CLOUD_SHADOWS",
    4: "VEGETATION",
    5: "NON_VEGETATED",
    6: "WATER",
    7: "UNCLASSIFIED",
    8: "MEDIUM_PROBABILITY_CLOUD",
    9: "HIGH_PROBABILITY_CLOUD",
    10: "THIN_CIRRUS",
    11: "SNOW_OR_ICE",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical_json(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def load_and_verify_pins():
    pins_path = INPUT / "source-pins.json"
    pins = json.loads(pins_path.read_text(encoding="utf-8"))
    seen = set()
    for row in pins["files"]:
        rel = row["path"]
        if rel in seen:
            raise ValueError(f"duplicate input pin: {rel}")
        seen.add(rel)
        path = ROOT / rel
        if not path.is_file() and not row.get("required_for_reproduction", True):
            continue
        verify_pinned_bytes(path.read_bytes(), row)
    return pins


def verify_pinned_bytes(data, row):
    if len(data) != row["bytes"] or sha(data) != row["sha256"]:
        raise ValueError(f"source/input byte pin mismatch: {row['path']}")


def validate_roster(components, contacts, roster):
    if len(components) != 10 or len(contacts) != 5:
        raise ValueError("full ten-component/five-contact scope is required")
    if len(roster.get("component_ids", [])) != 10 or len(roster.get("contact_ids", [])) != 5:
        raise ValueError("frozen issue roster is incomplete")
    if {f["id"] for f in components} != set(roster["component_ids"]):
        raise ValueError("component roster mismatch")
    if {f["id"] for f in contacts} != set(roster["contact_ids"]):
        raise ValueError("contact roster mismatch")


def validate_worldcover_grid(dataset, tile_id, transform=None):
    expected_west = 15.0 if tile_id == "S09E015" else 18.0 if tile_id == "S09E018" else None
    if expected_west is None:
        raise ValueError(f"unknown WorldCover tile: {tile_id}")
    actual_transform = transform if transform is not None else dataset.transform
    expected = Affine(1 / 12000, 0, expected_west, 0, -1 / 12000, -6.0)
    if dataset.crs is None or dataset.crs.to_epsg() != 4326:
        raise ValueError(f"WorldCover tile must be EPSG:4326: {tile_id}")
    if (dataset.width, dataset.height) != (36000, 36000) or dataset.nodata != 0:
        raise ValueError(f"WorldCover dimensions/NoData mismatch: {tile_id}")
    if any(abs(left - right) > 1e-12 for left, right in zip(actual_transform, expected)):
        raise ValueError(f"WorldCover pixel registration mismatch: {tile_id}")


def read_geojson(path):
    return json.loads(path.read_text(encoding="utf-8"))


def window_for_geometry(dataset, geom):
    """Return a clipped integer window enclosing every possible interior centre."""
    left, bottom, right, top = geom.bounds
    inv = ~dataset.transform
    corners = [inv * (x, y) for x, y in ((left, bottom), (left, top), (right, bottom), (right, top))]
    col0 = max(0, math.floor(min(col for col, _ in corners)))
    row0 = max(0, math.floor(min(row for _, row in corners)))
    col1 = min(dataset.width, math.ceil(max(col for col, _ in corners)))
    row1 = min(dataset.height, math.ceil(max(row for _, row in corners)))
    if col1 <= col0 or row1 <= row0:
        return None
    return Window(col0, row0, col1 - col0, row1 - row0)


def pixel_counts(dataset, geom):
    """Count pixel centres inside geom, with no all-touched inclusion."""
    win = window_for_geometry(dataset, geom)
    if win is None:
        return {}, 0, 0
    arr = dataset.read(1, window=win)
    rows, cols = np.indices(arr.shape, dtype=np.float64)
    global_cols = cols + int(win.col_off)
    global_rows = rows + int(win.row_off)
    transform = dataset.transform
    xs = transform.a * (global_cols + 0.5) + transform.b * (global_rows + 0.5) + transform.c
    ys = transform.d * (global_cols + 0.5) + transform.e * (global_rows + 0.5) + transform.f
    mask = contains_xy(geom, xs, ys)
    values = arr[mask]
    unique, counts = np.unique(values, return_counts=True)
    return {str(int(v)): int(c) for v, c in zip(unique, counts)}, int(mask.sum()), int(win.width * win.height)


def scl_accounting(class_counts):
    """Derive local SCL label totals without promoting them to feature status."""
    counts = {int(key): int(value) for key, value in class_counts.items()}
    return {
        "pixel_center_count": sum(counts.values()),
        "water_class_6_pixel_centers": counts.get(6, 0),
        "ambiguous_or_unclassified_pixel_centers": sum(counts.get(cls, 0) for cls in AMBIGUOUS_SCL_CLASSES),
    }


def validate_scl_accounting(class_counts, reported):
    expected = scl_accounting(class_counts)
    if any(reported.get(key) != value for key, value in expected.items()):
        raise ValueError("SCL class counts disagree with pixel-centre, water-label, or ambiguous accounting")
    return True


def run(output_path):
    pins = load_and_verify_pins()
    component_doc = read_geojson(INPUT / "component-features.geojson")
    contact_doc = read_geojson(INPUT / "contact-features.geojson")
    roster = json.loads((INPUT / "family-roster.json").read_text(encoding="utf-8"))
    prior_assessment = json.loads((OUTPUT / "physical-water-authority-assessment.json").read_text(encoding="utf-8"))

    components = component_doc["features"]
    contacts = contact_doc["features"]
    validate_roster(components, contacts, roster)
    contact_bindings = json.loads((INPUT / "contact-source-bindings.json").read_text(encoding="utf-8"))
    binding_by_id = {row["id"]: row for row in contact_bindings["features"]}
    if set(binding_by_id) != set(roster["contact_ids"]):
        raise ValueError("contact source-binding roster mismatch")
    prior_by_id = {r["component_id"]: r for r in prior_assessment["components"]}
    if set(prior_by_id) != set(roster["component_ids"]):
        raise ValueError("prior assessment does not cover exact roster")

    worldcover_by_component = {}
    coverage_controls = []
    for vintage, config in WORLD_COVER.items():
        for tile_id, tile_path in config["tiles"].items():
            with rasterio.open(tile_path) as ds:
                validate_worldcover_grid(ds, tile_id)
                tile_geom = box(*rasterio.transform.array_bounds(ds.height, ds.width, ds.transform)[::1])
                # array_bounds is (west, south, east, north), as required by box().
                for index, feature in enumerate(components, 1):
                    geom = shape(feature["geometry"])
                    if not geom.intersects(tile_geom):
                        continue
                    counts, inside_count, window_pixels = pixel_counts(ds, geom)
                    item = worldcover_by_component.setdefault(feature["id"], {}).setdefault(vintage, {
                        "class_counts": {}, "pixel_center_count": 0, "tile_pixel_center_counts": {},
                        "source_tiles": [],
                    })
                    for cls, count in counts.items():
                        item["class_counts"][cls] = item["class_counts"].get(cls, 0) + count
                    item["pixel_center_count"] += inside_count
                    item["tile_pixel_center_counts"][tile_id] = inside_count
                    item["source_tiles"].append(tile_id)
                    coverage_controls.append({"component_number": index, "vintage": vintage, "tile": tile_id,
                                              "pixel_centers": inside_count, "window_cells": window_pixels})

    scl_by_component = {}
    component_to_scene = {}
    selection_by_component = {}
    for tile, config in SCL_SCENES.items():
        transformer = Transformer.from_crs("EPSG:4326", config["epsg"], always_xy=True)
        with rasterio.open(config["path"]) as ds:
            if ds.crs is None or ds.crs.to_string() != config["epsg"]:
                raise ValueError(f"SCL CRS mismatch for {config['scene']}: {ds.crs}")
            tile_bounds = rasterio.transform.array_bounds(ds.height, ds.width, ds.transform)
            tile_geom = box(*tile_bounds)
            for number in config["components"]:
                feature = components[number - 1]
                geom = shape(feature["geometry"])
                projected = transform_geometry(transformer.transform, geom)
                if not tile_geom.covers(projected):
                    raise ValueError(f"SCL raster does not fully cover component {number}")
                counts, inside_count, _ = pixel_counts(ds, projected)
                if inside_count <= 0:
                    raise ValueError(f"no SCL pixel centres inside component {number}")
                scl_by_component[feature["id"]] = {
                    "scene_id": config["scene"], "date": config["date"], "native_crs": config["epsg"],
                    "source_asset_path": str(config["path"].relative_to(ROOT)),
                    "native_resolution_m": 20, "class_counts": counts, "pixel_center_count": inside_count,
                }
                component_to_scene[feature["id"]] = config["scene"]
                search_path = SOURCES / "earth-search" / f"component-{number:02d}-search.json"
                search = json.loads(search_path.read_text(encoding="utf-8"))
                returned = search.get("features", [])
                covering = []
                for rank, candidate in enumerate(returned, 1):
                    candidate_geom = shape(candidate["geometry"])
                    if candidate_geom.covers(geom):
                        covering.append((rank, candidate))
                if not covering:
                    raise ValueError(f"no saved first-page STAC item fully covers component {number}")
                selected_rank, selected = covering[0]
                if selected["id"] != config["scene"]:
                    raise ValueError(f"selected scene is not first covering item in saved search for component {number}")
                cloud_values = [row["properties"].get("eo:cloud_cover") for row in returned]
                if any(not isinstance(value, (int, float)) for value in cloud_values):
                    raise ValueError(f"saved search has a missing cloud value for component {number}")
                if cloud_values != sorted(cloud_values):
                    raise ValueError(f"saved search is not in ascending cloud-cover order for component {number}")
                selection_by_component[feature["id"]] = {
                    "search_snapshot": str(search_path.relative_to(ROOT)),
                    "search_snapshot_sha256": sha(search_path.read_bytes()),
                    "number_matched": search.get("numberMatched"),
                    "number_returned": search.get("numberReturned", len(returned)),
                    "selected_rank_among_returned_items": selected_rank,
                    "selected_item_id": selected["id"],
                    "selected_cloud_cover_percent": selected["properties"]["eo:cloud_cover"],
                    "captured_page_rule": "First captured result, in recorded ascending cloud-cover order, whose STAC polygon geometry covers the exact component geometry.",
                    "search_completeness_limit": "Selection is only among the saved first-page results; number_matched exceeds number_returned for this query, so no claim is made that this is globally lowest-cloud among all matching items.",
                }

    prior_number = {row["component_id"]: i for i, row in enumerate(prior_assessment["components"], 1)}
    treaty_screens = []
    component_rows = []
    for number, feature in enumerate(components, 1):
        geom = shape(feature["geometry"])
        world_rows = {}
        for vintage, config in WORLD_COVER.items():
            values = worldcover_by_component.get(feature["id"], {}).get(vintage, {
                "class_counts": {}, "pixel_center_count": 0, "tile_pixel_center_counts": {}, "source_tiles": []
            })
            class_counts = {int(k): v for k, v in values["class_counts"].items()}
            for cls in range(0, 101, 10):
                class_counts.setdefault(cls, 0)
            world_rows[vintage] = {
                "year": config["year"], "class_counts": {str(k): class_counts[k] for k in sorted(class_counts)},
                "pixel_center_count": values["pixel_center_count"],
                "permanent_water_class_80_pixel_centers": class_counts.get(80, 0),
                "herbaceous_wetland_class_90_pixel_centers": class_counts.get(90, 0),
                "source_tiles": sorted(values["source_tiles"]),
                "tile_pixel_center_counts": values["tile_pixel_center_counts"],
                "interpretation": "Product class labels at pixel centres; zero class-80 pixels is not proof of absence; class-90 wetland is reported separately.",
            }
        scl = scl_by_component[feature["id"]]
        scl_counts = {int(k): v for k, v in scl["class_counts"].items()}
        for cls in SCL_CLASS_NAMES:
            scl_counts.setdefault(cls, 0)
        scl["class_counts"] = {str(k): scl_counts[k] for k in sorted(scl_counts)}
        scl.update(scl_accounting(scl_counts))
        scl["class_labels"] = {str(k): SCL_CLASS_NAMES[k] for k in sorted(SCL_CLASS_NAMES)}
        scl["interpretation"] = "SCL product water label only; 20 m scene class is not ground truth or a full-feature wet/dry decision. Class 2 remains unknown across the mixed processing baselines."

        old = prior_by_id[feature["id"]]
        previous = old["jrc_water_findings"]
        component_rows.append({
            "component_number_in_frozen_feature_order": number,
            "component_id": feature["id"],
            "component_geometry_sha256": sha(canonical_json(feature["geometry"])),
            "prior_2018_2019_jrc_gsw": {
                "all_pixel_centres_nodata_both_years": previous["all_pixel_centres_nodata_both_years"],
                "classified_pixel_centres_by_year": previous["classified_pixel_centres_by_year"],
                "seasonal_water_pixel_centres_by_year": previous["seasonal_water_pixel_centres_by_year"],
                "any_permanent_water_pixel": previous["any_permanent_water_pixel"],
                "any_seasonal_water_pixel": previous["any_seasonal_water_pixel"],
                "vintage_note": "Retained prior assessment output; annual Landsat-derived classifications, with NoData unknown.",
            },
            "worldcover": world_rows,
            "sentinel2_scl": scl,
            "sentinel2_selection": selection_by_component[feature["id"]],
            "literal_treaty_coordinate_screens": [],
            "whole_component_water_status": "unknown",
            "causal_classification": "unknown",
        })

        for reference in TREATY_REFERENCES:
            horizontal = LineString([(-180.0, reference["latitude"]), (180.0, reference["latitude"])])
            ix = geom.intersection(horizontal)
            if not ix.is_empty:
                screen = {
                    "reference_id": reference["id"], "latitude": reference["latitude"],
                    "reference_kind": reference["kind"], "gazette_text_summary": reference["text"],
                    "intersection_type": ix.geom_type, "intersection_geometry": mapping(ix),
                    "intersection_length_degrees": ix.length,
                    "interpretation_limit": "Literal horizontal-coordinate screen only; named river endpoints and reach applicability are not georeferenced, so this does not establish that the treaty-defined boundary segment overlaps the component.",
                }
                treaty_screens.append({"component_number": number, "component_id": feature["id"], **screen})
                component_rows[-1]["literal_treaty_coordinate_screens"].append(screen)

    output = {
        "version": "angola-drc-boundary-water-assessment-v1",
        "scope": {"component_count": len(components), "contact_count": len(contacts),
                  "component_ids_sha256": sha(canonical_json(sorted(f["id"] for f in components))),
                  "contact_ids_sha256": sha(canonical_json(sorted(f["id"] for f in contacts))),
                  "contact_ids": sorted(f["id"] for f in contacts)},
        "contacts": [
            {
                "contact_id": feature["id"],
                "contact_geometry_sha256": sha(canonical_json(feature["geometry"])),
                "contact_feature_sha256": sha(canonical_json(feature)),
                "source_binding": {
                    "source_id": binding_by_id[feature["id"]]["source_metadata"]["source_id"],
                    "source_url": binding_by_id[feature["id"]]["source_metadata"]["source_url"],
                    "source_reference_year": binding_by_id[feature["id"]]["source_metadata"]["reference_year"],
                    "original_source_feature_id": binding_by_id[feature["id"]]["source_metadata"]["original_id"],
                    "source_binding_feature_sha256": binding_by_id[feature["id"]]["feature_sha256"],
                    "source_original_geometry_sha256": binding_by_id[feature["id"]]["source_metadata"].get("original_geometry_sha256"),
                    "source_license_text": binding_by_id[feature["id"]]["source_metadata"]["license"],
                    "binding_file": str((INPUT / "contact-source-bindings.json").relative_to(ROOT)),
                },
                "role": "retained complete neighboring administrative polygon as context for the original five-contact scope; no new contact-level water or treaty-segment classification is made",
                "water_status": "unknown",
                "boundary_authority_status": "unknown",
            }
            for feature in sorted(contacts, key=lambda row: row["id"])
        ],
        "inputs": {"source_pins_sha256": sha((INPUT / "source-pins.json").read_bytes()),
                   "baseline_commit": "cf6b5c585dbad62f617e0cf3843c9e4195b0db6c"},
        "software": {"python": platform.python_version(), "rasterio": rasterio.__version__,
                     "gdal": rasterio.__gdal_version__, "numpy": np.__version__,
                     "shapely": shapely.__version__, "proj": pyproj.proj_version_str},
        "methods": {
            "worldcover": {"pixel_inclusion": "strict pixel-centre membership via Shapely contains_xy on native grid centres; conservative floor/ceil enclosing window",
                            "crs": "EPSG:4326", "resolution_m_nominal": 10,
                            "class_80": "permanent water bodies", "class_90": "herbaceous wetland",
                            "no_data": 0, "vintage_rule": "2020 v100 and 2021 v200 remain separate; the algorithms differ, so no change inference."},
            "sentinel2_scl": {"pixel_inclusion": "strict native 20 m pixel-centre membership via Shapely contains_xy after exact polygon transform to scene UTM CRS; conservative floor/ceil enclosing window",
                               "water_label": 6, "unknown_classes": [0, 1, 2, 3, 7, 8, 9, 10, 11],
                               "scene_selection": "Reproduced from each saved STAC search snapshot: first item in the recorded ascending cloud-cover order whose STAC polygon covers the full component. Search results are limited to the saved first page (up to 50 items), not all numberMatched items; no global lowest-cloud claim is made. The selected native SCL grid is then checked for full component coverage.",
                               "date_rule": "Four scene dates differ; no temporal change is inferred."},
            "treaty_coordinate_screen": {"crs": "EPSG:4326", "predicate": "exact source-coordinate polygon/latitude-line intersection", "buffer_or_snap": False,
                                         "legal_limit": "Finite treaty segments depend on named river reaches/endpoints not supplied with georeferenced geometry in the printed text."},
            "worldcover_vintages": list(WORLD_COVER),
            "worldcover_tiles": [
                {"tile": tile_id, "path": str(tile_path.relative_to(ROOT))}
                for config in WORLD_COVER.values() for tile_id, tile_path in config["tiles"].items()
            ],
        },
        "controls": {
            "positive": {"ten_frozen_components_and_five_contacts_present": True,
                         "all_ten_have_worldcover_pixel_centres_in_each_vintage": all(all(row["worldcover"][v]["pixel_center_count"] > 0 for v in WORLD_COVER) for row in component_rows),
                         "all_ten_have_fully_covered_scl_scene_grid": len(scl_by_component) == 10},
            "negative": {"whole_component_water_status_not_upgraded": all(row["whole_component_water_status"] == "unknown" for row in component_rows),
                         "causal_classification_not_upgraded": all(row["causal_classification"] == "unknown" for row in component_rows),
                         "coordinate_screens_do_not_claim_legal_applicability": all("does not establish" in row["interpretation_limit"] for row in treaty_screens),
                         "worldcover_vintages_not_collapsed": len(WORLD_COVER) == 2 and set(WORLD_COVER) == {"2020-v100", "2021-v200"}},
            "coverage_rows": coverage_controls,
            "contact_context_rows": len(contacts),
            "sentinel_selection_rows": len(selection_by_component),
            "sentinel_selection_is_reproduced_from_saved_first_page": True,
        },
        "components": component_rows,
        "treaty_coordinate_screens": treaty_screens,
        "disposition": "All ten components remain unresolved for whole-footprint water status, treaty-segment applicability, modern boundary authority, and causal class. Pixel labels and literal coordinate overlaps are candidate-scale evidence only.",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(canonical_json(output))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT / "assessment-v1.json")
    args = parser.parse_args()
    run(args.output)
