#!/usr/bin/python3
"""Rasterize one Overture water GeoParquet shard to a sparse grid mask.

The output directory must not already exist.
"""

import json
import os
import shutil
import sys
from collections import Counter
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pyarrow
import pyarrow.compute as pc
import pyarrow.parquet as pq
from osgeo import gdal, ogr

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.execution.control import check_cancelled
from worldatlas.map_build.execution.runtime import RunFilePins
from worldatlas.map_build.inputs.configuration import WaterSettings
from worldatlas.map_build.physical.sources import ShardMask, create_mask
from worldatlas.map_build.physical.water_batch import GeometryStatus, WaterBatch
from worldatlas.shared.text import UNICODE_WHITESPACE

gdal.UseExceptions()
ogr.UseExceptions()

INLAND_WATER_SUBTYPE_POLICY = 'overture-inland-subtype-v1'
EXCLUDED_WATER_SUBTYPES = (
    'ocean',  # The coastline already defines the open ocean.
    'physical',  # Overture's named features, such as bays, can overlap water polygons.
)


def classify_water_subtypes(subtypes: pyarrow.Array) -> tuple[np.ndarray, int, int]:
    """Select rows by Overture subtype before checking their geometry.

    Skip the exact values ``ocean`` and ``physical``. Null, blank, and non-text
    values count as missing and make the shard incomplete. Other text values
    pass this check. Trim whitespace only when checking for blank text.

    Args:
        subtypes: Array of Overture subtype values.

    Returns:
        A 1-D Boolean array marking rows that pass the subtype check, the
        number of missing values, and the number of excluded values.

        For example, ["lake", "ocean", "physical", None] gives
        ([True, False, False, False], 1, 2).
    """
    # Arrow registers these compute kernels dynamically when the module loads.
    if pyarrow.types.is_dictionary(subtypes.type):
        subtypes = pc.dictionary_decode(subtypes)  # pyright: ignore[reportAttributeAccessIssue]
    if subtypes.type not in (pyarrow.string(), pyarrow.large_string()):
        # The whole column has the wrong type, so none of its rows has usable text.
        return np.zeros(len(subtypes), dtype=bool), len(subtypes), 0

    # Trim only to detect blank values. Compare excluded subtypes as stored.
    trimmed_subtypes = pc.utf8_trim(  # pyright: ignore[reportAttributeAccessIssue]
        subtypes, characters=UNICODE_WHITESPACE
    )
    missing_rows = pc.is_in(  # pyright: ignore[reportAttributeAccessIssue]
        trimmed_subtypes, value_set=pyarrow.array(('', None), type=subtypes.type)
    )
    excluded_rows = pc.is_in(  # pyright: ignore[reportAttributeAccessIssue]
        subtypes, value_set=pyarrow.array(EXCLUDED_WATER_SUBTYPES, type=subtypes.type)
    )
    eligible_rows = pc.invert(pc.or_(missing_rows, excluded_rows))  # pyright: ignore[reportAttributeAccessIssue]
    return (
        eligible_rows.to_numpy(zero_copy_only=False),
        int(pc.sum(missing_rows).as_py() or 0),  # pyright: ignore[reportAttributeAccessIssue]
        int(pc.sum(excluded_rows).as_py() or 0),  # pyright: ignore[reportAttributeAccessIssue]
    )


def gdal_batch(
    kernel: WaterBatch,
    raster: gdal.Dataset,
    batch: pyarrow.RecordBatch,
    counts: Counter[str],
    invalid_rows: list[int],
    grid: Grid,
    tile: int,
    source: Path,
) -> None:
    """Rasterize one selected batch and update its statistics.

    Args:
        kernel: Batch rasterizer.
        raster: Output raster to update.
        batch: Source rows containing subtypes and WKB.
        counts: Row and classification counts to update.
        invalid_rows: Zero-based file row numbers to append for invalid polygons.
        grid: Shared physical build grid.
        tile: Tile size in cells.
        source: Path to the Parquet file, used in errors.

    Raises:
        ValueError: A selected geometry is missing or malformed.
    """
    first_row = counts['rows']
    eligible, missing, excluded = classify_water_subtypes(batch.column('subtype'))
    counts['rows'] += len(batch)
    if missing:
        counts['missing_classification'] += missing
    if excluded:
        counts['excluded_classification'] += excluded
    status, failed = kernel.burn(raster, batch.column('geometry'), eligible, grid, tile)
    if failed is not None:
        message = (
            'missing geometry'
            if status[failed] == GeometryStatus.MISSING
            else 'invalid or empty WKB geometry'
        )
        raise ValueError(f'{source}, row {first_row + failed}: {message}')
    for code, name in (
        (GeometryStatus.POLYGON, 'polygons'),
        (GeometryStatus.NON_POLYGON, 'non_polygon'),
        (GeometryStatus.INVALID_POLYGON, 'invalid_polygon'),
    ):
        count = int(np.count_nonzero(status == code))
        if count:
            counts[name] += count
    invalid_rows.extend(
        (first_row + np.flatnonzero(status == GeometryStatus.INVALID_POLYGON)).tolist()
    )


