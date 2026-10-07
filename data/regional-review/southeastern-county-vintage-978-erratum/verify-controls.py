#!/usr/bin/env python3
"""Isolated changed-input, identity, output-safety, and analytic controls."""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
OWNED = "data/regional-review/southeastern-county-vintage-978-erratum/"
PACKET = ROOT / OWNED


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def must_reject(label, function):
    try:
        function()
    except (ValueError, FileExistsError):
        return {"control": label, "outcome": "rejected-as-expected"}
    raise AssertionError(f"Negative control failed to reject {label}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--script-sha256", required=True)
    parser.add_argument("--runner-sha256", required=True)
    parser.add_argument("--inventory-sha256", required=True)
    args = parser.parse_args()
    here = Path(__file__).resolve()
    runner_path = PACKET / "reproduce.py"
    inventory_path = PACKET / "baseline-inventory.json"
    if digest(here.read_bytes()) != args.script_sha256:
        raise SystemExit("Control script differs from the explicit reviewed pin")
    if digest(runner_path.read_bytes()) != args.runner_sha256:
        raise SystemExit("Geometry runner differs from the exact runner pin")
    inventory_bytes = inventory_path.read_bytes()
    if digest(inventory_bytes) != args.inventory_sha256:
        raise SystemExit("Baseline inventory differs from the explicit reviewed pin")
    inventory = json.loads(inventory_bytes)
    sys.path.insert(0, str(ROOT))
    from scripts.evidence.immutable import Baseline
    spec = importlib.util.spec_from_file_location("worldatlas_1252_runner", runner_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    drift = copy.deepcopy(inventory["files"])
    drift[0]["sha256"] = "0" * 64
    changed_input = must_reject("changed whole-file pin before computation", lambda: Baseline(ROOT, inventory["commit"], drift))
    duplicate = must_reject("duplicate source identity", lambda: module.unique_index([{"GEOID": "28059"}, {"GEOID": "28059"}], "GEOID", "fixture"))
    missing = must_reject("missing scoped identity", lambda: module.exact_roster({"one": {}}, {"one": {}, "two": {}}, "fixture"))

    with tempfile.TemporaryDirectory(prefix="worldatlas-1252-controls-") as temp_name:
        temp = Path(temp_name)
        owned_path = OWNED + "vintages/probe.json"
        target = temp / owned_path
        target.parent.mkdir(parents=True, exist_ok=True)
        sentinel = b"preserved-existing-bytes\n"
        target.write_bytes(sentinel)
        existing = must_reject("pre-existing output destination", lambda: module.exclusive_write(temp, owned_path, b"replacement"))
        if target.read_bytes() != sentinel:
            raise AssertionError("Existing destination bytes changed")

        outside = temp / "outside"
        outside.mkdir()
        link = temp / OWNED / "vintages" / "escape"
        link.symlink_to(outside, target_is_directory=True)
        escape = must_reject("symlink traversal outside owned directory", lambda: module.exclusive_write(temp, OWNED + "vintages/escape/payload.json", b"forbidden"))
        if (outside / "payload.json").exists():
            raise AssertionError("Symlink escape wrote outside the owned directory")

    positive = {"method_id": "six-county-frozen-reproduction", "kind": "positive-control", "outcome": "passed",
                "analytic_geometry": "two equal 1000 m squares offset by 500 m in EPSG:5070",
                "expected_iou": 1 / 3, "axis_policy": "longitude-latitude; pyproj always_xy"}
    # Wrong-axis and wrong-denominator methods must be observably distinct.
    from pyproj import Transformer
    from shapely.affinity import translate
    from shapely.geometry import box
    from shapely.ops import transform
    forward = Transformer.from_crs("EPSG:4326", "EPSG:5070", always_xy=True)
    inverse = Transformer.from_crs("EPSG:5070", "EPSG:4326", always_xy=True)
    center = forward.transform(-90, 30)
    left = translate(box(center[0], center[1], center[0] + 1000, center[1] + 1000), xoff=-500)
    right = box(center[0], center[1], center[0] + 1000, center[1] + 1000)
    left = transform(forward.transform, transform(inverse.transform, left))
    right = transform(forward.transform, transform(inverse.transform, right))
    observed = left.intersection(right).area / left.union(right).area
    if abs(observed - (1 / 3)) >= 1e-7:
        raise AssertionError(f"Analytic positive control failed: {observed}")
    positive["observed_iou"] = observed

    default_axis = Transformer.from_crs("EPSG:4326", "EPSG:5070").transform(-90, 30)
    correct_axis = forward.transform(-90, 30)
    if max(abs(default_axis[0] - correct_axis[0]), abs(default_axis[1] - correct_axis[1])) < 1_000_000:
        raise AssertionError("Authority-axis negative control failed to distinguish axis order")
    wrong_denominator = left.intersection(right).area / left.area
    if abs(wrong_denominator - observed) < 0.1:
        raise AssertionError("Wrong-denominator negative control failed to distinguish IoU")

    negative = {"method_id": "six-county-frozen-reproduction", "kind": "negative-control", "outcome": "passed",
                "rejections": [changed_input, duplicate, missing, existing, escape],
                "preserved_existing_output_sha256": digest(sentinel),
                "symlink_escape_created_no_external_file": True,
                "wrong_intersection_over_source_area": wrong_denominator,
                "correct_axis_coordinate_epsg5070": correct_axis,
                "default_axis_coordinate_epsg5070": default_axis,
                "wrong_axis_rejected": True}
    if len(negative["rejections"]) != 5:
        raise AssertionError("A required negative control is missing")

    runs = []
    for vintage in ("2026-10-07-c", "2026-10-07-d"):
        result_path = PACKET / "vintages" / vintage / "native-geometry-audit.json"
        result_bytes = result_path.read_bytes()
        result = json.loads(result_bytes)
        if len(result["subjects"]) != 6 or result["runner_sha256"] != args.runner_sha256:
            raise AssertionError(f"Run {vintage} is incomplete or used different runner code")
        runs.append({"path": OWNED + f"vintages/{vintage}/native-geometry-audit.json", "sha256": digest(result_bytes)})
    if runs[0]["sha256"] != runs[1]["sha256"]:
        raise AssertionError("Two complete fresh outputs are not byte-identical")
    reproducibility = {"method_id": "six-county-frozen-reproduction", "kind": "reproducibility", "outcome": "passed",
                       "run_one_sha256": runs[0]["sha256"], "run_two_sha256": runs[1]["sha256"], "runs": runs,
                       "scope": "all six identities, source/Atlas/Census join values, geometry summaries, frozen IoUs and rosters"}
    for filename, value in (("positive-control-final.json", positive), ("negative-control-final.json", negative), ("reproducibility-control-final.json", reproducibility)):
        target = PACKET / filename
        if target.exists():
            raise FileExistsError(f"Refusing existing control destination: {target}")
        module.exclusive_write(ROOT, OWNED + filename, (json.dumps(value, sort_keys=True, indent=2) + "\n").encode())
    print(json.dumps({"positive": "passed", "negative_rejections": len(negative["rejections"]), "reproducibility": reproducibility["run_one_sha256"]}, sort_keys=True))


if __name__ == "__main__":
    main()
