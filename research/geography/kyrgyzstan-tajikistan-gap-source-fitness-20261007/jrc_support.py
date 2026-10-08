#!/usr/bin/env python3
"""Validate the bounded JRC metadata/cohort plan without reading raster pixels."""
from __future__ import annotations
import hashlib
import json
import pathlib

OWNED = "research/geography/kyrgyzstan-tajikistan-gap-source-fitness-20261007/"
ROOT = OWNED + "jrc-occurrence-cohorts/"
EXACT = ROOT + "jrc-exact-block-intersections.json"
COHORTS = ROOT + "jrc-bounded-cohorts.json"
CAPTURE = ROOT + "source-capture.json"
METADATA = {
    "60E_40N": ("gsw-ifd-range-2.bin", 81328, "a68549e437f0ecc6516e020b984a966da963b538524a467c8049a3aa2801f314"),
    "70E_40N": ("gsw-ifd-range-4.bin", 81328, "341c573aaf6c810da854839c62367a761d2121c5e50f5c38bd470c7b23e205e1"),
    "60E_50N": ("gsw-ifd-range-5.bin", 81328, "89775e37a7aa661de0780034e97406f1ea23de15f82bdf4469baa7efa2a37fad"),
    "70E_50N": ("gsw-ifd-range-6.bin", 81328, "e1bf29a3a11dbddc61d39d6b8de4d79852bc7dad0e61fab391f90459be32e593"),
}
EXPECTED = {
    "deduplicated_tile_union_blocks": 256,
    "sum_of_per_cohort_unique_block_memberships": 306,
    "repeated_block_memberships_across_cohorts": 50,
    "sum_of_cohort_encoded_bytes": 855570,
    "sum_of_cohort_decoded_upper_bound_bytes": 80216064,
    "candidate_unique_blocks": 17,
    "contact_unique_blocks": 256,
    "candidate_blocks_without_contact_block_overlap": 0,
}

def _sha(raw):
    return hashlib.sha256(raw).hexdigest()

def _read(baseline, path):
    return baseline.pinned_bytes(path)

def load_and_validate(baseline, config, component_ids, contact_ids):
    exact_raw, cohort_raw, capture_raw = (_read(baseline, p) for p in (EXACT, COHORTS, CAPTURE))
    exact, plan, capture = (json.loads(x) for x in (exact_raw, cohort_raw, capture_raw))
    if exact.get("contract_sha256") != "2aa9ab4ea222fc7a00668e1306c9e4be15f15de943607979605d1d91068750b3":
        raise ValueError("JRC support contract differs from the frozen #1431 criterion")
    if (len(exact.get("features", [])) != 24 or
            {x["id"] for x in exact["features"] if x["kind"] == "candidate"} != set(component_ids) or
            {x["id"] for x in exact["features"] if x["kind"] == "contact"} != set(contact_ids)):
        raise ValueError("JRC exact-intersection rows do not cover the complete 15+9 scope")
    if plan.get("block_intersection_manifest_sha256") != _sha(exact_raw):
        raise ValueError("JRC cohort plan is not bound to the exact intersection manifest")
    for path, digest in exact["input_gzip_sha256"].items():
        descriptor = next((x for x in baseline.pins.values() if x["path"].endswith("/" + path)), None)
        if descriptor is None or descriptor["sha256"] != digest:
            raise ValueError(f"JRC source feature input hash is not pinned: {path}")
    feature_by_id = {x["id"]: x for x in exact["features"]}
    expected_status = {"water_status": "unverified", "administrative_assignment": None,
                       "cause_status": "unknown", "physical_authority": "unapproved",
                       "source_fitness": "unapproved-for-all-components"}
    for item in exact["features"]:
        if item["kind"] == "candidate" and item.get("status_snapshot") != expected_status:
            raise ValueError("JRC metadata changed the candidate's unresolved status fields")
    if plan.get("block_work_totals") != EXPECTED:
        raise ValueError("JRC cohort work totals differ from the independently checked plan")
    if len(plan.get("cohorts", [])) != 10:
        raise ValueError("JRC cohort count differs from the bounded plan")
    for cohort in plan["cohorts"]:
        if cohort["unique_block_count"] > 64 or cohort["decoded_full_block_upper_bound_bytes"] > 16777216:
            raise ValueError("JRC cohort exceeds its per-cohort block/decoded-byte cap")
        for member in cohort["members"]:
            source = feature_by_id.get(member["id"])
            if source is None or member["source_ref"] != source["source_ref"]:
                raise ValueError("JRC cohort member is absent from complete exact-support inventory")
            if member["block_indices_row_major"] != source["exact_closed_block_indices_by_tile"].get(cohort["tile"], []):
                raise ValueError("JRC cohort block mapping differs from exact intersections")
    for tile, (name, size, digest) in METADATA.items():
        raw = _read(baseline, ROOT + name)
        if len(raw) != size or _sha(raw) != digest:
            raise ValueError(f"JRC metadata-only range differs: {tile}")
        record = next((x for x in capture["tiles"] if x["tile"] == tile), None)
        if not record or record["retained_bytes"] != size or record["retained_sha256"] != digest:
            raise ValueError(f"JRC metadata capture descriptor differs: {tile}")
        if record.get("contains_image_block_bytes") is not False or record.get("earliest_image_block_offset_all_ifds") != size:
            raise ValueError(f"JRC metadata capture includes raster block bytes: {tile}")
    if sum(x[1] for x in METADATA.values()) != 325312:
        raise ValueError("JRC metadata range budget changed")
    return {
        "status": "metadata-and-cohort-plan-validated",
        "exact_intersections_sha256": _sha(exact_raw),
        "bounded_cohorts_sha256": _sha(cohort_raw),
        "source_capture_sha256": _sha(capture_raw),
        "metadata_ranges_sha256": {tile: item[2] for tile, item in METADATA.items()},
        "scope": {"candidates": 15, "contacts_context_only": 9, "complete_source_features": 24},
        "cohorts": 10,
        "per_cohort_cap": {"blocks": 64, "decoded_bytes": 16777216},
        "block_work_totals": EXPECTED,
        "metadata_range_bytes": 325312,
        "source_role": "long-period occurrence frequency context; not current water truth or boundary authority",
        "raster_pixel_values_read": False,
        "candidate_water_status": "unverified",
        "candidate_cause_status": "unknown",
        "administrative_assignment": None,
        "physical_authority": "unapproved",
    }
