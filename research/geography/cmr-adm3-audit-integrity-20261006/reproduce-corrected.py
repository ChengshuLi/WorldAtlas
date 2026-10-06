#!/usr/bin/env python3
"""Recompute #908's exact roster and geodesic candidate scores safely in memory."""
from __future__ import annotations
import csv, hashlib, json, zipfile
from pathlib import Path
from pyproj import Geod
from shapely import orient_polygons
from shapely.geometry import MultiPolygon, Polygon, shape
from shapely.validation import make_valid

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[2]
SOURCE = REPO / "data/regional-review/cameroon-adm3-authoritative-source-restoration"
IDS = SOURCE / "issue-subject-ids.json"
GB = REPO / "data/regional-review/regional-review-4c8c1c55a35245d1/sources/geoBoundaries-CMR-ADM3.geojson"
PRIOR = REPO / "data/regional-review/regional-review-d1c8bea8b9425b8c/unit-review.csv"
OCHA = SOURCE / "source/cmr_admin_boundaries.geojson.zip"
BASELINE = "a7c44deed5de3dd08bfdb0ee099d6e57efb3ea8b"
geod = Geod(ellps="WGS84")

def sha(raw: bytes) -> str: return hashlib.sha256(raw).hexdigest()
def safe_geometry(g): return make_valid(g) if not g.is_valid else g
def area(g):
    """Sum positive WGS84 ellipsoidal areas after CCW exterior/CW hole normalization."""
    g = orient_polygons(safe_geometry(g), exterior_cw=False)
    if g.geom_type == "Polygon": return abs(geod.geometry_area_perimeter(g)[0])
    if g.geom_type in ("MultiPolygon", "GeometryCollection"):
        return sum(area(part) for part in g.geoms if part.geom_type in ("Polygon", "MultiPolygon", "GeometryCollection"))
    return 0.0
def scores(a, b):
    a, b = safe_geometry(a), safe_geometry(b)
    overlap = area(a.intersection(b)); aa = area(a); ba = area(b); union = area(a.union(b))
    return {"iou": overlap / union if union else 0.0,
            "reference_coverage": overlap / aa if aa else 0.0,
            "candidate_coverage": overlap / ba if ba else 0.0}

def legacy_scores(a, b):
    """Faithfully reproduce #908's direct absolute signed-area behavior."""
    a, b = safe_geometry(a), safe_geometry(b)
    signed_area = lambda g: abs(geod.geometry_area_perimeter(g)[0])
    overlap = signed_area(a.intersection(b)); aa = signed_area(a); ba = signed_area(b); union = signed_area(a.union(b))
    return {"iou": overlap / union if union else 0.0,
            "reference_coverage": overlap / aa if aa else 0.0,
            "candidate_coverage": overlap / ba if ba else 0.0}

def exact_subjects():
    ids = json.loads(IDS.read_text())
    declared = json.loads((PACKET / "declared-subject-ids.json").read_text())
    assert len(ids) == 226 and len(set(ids)) == 226 and all(isinstance(x, str) for x in ids)
    assert len(declared) == 226 and len(set(declared)) == 226 and set(ids) == set(declared)
    with PRIOR.open(encoding="utf-8", newline="") as f:
        scoped = [r["location_id"] for r in csv.DictReader(f) if r["country"] == "CMR"]
    assert len(scoped) == 226 and len(set(scoped)) == 226 and set(ids) == set(scoped)
    return ids

