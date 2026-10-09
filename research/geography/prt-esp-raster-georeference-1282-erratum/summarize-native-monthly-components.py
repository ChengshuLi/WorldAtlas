#!/usr/bin/env python3
"""Compute complete 12-month JRC summaries one immutable component at a time.

Each component phase includes the full 2024 monthly source set, every native
1024 x 1024 block intersecting that component, the complete geometry/code
inputs, and its whole component-month output. No component is split by month
or block. The aggregate command reads only completed component results.
"""
from __future__ import annotations

import collections
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import subprocess
import sys
import traceback
import types
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window
from shapely import contains_xy
from shapely.geometry import Point, box, shape


ROOT = Path(__file__).resolve().parents[3]
OWN_REL = "research/geography/prt-esp-raster-georeference-1282-erratum/"
OLD_REL = "research/geography/portugal-spain-gap-source-families-20261007/"
SCRIPT_REL = OWN_REL + "summarize-native-monthly-components.py"
HELPER_REL = "scripts/evidence/immutable.py"
CAPTURE_REL = OLD_REL + "sources/jrc/monthlyhistory-v1_5-2024-capture.json"
GEOMETRY_REL = OLD_REL + "inputs/selected-70-component-geometries.geojson"
INDEX_REL = OLD_REL + "inputs/complete-input-index.json"
MATRIX_REL = OLD_REL + "outputs/source-status-matrix.json"
AUDIT_REL = OWN_REL + "runs/run-1/native-coverage-audit.json"
SOURCE_CAPTURE_SHA = "659cacf727f59cf19c637417160c172d89772b23563c1bd9bb025800fc57f5ce"
GEOMETRY_SHA = "c320f2be4a560532c0255e655bed696958a5638f6c37e4ab83b10e8aef02d1a4"
INDEX_SHA = "fde93383b699cff1e36668b85ee6529e7fb27062ab0c714c82412ab8f48e08be"
MATRIX_SHA = "1c02f0fa73f4b13211c275c1a4214424e4835df8469edd96e8dbb467b2181743"
AUDIT_SHA = "101390e3521ccefd6937efadbb528add17fb35f91f87c17ad054ac77e704b09b"
MAX_FILE = 32 * 1024 * 1024
MAX_PHASE = 256 * 1024 * 1024
BLOCK_BYTES = 1024 * 1024
OUTPUT_RESERVE = 256 * 1024
PRIOR_FAILURE_LOG = """Traceback (most recent call last):
  File \"/Users/chengshuli/world-atlas-workspace/.worldatlas-workspaces/ae1b9113bc909cae/cd4c34b51cabfedba197d1fec7ffd8bea30193a8c1835b651f642cfdf9462ccd/work/research/geography/prt-esp-raster-georeference-1282-erratum/summarize-native-monthly-components.py\", line 359, in <module>
    main()
  File \"/Users/chengshuli/world-atlas-workspace/.worldatlas-workspaces/ae1b9113bc909cae/cd4c34b51cabfedba197d1fec7ffd8bea30193a8c1835b651f642cfdf9462ccd/work/research/geography/prt-esp-raster-georeference-1282-erratum/summarize-native-monthly-components.py\", line 355, in main
    print(json.dumps(run_phase(sys.argv[1]), sort_keys=True))
  File \"/Users/chengshuli/world-atlas-workspace/.worldatlas-workspaces/ae1b9113bc909cae/cd4c34b51cabfedba197d1fec7ffd8bea30193a8c1835b651f642cfdf9462ccd/work/research/geography/prt-esp-raster-georeference-1282-erratum/summarize-native-monthly-components.py\", line 346, in run_phase
    result = component_phase(commit, phase, row, geometry_row, capture, audit, scope_rows, assets, baseline, evidence)
  File \"/Users/chengshuli/world-atlas-workspace/.worldatlas-workspaces/ae1b9113bc909cae/cd4c34b51cabfedba197d1fec7ffd8bea30193a8c1835b651f642cfdf9462ccd/work/research/geography/prt-esp-raster-georeference-1282-erratum/summarize-native-monthly-components.py\", line 289, in component_phase
    \"input_bindings\": {d[\"path\"]: {\"bytes\": d[\"bytes\"], \"sha256\": d[\"sha256\"]} for d in descriptors},
NameError: name 'descriptors' is not defined
"""


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), "cat-file", "blob", f"{commit}:{path}"])


