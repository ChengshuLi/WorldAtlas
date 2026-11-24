#!/usr/bin/python3
"""Compose the physical land and water grid from verified rasters."""

import json
import os
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any, BinaryIO, cast

import numpy as np
from osgeo import gdal

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.execution.control import check_cancelled
from worldatlas.map_build.execution.runtime import RunFilePins
from worldatlas.map_build.physical.sources import create_mask, open_mask
from worldatlas.shared.files import FilePin

gdal.UseExceptions()


def write_run_block(
    codes: np.ndarray,
    runs: BinaryIO,
    offsets: list[int],
    width: int,
    *,
    binary: bool = False,
) -> None:
    """Append a batch of physical rows as little-endian uint32 runs.

    Args:
        codes: Two-dimensional array of physical codes or binary land values.
        runs: Open binary stream for (end_column, code) records.
        offsets: Existing row offsets to extend.
        width: Number of columns in each row.
        binary: Convert binary water and land values to codes 1 and 17.

    Raises:
        ValueError: The final run offset is too large for uint32.
    """
    row_count = codes.shape[0]
    row_index, left_column = np.nonzero(codes[:, 1:] != codes[:, :-1])
    transitions = np.bincount(row_index, minlength=row_count).astype(
        np.int64, copy=False
    )
    run_counts = transitions + 1
    pairs = np.empty((int(run_counts.sum()), 2), dtype='<u4')
    # np.nonzero returns transitions in row-major order. Each preceding row adds
    # one terminal run, so its flattened transition index is the output slot + row.
    transition_slots = np.arange(len(row_index), dtype=np.int64) + np.repeat(
        np.arange(row_count, dtype=np.int64), transitions
    )
    pairs[transition_slots, 0] = left_column + 1
    pairs[transition_slots, 1] = codes[row_index, left_column]
    terminal_slots = np.cumsum(run_counts, dtype=np.int64) - 1
    pairs[terminal_slots, 0] = width
    pairs[terminal_slots, 1] = codes[:, -1]
    if binary:
        # Convert only emitted run values, not every cell of the full raster.
        pairs[:, 1] *= 16
        pairs[:, 1] += 1
    next_offsets = np.cumsum(run_counts, dtype=np.uint64) + offsets[-1]
    if next_offsets[-1] > np.iinfo(np.uint32).max:
        raise ValueError('too many runs for u32 offsets')
    pairs.tofile(runs)
    offsets.extend(next_offsets.tolist())


def main(
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
    masks = [open_mask(pin, grid, files) for pin in source_masks.values()]
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
            arrays = [ds.ReadAsArray(0, y, w, n) for ds in masks]
            if any(array is None for array in arrays):
                raise ValueError('GDAL could not read a physical mask')
            arrays = cast(list[np.ndarray], arrays)
            land_values, water_values = arrays
            if any(
                (np.max(x) > 1 if x.dtype == np.uint8 else np.any((x != 0) & (x != 1)))
                for x in arrays
            ):
                raise ValueError('nonbinary mask')
            if land_values.dtype == water_values.dtype == np.uint8:
                np.subtract(1, water_values, out=water_values)
                np.bitwise_and(land_values, water_values, out=land_values)
                dry = land_values
            else:
                # Binary masks from other GDAL types are supported as before.
                dry = np.logical_and(land_values == 1, water_values == 0).astype(
                    np.uint8
                )
            tif.GetRasterBand(1).WriteArray(dry, 0, y)
            candidate_count += int(np.count_nonzero(dry))
            write_run_block(dry, runs, offsets, w, binary=True)
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
    masks = []
    with (out / 'rows.u32le').open('xb') as f:
        np.asarray(offsets, dtype='<u4').tofile(f)
    for key, pin in source_masks.items():
        if files.pin(pin['path'])['sha256'] != pin['sha256']:
            raise ValueError(f'{key} changed during processing')
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
    with (out / 'report.json').open('x') as f:
        json.dump(report, f, indent=2)
        f.write('\n')
    return report
