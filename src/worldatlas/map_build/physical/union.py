#!/usr/bin/env python3
"""Combine verified inland-water masks into one raster."""

import json
import os
import shutil
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import numpy as np
from osgeo import gdal

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.execution.control import check_cancelled
from worldatlas.map_build.execution.runtime import RunFilePins
from worldatlas.map_build.physical.sources import ShardMask, create_mask, open_mask
from worldatlas.shared.files import FilePin

gdal.UseExceptions()


def union_mask(ds: gdal.Dataset, water: np.ndarray, y: int) -> None:
    """Combine the raster's water cells into a batch in place.

    Args:
        ds: Verified single-band uint8 water raster with zero or one per cell.
        water: Two-dimensional output block to update.
        y: First row of the output block in the full raster.

    Raises:
        ValueError: The block contains a value above 1.
    """
    width = water.shape[1]
    rows = water.shape[0]
    band = ds.GetRasterBand(1)
    nodata = band.GetNoDataValue()
    if (
        ds.GetDriver().ShortName != 'GTiff'
        or nodata not in (None, 0)
        or not hasattr(band, 'GetDataCoverageStatus')
    ):
        windows = [(0, width)]
    else:
        block_width, _ = band.GetBlockSize()
        windows = []
        for x in range(0, width, block_width):
            n = min(block_width, width - x)
            flags, _ = band.GetDataCoverageStatus(x, y, n, rows)
            if flags != gdal.GDAL_DATA_COVERAGE_STATUS_EMPTY:
                windows.append((x, n))
    for x, n in windows:
        arr = band.ReadAsArray(x, y, n, rows)
        if np.max(arr) > 1:
            raise ValueError('nonbinary candidate input')
        view = water[:, x : x + n]
        np.bitwise_or(view, arr, out=view)


def run(
    configuration_sha256: str,
    output: Path | str,
    grid: Grid,
    *,
    source_manifest: FilePin,
    shards: Sequence[ShardMask],
    minimum_free_bytes: int,
    rows_per_block: int,
    files: RunFilePins,
    emit: Callable[..., None] = print,
) -> dict[str, Any]:
    """Combine verified water shards into a single aligned raster.

    Args:
        configuration_sha256: Checksum of the saved stage settings.
        output: New directory for the combined mask and report.
        grid: Shared, validated physical grid.
        source_manifest: Saved list of raw water shards, pinned by checksum.
        shards: Complete masks and report pins returned by the water rasterizer.
        minimum_free_bytes: Shared disk reserve in bytes.
        rows_per_block: Number of grid rows to union at a time.
        files: Attempt-local file checksum verifier.
        emit: Progress callback.

    Returns:
        Report with the combined water count and raster checksum.
    """
    output = Path(output).resolve()
    w, h = grid.width, grid.height
    inputs = (
        [Path(source_manifest['path']).resolve()]
        + [Path(x['path']).resolve() for x in shards]
        + [Path(x['report']['path']).resolve() for x in shards]
    )
    if len(set(inputs)) != len(inputs):
        raise ValueError('input paths must be unique')
    masks = [open_mask(s, grid, files) for s in shards]
    os.mkdir(output)
    tif = create_mask(output / 'water-union.tif', grid)
    candidate = 0
    for y in range(0, h, rows_per_block):
        check_cancelled()
        if shutil.disk_usage(output).free < minimum_free_bytes:
            raise ValueError(
                'free disk below configured reserve; partial output preserved'
            )
        n = min(rows_per_block, h - y)
        water = np.zeros((n, w), dtype=np.uint8)
        for ds in masks:
            union_mask(ds, water, y)
        candidate += int(np.count_nonzero(water))
        tif.GetRasterBand(1).WriteArray(water, 0, y)
        emit(
            json.dumps({'rows_done': y + n, 'candidate_water_cells': candidate}),
            flush=True,
        )
    check_cancelled()
    tif.FlushCache()
    tif = None
    masks = []
    # Check that the mask and report bytes stayed fixed during the merge.
    files.verify([*shards, *(shard['report'] for shard in shards)])
    report = {
        'status': 'candidate-only',
        'configuration_sha256': configuration_sha256,
        'grid': vars(grid),
        'source_manifest': source_manifest,
        'shard_count': len(shards),
        'rows_per_block': rows_per_block,
        'shards': shards,
        'candidate_water_cells': candidate,
        'union_sha256': files.pin(output / 'water-union.tif')['sha256'],
    }
    with (output / 'report.json').open('x') as f:
        json.dump(report, f, indent=2)
        f.write('\n')
    return report
