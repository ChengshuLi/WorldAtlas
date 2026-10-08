#!/usr/bin/env python3
"""Measure exact input-geometry row operation counts without reading pixels."""

from __future__ import annotations

import gzip
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from shapely import area, box, intersection, intersects
from shapely.geometry import shape


BASE = Path(__file__).resolve().parent
PACKET = BASE.parent
OUTPUT = BASE / "classification-memory-admission.json"
PIXEL = 1 / 12_000
ORIGIN_X, ORIGIN_Y = 27.0, -15.0
CLASS_CODES = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def coord_window(geom, window: dict) -> tuple[int, int, int, int]:
    min_x, min_y, max_x, max_y = geom.bounds
    cmin, cmax = window["columns_half_open"]
    rmin, rmax = window["rows_half_open"]
    c0 = max(cmin, math.floor((min_x - ORIGIN_X) / PIXEL) - 1)
    c1 = min(cmax, math.ceil((max_x - ORIGIN_X) / PIXEL) + 1)
    r0 = max(rmin, math.floor((ORIGIN_Y - max_y) / PIXEL) - 1)
    r1 = min(rmax, math.ceil((ORIGIN_Y - min_y) / PIXEL) + 1)
    return c0, c1, r0, r1


def inspect_geometry(kind: str, identifier: str, raw_geometry: dict, window: dict) -> dict:
    geom = shape(raw_geometry)
    if geom.is_empty:
        return {"kind": kind, "id": identifier, "columns": 0, "rows": 0, "window_slots": 0,
                "max_intersecting_cells_in_row": 0, "max_positive_area_pieces_in_row": 0,
                "sum_intersecting_cell_events": 0, "sum_positive_area_pieces": 0}
    c0, c1, r0, r1 = coord_window(geom, window)
    columns = np.arange(c0, c1, dtype=np.int32)
    lefts = ORIGIN_X + columns * PIXEL
    rights = lefts + PIXEL
    max_hits = max_positive = total_hits = total_positive = 0
    max_hit_row = max_positive_row = None
    for row in range(r0, r1):
        top = ORIGIN_Y - row * PIXEL
        bottom = top - PIXEL
        cells = box(lefts, bottom, rights, top)
        hit = intersects(geom, cells)
        hit_count = int(np.count_nonzero(hit))
        total_hits += hit_count
        if hit_count == 0:
            continue
        pieces = intersection(geom, cells[hit])
        piece_areas = area(pieces)
        positive_count = int(np.count_nonzero(np.isfinite(piece_areas) & (piece_areas > 0.0)))
        total_positive += positive_count
        if hit_count > max_hits:
            max_hits, max_hit_row = hit_count, row
        if positive_count > max_positive:
            max_positive, max_positive_row = positive_count, row
    return {
        "kind": kind,
        "id": identifier,
        "columns": c1 - c0,
        "rows": r1 - r0,
        "window_slots": (c1 - c0) * (r1 - r0),
        "max_intersecting_cells_in_row": max_hits,
        "row_with_max_intersections": max_hit_row,
        "max_positive_area_pieces_in_row": max_positive,
        "row_with_max_positive_area_pieces": max_positive_row,
        "sum_intersecting_cell_events": total_hits,
        "sum_positive_area_pieces": total_positive,
    }


