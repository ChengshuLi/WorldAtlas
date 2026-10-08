#!/usr/bin/env python3
"""Reproduce the bounded #633 crosswalk and official Mauritius district screen."""
from __future__ import annotations

import hashlib
import argparse
import json
import re
import subprocess
import unicodedata
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform


PACKET = Path(__file__).resolve().parent
ROOT = next(parent for parent in PACKET.parents if (parent / "AGENTS.md").is_file())
PARENT = ROOT / "data/regional-review/regional-review-4f180b98473f1071"
BASELINE = None
CANDIDATE_BYTES = {}
SCOPE = None
EXPECTED_SUBJECTS = set()

MUS_DISTRICT_NAMES = {
    "black river", "flacq", "grand port", "moka", "pamplemousses",
    "plaines wilhems", "port louis", "riviere du rempart", "savanne",
}


def input_bytes(path: Path) -> bytes:
    relative = path.resolve(strict=True).relative_to(ROOT.resolve()).as_posix()
    if relative in CANDIDATE_BYTES:
        return CANDIDATE_BYTES[relative]
    require(BASELINE is not None, "immutable baseline reader was not initialized")
    return BASELINE.materialized_bytes(relative)


def sha256(path: Path) -> str:
    return hashlib.sha256(input_bytes(path)).hexdigest()


def read_json(path: Path):
    return json.loads(input_bytes(path).decode("utf-8"))


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    return " ".join("".join(c for c in value if not unicodedata.combining(c)).replace(".", "").split())


def overlay_metrics(a, b):
    union_area = a.union(b).area
    require(union_area > 0, "overlay control requires a positive-area union")
    return {
        "symmetric_difference_percent_of_union": 100 * a.symmetric_difference(b).area / union_area,
        "relative_area_change_percent": 100 * (b.area / a.area - 1),
    }


