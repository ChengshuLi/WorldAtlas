#!/usr/bin/env python3
"""Reproduce the exact Southeastern North America #428 county evidence."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import shapefile
from pyproj import Transformer
from shapely.geometry import box, shape
from shapely import make_valid
from shapely.ops import transform
from shapely.validation import explain_validity

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
from evidence.geometry import METHOD as SHARED_GEOMETRY_METHOD, VERSION as SHARED_GEOMETRY_VERSION, land_area_m2, transform_point

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
BASELINE = "bfa1c56ef72c1bc3a9d1fcf8263d073a966bf46f"
ISSUE = 428
REGION_ID = "framework:region:southeastern-north-america:8606d9313330"
AREA_IDS = {
    "framework:area:east-south-central:f7acffb4c365": 364,
    "framework:area:south-atlantic:383dc695ee31": 587,
}
ISSUE_ROSTER_SHA256 = "3ca1e40285884fca1e3ac8a23868e9a49e6d7c706c5c1106f560ffcede075dbc"
SOURCE_HASHES = {
    "source/geoBoundaries-USA-ADM2.geojson": "81fdd384df8012e5007ed2994a8ab306352f3c48e32cd8ea99182195e8647f43",
    "source/geoBoundaries-USA-ADM2-metaData.json": "a4d2a82a1cd434960b6ed49531bff3330d0881674eea9dc8711e1ad6bf049b9f",
    "source/census-2018/cb_2018_us_county_500k.zip": "aaa866af327754e1b80aa87bfb97b04a7209f4f871075aef84affb8f0b3afe67",
    "source/census-2018/georgia-kentucky-counties.geojson": "aab25c2227638b0048020747f8dd82b019ddd6f26100585c35533c5036cc7219",
    "source/census-2025/georgia-kentucky-counties.geojson": "e5296a323ee4c38afdf7c54a32e67b77c2e98647a6535cb2464b699fb8740105",
}
STATE_FIPS = {"Georgia": "13", "Kentucky": "21"}
EXPECTED_METADATA = {
    "source_id": "gb:USA:ADM2",
    "source_role": "Counties",
    "reference_year": "2018",
    "administrative_level": "ADM2",
    "parent_source_level": "ADM1",
    "license": "Public Domain",
}
PROJECTION = Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True)


def canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def git_bytes(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{BASELINE}:{path}"], cwd=REPO)


def issue_scope(snapshot: dict) -> dict:
    for match in re.finditer(r"```(?:json)?\s*(\{.*?\})\s*```", snapshot["body"], re.S):
        try:
            value = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "member_location_ids" in value:
            return value
    raise ValueError(f"Issue #{snapshot.get('number')} has no exact member roster")


def required_source_feature(subject_id: str, source_features: dict) -> dict:
    if subject_id not in source_features:
        raise ValueError(f"No exact GeoBoundaries shapeID for {subject_id}")
    return source_features[subject_id]


def projected(geometry):
    return transform(PROJECTION.transform, geometry)


def iou(left, right) -> float:
    union = left.union(right).area
    return 1.0 if union == 0 else left.intersection(right).area / union


def components(geometry) -> int:
    if geometry.geom_type == "Polygon":
        return 1
    if geometry.geom_type == "MultiPolygon":
        return len(geometry.geoms)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    output = ROOT / args.output_dir
    if not output.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("Output directory must remain under the issue-owned packet")
    output.mkdir(parents=True, exist_ok=False)

    snapshot = json.loads((ROOT / "issue-snapshot.json").read_bytes())
    scope = json.loads((ROOT / "scope.json").read_bytes())
    if issue_scope(snapshot) != scope or snapshot["number"] != ISSUE:
        raise ValueError("Saved workload does not exactly match issue #428")
    subjects = scope["member_location_ids"]
    subject_set = set(subjects)
    if len(subjects) != 279 or len(subject_set) != 279 or scope["location_count"] != 279:
        raise ValueError("Issue scope is not the exact 279-unique-subject workload")
    if sha_bytes(("\n".join(subjects)).encode()) != ISSUE_ROSTER_SHA256:
        raise ValueError("Issue roster checksum differs from its frozen declaration")
    if sha_bytes(("\n".join(subjects[:-1])).encode()) == ISSUE_ROSTER_SHA256:
        raise ValueError("Scope negative control did not reject an incomplete roster")
    for relative, expected in SOURCE_HASHES.items():
        if sha_file(ROOT / relative) != expected:
            raise ValueError(f"Pinned source byte mismatch: {relative}")

    # Check the frozen v5 workload against fresh-main v6 membership without repinning.
    inventory_bytes = git_bytes("data/macro-foundation/current-membership-inventory.json.gz")
    inventory = json.loads(gzip.decompress(inventory_bytes))
    lookup = {item["id"]: item for item in inventory}
    region = lookup[REGION_ID]
    if len(region["member_location_ids"]) != 1422 or not subject_set.issubset(set(region["member_location_ids"])):
        raise ValueError("Current region inventory changed or omits the exact issue subjects")
    for area_id, expected_count in AREA_IDS.items():
        if len(lookup[area_id]["member_location_ids"]) != expected_count:
            raise ValueError(f"Current area membership changed for {area_id}")
    for area in scope["area_scopes"]:
        members = set(lookup[area["id"]]["member_location_ids"])
        if len(members) != area["full_area_location_count"] or not subject_set.intersection(members):
            raise ValueError(f"Current area roster mismatch for {area['id']}")
        scoped = subject_set.intersection(members)
        if len(scoped) != area["owned_member_location_count"]:
            raise ValueError(f"Issue partial-area count changed for {area['id']}")

    # The six fixed work-item rosters are disjoint and exhaust this frozen region.
    all_batch_ids: set[str] = set()
    batch_counts = {}
    pairwise_overlaps = {}
    for number in range(427, 433):
        other = json.loads((ROOT / f"source/issue-{number}-api.json").read_bytes())
        roster = set(issue_scope(other)["member_location_ids"])
        if len(roster) != len(issue_scope(other)["member_location_ids"]):
            raise ValueError(f"Issue #{number} contains duplicate IDs")
        pairwise_overlaps[str(number)] = len(all_batch_ids & roster)
        if pairwise_overlaps[str(number)]:
            raise ValueError(f"Regional batch overlap at issue #{number}")
        all_batch_ids |= roster
        batch_counts[str(number)] = len(roster)
    if len(all_batch_ids) != 1422 or all_batch_ids != set(region["member_location_ids"]):
        raise ValueError("Issues #427–#432 do not exactly partition current region members")
    if batch_counts != {"427": 245, "428": 279, "429": 268, "430": 160, "431": 254, "432": 216}:
        raise ValueError(f"Regional issue partition changed: {batch_counts}")

    # Load current-main Atlas features for the exact issue IDs and all regional siblings.
    world_index = json.loads(git_bytes("data/world-index.json"))
    atlas_features = {}
    region_features = {}
    part_hashes = {}
    wanted_parts = []
    region_ids = set(region["member_location_ids"])
    for relative in world_index["parts"]:
        path = f"data/{relative}"
        raw = git_bytes(path)
        data = json.loads(raw)
        found = False
        for feature in data["features"]:
            props = feature["properties"]
            location_id = props["id"]
            if location_id in region_ids:
                found = True
                if location_id in region_features:
                    raise ValueError(f"Duplicate current region feature: {location_id}")
                region_features[location_id] = feature
                if location_id in subject_set:
                    atlas_features[location_id] = feature
        if found:
            wanted_parts.append(path)
            part_hashes[path] = sha_bytes(raw)
    if set(atlas_features) != subject_set:
        raise ValueError(f"Current feature omission: {len(subject_set-set(atlas_features))}")
    if set(region_features) != region_ids:
        raise ValueError(f"Current region feature omission: {len(region_ids-set(region_features))}")
    parent_counts = Counter(feature["properties"].get("parent_id") for feature in region_features.values())
    regional_source_counts = Counter()
    for feature in region_features.values():
        props = feature["properties"]
        metadata = props.get("metadata", {})
        regional_source_counts[metadata.get("source_id")] += 1
        if metadata.get("source_id") == "gb:USA:ADM2" and (not props.get("name") or any(metadata.get(k) != v for k, v in EXPECTED_METADATA.items())):
            raise ValueError(f"Neighboring US county granularity/source metadata differs for {props.get('id')}")
    if regional_source_counts["gb:USA:ADM2"] != 1421 or regional_source_counts["atlas:territory:BMU"] != 1:
        raise ValueError(f"Current region source cohort changed: {dict(regional_source_counts)}")

    # Confirm the owned 279 split exhausts the two area/state memberships.
    area_assignments = {}
    for area_id in AREA_IDS:
        members = set(lookup[area_id]["member_location_ids"])
        region_area = members & region_ids
        assigned = members & subject_set
        area_assignments[area_id] = {"current_area_count": len(members), "regional_count": len(region_area),
            "issue_subjects": len(assigned), "issue_has_exact_current_subset": assigned.issubset(members)}
    expected_parent_counts = {
        "framework:province:kentucky:cf2dcafc8b1a": 120,
        "framework:province:georgia:99c5fb82481b": 159,
    }
    scoped_parent_counts = Counter(atlas_features[s]["properties"].get("parent_id") for s in subject_set)
    if dict(scoped_parent_counts) != expected_parent_counts:
        raise ValueError(f"Current state parent roster differs: {dict(scoped_parent_counts)}")

    raw_geo = json.loads((ROOT / "source/geoBoundaries-USA-ADM2.geojson").read_bytes())
    raw_meta = json.loads((ROOT / "source/geoBoundaries-USA-ADM2-metaData.json").read_bytes())
    lfs_pointer = (ROOT / "source/geoBoundaries-USA-ADM2.geojson.lfs-pointer").read_text()
    lfs_oid = lfs_pointer.split("oid sha256:", 1)[1].splitlines()[0]
    if lfs_oid != SOURCE_HASHES["source/geoBoundaries-USA-ADM2.geojson"]:
        raise ValueError("GeoBoundaries restored bytes do not match its retained LFS pointer")
    source_ids = [f["properties"].get("shapeID") for f in raw_geo["features"]]
    if len(raw_geo["features"]) != 3233 or len(set(source_ids)) != 3233 or any(not value for value in source_ids):
        raise ValueError("GeoBoundaries USA ADM2 completeness/count/unique shapeID check failed")
    if int(raw_meta["admUnitCount"]) != 3233 or any(f["properties"].get("shapeGroup") != "USA" or f["properties"].get("shapeType") != "ADM2" for f in raw_geo["features"]):
        raise ValueError("GeoBoundaries metadata count/type does not match the retained national source")
    source_features = {f["properties"]["shapeID"]: f for f in raw_geo["features"]}
    source_by_subject = {}
    for subject in subjects:
        source_id = subject.rsplit(":", 1)[1]
        source_by_subject[subject] = required_source_feature(source_id, source_features)
    if required_source_feature(source_by_subject[subjects[0]]["properties"]["shapeID"], source_features) != source_by_subject[subjects[0]]:
        raise ValueError("GeoBoundaries source positive control failed")
    try:
        required_source_feature("WORLDATLAS-NONEXISTENT-SOURCE-ID", source_features)
    except ValueError:
        source_lookup_negative_control = "passed"
    else:
        source_lookup_negative_control = "failed"
    if source_lookup_negative_control != "passed":
        raise ValueError("GeoBoundaries source lookup negative control failed")

    c18 = json.loads((ROOT / "source/census-2018/georgia-kentucky-counties.geojson").read_bytes())
    c25 = json.loads((ROOT / "source/census-2025/georgia-kentucky-counties.geojson").read_bytes())
    if len(c18["features"]) != 279 or len(c25["features"]) != 279:
        raise ValueError("Census reference feature counts changed from 279")
    c18_by_geoid = {f["properties"]["GEOID"]: f for f in c18["features"]}
    c25_by_geoid = {f["properties"]["GEOID"]: f for f in c25["features"]}
    if len(c18_by_geoid) != 279 or len(c25_by_geoid) != 279 or set(c18_by_geoid) != set(c25_by_geoid):
        raise ValueError("Census 2018/2025 county GEOID rosters are not one-to-one")
    c18_by_name = defaultdict(list)
    for feature in c18["features"]:
        p = feature["properties"]
        c18_by_name[(p["STATE"], p["BASENAME"].casefold())].append(feature)

    # 2018 CBF is an explicitly generalized cartographic comparator, not a legal source.
    cbf_rows = {}
    with zipfile.ZipFile(ROOT / "source/census-2018/cb_2018_us_county_500k.zip") as archive:
        shp = next(name for name in archive.namelist() if name.endswith(".shp"))
        dbf = next(name for name in archive.namelist() if name.endswith(".dbf"))
        shx = next(name for name in archive.namelist() if name.endswith(".shx"))
        reader = shapefile.Reader(shp=archive.open(shp), dbf=archive.open(dbf), shx=archive.open(shx))
        fields = [field[0] for field in reader.fields[1:]]
        for row in reader.iterShapeRecords():
            props = dict(zip(fields, row.record))
            if props["STATEFP"] in {"13", "21"}:
                cbf_rows[props["GEOID"]] = (shape(row.shape.__geo_interface__), props)
    if len(cbf_rows) != 279:
        raise ValueError(f"2018 CBF state roster is not exactly 279: {len(cbf_rows)}")

    # Reproducibility controls detect axis-order mistakes and false-positive scoring.
    positive = shape(box(0, 0, 1, 1).__geo_interface__)
    negative = shape(box(3, 0, 4, 1).__geo_interface__)
    if iou(projected(positive), projected(positive)) != 1.0 or iou(projected(positive), projected(negative)) != 0.0:
        raise ValueError("Geometry positive/negative controls failed")
    xy = PROJECTION.transform(10, 45)
    swapped = PROJECTION.transform(45, 10)
    helper_xy = transform_point(10, 45, "EPSG:3857")
    helper_swapped = transform_point(45, 10, "EPSG:3857")
    helper_positive = land_area_m2(shape(box(0, 0, 1, 1).__geo_interface__))
    try:
        land_area_m2(shape({"type": "Point", "coordinates": [0, 0]}))
    except ValueError:
        helper_negative = True
    else:
        helper_negative = False
    if abs(xy[0] - swapped[0]) < 1_000_000 or abs(xy[1] - swapped[1]) < 1_000_000:
        raise ValueError("Longitude/latitude negative axis-order control failed")
    if abs(helper_xy[0] - helper_swapped[0]) < 1_000_000 or abs(helper_xy[1] - helper_swapped[1]) < 1_000_000 or helper_positive <= 0 or not helper_negative:
        raise ValueError("Shared geometry helper positive/negative controls failed")

    metric_names = ["geoboundaries_to_atlas_v6", "geoboundaries_to_census_2018_tiger", "atlas_v6_to_census_2018_tiger",
        "atlas_v6_to_census_2025_tiger", "census_2018_to_census_2025_tiger", "geoboundaries_to_census_2018_cbf",
        "atlas_v6_to_census_2018_cbf"]
    metrics = {name: [] for name in metric_names}
    rows = []
    county_status = Counter()
    for subject in sorted(subject_set):
        src = source_by_subject[subject]
        sp = src["properties"]
        atlas = atlas_features[subject]
        ap = atlas["properties"]
        parent = ap.get("parent_id")
        state = "13" if parent == "framework:province:georgia:99c5fb82481b" else "21"
        name = sp["shapeName"]
        candidates = c18_by_name.get((state, name.casefold()), [])
        if len(candidates) != 1:
            raise ValueError(f"Census 2018 name/state join is not unique for {subject}: {name}")
        f18 = candidates[0]
        cp18 = f18["properties"]
        geoid = cp18["GEOID"]
        f25 = c25_by_geoid.get(geoid)
        if f25 is None:
            raise ValueError(f"Census 2018 GEOID absent from 2025 for {subject}: {geoid}")
        fcbf = cbf_rows.get(geoid)
        if fcbf is None:
            raise ValueError(f"2018 CBF GEOID missing: {geoid}")
        cbf_geom, cbf_props = fcbf
        geoms = {"geoboundaries": shape(src["geometry"]), "atlas_v6": shape(atlas["geometry"]),
            "census_2018_tiger": shape(f18["geometry"]), "census_2025_tiger": shape(f25["geometry"]), "census_2018_cbf": cbf_geom}
        validity = {name: {"valid": geom.is_valid, "reason": explain_validity(geom)} for name, geom in geoms.items()}
        # Census TIGER responses contain three repeatable self-intersecting county
        # rings in Georgia. Keep originals/hashes; make_valid is used only to allow
        # reproducible area triage, and every such row remains insufficient-evidence.
        comparison_geoms = {name: (geom if geom.is_valid else make_valid(geom)) for name, geom in geoms.items()}
        projected_geoms = {name: projected(geom) for name, geom in comparison_geoms.items()}
        comparisons = {
            "geoboundaries_to_atlas_v6": iou(projected_geoms["geoboundaries"], projected_geoms["atlas_v6"]),
            "geoboundaries_to_census_2018_tiger": iou(projected_geoms["geoboundaries"], projected_geoms["census_2018_tiger"]),
            "atlas_v6_to_census_2018_tiger": iou(projected_geoms["atlas_v6"], projected_geoms["census_2018_tiger"]),
            "atlas_v6_to_census_2025_tiger": iou(projected_geoms["atlas_v6"], projected_geoms["census_2025_tiger"]),
            "census_2018_to_census_2025_tiger": iou(projected_geoms["census_2018_tiger"], projected_geoms["census_2025_tiger"]),
            "geoboundaries_to_census_2018_cbf": iou(projected_geoms["geoboundaries"], projected_geoms["census_2018_cbf"]),
            "atlas_v6_to_census_2018_cbf": iou(projected_geoms["atlas_v6"], projected_geoms["census_2018_cbf"]),
        }
        for metric, value in comparisons.items():
            metrics[metric].append(value)
        flags = sorted(metric for metric, value in comparisons.items() if value < 0.98)
        invalid_geometries = sorted(name for name, item in validity.items() if not item["valid"])
        flags.extend(f"invalid_geometry:{name}" for name in invalid_geometries)
        component_diff = components(geoms["geoboundaries"]) != components(geoms["atlas_v6"])
        p25 = f25["properties"]
        if ap.get("name", "").casefold() != name.casefold() or ap.get("metadata", {}).get("original_id") != sp["shapeID"]:
            raise ValueError(f"Atlas/source name or stable source identity mismatch for {subject}")
        if cp18["STATE"] != state or p25["STATE"] != state or p25["GEOID"] != geoid:
            raise ValueError(f"Census state or 2018/2025 GEOID mismatch for {subject}")
        md = ap.get("metadata", {})
        if any(md.get(k) != v for k, v in EXPECTED_METADATA.items()):
            raise ValueError(f"Atlas administrative metadata mismatch for {subject}")
        status = "insufficient-evidence" if flags or component_diff else "justified"
        county_status[f"2018:{cp18['FUNCSTAT']}"] += 1
        county_status[f"2025:{p25['FUNCSTAT']}"] += 1
        rows.append({
            "subject_id": subject, "name": name, "state_fips": state, "census_geoid_2018": geoid,
            "census_geoid_2025": p25["GEOID"], "census_county_name_2018": cp18["NAME"],
            "census_county_name_2025": p25["NAME"], "parent_id": parent,
            "source_shape_id": sp["shapeID"], "source_shape_type": sp.get("shapeType"),
            "source_vintage": sp.get("shapeYear"), "atlas_source_role": md.get("source_role"),
            "atlas_reference_year": md.get("reference_year"), "atlas_license": md.get("license"),
            "census_2018_function_status": cp18["FUNCSTAT"], "census_2025_function_status": p25["FUNCSTAT"],
            "census_2018_land_area_m2": int(cp18["AREALAND"]), "census_2018_water_area_m2": int(cp18["AREAWATER"]),
            "census_2018_cbf_name": cbf_props["NAME"], "census_2018_cbf_land_area_m2": int(cbf_props["ALAND"]),
            "geometry_type": {key: value.geom_type for key, value in geoms.items()},
            "geometry_validity": validity,
            "make_valid_comparison_types": {key: comparison_geoms[key].geom_type for key in invalid_geometries},
            "component_count": {key: components(value) for key, value in geoms.items()},
            "equal_area_iou": {key: round(value, 9) for key, value in comparisons.items()},
            "screening_flags": flags, "source_atlas_component_difference": component_diff,
            "classification": status,
            "classification_basis": ("Unexplained equal-area overlap screen below 0.98, invalid reference geometry repaired only in-memory for triage, or source/Atlas component-count difference; no boundary error established."
                if status == "insufficient-evidence" else "Exact source identity and state parent; unique 2018/2025 Census county join; no stated geometry screen triggered. This does not establish legal boundary or island completeness."),
            "unresolved_limits": ["Census/TIGER and Census CBF are statistical/cartographic references, not legal adjudication.",
                "The repository source-catalog SHA-256 basis differs from the restored upstream LFS GeoJSON SHA; shared source lineage is unresolved and no catalog edit is proposed."]
        })
    if len(rows) != 279 or len({row["subject_id"] for row in rows}) != 279:
        raise ValueError("Assessment output does not contain exactly 279 unique rows")
    if len({row["census_geoid_2018"] for row in rows}) != 279 or len({row["census_geoid_2025"] for row in rows}) != 279:
        raise ValueError("Census crosswalk is not one-to-one")

    county_names_nonempty = sum(bool(row["name"].strip()) and bool(row["census_county_name_2018"].strip()) for row in rows)
    shape_type_counts = Counter(row["source_shape_type"] for row in rows)
    atlas_component_differences = [row["subject_id"] for row in rows if row["source_atlas_component_difference"]]
    state_land = defaultdict(int)
    for row in rows:
        state_land[row["state_fips"]] += row["census_2018_land_area_m2"]
    largest_county_by_state = {}
    for state_code in sorted(state_land):
        largest = max((row for row in rows if row["state_fips"] == state_code), key=lambda row: row["census_2018_land_area_m2"])
        largest_county_by_state[state_code] = {
            "subject_id": largest["subject_id"], "name": largest["name"],
            "county_land_area_m2": largest["census_2018_land_area_m2"],
            "state_county_land_sum_m2": state_land[state_code],
            "share_of_scoped_state_county_land": round(largest["census_2018_land_area_m2"] / state_land[state_code], 9),
        }
    baseline_manifest = {}
    for path in ["data/world-index.json", "data/hierarchy.json", "data/geographic-releases/current-manifest.json",
        "data/macro-foundation/current-membership-inventory.json.gz", "data/macro-foundation/review-index.json", "data/administrative-sources.json", *sorted(part_hashes)]:
        baseline_manifest[path] = {"bytes": len(git_bytes(path)), "sha256": sha_bytes(git_bytes(path))}
    source_record = json.loads(git_bytes("data/administrative-sources.json"))["gb:USA:ADM2"]
    review_index = json.loads(git_bytes("data/macro-foundation/review-index.json"))
    if review_index.get("regional_interiors_approved") is not False:
        raise ValueError("Current macro review index no longer reports unapproved interiors")
    summary = {
        "version": 1, "issue": ISSUE, "baseline_commit": BASELINE, "scope_release_pin": scope["release"],
        "national_source_feature_count": len(source_features), "national_source_unique_shape_ids": len(set(source_ids)),
        "issue_roster_sha256": ISSUE_ROSTER_SHA256, "subjects": len(rows),
        "unit_identity_semantics_screen": {
            "nonempty_atlas_and_2018_census_names": county_names_nonempty,
            "source_shape_type_counts": dict(sorted(shape_type_counts.items())),
            "source_role": "Counties",
            "all_279_use_adm2_source_role_and_census_county_parent": county_names_nonempty == 279 and shape_type_counts == {"ADM2": 279},
            "source_atlas_component_count_difference_ids": sorted(atlas_component_differences),
            "largest_county_area_screen_by_state": largest_county_by_state,
            "area_screen_limit": "Census 2018 land areas are within-state scale triage only; not boundary or completeness evidence.",
        },
        "classification_counts": dict(Counter(row["classification"] for row in rows)),
        "census_function_status_counts": dict(sorted(county_status.items())),
        "invalid_geometry_source_observation_count": sum(not item["valid"] for row in rows for item in row["geometry_validity"].values()),
        "invalid_geometry_subject_count": sum(any(flag.startswith("invalid_geometry:") for flag in row["screening_flags"]) for row in rows),
        "invalid_geometry_subjects": [{"subject_id": row["subject_id"], "invalid_sources": row["screening_flags"]} for row in rows if any(flag.startswith("invalid_geometry:") for flag in row["screening_flags"])],
        "state_parent_counts": dict(sorted(scoped_parent_counts.items())),
        "current_southeastern_region_count": len(region_ids), "current_southeastern_region_issue_partition": batch_counts,
        "current_southeastern_region_source_cohorts": dict(sorted(regional_source_counts.items())),
        "current_southeastern_region_partition_exact": True,
        "partial_area_memberships": area_assignments,
        "current_full_division_granularity_counts": {key: AREA_IDS[key] for key in AREA_IDS},
        "metrics": {name: {"count": len(values), "minimum": round(min(values), 9),
            "median": round(float(np.median(values)), 9), "mean": round(float(np.mean(values)), 9),
            "maximum": round(max(values), 9), "below_0_98_triage_count": sum(v < 0.98 for v in values)} for name, values in metrics.items()},
        "screening_threshold_note": "0.98 is a triage threshold only; it proves neither correctness nor a boundary error.",
        "source_catalog_hash": source_record.get("sha256"), "restored_upstream_lfs_sha256": lfs_oid,
        "source_catalog_hash_basis_resolved": source_record.get("sha256") == lfs_oid,
        "baseline_files": baseline_manifest, "subject_parts": sorted(wanted_parts),
        "geoboundaries_metadata": raw_meta, "census_2018_layer_description": json.loads((ROOT/"source/census-2018/counties-layer-metadata.json").read_bytes()).get("description"),
        "census_2025_layer_description": json.loads((ROOT/"source/census-2025/counties-layer-metadata.json").read_bytes()).get("description"),
        "census_2018_retrieval_sha256": sha_file(ROOT/"source/census-2018/retrieval.json"),
        "census_2025_retrieval_sha256": sha_file(ROOT/"source/census-2025/retrieval.json"),
        "method": {"helper_version": SHARED_GEOMETRY_VERSION, "helper_policy": SHARED_GEOMETRY_METHOD,
            "projection": "EPSG:6933", "axis_order": "longitude-latitude via always_xy=True", "threshold": 0.98,
            "comparison": "planar equal-area intersection / union; shared helper is used for longitude-first transform and positive/negative geometry controls",
            "census_cbf": "2018 1:500,000 generalized cartographic file; comparator only"},
    }
    checks = {
        "issue": ISSUE, "baseline_commit": BASELINE, "scope_ids_exact": len(subject_set) == 279,
        "scope_hash_matches_issue": sha_bytes("\n".join(subjects).encode()) == ISSUE_ROSTER_SHA256,
        "scope_incomplete_roster_negative_control": "passed",
        "source_exact_lookup_positive_control": "passed", "source_missing_lookup_negative_control": source_lookup_negative_control,
        "source_national_feature_count": len(source_features), "source_metadata_adm_unit_count": int(raw_meta["admUnitCount"]),
        "source_shape_ids_all_unique": len(source_ids) == len(set(source_ids)),
        "nonempty_atlas_and_2018_census_names": county_names_nonempty,
        "source_shape_type_counts": dict(sorted(shape_type_counts.items())),
        "source_atlas_component_count_difference_count": len(atlas_component_differences),
        "largest_county_area_screen_by_state": largest_county_by_state, "census_2018_roster": len(c18_by_geoid), "census_2025_roster": len(c25_by_geoid),
        "county_features_exact": len(atlas_features), "region_features_exact": len(region_features),
        "region_source_cohorts": dict(sorted(regional_source_counts.items())),
        "region_issue_partition_exact": len(all_batch_ids) == 1422 and all_batch_ids == region_ids,
        "batch_pairwise_overlap_counts": pairwise_overlaps, "batch_counts": batch_counts,
        "state_parent_counts": dict(sorted(scoped_parent_counts.items())), "source_catalog_discrepancy_unresolved": source_record.get("sha256") != lfs_oid,
        "regional_interiors_approved": review_index.get("regional_interiors_approved"),
        "geometry_positive_negative_controls": "passed", "axis_order_negative_control": "passed",
        "shared_geometry_helper_version": SHARED_GEOMETRY_VERSION, "shared_geometry_helper_method": SHARED_GEOMETRY_METHOD,
        "shared_helper_positive_negative_controls": "passed",
    }
    (output / "county-assessments.json").write_bytes(canonical(rows))
    (output / "comparison-summary.json").write_bytes(canonical(summary))
    (output / "scope-and-control-checks.json").write_bytes(canonical(checks))
    print(json.dumps({"output": str(output.relative_to(ROOT)), "rows": len(rows),
        "classifications": summary["classification_counts"], "state_parent_counts": dict(scoped_parent_counts),
        "region_partition_exact": True, "metrics": summary["metrics"]}, sort_keys=True))


if __name__ == "__main__":
    main()
