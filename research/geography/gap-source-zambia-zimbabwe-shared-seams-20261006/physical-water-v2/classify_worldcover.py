#!/usr/bin/env python3
"""Split the ten original candidate polygons by retained WorldCover cells.

The default mode performs actual source decoding and spatial classification.
Use --controls-only for the tiny synthetic positive/adverse controls; this mode
does not read or decode any WorldCover pixel blocks.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import resource
import sys
import tempfile
import zlib
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import shapely
from shapely import area, box, intersection, intersects, symmetric_difference, union_all
from shapely.geometry import mapping, shape
from acquire_worldcover_window import assert_source_metadata


BASE = Path(__file__).resolve().parent
PACKET = BASE.parent
RANGE_MANIFEST = BASE / "worldcover-source-ranges.json"
GEOMETRY_ONE = PACKET / "run-one/source-geometry-results.json.gz"
GEOMETRY_TWO = PACKET / "run-two/source-geometry-results.json.gz"
OUTPUT_DIR = BASE / "RUN_NAME"
ORIGIN_X, ORIGIN_Y = 27.0, -15.0
PIXEL = 1 / 12_000
BLOCK = 1_024
TILE_COLS = 36
WATER = 80
WETLAND = 90
CLASS_NAMES = {
    10: "Tree cover", 20: "Shrubland", 30: "Grassland", 40: "Cropland",
    50: "Built-up", 60: "Bare or sparse vegetation", 70: "Snow and ice",
    80: "Permanent water bodies", 90: "Herbaceous wetland", 95: "Mangroves",
    100: "Moss and lichen",
}
LAND_CODES = set(CLASS_NAMES) - {WATER, WETLAND}
MAX_RSS_MIB = 700
MAX_ONE_FILE_BYTES = 32 * 1024 * 1024
MAX_ONE_RUN_OUTPUT_BYTES = 64 * 1024 * 1024
MAX_BOTH_RUN_OUTPUT_BYTES = 128 * 1024 * 1024


def peak_rss_mib() -> float:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value / (1024 * 1024) if sys.platform == "darwin" else value / 1024


def enforce_peak_rss():
    observed = peak_rss_mib()
    if observed > MAX_RSS_MIB:
        raise MemoryError(f"Process peak RSS exceeded the 700 MiB admission: {observed:.1f} MiB")


def validate_frozen_inputs():
    path = BASE / "frozen-inputs.json"
    frozen_bytes = path.read_bytes()
    frozen = json.loads(frozen_bytes)
    repo = BASE.parents[3]
    for row in frozen["input_files"]:
        source_path = (repo / row["path"]).resolve()
        if not source_path.is_relative_to(repo.resolve()) or not source_path.is_file():
            raise RuntimeError(f"Frozen input path is missing or escapes the repository: {row['path']}")
        data = source_path.read_bytes()
        if len(data) != row["bytes"] or sha256(data) != row["sha256"]:
            raise RuntimeError(f"Frozen input bytes changed: {row['path']}")
    for name, expected in frozen["producer_and_checker_hashes"].items():
        if sha256((BASE / name).read_bytes()) != expected:
            raise RuntimeError(f"Producer/checker code differs from frozen hash: {name}")
    runtime = frozen["runtime"]
    observed = {"python": sys.version.split()[0], "numpy": np.__version__, "shapely": shapely.__version__, "geos": shapely.geos_version_string, "zlib_compile": zlib.ZLIB_VERSION, "zlib_runtime": zlib.ZLIB_RUNTIME_VERSION}
    for name, value in observed.items():
        if runtime[name] != value:
            raise RuntimeError(f"Runtime differs from frozen value for {name}: {value} != {runtime[name]}")
    enforce_peak_rss()
    return frozen_bytes, frozen


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def category(code: int) -> str:
    if code == WATER:
        return "mapped-permanent-water"
    if code == WETLAND:
        return "mapped-herbaceous-wetland-water-status-unresolved"
    if code in LAND_CODES:
        return "mapped-nonwater-land-cover"
    return "unclassified-unresolved"


def coord_window(geom, complete_window):
    min_x, min_y, max_x, max_y = geom.bounds
    col_min, col_max = complete_window["columns_half_open"]
    row_min, row_max = complete_window["rows_half_open"]
    c0 = max(col_min, math.floor((min_x - ORIGIN_X) / PIXEL) - 1)
    c1 = min(col_max, math.ceil((max_x - ORIGIN_X) / PIXEL) + 1)
    r0 = max(row_min, math.floor((ORIGIN_Y - max_y) / PIXEL) - 1)
    r1 = min(row_max, math.ceil((ORIGIN_Y - min_y) / PIXEL) + 1)
    return c0, c1, r0, r1


def partition_geometry(geom, window, get_values, *, grid_origin=(ORIGIN_X, ORIGIN_Y), pixel_scale=PIXEL):
    """Return per-class clipped cell unions and touched-cell counts.

    Every positive-area candidate/cell intersection is retained. A map cell's
    source class is assigned to its exact clipped portion of the candidate.
    Geometries remain in longitude/latitude; areas are only algebraic closure
    checks and are never interpreted as physical area.
    """
    c0, c1, r0, r1 = window
    classes_by_row: dict[int, list] = defaultdict(list)
    counts: Counter[int] = Counter()
    origin_x, origin_y = grid_origin
    columns = np.arange(c0, c1, dtype=np.int32)
    lefts = origin_x + columns * pixel_scale
    rights = lefts + pixel_scale
    for row in range(r0, r1):
        top = origin_y - row * pixel_scale
        bottom = top - pixel_scale
        cells = box(lefts, bottom, rights, top)
        has_intersection = intersects(geom, cells)
        if not np.any(has_intersection):
            continue
        cols = columns[has_intersection]
        pieces = intersection(geom, cells[has_intersection])
        positive = area(pieces) > 0.0
        if not np.any(positive):
            continue
        cols = cols[positive]
        pieces = pieces[positive]
        codes = get_values(row, cols)
        for code in np.unique(codes):
            code_int = int(code)
            selected = codes == code
            counts[code_int] += int(np.count_nonzero(selected))
            classes_by_row[code_int].append(union_all(pieces[selected]))

    portions = {}
    for code in sorted(classes_by_row):
        portions[code] = union_all(classes_by_row[code])
    combined = union_all(list(portions.values())) if portions else shapely.GeometryCollection()
    residual = symmetric_difference(geom, combined)
    original_area = float(area(geom))
    residual_area = float(area(residual))
    tolerance = max(original_area * 1e-10, 1e-14)
    if residual_area > tolerance:
        raise RuntimeError(f"Candidate-to-source-cell partition left a residual: {residual_area} > {tolerance}")
    if any(not geom.is_valid for geom in portions.values()):
        raise RuntimeError("A class portion is invalid; no repair is permitted")
    return portions, counts, {"candidate_degree_square_area_for_closure_only": original_area, "symmetric_difference_degree_square_area": residual_area, "closure_tolerance_degree_square": tolerance}


def synthetic_controls() -> dict:
    """Nonvacuous positive, adverse and mutation checks on a 2x2 synthetic grid."""
    synthetic_origin = (27.0, -15.0)
    one = PIXEL
    values = np.array([[80, 40], [90, 0]], dtype=np.uint8)
    candidate = box(synthetic_origin[0] + 0.2 * one, synthetic_origin[1] - 1.9 * one, synthetic_origin[0] + 1.8 * one, synthetic_origin[1] - 0.1 * one)
    get_synthetic_values = lambda row, cols: values[row, cols]
    partitions, counts, _ = partition_geometry(candidate, (0, 2, 0, 2), get_synthetic_values, grid_origin=synthetic_origin, pixel_scale=one)
    expected_counts = {80: 1, 40: 1, 90: 1, 0: 1}
    if dict(counts) != expected_counts:
        raise RuntimeError(f"Synthetic positive/adverse class control failed: {dict(counts)}")
    if abs(sum(float(area(g)) for g in partitions.values()) - float(area(candidate))) > 1e-12:
        raise RuntimeError("Synthetic class partition does not close")
    if category(80) != "mapped-permanent-water" or category(40) != "mapped-nonwater-land-cover":
        raise RuntimeError("Water/land positive controls were misclassified")
    if category(90) != "mapped-herbaceous-wetland-water-status-unresolved" or category(0) != "unclassified-unresolved":
        raise RuntimeError("Wetland/nodata adverse controls were misclassified")
    mutated = values.copy()
    mutated[0, 0] = 30
    mutated_parts, mutated_counts, _ = partition_geometry(candidate, (0, 2, 0, 2), lambda row, cols: mutated[row, cols], grid_origin=synthetic_origin, pixel_scale=one)
    if 80 in mutated_parts or 30 not in mutated_parts or mutated_counts.get(30) != 1:
        raise RuntimeError("Mutation control did not reject a water-to-land class flip")
    return {
        "result": "passed",
        "grid_shape": [2, 2],
        "candidate_coverage": "all four cells have positive-area intersections; exact clipped portions close",
        "positive_controls": {"class_80": {"category": category(80), "cells": 1}, "class_40": {"category": category(40), "cells": 1}},
        "adverse_controls": {"class_90": {"category": category(90), "cells": 1}, "class_0": {"category": category(0), "cells": 1}},
        "mutation_control": {"input_change": "single class-80 cell changed to class 30", "expected": "water evidence decreases and mapped-land class increases", "result": "passed"},
        "source_pixels_read": False,
    }


def serialize_result_bundle(result: dict) -> dict[str, bytes]:
    """Serialize complete record arrays as independently bounded JSON shards."""
    index = {key: value for key, value in result.items() if key not in {"component_results"}}
    index["scope"] = {key: value for key, value in result.get("scope", {}).items() if key != "point_contact_fragments"}
    index["output_layout"] = "worldcover-classification-index-v1; component and point-contact-fragment records are in ordered JSON shards listed in this index"
    payloads: dict[str, bytes] = {}
    shard_sets = {
        "component_result_shards": ("component-results", "component-result", result.get("component_results", [])),
        "point_contact_fragment_shards": ("contact-fragments", "point-contact-fragment", result.get("scope", {}).get("point_contact_fragments", [])),
    }
    for field, (directory, record_type, records) in shard_sets.items():
        descriptors = []
        for position, record in enumerate(records, start=1):
            relative_path = f"{directory}/{position:04d}.json"
            raw = (json.dumps({"version": 1, "record_type": record_type, "record": record}, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
            payloads[relative_path] = raw
            descriptors.append({"path": relative_path, "bytes": len(raw), "sha256": sha256(raw)})
        index[field] = descriptors
    index["component_result_count"] = len(result.get("component_results", []))
    index["point_contact_fragment_count"] = len(result.get("scope", {}).get("point_contact_fragments", []))
    index_raw = (json.dumps(index, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    payloads["worldcover-classification-index.json"] = index_raw
    return payloads


def write_result_bundle(result: dict, output_dir: Path, run_name: str, *, existing_output_bytes: int = 0, file_limit_bytes: int = MAX_ONE_FILE_BYTES, run_limit_bytes: int = MAX_ONE_RUN_OUTPUT_BYTES, pair_limit_bytes: int = MAX_BOTH_RUN_OUTPUT_BYTES, producer_sha256: str | None = None) -> dict:
    """Validate every ordinary-file and aggregate bound before creating output."""
    if output_dir.exists():
        raise RuntimeError(f"output already exists; preserve it and inspect: {output_dir}")
    payloads = serialize_result_bundle(result)
    for relative_path, raw in payloads.items():
        if len(raw) > file_limit_bytes:
            raise RuntimeError(f"Ordinary output file exceeds the {file_limit_bytes}-byte cap before write: {relative_path} ({len(raw)} bytes)")
    receipt = {
        "version": 1,
        "run": run_name,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "result_index_file": "worldcover-classification-index.json",
        "result_index_sha256": sha256(payloads["worldcover-classification-index.json"]),
        "result_files": [{"path": name, "bytes": len(raw), "sha256": sha256(raw)} for name, raw in sorted(payloads.items())],
        "result_file_count": len(payloads),
        "result_bytes": sum(map(len, payloads.values())),
        "producer_sha256": producer_sha256 or sha256(Path(__file__).read_bytes()),
        "selected_original_block_count": result["selected_original_blocks_loaded"],
        "selected_original_block_decoded_bytes": result["selected_original_blocks_decoded_bytes"],
        "components": len(result["component_results"]),
        "controls": result["synthetic_controls"]["result"],
        "process_peak_rss_mib": round(peak_rss_mib(), 1),
    }
    receipt["bundle_bytes_including_receipt"] = 0
    for _ in range(4):
        receipt_raw = (json.dumps(receipt, indent=2) + "\n").encode("utf-8")
        bundle_bytes = sum(map(len, payloads.values())) + len(receipt_raw)
        if receipt["bundle_bytes_including_receipt"] == bundle_bytes:
            break
        receipt["bundle_bytes_including_receipt"] = bundle_bytes
    receipt_raw = (json.dumps(receipt, indent=2) + "\n").encode("utf-8")
    bundle_bytes = sum(map(len, payloads.values())) + len(receipt_raw)
    if receipt["bundle_bytes_including_receipt"] != bundle_bytes:
        raise RuntimeError("Could not stabilize the exact receipt-inclusive output byte count")
    if len(receipt_raw) > file_limit_bytes:
        raise RuntimeError(f"Execution receipt exceeds the {file_limit_bytes}-byte cap before write")
    bundle_bytes = sum(map(len, payloads.values())) + len(receipt_raw)
    if bundle_bytes > run_limit_bytes:
        raise RuntimeError(f"Run output exceeds the {run_limit_bytes}-byte cap before write: {bundle_bytes}")
    if existing_output_bytes + bundle_bytes > pair_limit_bytes:
        raise RuntimeError(f"Combined two-run output exceeds the {pair_limit_bytes}-byte cap before write")

    output_dir.mkdir(parents=True, exist_ok=False)
    for relative_path, raw in payloads.items():
        target = output_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    (output_dir / "execution-receipt.json").write_bytes(receipt_raw)
    return receipt


def output_writer_controls() -> dict:
    """Exercise real shard writing, receipt paths, bounds, and no-overwrite behavior."""
    synthetic = {
        "selected_original_blocks_loaded": 0,
        "selected_original_blocks_decoded_bytes": 0,
        "synthetic_controls": {"result": "passed"},
        "component_results": [{"component_id": "synthetic-component", "class_portions": [{"class_code": 80, "coordinates": [[1, 2]]}]}],
        "scope": {"point_contact_fragments": [{"fragment_id": "synthetic-contact", "classification_status": "nonareal"}]},
    }
    with tempfile.TemporaryDirectory(prefix="worldcover-output-controls-") as temporary:
        output_dir = Path(temporary) / "run-one"
        receipt = write_result_bundle(synthetic, output_dir, "one", producer_sha256="0" * 64)
        index_path = output_dir / receipt["result_index_file"]
        if not index_path.is_file() or sha256(index_path.read_bytes()) != receipt["result_index_sha256"]:
            raise RuntimeError("Output-writer control failed to bind the index path and bytes")
        index = json.loads(index_path.read_text(encoding="utf-8"))
        disk_receipt = json.loads((output_dir / "execution-receipt.json").read_text(encoding="utf-8"))
        component = json.loads((output_dir / index["component_result_shards"][0]["path"]).read_text(encoding="utf-8"))
        fragment = json.loads((output_dir / index["point_contact_fragment_shards"][0]["path"]).read_text(encoding="utf-8"))
        if component["record"] != synthetic["component_results"][0] or fragment["record"] != synthetic["scope"]["point_contact_fragments"][0]:
            raise RuntimeError("Output-writer control failed to preserve component or contact records")
        for descriptor in disk_receipt["result_files"]:
            raw = (output_dir / descriptor["path"]).read_bytes()
            if len(raw) != descriptor["bytes"] or sha256(raw) != descriptor["sha256"]:
                raise RuntimeError("Output-writer control failed to verify a receipt file path/hash")
        actual_bundle_bytes = sum(path.stat().st_size for path in output_dir.rglob("*") if path.is_file())
        if actual_bundle_bytes != disk_receipt["bundle_bytes_including_receipt"]:
            raise RuntimeError("Output-writer control reported an incorrect receipt-inclusive byte count")
        if any(path.stat().st_size > MAX_ONE_FILE_BYTES for path in output_dir.rglob("*") if path.is_file()):
            raise RuntimeError("Output-writer control exceeded the ordinary-file cap")
        before = {str(path.relative_to(output_dir)): sha256(path.read_bytes()) for path in output_dir.rglob("*") if path.is_file()}
        try:
            write_result_bundle(synthetic, output_dir, "one", producer_sha256="0" * 64)
        except RuntimeError as error:
            if "already exists" not in str(error):
                raise
        else:
            raise RuntimeError("Output-writer control overwrote a non-fresh output directory")
        after = {str(path.relative_to(output_dir)): sha256(path.read_bytes()) for path in output_dir.rglob("*") if path.is_file()}
        if before != after:
            raise RuntimeError("Output-writer control changed existing output after fresh-directory rejection")
        rejected_dir = Path(temporary) / "oversize"
        try:
            write_result_bundle(synthetic, rejected_dir, "one", file_limit_bytes=64, producer_sha256="0" * 64)
        except RuntimeError as error:
            if "before write" not in str(error) or rejected_dir.exists():
                raise RuntimeError("Output-writer control did not reject oversized files before writing") from error
        else:
            raise RuntimeError("Output-writer control accepted an oversized ordinary file")
        for name, bounds in [("run-cap", {"run_limit_bytes": 64}), ("pair-cap", {"pair_limit_bytes": 64})]:
            rejected_cap_dir = Path(temporary) / name
            try:
                write_result_bundle(synthetic, rejected_cap_dir, "one", producer_sha256="0" * 64, **bounds)
            except RuntimeError as error:
                if "before write" not in str(error) or rejected_cap_dir.exists():
                    raise RuntimeError(f"Output-writer control did not enforce the {name} before writing") from error
            else:
                raise RuntimeError(f"Output-writer control accepted the {name}")
    return {"result": "passed", "complete_component_and_fragment_records_sharded": True, "index_receipt_paths_and_hashes": "passed", "ordinary_file_cap_bytes": MAX_ONE_FILE_BYTES, "oversize_rejected_before_write": True, "run_cap_rejected_before_write": True, "pair_cap_rejected_before_write": True, "fresh_output_directory_required": True, "existing_output_preserved": True}


def load_source():
    manifest_bytes = RANGE_MANIFEST.read_bytes()
    manifest = json.loads(manifest_bytes)
    source = manifest["source"]
    if manifest["head_before"] != manifest["head_after"]:
        raise RuntimeError("WorldCover object metadata differs across recorded acquisition")
    if source["whole_object_sha256"] is not None:
        raise RuntimeError("Whole-object digest must remain unknown for multipart ETag")
    if manifest["selected_block_count"] != 60:
        raise RuntimeError("Expected 60 retained original COG blocks")
    if manifest["head_before"] != manifest["head_after"] or source["etag"] != manifest["head_before"]["etag"]:
        raise RuntimeError("Range manifest source metadata does not match the stable HEAD records")

    ifd_record = manifest["ifd_metadata_range"]
    ifd_path = BASE / ifd_record["file"]
    ifd_bytes = ifd_path.read_bytes()
    if len(ifd_bytes) != ifd_record["content_length"] or sha256(ifd_bytes) != ifd_record["sha256"]:
        raise RuntimeError("Retained TIFF IFD bytes differ from range receipt")
    tiff = assert_source_metadata(ifd_bytes)
    if sha256(tiff["metadata_xml"].encode("ascii")) != source["metadata_xml_sha256"]:
        raise RuntimeError("TIFF embedded product metadata differs from the pinned source manifest")

    block_rows = {b["tile_row"] for b in manifest["blocks"]}
    block_cols = {b["tile_column"] for b in manifest["blocks"]}
    block_by_id = {(b["tile_row"], b["tile_column"]): b for b in manifest["blocks"]}
    if block_rows != set(range(7, 13)) or block_cols != set(range(21, 31)) or len(block_by_id) != 60:
        raise RuntimeError("Retained TIFF blocks do not form the expected complete issue window")

    cache: dict[tuple[int, int], np.ndarray] = {}
    for (tile_row, tile_col), record in block_by_id.items():
        row = record["http"]
        path = BASE / record["file"]
        data = path.read_bytes()
        if len(data) != record["encoded_bytes"] or sha256(data) != record["sha256"]:
            raise RuntimeError(f"Retained block bytes differ from manifest: {path.name}")
        if row["status"] != 206 or row["if_match"] != source["etag"] or row["etag"] != source["etag"]:
            raise RuntimeError(f"Range lacks exact conditional source binding: {path.name}")
        if len(data) != row["content_length"] or sha256(data) != row["sha256"]:
            raise RuntimeError(f"Block bytes differ from HTTP receipt: {path.name}")
        try:
            decoded = zlib.decompress(data)
        except zlib.error:
            decoded = zlib.decompress(data, -zlib.MAX_WBITS)
        if len(decoded) != BLOCK * BLOCK:
            raise RuntimeError(f"Unexpected decoded block length for {path.name}: {len(decoded)}")
        cache[(tile_row, tile_col)] = np.frombuffer(decoded, dtype=np.uint8).reshape((BLOCK, BLOCK))
        enforce_peak_rss()

    def get_values(row: int, columns: np.ndarray) -> np.ndarray:
        tile_row, local_row = divmod(row, BLOCK)
        values = np.empty(len(columns), dtype=np.uint8)
        tile_columns = columns // BLOCK
        for tile_col in np.unique(tile_columns):
            selected = np.flatnonzero(tile_columns == tile_col)
            values[selected] = cache[(tile_row, int(tile_col))][local_row, columns[selected] % BLOCK]
        return values

    return manifest, manifest_bytes, source, cache, get_values, sha256(ifd_bytes)


def build_result(run_name: str) -> dict:
    controls = synthetic_controls()
    frozen_bytes, frozen = validate_frozen_inputs()
    manifest, range_bytes, source, cache, get_values, ifd_hash = load_source()
    g1_bytes, g2_bytes = GEOMETRY_ONE.read_bytes(), GEOMETRY_TWO.read_bytes()
    g1_hash, g2_hash = sha256(g1_bytes), sha256(g2_bytes)
    if g1_hash != g2_hash:
        raise RuntimeError("The two preserved complete source-comparison runs differ in their candidate geometry evidence")
    decoded_geometry_bytes = gzip.decompress(g1_bytes)
    data = json.loads(decoded_geometry_bytes)
    if len(data["components"]) != 10 or len(data["component_ids"]) != 10 or len(data["subject_ids"]) != 4:
        raise RuntimeError("Candidate or contact roster changed from original #1234 scope")
    coverage_bytes = (BASE / "source-coverage.json").read_bytes()
    coverage = json.loads(coverage_bytes)
    if coverage["result"] != "complete candidate footprints and local contact geometries are within the retained source window":
        raise RuntimeError("Complete candidate/contact coverage proof is missing or failed")
    if coverage["complete_components"]["ids"] != sorted(data["component_ids"]):
        raise RuntimeError("Coverage proof does not bind the complete original candidate roster")
    if coverage["contact_subjects"]["ids"] != sorted(data["subject_ids"]):
        raise RuntimeError("Coverage proof does not bind the four original contact subjects")
    range_meta = manifest["complete_pixel_window"]
    valid_class_counts: Counter[int] = Counter()
    results = []
    for item in data["components"]:
        component_id = item["component_id"]
        feature = item["original_component_feature"]
        geom_bytes = json.dumps(feature["geometry"], sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        geom = shape(feature["geometry"])
        if geom.is_empty or not geom.is_valid:
            raise RuntimeError(f"Original candidate geometry is empty or invalid: {component_id}")
        c0, c1, r0, r1 = coord_window(geom, range_meta)
        if c0 < range_meta["columns_half_open"][0] or c1 > range_meta["columns_half_open"][1] or r0 < range_meta["rows_half_open"][0] or r1 > range_meta["rows_half_open"][1]:
            raise RuntimeError(f"Candidate grid window escapes retained source selection: {component_id}")
        portions, class_counts, closure = partition_geometry(geom, (c0, c1, r0, r1), get_values)
        if not portions:
            raise RuntimeError(f"No positive-area map cells cover candidate: {component_id}")
        valid_class_counts.update(class_counts)
        portions_out = []
        for code in sorted(portions):
            portions_out.append({
                "class_code": code,
                "class_name": CLASS_NAMES.get(code, "Unrecognized / no-data value"),
                "category": category(code),
                "touched_positive_area_pixel_count": class_counts[code],
                "geometry": mapping(portions[code]),
            })
        classes = {category(code) for code in portions}
        has_water = "mapped-permanent-water" in classes
        has_land = "mapped-nonwater-land-cover" in classes
        summary = "mixed-mapped-water-and-land-cover" if has_water and has_land else "mapped-water-observed" if has_water else "mapped-land-cover-observed" if has_land else "unresolved-in-map-classes"
        results.append({
            "component_id": component_id,
            "original_geometry_sha256": sha256(geom_bytes),
            "original_geometry_type": feature["geometry"]["type"],
            "source_grid_window": {"columns_half_open": [c0, c1], "rows_half_open": [r0, r1]},
            "map_class_summary": summary,
            "class_portions": portions_out,
            "partition_closure": closure,
            "interpretation_limit": "The result describes ESA WorldCover 2021 v200 map classes only; wetland and unrecognized/no-data classes remain water-status unresolved, and the map alone does not prove physical shoreline, dry land, political ownership, source authority, or executed processing cause.",
        })
        enforce_peak_rss()
    expected_subjects = set(data["subject_ids"])
    local_contact_rows: dict[str, list] = {subject: [] for subject in expected_subjects}
    for item in data["components"]:
        component_id = item["component_id"]
        for row in item["source_feature_intersections"]:
            source_id = f"gb:{row['country']}:ADM2:{row['shapeID']}"
            if source_id not in expected_subjects:
                continue
            raw_geometry = row["intersection"]["geometry"]
            geometry_bytes = json.dumps(raw_geometry, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            geom = shape(raw_geometry)
            contact_result = {
                "component_id": component_id,
                "source_subject_id": source_id,
                "source_feature_sha256": row["source_feature_sha256"],
                "local_intersection_geometry_sha256": sha256(geometry_bytes),
                "geometry_type": raw_geometry["type"],
                "nonempty_source_intersection": row["intersection"]["empty"] is False,
            }
            if geom.is_empty or float(area(geom)) == 0.0:
                contact_result.update({"classification_status": "empty-or-nonareal-contact; raster classes do not resolve point/line contact"})
            else:
                if not geom.is_valid:
                    raise RuntimeError(f"Local contact intersection is invalid; no repair is permitted: {component_id}:{source_id}")
                c0, c1, r0, r1 = coord_window(geom, range_meta)
                if c0 < range_meta["columns_half_open"][0] or c1 > range_meta["columns_half_open"][1] or r0 < range_meta["rows_half_open"][0] or r1 > range_meta["rows_half_open"][1]:
                    raise RuntimeError(f"Local contact grid window escapes retained source selection: {component_id}:{source_id}")
                portions, class_counts, closure = partition_geometry(geom, (c0, c1, r0, r1), get_values)
                contact_result.update({
                    "classification_status": "local areal intersection split by mapped class",
                    "map_class_summary": "mixed-mapped-water-and-land-cover" if 80 in class_counts and bool(set(class_counts) & LAND_CODES) else "mapped-water-observed" if 80 in class_counts else "mapped-land-cover-observed" if set(class_counts) & LAND_CODES else "wetland-or-unclassified-only",
                    "class_portions": [{"class_code": code, "class_name": CLASS_NAMES.get(code, "Unrecognized / no-data value"), "category": category(code), "touched_positive_area_pixel_count": class_counts[code], "geometry": mapping(portions[code])} for code in sorted(portions)],
                    "partition_closure": closure,
                })
            local_contact_rows[source_id].append(contact_result)
            enforce_peak_rss()
    if any(not local_contact_rows[subject] for subject in expected_subjects):
        raise RuntimeError("One or more of the original four contact subjects has no local source-intersection evidence")
    point_row = data["original_source_contacts"]["matched_rows"]
    point_contact_evidence = []
    for row in point_row:
        raw_geometry = row["geometry"]
        geom = shape(raw_geometry)
        point_contact_evidence.append({
            "kind": row["kind"],
            "geometry_type": raw_geometry["type"],
            "geometry_sha256": sha256(json.dumps(raw_geometry, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")),
            "classification_status": "nonareal point contact; physical raster evidence does not determine which boundary model is correct" if float(area(geom)) == 0.0 else "areal fragment handled with candidate component classification",
        })
    contact_fragments = []
    for feature in data["original_contact_fragment_features"]:
        raw_geometry = feature["geometry"]
        geom = shape(raw_geometry)
        item = {"fragment_id": feature["id"], "geometry_type": raw_geometry["type"], "geometry_sha256": sha256(json.dumps(raw_geometry, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))}
        if geom.is_empty or float(area(geom)) == 0.0:
            item["classification_status"] = "empty-or-nonareal fragment; no areal class assignment"
        else:
            c0, c1, r0, r1 = coord_window(geom, range_meta)
            if c0 < range_meta["columns_half_open"][0] or c1 > range_meta["columns_half_open"][1] or r0 < range_meta["rows_half_open"][0] or r1 > range_meta["rows_half_open"][1]:
                raise RuntimeError(f"Point-contact fragment escapes retained source selection: {feature['id']}")
            portions, class_counts, closure = partition_geometry(geom, (c0, c1, r0, r1), get_values)
            item.update({
                "classification_status": "fragment area split by mapped class",
                "class_portions": [{"class_code": code, "class_name": CLASS_NAMES.get(code, "Unrecognized / no-data value"), "category": category(code), "touched_positive_area_pixel_count": class_counts[code], "geometry": mapping(portions[code])} for code in sorted(portions)],
                "partition_closure": closure,
            })
        contact_fragments.append(item)
        enforce_peak_rss()
    return {
        "version": 1,
        "method": "exact candidate polygon intersection with each positive-area overlapping source-grid cell; cell label assigned to the clipped candidate portion; CRS84 coordinate order (longitude, latitude); no transform, repair, snap, buffer, simplification, or nearest fill; all algebraic area values are used only for coverage closure",
        "source": {"id": source["id"], "url": source["url"], "period_utc": source["classification_period_utc"], "version": source["product_version"], "etag": source["etag"], "whole_object_bytes": source["whole_object_bytes"], "whole_object_sha256": None, "crs": source["crs"], "pixel_scale_degrees": source["pixel_scale_degrees"], "license": source["license"], "classes": {str(code): name for code, name in CLASS_NAMES.items()}},
        "scope": {"issue": 1234, "component_count": len(results), "component_ids": sorted(x["component_id"] for x in results), "contact_subject_ids": sorted(data["subject_ids"]), "contact_subject_full_geometries_classified": False, "local_source_intersections_per_contact_subject": {subject: local_contact_rows[subject] for subject in sorted(local_contact_rows)}, "point_only_contact_evidence": point_contact_evidence, "point_contact_fragments": contact_fragments, "contact_scope_note": "Each complete candidate and each local candidate/source intersection for all four contact subjects is checked. Areal local intersections and the two retained point-contact fragments are classified; zero-area point/line intersections remain unresolved. The full neighboring administrative polygons extend outside this window and are not claimed to be covered or classified."},
        "input_pins": {"frozen_inputs_sha256": sha256(frozen_bytes), "range_manifest_sha256": sha256(range_bytes), "tiff_ifd_range_sha256": ifd_hash, "source_coverage_sha256": sha256(coverage_bytes), "source_geometry_run_one_sha256": g1_hash, "source_geometry_run_two_sha256": g2_hash, "source_geometry_compressed_bytes_each": len(g1_bytes), "source_geometry_uncompressed_bytes": len(decoded_geometry_bytes), "source_geometry_uncompressed_sha256": sha256(decoded_geometry_bytes)},
        "synthetic_controls": controls,
        "selected_original_blocks_loaded": len(cache),
        "selected_original_blocks_decoded_bytes": sum(arr.nbytes for arr in cache.values()),
        "component_results": results,
        "aggregate_class_cell_counts": {str(k): valid_class_counts[k] for k in sorted(valid_class_counts)},
        "aggregate_class_categories": {category(k): sum(v for code, v in valid_class_counts.items() if category(code) == category(k)) for k in sorted(valid_class_counts)},
        "limits": ["Africa-level map accuracy is not a candidate-specific confidence measure.", "The WorldCover docs declare nominal 10 m grid spacing but no candidate-scale absolute registration tolerance.", "Map classes are land-cover observations, not a legal/dry-land or hydrological boundary record.", "Class 90 is wetland and remains separate from class 80 permanent water.", "The source is for 2021 and does not establish present-day conditions or legal boundary effects."],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--controls-only", action="store_true", help="run tiny synthetic controls without reading source pixel blocks")
    parser.add_argument("--preflight-only", action="store_true", help="verify all frozen input/code/runtime pins and synthetic controls without decoding source pixels")
    parser.add_argument("--run", choices=["one", "two"], help="write the actual result to run-one or run-two; omitted with --controls-only")
    args = parser.parse_args()
    if args.preflight_only:
        if args.controls_only or args.run:
            parser.error("--preflight-only cannot be combined with other modes")
        frozen_bytes, frozen = validate_frozen_inputs()
        controls = synthetic_controls()
        writer_controls = output_writer_controls()
        print(json.dumps({"result": "preflight passed", "frozen_manifest_sha256": sha256(frozen_bytes), "frozen_input_files": frozen["input_file_count"], "frozen_input_bytes": frozen["input_bytes"], "runtime": frozen["runtime"], "controls": controls["result"], "output_writer_controls": writer_controls, "source_pixels_read": False}, sort_keys=True, indent=2))
        return
    if args.controls_only:
        if args.run:
            parser.error("--run cannot be combined with --controls-only")
        print(json.dumps({"classification_controls": synthetic_controls(), "output_writer_controls": output_writer_controls()}, sort_keys=True, indent=2))
        return
    if not args.run:
        parser.error("actual classification requires --run one|two")
    output = BASE / f"run-{args.run}"
    result = build_result(args.run)
    other_name = "two" if args.run == "one" else "one"
    other_dir = BASE / f"run-{other_name}"
    existing_output_bytes = sum(path.stat().st_size for path in other_dir.rglob("*") if path.is_file()) if other_dir.is_dir() else 0
    enforce_peak_rss()
    receipt = write_result_bundle(result, output, args.run, existing_output_bytes=existing_output_bytes)
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