def run(
    source: Path | str,
    expected: str,
    output: Path | str,
    configuration_sha256: str,
    grid: Grid,
    *,
    settings: WaterSettings,
    minimum_free_bytes: int,
    files: RunFilePins,
    emit: Callable[..., None] = print,
) -> tuple[ShardMask, tuple[str, ...]]:
    """Write one complete water mask and its report.

    Args:
        source: Local source GeoParquet file.
        expected: SHA-256 digest for the source file.
        output: New directory for the shard mask and report.
        configuration_sha256: Checksum of the saved stage settings.
        grid: Shared physical build grid.
        settings: Validated inland-water rasterizer options.
        minimum_free_bytes: Shared physical build disk reserve in bytes.
        files: Attempt-local file checksum verifier.
        emit: Progress callback.

    Returns:
        Mask and report file pins, followed by the rasterizer identity. The
        identity contains the script checksum, engine name, kernel
        checksum, and GDAL version.

    Raises:
        ValueError: Input validation fails, the input changes, or the mask is incomplete.
            A completed raster pass with input issues writes a diagnostic report
            before raising.
    """
    source = Path(source).resolve()
    output = Path(output).resolve()
    tile = settings.get('tile_size', 1024)
    reserve = minimum_free_bytes
    batch_size = settings.get('batch_size', 8192)
    if len(expected) != 64 or files.pin(source)['sha256'] != expected.lower():
        raise ValueError('source SHA-256 does not match expected digest')
    pf = pq.ParquetFile(source, pre_buffer=False)
    geometry_metadata = (pf.schema_arrow.metadata or {}).get(b'geo')
    if geometry_metadata is None:
        raise ValueError(f'{source}: missing GeoParquet metadata')
    geo = json.loads(geometry_metadata)
    if (
        geo['primary_column'] != 'geometry'
        or geo['columns']['geometry'].get('encoding') != 'WKB'
    ):
        raise ValueError('unexpected GeoParquet geometry encoding or column')
    # GeoParquet specifies OGC:CRS84 when crs is absent. Refuse a different or
    # explicitly null CRS rather than silently assume longitude/latitude.
    if 'crs' in geo['columns']['geometry']:
        raise ValueError(
            'unsupported explicit CRS; expected GeoParquet default OGC:CRS84'
        )
    if shutil.disk_usage(output.parent).free < reserve:
        raise ValueError('free disk below configured reserve')
    os.mkdir(output)
    out = Path(output)
    kernel = WaterBatch()
    raster = create_mask(out / 'water.tif', grid)
    counts = Counter()
    invalid_rows: list[int] = []
    # A feature's raster burn is identical across batches because the operation
    # is a monotone union (the mask is initialized to zero and burns only 1).
    for batch in pf.iter_batches(
        batch_size=batch_size,
        columns=['subtype', 'geometry'],
        use_threads=False,
    ):
        check_cancelled()
        if shutil.disk_usage(out).free < reserve:
            raise ValueError(
                'free disk below configured reserve; partial output preserved'
            )
        gdal_batch(kernel, raster, batch, counts, invalid_rows, grid, tile, source)
        # Release this batch before Arrow reads the next one.
        del batch
        emit(
            json.dumps(
                {
                    'rows': counts['rows'],
                    'polygons': counts['polygons'],
                    'invalid_polygon': counts['invalid_polygon'],
                    'gdal_cache_used_bytes': gdal.GetCacheUsed(),
                }
            ),
            flush=True,
        )
    check_cancelled()
    raster.FlushCache()
    raster = None
    if files.pin(source)['sha256'] != expected.lower():
        raise ValueError('source changed during processing')
    invalid_rows_filename = None
    if invalid_rows:
        invalid_rows_filename = 'invalid-feature-rows.json'
        with (out / invalid_rows_filename).open('x') as f:
            f.write(json.dumps(invalid_rows, indent=2) + '\n')
    source_row_count = pf.metadata.num_rows
    complete = (
        counts.get('rows') == source_row_count
        and not invalid_rows
        and not counts['missing_classification']
    )
    script_sha256 = files.pin(__file__)['sha256']
    mask = files.pin(out / 'water.tif')
    kernel_provenance = kernel.provenance
    report = {
        'status': 'candidate-only' if complete else 'incomplete-input-issues',
        'source': str(source),
        'source_sha256': expected.lower(),
        'rows_in_source': source_row_count,
        'script_sha256': script_sha256,
        'rasterizer': 'gdal',
        'gdal_kernel': kernel_provenance,
        'batch_timings': kernel.timings,
        'counts': dict(counts),
        'batch_size': batch_size,
        'tile_size': tile,
        'invalid_feature_rows': invalid_rows_filename,
        'policy': {'method': INLAND_WATER_SUBTYPE_POLICY},
        'selection_notes': settings.get('selection_notes'),
        'configuration_sha256': configuration_sha256,
        'grid': vars(grid),
        'runtime': {
            'python': sys.version,
            'pyarrow': pyarrow.__version__,
            'gdal': gdal.VersionInfo('--version'),
            'geos': '.'.join(
                str(f())
                for f in (
                    ogr.GetGEOSVersionMajor,
                    ogr.GetGEOSVersionMinor,
                    ogr.GetGEOSVersionMicro,
                )
            ),
        },
        'output_sha256': mask['sha256'],
    }
    report_path = out / 'report.json'
    with report_path.open('x') as f:
        f.write(json.dumps(report, indent=2) + '\n')
    if not complete:
        raise ValueError(f'incomplete water shard: see {report_path}')

    rasterizer_identity = (
        script_sha256,
        'gdal',
        kernel_provenance['binding_sha256'],
        kernel_provenance['gdal'],
    )
    return (
        ShardMask(**mask, status='candidate-only', report=files.pin(report_path)),
        rasterizer_identity,
    )
