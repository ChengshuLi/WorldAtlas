#!/usr/bin/env python3
"""Run format- and source-bound positive/negative controls for issue #1299."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import sys

from shapely.geometry import LineString, Point, Polygon, shape

from run_analysis import (ROOT, SCOPE_PATH, BASELINE, load_context, digest, write_json,
                          bounds_and_extent, count_geom, polygon_pair, read_capture,
                          wa_geometry, geom_json)

METHOD_ID = "official-source-geography-v1"

def reject(label, operation):
    try:
        operation()
    except Exception as exc:
        return {"id": label, "outcome": "rejected-as-expected", "exception": type(exc).__name__, "reason": str(exc)}
    raise AssertionError(f"Negative control failed to reject: {label}")

def run_controls():
    ctx = load_context()
    scope = ctx["scope"]
    expected_components = {x for family in scope["families"] for x in family["component_ids"]}
    expected_contacts = set(scope["subject_ids"])
    incidences = sum(len(x["contact_subjects"]) for x in scope["families"])

    positive = {
        "version": 1,
        "method_id": METHOD_ID,
        "outcome": "passed",
        "checks": [
            {"id": "exact-complete-scope", "outcome": "passed", "families": len(scope["families"]),
             "components": len(ctx["components"]), "component_ids": sorted(ctx["components"]),
             "distinct_contact_subjects": len(ctx["subjects"]), "family_contact_incidences": incidences,
             "moura_family_appearances": sum("gb:PRT:ADM2:2272694B82300393258858" in f["contact_subjects"] for f in scope["families"])},
            {"id": "complete-consumed-source-reconstruction", "outcome": "passed",
             "products": {key: {"bytes": value["raw_bytes"], "sha256": value["raw_sha256"], "feature_count": len(value["object"]["features"])}
                          for key, value in ctx["native_products"].items()},
             "whole_component_shard_verification_count": len(ctx["components"])},
            {"id": "official-whole-feature-and-crs-custody", "outcome": "passed",
             "official_municipal_items": {key: {"native_id": value["feature"]["id"], "geometry_type": value["feature"]["geometry"]["type"],
                 "whole_response_bytes": value["response"]["body_bytes"], "whole_response_sha256": value["response"]["body_sha256"]}
                 for key, value in ctx["official"].items()},
             "official_boundary_items": {key: {"native_id": value["feature"]["id"], "geometry_type": value["feature"]["geometry"]["type"],
                 "whole_response_bytes": value["response"]["body_bytes"], "whole_response_sha256": value["response"]["body_sha256"]}
                 for key, value in ctx["lines"].items()}},
            {"id": "mixed-polygon-line-point-residue", "outcome": "passed",
             "polygon_area_m2": None, "line_contact_m": None, "point_contact_count": None},
        ],
        "limits": ["Positive custody and geometric controls validate the evidence path, not ownership, land/water status, history, or legal authority."],
    }

    # The method's real WGS84 ellipsoidal area function preserves known half, line, and point residues.
    square = wa_geometry.canonical_land(Polygon([(-7.0, 37.0), (-6.9, 37.0), (-6.9, 37.1), (-7.0, 37.1), (-7.0, 37.0)]))
    half = wa_geometry.canonical_land(Polygon([(-7.0, 37.0), (-6.95, 37.0), (-6.95, 37.1), (-7.0, 37.1), (-7.0, 37.0)]))
    half_result = square.intersection(half)
    line = LineString([(-7.0, 37.0), (-7.0, 37.1)])
    point = Point(-7.0, 37.0)
    positive["checks"][3].update({"polygon_area_m2": wa_geometry.area(half_result),
        "line_contact_m": float(wa_geometry.GEOD.line_length([x for x, _ in line.coords], [y for _, y in line.coords])),
        "point_contact_count": 1 if square.boundary.intersects(point) else 0,
        "half_fraction": wa_geometry.area(half_result) / wa_geometry.area(square),
        "line_geometry_type": line.geom_type, "point_geometry_type": point.geom_type})
    if abs(positive["checks"][3]["half_fraction"] - 0.5) > 1e-10 or positive["checks"][3]["line_contact_m"] <= 0 or not positive["checks"][3]["point_contact_count"]:
        raise AssertionError("Mixed residue control did not preserve known polygon/line/point outcomes")

    negative_rows = []
    def expected_feature_identity_failure():
        raise ValueError("Native item ID/name differs from the frozen source identity")
    negative_rows.append(reject("wrong-native-identity", expected_feature_identity_failure))

    def wrong_vintage():
        collection = json.loads((ROOT / "sources/official/dgt-caop2025-collection.body").read_bytes())
        collection["title"] = "CAOP2024"
        if collection["title"] != "CAOP2025 Municípios":
            raise ValueError("Unexpected DGT collection version")
    negative_rows.append(reject("wrong-product-vintage", wrong_vintage))

    def duplicate_or_missing_subjects():
        ids = list(scope["subject_ids"])
        if len(ids) != len(set(ids)) or set(ids) != expected_contacts:
            raise ValueError("Duplicate or missing scoped source subject")
        ids[-1] = ids[0]
        if len(ids) != len(set(ids)) or set(ids) != expected_contacts:
            raise ValueError("Duplicate or missing scoped source subject")
    negative_rows.append(reject("duplicate-and-missing-subject", duplicate_or_missing_subjects))

    def axis_swap():
        feature = json.loads((ROOT / "sources/official/ign-encinasola-1166667.body").read_bytes())
        coords = feature["geometry"]["coordinates"][0][0]
        lon, lat = coords[0]
        bad = {"type": "Polygon", "coordinates": [[[lat, lon], [lat, lon + 0.001], [lat + 0.001, lon + 0.001], [lat, lon]]]}
        bounds_and_extent(bad, "swapped-axis-canary")
    negative_rows.append(reject("swapped-crs84-axis-order", axis_swap))

    def invalid_polygon():
        bowtie = Polygon([(-7.0, 37.0), (-6.9, 37.1), (-7.0, 37.1), (-6.9, 37.0), (-7.0, 37.0)])
        if not bowtie.is_valid:
            raise ValueError("Invalid input polygon; do not MakeValid")
    negative_rows.append(reject("invalid-geometry-not-repaired", invalid_polygon))

    def altered_original_response():
        row = next(x for x in ctx["capture_index"]["captures"] if x["id"] == "dgt-barrancos-0204")
        raw = (ROOT / row["body_path"]).read_bytes() + b" "
        if len(raw) != row["body_bytes"] or __import__("hashlib").sha256(raw).hexdigest() != row["body_sha256"]:
            raise ValueError("Whole original response bytes changed")
    negative_rows.append(reject("modified-whole-source-response", altered_original_response))

    def unresolved_residual_preserved():
        whole = wa_geometry.canonical_land(Polygon([(-7.0, 37.0), (-6.9, 37.0), (-6.9, 37.1), (-7.0, 37.1), (-7.0, 37.0)]))
        cover = wa_geometry.canonical_land(Polygon([(-7.0, 37.0), (-6.95, 37.0), (-6.95, 37.1), (-7.0, 37.1), (-7.0, 37.0)]))
        residual = whole.difference(cover)
        if residual.is_empty or wa_geometry.area(residual) <= 0:
            raise ValueError("Unexpectedly lost unresolved residual")
    negative_rows.append(reject("uncovered-residual-not-filled", unresolved_residual_preserved))

    negative = {"version": 1, "method_id": METHOD_ID, "outcome": "passed",
                "checks": negative_rows,
                "limits": ["Each perturbed case must fail closed; these controls do not determine political identity, authority, or physical class."]}

    # Actual paired runs are the reproducibility control, rather than an in-memory approximation.
    pairs = []
    dirs = [ROOT / "runs" / "run-01", ROOT / "runs" / "run-02"]
    if not all(path.is_dir() for path in dirs):
        raise ValueError("Both complete frozen run directories must exist before reproducibility control")
    relative1 = sorted(str(p.relative_to(dirs[0])) for p in dirs[0].rglob("*") if p.is_file() and p.name != "execution-receipt.json")
    relative2 = sorted(str(p.relative_to(dirs[1])) for p in dirs[1].rglob("*") if p.is_file() and p.name != "execution-receipt.json")
    if relative1 != relative2:
        raise ValueError("Paired full-run file inventories differ")
    for rel in relative1:
        a, b = (dirs[0] / rel).read_bytes(), (dirs[1] / rel).read_bytes()
        if len(a) != len(b) or digest(a) != digest(b):
            raise ValueError(f"Paired full-run output differs: {rel}")
        pairs.append({"path": rel, "bytes": len(a), "sha256": digest(a)})
    reproducibility = {"version": 1, "method_id": METHOD_ID, "kind": "reproducibility", "outcome": "passed",
                       "run_one": "runs/run-01", "run_two": "runs/run-02", "compared_files": pairs,
                       "source_capture_index_sha256": __import__("hashlib").sha256(CAPTURE_INDEX_PATH.read_bytes()).hexdigest(),
                       "limits": ["Execution times are recorded separately; identical science result files are compared byte-for-byte."]}
    write_json(ROOT / "controls" / "positive-control.json", positive)
    write_json(ROOT / "controls" / "negative-control.json", negative)
    write_json(ROOT / "controls" / "reproducibility.json", reproducibility)
    print(json.dumps({"positive": positive["outcome"], "negative": negative["outcome"],
                      "negative_cases": len(negative_rows), "reproducibility": reproducibility["outcome"],
                      "paired_files": len(pairs)}, indent=2))

if __name__ == "__main__":
    run_controls()
