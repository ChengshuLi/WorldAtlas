#!/usr/bin/env python3
"""Reproduce diagnostic 2012 NER ADM3 vs 2018 ADM2 overlap fractions.

Requires the repository's pinned Python dependencies and exact source files in
a private cache (these NER geometries are intentionally not redistributed).
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from shapely.geometry import shape

sys.path.insert(0, "scripts")
sys.path.insert(0, "scripts/evidence")
from geometry import METHOD, land_area_m2  # noqa: E402

PACKET = Path("data/regional-review/regional-review-f834434be524dfdb")
EXPECTED = {
    "adm3": "9e51e9033ff65c867faa8d741a5b39522d448fa15ae75e0bf5b1da68cb7bc5fa",
    "adm2": "228f3bb7fee0259949727102b309b987c56d29f3e23c77f64d1c48fc19955dc3",
}


def read_pinned(path, key):
    raw = Path(path).read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != EXPECTED[key]:
        raise SystemExit(f"{key} source SHA256 mismatch: {actual}")
    return json.loads(raw)


def baseline_json(path, commit):
    raw = subprocess.check_output(["git", "show", f"{commit}:{path}"])
    return json.loads(raw)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--adm3", required=True, help="private-cache 2012 ADM3 GeoJSON")
    parser.add_argument("--adm2", required=True, help="private-cache 2018 ADM2 GeoJSON")
    parser.add_argument("--output", default=str(PACKET / "niger-parent-overlap.json"))
    args = parser.parse_args()

    scope = json.loads((PACKET / "issue-scope.json").read_text())
    commit = "0c6232db2b2f9531a479f0c752f66c4d12013f3b"
    ids = {value for value in scope["member_location_ids"] if value.startswith("gb:NER:ADM3:")}
    baseline = json.loads((PACKET / "baseline-inputs.json").read_text())
    if baseline["baseline_commit"] != commit:
        raise SystemExit("Unexpected baseline commit")
    props = {}
    for entry in baseline["files"]:
        if not entry["path"].startswith("data/geography/") or not entry["path"].endswith(".json"):
            continue
        collection = baseline_json(entry["path"], commit)
        for feature in collection.get("features", []):
            if feature["properties"].get("id") in ids:
                props[feature["properties"]["id"]] = feature["properties"]

    adm3 = read_pinned(args.adm3, "adm3")["features"]
    adm2 = read_pinned(args.adm2, "adm2")["features"]
    candidates = [(f["properties"]["shapeName"], f["properties"]["shapeID"], shape(f["geometry"]))
                  for f in adm2]
    rows = []
    for feature in adm3:
        native_id = feature["properties"]["shapeID"]
        identity = "gb:NER:ADM3:" + native_id
        if identity not in ids:
            continue
        polygon = shape(feature["geometry"])
        denominator = land_area_m2(polygon)
        overlaps = []
        for name, shape_id, parent in candidates:
            intersection = polygon.intersection(parent)
            if intersection.is_empty:
                continue
            overlap = land_area_m2(intersection)
            overlaps.append((overlap / denominator, overlap / land_area_m2(parent), name, shape_id))
        overlaps.sort(reverse=True)
        rows.append({
            "id": identity,
            "name": feature["properties"]["shapeName"].strip(),
            "atlas_parent_id": props[identity]["parent_id"],
            "source_parent_candidates": [
                {"name": name, "shapeID": shape_id,
                 "subject_area_fraction": round(subject_fraction, 8),
                 "parent_area_fraction": round(parent_fraction, 8)}
                for subject_fraction, parent_fraction, name, shape_id in overlaps[:3]
            ],
        })
    if len(rows) != len(ids) or len({row["id"] for row in rows}) != len(rows):
        raise SystemExit("Scoped source membership is incomplete or duplicated")
    positive = next((row for row in rows if row["source_parent_candidates"] and
                     row["source_parent_candidates"][0]["subject_area_fraction"] > .99), None)
    negative = next((row for row in rows if row["source_parent_candidates"] and
                     row["source_parent_candidates"][0]["subject_area_fraction"] < .8), None)
    if positive is None or negative is None:
        raise SystemExit("Positive or negative spatial control absent")
    thresholds = [.9999, .99, .95, .9, .8]
    counts = {str(t): sum(row["source_parent_candidates"][0]["subject_area_fraction"] >= t
                          for row in rows) for t in thresholds}
    value = {
        "version": 1,
        "baseline_commit": baseline["baseline_commit"],
        "source_sha256": EXPECTED,
        "method": METHOD,
        "software": {"shapely": __import__("shapely").__version__,
                     "pyproj": __import__("pyproj").__version__},
        "method_details": "WGS84 ellipsoidal area and intersections using evidence.geometry.land_area_m2; 2012 ADM3 polygons compared with every 2018 ADM2 source polygon. Fractions are overlap diagnostics, not proof of legal role or boundary equality.",
        "positive_control": positive["id"],
        "negative_control": negative["id"],
        "summary_scoped_subject_count": len(rows),
        "counts_by_maximum_source_parent_overlap_fraction": counts,
        "subjects": sorted(rows, key=lambda row: row["id"]),
    }
    Path(args.output).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"subjects": len(rows), "threshold_counts": counts,
                      "positive_control": positive["id"],
                      "negative_control": negative["id"],
                      "limits": "source-vintage overlap does not establish statutory parent or a correction"}, indent=2))


if __name__ == "__main__":
    main()