def git_descriptor(commit: str, path: str) -> dict:
    raw = git_bytes(commit, path)
    if len(raw) > MAX_FILE:
        raise ValueError(f"Pinned file exceeds 32 MiB: {path}")
    return {"path": path, "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes"}


def sha_roster(values: set[str]) -> str:
    return sha(("\n".join(sorted(values)) + "\n").encode())


def valid_header(crs: str | None, transform: tuple[float, ...], expected: dict) -> bool:
    """Compare native CRS/affine against an independently retained header row."""
    if not crs or crs != expected["crs"] or len(transform) < 6:
        return False
    actual = transform[:6]
    target = expected["transform"][:6]
    return all(math.isclose(float(a), float(b), rel_tol=0.0, abs_tol=1e-10) for a, b in zip(actual, target))


def candidate_blocks(geom, ds) -> list[tuple[int, int]]:
    """Return all native blocks with positive-area intersection with a geometry."""
    if ds.crs.to_epsg() != 4326 or ds.transform.b != 0 or ds.transform.d != 0:
        raise ValueError("The captured source must be north-up EPSG:4326")
    bx, by = ds.block_shapes[0][1], ds.block_shapes[0][0]
    west, north = ds.transform.c, ds.transform.f
    px, py = ds.transform.a, -ds.transform.e
    rows, cols = math.ceil(ds.height / by), math.ceil(ds.width / bx)
    minx, miny, maxx, maxy = geom.bounds
    c0 = max(0, math.floor((minx - west) / px / bx))
    c1 = min(cols, math.ceil((maxx - west) / px / bx))
    r0 = max(0, math.floor((north - maxy) / py / by))
    r1 = min(rows, math.ceil((north - miny) / py / by))
    selected = []
    for br in range(r0, r1):
        row0 = br * by
        row1 = min(ds.height, row0 + by)
        y_top = north - row0 * py
        y_bottom = north - row1 * py
        for bc in range(c0, c1):
            col0 = bc * bx
            col1 = min(ds.width, col0 + bx)
            x_left = west + col0 * px
            x_right = west + col1 * px
            # Boundary-only contact cannot contain a pixel center. Positive
            # area is conservative for all center-in-polygon observations.
            if geom.intersection(box(x_left, y_bottom, x_right, y_top)).area > 0:
                selected.append((br, bc))
    return selected


def make_baseline(commit: str, assets: list[dict]):
    capture_raw = git_bytes(commit, CAPTURE_REL)
    if sha(capture_raw) != SOURCE_CAPTURE_SHA:
        raise ValueError("Inherited JRC source capture no longer matches its reviewed hash")
    capture = json.loads(capture_raw)
    if len(assets) != 24 or capture.get("asset_count") != 24:
        raise ValueError("The complete 24-asset JRC 2024 capture is required")
    static_expected = {
        GEOMETRY_REL: GEOMETRY_SHA,
        INDEX_REL: INDEX_SHA,
        MATRIX_REL: MATRIX_SHA,
        AUDIT_REL: AUDIT_SHA,
    }
    descriptors = []
    for path, expected in static_expected.items():
        row = git_descriptor(commit, path)
        if row["sha256"] != expected:
            raise ValueError("Pinned scope or prior audit changed: " + path)
        descriptors.append(row)
    for path in (CAPTURE_REL, SCRIPT_REL, HELPER_REL):
        descriptors.append(git_descriptor(commit, path))
    for asset in assets:
        path = OLD_REL + "sources/jrc/monthlyhistory-v1_5-2024/" + asset["filename"]
        descriptors.append({"path": path, "bytes": asset["bytes"], "sha256": asset["sha256"], "hash_kind": "file-bytes"})
    helper_raw = git_bytes(commit, HELPER_REL)
    helper_module = types.ModuleType("evidence_immutable")
    helper_module.__file__ = str(ROOT / HELPER_REL)
    exec(compile(helper_raw, helper_module.__file__, "exec"), helper_module.__dict__)
    Baseline = helper_module.Baseline
    baseline = Baseline(ROOT, commit, descriptors, max_phase_bytes=MAX_PHASE)
    if baseline.pinned_bytes(HELPER_REL) != helper_raw:
        raise ValueError("Executed shared evidence helper differs from immutable source")
    return baseline, helper_module, descriptors


