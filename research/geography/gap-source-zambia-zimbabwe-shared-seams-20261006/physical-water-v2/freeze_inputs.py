#!/usr/bin/env python3
"""Freeze exact inputs/runtime and a bounded execution admission record."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import gzip
import math
import platform
import sys
import zlib
from datetime import datetime, timezone
from pathlib import Path

import numpy
import shapely


BASE = Path(__file__).resolve().parent
PACKET = BASE.parent
REPO = PACKET.parents[2]
OUTPUT = BASE / "frozen-inputs.json"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def descriptor(path: Path) -> dict:
    return {"path": str(path.relative_to(REPO)), "bytes": path.stat().st_size, "sha256": digest(path)}


def coordinate_window(geometry: dict | None, complete_window: dict) -> dict | None:
    """Measure exact input geometry envelope rows without opening raster values."""
    if not isinstance(geometry, dict) or not isinstance(geometry.get("coordinates"), list):
        return None
    xs: list[float] = []
    ys: list[float] = []

    def collect(value) -> None:
        if isinstance(value, list):
            if len(value) >= 2 and isinstance(value[0], (int, float)) and isinstance(value[1], (int, float)):
                xs.append(float(value[0]))
                ys.append(float(value[1]))
            else:
                for child in value:
                    collect(child)

    collect(geometry["coordinates"])
    if not xs:
        return None
    columns = complete_window["columns_half_open"]
    rows = complete_window["rows_half_open"]
    pixel = 1 / 12_000
    c0 = max(columns[0], math.floor((min(xs) - 27.0) / pixel) - 1)
    c1 = min(columns[1], math.ceil((max(xs) - 27.0) / pixel) + 1)
    r0 = max(rows[0], math.floor((-15.0 - max(ys)) / pixel) - 1)
    r1 = min(rows[1], math.ceil((-15.0 - min(ys)) / pixel) + 1)
    return {"columns": c1 - c0, "rows": r1 - r0, "coordinate_count": len(xs)}


def geometry_row_admission(geometry_gzip: bytes, range_manifest: dict) -> dict:
    """Report the largest exact per-row vector operation envelope for #1234."""
    data = json.loads(gzip.decompress(geometry_gzip))
    window = range_manifest["complete_pixel_window"]
    candidates = []
    contacts = []
    fragments = []
    subjects = set(data["subject_ids"])
    for component in data["components"]:
        candidates.append({"component_id": component["component_id"], **coordinate_window(component["original_component_feature"]["geometry"], window)})
        for row in component["source_feature_intersections"]:
            source_id = f"gb:{row['country']}:ADM2:{row['shapeID']}"
            if source_id in subjects:
                contacts.append({"component_id": component["component_id"], "source_subject_id": source_id, "empty": row["intersection"]["empty"], **(coordinate_window(row["intersection"]["geometry"], window) or {"columns": 0, "rows": 0, "coordinate_count": 0})})
    for feature in data["original_contact_fragment_features"]:
        fragments.append({"fragment_id": feature["id"], **(coordinate_window(feature["geometry"], window) or {"columns": 0, "rows": 0, "coordinate_count": 0})})
    all_rows = [*candidates, *contacts, *fragments]
    return {
        "basis": "pinned original comparison geometry coordinates and exact classifier envelope formula; no raster pixel values read",
        "complete_candidate_count": len(candidates),
        "local_contact_intersection_count": len(contacts),
        "original_contact_fragment_count": len(fragments),
        "maximum_candidate_row_width_cells": max(row["columns"] for row in candidates),
        "maximum_candidate_window_rows": max(row["rows"] for row in candidates),
        "maximum_local_contact_row_width_cells": max(row["columns"] for row in contacts),
        "maximum_local_contact_window_rows": max(row["rows"] for row in contacts),
        "maximum_all_geometry_row_width_cells": max(row["columns"] for row in all_rows),
        "maximum_all_geometry_window_rows": max(row["rows"] for row in all_rows),
        "source_window_width_cells": window["dimensions"][0],
        "candidates": candidates,
        "local_contact_intersections": contacts,
        "point_contact_fragments": fragments,
    }