def one_run():
    ids = exact_subjects()
    prior_rows = {r["location_id"]: r for r in csv.DictReader(PRIOR.open(encoding="utf-8", newline="")) if r["country"] == "CMR"}
    gb = json.loads(GB.read_text())
    gb_by_id = {f["properties"]["shapeID"]: shape(f["geometry"]) for f in gb["features"]}
    assert len(gb_by_id) == 360
    with zipfile.ZipFile(OCHA) as z:
        ocha = json.loads(z.read("cmr_admin3_em.geojson"))
        adm1 = json.loads(z.read("cmr_admin1_em.geojson"))["features"]
        adm2 = json.loads(z.read("cmr_admin2_em.geojson"))["features"]
    by_code = {f["properties"]["adm3_pcode"]: f for f in ocha["features"]}
    original = json.loads((SOURCE / "candidate-crosswalk.json").read_text())
    assert len(original["crosswalk"]) == len(ids) == 226
    adm1_codes = {f["properties"]["adm1_pcode"] for f in adm1}
    adm2_codes = {f["properties"]["adm2_pcode"] for f in adm2}
    assert len(adm1) == len(adm1_codes) == 10 and len(adm2) == len(adm2_codes) == 58
    assert all(f["properties"].get("adm1_pcode") in adm1_codes for f in adm2)
    assert all(f["properties"].get("adm2_pcode") in adm2_codes and f["properties"].get("adm1_pcode") in adm1_codes for f in ocha["features"])
    wri = json.loads((SOURCE / "source/arrondissements.geojson").read_text())["features"]
    actual = []
    for old in original["crosswalk"]:
        sid = old["subject_id"]
        assert sid in set(ids) and old["gb_source_feature_id"] in gb_by_id
        code = old["ocha_spatial_candidate_pcode"]
        assert code in by_code
        m = scores(gb_by_id[old["gb_source_feature_id"]], shape(by_code[code]["geometry"]))
        row = {"subject_id": sid, "source_feature_id": old["gb_source_feature_id"],
               "candidate_pcode": code, "measurements": {k: round(v, 8) for k, v in m.items()},
               "recorded_numeric_values": {k: v for k, v in old.items()
                   if isinstance(v, (int, float)) and not isinstance(v, bool)},
               "recorded": {"iou": old["ocha_spatial_best_iou"],
                            "reference_coverage": old["ocha_spatial_best_reference_coverage"],
                            "candidate_coverage": old["ocha_spatial_best_candidate_coverage"]}}
        actual.append(row)
    assert [r["subject_id"] for r in actual] == [r["subject_id"] for r in original["crosswalk"]]
    deltas = {k: sum(r["measurements"][k] == r["recorded"][k] for r in actual) for k in ("iou", "reference_coverage", "candidate_coverage")}
    assert deltas == {"iou": 226, "reference_coverage": 226, "candidate_coverage": 226}
    counts = {
      "runner_up_margin_at_least_0_10": original["ocha_roster"]["spatial_matches_with_runner_up_margin_at_least_0_10"],
      "normalized_name_parent_matches": sum(r["ocha_exact_normalized_name_parent_matches"] == 1 for r in original["crosswalk"]),
      "high_iou_ge_0_95": sum(r["ocha_spatial_best_iou"] >= .95 for r in original["crosswalk"]),
      "both_coverages_ge_0_95": original["ocha_roster"]["spatial_matches_covering_at_least_0_95_of_both_polygons"],
      "low_iou_lt_0_95": sum(r["ocha_spatial_best_iou"] < .95 for r in original["crosswalk"]),
      "historical_name_differences": sum(r["historical_source_name_differs_from_atlas_name"] for r in original["crosswalk"]),
      "name_differences_directly_joined": original["ocha_roster"]["name_differences_with_direct_normalized_ocha_join"],
      "spatial_candidate_parent_mismatches": len(original["ocha_roster"]["spatial_candidate_parent_mismatch_subject_ids"]),
      "wri_name_parent_matches": sum(r["inc_wri_exact_normalized_name_parent_matches"] == 1 for r in original["crosswalk"]),
    }
    for component_pair, count in original["ocha_roster"]["historical_to_spatial_candidate_geometry_component_pairs_all_subjects"].items():
        counts["component_pair_" + component_pair.replace("->", "_to_")] = count
    return {"version": 1, "issue": 1101, "baseline_commit": BASELINE,
      "scope_count": len(ids), "subject_ids": ids,
      "subject_ids_sha256": hashlib.sha256(json.dumps(sorted(ids), separators=(",", ":")).encode()).hexdigest(),
      "inputs": {"reproducer_sha256": sha((SOURCE/"reproduce.py").read_bytes()),
                 "crosswalk_sha256": sha((SOURCE/"candidate-crosswalk.json").read_bytes()),
                 "review_sha256": sha((SOURCE/"review.md").read_bytes()),
                 "manifest_sha256": sha((SOURCE/"evidence-quality.json").read_bytes()),
                 "subject_ids_sha256": sha(IDS.read_bytes()),
                 "ocha_sha256": sha(OCHA.read_bytes()), "wri_sha256": sha((SOURCE/"source/arrondissements.geojson").read_bytes()),
                 "historical_geojson_sha256": sha(GB.read_bytes()),
                 "prior_review_sha256": sha(PRIOR.read_bytes())},
      "orientation_safe_recomputation": {"metric_vintage": "baseline", "evaluation_commit": BASELINE,
        "score_count": 678, "matching_recorded_values_to_8_decimals": deltas,
        "mismatching_values": 0, "actual_selected_input_cancellation_cases": 0},
      "ocha_neighboring_tiers": {"adm1_regions": len(adm1), "adm2_departments": len(adm2),
        "adm3_arrondissements": len(ocha["features"]), "adm2_parent_code_coverage": len(adm2),
        "adm3_parent_code_coverage": len(ocha["features"]), "all_parent_codes_resolve": True,
        "source_valid_on": "2019-01-04", "source_boundary_vintage": "1987-08-22"},
      "wri_comparison_inventory": {"features": len(wri), "missing_arrondissement_codes": sum(f.get("properties",{}).get("code_arr") is None for f in wri),
        "source_role": "non-legal comparison; original source metadata identifies no legal validation"},
      "aggregate_counts": counts, "rows": actual}