def parent_inventory_for_scope(path: Path, expected_subjects: set[str]):
    raw = input_bytes(path)
    rows = {}
    for line in raw.decode("utf-8").splitlines():
        row = json.loads(line)
        if row["id"] in expected_subjects:
            require(row["id"] not in rows, f"duplicate parent inventory ID: {row['id']}")
            rows[row["id"]] = row
    require(set(rows) == expected_subjects,
            "parent #482 evidence must include every exact #633 subject and no additional scope row")
    return rows


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    global BASELINE, CANDIDATE_BYTES, SCOPE, EXPECTED_SUBJECTS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vintage", required=True,
                        help="fresh lower-case run name under this packet's vintages/ directory")
    parser.add_argument("--compare-vintage",
                        help="prior complete run name for an exact reproducibility comparison")
    parser.add_argument("--simulate-post-computation-failure", action="store_true",
                        help=argparse.SUPPRESS)
    args = parser.parse_args()

    manifest_path = PACKET / "evidence-quality.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(manifest.get("issue") == 633 and manifest.get("lane") == "geography",
            "evidence manifest must bind this #633 geography packet")
    require(manifest.get("worker_id") == "01a10947-b3d7-7812-8b2f-c5a47e88ccb2",
            "evidence manifest must bind the serialized worker")
    baseline_spec = manifest["baseline"]
    helper_path = "scripts/evidence/immutable.py"
    helper_pin = next((row for row in baseline_spec["files"] if row["path"] == helper_path), None)
    require(helper_pin is not None, "shared immutable evidence helper must be pinned")
    # Load the writer from the immutable baseline bytes, never from an unchecked
    # working-tree import.  The manifest pins the complete helper file.
    namespace = {"__builtins__": __builtins__, "__name__": "evidence.immutable"}
    helper_raw = __import__("subprocess").check_output(
        ["git", "-C", str(ROOT), "show", f"{baseline_spec['commit']}:{helper_path}"])
    require(hashlib.sha256(helper_raw).hexdigest() == helper_pin["sha256"],
            "pinned immutable helper hash differs from the evidence manifest")
    exec(compile(helper_raw, helper_path, "exec"), namespace)
    BaselineClass = namespace["Baseline"]
    BASELINE = BaselineClass(ROOT, baseline_spec["commit"], baseline_spec["files"])

    def admit_candidate(file):
        relative = file["path"]
        require(relative.startswith("data/regional-review/wio-offshore-island-sources-20261003/"),
                "candidate inputs must stay inside the issue-owned packet")
        target = ROOT / relative
        for ancestor in [target, *target.parents]:
            if ancestor == ROOT.parent:
                break
            require(not ancestor.is_symlink(), f"symlink in candidate input path: {relative}")
        raw = target.read_bytes()
        require(len(raw) == file["bytes"] and hashlib.sha256(raw).hexdigest() == file["sha256"],
                f"candidate input differs from its evidence descriptor: {relative}")
        BASELINE.admit(relative, len(raw))
        CANDIDATE_BYTES[relative] = raw

    scope_descriptor = next(row for row in manifest["outputs"] if row["path"].endswith("/scope.json"))
    inventory_descriptor = next(row for row in manifest["outputs"] if row["path"].endswith("/source-inventory.json"))
    for descriptor in [scope_descriptor, inventory_descriptor]:
        admit_candidate(descriptor)
    for source in manifest["sources"]:
        for descriptor in source.get("files", []):
            admit_candidate(descriptor)

    # The owned candidate inventory supplies fixed source metadata, including
    # official service envelopes; retain its exact bytes/hash as an input.
    scope_relative = scope_descriptor["path"]
    inventory_relative = inventory_descriptor["path"]
    SCOPE = read_json(ROOT / scope_relative)
    owned_inventory = read_json(ROOT / inventory_relative)
    EXPECTED_SUBJECTS = set(SCOPE["subjects"])
    require(SCOPE["issue"] == 633 and len(EXPECTED_SUBJECTS) == 24,
            "scope must contain exactly the 24 declared #633 subjects")
    require(SCOPE["baseline_commit"] == BASELINE.commit,
            "scope evaluation commit differs from the immutable baseline")

    output_names = ["subject-findings.json", "district-comparison.json", "results.json"]
    control_names = [
        "control-generator-positive.json", "control-generator-negative.json",
        "control-generator-reproducibility.json", "control-overlay-positive.json",
        "control-overlay-negative.json", "control-shom-positive.json",
        "control-shom-negative.json",
    ]
    if args.compare_vintage:
        require(args.compare_vintage != args.vintage and re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", args.compare_vintage),
                "comparison must name a distinct valid prior run")
        for name in [*output_names, "publication.json"]:
            descriptor = next((row for row in manifest["outputs"] if row["path"].endswith(
                f"/vintages/{args.compare_vintage}/{name}")), None)
            require(descriptor is not None, f"comparison vintage is not inventoried: {args.compare_vintage}/{name}")
            admit_candidate(descriptor)
        prior_receipt_descriptor = next(row for row in manifest["outputs"] if row["path"].endswith(
            f"/vintages/{args.compare_vintage}/publication.json"))
        prior_receipt = json.loads(CANDIDATE_BYTES[prior_receipt_descriptor["path"]])
        require(prior_receipt.get("version") == 1 and prior_receipt.get("status") == "complete" and
                len(prior_receipt.get("outputs", [])) == len(output_names) and
                {Path(row["path"]).name: row["sha256"] for row in prior_receipt["outputs"]} == {
                    name: next(row["sha256"] for row in manifest["outputs"] if row["path"].endswith(
                        f"/vintages/{args.compare_vintage}/{name}")) for name in output_names},
                "prior vintage receipt does not bind the exact complete product set")
        output_names += control_names
    writer = namespace["NewVintage"](BASELINE, SCOPE["owned_path"], args.vintage, output_names)

    inventory_path = PARENT / "subject-inventory.jsonl"
    source_registry_path = PARENT / "sources.json"
    prior_geometry_path = PARENT / "geometry-comparison.json"
    syc_crosswalk_path = PARENT / "seychelles-2019-region-district-crosswalk.json"
    settlement_path = PARENT / "settlement-administration-review.json"
    settlement_review = read_json(settlement_path)
    require(settlement_review["scope_issue"] == 482 and settlement_review["scope_location_count"] == 144,
            "settlement/source-gap evidence must remain the exact predecessor #482 scope")
    require("not a geocoded" in settlement_review["settlement_disposition"]["Seychelles"].lower(),
            "prior Seychelles source outcome must distinguish district data from geocoded settlements")
    require("not an exhaustive geocoded settlement inventory" in
            settlement_review["settlement_disposition"]["Mauritius"],
            "prior Mauritius source outcome must distinguish census/locality counts from coordinates")

    # Parse exactly the authenticated byte snapshot materialized_bytes checked.
    # Do not consume roster values from the mutable checkout before authentication.
    parent_inventory = parent_inventory_for_scope(inventory_path, EXPECTED_SUBJECTS)

    current = {}
    containing_paths = {
        "data/geography/part-16.json",
        "data/geography/part-23.json",
        "data/geography/part-28.json",
    }
    for relative in sorted(containing_paths):
        document = read_json(ROOT / relative)
        for feature in document["features"]:
            identity = feature.get("id") or feature.get("properties", {}).get("id")
            if identity in EXPECTED_SUBJECTS:
                require(identity not in current, f"duplicate current geometry ID: {identity}")
                current[identity] = feature
    require(set(current) == EXPECTED_SUBJECTS,
            "current geography containing files must resolve all 24 exact subjects once")

    # Compare current record envelopes with the official WMS metadata envelopes.
    # This is a coarse extent screen, not proof of raster or tile availability.
    shom_subjects = {
        "atlas:coverage:ATF-5919": "Shom:LitTo3D-Eparses-2012",
        "atlas:coverage:FRA-4602": "Shom:LitTo3D-Mayotte-2012",
        "atlas:coverage:FRA-4601": "Shom:LitTo3D-Reunion-2016",
    }
    source_by_id = {row["id"]: row for row in owned_inventory["sources"]}
    shom_extent_screen = []
    for subject_id, source_id in shom_subjects.items():
        source = source_by_id[source_id]
        advertised = source["wms_reported_geographic_bbox_wgs84"]
        west, south, east, north = shape(current[subject_id]["geometry"]).bounds
        inside = (west >= advertised["west"] and east <= advertised["east"] and
                  south >= advertised["south"] and north <= advertised["north"])
        outside_edges = {}
        if west < advertised["west"]: outside_edges["west_degrees"] = advertised["west"] - west
        if east > advertised["east"]: outside_edges["east_degrees"] = east - advertised["east"]
        if south < advertised["south"]: outside_edges["south_degrees"] = advertised["south"] - south
        if north > advertised["north"]: outside_edges["north_degrees"] = north - advertised["north"]
        shom_extent_screen.append({
            "subject_id": subject_id,
            "source_id": source_id,
            "current_record_bbox_wgs84": {"west": west, "south": south, "east": east, "north": north},
            "advertised_wms_bbox_wgs84": advertised,
            "record_bbox_inside_wms_envelope": inside,
            "record_bbox_outside_edges_degrees": outside_edges,
            "interpretation_limit": "Metadata envelope comparison only; does not prove raster/tile acquisition or physical completeness.",
        })
    require({row["subject_id"] for row in shom_extent_screen} == set(shom_subjects),
            "Shom envelope screen must cover every listed Litto3D target")

    geometry_comparison = read_json(prior_geometry_path)
    gb_rows = geometry_comparison["geoBoundaries_location_comparisons"]["per_location"]
    ne_rows = geometry_comparison["natural_earth_location_comparisons"]
    prior_metrics = {row["id"]: row for row in gb_rows + ne_rows}
    require(EXPECTED_SUBJECTS <= set(prior_metrics),
            "retained #482 comparison results must include all 24 assigned subjects")

    source_registry = read_json(source_registry_path)
    source_sets = {row["source_id"]: row for row in source_registry["source_sets"]}
    require(source_sets["gb:MUS:ADM1"]["feature_count"] == 12,
            "pinned Mauritius source registry count changed")
    require(source_sets["gb:SYC:ADM2"]["feature_count"] == 8,
            "pinned Seychelles source registry count changed")

    mus_source_file = PARENT / "sources/geoBoundaries-MUS-ADM1-2017.geojson"
    syc_source_file = PARENT / "sources/geoBoundaries-SYC-ADM2-2020.geojson"
    ne_source_file = PARENT / "sources/natural-earth-10m-admin1-selected.geojson"
    pins = {
        "mauritius_geoboundaries": (mus_source_file, "fd3c09513dba7df021ed0f7bd2b05d187932155c99027b4dcc1c90ef8ee554c3"),
        "seychelles_geoboundaries": (syc_source_file, "fc53d69a99b7cadd481c2fa6bcabe36f7138172464ceadf83af382881e3f817a"),
        "natural_earth_extract": (ne_source_file, "eb0fac5a0668edd68e5fdf3700de3941ee98551bcf0c00b1eb33e334be7ac496"),
    }
    for name, (path, expected_hash) in pins.items():
        require(sha256(path) == expected_hash, f"retained #482 source pin changed: {name}")

    # The parent packet's all-location geometry screen provides independent
    # context for all 24 rows. This new run does not claim that parent output was
    # freshly recomputed; it reads and pins its exact retained input bytes.
    mus_admin = read_json(mus_source_file)["features"]
    syc_admin = read_json(syc_source_file)["features"]
    source_component_counts = {
        "gb:MUS:ADM1": len(mus_admin),
        "gb:SYC:ADM2": len(syc_admin),
    }
    require(source_component_counts == {"gb:MUS:ADM1": 12, "gb:SYC:ADM2": 8},
            "original boundary source row counts do not match pinned metadata")

    crosswalk = read_json(syc_crosswalk_path)
    syc_rows = {row["location_id"]: row for row in crosswalk["records"]}
    require(set(syc_rows) == {identity for identity in EXPECTED_SUBJECTS if identity.startswith("gb:SYC:ADM2:")},
            "2019 Seychelles crosswalk does not cover exactly the eight assigned regions")
    require(crosswalk["regions_assigned"] == 8 and crosswalk["ADM3_district_rows_in_full_reference"] == 27,
            "2019 Seychelles administrative crosswalk counts changed")

    issue_rows = []
    for identity in sorted(EXPECTED_SUBJECTS):
        row = parent_inventory[identity]
        metric = prior_metrics[identity]
        item = {
            "id": identity,
            "name": row["name"],
            "current_containing_file": row["containing_file"],
            "current_geometry_type": row["current_geometry_type"],
            "current_component_count": row["current_component_count"],
            "administrative_or_physical_role": row["source_role"],
            "source_id": row["source_id"],
            "source_vintage": row["source_reference_year"],
            "source_license": row["source_license"],
            "source_geometry_component_count": metric.get("source_components"),
            "retained_parent_source_vs_current_symmetric_difference_percent": metric.get("symmetric_difference_of_union_percent"),
            "retained_parent_source_vs_current_relative_area_change_percent": metric.get("relative_area_change_percent"),
            "current_parent_chain": row["parent_chain"],
            "retained_parent_assessment": row["assessment"],
            "settlement_locality_disposition": row["settlement_disposition"],
            "uncertainties": row["uncertainties"],
        }
        if identity.startswith("gb:MUS:ADM1:"):
            item["mauritius_geographical_crosswalk"] = (
                "One of nine Mauritius Island geographical districts" if row["name"] in {
                    "Black River", "Flacq", "Grand Port", "Moka", "Pamplemousses",
                    "Plaines Wilhems", "Port Louis", "Rivière du Rempart", "Savanne"
                } else "Outer-island/Rodrigues record; not one of the nine Mauritius Island districts"
            )
            if norm(row["name"]) in MUS_DISTRICT_NAMES:
                item["official_onsdi_district_crosswalk"] = "normalized exact name; see district-comparison.json"
        elif identity.startswith("gb:SYC:ADM2:"):
            syc = syc_rows[identity]
            item["2019_nbs_adm3_reference"] = {
                "reference_region": syc["NBS_reference_region"],
                "reference_island_parent": syc["NBS_admin1_island"],
                "district_row_count": syc["2019_district_rows_assigned_to_region"],
                "current_parent_label_matches_2019_reference": syc["parent_name_matches_reference"],
                "current_parent_label": syc["current_parent_name"],
            }
        if identity == "gb:SYC:ADM2:34574756B54247629098598":
            item["outer_islands_granularity_finding"] = {
                "retained_2019_source_components": 1057,
                "current_components": 7,
                "meaning": "Counts cannot be reconciled from GSHHG or the unlicensed MSP Atlas candidate without a named island-to-source-feature crosswalk."
            }
        if identity == "gb:MUS:ADM1:65221844B12885462064369":
            item["st_brandon_finding"] = "Official descriptions report a shifting reef with numerous low islets; the retained GSHHG non-intersection is not absence evidence. The exact geoBoundaries footprint-to-island/reef crosswalk is unresolved."
        if identity == "gb:MUS:ADM1:65221844B83452679821580":
            item["agalega_finding"] = "This ODbL/OSM ADM1 record is distinct from the disjoint single-component Natural Earth MUS-5180 named dependency record; the source-unit crosswalk between their coverage remains unresolved."
        if identity == "atlas:coverage:MUS-5180":
            item["agalega_finding"] = "This Public Domain Natural Earth named dependency record remains distinct from the two-component ODbL/OSM geoBoundaries ADM1 record; it is not a substitute for reef/island completeness."
        if identity.startswith("atlas:coverage:") and identity != "atlas:coverage:MUS-5180":
            item["physical_source_finding"] = "Natural Earth 1:10m named territory/dependency geometry reproduces the current feature closely but does not establish a current emergent-land or reef inventory. Shom/IGN Litto3D is a lawful scale-appropriate candidate; exact island/tile crosswalk is still required."
            match = next((row for row in shom_extent_screen if row["subject_id"] == identity), None)
            if match:
                item["shom_wms_extent_screen"] = match
        issue_rows.append(item)

    district_path = PACKET / "sources/mauritius_districts-20261008.geojson"
    parks_path = PACKET / "sources/mauritius_islet_parks-20261008.geojson"
    expected_district_hash = "63f5c5c2660ff216a4429529814a3987ffa05e789bcbe889db520a74236b7540"
    expected_parks_hash = "cbefa4e20d77a48e96ed75ad48b2f69158750e52f2f363a42e6ae0797c84d94e"
    require(sha256(district_path) == expected_district_hash, "retained ONSDI district source bytes changed")
    require(sha256(parks_path) == expected_parks_hash, "retained ONSDI islet-park source bytes changed")

    district_fc = read_json(district_path)
    parks_fc = read_json(parks_path)
    require(len(district_fc["features"]) == 9 and district_fc["numberMatched"] == 9,
            "ONSDI administrative district source must return nine features")
    require(len(parks_fc["features"]) == 8 and parks_fc["numberMatched"] == 8,
            "ONSDI park-point layer must return eight features")
    require(district_fc.get("crs", {}).get("properties", {}).get("name", "").endswith("EPSG::32740"),
            "ONSDI district WFS native CRS must be EPSG:32740")
    require(parks_fc.get("crs", {}).get("properties", {}).get("name", "").endswith("EPSG::4326"),
            "ONSDI park WFS native CRS must be EPSG:4326")

    # Exact one-to-one name join for the nine geographical districts.
    districts_by_name = {}
    for feature in district_fc["features"]:
        name = norm(feature["properties"]["name"])
        require(name not in districts_by_name, f"duplicate ONSDI district name: {name}")
        districts_by_name[name] = feature
    source_by_name = {}
    for feature in mus_admin:
        name = norm(feature["properties"]["shapeName"])
        if name in MUS_DISTRICT_NAMES:
            require(name not in source_by_name, f"duplicate geoBoundaries district name: {name}")
            source_by_name[name] = feature
    current_by_name = {}
    for feature in current.values():
        properties = feature["properties"]
        if properties.get("id", "").startswith("gb:MUS:ADM1:"):
            name = norm(properties["name"])
            if name in MUS_DISTRICT_NAMES:
                require(name not in current_by_name, f"duplicate current district name: {name}")
                current_by_name[name] = feature
    require(set(districts_by_name) == MUS_DISTRICT_NAMES,
            "ONSDI district source roster is not exactly the nine named Mauritius Island districts")
    require(set(source_by_name) == MUS_DISTRICT_NAMES and set(current_by_name) == MUS_DISTRICT_NAMES,
            "2017 source/current roster does not crosswalk one-to-one to the nine ONSDI districts")

    to_equal_area = Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True).transform
    gov_to_equal_area = Transformer.from_crs("EPSG:32740", "EPSG:6933", always_xy=True).transform
    district_rows = []
    for name in sorted(MUS_DISTRICT_NAMES):
        gov_feature = districts_by_name[name]
        gb_feature = source_by_name[name]
        current_feature = current_by_name[name]
        gov_shape = transform(gov_to_equal_area, shape(gov_feature["geometry"]))
        source_shape = transform(to_equal_area, shape(gb_feature["geometry"]))
        current_shape = transform(to_equal_area, shape(current_feature["geometry"]))
        require(all(g.is_valid and g.area > 0 for g in (gov_shape, source_shape, current_shape)),
                f"invalid/non-area geometry in district comparison for {name}")

        district_rows.append({
            "name": gov_feature["properties"]["name"],
            "issue_subject_id": current_feature["properties"]["id"],
            "govmu_wfs_fid": gov_feature.get("id"),
            "crosswalk": "unique accent/case/punctuation-normalized exact name",
            "govmu_against_2017_geoboundaries": overlay_metrics(gov_shape, source_shape),
            "current_atlas_against_govmu": overlay_metrics(gov_shape, current_shape),
            "invalid_geometries": 0,
        })

    parks = [
        {"name": feature["properties"]["name"], "longitude": feature["geometry"]["coordinates"][0],
         "latitude": feature["geometry"]["coordinates"][1]}
        for feature in parks_fc["features"]
    ]
    syc_mismatches = [
        {"id": identity, "reference": row["NBS_reference_region"], "current_parent": row["current_parent_name"]}
        for identity, row in syc_rows.items() if not row["parent_name_matches_reference"]
    ]

    findings_path = PACKET / "subject-findings.json"
    findings = {
        "version": 1,
        "issue": 633,
        "stage": "source-research-with-unresolved-completeness-and-crosswalk-questions",
        "geographic_approval": "not-requested",
        "subject_count": len(issue_rows),
        "subjects": issue_rows,
        "mauritius_official_district_source": {
            "crosswalk_count": len(district_rows),
            "one_to_one_names": [row["name"] for row in district_rows],
            "comparison_path": "district-comparison.json",
            "interpretation": "The government source independently corroborates an exact nine-name administrative roster, but source date/legal lineage are not declared and measured geometry differences are not approval or automatic correction triggers."
        },
        "mauritius_protected_islet_point_screen": {
            "feature_count": len(parks),
            "features": parks,
            "interpretation": "A protected-islet point subset near Mauritius Island, not a physical land inventory or evidence for St Brandon/Agaléga."
        },
        "shom_wms_extent_screen": shom_extent_screen,
        "seychelles_current_parent_mismatches_against_2019_reference": syc_mismatches,
        "cross_scope_findings": [
            "St Brandon and Natural Earth Agaléga GSHHG level-1 non-intersections are insufficient-resolution non-detections, not evidence of absence.",
            "Natural Earth Agaléga MUS-5180 and the geoBoundaries Agaléga ADM1 are distinct disjoint records with different source roles. Keep both IDs and preserve their separate pins pending a physical island-to-record crosswalk.",
            "The SeyMSP API count and grouped records are source lead observations, not island counts; underlying licenseInfo is blank and no polygons are retained.",
            "No current official, licensed geocoded settlement inventory for the complete 24-subject scope was found. Census/statistical localities are names or administrative records, not complete settlement coordinate data.",
            "Shom/IGN Litto3D is an openly licensed high-resolution source candidate for Eparses, Mayotte, and Réunion. Official WMS metadata envelopes enclose the current Mayotte record bbox, but the current Iles Éparses and Réunion record bboxes extend outside their product envelopes; these are extent warnings, not proof of missing data or acquired-tile coverage."
        ],
        "next_actions": [
            "Crosswalk every Eparses, Mayotte, and Réunion target feature to licensed Shom/IGN tile footprints, source masks, acquisition dates, and emergent-land/reef records.",
            "Obtain current Seychelles region-to-island and settlement crosswalks from NBS/Ministry with reusable physical-island geometry rights; resolve Other Islands source feature membership and parent labels.",
            "Obtain current official St Brandon and Agaléga emergent-island/reef vectors or survey coverage metadata under usable reuse terms; compare complete neighbors before any correction recommendation.",
            "Obtain a dated, licensed geocoded settlement/locality source for all assigned territories, or retain the explicit scoped no-source outcome."
        ]
    }
    findings_bytes = (json.dumps(findings, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    input_paths = {
        "scope.json": PACKET / "scope.json",
        "source-inventory.json": PACKET / "source-inventory.json",
        "parent_subject_inventory": inventory_path,
        "parent_sources_registry": source_registry_path,
        "parent_geometry_comparison": prior_geometry_path,
        "parent_seychelles_crosswalk": syc_crosswalk_path,
        "parent_settlement_review": settlement_path,
        "parent_mus_geoboundaries": mus_source_file,
        "parent_syc_geoboundaries": syc_source_file,
        "parent_natural_earth_selected": ne_source_file,
        "current_part_16": ROOT / "data/geography/part-16.json",
        "current_part_23": ROOT / "data/geography/part-23.json",
        "current_part_28": ROOT / "data/geography/part-28.json",
        "retained_onsdi_districts": district_path,
        "retained_onsdi_islet_parks": parks_path,
    }
    comparison = {
        "version": 1,
        "scope_issue": 633,
        "baseline_commit": SCOPE["baseline_commit"],
        "method": {
            "geometry": "Shapely 2.1.2 valid source/current polygon overlay; EPSG:6933 equal-area area operations",
            "source_crs": "GeoBoundary/Natural Earth current and source GeoJSON CRS84 is read as longitude-latitude; ONSDI Mauritius districts transform from retained EPSG:32740 via pyproj 3.7.2",
            "axis_order": "longitude-latitude; all transforms use always_xy=True",
            "repair_policy": "No geometry repair, simplification, or reprojection relabeling. All 27 polygons compared here were valid.",
            "crosswalk": "The nine administrative names use a unique Unicode NFKD, case/punctuation-normalized exact equality; no fuzzy match or centroid inference.",
            "limits": "Symmetric difference is a source-comparison triage metric; a matching name or valid geometry does not prove legal authority, correct role, contemporaneity, complete islands, coastline accuracy, or settlement completeness. Retained #482 all-scope comparisons are read as immutable inputs, not freshly rerun by this script."
        },
        "counts": {
            "issue_subjects": len(issue_rows),
            "matched_current_features": len(current),
            "retained_2017_mauritius_source_features": len(mus_admin),
            "retained_2020_seychelles_source_features": len(syc_admin),
            "onsdi_mauritius_district_features": len(district_fc["features"]),
            "onsdi_islet_park_points": len(parks_fc["features"]),
            "2019_seychelles_regions": crosswalk["regions_assigned"],
            "2019_seychelles_adm3_rows": crosswalk["ADM3_district_rows_in_full_reference"]
        },
        "district_comparisons": district_rows,
        "shom_wms_extent_screen": shom_extent_screen,
        "islet_park_points": parks,
        "retained_parent_scope_comparison_record_count": len(prior_metrics),
        "predecessor_settlement_scope": {
            "issue": settlement_review["scope_issue"],
            "assigned_locations": settlement_review["scope_location_count"],
            "mauritius_outcome": settlement_review["settlement_disposition"]["Mauritius"],
            "seychelles_outcome": settlement_review["settlement_disposition"]["Seychelles"],
            "named_island_territory_outcome": settlement_review["settlement_disposition"]["Natural Earth island/department units"]
        },
        "input_sha256": {name: sha256(path) for name, path in input_paths.items()},
        "output_sha256": {}
    }
    district_document = {
        "version": 1,
        "method": comparison["method"],
        "input_sha256": comparison["input_sha256"],
        "district_comparisons": district_rows,
        "park_points": parks,
        "shom_wms_extent_screen": shom_extent_screen,
    }
    eparses = next(row for row in shom_extent_screen if row["subject_id"] == "atlas:coverage:ATF-5919")
    reunion = next(row for row in shom_extent_screen if row["subject_id"] == "atlas:coverage:FRA-4601")
    district_document["metrics"] = {
        "ONSDI-vs-2017-min": min(row["govmu_against_2017_geoboundaries"]["symmetric_difference_percent_of_union"] for row in district_rows),
        "ONSDI-vs-2017-max": max(row["govmu_against_2017_geoboundaries"]["symmetric_difference_percent_of_union"] for row in district_rows),
        "Atlas-vs-ONSDI-min": min(row["current_atlas_against_govmu"]["symmetric_difference_percent_of_union"] for row in district_rows),
        "Atlas-vs-ONSDI-max": max(row["current_atlas_against_govmu"]["symmetric_difference_percent_of_union"] for row in district_rows),
        "Shom-Eparses-product-envelope-west-excess": eparses["record_bbox_outside_edges_degrees"]["west_degrees"],
        "Shom-Reunion-product-envelope-east-excess": reunion["record_bbox_outside_edges_degrees"]["east_degrees"],
        "Shom-product-envelope-contained-targets": sum(row["record_bbox_inside_wms_envelope"] for row in shom_extent_screen),
    }
    district_bytes = (json.dumps(district_document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    comparison["output_sha256"] = {
        "subject-findings.json": hashlib.sha256(findings_bytes).hexdigest(),
        "district-comparison.json": hashlib.sha256(district_bytes).hexdigest(),
    }
    results_bytes = (json.dumps(comparison, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    output_payload = {
        "subject-findings.json": findings_bytes,
        "district-comparison.json": district_bytes,
        "results.json": results_bytes,
    }
    if args.compare_vintage:
        prior = args.compare_vintage
        reproduced = {}
        new_products = {
            "subject-findings.json": findings_bytes,
            "district-comparison.json": district_bytes,
            "results.json": results_bytes,
        }
        for name, new_bytes in new_products.items():
            old_descriptor = next(row for row in manifest["outputs"] if row["path"].endswith(
                f"/vintages/{prior}/{name}"))
            old_bytes = CANDIDATE_BYTES[old_descriptor["path"]]
            reproduced[name] = hashlib.sha256(old_bytes).hexdigest() == hashlib.sha256(new_bytes).hexdigest()
        require(all(reproduced.values()), "Fresh runs differ in one or more complete result products")

        # Known projected squares exercise the same measurement used by all overlays.
        from shapely.geometry import box
        identical = overlay_metrics(box(0, 0, 2, 2), box(0, 0, 2, 2))
        offset = overlay_metrics(box(0, 0, 2, 2), box(1, 0, 3, 2))
        require(identical["symmetric_difference_percent_of_union"] == 0.0,
                "positive overlay control failed")
        require(abs(offset["symmetric_difference_percent_of_union"] - (200 / 3)) < 1e-12,
                "negative overlay control failed")

        mayotte = next(row for row in shom_extent_screen if row["subject_id"] == "atlas:coverage:FRA-4602")
        mismatches = [row for row in shom_extent_screen if not row["record_bbox_inside_wms_envelope"]]
        require(mayotte["record_bbox_inside_wms_envelope"] and len(mismatches) == 2 and
                eparses["record_bbox_outside_edges_degrees"].get("west_degrees", 0) > 0.6 and
                reunion["record_bbox_outside_edges_degrees"].get("east_degrees", 0) > 0.01,
                "positive/negative Shom envelope controls failed")

        expected_tests = [
            "test_broken_symlink_run_is_rejected_without_following_it",
            "test_existing_ordinary_run_is_preserved",
            "test_failure_after_calculation_has_no_output_vintage_or_receipt",
            "test_parent_roster_uses_authenticated_reader_bytes",
            "test_path_traversal_is_rejected",
        ]
        safety = subprocess.run([__import__("sys").executable, str(PACKET / "test_reproduce_safety.py")],
                                cwd=ROOT, capture_output=True, text=True, check=False)
        require(safety.returncode == 0 and all(name in safety.stderr for name in expected_tests) and
                "Ran 5 tests" in safety.stderr and "OK" in safety.stderr,
                "reproduction adverse-control suite did not complete every expected test")

        def control(method_id, kind, **fields):
            value = {"method_id": method_id, "kind": kind, "outcome": "passed", **fields}
            return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

        prior_product_bytes = {
            name: CANDIDATE_BYTES[next(row["path"] for row in manifest["outputs"] if row["path"].endswith(
                f"/vintages/{prior}/{name}"))] for name in new_products
        }
        run_one_digest = hashlib.sha256(b"".join(name.encode() + b"\0" + prior_product_bytes[name]
                                                  for name in sorted(new_products))).hexdigest()
        run_two_digest = hashlib.sha256(b"".join(name.encode() + b"\0" + new_products[name]
                                                  for name in sorted(new_products))).hexdigest()
        require(run_one_digest == run_two_digest, "complete two-run product digests differ")
        output_payload.update({
            "control-generator-positive.json": control("wio-run-generation", "positive-control",
                complete_receipt=True, resolved_subjects=len(current), joined_districts=len(district_rows),
                valid_geometry_comparisons=27),
            "control-generator-negative.json": control("wio-run-generation", "negative-control",
                adverse_tests=expected_tests, no_partial_receipt=True),
            "control-generator-reproducibility.json": control("wio-run-generation", "reproducibility",
                run_one_sha256=run_one_digest, run_two_sha256=run_two_digest,
                compared_products=reproduced),
            "control-overlay-positive.json": control("mauritius-equal-area-overlay", "positive-control",
                fixture="identical projected 2x2 squares", symmetric_difference_percent=identical["symmetric_difference_percent_of_union"]),
            "control-overlay-negative.json": control("mauritius-equal-area-overlay", "negative-control",
                fixture="projected 2x2 squares offset by 1 unit", symmetric_difference_percent=offset["symmetric_difference_percent_of_union"]),
            "control-shom-positive.json": control("shom-wms-envelope-screen", "positive-control",
                subject_id=mayotte["subject_id"], enclosed=True),
            "control-shom-negative.json": control("shom-wms-envelope-screen", "negative-control",
                subjects=[row["subject_id"] for row in mismatches], outside_edges=[row["record_bbox_outside_edges_degrees"] for row in mismatches]),
        })
    if args.simulate_post_computation_failure:
        raise SystemExit("SIMULATED: failed after computation and before publication")
    records = writer.publish_bytes(output_payload)
    receipt_path = writer.root / "publication.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(receipt.get("version") == 1 and receipt.get("status") == "complete" and
            receipt.get("outputs") == records,
            "fresh run completion receipt does not match the complete output set")
    for record in records:
        output_path = ROOT / record["path"]
        raw = output_path.read_bytes()
        require(len(raw) == record["bytes"] and hashlib.sha256(raw).hexdigest() == record["sha256"],
                "published run output differs from its completion receipt")
    print(json.dumps({
        "status": "reproduced",
        "vintage": args.vintage,
        "publication": receipt_path.relative_to(ROOT).as_posix(),
        "issue_subjects": len(issue_rows),
        "current_subjects_resolved": len(current),
        "mauritius_district_names": len(district_rows),
        "valid_geometry_comparisons": 27,
        "shom_bbox_inside_by_target": {row["subject_id"]: row["record_bbox_inside_wms_envelope"] for row in shom_extent_screen},
        "district_symdiff_range_percent": [
            min(row["govmu_against_2017_geoboundaries"]["symmetric_difference_percent_of_union"] for row in district_rows),
            max(row["govmu_against_2017_geoboundaries"]["symmetric_difference_percent_of_union"] for row in district_rows)
        ],
        "finding_count": len(issue_rows),
        "outputs": [record["path"] for record in records],
    }, indent=2))


if __name__ == "__main__":
    main()
