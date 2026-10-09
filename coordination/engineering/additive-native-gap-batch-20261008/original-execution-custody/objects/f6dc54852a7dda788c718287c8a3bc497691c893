#!/usr/bin/env python3
"""Stage 11 GSHHG records, publishing only after complete member validation."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import pathlib
import struct
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]
CAMPAIGN = ROOT / "research/geography/alaska-thirteen-geometry-measurement-20261008"
FIT = ROOT / "research/geography/alaska-thirteen-source-fitness-20261008/sources"
CUSTODY = ROOT / "coordination/engineering/gshhg-native-member-custody-20261007"
NATIVE = CUSTODY / "results"
SELECTED = CAMPAIGN / "sources/native-selected"
LIMIT = 268_435_456
HEADER = struct.Struct(">11i")


def digest(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def import_reader():
    path = CUSTODY / "reader.py"
    spec = importlib.util.spec_from_file_location("admitted_gshhg_reader", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load pinned native reader")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    start = time.monotonic()
    args = sys.argv[1:]
    destination = "native-selected"
    if args:
        if len(args) != 2 or args[0] != "--destination":
            raise SystemExit("usage: extract_native_records.py [--destination OWNED_RELATIVE_DIR]")
        destination = args[1]
    selected_dir = (CAMPAIGN / destination).resolve()
    if not selected_dir.is_relative_to(CAMPAIGN.resolve()) or selected_dir == CAMPAIGN.resolve():
        raise RuntimeError("selected record destination must remain inside the owned campaign")
    if destination.startswith(".scratch/") is False and destination != "sources/native-selected":
        raise RuntimeError("only the declared final or owned scratch destinations are allowed")
    phase = json.loads((CAMPAIGN / "phase-admission.json").read_text())
    if phase.get("status") != "PASS" or phase.get("complete_phase_bytes", LIMIT + 1) > LIMIT:
        raise RuntimeError("complete phase admission is absent or exceeds 256 MiB")
    if phase.get("scientific_operations_invoked") is not False:
        raise RuntimeError("phase admission must precede scientific execution")

    query_path = FIT / "gshhg-native-query-records.json"
    query_bytes = query_path.read_bytes()
    query = json.loads(query_bytes)
    rows = query["records"]
    if len(rows) != 11 or len({row["id"] for row in rows}) != 11:
        raise RuntimeError("expected the exact 11 unique referenced native records")
    rows.sort(key=lambda row: row["offset"])
    ranges = []
    for row in rows:
        start_at, size = row["offset"], row["record_bytes"]
        if not isinstance(start_at, int) or not isinstance(size, int) or size < 44:
            raise RuntimeError("invalid native record byte range")
        ranges.append((start_at, start_at + size, row))
    if any(ranges[i][1] > ranges[i + 1][0] for i in range(len(ranges) - 1)):
        raise RuntimeError("overlapping selected native ranges")

    index_path = NATIVE / "member-index.json"
    index_bytes = index_path.read_bytes()
    index = json.loads(index_bytes)
    downstream_path = NATIVE / "downstream-reader.json"
    downstream_bytes = downstream_path.read_bytes()
    downstream = json.loads(downstream_bytes)
    canonical_index_bytes = json.dumps(index, sort_keys=True, separators=(",", ":")).encode()
    canonical_index_sha = hashlib.sha256(canonical_index_bytes).hexdigest()
    if downstream.get("index_sha256") != canonical_index_sha:
        raise RuntimeError("member index differs from the pinned downstream-reader binding")
    reader = import_reader()
    reader_path = CUSTODY / "reader.py"
    reader_sha = digest(reader_path)
    index_sha = hashlib.sha256(index_bytes).hexdigest()
    query_sha = hashlib.sha256(query_bytes).hexdigest()

    # Hold the extracted bytes in a private scratch file. A read error, altered
    # source, bad later chunk, or final member-digest failure leaves no published
    # selected-record output and no geometry operation can consume the stage.
    selected_dir.mkdir(parents=True, exist_ok=True)
    temp_name = None
    output_path = selected_dir / "records.bin"
    if output_path.exists():
        raise RuntimeError("refusing to overwrite a previous selected-record output")
    selected_hashers = {row["id"]: hashlib.sha256() for row in rows}
    coordinate_hashers = {row["id"]: hashlib.sha256() for row in rows}
    selected_counts = {row["id"]: 0 for row in rows}
    output_offsets = {}
    position = 0
    output_count = 0
    try:
        with tempfile.NamedTemporaryFile(mode="w+b", dir=selected_dir, prefix=".unverified-", delete=False) as stage:
            temp_name = stage.name

            def get_encoded(pin):
                return reader.directory_body(NATIVE, pin)

            for block in reader._verify_native_chunks(index, get_encoded):
                block_end = position + len(block)
                for begin, end, row in ranges:
                    overlap_begin = max(position, begin)
                    overlap_end = min(block_end, end)
                    if overlap_begin >= overlap_end:
                        continue
                    piece = block[overlap_begin - position:overlap_end - position]
                    identity = row["id"]
                    if selected_counts[identity] == 0:
                        output_offsets[identity] = output_count
                    stage.write(piece)
                    selected_hashers[identity].update(piece)
                    coordinate_begin = max(overlap_begin, begin + 44)
                    if coordinate_begin < overlap_end:
                        coordinate_hashers[identity].update(
                            block[coordinate_begin - position:overlap_end - position])
                    selected_counts[identity] += len(piece)
                    output_count += len(piece)
                position = block_end
            stage.flush()
            os.fsync(stage.fileno())

        if position != reader.MEMBER_BYTES or output_count != sum(row["record_bytes"] for row in rows):
            raise RuntimeError("authenticated whole member or selected byte count differs")

        # Independent post-stream record checks bind the exact selected row
        # headers, full-record hashes and coordinate hashes to retained metadata.
        with open(temp_name, "rb") as staged:
            for row in rows:
                identity = row["id"]
                expected_bytes = row["record_bytes"]
                if selected_counts[identity] != expected_bytes:
                    raise RuntimeError(f"selected record byte count differs for native ID {identity}")
                if selected_hashers[identity].hexdigest() != row["record_sha256"]:
                    raise RuntimeError(f"selected native record digest differs for ID {identity}")
                if coordinate_hashers[identity].hexdigest() != row["coordinate_bytes_sha256"]:
                    raise RuntimeError(f"selected native coordinates differ for ID {identity}")
                staged.seek(output_offsets[identity])
                header = staged.read(44)
                if len(header) != 44 or list(HEADER.unpack(header)) != row["header_int32"]:
                    raise RuntimeError(f"selected native header differs for ID {identity}")
                if HEADER.unpack(header)[0:3] != (identity, row["n"], row["flag"]):
                    raise RuntimeError(f"selected native ID/count/flags differ for ID {identity}")
                if row["level"] != (row["flag"] & 255) or row["level"] != 1:
                    raise RuntimeError(f"selected native level differs for ID {identity}")
                staged.seek(output_offsets[identity] + expected_bytes - 8)
                if len(staged.read(8)) != 8:
                    raise RuntimeError(f"selected coordinate tail is truncated for ID {identity}")

        os.replace(temp_name, output_path)
        temp_name = None
        output_sha = digest(output_path)
        if output_path.stat().st_size != output_count:
            raise RuntimeError("published selected native file changed size")

        result = {
            "version": 1,
            "status": "bytes-verified",
            "geometry_operations_invoked": False,
            "whole_native_member": {
                "member_name": reader.MEMBER,
                "bytes": reader.MEMBER_BYTES,
                "sha256": reader.MEMBER_SHA,
                "records_authenticated": 188612,
                "validation_completed_before_publish": True,
            },
            "reader": {"path": reader_path.relative_to(ROOT).as_posix(), "sha256": reader_sha},
            "member_index": {"path": index_path.relative_to(ROOT).as_posix(), "sha256": index_sha,
                             "canonical_sha256": canonical_index_sha},
            "downstream_reader": {"path": downstream_path.relative_to(ROOT).as_posix(),
                                  "sha256": hashlib.sha256(downstream_bytes).hexdigest()},
            "query_metadata": {"path": query_path.relative_to(ROOT).as_posix(), "sha256": query_sha},
            "selected_output": {
                "path": output_path.relative_to(ROOT).as_posix(), "bytes": output_path.stat().st_size,
                "sha256": output_sha,
                "record_order": [row["id"] for row in rows],
                "records": [{"id": row["id"], "source_offset": row["offset"],
                             "output_offset": output_offsets[row["id"]], "bytes": row["record_bytes"],
                             "sha256": row["record_sha256"],
                             "coordinate_bytes_sha256": row["coordinate_bytes_sha256"],
                             "header_int32": row["header_int32"], "level": row["level"],
                             "version": row["version"], "seam_flags": row["seam_flags"],
                             "source": row["source"], "river_lake": row["river_lake"],
                             "area_scale": row["area_scale"], "container": row["container"],
                             "ancestor": row["ancestor"],
                             "first_point": row["first_point"], "last_point": row["last_point"],
                             "native_bounds_microdegrees": row["native_bounds_microdegrees"],
                             "closed": row["closed"],
                             "source_geometry_validity": "not evaluated; custody only"}
                            for row in rows],
            },
            "limits": [
                "All 11 selected records are GSHHG level 1 coarse land support; this does not establish shoreline authority.",
                "Native coordinates are authenticated bytes; geometry validity, observation date, datum registration, and repair authority are not established by this extraction.",
                "Selected record staging remains private until all 188612 native records and the full member hash pass.",
            ],
            "execution": {"python": sys.version.split()[0], "elapsed_seconds": round(time.monotonic() - start, 3)},
        }
        receipt_path = selected_dir / "receipt.json"
        if receipt_path.exists():
            raise RuntimeError("refusing to overwrite previous extraction receipt")
        receipt_path.write_text(json.dumps(result, indent=2) + "\n")
    finally:
        if temp_name is not None:
            pathlib.Path(temp_name).unlink(missing_ok=True)
    print(json.dumps({"status": result["status"], "selected_records": len(rows),
                      "bytes": result["selected_output"]["bytes"],
                      "sha256": result["selected_output"]["sha256"],
                      "elapsed_seconds": result["execution"]["elapsed_seconds"]}))


if __name__ == "__main__":
    main()