def controls():
    square = Polygon([(10,0),(11,0),(11,1),(10,1),(10,0)])
    second = Polygon([(12,0),(13,0),(13,1),(12,1),(12,0)])
    reversed_second = Polygon(list(second.exterior.coords)[::-1])
    mixed = MultiPolygon([square, reversed_second])
    hole = Polygon([(10,0),(12,0),(12,2),(10,2),(10,0)],
                   holes=[[(10.5,.5),(10.5,1.5),(11.5,1.5),(11.5,.5),(10.5,.5)]])
    pos = scores(square, square); mixed_scores = scores(mixed, mixed); hole_scores = scores(hole, hole)
    neg = scores(square, second)
    legacy_mixed = legacy_scores(mixed, mixed)
    assert all(abs(pos[k]-1) < 1e-12 for k in pos)
    assert all(abs(mixed_scores[k]-1) < 1e-12 for k in mixed_scores)
    assert all(abs(hole_scores[k]-1) < 1e-12 for k in hole_scores)
    assert neg["iou"] == 0 and neg["reference_coverage"] == 0 and neg["candidate_coverage"] == 0
    hole_area = area(hole); unholed_area = area(Polygon([(10,0),(12,0),(12,2),(10,2),(10,0)]))
    assert 0 < hole_area < unholed_area
    assert legacy_mixed["iou"] == 1 and legacy_mixed["reference_coverage"] == 0 and legacy_mixed["candidate_coverage"] == 0
    return {
      "positive": {"method_id":"orientation-safe-geodesic-recomputation","kind":"positive-control","outcome":"passed","square_self":pos,"hole_self":hole_scores,"hole_area_m2":hole_area,"unholed_area_m2":unholed_area,"hole_reduces_area":True},
      "mixed": {"method_id":"orientation-safe-geodesic-recomputation","kind":"positive-control","outcome":"passed","two_disjoint_components_opposite_winding_self":mixed_scores,"legacy_direct_signed_area_bug_reproduced":legacy_mixed,"legacy_expected_iou":1,"legacy_expected_coverages":0},
      "negative": {"method_id":"orientation-safe-geodesic-recomputation","kind":"negative-control","outcome":"passed","disjoint_square_pair":neg}}

def subject_controls():
    ids = exact_subjects(); expected = set(ids)
    cases = {"exact": ids, "duplicate": ids + [ids[0]], "missing": ids[:-1],
             "fabricated": ids[:-1] + ["gb:CMR:ADM3:NOT-IN-SCOPE"]}
    results = {}
    for label, values in cases.items():
        ok = len(values) == 226 and len(set(values)) == 226 and set(values) == expected
        results[label] = {"count": len(values), "unique_count": len(set(values)),
                          "matches_declared_roster": set(values) == expected,
                          "accepted": ok}
    assert results["exact"]["accepted"] and all(not results[x]["accepted"] for x in ("duplicate","missing","fabricated"))
    return {"method_id":"exact-issue-subject-roster-guard","kind":"negative-control","outcome":"passed",
            "source_id_list_sha256":sha(IDS.read_bytes()),"declared_issue_scope_sha256":sha((PACKET/"declared-subject-ids.json").read_bytes()),"cases":results}

def main():
    one = one_run(); two = one_run()
    bytes_one = json.dumps(one, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    bytes_two = json.dumps(two, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    assert bytes_one == bytes_two
    (PACKET/"corrected-measurements.json").write_text(json.dumps(one, ensure_ascii=False, indent=2)+"\n")
    c = controls()
    (PACKET/"controls-positive.json").write_text(json.dumps(c["positive"], indent=2)+"\n")
    (PACKET/"controls-mixed-winding.json").write_text(json.dumps(c["mixed"], indent=2)+"\n")
    (PACKET/"controls-negative.json").write_text(json.dumps(c["negative"], indent=2)+"\n")
    sc = subject_controls()
    (PACKET/"subject-guard-controls.json").write_text(json.dumps(sc, indent=2)+"\n")
    sp = {"method_id":"exact-issue-subject-roster-guard","kind":"positive-control","outcome":"passed","expected_count":226,"observed_count":len(exact_subjects()),"unique_count":len(set(exact_subjects())),"exact_issue_scope_match":True}
    (PACKET/"subject-guard-positive.json").write_text(json.dumps(sp, indent=2)+"\n")
    report = {"method_id":"orientation-safe-geodesic-recomputation","kind":"reproducibility","outcome":"passed","run_one_sha256":sha(bytes_one),"run_two_sha256":sha(bytes_two),"runs_equal":True,"scope_count":226,"score_count":678}
    (PACKET/"reproducibility.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({"scope_count":one["scope_count"],"matching_values":one["orientation_safe_recomputation"]["matching_recorded_values_to_8_decimals"],"runs_equal":True,"counts":one["aggregate_counts"]},indent=2))

if __name__ == "__main__": main()
