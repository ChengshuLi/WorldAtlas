#!/usr/bin/env python3
"""Compare scoped Atlas fragments with source-Moughataa × RESOLVE intersections.

RESOLVE's raw global polygons contain invalid nested shells. make_valid is used
only on diagnostic clones; source bytes are never modified. Results are
diagnostic because repair behavior and Atlas edge adjustments require review.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from shapely import make_valid
from shapely.geometry import shape
from shapely.ops import unary_union

sys.path.insert(0, "scripts")
sys.path.insert(0, "scripts/evidence")
from geometry import METHOD, land_area_m2  # noqa: E402

PACKET = Path("data/regional-review/regional-review-f834434be524dfdb")
EXPECTED = {
    "mrt_adm2": "29caf92b290e3281d43c3a6497893ebfcebede733694d49cebb6d12ea4ff256b",
    "resolve": "63d8aa93b237b9abe8a2e3ca8b52c85cc32d993ee962e3a8503e9a619a462979",
}


def load(path, digest, key):
    raw = Path(path).read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != digest:
        raise SystemExit(f"{key} source SHA256 mismatch: {actual}")
    return json.loads(raw)


def baseline_json(path, commit):
    return json.loads(subprocess.check_output(["git", "show", f"{commit}:{path}"]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mrt-adm2", default=str(PACKET / "sources/geoboundaries/geoBoundaries-MRT-ADM2.geojson"))
    parser.add_argument("--resolve", default=str(PACKET / "sources/resolve/features-2017-ids.json"))
    parser.add_argument("--output", default=str(PACKET / "mauritania-fragment-reproduction.json"))
    args = parser.parse_args()
    adm2 = load(args.mrt_adm2, EXPECTED["mrt_adm2"], "MRT ADM2")["features"]
    raw_ecos = load(args.resolve, EXPECTED["resolve"], "RESOLVE 2017")["features"]
    scope = json.loads((PACKET / "issue-scope.json").read_text())
    wanted = {item for item in scope["member_location_ids"] if item.startswith("atlas:physical:")}
    atlas = {}
    baseline = json.loads((PACKET / "baseline-inputs.json").read_text())
    commit = "0c6232db2b2f9531a479f0c752f66c4d12013f3b"
    if baseline["baseline_commit"] != commit:
        raise SystemExit("Unexpected baseline commit")
    for entry in baseline["files"]:
        if entry["path"].startswith("data/geography/") and entry["path"].endswith(".json"):
            for feature in baseline_json(entry["path"], commit).get("features", []):
                identity = feature["properties"].get("id")
                if identity in wanted:
                    atlas[identity] = feature
    if set(atlas) != wanted:
        raise SystemExit("Scoped Atlas fragment roster is incomplete")

    source_by_id = {feature["properties"]["shapeID"]: shape(feature["geometry"]) for feature in adm2}
    eco_by_id = {int(feature["properties"]["ECO_ID"]): shape(feature["geometry"]) for feature in raw_ecos}
    invalid_raw = sorted(key for key, geometry in eco_by_id.items() if not geometry.is_valid)
    eco_diagnostic = {key: make_valid(geometry) for key, geometry in eco_by_id.items()}
    groups = {}
    for identity, feature in atlas.items():
        metadata = feature["properties"]["metadata"]
        key = (metadata["original_id"], int(metadata["source_id"].split(":")[1]))
        groups.setdefault(key, []).append((identity, shape(feature["geometry"])))

    rows = []
    for (source_id, eco_id), pieces in sorted(groups.items()):
        if source_id not in source_by_id or eco_id not in eco_diagnostic:
            raise SystemExit(f"Missing source geometry for {(source_id, eco_id)}")
        expected = source_by_id[source_id].intersection(eco_diagnostic[eco_id])
        actual = unary_union([geometry for _, geometry in pieces])
        difference = actual.symmetric_difference(expected)
        expected_area = land_area_m2(expected)
        rows.append({
            "moughataa_source_id": source_id,
            "ecoregion_id": eco_id,
            "atlas_ids": sorted(identity for identity, _ in pieces),
            "expected_area_m2": expected_area,
            "actual_area_m2": land_area_m2(actual),
            "symmetric_difference_m2": land_area_m2(difference),
            "symmetric_difference_fraction_of_expected": land_area_m2(difference) / expected_area,
            "actual_coverage_of_expected": land_area_m2(actual.intersection(expected)) / expected_area,
            "valid": actual.is_valid and expected.is_valid,
        })

    positive = next((row for row in rows if row["actual_coverage_of_expected"] > .95), None)
    negative = source_by_id["47542326B42701553126465"].intersection(eco_diagnostic[845])
    if positive is None or not negative.is_empty:
        raise SystemExit("Positive or negative spatial control failed")
    output = {
        "version": 1,
        "method": METHOD,
        "method_details": "WGS84 ellipsoidal area and intersections through evidence.geometry.land_area_m2. Expected = retained 2020 Moughataa × exact RESOLVE ECO_ID. Shapely make_valid is applied only to diagnostic clones of unchanged global RESOLVE polygons because raw files contain nested shells; this repair can alter interpretation. Results do not imply that an ecological fragment is an administrative unit or certify source completeness.",
        "software": {"shapely": __import__("shapely").__version__, "pyproj": __import__("pyproj").__version__},
        "raw_invalid_resolve_eco_ids": invalid_raw,
        "positive_control": positive["atlas_ids"][0],
        "negative_control": "Tichitt source Moughataa × West Sahara desert expected intersection is empty",
        "rows": rows,
    }
    Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"fragment_groups": len(rows), "raw_invalid_ecoregions": invalid_raw,
                      "positive_control_passed": True, "negative_control_passed": True,
                      "limits": "diagnostic geometry repair and overlap comparison; not geographic approval"}, indent=2))


if __name__ == "__main__":
    main()