def component_phase(commit: str, phase: str, component: dict, geometry: dict, capture: dict,
                    audit: dict, scope_rows: dict, assets: list[dict], baseline, evidence,
                    descriptors: list[dict]):
    component_id = component["component_id"]
    geom = shape(geometry["geometry"])
    source_row = scope_rows[component_id]
    if sorted(component["family_ids"]) != sorted(source_row["family_ids"]):
        raise ValueError("Component family crosswalk differs from original scope")
    if sorted(component["contact_ids"]) != sorted(source_row["contact_ids"]):
        raise ValueError("Component contact crosswalk differs from original scope")

    audit_assets = {row["filename"]: row for row in audit["assets"]}
    by_tile = collections.defaultdict(list)
    for asset in assets:
        tile = asset["filename"].split("_v1_5_2024_")[0].removeprefix("monthlyhistory_")
        by_tile[tile].append(asset)

    selected = []
    for tile, tile_assets in sorted(by_tile.items()):
        first = next((a for a in tile_assets if a["filename"].endswith("_01.tif")), None)
        if first is None:
            raise ValueError("Missing January native transform for " + tile)
        first_path = ROOT / OLD_REL / "sources/jrc/monthlyhistory-v1_5-2024" / first["filename"]
        with rasterio.open(first_path) as ds:
            meta = audit_assets[first["filename"]]
            if sha(baseline.materialized_bytes(OLD_REL + "sources/jrc/monthlyhistory-v1_5-2024/" + first["filename"])) != first["sha256"]:
                raise ValueError("Materialized raster differs from captured bytes")
            if not valid_header(ds.crs.to_string() if ds.crs else None, tuple(ds.transform), meta):
                raise ValueError("Native header differs from retained independent metadata")
            if ds.width != 40000 or ds.height != 40000 or ds.dtypes != ("uint8",) or ds.block_shapes != [(1024, 1024)]:
                raise ValueError("Unexpected native raster structure")
            blocks = candidate_blocks(geom, ds)
            if blocks:
                selected.append((tile, blocks))

    # Phase is per whole component: admit all 12 months for each intersecting
    # native tile and every geometry-intersecting block before pixel reads.
    planned = []
    for tile, blocks in selected:
        tile_assets = sorted(by_tile[tile], key=lambda row: row["filename"])
        if len(tile_assets) != 12:
            raise ValueError("A complete twelve-month tile series is required")
        for asset in tile_assets:
            asset_path = OLD_REL + "sources/jrc/monthlyhistory-v1_5-2024/" + asset["filename"]
            baseline.materialized_bytes(asset_path)
            native = audit_assets[asset["filename"]]
            with rasterio.open(ROOT / asset_path) as ds:
                if not valid_header(ds.crs.to_string() if ds.crs else None, tuple(ds.transform), native):
                    raise ValueError("Monthly native affine differs from its audited metadata")
                for br, bc in blocks:
                    baseline.admit(f"decoded:{asset_path}:block:{br}:{bc}", BLOCK_BYTES)
                    planned.append((asset, ds.transform, br, bc))
    baseline.admit("planned-output-reserve:component-month-summary.json", OUTPUT_RESERVE)

    vintage = f"jrc-2024-{phase}-{sha(component_id.encode())[:12]}"
    writer = evidence.NewVintage(baseline, OWN_REL, vintage, ["component-month-summary.json"])
    month_counts = {f"2024-{m:02d}": collections.Counter() for m in range(1, 13)}
    month_samples = collections.Counter()
    water_centres = set()
    code_controls = {}
    planned_blocks = []
    # Pixel reads start only after all source/code/geometry/block/output bytes
    # for this complete 12-month component phase have been admitted.
    for tile, blocks in selected:
        tile_assets = sorted(by_tile[tile], key=lambda row: row["filename"])
        for asset in tile_assets:
            asset_path = OLD_REL + "sources/jrc/monthlyhistory-v1_5-2024/" + asset["filename"]
            with rasterio.open(ROOT / asset_path) as ds:
                if not valid_header(ds.crs.to_string() if ds.crs else None, tuple(ds.transform), audit_assets[asset["filename"]]):
                    raise ValueError("Native transform changed after phase admission")
                month = int(asset["filename"][-6:-4])
                bx, by = ds.block_shapes[0][1], ds.block_shapes[0][0]
                for br, bc in blocks:
                    row0, col0 = br * by, bc * bx
                    height, width = min(by, ds.height - row0), min(bx, ds.width - col0)
                    data = ds.read(1, window=Window(col0, row0, width, height))
                    xs = ds.transform.c + (np.arange(col0, col0 + width) + 0.5) * ds.transform.a
                    ys = ds.transform.f + (np.arange(row0, row0 + height) + 0.5) * ds.transform.e
                    xx, yy = np.meshgrid(xs, ys)
                    mask = contains_xy(geom, xx, yy)
                    vals = data[mask]
                    if len(vals) and not set(map(int, np.unique(vals))).issubset({0, 1, 2}):
                        raise ValueError("Unexpected monthly-history code inside scoped geometry")
                    month_samples[month] += int(len(vals))
                    month_counts[f"2024-{month:02d}"].update(map(int, vals))
                    for code in (0, 1, 2):
                        if code not in code_controls and np.any(mask & (data == code)):
                            rr, cc = np.argwhere(mask & (data == code))[0]
                            pixel_row, pixel_col = row0 + int(rr), col0 + int(cc)
                            center = list(ds.xy(pixel_row, pixel_col))
                            if not geom.contains(Point(*center)):
                                raise ValueError("Positive pixel-center control is not inside the target component")
                            code_controls[code] = {
                                "month": f"2024-{month:02d}", "tile": tile,
                                "row": pixel_row, "column": pixel_col, "value": code,
                                "center_lonlat": center,
                                "interpretation": {0: "no observation", 1: "observed non-water in this month", 2: "water detected in this month"}[code],
                            }
                    if np.any(mask & (data == 2)):
                        rr, cc = np.nonzero(mask & (data == 2))
                        for r, c in zip(rr, cc):
                            pixel_row, pixel_col = row0 + int(r), col0 + int(c)
                            water_centres.add((tile, pixel_row, pixel_col))
                    planned_blocks.append({"month": f"2024-{month:02d}", "asset": asset["filename"], "block_row": br, "block_column": bc, "decoded_bytes": BLOCK_BYTES})

    months = []
    for month in range(1, 13):
        key = f"2024-{month:02d}"
        counts = month_counts[key]
        months.append({"month": key, "source_grid_pixel_centers": month_samples[month],
                       "code_counts": {str(code): int(counts[code]) for code in (0, 1, 2)},
                       "meaning": {"0": "no observation", "1": "observed non-water in this month", "2": "water detected in this month"}})
    summary = {
        "schema": "worldatlas-jrc-native-component-month-summary-v1",
        "component_id": component_id,
        "family_ids": sorted(component["family_ids"]),
        "contact_ids": sorted(component["contact_ids"]),
        "coverage_status": component["native_tile_union_coverage_status"],
        "method": "Complete native-affine pixel-center counts for all twelve 2024 months and every full native block intersecting this unchanged component geometry.",
        "source_months": [f"2024-{m:02d}" for m in range(1, 13)],
        "native_tiles": [tile for tile, _ in selected],
        "blocks_per_month": {tile: len(blocks) for tile, blocks in selected},
        "decoded_block_instances": len(planned_blocks),
        "decoded_unique_bytes": len(planned_blocks) * BLOCK_BYTES,
        "admitted_phase_bytes_before_output": sum(baseline.consumed.values()),
        "phase_budget_bytes": MAX_PHASE,
        "months": months,
        "components_with_any_monthly_code_2_pixel_center": len(water_centres),
        "native_positive_pixel_controls": {str(code): row for code, row in sorted(code_controls.items())},
        "adversarial_affine_controls": {
            "native_header_accepted": True,
            "north_edge_shifted_10_degrees_rejected": all(
                not valid_header(audit_assets[a["filename"]]["crs"],
                                tuple(audit_assets[a["filename"]]["transform"][:5] + [audit_assets[a["filename"]]["transform"][5] + 10]),
                                audit_assets[a["filename"]])
                for a in assets
            ),
            "web_mercator_rejected": all(not valid_header("EPSG:3857", tuple(audit_assets[a["filename"]]["transform"]), audit_assets[a["filename"]]) for a in assets),
            "flipped_row_direction_rejected": all(
                not valid_header(audit_assets[a["filename"]]["crs"],
                                tuple(audit_assets[a["filename"]]["transform"][:4] + [abs(audit_assets[a["filename"]]["transform"][4])] + audit_assets[a["filename"]]["transform"][5:]),
                                audit_assets[a["filename"]])
                for a in assets
            ),
        },
        "input_bindings": {d["path"]: {"bytes": d["bytes"], "sha256": d["sha256"]} for d in descriptors},
        "runtime": {"python": platform.python_version(), "numpy": np.__version__, "shapely": importlib.metadata.version("shapely"),
                    "rasterio": rasterio.__version__, "gdal": rasterio.__gdal_version__},
        "limits": [
            "Counts include only source-grid pixel centers inside this component geometry; partial-cell area is not measured.",
            "Code 0 is no observation, code 1 is only that month's observed non-water, and code 2 is a monthly detection.",
            "These measurements do not classify all physical surface, ownership, cause, rightful territory, boundaries, or historical state.",
            "The 2024 Landsat Collection 2 product is current observational context, not a substitute for the source vintages of recorded administrative contacts.",
        ],
    }
    raw = evidence.canonical_json(summary)
    if len(raw) > OUTPUT_RESERVE:
        raise ValueError("Component summary exceeded the reserved output allowance")
    return writer.publish({"component-month-summary.json": summary})


