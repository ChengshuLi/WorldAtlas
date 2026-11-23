#!/usr/bin/env python3
"""Combine verified inland-water masks into one raster."""

import hashlib
import json
import os
import shutil
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, Literal

import numpy as np
from osgeo import gdal

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.execution.control import check_cancelled
from worldatlas.map_build.execution.runtime import RunFilePins
from worldatlas.map_build.inputs.configuration import FilePin
from worldatlas.map_build.physical.sources import create_mask, open_mask

gdal.UseExceptions()


def union_mask(ds: gdal.Dataset, water: np.ndarray, y: int) -> None:
    """Combine the raster's water cells into a batch in place.

    Args:
        ds: Single-band water raster with zero or one per cell.
        water: Two-dimensional output block to update.
        y: First row of the output block in the full raster.

    Raises:
        ValueError: The dataset has multiple bands or nonbinary values.
    """
    width = water.shape[1]
    rows = water.shape[0]
    band = ds.GetRasterBand(1)
    nodata = band.GetNoDataValue()
    if ds.RasterCount != 1:
        raise ValueError('candidate mask must have one band')
    if (
        ds.GetDriver().ShortName != 'GTiff'
        or band.DataType != gdal.GDT_Byte
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
        if np.any((arr != 0) & (arr != 1)):
            raise ValueError('nonbinary candidate input')
        view = water[:, x : x + n]
        np.bitwise_or(view, arr.astype(np.uint8, copy=False), out=view)


class ShardMask(FilePin):
    """Pin one completed water shard mask and its report."""

    status: Literal['candidate-only']
    report: FilePin


def verify_lineage(
    source_manifest: FilePin,
    shards: Sequence[ShardMask],
    grid: Grid,
    files: RunFilePins,
) -> None:
    """Verify that the output masks came from the pinned complete shard set.

    Args:
        source_manifest: Pin for the saved list of raw water sources.
        shards: All completed shard mask and report pins.
        grid: Physical grid expected in every report.
        files: Attempt-local file checksum verifier.

    Raises:
        ValueError: A shard, report, or source manifest is incomplete or mismatched.
    """
    spec = source_manifest
    if files.pin(spec['path'])['sha256'] != spec['sha256']:
        raise ValueError('pinned source manifest required')
    manifest = json.loads(Path(spec['path']).read_bytes())
    entries = manifest.get('files')
    if (
        not isinstance(entries, list)
        or manifest.get('file_count') != len(entries)
        or not entries
    ):
        raise ValueError('source manifest must list every raw shard')
    expected = [f.get('sha256') for f in entries]
    if any(
        not isinstance(v, str)
        or len(v) != 64
        or any(ch not in '0123456789abcdef' for ch in v)
        for v in expected
    ) or len(set(expected)) != len(expected):
        raise ValueError('source manifest hashes must be unique SHA-256 values')
    seen = []
    policies = []
    scripts = []
    kernels = []
    for shard in shards:
        report = shard['report']
        if files.pin(report['path'])['sha256'] != report['sha256']:
            raise ValueError('pinned shard report required')
        doc = json.loads(Path(report['path']).read_bytes())
        row_count = doc.get('rows_in_source')
        script = doc.get('script_sha256')
        if (
            doc.get('status') != 'candidate-only'
            or doc.get('output_sha256') != shard['sha256']
            or doc.get('grid') != vars(grid)
            or doc.get('invalid_feature_ids')
            or doc.get('counts', {}).get('missing_classification', 0)
            or doc.get('counts', {}).get('invalid_polygon', 0)
            or not doc.get('policy')
            or not isinstance(script, str)
            or len(script) != 64
            or any(ch not in '0123456789abcdef' for ch in script)
            or not isinstance(row_count, int)
            or isinstance(row_count, bool)
            or row_count < 0
            or row_count != doc.get('counts', {}).get('rows')
        ):
            raise ValueError('incomplete or inconsistent shard report')
        rasterizer = doc.get('rasterizer')
        if rasterizer not in ('python', 'gdal'):
            raise ValueError('unknown water rasterizer')
        if rasterizer == 'gdal':
            kernel = doc.get('gdal_kernel')
            if (
                not isinstance(kernel, dict)
                or kernel.get('implementation') != 'python-gdal-api-v2'
                or kernel.get('method') not in ('hybrid', 'tiled')
                or not isinstance(kernel.get('binding_sha256'), str)
                or len(kernel['binding_sha256']) != 64
                or any(ch not in '0123456789abcdef' for ch in kernel['binding_sha256'])
            ):
                raise ValueError('invalid in-process GDAL water kernel')
            kernels.append(
                ('gdal', kernel['method'], kernel['binding_sha256'], kernel.get('gdal'))
            )
        else:
            kernels.append(('python',))
        seen.append(doc.get('source_sha256'))
        policies.append(doc.get('policy'))
        scripts.append(doc.get('script_sha256'))
    if (
        len(seen) != len(expected)
        or set(seen) != set(expected)
        or len(set(seen)) != len(seen)
    ):
        raise ValueError(
            'shard reports do not cover the pinned source manifest exactly'
        )
    if any(p != policies[0] for p in policies):
        raise ValueError('inconsistent shard selection policy')
    if any(p != scripts[0] for p in scripts):
        raise ValueError('inconsistent shard rasterizer')
    if any(k != kernels[0] for k in kernels):
        raise ValueError('inconsistent water kernels')


def run(
    config_path: Path | str,
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
        config_path: Saved union request used for the report checksum.
        output: New directory for the combined mask and report.
        grid: Shared, validated physical grid.
        source_manifest: Saved list of raw water shards, pinned by checksum.
        shards: Completed masks and reports for those shards.
        minimum_free_bytes: Shared disk reserve in bytes.
        rows_per_block: Number of grid rows to union at a time.
        files: Attempt-local file checksum verifier.
        emit: Progress callback.

    Returns:
        Report with the combined water count and raster checksum.
    """
    config_path = Path(config_path).resolve()
    data = config_path.read_bytes()
    output = Path(output).resolve()
    w, h = grid.width, grid.height
    verify_lineage(source_manifest, shards, grid, files)
    inputs = (
        [config_path, Path(source_manifest['path']).resolve()]
        + [Path(x['path']).resolve() for x in shards]
        + [Path(x['report']['path']).resolve() for x in shards]
    )
    if len(set(inputs)) != len(inputs):
        raise ValueError('input paths must be unique')
    if any(p.is_relative_to(output) or output.is_relative_to(p.parent) for p in inputs):
        raise ValueError(
            'output must be outside input directories and must not contain inputs'
        )
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
    for item in shards:
        if files.pin(item['path'])['sha256'] != item['sha256']:
            raise ValueError('input changed during union')
    if config_path.read_bytes() != data:
        raise ValueError('configuration changed during union')
    verify_lineage(source_manifest, shards, grid, files)
    report = {
        'status': 'candidate-only',
        'configuration_sha256': hashlib.sha256(data).hexdigest(),
        'grid': vars(grid),
        'source_manifest': source_manifest,
        'shard_count': len(shards),
        'rows_per_block': rows_per_block,
        'shards': shards,
        'candidate_water_cells': candidate,
        'union_sha256': files.pin(output / 'water-union.tif')['sha256'],
    }
    with (output / 'config.json').open('xb') as f:
        f.write(data)
    with (output / 'report.json').open('x') as f:
        json.dump(report, f, indent=2)
        f.write('\n')
    return report
