#!/usr/bin/env python3
"""Summarize the retained Sentinel-1 scene observations by candidate/contact."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SAR = ROOT / "sentinel1-2020-seasonal-backscatter.json"
COG_METADATA = ROOT / "sources" / "sentinel-1-aws" / "cog-header-metadata.json"
OUTPUT = ROOT / "sentinel1-2020-backscatter-assessments.json"
COMPONENTS = ROOT / "inputs" / "original-components.geojson"
CONTACTS = ROOT / "inputs" / "source-contact-features.geojson"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    sar = json.loads(SAR.read_text())
    header = json.loads(COG_METADATA.read_text())
    component_ids = [feature["id"] for feature in json.loads(COMPONENTS.read_text())["features"]]
    contact_features = json.loads(CONTACTS.read_text())["features"]
    contacts = [
        (feature["properties"]["shapeID"], feature["properties"]["shapeName"])
        for feature in contact_features
    ]
    observations_by_component = defaultdict(lambda: defaultdict(list))
    contact_samples = defaultdict(lambda: defaultdict(list))
    for observation in sar["component_observations"]:
        observations_by_component[observation["component_id"]][observation["season"]].append(observation)
        for overlap in observation["candidate_contact_intersections"]:
            contact_samples[(observation["component_id"], overlap["contact_shape_id"])][
                observation["season"]
            ].append(
                {
                    "scene_item_id": observation["item_id"],
                    "acquisition_datetime": observation["acquisition_datetime"],
                    "valid_pixel_center_count": overlap["valid_pixel_center_count"],
                    "bands": overlap["bands"],
                }
            )

    footprint_by_component = {
        row["component_id"]: row for row in sar["component_tiepoint_footprint_coverage"]
    }
    candidate_rows = []
    for component_id in component_ids:
        seasonal = {}
        for season in ("wet", "dry"):
            seasonal[season] = [
                {
                    "scene_item_id": row["item_id"],
                    "acquisition_datetime": row["acquisition_datetime"],
                    "platform": row["platform"],
                    "relative_orbit": row["relative_orbit"],
                    "scene_component_fraction_planar_deg2": row[
                        "scene_component_fraction_planar_deg2"
                    ],
                    "selected_pixel_centers": row["selected_pixel_centers"],
                    "bands": row["bands"],
                }
                for row in observations_by_component[component_id][season]
            ]
        candidate_rows.append(
            {
                "component_id": component_id,
                "physical_water_status": "unverified",
                "historic_channel_status": "unresolved",
                "candidate_orbit": footprint_by_component[component_id]["relative_orbit"],
                "tiepoint_footprint_coverage": {
                    season: {
                        "fraction_of_candidate_planar_deg2": footprint_by_component[component_id][
                            f"{season}_planar_footprint_coverage_fraction"
                        ],
                        "fully_covered": footprint_by_component[component_id][
                            f"{season}_fully_covered_by_tiepoint_footprint_union"
                        ],
                    }
                    for season in ("wet", "dry")
                },
                "seasonal_scene_observations": seasonal,
                "interpretation_limit": "Only two 2020 seasonal backscatter distributions are summarized. They do not classify water, identify banks or channel history, or establish boundary authority.",
            }
        )

    contact_rows = []
    for contact_id, contact_name in contacts:
        pair_records = [
            row
            for row in sar["candidate_contact_pairs"]
            if row["contact_shape_id"] == contact_id and row["positive_area_intersection"]
        ]
        seasons = {}
        for season in ("wet", "dry"):
            sampled_pair_ids = []
            no_center_pair_ids = []
            for pair in pair_records:
                key = (pair["component_id"], contact_id)
                rows = contact_samples[key][season]
                valid = sum(row["valid_pixel_center_count"] for row in rows)
                if valid:
                    sampled_pair_ids.append(pair["component_id"])
                else:
                    no_center_pair_ids.append(pair["component_id"])
            seasons[season] = {
                "positive_area_candidate_intersection_count": len(pair_records),
                "intersection_ids_with_sampled_pixel_centers": sampled_pair_ids,
                "intersection_ids_without_sampled_pixel_centers": no_center_pair_ids,
            }
        contact_rows.append(
            {
                "contact_shape_id": contact_id,
                "contact_name": contact_name,
                "physical_water_status": "unverified",
                "candidate_intersection_samples_only": True,
                "seasonal_candidate_intersection_coverage": seasons,
                "interpretation_limit": "These measurements cover only positive-area candidate/contact intersection pieces, not the full administrative contact polygon.",
            }
        )

    conflict_assets = header["metadata_conflict"]["cog_tifftag_imagedescription_values"]
    result = {
        "version": 1,
        "source_analysis_file": str(SAR.relative_to(ROOT)),
        "source_analysis_sha256": sha256(SAR),
        "cog_header_metadata_file": str(COG_METADATA.relative_to(ROOT)),
        "cog_header_metadata_sha256": sha256(COG_METADATA),
        "input_counts": {"candidate_components": len(candidate_rows), "source_contacts": len(contacts)},
        "scope_disposition": {
            "water_classification": "not performed",
            "candidate_bank_or_channel_line": "not derived",
            "historic_channel": "unresolved",
            "processing_cause": "unresolved",
            "boundary_authority": "unresolved",
            "administrative_assignment": "not made",
        },
        "source_quality_conflict": {
            "stac_and_safe_mission": "Sentinel-1B",
            "cog_image_description": conflict_assets,
            "cog_has_embedded_crs_or_geotransform": False,
            "disposition": header["metadata_conflict"]["disposition"],
        },
        "candidates": candidate_rows,
        "contacts": contact_rows,
        "thresholds_db_are_sensitivity_metrics_not_a_water_mask": sar["method"]["thresholds_db"],
    }
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
