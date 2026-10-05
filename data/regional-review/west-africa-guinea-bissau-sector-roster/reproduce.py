#!/usr/bin/env python3
"""Reproduce a source-name and ellipsoidal area-overlap screen for GNB rosters.

The SALB geometry must be restored from its official GeoJSON URL. This script
does not modify or save that source. The output is a derived tabular screening
result, not a boundary certification or a legal crosswalk.
"""
import argparse
import csv
import hashlib
import json
import re
import collections
import unicodedata
from pathlib import Path
import sys
from importlib.metadata import version
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from shapely.geometry import shape
from evidence.geometry import ownership_overlap


EXPECTED_SALB_SHA256 = "aa5bcf549d10140e372012484c355a4f794fa304a87f225c7d95d3ebafc4cd28"
EXPECTED_OLD_SHA256 = "8839091ee5599651642efc6f8ac65d82a4f40e779bd38debedfd417649bfc680"
EXPECTED_PACKAGES = {"shapely": "2.0.7", "pyproj": "3.5.0", "numpy": "1.24.4"}
PARENT_PACKET = Path(__file__).resolve().parents[1] / "regional-review-1deb892647c1aa26"
OLD = PARENT_PACKET / "sources/geoboundaries-9469f09/GNB-geoBoundaries-GNB-ADM2.geojson"
ASSESSED = PARENT_PACKET / "reproduction/subject-assessments.csv"


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(value):
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(c for c in value if not unicodedata.combining(c)).lower()
    tokens = re.findall(r"[a-z0-9]+", value)
    tokens = ["autonomous" if token == "autonomo" else token for token in tokens]
    tokens = [token for token in tokens if token not in {"setor", "sector", "de"}]
    return " ".join(sorted(tokens))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("salb_geojson", type=Path, help="restored official SALB GeoJSON bytes")
    parser.add_argument("--output", type=Path, default=Path("crosswalk-screen.csv"))
    parser.add_argument("--roster-output", type=Path, default=Path("salb-roster.csv"))
    args = parser.parse_args()
    for package, expected in EXPECTED_PACKAGES.items():
        installed = version(package)
        if installed != expected:
            raise SystemExit(f"{package} version mismatch: expected {expected}, got {installed}")
    digest = sha(args.salb_geojson)
    if digest != EXPECTED_SALB_SHA256:
        raise SystemExit(f"SALB SHA-256 mismatch: {digest}")
    old_digest = sha(OLD)
    if old_digest != EXPECTED_OLD_SHA256:
        raise SystemExit(f"geoBoundaries SHA-256 mismatch: {old_digest}")
    old_doc = json.loads(OLD.read_text(encoding="utf-8"))
    salb_doc = json.loads(args.salb_geojson.read_text(encoding="utf-8"))
    with open(ASSESSED, newline="", encoding="utf-8") as stream:
        atlas = {row["source_shape_id"]: row for row in csv.DictReader(stream) if row["country_iso"] == "GNB"}
    if len(old_doc["features"]) != 39 or len(salb_doc["features"]) != 39 or len(atlas) != 39:
        raise SystemExit("Expected 39 source features in each roster and 39 assessed subjects")

    official = []
    for f in salb_doc["features"]:
        p = f["properties"]
        official.append({"code": p["adm2cd"], "name": p["adm2nm"], "parent_code": p["adm1cd"], "parent": p["adm1nm"], "geom": shape(f["geometry"])})
    old_features = {f["properties"]["shapeID"]: f for f in old_doc["features"]}
    fields = ["atlas_subject_id", "source_id", "source_name", "atlas_source_vintage", "atlas_source_license", "atlas_parent_id", "atlas_parent_name", "salb_normalized_name_candidates", "salb_top_overlap_code", "salb_top_overlap_name", "salb_top_parent_code", "salb_top_parent_name", "salb_vintage", "salb_license_terms", "old_area_covered_by_top_pct", "salb_top_area_covered_by_old_pct", "salb_neighbor_names_by_overlap", "screen_result", "row_uncertainty"]
    rows = []
    for sid, old_f in sorted(old_features.items()):
        p = old_f["properties"]
        row = atlas[sid]
        geom = shape(old_f["geometry"])
        exact = [o for o in official if norm(o["name"]) == norm(p["shapeName"])]
        old_screen = ownership_overlap(geom, {o["code"]: [o["geom"]] for o in official})
        scores = sorted(((share, o) for o in official if (share := old_screen["shares"].get(o["code"], 0)) > 0), reverse=True, key=lambda x: x[0])
        # Reciprocal cover asks how much of each official feature is covered by this old subject.
        top_reciprocal = {o["code"]: ownership_overlap(o["geom"], {sid: [geom]})["shares"].get(sid, 0) for _, o in scores[:3]}
        top = (scores[0][0], scores[0][1], scores[0][0], top_reciprocal[scores[0][1]["code"]])
        neighbors = [f"{o['code']}:{o['name']} ({old_pct*100:.1f}% old)" for old_pct, o in scores[:3]]
        parent_match = norm(row["declared_parent_name"]) == norm(top[1]["parent"])
        exact_top = any(o["code"] == top[1]["code"] for o in exact)
        result = "screen-consistent-name-and-parent" if exact_top and parent_match else "review-required-name-parent-or-vintage"
        rows.append({
            "atlas_subject_id": f"gb:GNB:ADM2:{sid}", "source_id": sid, "source_name": p["shapeName"],
            "atlas_source_vintage": row["source_vintage"], "atlas_source_license": row["source_license"],
            "atlas_parent_id": row["declared_parent_id"], "atlas_parent_name": row["declared_parent_name"],
            "salb_normalized_name_candidates": ";".join(f"{o['code']}:{o['name']} [{o['parent_code']}:{o['parent']}]" for o in exact) or "none",
            "salb_top_overlap_code": top[1]["code"], "salb_top_overlap_name": top[1]["name"],
            "salb_top_parent_code": top[1]["parent_code"], "salb_top_parent_name": top[1]["parent"],
            "salb_vintage": "valid 2016-01-01 through last verification/update 2021-09-02",
            "salb_license_terms": "restricted: non-commercial only; attribute DGGC and SALB/United Nations; no geometry/content changes without contributor consent",
            "old_area_covered_by_top_pct": f"{top[2]*100:.4f}", "salb_top_area_covered_by_old_pct": f"{top[3]*100:.4f}",
            "salb_neighbor_names_by_overlap": ";".join(neighbors), "screen_result": result,
            "row_uncertainty": "candidate name/parent/overlap screens agree; legal boundary and completeness not established" if result == "screen-consistent-name-and-parent" else "cross-vintage name, parent or overlap screen requires source resolution; area rank does not establish identity",
        })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    args.roster_output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.roster_output, "w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["salb_adm2_code", "salb_adm2_name", "salb_adm1_code", "salb_adm1_name", "parent_kind", "salb_source_vintage", "salb_license_terms", "completeness_limit", "unit_uncertainty", "neighbor_codes", "neighbor_names"] , lineterminator="\n")
        writer.writeheader()
        for o in sorted(official, key=lambda item: item["code"]):
            parent_kind = "autonomous-sector under ADM1 Bissau" if "bissau" in norm(o["name"]) and "autonomous" in norm(o["name"]) else "sector under region"
            touching = sorted((other for other in official if other["code"] != o["code"] and o["geom"].boundary.intersects(other["geom"].boundary)), key=lambda other: other["code"])
            writer.writerow({"salb_adm2_code": o["code"], "salb_adm2_name": o["name"], "salb_adm1_code": o["parent_code"], "salb_adm1_name": o["parent"], "parent_kind": parent_kind, "salb_source_vintage": "valid 2016-01-01 through last verification/update 2021-09-02", "salb_license_terms": "restricted: non-commercial only; attribute DGGC and SALB/United Nations; no geometry/content changes without contributor consent", "completeness_limit": "39 layer features; SALB terms disclaim completeness/warranty; 2025 government reports 36 sectors under regions", "unit_uncertainty": "2025 effective status and any merger/renaming not established from accessible dated DGGC instrument", "neighbor_codes": ";".join(other["code"] for other in touching), "neighbor_names": ";".join(other["name"] for other in touching)})
    from shapely.geometry import box
    positive = ownership_overlap(box(0, 0, 1, 1), {"known-target": [box(0, 0, 1, 1)]})
    positive_ok = positive["owner"] == "known-target" and positive["status"] == "derived"
    negative = ownership_overlap(box(0, 0, 1, 1), {"disjoint-control": [box(3, 0, 4, 1)]})
    negative_ok = negative["owner"] is None and negative["status"] == "no-majority" and negative["coverage"] == 0
    if not positive_ok or not negative_ok:
        raise SystemExit("Shared geometry helper control failed")
    (args.output.parent / "positive-control.json").write_text(json.dumps({"method_id": "salb-overlap-screen", "kind": "positive-control", "outcome": "passed", "expected_owner": "known-target", "observed": positive}, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    (args.output.parent / "negative-control.json").write_text(json.dumps({"method_id": "salb-overlap-screen", "kind": "negative-control", "outcome": "passed", "expected_owner": None, "observed": negative}, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    salb_parents = collections.Counter(o["parent"] for o in official)
    summary = {
        "old_geoboundaries_subject_count": len(rows), "salb_adm2_count": len(official),
        "salb_regional_sector_count": sum(1 for o in official if not ("bissau" in norm(o["name"]) and "autonomous" in norm(o["name"]))),
        "salb_autonomous_sector_count": sum(1 for o in official if "bissau" in norm(o["name"]) and "autonomous" in norm(o["name"])),
        "atlas_parent_vs_overlap_candidate_review_rows": sum(1 for row in rows if row["screen_result"] != "screen-consistent-name-and-parent"),
        "atlas_parent_vs_overlap_candidate_consistent_rows": sum(1 for row in rows if row["screen_result"] == "screen-consistent-name-and-parent"),
        "salb_features_by_adm1_name": dict(sorted(salb_parents.items())),
        "input_sha256": {"salb_geojson": digest, "geoboundaries_geojson": sha(OLD)},
        "helper": "worldatlas-evidence-geometry-v1",
        "crosswalk_metric_values": {
            f"crosswalk_{row['source_id']}_{field}": float(row[field])
            for row in rows for field in ("old_area_covered_by_top_pct", "salb_top_area_covered_by_old_pct")
        },
    }
    summary["salb_regional_sector_difference_vs_2025_nc4"] = summary["salb_regional_sector_count"] - 36
    summary["validation"] = {"positive_control": positive_ok, "negative_control": negative_ok}
    summary_path = args.output.parent / "summary.json"
    summary_path.write_text(json.dumps(summary, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    metrics_path = args.output.parent / "summary-metrics.csv"
    metrics = [
        ("old_geoboundaries_subject_count", summary["old_geoboundaries_subject_count"], "subjects"),
        ("salb_adm2_count", summary["salb_adm2_count"], "features"),
        ("salb_regional_sector_count", summary["salb_regional_sector_count"], "sectors"),
        ("salb_autonomous_sector_count", summary["salb_autonomous_sector_count"], "sectors"),
        ("atlas_parent_vs_overlap_candidate_review_rows", summary["atlas_parent_vs_overlap_candidate_review_rows"], "rows"),
        ("atlas_parent_vs_overlap_candidate_consistent_rows", summary["atlas_parent_vs_overlap_candidate_consistent_rows"], "rows"),
        ("salb_regional_sector_difference_vs_2025_nc4", summary["salb_regional_sector_difference_vs_2025_nc4"], "sectors"),
    ]
    metrics.extend((metric_id, value, "percent") for metric_id, value in sorted(summary["crosswalk_metric_values"].items()))
    with open(metrics_path, "w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["metric_id", "value", "unit"])
        for metric_id, value, unit in metrics:
            rendered_value = f"{value:.4f}" if unit == "percent" else str(int(value))
            writer.writerow([metric_id, rendered_value, unit])
    print(f"SALB sha256={digest}; old geoBoundaries sha256={old_digest}; rows={len(rows)}; outputs={args.output},{args.roster_output},{summary_path},{metrics_path}")


if __name__ == "__main__":
    main()
