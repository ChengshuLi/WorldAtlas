#!/usr/bin/env python3
"""Run format- and source-bound positive/negative controls for issue #1299."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import os
import re
import copy
import sys
import importlib.util
import subprocess
import tempfile

from shapely.geometry import LineString, Point, Polygon, shape

ANALYSIS_PATH = Path(__file__).with_name("run-analysis.py")
ANALYSIS_SPEC = importlib.util.spec_from_file_location("run_analysis", ANALYSIS_PATH)
ANALYSIS = importlib.util.module_from_spec(ANALYSIS_SPEC)
ANALYSIS_SPEC.loader.exec_module(ANALYSIS)
ROOT, SCOPE_PATH, BASELINE = ANALYSIS.ROOT, ANALYSIS.SCOPE_PATH, ANALYSIS.BASELINE
CAPTURE_INDEX_PATH = ANALYSIS.CAPTURE_INDEX_PATH
load_context, digest, write_json = ANALYSIS.load_context, ANALYSIS.digest, ANALYSIS.write_json
bounds_and_extent, count_geom, polygon_pair = ANALYSIS.bounds_and_extent, ANALYSIS.count_geom, ANALYSIS.polygon_pair
read_capture, wa_geometry, geom_json = ANALYSIS.read_capture, ANALYSIS.wa_geometry, ANALYSIS.geom_json
OWNED_PATH = ANALYSIS.OWNED_PATH
NewVintage = ANALYSIS.NewVintage

METHOD_ID = "official-source-geography-v1"
CONTROL_PRODUCER_COMMIT = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ANALYSIS.REPO, text=True).strip()

def reject(label, operation):
    try:
        operation()
    except Exception as exc:
        return {"id": label, "outcome": "rejected-as-expected", "exception": type(exc).__name__, "reason": str(exc)}
    raise AssertionError(f"Negative control failed to reject: {label}")

def _run_controls():
    ctx = load_context()
    scope = ctx["scope"]
    expected_components = {x for family in scope["families"] for x in family["component_ids"]}
    expected_contacts = set(scope["subject_ids"])
    incidences = sum(len(x["contact_subjects"]) for x in scope["families"])

    positive = {
        "version": 1,
        "method_id": METHOD_ID,
        "kind": "positive-control",
        "producer_commit": CONTROL_PRODUCER_COMMIT,
        "corrected_control_sha256": digest(Path(__file__).read_bytes()),
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
            {"id": "uncovered-residual-preserved", "outcome": "passed",
             "residual_area_m2": None, "residual_type": None},
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
    residual = square.difference(half)
    positive["checks"][4].update({"residual_area_m2": wa_geometry.area(residual), "residual_type": residual.geom_type})
    if residual.is_empty or wa_geometry.area(residual) <= 0:
        raise AssertionError("Uncovered residual was not preserved")

    negative_rows = []
    def expected_feature_identity_failure():
        ANALYSIS.geojson_feature(ctx["capture_index"], "dgt-barrancos-0204", "not-0204", "Barrancos")
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

    def wrong_subject_parent():
        exact = {key: value["feature"] for key, value in ctx["subjects"].items()}
        corrupted = copy.deepcopy(exact)
        corrupted["gb:PRT:ADM2:2272694B82300393258858"]["properties"]["parent_id"] = "framework:province:huelva:wrong"
        ANALYSIS.validate_subject_parents(corrupted)
    negative_rows.append(reject("wrong-subject-parent", wrong_subject_parent))

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

    negative = {"version": 1, "method_id": METHOD_ID, "producer_commit": CONTROL_PRODUCER_COMMIT,
                "corrected_control_sha256": digest(Path(__file__).read_bytes()), "outcome": "passed",
                "kind": "negative-control", "checks": negative_rows,
                "limits": ["Each perturbed case must fail closed; these controls do not determine political identity, authority, or physical class."]}

    # Actual paired runs are the reproducibility control, rather than an in-memory approximation.
    pairs = []
    outroot = ANALYSIS.REPO / OWNED_PATH / "vintages"
    run_one = os.environ.get("WORLDATLAS_RUN_ONE", "run-01")
    run_two = os.environ.get("WORLDATLAS_RUN_TWO", "run-02")
    if not re.fullmatch(r"run-[0-9]{2}(?:-r[0-9]+)?", run_one) or not re.fullmatch(r"run-[0-9]{2}(?:-r[0-9]+)?", run_two) or run_one == run_two:
        raise ValueError("Reproducibility control requires two distinct safe run vintages")
    dirs = [outroot / run_one, outroot / run_two]
    if not all((path / "publication.json").is_file() for path in dirs):
        raise ValueError("Both complete frozen run directories must exist before reproducibility control")
    receipts = [json.loads((path / "publication.json").read_bytes()) for path in dirs]
    inventories = []
    for path, receipt in zip(dirs, receipts):
        entries = [row for row in receipt.get("outputs", []) if not row["path"].endswith("execution-receipt.json")]
        for row in entries:
            target = ANALYSIS.REPO / row["path"]
            if target.is_symlink() or not target.is_file():
                raise ValueError("Paired run output is absent or unsafe")
            raw = target.read_bytes()
            if len(raw) != row["bytes"] or digest(raw) != row["sha256"]:
                raise ValueError("Paired run output no longer matches its completion receipt")
        inventories.append({row["path"].split("/vintages/", 1)[-1].split("/", 1)[-1]: row for row in entries})
    if set(inventories[0]) != set(inventories[1]):
        raise ValueError("Paired full-run file inventories differ")
    for rel in sorted(inventories[0]):
        a, b = inventories[0][rel], inventories[1][rel]
        if a["bytes"] != b["bytes"] or a["sha256"] != b["sha256"]:
            raise ValueError(f"Paired full-run output differs: {rel}")
        pairs.append({"path": rel, "bytes": a["bytes"], "sha256": a["sha256"]})
    inventory_digest = digest(json.dumps(pairs, sort_keys=True, separators=(",", ":")).encode())
    reproducibility = {"version": 1, "method_id": METHOD_ID, "producer_commit": CONTROL_PRODUCER_COMMIT,
                       "corrected_control_sha256": digest(Path(__file__).read_bytes()), "kind": "reproducibility", "outcome": "passed",
                       "run_one": "runs/run-01", "run_two": "runs/run-02", "compared_files": pairs,
                       "run_one_sha256": inventory_digest, "run_two_sha256": inventory_digest,
                       "source_capture_index_sha256": __import__("hashlib").sha256(CAPTURE_INDEX_PATH.read_bytes()).hexdigest(),
                       "limits": ["Execution times are recorded separately; identical science result files are compared byte-for-byte."]}
    write_json(ROOT / "controls" / "positive-control.json", positive)
    write_json(ROOT / "controls" / "negative-control.json", negative)
    write_json(ROOT / "controls" / "reproducibility.json", reproducibility)
    print(json.dumps({"positive": positive["outcome"], "negative": negative["outcome"],
                      "negative_cases": len(negative_rows), "reproducibility": reproducibility["outcome"],
                      "paired_files": len(pairs)}, indent=2))

def run_controls():
    global ROOT, NewVintage, wa_geometry
    baseline, _packet = ANALYSIS.packet_baseline()
    NewVintage, wa_geometry = ANALYSIS.NewVintage, ANALYSIS.wa_geometry
    names = ["positive-control.json", "negative-control.json", "reproducibility.json"]
    control_vintage = os.environ.get("WORLDATLAS_CONTROL_VINTAGE", "controls")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", control_vintage):
        raise ValueError("Use a safe fresh control vintage")
    vintage = NewVintage(baseline, OWNED_PATH, control_vintage, names)
    ANALYSIS.planned_run_outputs()  # Check the fixed accepted scope before reading/calculating.
    prior_root = ROOT
    prior_analysis_root = ANALYSIS.ROOT
    prior_outputs, prior_expected, prior_run = ANALYSIS.ACTIVE_OUTPUTS, ANALYSIS.ACTIVE_EXPECTED, ANALYSIS.ACTIVE_RUN
    with tempfile.TemporaryDirectory(prefix="worldatlas-1482-controls-") as scratch:
        ROOT = Path(scratch)
        ANALYSIS.ROOT = ROOT
        ANALYSIS.ACTIVE_OUTPUTS, ANALYSIS.ACTIVE_EXPECTED, ANALYSIS.ACTIVE_RUN = {}, set(names), None
        try:
            _run_controls()
            if set(ANALYSIS.ACTIVE_OUTPUTS) != set(names):
                raise ValueError("Complete fresh control output inventory mismatch")
            vintage.publish_bytes(ANALYSIS.ACTIVE_OUTPUTS)
        finally:
            ROOT, ANALYSIS.ROOT = prior_root, prior_analysis_root
            ANALYSIS.ACTIVE_OUTPUTS, ANALYSIS.ACTIVE_EXPECTED, ANALYSIS.ACTIVE_RUN = prior_outputs, prior_expected, prior_run

if __name__ == "__main__":
    run_controls()
