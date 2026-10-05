#!/usr/bin/env python3
"""Reproduce the scoped Texas county/source crosswalk and geometry screening."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import subprocess
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import shapely
import shapefile
from pyproj import Transformer
from shapely.geometry import box, shape
from shapely.ops import transform

BASELINE = "4877ef4e99528615daf657a376b7605d1657f817"
ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
ISSUE_ID = 431
ADJACENT_ISSUE_ID = 432
TEXAS_ID = "framework:province:texas:d326ad9fd3b4"
AREA_ID = "framework:area:west-south-central:1e780b4bc1dd"
REGION_ID = "framework:region:southeastern-north-america:8606d9313330"
PINNED_HASHES = {
    "source/geoBoundaries-USA-ADM2.geojson": "81fdd384df8012e5007ed2994a8ab306352f3c48e32cd8ea99182195e8647f43",
    "source/geoBoundaries-USA-ADM2-metaData.json": "a4d2a82a1cd434960b6ed49531bff3330d0881674eea9dc8711e1ad6bf049b9f",
    "source/census-2018/counties-layer-metadata.json": "2d3b72f3957787cae0f8ae5a77bafd0b9603f8d6a5b4db2a700898e179e855c6",
    "source/census-2018/texas-counties.geojson": "309151b2ea2bfcad71698f7c3b82a52fc92cb3a59c29ee040d22ec7263b34cc7",
    "source/census-2018/cb_2018_us_county_500k.zip": "aaa866af327754e1b80aa87bfb97b04a7209f4f871075aef84affb8f0b3afe67",
    "source/census-2025/counties-layer-metadata.json": "0c64a04e01055622c957ef56f9b8fd35c99c4bcc78c2fa1bba11e716d6a72f31",
    "source/census-2025/texas-counties.geojson": "efc43054c4a7f555ba1a1cf26e6315e5562005635152a9a41795152fe0eec0d6",
}
EQUAL_AREA = Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True)


def stable_json(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_bytes(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{BASELINE}:{path}"], cwd=REPO)


def issue_workload(issue: dict) -> dict:
    for marker in issue["body"].split("```")[1::2]:
        try:
            candidate = json.loads(marker.removeprefix("json\n"))
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(candidate, dict) and "member_location_ids" in candidate:
            return candidate
    raise ValueError(f"Issue #{issue.get('number')} has no machine-readable member roster")


def projected(geometry):
    return transform(EQUAL_AREA.transform, geometry)


def iou(left, right) -> float:
    union = left.union(right).area
    return 1.0 if union == 0 else left.intersection(right).area / union


def component_count(geometry) -> int:
    if geometry.geom_type == "Polygon":
        return 1
    if geometry.geom_type == "MultiPolygon":
        return len(geometry.geoms)
    return 0


def emit_json(path: Path, value: object) -> None:
    path.write_bytes(stable_json(value))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True, help="new directory under this packet for immutable run outputs")
    args = parser.parse_args()
    output = ROOT / args.output_dir
    if not output.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("Output directory must stay inside the issue-owned packet")

    issue = json.loads((ROOT / "issue-snapshot.json").read_bytes())
    adjacent_issue = json.loads((ROOT / "source/adjacent-issue-432-api.json").read_bytes())
    scope = json.loads((ROOT / "scope.json").read_bytes())
    for relative, expected_sha in PINNED_HASHES.items():
        actual_sha = file_sha(ROOT / relative)
        if actual_sha != expected_sha:
            raise ValueError(f"Pinned evidence hash mismatch for {relative}: {actual_sha}")
    workload = issue_workload(issue)
    if workload != scope:
        raise ValueError("Saved scope does not byte-for-byte match the issue's workload JSON")
    subjects = scope["member_location_ids"]
    subject_set = set(subjects)
    if len(subjects) != 254 or len(subject_set) != 254 or scope["location_count"] != 254:
        raise ValueError("Issue scope is not the exact 254-unique-subject Texas workload")

    adjacent_scope = issue_workload(adjacent_issue)
    adjacent_ids = set(adjacent_scope["member_location_ids"])
    if len(adjacent_ids) != 216:
        raise ValueError("Adjacent packet #432 roster changed from the recorded 216 subjects")
    if subject_set & adjacent_ids:
        raise ValueError("Issue #431 overlaps adjacent packet #432")
    area_subject_ids = subject_set | adjacent_ids

    source_geojson = json.loads((ROOT / "source/geoBoundaries-USA-ADM2.geojson").read_bytes())
    meta = json.loads((ROOT / "source/geoBoundaries-USA-ADM2-metaData.json").read_bytes())
    lfs_pointer = (ROOT / "source/geoBoundaries-USA-ADM2.geojson.lfs-pointer").read_text()
    lfs_oid = lfs_pointer.split("oid sha256:", 1)[1].splitlines()[0]
    if file_sha(ROOT / "source/geoBoundaries-USA-ADM2.geojson") != lfs_oid:
        raise ValueError("Restored GeoBoundaries bytes do not match their upstream LFS OID")
    source_features = {
        f["properties"]["shapeID"]: f for f in source_geojson["features"]
        if f["properties"].get("shapeGroup") == "USA" and f["properties"].get("shapeType") == "ADM2"
    }
    source_by_atlas_id = {}
    for subject in subjects:
        source_id = subject.rsplit(":", 1)[1]
        feature = source_features.get(source_id)
        if feature is None:
            raise ValueError(f"No exact pinned source feature for {subject}")
        source_by_atlas_id[subject] = feature

    c18 = json.loads((ROOT / "source/census-2018/texas-counties.geojson").read_bytes())
    c25 = json.loads((ROOT / "source/census-2025/texas-counties.geojson").read_bytes())
    census18 = c18["features"]
    census25 = c25["features"]
    if len(census18) != 254 or len(census25) != 254:
        raise ValueError("Pinned Census comparison rosters do not each contain 254 Texas counties")
    census18_by_name = defaultdict(list)
    census25_by_geoid = {f["properties"]["GEOID"]: f for f in census25}
    for feature in census18:
        census18_by_name[feature["properties"]["BASENAME"]].append(feature)
    if len(census25_by_geoid) != 254:
        raise ValueError("2025 Texas GEOIDs are not unique")

    # Read the exact generalized 2018 Census Cartographic Boundary File cited
    # by the upstream GeoBoundaries metadata. This is distinct from detailed
    # TIGER/Line and is a representation comparator, not legal adjudication.
    cbf_zip = ROOT / "source/census-2018/cb_2018_us_county_500k.zip"
    with zipfile.ZipFile(cbf_zip) as archive:
        names = archive.namelist()
        shp_name = next(name for name in names if name.endswith(".shp"))
        dbf_name = next(name for name in names if name.endswith(".dbf"))
        shx_name = next(name for name in names if name.endswith(".shx"))
        cbf_reader = shapefile.Reader(shp=archive.open(shp_name), dbf=archive.open(dbf_name), shx=archive.open(shx_name))
        cbf_fields = [field[0] for field in cbf_reader.fields[1:]]
        cbf_rows = {}
        for shape_record in cbf_reader.iterShapeRecords():
            properties = dict(zip(cbf_fields, shape_record.record))
            if properties["STATEFP"] == "48":
                cbf_rows[properties["GEOID"]] = (shape(shape_record.shape.__geo_interface__), properties)
    if len(cbf_rows) != 254:
        raise ValueError(f"2018 Census CBF Texas roster is not 254 counties: {len(cbf_rows)}")

    world_index = json.loads(git_bytes("data/world-index.json"))
    wanted_parts = set()
    atlas_features = {}
    area_features = {}
    part_hashes = {}
    for relative in world_index["parts"]:
        path = f"data/{relative}"
        raw = git_bytes(path)
        part_hashes[path] = hashlib.sha256(raw).hexdigest()
        data = json.loads(raw)
        found = 0
        for feature in data["features"]:
            properties = feature["properties"]
            if properties["id"] in area_subject_ids:
                if properties["id"] in area_features:
                    raise ValueError(f"Duplicate live-baseline subject: {properties['id']}")
                area_features[properties["id"]] = feature
                if properties["id"] in subject_set:
                    atlas_features[properties["id"]] = feature
                found += int(properties["id"] in subject_set)
        if found:
            wanted_parts.add(path)
    if set(atlas_features) != subject_set:
        raise ValueError(f"Live baseline subject difference: missing={len(subject_set-set(atlas_features))}")
    if set(area_features) != area_subject_ids:
        raise ValueError(f"Current West South Central area feature difference: missing={len(area_subject_ids-set(area_features))}")

    inv_raw = git_bytes("data/macro-foundation/current-membership-inventory.json.gz")
    inventory = json.loads(gzip.decompress(inv_raw))
    area = next(item for item in inventory if item["id"] == AREA_ID)
    province = next(item for item in inventory if item["id"] == TEXAS_ID)
    if set(province["member_location_ids"]) != subject_set:
        raise ValueError("Current v6 Texas member inventory does not exactly equal issue #431 scope")
    if len(area["member_location_ids"]) != 470 or not subject_set.issubset(set(area["member_location_ids"])):
        raise ValueError("Current v6 West South Central area membership is inconsistent")
    if len(area["member_location_ids"]) != len(subject_set) + len(adjacent_ids):
        raise ValueError("Sibling issue rosters do not account for the full current area member count")
    if set(area["member_location_ids"]) != subject_set | adjacent_ids:
        raise ValueError("Sibling issue rosters are not an exact partition of current area members")
    parent_counts = Counter(feature["properties"].get("parent_id") for feature in area_features.values())
    expected_parent_counts = {
        "framework:province:texas:d326ad9fd3b4": 254,
        "framework:province:oklahoma:61cefcfa5f2e": 77,
        "framework:province:arkansas:6fd10bbe861b": 75,
        "framework:province:louisiana:d516859f0536": 64,
    }
    if dict(parent_counts) != expected_parent_counts:
        raise ValueError(f"Current West South Central state membership changed: {dict(parent_counts)}")
    expected_granularity = {"source_id": "gb:USA:ADM2", "source_role": "Counties", "reference_year": "2018",
        "administrative_level": "ADM2", "parent_source_level": "ADM1", "license": "Public Domain"}
    for feature in area_features.values():
        properties = feature["properties"]
        metadata = properties.get("metadata", {})
        if not properties.get("name") or any(metadata.get(key) != value for key, value in expected_granularity.items()):
            raise ValueError(f"Neighboring granularity/source metadata differs for {properties.get('id')}")

    registry = json.loads(git_bytes("data/administrative-sources.json"))["gb:USA:ADM2"]
    release_manifest = json.loads(git_bytes("data/geographic-releases/current-manifest.json"))
    macro_review_index = json.loads(git_bytes("data/macro-foundation/review-index.json"))
    if macro_review_index.get("regional_interiors_approved") is not False:
        raise ValueError("This evidence packet must not inherit regional approval")

    # Axis-order control: source GeoJSON is lon/lat; a swapped transform must differ.
    control_xy = EQUAL_AREA.transform(10.0, 45.0)
    swapped_xy = EQUAL_AREA.transform(45.0, 10.0)
    if abs(control_xy[0] - swapped_xy[0]) < 1_000_000 or abs(control_xy[1] - swapped_xy[1]) < 1_000_000:
        raise ValueError("Coordinate-order negative control did not detect swapped axes")
    if iou(projected(shape(box(0, 0, 1, 1).__geo_interface__)), projected(shape(box(0, 0, 1, 1).__geo_interface__))) != 1.0:
        raise ValueError("Identical-geometry positive control failed")
    if iou(projected(shape(box(0, 0, 1, 1).__geo_interface__)), projected(shape(box(3, 0, 4, 1).__geo_interface__))) != 0.0:
        raise ValueError("Disjoint-geometry negative control failed")

    rows = []
    mismatch_rows = []
    component_counts = Counter()
    areas = defaultdict(list)
    metrics = {name: [] for name in (
        "source_to_atlas_v6_iou",
        "source_to_2018_census_iou", "atlas_v6_to_2018_census_iou",
        "atlas_v6_to_2025_census_iou", "census_2018_to_2025_iou",
        "source_to_2018_cbf_iou", "atlas_v6_to_2018_cbf_iou",
    )}
    for atlas_id in sorted(subjects):
        source_feature = source_by_atlas_id[atlas_id]
        source_props = source_feature["properties"]
        atlas_feature = atlas_features[atlas_id]
        atlas_props = atlas_feature["properties"]
        name = source_props["shapeName"]
        matches18 = census18_by_name.get(name, [])
        reasons = []
        if len(matches18) != 1:
            reasons.append("nonunique-or-missing-2018-census-name-join")
            mismatch_rows.append(atlas_id)
            continue
        feature18 = matches18[0]
        census_props = feature18["properties"]
        feature25 = census25_by_geoid.get(census_props["GEOID"])
        if feature25 is None:
            reasons.append("2018-geoid-missing-from-2025-census")
            mismatch_rows.append(atlas_id)
            continue
        if census_props["STATE"] != "48" or feature25["properties"]["STATE"] != "48":
            reasons.append("census-state-code-not-texas")
        if atlas_props.get("parent_id") != TEXAS_ID:
            reasons.append("atlas-parent-not-texas")
        if atlas_props.get("name") != name or atlas_props.get("metadata", {}).get("original_id") != source_props["shapeID"]:
            reasons.append("atlas-source-identity-mismatch")
        source_geom = shape(source_feature["geometry"])
        atlas_geom = shape(atlas_feature["geometry"])
        census18_geom = shape(feature18["geometry"])
        census25_geom = shape(feature25["geometry"])
        cbf_geom, cbf_props = cbf_rows[census_props["GEOID"]]
        geoms = {"source": source_geom, "atlas": atlas_geom, "census2018": census18_geom, "census2025": census25_geom, "census2018_cbf_500k": cbf_geom}
        for label, geom in geoms.items():
            if geom.geom_type not in {"Polygon", "MultiPolygon"} or geom.is_empty or not geom.is_valid or geom.area <= 0:
                reasons.append(f"{label}-geometry-invalid-or-nonpolygon")
            component_counts[f"{label}_parts_{component_count(geom)}"] += 1
        projected_geoms = {key: projected(value) for key, value in geoms.items()}
        comparisons = {
            "source_to_atlas_v6_iou": iou(projected_geoms["source"], projected_geoms["atlas"]),
            "source_to_2018_census_iou": iou(projected_geoms["source"], projected_geoms["census2018"]),
            "atlas_v6_to_2018_census_iou": iou(projected_geoms["atlas"], projected_geoms["census2018"]),
            "atlas_v6_to_2025_census_iou": iou(projected_geoms["atlas"], projected_geoms["census2025"]),
            "census_2018_to_2025_iou": iou(projected_geoms["census2018"], projected_geoms["census2025"]),
            "source_to_2018_cbf_iou": iou(projected_geoms["source"], projected_geoms["census2018_cbf_500k"]),
            "atlas_v6_to_2018_cbf_iou": iou(projected_geoms["atlas"], projected_geoms["census2018_cbf_500k"]),
        }
        for metric, value in comparisons.items():
            metrics[metric].append(value)
        for key, geom in projected_geoms.items():
            areas[key].append(geom.area)
        # A 0.98 value is a screening flag for human source review, not a fact or legal test.
        screening_flags = [metric for metric, value in comparisons.items() if value < 0.98]
        if screening_flags:
            reasons.append("overlap-screen-below-0.98-see-metric; not a correction finding")
        component_difference = component_count(source_geom) != component_count(atlas_geom)
        if component_difference:
            reasons.append("source-atlas-component-count-difference-review; not a correction finding")
        if reasons:
            mismatch_rows.append(atlas_id)
        rows.append({
            "subject_id": atlas_id,
            "atlas_name": atlas_props.get("name"),
            "parent_id": atlas_props.get("parent_id"),
            "source_id": source_props["shapeID"],
            "source_name": name,
            "source_shape_iso": source_props.get("shapeISO"),
            "source_shape_type": source_props.get("shapeType"),
            "source_shape_group": source_props.get("shapeGroup"),
            "source_role": atlas_props.get("metadata", {}).get("source_role"),
            "source_vintage": atlas_props.get("metadata", {}).get("reference_year"),
            "source_license": atlas_props.get("metadata", {}).get("license"),
            "atlas_administrative_level": atlas_props.get("metadata", {}).get("administrative_level"),
            "atlas_source_parent_level": atlas_props.get("metadata", {}).get("parent_source_level"),
            "atlas_semantic_review_status": atlas_props.get("metadata", {}).get("semantic_review", {}).get("status"),
            "atlas_geographic_area_code": atlas_props.get("metadata", {}).get("geographic_area_code"),
            "census_geoid_2018": census_props["GEOID"],
            "census_geoid_2025": feature25["properties"]["GEOID"],
            "census_county_name_2018": census_props["NAME"],
            "census_county_name_2025": feature25["properties"]["NAME"],
            "census_2018_county_status": census_props["FUNCSTAT"],
            "census_2025_county_status": feature25["properties"]["FUNCSTAT"],
            "census_2018_cbf_name": cbf_props["NAME"],
            "census_2018_cbf_land_area_m2": int(cbf_props["ALAND"]),
            "census_2018_cbf_water_area_m2": int(cbf_props["AWATER"]),
            "geometry_types": {key: geom.geom_type for key, geom in geoms.items()},
            "geometry_valid": {key: geom.is_valid for key, geom in geoms.items()},
            "multipart_components": {key: component_count(geom) for key, geom in geoms.items()},
            "equal_area_iou": {key: round(value, 9) for key, value in comparisons.items()},
            "screening_flags": screening_flags,
            "classification": (
                "insufficient-evidence" if screening_flags or component_difference else "justified"
            ),
            "classification_basis": (
                "insufficient-evidence: a reproducible equal-area screening difference or source-to-Atlas component-count difference remains unexplained at this evidence tier; the 0.98 value is only the explicit triage trigger, not proof of error"
                if screening_flags or component_difference else
                "justified for county identity, source tier and parent: exact source shapeID, one-to-one 2018/2025 Census name/GEOID joins, current Texas parent, and no comparison triggered the stated triage screen; this does not prove legal boundary or island completeness"
            ),
            "source_atlas_component_count_difference": component_difference,
            "unresolved_findings": [
                "Census TIGER is a statistical geography, not a legal boundary determination",
                "repository source-catalog SHA-256 basis differs from restored pinned upstream GeoJSON bytes; #954 tracks this discrepancy for its own Louisiana/Oklahoma/Arkansas scope only, and does not resolve these Texas members",
            ],
            "reasons": reasons,
        })

    if len(rows) != 254 or len({row["subject_id"] for row in rows}) != 254:
        raise ValueError(f"Assessment row coverage mismatch: {len(rows)}")
    if len({row["census_geoid_2018"] for row in rows}) != 254:
        raise ValueError("2018 Census GEOID crosswalk is not one-to-one")
    if len({row["census_geoid_2025"] for row in rows}) != 254:
        raise ValueError("2025 Census GEOID crosswalk is not one-to-one")

    ledger = []
    for metric, values in metrics.items():
        ordered = sorted(values)
        ledger.append({
            "metric_id": metric,
            "count": len(values),
            "minimum": round(min(values), 9),
            "median": round(float(np.median(values)), 9),
            "mean": round(float(np.mean(values)), 9),
            "maximum": round(max(values), 9),
            "below_0_98_screen_count": sum(value < 0.98 for value in values),
            "units": "dimensionless equal-area intersection-over-union",
            "vintage": "current",
            "evaluation_commit": BASELINE,
        })
    summary = {
        "version": 2,
        "baseline_commit": BASELINE,
        "issue_number": ISSUE_ID,
        "adjacent_issue_number": ADJACENT_ISSUE_ID,
        "subject_count": len(subjects),
        "assessment_rows": len(rows),
        "overall_classification_counts": dict(Counter(row["classification"] for row in rows)),
        "issue_scope_release_pin": scope.get("release"),
        "current_main_release_manifest": release_manifest,
        "current_main_location_index_sha256": hashlib.sha256(git_bytes("data/world-index.json")).hexdigest(),
        "current_main_hierarchy_sha256": hashlib.sha256(git_bytes("data/hierarchy.json")).hexdigest(),
        "current_main_current_membership_inventory_sha256": hashlib.sha256(inv_raw).hexdigest(),
        "current_main_macro_review_index_sha256": hashlib.sha256(git_bytes("data/macro-foundation/review-index.json")).hexdigest(),
        "current_main_geography_part_sha256": part_hashes,
        "current_main_subject_parts": sorted(wanted_parts),
        "current_main_area_members": len(area["member_location_ids"]),
        "current_main_texas_members": len(province["member_location_ids"]),
        "area_subject_partition": {
            "issue_431_subjects": len(subject_set),
            "issue_432_subjects": len(adjacent_ids),
            "overlap": 0,
            "union_equals_current_area": True,
        },
        "current_neighboring_granularity": {
            "subjects": len(area_features),
            "unique_named_units": sum(bool(feature["properties"].get("name")) for feature in area_features.values()),
            "source_metadata": expected_granularity,
            "state_parent_counts": dict(sorted(parent_counts.items())),
            "roster_coverage": "exact; Texas #431 and siblings #432",
        },
        "source_metadata": {
            "geoBoundaries_release_commit": "9469f09592ced973a3448cf66b6100b741b64c0d",
            "geoBoundaries_lfs_raw_sha256": lfs_oid,
            "geoBoundaries_lfs_size": (ROOT / "source/geoBoundaries-USA-ADM2.geojson").stat().st_size,
            "geoBoundaries_metadata": meta,
            "repository_administrative_source_record_sha256": registry.get("sha256"),
            "repository_hash_basis_reconciled": registry.get("sha256") == lfs_oid,
            "source_original_id_field": "shapeID",
            "source_shapeISO_nonempty_subject_count": sum(bool(source_by_atlas_id[s]["properties"].get("shapeISO")) for s in subjects),
            "repo_scope_claims": {
                "role": "Counties",
                "vintage": "2018",
                "license": "Public Domain",
                "provenance_note": "Pinned GeoBoundaries metadata calls boundarySource United States Census Bureau MAF/TIGER Database, boundaryCanonical Counties, and points licenseSource to the Census Cartographic Boundary File page; source uses shapeID (not county GEOID) for identities.",
            },
        },
        "census_layer_counts": {"2018_tiger_counties": len(census18), "2025_tiger_counties": len(census25), "2018_cartographic_boundary_file_texas_counties": len(cbf_rows)},
        "geometry_component_counts": dict(sorted(component_counts.items())),
        "equal_area_method": {
            "source_coordinates": "GeoJSON longitude, latitude (WGS84)",
            "projection": "EPSG:6933 (World Equidistant Cylindrical / equal-area)",
            "axis_order": "always_xy=True",
            "measurement": "Shapely planar intersection-over-union after EPSG:4326 to EPSG:6933 transformation; screening only, not a legal-boundary test",
            "control_lon_lat_10_45": [round(control_xy[0], 6), round(control_xy[1], 6)],
            "negative_control_swapped_lat_lon_45_10": [round(swapped_xy[0], 6), round(swapped_xy[1], 6)],
            "positive_control_identical_polygon_iou": 1.0,
            "negative_control_disjoint_polygon_iou": 0.0,
        },
        "metrics": ledger,
        "screening_threshold_note": "0.98 is a triage threshold only; it neither proves correctness nor justifies a correction.",
        "limits": [
            "The scope's declared release is v5; this run compares the exact frozen ID roster with v6 on current main and preserves the v5 declarations.",
            "The 2018 source file's identity, license, vintage, role and full-file hash are traced to the pinned GeoBoundaries commit/LFS OID; the repository's prior source-catalog SHA field has a different, unresolved basis tracked in #954.",
            "Census TIGER geometries represent statistical collection/tabulation geographies and are not a legal determination of jurisdictional authority or ownership.",
            "Equal-area polygon overlap cannot establish surveyed boundaries, all island/shoreline completeness, or boundary-change causes; low overlaps are comparison targets only.",
            "The 2018 Census 1:500,000 Cartographic Boundary File is the same-purpose generalized comparator cited in the upstream source metadata. Differences from it, as well as detailed TIGER/Line differences, remain representational signals and do not establish an erroneous county polygon.",
            "No region interior approval, boundary modification, import, publication or release certification follows from this packet.",
        ],
    }

    output.mkdir(parents=True, exist_ok=False)
    (output / "county-assessments.jsonl").write_bytes(b"".join(stable_json(row) for row in rows))
    emit_json(output / "comparison-summary.json", summary)
    emit_json(output / "scope-and-control-checks.json", {
        "issue_scope_equals_saved_snapshot": True,
        "unique_issue_subjects": len(subject_set),
        "all_subjects_present_in_current_main": len(atlas_features),
        "all_subjects_match_current_texas_membership": True,
        "all_subjects_with_current_texas_parent": sum(atlas_features[s]["properties"].get("parent_id") == TEXAS_ID for s in subjects),
        "current_area_count": len(area["member_location_ids"]),
        "current_area_feature_count": len(area_features),
        "all_area_subjects_named": all(bool(feature["properties"].get("name")) for feature in area_features.values()),
        "all_area_subjects_share_county_role_vintage_license_and_ADM2_tier": True,
        "current_area_state_parent_counts": dict(sorted(parent_counts.items())),
        "adjacent_packet_count": len(adjacent_ids),
        "sibling_intersection": 0,
        "sibling_union_is_area": True,
        "geoBoundaries_source_matches_issue_roster": len(source_by_atlas_id),
        "unique_2018_county_crosswalks": len({row["census_geoid_2018"] for row in rows}),
        "unique_2025_county_crosswalks": len({row["census_geoid_2025"] for row in rows}),
        "assessment_row_count": len(rows),
        "row_identity_or_geometry_warnings": len(mismatch_rows),
        "all_geometries_valid": all(all(row["geometry_valid"].values()) for row in rows),
        "axis_order_control_passed": True,
        "identical_geometry_control_passed": True,
        "disjoint_geometry_control_passed": True,
        "mismatch_subjects": mismatch_rows,
    })


if __name__ == "__main__":
    main()