def main() -> None:
    range_manifest = json.loads((BASE / "worldcover-source-ranges.json").read_text(encoding="utf-8"))
    geometry_bytes = (PACKET / "run-one/source-geometry-results.json.gz").read_bytes()
    row_admission = geometry_row_admission(geometry_bytes, range_manifest)
    range_files = [BASE / row["file"] for row in [range_manifest["ifd_metadata_range"], *range_manifest["blocks"]]]
    named = [
        PACKET / "run-one/source-geometry-results.json.gz",
        PACKET / "run-two/source-geometry-results.json.gz",
        PACKET / "source-provenance.json",
        PACKET / "reproducibility.json",
        BASE / "worldcover-source-ranges.json",
        BASE / "worldcover-range-integrity.json",
        BASE / "source-coverage.json",
        BASE / "classification-memory-admission.json",
        BASE / "sources/WorldCover_PUM_V2.0.pdf",
        BASE / "sources/WorldCover_PUM_V2.0.headers",
        BASE / "sources/WorldCover_PVR_V2.0.pdf",
        BASE / "sources/WorldCover_PVR_V2.0.headers",
        BASE / "sources/esa-worldcover-data-access.html",
        BASE / "sources/esa-worldcover-data-access.headers",
    ]
    inputs = [descriptor(path) for path in [*named, *range_files]]
    inputs.sort(key=lambda item: item["path"])
    unique = {item["path"] for item in inputs}
    if len(unique) != len(inputs):
        raise RuntimeError("Duplicate frozen input path")
    input_bytes = sum(item["bytes"] for item in inputs)
    storage_snapshot = json.loads((BASE / "workspace-storage-admission.json").read_text(encoding="utf-8"))
    producer_hashes = {name: digest(BASE / name) for name in ["classify_worldcover.py", "verify_worldcover_ranges.py", "verify_source_coverage.py", "verify_classification_runs.py", "inspect_classification_allocations.py", "supervise_classification.py", "freeze_inputs.py", "record_workspace_storage.mjs"]}
    runtime_body_total = 9_901_207 + 18_058_560 + 352_048 + 3_258_528 + 2_289_328
    producer_bytes = sum((BASE / name).stat().st_size for name in producer_hashes)
    static_phase_sum = input_bytes + range_manifest["selected_decoded_bytes"] + 932_627 + runtime_body_total + producer_bytes + 67_108_864
    remaining_phase_budget = 256 * 1024 * 1024 - static_phase_sum

    packet_id = "research/geography/gap-source-zambia-zimbabwe-shared-seams-20261006"
    report = {
        "version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "issue": 1234,
        "classification_source": "ESA WorldCover 2021 v200 (2021 product vintage)",
        "geometry_baseline": "79ffb2ed04702e16f009e4675a8d74ef9bd09d4f",
        "source_comparison_vintage": "cea80a8aa1f8a55ccb448a8f2ff71e10c49a26f1",
        "author_branch_base_commit": "6a1c3b5410587289285f31809312792f0f085e87",
        "input_files": inputs,
        "input_file_count": len(inputs),
        "input_bytes": input_bytes,
        "retained_worldcover_range_bytes": range_manifest["selected_encoded_bytes"] + range_manifest["ifd_metadata_range"]["content_length"],
        "worldcover_selected_decoded_block_capacity_bytes": range_manifest["selected_decoded_bytes"],
        "worldcover_issue_pixel_window_bytes": range_manifest["complete_pixel_window"]["decoded_bytes"],
        "geometry_row_admission": row_admission,
        "runtime": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "numpy": numpy.__version__,
            "shapely": shapely.__version__,
            "geos": shapely.geos_version_string,
            "zlib_compile": zlib.ZLIB_VERSION,
            "zlib_runtime": zlib.ZLIB_RUNTIME_VERSION,
            "pypdf": importlib.metadata.version("pypdf"),
        },
        "producer_and_checker_hashes": producer_hashes,
        "storage_snapshot": storage_snapshot,
        "resource_admission": {
            "gis_window_requested_mib": 768,
            "process_abort_threshold_mib": 700,
            "expected_peak_rss_mib": 256,
            "max_result_bytes_total_both_runs": 134_217_728,
            "temporary_storage_cap_bytes": 67_108_864,
            "source_input_bytes": input_bytes,
            "no_full_cog_download": True,
            "pixel_decode_runs": 2,
            "per_run_full_block_decode_capacity_bytes": range_manifest["selected_decoded_bytes"],
            "geometry_partition": "bounded per candidate and per source row; no raster-wide in-memory array",
            "measurement": "Use supervise_classification.py after explicit root window authorization. It samples process-group RSS and system free memory every 250 ms, stops at 640 MiB to retain 60 MiB below the producer's unchanged 700 MiB abort, enforces the unchanged 40% host-free gate and authorized wall-time, and records JSONL/stdout/stderr/summary logs with a 1 MiB per producer log-file limit. The report explicitly discloses sampler latency/overshoot. Keep existing 32 MiB ordinary-file, 64 MiB per-run, 128 MiB paired-output, 256 MiB phase-accounting, and storage caps.",
        },
        "measured_preflight": {
            "scope": "No-pixel preflight only; this does not authorize or measure a GIS classification run.",
            "command": "bundled Python 3.12.14 classify_worldcover.py --preflight-only under /usr/bin/time -l",
            "result": "passed",
            "source_pixels_read": False,
            "elapsed_seconds": 0.20,
            "process_peak_rss_bytes": 47153152,
            "measured_at_utc": "2026-10-08T03:13:40Z",
            "pinned_project_input_files": len(inputs),
            "pinned_project_input_bytes": input_bytes,
            "owned_producer_and_checker_files": len(producer_hashes),
            "owned_producer_and_checker_bytes": sum((BASE / name).stat().st_size for name in producer_hashes),
            "loaded_runtime_module_files": 236,
            "loaded_runtime_module_file_bytes": 9901207,
            "python_executable_bytes": 18058560,
            "loaded_non_python_runtime_files": [
                {"path": "shapely/.dylibs/libgeos_c.1.19.2.dylib", "bytes": 352048},
                {"path": "shapely/.dylibs/libgeos.3.13.1.dylib", "bytes": 3258528},
                {"path": "/usr/lib/dyld", "bytes": 2289328},
            ],
            "measured_runtime_body_total_bytes": runtime_body_total,
            "measured_runtime_body_formula": "9,901,207 loaded Python module files + 18,058,560 Python executable + 3,610,576 GEOS dylibs + 2,289,328 macOS dyld",
            "held_preflight_vmmap_physical_footprint": "24.9 MiB",
            "preflight_open_descriptor_count_including_stdio": 3,
            "runtime_body_measurement_note": "Module and executable byte counts were measured in a second preflight-only process using the same bundled runtime and entry point. GEOS dylibs and dyld were inventoried from vmmap/lsof on a held preflight-only process; that process had three open stdio descriptors. macOS system frameworks are shared OS libraries, not project-copied runtime bodies; observed process RSS/physical footprint captures their actual process cost.",
            "per_classification_run_encoded_source_bytes": range_manifest["selected_encoded_bytes"] + range_manifest["ifd_metadata_range"]["content_length"],
            "per_classification_run_decoded_original_block_capacity_bytes": range_manifest["selected_decoded_bytes"],
            "per_classification_run_geometry_compressed_bytes": (PACKET / "run-one/source-geometry-results.json.gz").stat().st_size,
            "per_classification_run_geometry_decoded_bytes": 932627,
            "largest_retained_encoded_tiff_block_bytes": max(row["encoded_bytes"] for row in range_manifest["blocks"]),
            "per_run_maximum_ordinary_output_file_bytes": 33554432,
            "per_run_total_output_cap_bytes_including_receipt": 67108864,
            "two_run_total_output_cap_bytes": 134217728,
            "prospective_one_run_static_phase_sum_bytes": static_phase_sum,
            "prospective_one_run_static_phase_sum_formula": f"{input_bytes} pinned inputs + {range_manifest['selected_decoded_bytes']} decoded original blocks + 932627 decoded comparison geometry + {runtime_body_total} measured runtime bodies incl. GEOS/dyld + {producer_bytes} owned producer/checker bytes + 67108864 result-bundle/receipt cap",
            "expected_peak_rss_budget_mib": 256,
            "remaining_256_mib_budget_for_live_row_geometry_and_allocator_overhead_bytes": remaining_phase_budget,
            "phase_sum_note": "The exact static phase sum leaves the recorded remaining allowance for row-wise GEOS/NumPy geometry intermediates and allocator overhead. Classification RSS remains unmeasured and must be checked live against the 700 MiB abort before and during both authorized runs.",
            "issue_window_pixel_bytes_theoretical_only": range_manifest["complete_pixel_window"]["decoded_bytes"],
            "raster_crop_files_or_crop_intermediates": 0,
            "crop_handling": "No 47,518,164-byte crop file is created. The producer decodes the 60 pinned original TIFF blocks and uses row-bounded candidate/cell intersections; no raster-wide crop array is materialized.",
            "per_run_result_output_cap_bytes": 67108864,
            "two_run_result_output_cap_bytes": 134217728,
            "planned_temporary_file_bytes": 0,
            "storage_snapshot": storage_snapshot,
            "classification_peak_rss": "not yet measured; only eligible after explicit GIS-window authorization; stop above 700 MiB",
        },
        "limits": [
            "The acquisition and comparison outputs are pinned as exact files; the original complete geoBoundaries source comparisons remain in both prior runs and are not replaced.",
            "The product COG reports a multipart ETag; no whole-object SHA-256 is claimed.",
            "Source class evidence does not establish candidate-specific accuracy, legal shoreline, political ownership, or processing cause.",
            "This manifest is a pre-execution input/runtime/storage admission; measured actual runtime/RSS/output are added only after the authorized GIS executions.",
        ],
    }
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"frozen_input_files": len(inputs), "input_bytes": input_bytes, "worldcover_range_bytes": report["retained_worldcover_range_bytes"], "decoded_selected_block_capacity_bytes": report["worldcover_selected_decoded_block_capacity_bytes"], "window_pixel_bytes": report["worldcover_issue_pixel_window_bytes"], "gis_window_requested_mib": 768, "expected_peak_rss_mib": 256, "result_cap_bytes_both_runs": 134217728, "manifest": str(OUTPUT)}, indent=2))


if __name__ == "__main__":
    main()
