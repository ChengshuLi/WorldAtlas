#!/usr/bin/env python3
"""Join complete component phase outputs without reopening any raster data."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OWN = "research/geography/prt-esp-raster-georeference-1282-erratum/"
OLD = "research/geography/portugal-spain-gap-source-families-20261007/"
HELPER = "scripts/evidence/immutable.py"
RUNNER = OWN + "summarize-native-monthly-components.py"
AGGREGATOR = OWN + "aggregate-native-monthly-components.py"
INDEX = OLD + "inputs/complete-input-index.json"
MATRIX = OLD + "outputs/source-status-matrix.json"
AUDIT = OWN + "runs/run-1/native-coverage-audit.json"
GEOMETRY = OLD + "inputs/selected-70-component-geometries.geojson"
MONTHS = [f"2024-{month:02d}" for month in range(1, 13)]
COMPONENT_ROSTER = "d537eeaee6c9cbc0ac03ff7227cb1a87c214bfde6644df9c50d46bb2e63e5c5f"
FAMILY_ROSTER = "6ccdac13874fa8d4b6f444076ace737a4ac6a9f84fae2c1168207b1385d892a0"
CONTACT_ROSTER = "a47f36a11e723a12f662930f8ac98c4f500e6d0a8f78872699a8592cea60c2d6"
MAX_FILE = 32 * 1024 * 1024
MAX_PHASE = 256 * 1024 * 1024


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), "cat-file", "blob", f"{commit}:{path}"])


def descriptor(commit: str, path: str) -> dict:
    raw = git_bytes(commit, path)
    if len(raw) > MAX_FILE:
        raise ValueError("Pinned aggregate input exceeds 32 MiB: " + path)
    return {"path": path, "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes"}


def load_helper(commit: str, paths: list[str]):
    pins = [descriptor(commit, path) for path in paths]
    source = git_bytes(commit, HELPER)
    module = types.ModuleType("evidence_immutable")
    module.__file__ = str(ROOT / HELPER)
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    baseline = module.Baseline(ROOT, commit, pins, max_phase_bytes=MAX_PHASE)
    if baseline.pinned_bytes(HELPER) != source:
        raise ValueError("Shared evidence helper source mismatch")
    return module, baseline, pins


def component_path(phase: str, component_id: str, runner_sha: str) -> str:
    return OWN + f"vintages/jrc-2024-{phase}-{runner_sha}-{sha(component_id.encode())[:12]}/component-month-summary.json"


def publication_path(result_path: str) -> str:
    return str(Path(result_path).parent / "publication.json")


def verify_publication(baseline, summary_path: str, publication_pathname: str, result_raw: bytes) -> None:
    receipt = json.loads(baseline.pinned_bytes(publication_pathname))
    expected = {
        "path": summary_path,
        "bytes": len(result_raw),
        "sha256": sha(result_raw),
        "hash_kind": "file-bytes",
    }
    if receipt.get("version") != 1 or receipt.get("status") != "complete" or receipt.get("outputs") != [expected]:
        raise ValueError("Component output lacks its exact exclusive completion receipt")


def run() -> None:
    commit = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"]).decode().strip()
    runner_sha = sha(git_bytes(commit, RUNNER))[:12]
    # Discover all phase outputs from the immutable expected 23-subject roster.
    audit = json.loads(git_bytes(commit, AUDIT))
    matrix = json.loads(git_bytes(commit, MATRIX))
    index = json.loads(git_bytes(commit, INDEX))
    geometry = json.loads(git_bytes(commit, GEOMETRY))
    if len(audit["components"]) != 70 or len(matrix["components"]) != 70 or len(geometry["features"]) != 70:
        raise ValueError("Complete native and source roster is required")
    coverage = {row["component_id"]: row for row in audit["components"]}
    component_ids = set(coverage)
    if sha(("\n".join(sorted(component_ids)) + "\n").encode()) != COMPONENT_ROSTER:
        raise ValueError("Component roster hash mismatch")
    covered_ids = sorted(identity for identity, row in coverage.items() if row["native_tile_union_coverage_status"] != "none")
    if len(covered_ids) != 23:
        raise ValueError("Expected 23 components with native tile footprint coverage")

    result_paths = {}
    for phase in ("run-1", "run-2"):
        for component_id in covered_ids:
            path = component_path(phase, component_id, runner_sha)
            if path in result_paths.values():
                raise ValueError("Duplicate component result path")
            result_paths[(phase, component_id)] = path
    failure_component = "physical-component:0ffe3884cb8abcafd1513dc6ef642bbe14d77a214d53730c7f896a47b5d41009"
    failure_head = "a440f6de3c81b6ed9d3fe9611f1966bf05d4e602"
    failure_vintage = "failed-" + sha((failure_head + "run-1" + failure_component).encode())[:16]
    failure_path = OWN + f"vintages/{failure_vintage}/failure.json"
    failure_receipt = str(Path(failure_path).parent / "publication.json")
    full_failure_vintage = "failed-full-" + sha((failure_head + "run-1" + failure_component).encode())[:16]
    full_failure_path = OWN + f"vintages/{full_failure_vintage}/failure.json"
    full_failure_log = OWN + f"vintages/{full_failure_vintage}/failure.log"
    full_failure_receipt = str(Path(full_failure_path).parent / "publication.json")
    collision_head = "ff53c2d14555187c9e6f6d72f8db31f47bfad988"
    collision_vintage = "failed-full-" + sha((collision_head + "run-1" + failure_component).encode())[:16]
    collision_failure_path = OWN + f"vintages/{collision_vintage}/failure.json"
    collision_failure_log = OWN + f"vintages/{collision_vintage}/failure.log"
    collision_failure_receipt = str(Path(collision_failure_path).parent / "publication.json")
    pinned_paths = [HELPER, RUNNER, AGGREGATOR, INDEX, MATRIX, AUDIT, GEOMETRY]
    pinned_paths += sorted(set(result_paths.values()))
    pinned_paths += [publication_path(path) for path in sorted(set(result_paths.values()))]
    pinned_paths += [failure_path, failure_receipt, full_failure_path, full_failure_log, full_failure_receipt,
                     collision_failure_path, collision_failure_log, collision_failure_receipt]
    helper, baseline, pins = load_helper(commit, pinned_paths)
    index_data = json.loads(baseline.pinned_bytes(INDEX))
    matrix_data = json.loads(baseline.pinned_bytes(MATRIX))
    audit_data = json.loads(baseline.pinned_bytes(AUDIT))

    result_bytes = {}
    result_rows = {}
    for component_id in covered_ids:
        pair = []
        for phase in ("run-1", "run-2"):
            path = result_paths[(phase, component_id)]
            raw = baseline.pinned_bytes(path)
            verify_publication(baseline, path, publication_path(path), raw)
            row = json.loads(raw)
            if row.get("schema") != "worldatlas-jrc-native-component-month-summary-v1" or row.get("component_id") != component_id:
                raise ValueError("Component result identity/schema mismatch")
            if row.get("coverage_status") != coverage[component_id]["native_tile_union_coverage_status"]:
                raise ValueError("Component result coverage status mismatch")
            if [month.get("month") for month in row.get("months", [])] != MONTHS:
                raise ValueError("Incomplete or duplicate month series")
            if row.get("admitted_phase_bytes_before_output", MAX_PHASE + 1) > MAX_PHASE:
                raise ValueError("A complete component phase exceeded its cap")
            if row.get("decoded_unique_bytes") != row.get("decoded_block_instances") * 1024 * 1024:
                raise ValueError("Decoded byte ledger differs from complete block inventory")
            if not all(row.get("adversarial_affine_controls", {}).get(key) for key in (
                "native_header_accepted", "north_edge_shifted_10_degrees_rejected", "web_mercator_rejected", "flipped_row_direction_rejected"
            )):
                raise ValueError("Native affine controls did not all pass")
            if row.get("family_ids") != coverage[component_id]["family_ids"] or row.get("contact_ids") != coverage[component_id]["contact_ids"]:
                raise ValueError("Component source crosswalk mismatch")
            totals = {str(code): sum(int(month["code_counts"][str(code)]) for month in row["months"]) for code in (0, 1, 2)}
            control_codes = set(row.get("native_positive_pixel_controls", {}))
            if any((totals[code] > 0) != (code in control_codes) for code in ("0", "1", "2")):
                raise ValueError("Native positive pixel controls do not match complete annual code counts")
            for code, control in row.get("native_positive_pixel_controls", {}).items():
                if control.get("value") != int(code) or control.get("month") not in MONTHS:
                    raise ValueError("Native pixel control has a wrong code or month")
            pair.append(row)
            result_bytes[(phase, component_id)] = raw
        if result_bytes[("run-1", component_id)] != result_bytes[("run-2", component_id)]:
            raise ValueError("Two fresh whole-component runs differ: " + component_id)
        result_rows[component_id] = pair[0]

    failure_raw = baseline.pinned_bytes(failure_path)
    verify_publication(baseline, failure_path, failure_receipt, failure_raw)
    failure = json.loads(failure_raw)
    if failure.get("status") != "failed-no-scientific-output" or failure.get("attempt_head") != failure_head:
        raise ValueError("Prior failed attempt is not accurately retained")
    full_failure_raw = baseline.pinned_bytes(full_failure_path)
    full_failure_log_raw = baseline.pinned_bytes(full_failure_log)
    full_receipt = json.loads(baseline.pinned_bytes(full_failure_receipt))
    expected_full_outputs = [
        {"path": full_failure_path, "bytes": len(full_failure_raw), "sha256": sha(full_failure_raw), "hash_kind": "file-bytes"},
        {"path": full_failure_log, "bytes": len(full_failure_log_raw), "sha256": sha(full_failure_log_raw), "hash_kind": "file-bytes"},
    ]
    if full_receipt.get("version") != 1 or full_receipt.get("status") != "complete" or full_receipt.get("outputs") != expected_full_outputs:
        raise ValueError("Whole-byte prior failure log lacks its exact completion receipt")
    full_failure = json.loads(full_failure_raw)
    if full_failure.get("status") != "failed-no-scientific-output" or full_failure.get("log_bytes") != len(full_failure_log_raw) or full_failure.get("log_sha256") != sha(full_failure_log_raw):
        raise ValueError("Whole-byte failure log binding mismatch")
    collision_failure_raw = baseline.pinned_bytes(collision_failure_path)
    collision_failure_log_raw = baseline.pinned_bytes(collision_failure_log)
    collision_receipt = json.loads(baseline.pinned_bytes(collision_failure_receipt))
    expected_collision_outputs = [
        {"path": collision_failure_path, "bytes": len(collision_failure_raw), "sha256": sha(collision_failure_raw), "hash_kind": "file-bytes"},
        {"path": collision_failure_log, "bytes": len(collision_failure_log_raw), "sha256": sha(collision_failure_log_raw), "hash_kind": "file-bytes"},
    ]
    collision_failure = json.loads(collision_failure_raw)
    if (collision_receipt.get("version") != 1 or collision_receipt.get("status") != "complete" or
        collision_receipt.get("outputs") != expected_collision_outputs or
        collision_failure.get("attempt_head") != collision_head or
        collision_failure.get("status") != "failed-no-scientific-output" or
        collision_failure.get("log_bytes") != len(collision_failure_log_raw) or
        collision_failure.get("log_sha256") != sha(collision_failure_log_raw)):
        raise ValueError("Output-collision failure is not faithfully preserved")

    matrix_components = {row["component_id"]: row for row in matrix_data["components"]}
    index_families = index_data["scope"]["family_component_contact_rows"]
    family_ids = {row["id"] for row in index_families}
    contact_ids = set(index_data["scope"]["contact_ids"])
    if len(index_families) != 52 or len(contact_ids) != 57:
        raise ValueError("Original family/contact roster mismatch")
    if sha(("\n".join(sorted(family_ids)) + "\n").encode()) != FAMILY_ROSTER:
        raise ValueError("Family roster hash mismatch")
    if sha(("\n".join(sorted(contact_ids)) + "\n").encode()) != CONTACT_ROSTER:
        raise ValueError("Contact roster hash mismatch")
    matrix_families = {row["family_id"]: row for row in matrix_data["families"]}
    if set(matrix_families) != family_ids:
        raise ValueError("Original acceptance family IDs differ from the independent source matrix")
    family_components = set()
    family_contacts = set()
    for family in index_families:
        fid = family["id"]
        reference = matrix_families[fid]
        if set(family["component_ids"]) != set(reference["component_ids"]) or set(family["contact_ids"]) != set(reference["contact_ids"]):
            raise ValueError("Original family-to-component/contact crosswalk differs from the source matrix: " + fid)
        family_components.update(family["component_ids"])
        family_contacts.update(family["contact_ids"])
    if family_components != component_ids or family_contacts != contact_ids:
        raise ValueError("Family memberships do not exactly cover the original component/contact rosters")
    for component_id, row in matrix_components.items():
        if set(row["family_ids"]) != set(coverage[component_id]["family_ids"]) or set(row["contact_ids"]) != set(coverage[component_id]["contact_ids"]):
            raise ValueError("Independent component source matrix crosswalk mismatch: " + component_id)

    components = []
    for component_id in sorted(component_ids):
        cov = coverage[component_id]
        source = matrix_components[component_id]
        if cov["native_tile_union_coverage_status"] == "none":
            components.append({
                "component_id": component_id,
                "family_ids": cov["family_ids"],
                "contact_ids": cov["contact_ids"],
                "native_tile_coverage": "none",
                "monthly_pixel_center_counts": None,
                "status": "unknown-no-native-2024-footprint",
                "limitation": "The captured 10W_30N and 10W_40N native footprints do not cover this component; counts are unknown, not zero.",
            })
            continue
        row = result_rows[component_id]
        components.append({
            "component_id": component_id,
            "family_ids": row["family_ids"],
            "contact_ids": row["contact_ids"],
            "native_tile_coverage": row["coverage_status"],
            "monthly_pixel_center_counts": row["months"],
            "source_grid_pixel_centers_with_code_2_in_any_month": row["components_with_any_monthly_code_2_pixel_center"],
            "native_positive_pixel_controls": row["native_positive_pixel_controls"],
            "status": "measured-within-native-footprint",
            "limitation": "Counts are complete only for source-grid pixel centers inside this component and native tile footprint; a partial footprint does not establish total component counts.",
        })

    families = []
    for family in sorted(index_families, key=lambda row: row["id"]):
        members = [coverage[cid] for cid in family["component_ids"]]
        is_complete = bool(members) and all(m["native_tile_union_coverage_status"] == "full" for m in members)
        counts = None
        if is_complete:
            counts = {month: {str(code): 0 for code in (0, 1, 2)} for month in MONTHS}
            for component_id in family["component_ids"]:
                row = result_rows[component_id]
                for month_row in row["months"]:
                    for code in ("0", "1", "2"):
                        counts[month_row["month"]][code] += int(month_row["code_counts"][code])
        unresolved = sorted(m["component_id"] for m in members if m["native_tile_union_coverage_status"] != "full")
        families.append({
            "family_id": family["id"],
            "component_ids": family["component_ids"],
            "contact_ids": family["contact_ids"],
            "full_native_footprint_monthly_counts": counts,
            "unresolved_components": unresolved,
            "status": "measured-for-all-full-footprint-members" if is_complete else "unknown-incomplete-native-footprint-coverage",
            "limitation": "No family totals are emitted when any member lacks full native raster footprint coverage.",
        })

    control_coverage = {
        str(code): {
            "components_with_positive_native_pixel": sorted(
                component_id for component_id, row in result_rows.items()
                if str(code) in row["native_positive_pixel_controls"]
            ),
            "components_without_positive_native_pixel": sorted(
                component_id for component_id, row in result_rows.items()
                if str(code) not in row["native_positive_pixel_controls"]
            ),
            "meaning": {0: "no observation", 1: "observed non-water in that month", 2: "water detected in that month"}[code],
        }
        for code in (0, 1, 2)
    }
    if any(not value["components_with_positive_native_pixel"] for value in control_coverage.values()):
        raise ValueError("The complete covered scope lacks a native pixel control for code 0, 1, or 2")
    summary = {
        "schema": "worldatlas-jrc-2024-native-component-month-summary-v1",
        "source": {
            "product": "JRC Global Surface Water Monthly History v1.5, 2024",
            "source_vintage": "2022-2024 Landsat Collection 2 monthly history",
            "official_url": "https://global-surface-water.appspot.com/download",
            "license": "Official JRC page states free without use restriction; source attribution requested as EC JRC/Google.",
            "captured_assets": 24,
            "native_footprints": "10W_30N covers 20-30N; 10W_40N covers 30-40N. Both are native EPSG:4326, 0.00025 degree, north-up rasters.",
        },
        "scope": {"families": 52, "components": 70, "contacts": 57,
                   "component_roster_sha256": COMPONENT_ROSTER, "family_roster_sha256": FAMILY_ROSTER, "contact_roster_sha256": CONTACT_ROSTER},
        "reproduction": {"covered_components_run_twice_byte_identically": len(result_rows),
                         "components_without_native_footprint": sum(c["status"] == "unknown-no-native-2024-footprint" for c in components)},
        "code_meanings": {"0": "no observation", "1": "observed non-water for that month", "2": "water detected for that month"},
        "native_pixel_controls": control_coverage,
        "components": components,
        "families": families,
        "limits": [
            "The old filename-derived +10 degree raster positions and summaries are withdrawn as spatially supported observations.",
            "Monthly detections and non-detections are observational context; they do not establish wetted area, land/water classification, ownership, cause, boundaries, or historical territorial status.",
            "47 components have no captured native tile footprint. Their counts remain unknown and are not zero.",
            "One footprint-covered component is partial. Family totals are withheld for every family with any partial or uncovered component.",
            "Current JRC observations are not a temporal substitute for the recorded 2018/2020 administrative source vintages; APA, MAPA-original and MITECO source gaps remain unresolved as described in the retained erratum.",
        ],
    }
    run_manifest = {
        "schema": "worldatlas-jrc-component-reproducibility-v1",
        "status": "reproduced-byte-identically-for-23-complete-component-phases",
        "phases_per_component": "Every phase includes all 12 months and every native block intersecting the whole immutable component geometry.",
        "component_results": [
            {"component_id": component_id,
             "run_1": {"path": result_paths[("run-1", component_id)], "bytes": len(result_bytes[("run-1", component_id)]), "sha256": sha(result_bytes[("run-1", component_id)])},
             "run_2": {"path": result_paths[("run-2", component_id)], "bytes": len(result_bytes[("run-2", component_id)]), "sha256": sha(result_bytes[("run-2", component_id)])},
             "identical": result_bytes[("run-1", component_id)] == result_bytes[("run-2", component_id)]}
            for component_id in covered_ids
        ],
        "failed_attempts": [
            {"path": failure_path, "bytes": len(failure_raw), "sha256": sha(failure_raw),
             "attempt_head": failure_head, "status": "failed-no-scientific-output", "log_preserved": False},
            {"path": full_failure_path, "bytes": len(full_failure_raw), "sha256": sha(full_failure_raw),
             "log_path": full_failure_log, "log_bytes": len(full_failure_log_raw), "log_sha256": sha(full_failure_log_raw),
             "attempt_head": failure_head, "status": "failed-no-scientific-output", "log_preserved": True},
            {"path": collision_failure_path, "bytes": len(collision_failure_raw), "sha256": sha(collision_failure_raw),
             "log_path": collision_failure_log, "log_bytes": len(collision_failure_log_raw), "log_sha256": sha(collision_failure_log_raw),
             "attempt_head": collision_head, "status": "failed-no-scientific-output", "log_preserved": True},
        ],
        "aggregate_inputs": [{"path": row["path"], "bytes": row["bytes"], "sha256": row["sha256"]} for row in pins],
        "limits": ["The aggregate step reads only completed component JSON outputs; it does not reopen or decode raster pixels."],
    }
    baseline.admit("planned-output-reserve:aggregate-summary-and-reproducibility.json", 1024 * 1024)
    vintage = "jrc-2024-aggregate-" + commit[:12]
    writer = helper.NewVintage(baseline, OWN, vintage, ["corrected-monthly-summary.json", "reproducibility.json"])
    writer.publish({"corrected-monthly-summary.json": summary, "reproducibility.json": run_manifest})
    print(json.dumps({"vintage": vintage, "components": len(components), "families": len(families),
                      "covered": len(result_rows), "without_coverage": sum(c["status"] == "unknown-no-native-2024-footprint" for c in components),
                      "summary_sha256": sha(helper.canonical_json(summary)), "reproducibility_sha256": sha(helper.canonical_json(run_manifest))}, sort_keys=True))


if __name__ == "__main__":
    if sys.argv[1:] != ["aggregate"]:
        raise SystemExit("Usage: aggregate-native-monthly-components.py aggregate")
    run()