def main() -> None:
    range_path = BASE / "worldcover-source-ranges.json"
    range_bytes = range_path.read_bytes()
    range_manifest = json.loads(range_bytes)
    geometry_path = PACKET / "run-one/source-geometry-results.json.gz"
    geometry_bytes = geometry_path.read_bytes()
    geometry_json = gzip.decompress(geometry_bytes)
    data = json.loads(geometry_json)
    subjects = set(data["subject_ids"])
    rows = []
    window = range_manifest["complete_pixel_window"]
    for component in data["components"]:
        rows.append(inspect_geometry("candidate", component["component_id"], component["original_component_feature"]["geometry"], window))
        for intersection_row in component["source_feature_intersections"]:
            subject_id = f"gb:{intersection_row['country']}:ADM2:{intersection_row['shapeID']}"
            if subject_id in subjects:
                rows.append(inspect_geometry("local_contact", f"{component['component_id']}:{subject_id}", intersection_row["intersection"]["geometry"], window))
    for feature in data["original_contact_fragment_features"]:
        rows.append(inspect_geometry("point_fragment", feature["id"], feature["geometry"], window))

    counts = Counter(row["kind"] for row in rows)
    maxima = {}
    for kind in ("candidate", "local_contact", "point_fragment"):
        members = [row for row in rows if row["kind"] == kind]
        maxima[kind] = {
            "count": len(members),
            "max_envelope_width": max(row["columns"] for row in members),
            "max_envelope_rows": max(row["rows"] for row in members),
            "max_intersecting_cells_in_one_row": max(row["max_intersecting_cells_in_row"] for row in members),
            "max_positive_area_pieces_in_one_row": max(row["max_positive_area_pieces_in_row"] for row in members),
            "sum_positive_area_pieces_across_all_inputs": sum(row["sum_positive_area_pieces"] for row in members),
        }
    max_positive = max(rows, key=lambda row: row["max_positive_area_pieces_in_row"])
    blocks = range_manifest["blocks"]
    classification = {
        "version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "issue": 1234,
        "result": "geometry-only allocation inventory complete; raster values not read",
        "source_pixels_read": False,
        "method": "Apply the classifier's exact coordinate-window formula to the pinned full candidate/local-contact/fragment geometries, then vectorize the same cells/intersects/intersection/area calls row by row; no WorldCover values or compressed TIFF blocks are opened.",
        "input_pins": {
            "source_geometry_run_one_sha256": sha256(geometry_bytes),
            "source_geometry_run_one_bytes": len(geometry_bytes),
            "source_geometry_uncompressed_sha256": sha256(geometry_json),
            "source_geometry_uncompressed_bytes": len(geometry_json),
            "range_manifest_sha256": sha256(range_bytes),
            "component_count": len(data["components"]),
            "contact_subject_count": len(data["subject_ids"]),
            "local_contact_intersection_count": counts["local_contact"],
            "point_contact_fragment_count": counts["point_fragment"],
        },
        "exact_geometry_row_counts": {
            "all_partitioned_geometries": len(rows),
            "counts_by_kind": dict(counts),
            "sum_of_conservative_envelope_cell_slots": sum(row["window_slots"] for row in rows),
            "sum_of_actual_positive_area_piece_events": sum(row["sum_positive_area_pieces"] for row in rows),
            "maximum_positive_area_pieces_in_one_row": max_positive["max_positive_area_pieces_in_row"],
            "maximum_positive_row_record": max_positive,
            "per_kind": maxima,
            "records": rows,
        },
        "live_allocation_lifetimes": [
            {"stage": "frozen-input validation", "live": "one input file byte buffer at a time; SHA-256 and byte-count scan over 74 pinned files", "bound_or_measure": "11,652,764 total pinned disk bytes are not all simultaneously resident; one currently read file buffer is bounded by that file's on-disk size"},
            {"stage": "WorldCover source load", "live": "60 NumPy uint8 1024x1024 block views backed by retained decompressed Python bytes; manifest and IFD metadata; one encoded block and one decompression result transiently", "bound_or_measure": f"60 x 1,048,576 = {60*1024*1024:,} decoded payload bytes retained; 60 array headers/views plus Python bytes owners; largest encoded block {max(row['encoded_bytes'] for row in blocks):,} bytes; one decompression output 1,048,576 bytes"},
            {"stage": "geometry input load", "live": "both compressed run files, one decompressed JSON byte buffer, parsed JSON object tree, and source row records", "bound_or_measure": "compressed run-one and run-two inputs are each 329,369 bytes; decoded geometry input is 932,627 bytes; parsed Python object overhead depends on object/coordinate counts and is not represented by decoded-byte length"},
            {"stage": "single partition row", "live": "columns int32; left/right float64 arrays; GEOS cell boxes; intersects bools; selected columns; GEOS intersection objects; area float64 array; positive mask; selected piece pointer arrays; uint8 values and at most three block-column selection arrays", "bound_or_measure": f"width envelope max 1,536 columns; exact geometry sweep observed at most {max(row['max_intersecting_cells_in_row'] for row in rows)} intersecting cells and {max(row['max_positive_area_pieces_in_row'] for row in rows)} positive pieces in any row. Row pointer arrays and fixed NumPy vectors are small; GEOS per-object/native coordinate bytes are implementation/data dependent."},
            {"stage": "per-geometry accumulation", "live": "classes_by_row retains one GEOS union per unique uint8 value per row until all row unions are merged; final per-class portions coexist with row unions until partition_geometry returns", "bound_or_measure": f"Given uint8 inputs, the absolute code-level ceiling is min(256, positive pieces per row) unions per row; geometry-only maximum is {max(row['max_positive_area_pieces_in_row'] for row in rows)} pieces, up to {min(256, max(row['max_positive_area_pieces_in_row'] for row in rows))} row-unions. The actual number of class codes and GEOS vertex payloads depends on pixel values and cannot be measured without the authorized classification."},
            {"stage": "result accumulation and serialization", "live": "all 10 component results, 21 contact results, two contact-fragment records, mapping() Python coordinate lists, then all JSON shard byte buffers and index/receipt buffers", "bound_or_measure": "64 MiB per run / 128 MiB paired output are enforced on serialized bytes only after result geometries and all shard byte buffers have been materialized. Those output caps do not bound simultaneous Python/GEOS RSS."},
        ],
        "resource_accounting_distinctions": {
            "encoded_source_bytes": "4,074,286 compressed block bytes plus 131,072-byte IFD range are on-disk/authenticated acquisition bytes; block bytes are read one at a time during load_source, not retained together.",
            "decoded_block_bytes": f"{60*1024*1024:,} bytes are retained as the cache's 60 original 1024x1024 uint8 blocks; this is a real live payload floor after source load, not a whole-raster crop.",
            "phase_budget": "176,550,571-byte static phase sum is a conservative byte-accounting budget, not process RSS and not a measured live allocation bound.",
            "rss": "Only live process-group RSS sampling can include Python object overhead, GEOS allocations, allocator fragmentation, runtime pages, and output materialization; no preflight RSS value predicts those allocations exactly.",
        },
        "guard_recommendation": {
            "requested_window_mib": 768,
            "producer_abort_mib": 700,
            "supervisor_stop_mib": 640,
            "supervisory_margin_mib_below_producer_abort": 60,
            "host_free_gate_percent": 40,
            "poll_interval_seconds": 0.25,
            "maximum_bytes_per_producer_log": 1_048_576,
            "wall_time": "Must be supplied by root's window authorization; supervisor terminates the entire process group on expiry.",
            "sampling_limit": "250 ms is nominal cadence. OS scheduling, ps/memory_pressure latency, signal delivery, and file-size check timing are additional; a fast allocation spike can cross the soft or hard line between samples, and fast producer output can cross 1 MiB between log checks.",
        },
        "limits": [
            "The geometry row sweep performs Shapely/GEOS geometry operations but opens no WorldCover pixel values and does not classify any geography.",
            "No finite byte-exact peak RSS ceiling follows from the input geometry dimensions alone: GEOS object/native vertex storage and class-labeled result geometry complexity depend on pixel labels, and mapping plus serialization duplicates representation before output caps are checked.",
            "The producer's 700 MiB peak check is point-in-time at input-block and geometry-loop boundaries; the process-group supervisor adds 250 ms polling and the 640 MiB early-stop margin.",
        ],
    }
    OUTPUT.write_text(json.dumps(classification, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "result": classification["result"], "source_pixels_read": False,
                      "counts": dict(counts), "maximum_row_positive_pieces": max_positive["max_positive_area_pieces_in_row"],
                      "sum_positive_area_piece_events": classification["exact_geometry_row_counts"]["sum_of_actual_positive_area_piece_events"]}, indent=2))


if __name__ == "__main__":
    main()
