#!/usr/bin/env python3
"""Reproduce the exact-ID comparison between #435 sources and current Atlas shapes.

Area overlap is a diagnostic only: it does not establish legal boundaries,
source completeness, purpose, or the suitability of a territorial tier.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import shape
from shapely import make_valid
from shapely.ops import transform
from source_bytes import source_bytes

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "sources"
FINDINGS = ROOT / "findings"
SCOPE = json.loads((ROOT / "source/issue-scope.json").read_text())
ROSTER = [json.loads(line) for line in (FINDINGS / "subject-roster.jsonl").read_text().splitlines()]
PROJECT = Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True).transform

SOURCE_FILES = {
    "BWA": "gb-BWA-ADM2.geojson",
    "LSO": "gb-LSO-ADM1.geojson",
    "NAM": "gb-NAM-ADM2.geojson",
    "SWZ": "gb-SWZ-ADM2.geojson",
    "ZAF": "gb-ZAF-ADM3.geojson",
}
ECO_FILE = SOURCES / "arcgis-resolve-scoped-ecoregions.geojson"


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def projected(feature: dict):
    return transform(PROJECT, shape(feature["geometry"]))


source_shapes = {}
source_hashes = {}
for country, filename in SOURCE_FILES.items():
    raw_source = source_bytes(filename)
    source_hashes[country] = hashlib.sha256(raw_source).hexdigest()
    document = json.loads(raw_source)
    for feature in document["features"]:
        props = feature["properties"]
        source_shapes[f"{country}:{props['shapeType']}:{props['shapeID']}"] = feature
eco_doc = json.loads(ECO_FILE.read_text())
eco_shapes = {int(feature["properties"]["ECO_ID"]): feature for feature in eco_doc["features"]}

atlas_shapes = {}
for part in sorted((ROOT.parents[1] / "geography").glob("part-*.json")):
    for feature in json.loads(part.read_text())["features"]:
        atlas_shapes[feature["properties"]["id"]] = (feature, part.name)

rows = []
missing_atlas = []
missing_source = []
for row in ROSTER:
    location_id = row["id"]
    if location_id not in atlas_shapes:
        missing_atlas.append(location_id)
        continue
    atlas_feature, part_name = atlas_shapes[location_id]
    source_id = row.get("source_original_id")
    source_ref = row.get("source_id", "")
    source_key = None
    if source_ref.startswith("gb:"):
        source_key = source_ref.removeprefix("gb:") + ":" + str(source_id)
    elif source_ref.startswith("resolve:"):
        # This is the referenced whole admin feature; the Atlas geometry is an
        # ecological clip/subregion and must not be treated as the whole unit.
        for candidate in source_shapes:
            if candidate.endswith(":" + str(source_id)):
                source_key = candidate
                break
    source_feature = source_shapes.get(source_key)
    if source_feature is None:
        missing_source.append({"id": location_id, "source_original_id": source_id})
        continue
    source_props = source_feature["properties"]
    atlas_geom_raw = projected(atlas_feature)
    source_geom_raw = projected(source_feature)
    atlas_valid = atlas_geom_raw.is_valid
    source_valid = source_geom_raw.is_valid
    atlas_geom = make_valid(atlas_geom_raw)
    source_geom = make_valid(source_geom_raw)
    intersection = atlas_geom.intersection(source_geom).area
    atlas_area = atlas_geom.area
    source_area = source_geom.area
    if source_ref.startswith("gb:"):
        comparison = {
            "comparison": "Atlas named location against its pinned source feature",
            "intersection_over_atlas": intersection / atlas_area if atlas_area else None,
            "intersection_over_source": intersection / source_area if source_area else None,
            "area_ratio_atlas_to_source": atlas_area / source_area if source_area else None,
            "intersection_over_union": intersection / (atlas_area + source_area - intersection)
            if atlas_area + source_area > intersection else None,
            "symmetric_difference_km2": (atlas_area + source_area - 2 * intersection) / 1_000_000,
        }
    else:
        comparison = {
            "comparison": "ecological subregion against referenced whole administrative feature",
            "fragment_area_share_of_admin_source": intersection / source_area if source_area else None,
            "fragment_covered_by_admin_source": intersection / atlas_area if atlas_area else None,
            "whole_admin_area_km2": source_area / 1_000_000,
            "fragment_area_km2": atlas_area / 1_000_000,
            "whole_source_geometry_used_as_fragment_evidence": False,
        }
        eco_id = int(source_ref.split(":", 1)[1])
        eco_feature = eco_shapes[eco_id]
        eco_geom_raw = projected(eco_feature)
        eco_valid = eco_geom_raw.is_valid
        eco_geom = make_valid(eco_geom_raw)
        derived_geom = make_valid(source_geom.intersection(eco_geom))
        derived_intersection = atlas_geom.intersection(derived_geom).area
        derived_iou = derived_intersection / (atlas_area + derived_geom.area - derived_intersection)
        comparison["against_reproduced_admin_by_ecoregion_clip"] = {
            "ecoregion_id": eco_id,
            "ecoregion_name": eco_feature["properties"]["ECO_NAME"],
            "ecoregion_geometry_valid_before_repair_for_comparison": eco_valid,
            "reproduced_clip_iou": derived_iou,
            "atlas_covered_by_reproduced_clip": derived_intersection / atlas_area if atlas_area else None,
            "reproduced_clip_covered_by_atlas": derived_intersection / derived_geom.area if derived_geom.area else None,
            "reproduced_clip_area_km2": derived_geom.area / 1_000_000,
            "atlas_to_clip_symmetric_difference_km2": (atlas_area + derived_geom.area - 2 * derived_intersection) / 1_000_000,
        }
    rows.append({
        "id": location_id,
        "name": row["name"],
        "area_id": row["area_id"],
        "parent_id": row["parent_id"],
        "part": part_name,
        "source_id": row.get("source_id"),
        "source_original_id": source_id,
        "source_feature_key": source_key,
        "source_feature_name": source_props.get("shapeName"),
        "source_shape_type": source_props.get("shapeType"),
        "atlas_geometry_type": atlas_feature["geometry"]["type"],
        "atlas_polygon_components": row.get("polygon_component_count"),
        "atlas_geometry_valid_before_repair_for_comparison": atlas_valid,
        "pinned_source_geometry_valid_before_repair_for_comparison": source_valid,
        "area_metrics_use_make_valid_repair": not (atlas_valid and source_valid),
        "atlas_name_equals_source_feature_name": row["name"] == source_props.get("shapeName"),
        "comparison": comparison,
    })

output_path = FINDINGS / "pinned-source-reconciliation.jsonl"
output_path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows))
summary = {
    "version": 1,
    "scope_count": len(ROSTER),
    "reconciled_count": len(rows),
    "direct_admin_source_features": sum(row["source_id"].startswith("gb:") for row in rows),
    "ecological_subregions_with_admin_source_reference": sum(row["source_id"].startswith("resolve:") for row in rows),
    "missing_atlas_ids": missing_atlas,
    "missing_source_links": missing_source,
    "source_bytes_sha256": source_hashes,
    "ecoregion_source_bytes_sha256": file_sha(ECO_FILE),
    "pinned_source_record_counts": {
        country: sum(key.startswith(country + ":") for key in source_shapes)
        for country in SOURCE_FILES
    },
    "geometry_comparison": {
        "projection": "EPSG:6933 equal-area",
        "purpose": "Reproducible geometric similarity diagnostic against pinned source bytes",
        "limitations": [
            "similarity does not prove boundary authority, source completeness, legal currency, or intended territorial meaning",
            "physical subregion geometries are ecological clips and are not expected to equal their referenced whole administrative feature",
            "coordinate quantization and differing source generalization can yield legitimate area differences",
        ],
    },
    "result_sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
}
(FINDINGS / "pinned-source-reconciliation-summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
print(json.dumps(summary, indent=2, sort_keys=True))
