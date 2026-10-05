#!/usr/bin/env python3
"""Reproduce the bounded Cameroon ADM3 candidate-source roster crosswalk.

The script uses exact normalized name/parent joins and a separately reported
geometric candidate crosswalk. Spatial scores identify possible counterparts;
they do not prove legal boundary identity.
"""
from __future__ import annotations

import csv
import hashlib
import json
import unicodedata
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from pyproj import Geod
from shapely.geometry import Polygon, shape
from shapely.strtree import STRtree
from shapely.validation import make_valid

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
PRIOR_REVIEW = REPO / "data/regional-review/regional-review-d1c8bea8b9425b8c/unit-review.csv"
GB_SOURCE = REPO / "data/regional-review/regional-review-4c8c1c55a35245d1/sources/geoBoundaries-CMR-ADM3.geojson"
OCHA_ZIP = ROOT / "source/cmr_admin_boundaries.geojson.zip"
WRI_GEOJSON = ROOT / "source/arrondissements.geojson"
OUT = ROOT / "candidate-crosswalk.json"
POSITIVE_CONTROL = ROOT / "positive-control.json"
NEGATIVE_CONTROL = ROOT / "negative-control.json"
ISSUE_IDS = json.loads((ROOT / "issue-subject-ids.json").read_text(encoding="utf-8"))
METHOD_ID = "cmr-adm3-ocha-spatial-candidate-crosswalk"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def norm(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", value or "").casefold()
    text = "".join(c for c in text if not unicodedata.combining(c))
    return "".join(c for c in text if c.isalnum())


def component_count(geometry: dict) -> int:
    kind = geometry.get("type")
    if kind == "Polygon":
        return 1
    if kind == "MultiPolygon":
        return len(geometry.get("coordinates", []))
    return 0


with PRIOR_REVIEW.open(encoding="utf-8", newline="") as stream:
    subjects = [row for row in csv.DictReader(stream) if row["country"] == "CMR"]
assert len(subjects) == 226 and len({row["location_id"] for row in subjects}) == 226
assert set(ISSUE_IDS) == {row["location_id"] for row in subjects}
with GB_SOURCE.open(encoding="utf-8") as stream:
    gb_features = json.load(stream)["features"]
gb_by_shape_id = {feature["properties"]["shapeID"]: shape(feature["geometry"]) for feature in gb_features}
assert len(gb_by_shape_id) == 360

with zipfile.ZipFile(OCHA_ZIP) as archive:
    ocha = json.loads(archive.read("cmr_admin3_em.geojson"))
    ocha_features = ocha["features"]
    source_member = "cmr_admin3_em.geojson"
    source_license = "HDX package cod-ab-cmr; CC BY-IGO 3.0"

ocha_by_name_parent: dict[tuple[str, str], list[dict]] = defaultdict(list)
for feature in ocha_features:
    props = feature["properties"]
    key = (norm(props.get("adm3_name")), norm(props.get("adm2_name")))
    ocha_by_name_parent[key].append(feature)

ocha_geometries = [shape(feature["geometry"]) for feature in ocha_features]
ocha_tree = STRtree(ocha_geometries)
geod = Geod(ellps="WGS84")


def geodesic_area(geometry) -> float:
    return abs(geod.geometry_area_perimeter(geometry)[0])


def polygon_scores(reference, candidate) -> dict[str, float]:
    if not reference.is_valid:
        reference = make_valid(reference)
    if not candidate.is_valid:
        candidate = make_valid(candidate)
    overlap_area = geodesic_area(reference.intersection(candidate))
    reference_area = geodesic_area(reference)
    candidate_area = geodesic_area(candidate)
    union_area = geodesic_area(reference.union(candidate))
    return {
        "iou": overlap_area / union_area if union_area else 0,
        "reference_coverage": overlap_area / reference_area if reference_area else 0,
        "candidate_coverage": overlap_area / candidate_area if candidate_area else 0,
    }


positive_geometry = Polygon([(10, 0), (11, 0), (11, 1), (10, 1), (10, 0)])
positive_scores = polygon_scores(positive_geometry, positive_geometry)
positive = {"method_id": METHOD_ID, "kind": "positive-control", "outcome": "passed" if positive_scores["iou"] == 1 else "failed", "expected_iou": 1, "observed_iou": positive_scores["iou"], "observed_reference_coverage": positive_scores["reference_coverage"], "observed_candidate_coverage": positive_scores["candidate_coverage"]}
negative_geometry = Polygon([(12, 0), (13, 0), (13, 1), (12, 1), (12, 0)])
negative_scores = polygon_scores(positive_geometry, negative_geometry)
negative = {"method_id": METHOD_ID, "kind": "negative-control", "outcome": "passed" if negative_scores["iou"] == 0 else "failed", "expected_iou": 0, "observed_iou": negative_scores["iou"], "observed_reference_coverage": negative_scores["reference_coverage"], "observed_candidate_coverage": negative_scores["candidate_coverage"]}
POSITIVE_CONTROL.write_text(json.dumps(positive, indent=2) + "\n", encoding="utf-8")
NEGATIVE_CONTROL.write_text(json.dumps(negative, indent=2) + "\n", encoding="utf-8")

if WRI_GEOJSON.exists():
    wri = json.loads(WRI_GEOJSON.read_text(encoding="utf-8"))
    wri_features = wri["features"]
else:
    wri_features = []
wri_by_name_parent: dict[tuple[str, str], list[dict]] = defaultdict(list)
for feature in wri_features:
    props = feature["properties"]
    key = (norm(props.get("nom_arr")), norm(props.get("nom_dep")))
    wri_by_name_parent[key].append(feature)

rows = []
for subject in subjects:
    key = (norm(subject["atlas_name"]), norm(subject["atlas_parent_name"]))
    ocha_matches = ocha_by_name_parent.get(key, [])
    wri_matches = wri_by_name_parent.get(key, [])
    ocha_match = ocha_matches[0] if len(ocha_matches) == 1 else None
    wri_match = wri_matches[0] if len(wri_matches) == 1 else None
    oprops = ocha_match["properties"] if ocha_match else {}
    wprops = wri_match["properties"] if wri_match else {}
    ogeometry = ocha_match.get("geometry", {}) if ocha_match else {}
    wgeometry = wri_match.get("geometry", {}) if wri_match else {}
    reference = gb_by_shape_id[subject["source_feature_id"]]
    if not reference.is_valid:
        reference = make_valid(reference)
    spatial_scores = []
    for candidate_index in ocha_tree.query(reference):
        candidate = ocha_geometries[int(candidate_index)]
        measures = polygon_scores(reference, candidate)
        if measures["iou"] <= 0:
            continue
        spatial_scores.append({"index": int(candidate_index), **measures})
    spatial_scores.sort(key=lambda score: (-score["iou"], score["index"]))
    assert spatial_scores
    best = spatial_scores[0]
    best_feature = ocha_features[best["index"]]
    best_props = best_feature["properties"]
    best_geometry = best_feature.get("geometry", {})
    second_iou = spatial_scores[1]["iou"] if len(spatial_scores) > 1 else 0
    rows.append({
        "subject_id": subject["location_id"],
        "gb_source_feature_id": subject["source_feature_id"],
        "atlas_name": subject["atlas_name"],
        "historical_source_name": subject["source_name"],
        "historical_source_name_differs_from_atlas_name": subject["source_name"] != subject["atlas_name"],
        "current_atlas_parent_name": subject["atlas_parent_name"],
        "historical_source_name_encoding_roundtrip": subject["source_name_latin1_utf8_roundtrip_matches_atlas"],
        "historical_source_geometry_components": int(subject["source_geometry_components"]),
        "ocha_exact_normalized_name_parent_matches": len(ocha_matches),
        "ocha_adm3_pcode": oprops.get("adm3_pcode"),
        "ocha_adm3_name": oprops.get("adm3_name"),
        "ocha_adm2_name": oprops.get("adm2_name"),
        "ocha_adm3_geometry_type": ogeometry.get("type"),
        "ocha_adm3_geometry_components": component_count(ogeometry),
        "ocha_spatial_candidate_pcode": best_props.get("adm3_pcode"),
        "ocha_spatial_candidate_adm3_name": best_props.get("adm3_name"),
        "ocha_spatial_candidate_adm2_name": best_props.get("adm2_name"),
        "ocha_spatial_candidate_geometry_type": best_geometry.get("type"),
        "ocha_spatial_candidate_geometry_components": component_count(best_geometry),
        "ocha_spatial_best_iou": round(best["iou"], 8),
        "ocha_spatial_best_reference_coverage": round(best["reference_coverage"], 8),
        "ocha_spatial_best_candidate_coverage": round(best["candidate_coverage"], 8),
        "ocha_spatial_second_iou": round(second_iou, 8),
        "ocha_spatial_runner_up_margin": round(best["iou"] - second_iou, 8),
        "inc_wri_exact_normalized_name_parent_matches": len(wri_matches),
        "inc_wri_arrondissement_name": wprops.get("nom_arr"),
        "inc_wri_department_name": wprops.get("nom_dep"),
        "inc_wri_geometry_type": wgeometry.get("type"),
        "inc_wri_geometry_components": component_count(wgeometry),
    })

ocha_codes = [feature["properties"].get("adm3_pcode") for feature in ocha_features]
ocha_parents = {feature["properties"].get("adm2_pcode") for feature in ocha_features}
matched_component_pairs = Counter(
    f"{row['historical_source_geometry_components']}->{row['ocha_spatial_candidate_geometry_components']}"
    for row in rows
)
unique_spatial_matches = sum(row["ocha_spatial_runner_up_margin"] >= 0.10 for row in rows)
strong_spatial_matches = sum(row["ocha_spatial_best_iou"] >= 0.95 for row in rows)
two_sided_spatial_matches = sum(row["ocha_spatial_best_reference_coverage"] >= 0.95 and row["ocha_spatial_best_candidate_coverage"] >= 0.95 for row in rows)
changed_spatial_geometries = [row["subject_id"] for row in rows if row["ocha_spatial_best_iou"] < 0.95]
name_encoding_differences = [row for row in rows if row["historical_source_name_differs_from_atlas_name"]]
spatial_parent_mismatches = [
    row["subject_id"] for row in rows
    if norm(row["current_atlas_parent_name"]) != norm(row["ocha_spatial_candidate_adm2_name"])
]
result = {
    "version": 1,
    "method": "exact normalized name and current-parent joins plus geodesic intersection-over-union candidate matching against all OCHA COD-AB ADM3 polygons; geometry match is not legal identity proof",
    "scope_count": len(rows),
    "issue_subject_ids_path": "issue-subject-ids.json",
    "scope_ids_sha256": hashlib.sha256(json.dumps(sorted(row["subject_id"] for row in rows), separators=(",", ":")).encode()).hexdigest(),
    "prior_review_input": {"path_from_repository": "data/regional-review/regional-review-d1c8bea8b9425b8c/unit-review.csv", "sha256": sha256(PRIOR_REVIEW)},
    "historical_geometry_input": {"path_from_repository": "data/regional-review/regional-review-4c8c1c55a35245d1/sources/geoBoundaries-CMR-ADM3.geojson", "sha256": sha256(GB_SOURCE), "vintage": 2017},
    "ocha_source": {"path": "source/cmr_admin_boundaries.geojson.zip", "sha256": sha256(OCHA_ZIP), "member": source_member, "license": source_license},
    "inc_wri_source": {"path": "source/arrondissements.geojson", "sha256": sha256(WRI_GEOJSON) if WRI_GEOJSON.exists() else None},
    "ocha_roster": {"feature_count": len(ocha_features), "unique_pcode_count": len(set(ocha_codes)), "missing_pcode_count": sum(code is None for code in ocha_codes), "unique_parent_pcode_count": len(ocha_parents), "scope_unique_name_parent_match_count": sum(row["ocha_exact_normalized_name_parent_matches"] == 1 for row in rows), "historical_to_spatial_candidate_geometry_component_pairs_all_subjects": dict(sorted(matched_component_pairs.items())), "spatial_matches_with_runner_up_margin_at_least_0_10": unique_spatial_matches, "spatial_matches_iou_at_least_0_95": strong_spatial_matches, "spatial_matches_covering_at_least_0_95_of_both_polygons": two_sided_spatial_matches, "spatial_matches_below_0_95_iou": len(changed_spatial_geometries), "below_0_95_iou_subject_ids": changed_spatial_geometries, "historical_name_differences": len(name_encoding_differences), "name_differences_with_direct_normalized_ocha_join": sum(row["ocha_exact_normalized_name_parent_matches"] == 1 for row in name_encoding_differences), "spatial_candidate_parent_mismatch_subject_ids": spatial_parent_mismatches},
    "inc_wri_roster": {"feature_count": len(wri_features), "scope_unique_name_parent_match_count": sum(row["inc_wri_exact_normalized_name_parent_matches"] == 1 for row in rows)},
    "crosswalk": rows,
}
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"output": str(OUT.relative_to(REPO)), "scope_count": len(rows), "ocha": result["ocha_roster"], "inc_wri": result["inc_wri_roster"]}, indent=2))
