#!/usr/bin/env python3
"""Reproduce 2020 MRT ADM2 vs 2015 ADM1 candidate-parent overlaps."""
import json
from pathlib import Path
import subprocess
import sys
from shapely.geometry import shape

sys.path.insert(0, "scripts")
sys.path.insert(0, "scripts/evidence")
from geometry import METHOD, land_area_m2  # noqa: E402

PACKET = Path("data/regional-review/regional-review-f834434be524dfdb")


def baseline_json(path):
    return json.loads(subprocess.check_output([
        "git", "show", f"0c6232db2b2f9531a479f0c752f66c4d12013f3b:{path}"
    ]))


def main():
    scope = json.loads((PACKET / "issue-scope.json").read_text())
    wanted = {value for value in scope["member_location_ids"] if value.startswith("gb:MRT:ADM2:")}
    baseline = json.loads((PACKET / "baseline-inputs.json").read_text())
    if baseline["baseline_commit"] != "0c6232db2b2f9531a479f0c752f66c4d12013f3b":
        raise SystemExit("Unexpected baseline commit")
    atlas = {}
    for descriptor in baseline["files"]:
        if descriptor["path"].startswith("data/geography/") and descriptor["path"].endswith(".json"):
            for feature in baseline_json(descriptor["path"]).get("features", []):
                properties = feature["properties"]
                if properties.get("id") in wanted:
                    atlas[properties["id"]] = properties
    adm2_path = PACKET / "sources/geoboundaries/geoBoundaries-MRT-ADM2.geojson"
    adm1_path = PACKET / "sources/geoboundaries/geoBoundaries-MRT-ADM1.geojson"
    adm2 = json.loads(adm2_path.read_text())["features"]
    adm1 = json.loads(adm1_path.read_text())["features"]
    raw_adm2 = {feature["properties"]["shapeID"]: shape(feature["geometry"]) for feature in adm2}
    raw_adm1 = {feature["properties"]["shapeID"]: shape(feature["geometry"]) for feature in adm1}
    parents = [(feature["properties"]["shapeName"], feature["properties"]["shapeID"],
                shape(feature["geometry"])) for feature in adm1]
    rows = []
    for feature in adm2:
        props = feature["properties"]
        identity = "gb:MRT:ADM2:" + props["shapeID"]
        if identity not in wanted:
            continue
        polygon = shape(feature["geometry"])
        area = land_area_m2(polygon)
        overlaps = []
        for name, shape_id, parent in parents:
            intersection = polygon.intersection(parent)
            if not intersection.is_empty:
                part = land_area_m2(intersection)
                overlaps.append((part / area, part / land_area_m2(parent), name, shape_id))
        overlaps.sort(reverse=True)
        rows.append({"id": identity, "name": props["shapeName"],
                     "atlas_parent_id": atlas[identity]["parent_id"],
                     "candidate_parents": [
                         {"name": name, "shapeID": shape_id,
                          "subject_area_fraction": round(subject_fraction, 8),
                          "parent_area_fraction": round(parent_fraction, 8)}
                         for subject_fraction, parent_fraction, name, shape_id in overlaps[:3]],
                     "atlas_parent_matches_top_name": bool(overlaps and
                         atlas[identity]["parent_id"].split(":")[2].replace("-", " ").lower()
                         in overlaps[0][2].lower())})
    if len(rows) != len(wanted) or len({row["id"] for row in rows}) != len(rows):
        raise SystemExit("Scoped Mauritania unit roster incomplete/duplicated")
    positive = next((row for row in rows if row["candidate_parents"] and
                     row["candidate_parents"][0]["subject_area_fraction"] > .95), None)
    negative_geometry = raw_adm2["47542326B14226246765401"].intersection(raw_adm1["64602211B19416274064143"])
    if positive is None or not negative_geometry.is_empty:
        raise SystemExit("Positive/negative source-parent control failed")
    result = {"version": 1, "baseline_commit": baseline["baseline_commit"],
              "method": METHOD,
              "method_details": "WGS84 ellipsoidal area intersections via shared WorldAtlas evidence.geometry.land_area_m2; compare each 2020 ADM2 subject with every 2015 ADM1 candidate. Overlap does not establish legal parentage or current completeness.",
              "positive_control": positive["id"],
              "negative_control": "F'Derick × distant Adrar parent candidate is empty",
              "software": {"shapely": __import__("shapely").__version__,
                           "pyproj": __import__("pyproj").__version__},
              "rows": sorted(rows, key=lambda row: row["id"])}
    (PACKET / "mauritania-parent-overlap.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"scoped_subjects": len(rows),
                      "overlap_at_least_95_percent": sum(row["candidate_parents"][0]["subject_area_fraction"] >= .95 for row in rows),
                      "atlas_parent_name_matches": sum(row["atlas_parent_matches_top_name"] for row in rows),
                      "positive_control": positive["id"],
                      "limits": "2015/2020 source geometry overlap is diagnostic, not legal parent evidence"}, indent=2))


if __name__ == "__main__":
    main()
