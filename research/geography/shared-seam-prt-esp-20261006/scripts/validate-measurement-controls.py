#!/usr/bin/env python3
"""Analytic positive/negative controls for the seam overlay measurement."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import Polygon, mapping
from shapely.ops import transform

ROOT = Path(__file__).resolve().parents[4]
OWNED = ROOT / "research/geography/shared-seam-prt-esp-20261006"
ANALYSIS = OWNED / "scripts/reproduce-comparison.py"
METHOD_ID = "utm29-direct-geos-overlay-measurement"


def load_analysis():
    spec = importlib.util.spec_from_file_location("seam_analysis", ANALYSIS)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def source_polygon(bounds, to_source):
    west, south, east, north = bounds
    return transform(to_source.transform, Polygon([
        (west, south), (east, south), (east, north), (west, north), (west, south),
    ]))


def evaluate(module, kind, gap_bounds, subject_bounds, expected):
    to_source = Transformer.from_crs("EPSG:25829", "OGC:CRS84", always_xy=True)
    gap_source = source_polygon(gap_bounds, to_source)
    subject_source = source_polygon(subject_bounds, to_source)
    gap_projected = module.projected(gap_source)
    actual = module.gap_coverage_record(gap_projected, [("analytic-subject", subject_source)])
    for field, value in expected.items():
        observed = actual[field]
        if isinstance(value, float):
            if observed is None or abs(observed - value) > 1e-5:
                raise AssertionError(f"{kind} {field}: expected {value}, got {observed}")
        elif observed != value:
            raise AssertionError(f"{kind} {field}: expected {value!r}, got {observed!r}")
    if actual["invalid_member_ids"] or actual["operation_errors"]:
        raise AssertionError(f"{kind}: source validity or overlay operation failed")
    return {
        "version": 1,
        "method_id": METHOD_ID,
        "kind": kind,
        "outcome": "passed",
        "control_semantics": "Known EPSG:25829 rectangles are transformed to CRS84, then passed through the exact production projection and direct GEOS union/difference/boundary-contact function. No geometry repair is used.",
        "input_gap_bounds_epsg25829_m": list(gap_bounds),
        "input_subject_bounds_epsg25829_m": list(subject_bounds),
        "input_gap_geometry_crs84": mapping(gap_source),
        "input_subject_geometry_crs84": mapping(subject_source),
        "expected": expected,
        "actual": actual,
        "analysis_script_sha256": hashlib.sha256(ANALYSIS.read_bytes()).hexdigest(),
        "execution_commit": subprocess.check_output(["git", "-C", ROOT, "rev-parse", "HEAD"], text=True).strip(),
    }


def main():
    module = load_analysis()
    gap = (650000.0, 4400000.0, 650100.0, 4400100.0)
    controls = [
        evaluate(module, "positive-control", gap,
            (650000.0, 4400000.0, 650050.0, 4400100.0),
            {"covered_area_m2": 5000.0, "uncovered_residual_area_m2": 5000.0,
             "covered_fraction": 0.5, "shared_boundary_contact_length_m": 150.0,
             "gap_intersection_type": "Polygon", "boundary_contact_type": "GeometryCollection"}),
        evaluate(module, "negative-control", gap,
            (650500.0, 4400000.0, 650600.0, 4400100.0),
            {"covered_area_m2": 0.0, "uncovered_residual_area_m2": 10000.0,
             "covered_fraction": 0.0, "shared_boundary_contact_length_m": 0.0,
             "gap_intersection_type": "Polygon", "boundary_contact_type": "LineString"}),
    ]
    out = OWNED / "validation"
    out.mkdir(exist_ok=True)
    for row, name in zip(controls, ("positive-control.json", "negative-control.json")):
        (out / name).write_text(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps({"method_id": METHOD_ID, "controls": [row["kind"] for row in controls], "outcome": "passed"}))


if __name__ == "__main__":
    main()
