#!/usr/bin/env python3
"""Bounded native-validity and legacy-score reproduction for issue #1148.

Run from the repository root with Python 3.12, Shapely 2.1.2 and pyproj
3.7.2. Reads only the two state responses, two Atlas parts, the retained
2018 GeoBoundaries product, and 2018 county cartographic controls. Writes
one result file under this issue's owned directory. It never repairs input.
"""
import csv
import hashlib
import io
import json
import pathlib
import subprocess
import sys
import zipfile

import pyproj
import shapely
from pyproj import Transformer
from shapely.geometry import Polygon, shape
from shapely.ops import transform
from shapely.validation import explain_validity

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "scripts"))
from evidence.geometry import canonical_land, VERSION as GEOMETRY_HELPER_VERSION

ROOT = pathlib.Path.cwd()
OWNED = ROOT / "data/regional-review/southeastern-comparator-validity-427"
ORIGINAL = ROOT / "data/regional-review/regional-review-599d6fe712bbbcae"
SUBJECTS = {
    "01095": "gb:USA:ADM2:52423323B91350179619182",
    "47145": "gb:USA:ADM2:52423323B98361785836731",
}
STATES = {"01095": "01", "47145": "47"}
EXPECTED_STATE_FEATURES = {"01": 67, "47": 95}
EXPECTED = {
    "data/geography/part-26.json": "44de5da3531f5641e0496ab7b01ed73871b40705e2a3eafdda470926872b6632",
    "data/geography/part-27.json": "e8df7555853e9262162c5e5d5c85e5c30be3fa8f0e6339bafec0e08323054758",
    "data/hierarchy.json": "568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b",
    "data/regional-review/regional-review-599d6fe712bbbcae/sources/census-tigerweb-acs26/counties-state-01.geojson": "386d08c97bfae31678cf70609ba277a4bbc271f4e79d5f651537cf64cac00084",
    "data/regional-review/regional-review-599d6fe712bbbcae/sources/census-tigerweb-acs26/counties-state-47.geojson": "b9b10ee31927e67c295180c885e8e616940d099a52879df2c5a49bad123f6a15",
    "data/regional-review/regional-review-599d6fe712bbbcae/sources/geoboundaries-2018/geoBoundaries-USA-ADM2.geojson": "81fdd384df8012e5007ed2994a8ab306352f3c48e32cd8ea99182195e8647f43",
    "data/regional-review/regional-review-599d6fe712bbbcae/sources/census-2018-cartographic-boundaries/cb_2018_us_county_500k.zip": "aaa866af327754e1b80aa87bfb97b04a7209f4f871075aef84affb8f0b3afe67",
    "data/regional-review/regional-review-599d6fe712bbbcae/findings/usa-county-crosswalk.csv": "7990aff113168a4447b40ae72bbcccf3b0a28102a4465c87257e98ad993db98a",
    "data/regional-review/regional-review-599d6fe712bbbcae/reproduce-review.py": "50204510d6786d0708cf911f0653ea795542e30ccdefec6b907a3d14b1f1088d",
    "data/regional-review/regional-review-599d6fe712bbbcae/REVIEW.md": "3685b58e8586a0ac6b222d4500989f40d8a71c0fe675426bb08f302a88d06744",
    "data/regional-review/regional-review-599d6fe712bbbcae/sources/census-tigerweb-acs26/layer-82-metadata-20261005.json": "56df6e7d6cff8fe1e082bbdc10109cc2c7c22a134f5dfca1899f93d9bd98337d",
    "data/regional-review/regional-review-599d6fe712bbbcae/census-tigerweb-state-retrieval-receipts.json": "efb6dbe4859e5d36595403b418afb0ebc7e50f0289fffec22c8a5e7f75721f0a",
    "data/regional-review/regional-review-599d6fe712bbbcae/sources/geoboundaries-2018/upstream-metaData.json": "a4d2a82a1cd434960b6ed49531bff3330d0881674eea9dc8711e1ad6bf049b9f",
    "data/regional-review/regional-review-599d6fe712bbbcae/sources/geoboundaries-2018/CITATION-AND-USE-geoBoundaries.txt": "f6ea7572bea6036c4cdcacf8c0ca7bf09098d4e600d19546d7432533e9a290d5",
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_pins():
    actual_hashes = {}
    for rel, expected in EXPECTED.items():
        actual = sha256(ROOT / rel)
        if actual != expected:
            raise RuntimeError(f"Pinned input mismatch for {rel}: {actual}")
        actual_hashes[rel] = actual
    return actual_hashes


def iou(a, b):
    """Same EPSG:5070 intersection/union operation as the retained method."""
    forward = Transformer.from_crs("EPSG:4326", "EPSG:5070", always_xy=True).transform
    aa, bb = transform(forward, a), transform(forward, b)
    union = aa.union(bb).area
    return aa.intersection(bb).area / union if union else 0.0


def load_features(path):
    return json.loads(path.read_text())["features"]


def main():
    input_hashes = check_pins()
    baseline_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if len(baseline_commit) != 40:
        raise RuntimeError("Could not resolve exact checkout baseline commit")
    state_files = {
        "01": ORIGINAL / "sources/census-tigerweb-acs26/counties-state-01.geojson",
        "47": ORIGINAL / "sources/census-tigerweb-acs26/counties-state-47.geojson",
    }
    native = {}
    controls = {}
    for geoid, state in STATES.items():
        features = load_features(state_files[state])
        if len(features) != EXPECTED_STATE_FEATURES[state] or any(f.get("geometry") is None for f in features):
            raise RuntimeError(f"Incomplete geometry response for state {state}")
        state_geoids = [f.get("properties", {}).get("GEOID") for f in features]
        if len(set(state_geoids)) != len(state_geoids) or any(not x.startswith(state) for x in state_geoids):
            raise RuntimeError(f"Duplicate or wrong-state GEOID in response {state}")
        found = [f for f in features if f.get("properties", {}).get("GEOID") == geoid]
        if len(found) != 1:
            raise RuntimeError(f"Expected one {geoid} comparator, got {len(found)}")
        f = found[0]
        props = f["properties"]
        geom = shape(f["geometry"])
        try:
            canonical_land(geom)
        except ValueError as error:
            helper_rejection = str(error)
        else:
            helper_rejection = None
        if helper_rejection is None:
            raise RuntimeError(f"Shared geometry helper accepted invalid target {geoid}")
        native[geoid] = (f, geom, helper_rejection)
        if props.get("STATE") != state or not props.get("NAME"):
            raise RuntimeError(f"State/name parent identity mismatch for {geoid}")
        positive_geoid = "01089" if state == "01" else "47093"
        positive = [x for x in features if x.get("properties", {}).get("GEOID") == positive_geoid]
        if len(positive) != 1:
            raise RuntimeError(f"Missing same-state positive control {positive_geoid}")
        positive_geom = shape(positive[0]["geometry"])
        controls[positive_geoid] = {
            "name": positive[0]["properties"].get("NAME"),
            "same_state": positive[0]["properties"].get("STATE") == state,
            "valid": positive_geom.is_valid,
            "reason": explain_validity(positive_geom),
            "shared_helper_accepts": bool(canonical_land(positive_geom).is_valid),
        }

    part_features = {}
    for name in ("part-26.json", "part-27.json"):
        for f in json.loads((ROOT / "data/geography" / name).read_text())["features"]:
            if f.get("id") in SUBJECTS.values():
                part_features[f["id"]] = (name, f)
    if set(part_features) != set(SUBJECTS.values()):
        raise RuntimeError("Atlas containing-file loop missed or duplicated a scoped ID")
    hierarchy = {x["id"]: x for x in json.loads((ROOT / "data/hierarchy.json").read_text())}
    parent_expectations = {"01095": ("framework:province:alabama:2ea4f64966c3", "Alabama"),
                           "47145": ("framework:province:tennessee:1e9839d5c457", "Tennessee")}

    source_path = ORIGINAL / "sources/geoboundaries-2018/geoBoundaries-USA-ADM2.geojson"
    gb = {f["properties"]["shapeID"]: f for f in load_features(source_path)}
    crosswalk = {}
    control_geoids = {"01089", "47093"}
    with (ORIGINAL / "findings/usa-county-crosswalk.csv").open(newline="") as f:
        for row in csv.DictReader(f):
            if row["geoid_2018_and_2026"] in SUBJECTS or row["geoid_2018_and_2026"] in control_geoids:
                crosswalk[row["geoid_2018_and_2026"]] = row
    if not set(SUBJECTS).issubset(crosswalk) or not control_geoids.issubset(crosswalk):
        raise RuntimeError("Original crosswalk lacks a target or same-state positive control")

    out_subjects = []
    for geoid, ident in SUBJECTS.items():
        census_feature, census_geom, helper_rejection = native[geoid]
        props = census_feature["properties"]
        atlas_file, atlas_feature = part_features[ident]
        atlas_geom = shape(atlas_feature["geometry"])
        parent_id, parent_name = parent_expectations[geoid]
        parent = hierarchy.get(parent_id)
        if (atlas_feature.get("properties", {}).get("parent_id") != parent_id or not parent or
                parent.get("name") != parent_name or parent.get("level") != "province"):
            raise RuntimeError(f"Atlas parent-chain mismatch for {geoid}")
        row = crosswalk[geoid]
        gb_id = row["source_shape_id"]
        source_feature = gb.get(gb_id)
        if source_feature is None:
            raise RuntimeError(f"Missing retained 2018 comparator for {geoid}")
        source_geom = shape(source_feature["geometry"])
        score = iou(source_geom, census_geom)
        published = float(row["2026_tiger_iou"])
        # Retained table is rounded to 8 decimal places.
        if round(score, 8) != published:
            raise RuntimeError(f"Legacy #427 score changed for {geoid}: {score} vs {published}")
        out_subjects.append({
            "atlas_id": ident,
            "atlas_containing_file": atlas_file,
            "atlas_geometry_valid": atlas_geom.is_valid,
            "native_geoid": geoid,
            "native_name": props.get("NAME"),
            "native_state_fips": props.get("STATE"),
            "native_county_fips": props.get("COUNTY"),
            "native_source_geometry_type": census_geom.geom_type,
            "native_source_crs": "EPSG:4326; original response requested outSR=4326",
            "native_is_valid": census_geom.is_valid,
            "native_validity_reason": explain_validity(census_geom),
            "shared_helper_rejection": helper_rejection,
            "native_source_bounds_lon_lat": list(census_geom.bounds),
            "source_2018_feature_id": gb_id,
            "source_2018_geometry_valid": source_geom.is_valid,
            "comparator_iou_epsg5070": score,
            "retained_iou_epsg5070": published,
            "retained_above_0_95_triage_cutoff": bool(row["below_095_2026"] == "False"),
            "same_state_parent_consistency": props.get("STATE") == STATES[geoid],
            "atlas_parent_id": parent_id,
            "atlas_parent_name": parent_name,
            "atlas_parent_level": parent["level"],
            "atlas_parent_child_count": parent["metadata"].get("child_count"),
            "state_filtered_response_feature_count": EXPECTED_STATE_FEATURES[STATES[geoid]],
            "operation_note": "Unrepaired native 2018 source and unrepaired native Census comparator; EPSG:5070 transform using always_xy; intersection area / union area; run for disclosure only because Census comparator fails native validity.",
        })

    positive_score_controls = []
    for geoid in sorted(control_geoids):
        census_feature, census_geom, _ = native.get(geoid, (None, None, None))
        if census_feature is None:
            state = "01" if geoid.startswith("01") else "47"
            match = [f for f in load_features(state_files[state]) if f["properties"].get("GEOID") == geoid]
            if len(match) != 1:
                raise RuntimeError(f"Missing score positive-control Census row {geoid}")
            census_feature = match[0]
            census_geom = shape(census_feature["geometry"])
            native[geoid] = (census_feature, census_geom, None)
        source_id = crosswalk[geoid]["source_shape_id"]
        source_feature = gb.get(source_id)
        if source_feature is None:
            raise RuntimeError(f"Missing 2018 geometry for positive control {geoid}")
        source_geom = shape(source_feature["geometry"])
        score = iou(source_geom, census_geom)
        if not source_geom.is_valid or not census_geom.is_valid or not (0 < score <= 1):
            raise RuntimeError(f"Valid-input score positive control failed for {geoid}")
        positive_score_controls.append({"geoid": geoid, "same_state": census_feature["properties"]["STATE"] == geoid[:2],
                                        "both_inputs_valid": True, "legacy_iou_finite_and_in_unit_range": True})

    bowtie = Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])
    if bowtie.is_valid or "Self-intersection" not in explain_validity(bowtie):
        raise RuntimeError("Synthetic negative validity control failed")
    if any(x["native_is_valid"] for x in out_subjects):
        raise RuntimeError("A target unexpectedly passed native validity")
    if not all(x["valid"] and x["same_state"] and x["shared_helper_accepts"] for x in controls.values()):
        raise RuntimeError("Same-state positive controls failed")
    try:
        canonical_land(bowtie)
    except ValueError:
        bowtie_helper_rejected = True
    else:
        bowtie_helper_rejected = False
    if not bowtie_helper_rejected:
        raise RuntimeError("Shared geometry helper accepted synthetic invalidity control")

    results = {
        "version": 1,
        "issue": 1148,
        "retrieved_or_reproduced_on": "2026-10-06",
        "baseline_commit": baseline_commit,
        "input_sha256": input_hashes,
        "software": {"python": sys.version.split()[0], "shapely": shapely.__version__, "geos": shapely.geos_version_string, "pyproj": pyproj.__version__},
        "method": {
            "native_validity": "Construct shapely.geometry.shape from retained GeoJSON geometry; read is_valid and shapely.validation.explain_validity before any projection/overlay/repair.",
            "score_reproduction": "Transform both original 2018 geoBoundaries and 2026 TIGERweb geometries from EPSG:4326 to EPSG:5070 with pyproj Transformer(always_xy=True); Shapely intersection area divided by union area, matching #427 iou(). No geometry repair.",
            "native_axis_order": "GeoJSON longitude,latitude; the exact retained TIGERweb query requested outSR=4326.",
        },
        "subjects": out_subjects,
        "controls": {
            "positive": controls,
            "negative": {"fixture": "bow-tie polygon; coordinate list preserved in this script", "valid": bowtie.is_valid, "reason": explain_validity(bowtie), "shared_helper_rejected": bowtie_helper_rejected, "passed": (not bowtie.is_valid and "Self-intersection" in explain_validity(bowtie) and bowtie_helper_rejected)},
            "score_positive": positive_score_controls,
            "score_negative": [{"geoid": row["native_geoid"], "inputs_invalid": not row["native_is_valid"],
                                "legacy_iou_produced_historical_value": row["comparator_iou_epsg5070"] == row["retained_iou_epsg5070"],
                                "positive_boundary_interpretation_withheld": True} for row in out_subjects],
            "scope": "Two invalid requested rows and two valid same-state, same-layer GEOID controls (not selected as known-adjacent parcels); does not estimate validity for either whole state or the national layer.",
            "shared_geometry_helper": GEOMETRY_HELPER_VERSION,
        },
        "decision": "The two published 2026 IoUs and above-0.95 triage flags reproduce to the retained 8-decimal table precision. They remain arithmetic diagnostics from an operation that accepted invalid input; they are not valid-topology comparator suitability or affirmative boundary evidence. Withhold any boundary-correctness inference and comparator-acceptance use until the Census source defect is resolved or a separately sourced valid comparator is evaluated.",
        "scope_limit": "No coordinate repair, score replacement, boundary correction, county-law conclusion, regional approval, or production action.",
    }
    output = OWNED / "vintages/2026-10-06/native-validity-and-score-reproduction.json"
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    validation = output.parent / "validation"
    validation.mkdir(exist_ok=True)
    receipts = {
        "native-validity-positive-control.json": {"method_id": "native-validity", "kind": "positive-control", "outcome": "passed", "fixtures": controls},
        "native-validity-negative-control.json": {"method_id": "native-validity", "kind": "negative-control", "outcome": "passed", "fixtures": results["controls"]["negative"], "scoped_targets": [{"geoid": x["native_geoid"], "is_valid": x["native_is_valid"], "reason": x["native_validity_reason"]} for x in out_subjects]},
        "legacy-iou-positive-control.json": {"method_id": "legacy-iou", "kind": "positive-control", "outcome": "passed", "fixtures": positive_score_controls},
        "legacy-iou-negative-control.json": {"method_id": "legacy-iou", "kind": "negative-control", "outcome": "passed", "fixtures": results["controls"]["score_negative"]},
    }
    for filename, receipt in receipts.items():
        target = validation / filename
        if target.exists():
            raise FileExistsError(target)
        target.write_text(json.dumps(receipt, sort_keys=True, indent=2, ensure_ascii=False) + "\n")
    output.write_text(json.dumps(results, sort_keys=True, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"output": str(output.relative_to(ROOT)), "subjects": len(out_subjects), "controls_passed": len(receipts), "sha256": sha256(output), "validation_files": sorted(p.name for p in validation.iterdir())}, sort_keys=True))


if __name__ == "__main__":
    main()
