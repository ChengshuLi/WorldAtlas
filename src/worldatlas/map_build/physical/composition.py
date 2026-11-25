#!/usr/bin/python3
"""Compose the physical land and water grid from verified rasters."""

import json
import os
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any, BinaryIO

import numpy as np
from osgeo import gdal

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.execution.control import check_cancelled
from worldatlas.map_build.execution.runtime import RunFilePins
from worldatlas.map_build.physical.sources import create_mask, open_mask
from worldatlas.shared.files import FilePin, write_json

gdal.UseExceptions()


def write_run_block(
    dry_land: np.ndarray,
    runs: BinaryIO,
    offsets: list[int],
) -> None:
    """Encode a binary land mask as little-endian uint32 physical runs.

    Args:
        dry_land: Full-width rows of uint8 cells, with 0 for water and 1 for land.
        runs: Open binary stream for (end_column, code) records.
        offsets: Existing row offsets to extend.

    Raises:
        ValueError: The final run offset is too large for uint32.
    """
    row_count, width = dry_land.shape
    row_index, left_column = np.nonzero(dry_land[:, 1:] != dry_land[:, :-1])
    run_ends = np.cumsum(
        np.bincount(row_index, minlength=row_count) + 1, dtype=np.int64
    )
    total_runs = int(run_ends[-1])
    previous_end = offsets[-1]
    if previous_end + total_runs > np.iinfo(np.uint32).max:
        raise ValueError('too many runs for u32 offsets')

    pairs = np.empty((total_runs, 2), dtype='<u4')
    # Each earlier row adds one final run. Transition 7 in row 2 goes in slot 9.
    transition_slots = np.arange(len(row_index), dtype=np.int64) + row_index
    pairs[transition_slots, 0] = left_column + 1
    pairs[transition_slots, 1] = dry_land[row_index, left_column]
    terminal_slots = run_ends - 1
    pairs[terminal_slots, 0] = width
    pairs[terminal_slots, 1] = dry_land[:, -1]
    # Encode each run once. Physical streams use 1 for water and 17 for land.
    pairs[:, 1] *= 16
    pairs[:, 1] += 1
    pairs.tofile(runs)
    offsets.extend((run_ends + previous_end).tolist())


def run(
    configuration_sha256: str,
    output: Path | str,
    grid: Grid,
    *,
    land: FilePin,
    water: FilePin,
    minimum_free_bytes: int,
    rows_per_block: int,
    files: RunFilePins,
    emit: Callable[..., None] | None = None,
) -> dict[str, Any]:
    """Combine the coastline land mask and inland water mask.

    Args:
        configuration_sha256: Checksum of the saved stage settings.
        output: New directory for the GeoTIFF and row-run files.
        grid: Shared, validated physical grid.
        land: Pin for the binary coastline land mask.
        water: Pin for the binary inland water mask.
        minimum_free_bytes: Shared disk reserve in bytes.
        rows_per_block: Number of grid rows to process at a time.
        files: Attempt-local file checksum verifier.
        emit: Optional progress callback.

    Returns:
        Report with output digests and physical cell counts.
    """
    w, h = grid.width, grid.height
    output = Path(output).resolve()
    source_masks = {'land': land, 'water': water}
    inputs = [Path(pin['path']).resolve() for pin in source_masks.values()]
    if len(set(inputs)) != len(inputs):
        raise ValueError('inputs must be distinct')
    land_mask = open_mask(land, grid, files)
    water_mask = open_mask(water, grid, files)
    os.mkdir(output)
    out = Path(output)
    tif = create_mask(out / 'physical-dry.tif', grid)
    offsets = [0]
    candidate_count = 0
    with (out / 'runs.u32le').open('xb') as runs:
        for y in range(0, h, rows_per_block):
            check_cancelled()
            if shutil.disk_usage(out).free < minimum_free_bytes:
                raise ValueError(
                    'free disk below configured reserve; partial output preserved'
                )
            n = min(rows_per_block, h - y)
            land_values = land_mask.ReadAsArray(0, y, w, n)
            water_values = water_mask.ReadAsArray(0, y, w, n)
            if land_values is None or water_values is None:
                raise ValueError('GDAL could not read a physical mask')
            if np.max(land_values) > 1 or np.max(water_values) > 1:
                raise ValueError('nonbinary mask')
            # Flip the water bits so the AND keeps only land outside inland water.
            np.subtract(1, water_values, out=water_values)
            np.bitwise_and(land_values, water_values, out=land_values)
            tif.GetRasterBand(1).WriteArray(land_values, 0, y)
            candidate_count += int(np.count_nonzero(land_values))
            write_run_block(land_values, runs, offsets)
            if emit is not None:
                emit(
                    json.dumps(
                        {'rows_done': y + n, 'candidate_dry_cells': candidate_count}
                    ),
                    flush=True,
                )
    check_cancelled()
    tif.FlushCache()
    tif = None
    land_mask.Close()
    water_mask.Close()
    with (out / 'rows.u32le').open('xb') as f:
        np.asarray(offsets, dtype='<u4').tofile(f)
    files.verify(source_masks.values())
    report = {
        'status': 'candidate-only',
        'configuration_sha256': configuration_sha256,
        'grid': vars(grid),
        'rows_per_block': rows_per_block,
        'inputs': source_masks,
        'candidate_dry_cells': candidate_count,
        'output_sha256': {
            name: files.pin(out / name)['sha256']
            for name in ('physical-dry.tif', 'rows.u32le', 'runs.u32le')
        },
    }
    write_json(out / 'report.json', report)
    return report
