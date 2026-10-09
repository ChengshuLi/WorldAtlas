#!/usr/bin/env python3
"""Derive trusted-gate positive and negative measurement receipts from two audits."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

OWN = Path(__file__).resolve().parent
METHOD = "native-geotiff-coverage-and-pixel-controls"
RUNS = ("run-1", "run-2")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_run(name: str) -> tuple[bytes, dict]:
    path = OWN / "runs" / name / "native-coverage-audit.json"
    assert path.is_file() and not path.is_symlink()
    data = path.read_bytes()
    document = json.loads(data)
    assert document["method_id"] == METHOD and document["outcome"] == "passed"
    return data, document


def write_new(path: Path, value: dict) -> None:
    assert OWN in path.parent.resolve().parents and not path.exists() and not path.is_symlink()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    runs = [load_run(name) for name in RUNS]
    hashes = [digest(raw) for raw, _ in runs]
    assert hashes[0] == hashes[1], "The two original audit runs must remain byte-identical"
    audit = runs[0][1]

    assets = audit["assets"]
    assert len(assets) == 24
    for asset in assets:
        north = 30 if "_30N_" in asset["filename"] else 40
        assert asset["crs"] == "EPSG:4326"
        assert asset["width"] == asset["height"] == 40_000
        assert abs(asset["bounds"][3] - north) < 1e-10
    assert audit["summary"] == {
        "components_with_full_native_tile_coverage": 22,
        "components_with_native_tile_coverage": 23,
        "components_with_no_native_tile_coverage": 47,
        "components_with_partial_native_tile_coverage": 1,
        "limitations": audit["summary"]["limitations"],
    }

    checks = audit["controls"]["checks"]
    expected = [(1265, 11154, 2), (194, 12287, 1), (692, 11964, 0)]
    assert [(row["row"], row["column"], row["value"]) for row in checks] == expected
    assert all(row["claimed_center_inside_component"] and not row["native_center_inside_component"] for row in checks)
    assert all(abs((row["claimed_lonlat"][1] - row["native_center_lonlat"][1]) - 10) < 1e-9 for row in checks)

    positive = {
        "schema": "worldatlas-measurement-control-v1",
        "method_id": METHOD,
        "kind": "positive-control",
        "outcome": "passed",
        "audit_runs": [{"run": name, "sha256": sha} for name, sha in zip(RUNS, hashes)],
        "authenticated_native_headers": {"count": len(assets), "crs": "EPSG:4326", "native_north_edges_degrees": [30, 40]},
        "native_pixel_controls": [
            {key: row[key] for key in ("row", "column", "value", "native_center_lonlat", "claimed_center_inside_component", "native_center_inside_component")}
            for row in checks
        ],
        "measurement_summary": {key: audit["summary"][key] for key in (
            "components_with_native_tile_coverage", "components_with_full_native_tile_coverage",
            "components_with_partial_native_tile_coverage", "components_with_no_native_tile_coverage")},
        "interpretation": "Positive controls confirm native metadata, pixel row/column values, and the bounded footprint measurement; they do not classify water or whole components.",
    }

    adverse = audit["controls"]["adversarial_fixtures"]
    expected_cases = {
        "north-edge-shifted-plus-10-degrees", "wrong-crs-web-mercator", "flipped-row-direction",
        "out-of-native-coverage-point", "claimed-controls-even-if-hashes-refresh",
    }
    assert {row["case"] for row in adverse} == expected_cases and all(row["rejected"] is True for row in adverse)
    negative = {
        "schema": "worldatlas-measurement-control-v1",
        "method_id": METHOD,
        "kind": "negative-control",
        "outcome": "passed",
        "audit_runs": [{"run": name, "sha256": sha} for name, sha in zip(RUNS, hashes)],
        "rejected_adversarial_fixtures": adverse,
        "interpretation": "Every shifted, wrong-CRS, flipped-row, out-of-coverage, and refreshed-hash false-location control was rejected.",
    }
    write_new(OWN / "controls/native-footprint-positive.json", positive)
    write_new(OWN / "controls/native-footprint-negative.json", negative)
    print(json.dumps({"status": "passed", "runs": dict(zip(RUNS, hashes)), "controls": [
        "controls/native-footprint-positive.json", "controls/native-footprint-negative.json"]}, indent=2))


if __name__ == "__main__":
    main()