def write_failure(commit: str, phase: str, component_id: str, failure_head: str,
                  error: str, error_log: str, baseline, evidence):
    """Retain a bounded failure receipt; it never masquerades as a result."""
    vintage = f"failed-full-{sha((failure_head + phase + component_id).encode())[:16]}"
    writer = evidence.NewVintage(baseline, OWN_REL, vintage, ["failure.json", "failure.log"])
    log_raw = error_log.encode("utf-8")
    payload = {
        "schema": "worldatlas-geography-phase-failure-v1",
        "status": "failed-no-scientific-output",
        "phase": phase,
        "component_id": component_id,
        "attempt_head": failure_head,
        "pinned_baseline": commit,
        "error": error,
        "log_bytes": len(log_raw),
        "log_sha256": sha(log_raw),
        "stdout_bytes": 0,
        "admitted_bytes_before_failure_receipt": sum(baseline.consumed.values()),
        "limits": ["No component counts or geographic conclusions are retained by this failure receipt."],
    }
    writer.publish_bytes({"failure.json": evidence.canonical_json(payload), "failure.log": log_raw})


def run_phase(phase: str) -> dict:
    if phase not in ("run-1", "run-2"):
        raise ValueError("Run must be run-1 or run-2")
    commit = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"]).decode().strip()
    capture_raw = git_bytes(commit, CAPTURE_REL)
    if sha(capture_raw) != SOURCE_CAPTURE_SHA:
        raise ValueError("Inherited JRC capture changed")
    capture = json.loads(capture_raw)
    assets = capture["assets"]
    baseline, evidence, descriptors = make_baseline(commit, assets)
    geometry = json.loads(baseline.pinned_bytes(GEOMETRY_REL))
    index = json.loads(baseline.pinned_bytes(INDEX_REL))
    matrix = json.loads(baseline.pinned_bytes(MATRIX_REL))
    audit = json.loads(baseline.pinned_bytes(AUDIT_REL))
    if len(geometry["features"]) != 70 or len(matrix["components"]) != 70 or len(audit["components"]) != 70:
        raise ValueError("Complete 70-component scope and native coverage audit required")
    geo_by_id = {f["properties"]["source_payload_id"]: f for f in geometry["features"]}
    coverage_by_id = {r["component_id"]: r for r in audit["components"]}
    source_rows = {r["component_id"]: r for r in matrix["components"]}
    original_scope = index["scope"]["family_component_contact_rows"]
    scope_rows = {}
    for family in original_scope:
        for component_id in family["component_ids"]:
            row = scope_rows.setdefault(component_id, {"family_ids": set(), "contact_ids": set()})
            row["family_ids"].add(family["id"])
            row["contact_ids"].update(family["contact_ids"])
    scope_rows = {k: {"family_ids": sorted(v["family_ids"]), "contact_ids": sorted(v["contact_ids"])} for k, v in scope_rows.items()}
    if set(geo_by_id) != set(coverage_by_id) or set(geo_by_id) != set(scope_rows) or len(original_scope) != 52:
        raise ValueError("Original family/component roster mismatch")
    ids = set(geo_by_id)
    if sha_roster(ids) != "d537eeaee6c9cbc0ac03ff7227cb1a87c214bfde6644df9c50d46bb2e63e5c5f":
        raise ValueError("Unexpected component identities")

    covered = [coverage_by_id[cid] for cid in sorted(ids) if coverage_by_id[cid]["native_tile_union_coverage_status"] != "none"]
    if len(covered) != 23:
        raise ValueError("Expected 23 native-footprint-covered components")
    results = []
    for covered_index, row in enumerate(covered):
        geometry_row = geo_by_id[row["component_id"]]
        if covered_index:
            baseline, evidence, descriptors = make_baseline(commit, assets)
        try:
            result = component_phase(commit, phase, row, geometry_row, capture, audit, scope_rows, assets, baseline, evidence, descriptors)
        except Exception as exc:
            write_failure(commit, phase, row["component_id"], commit, f"{type(exc).__name__}: {exc}", traceback.format_exc(), baseline, evidence)
            raise
        results.append({"component_id": row["component_id"], "path": result[0]["path"], "bytes": result[0]["bytes"], "sha256": result[0]["sha256"]})
        print(json.dumps({"phase": phase, "component_id": row["component_id"], "path": result[0]["path"], "sha256": result[0]["sha256"]}), flush=True)
    return {"phase": phase, "component_count": len(results), "results": results}


def record_prior_failure(commit: str, phase: str, component_id: str, error: str) -> None:
    capture_raw = git_bytes(commit, CAPTURE_REL)
    if sha(capture_raw) != SOURCE_CAPTURE_SHA:
        raise ValueError("Failure attempt source capture differs from the retained pin")
    capture = json.loads(capture_raw)
    baseline, evidence, _ = make_baseline(commit, capture["assets"])
    # The first reproduction had already admitted and decoded this complete
    # component phase before failing while building its output binding.
    audit = json.loads(baseline.pinned_bytes(AUDIT_REL))
    component = next(row for row in audit["components"] if row["component_id"] == component_id)
    geometry_raw = baseline.pinned_bytes(GEOMETRY_REL)
    geometry = next(feature for feature in json.loads(geometry_raw)["features"]
                    if feature["properties"]["source_payload_id"] == component_id)
    geom = shape(geometry["geometry"])
    asset = next(row for row in capture["assets"] if row["filename"].endswith("_01.tif") and "10W_40N" in row["filename"])
    tile_path = OLD_REL + "sources/jrc/monthlyhistory-v1_5-2024/" + asset["filename"]
    with rasterio.open(ROOT / tile_path) as ds:
        blocks = candidate_blocks(geom, ds)
    if not blocks:
        raise ValueError("Failure component no longer has native raster blocks")
    for month_asset in capture["assets"]:
        if "10W_40N" not in month_asset["filename"]:
            continue
        for br, bc in blocks:
            baseline.admit(f"decoded:{month_asset['filename']}:block:{br}:{bc}", BLOCK_BYTES)
    baseline.admit("planned-output-reserve:component-month-summary.json", OUTPUT_RESERVE)
    write_failure(commit, phase, component_id, commit, error, PRIOR_FAILURE_LOG, baseline, evidence)


def main() -> None:
    if len(sys.argv) == 2 and sys.argv[1] in ("run-1", "run-2"):
        print(json.dumps(run_phase(sys.argv[1]), sort_keys=True))
        return
    if len(sys.argv) == 5 and sys.argv[1] == "record-failure":
        record_prior_failure(sys.argv[2], sys.argv[3], sys.argv[4], "NameError: name 'descriptors' is not defined after complete component computation")
        return
    raise SystemExit("Usage: summarize-native-monthly-components.py run-1|run-2 | record-failure COMMIT PHASE COMPONENT_ID")


if __name__ == "__main__":
    main()
