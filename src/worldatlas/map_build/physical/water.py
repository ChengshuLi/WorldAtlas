#!/usr/bin/python3
"""Rasterize one Overture water GeoParquet shard to a sparse grid mask.

The output directory must not already exist.
"""

import gc
import hashlib
import json
import math
import os
import shutil
import sys
from collections import Counter
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, cast

import numpy as np
import pyarrow
import pyarrow.compute as pc
import pyarrow.parquet as pq
from osgeo import gdal, ogr, osr

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.execution.control import check_cancelled
from worldatlas.map_build.execution.runtime import RunFilePins
from worldatlas.map_build.inputs.configuration import WaterSettings
from worldatlas.map_build.physical.sources import create_mask
from worldatlas.map_build.physical.water_batch import GeometryStatus, WaterBatch

gdal.UseExceptions()
ogr.UseExceptions()

POLYGON = (ogr.wkbPolygon, ogr.wkbMultiPolygon)
# The complete whitespace set used by Python str.strip(), including its four
# C0 separators. Pass it explicitly so Arrow follows exactly the same policy.
PYTHON_WHITESPACE = ''.join(
    map(
        chr,
        [
            *range(9, 14),
            *range(28, 33),
            0x85,
            0xA0,
            0x1680,
            *range(0x2000, 0x200B),
            0x2028,
            0x2029,
            0x202F,
            0x205F,
            0x3000,
        ],
    )
)


def selected(subtype: str | None) -> str | None:
    """Decide whether an Overture subtype belongs in the inland-water mask.

    Args:
        subtype: Value in the source's subtype column.

    Returns:
        None for eligible rows, or a count key for missing or excluded subtypes.
    """
    if not isinstance(subtype, str) or not subtype.strip():
        return 'missing_classification'
    if subtype in ('ocean', 'physical'):
        return 'excluded_classification'
    return None


def python_batch(
    raster: gdal.Dataset,
    batch: pyarrow.RecordBatch,
    counts: Counter[str],
    invalid: list[str],
    grid: tuple[int, int, float, float, float],
    tile: int,
    srs: osr.SpatialReference,
) -> None:
    """Rasterize one batch using a GDAL feature per source polygon.

    Args:
        raster: Output water mask to update in place.
        batch: Source rows containing IDs, subtypes and WKB.
        counts: Selection counts to update.
        invalid: Invalid polygon IDs to append.
        grid: (width, height, west, north, step) in grid cells and degrees.
        tile: Number of cells along one side of each tile.
        srs: Geographic coordinate reference for the features.

    Raises:
        ValueError: A selected geometry is missing, malformed or empty.
    """
    width, height, west, north, step = grid
    tiles = {}
    for item in batch.to_pylist():
        counts['rows'] += 1
        reason = selected(item['subtype'])
        if reason:
            counts[reason] += 1
            continue
        if item['geometry'] is None:
            raise ValueError(f"missing geometry: {item['id']}")
        geom = ogr.CreateGeometryFromWkb(item['geometry'])
        if geom is None or geom.IsEmpty():
            raise ValueError(f"invalid or empty WKB geometry: {item['id']}")
        if ogr.GT_Flatten(geom.GetGeometryType()) not in POLYGON:
            counts['non_polygon'] += 1
            continue
        if not geom.IsValid():
            invalid.append(item['id'])
            counts['invalid_polygon'] += 1
            continue
        xmin, xmax, ymin, ymax = geom.GetEnvelope()
        x0 = max(0, math.floor((xmin - west) / step))
        x1 = min(width - 1, math.floor((xmax - west) / step))
        y0 = max(0, math.floor((north - ymax) / step))
        y1 = min(height - 1, math.floor((north - ymin) / step))
        if x0 <= x1 and y0 <= y1:
            for ty in range(y0 // tile, y1 // tile + 1):
                for tx in range(x0 // tile, x1 // tile + 1):
                    tiles.setdefault((tx, ty), []).append(geom)
        counts['polygons'] += 1
    driver = ogr.GetDriverByName('Memory')
    for (tx, ty), geometries in tiles.items():
        x, y = tx * tile, ty * tile
        w, h = min(tile, width - x), min(tile, height - y)
        target = gdal.GetDriverByName('MEM').Create('', w, h, 1, gdal.GDT_Byte)
        target.SetGeoTransform((west + x * step, step, 0, north - y * step, 0, -step))
        target.GetRasterBand(1).WriteArray(
            raster.GetRasterBand(1).ReadAsArray(x, y, w, h)
        )
        ds = driver.CreateDataSource('')
        layer = ds.CreateLayer('water', srs, ogr.wkbUnknown)
        definition = layer.GetLayerDefn()
        for geometry in geometries:
            feat = ogr.Feature(definition)
            feat.SetGeometry(geometry)
            layer.CreateFeature(feat)
        gdal.RasterizeLayer(target, [1], layer, burn_values=[1])
        raster.GetRasterBand(1).WriteArray(target.ReadAsArray(), x, y)


def classifications(subtypes: pyarrow.Array) -> tuple[np.ndarray, int, int]:
    """Classify a batch of water subtypes with Arrow.

    Args:
        subtypes: Array of Overture subtype values.

    Returns:
        (eligible_mask, missing_count, excluded_count). The 1-D mask has a
        true value for each row eligible for inland-water rasterization.
    """
    # Arrow registers these compute kernels dynamically when the module loads.
    if pyarrow.types.is_dictionary(subtypes.type):
        subtypes = pc.dictionary_decode(subtypes)  # pyright: ignore[reportAttributeAccessIssue]
    if not (
        pyarrow.types.is_string(subtypes.type)
        or pyarrow.types.is_large_string(subtypes.type)
    ):
        return np.zeros(len(subtypes), dtype=bool), len(subtypes), 0
    trimmed = pc.utf8_trim(subtypes, characters=PYTHON_WHITESPACE)  # pyright: ignore[reportAttributeAccessIssue]
    missing = pc.or_(pc.is_null(subtypes), pc.fill_null(pc.equal(trimmed, ''), False))  # pyright: ignore[reportAttributeAccessIssue]
    excluded = pc.is_in(  # pyright: ignore[reportAttributeAccessIssue]
        subtypes, value_set=pyarrow.array(['ocean', 'physical'], type=subtypes.type)
    )
    eligible = pc.invert(pc.or_(missing, excluded)).to_numpy(zero_copy_only=False)  # pyright: ignore[reportAttributeAccessIssue]
    return (
        eligible,
        int(pc.sum(missing).as_py() or 0),  # pyright: ignore[reportAttributeAccessIssue]
        int(pc.sum(excluded).as_py() or 0),  # pyright: ignore[reportAttributeAccessIssue]
    )


class SourceIds:
    """Read source feature IDs only for rows needed in diagnostics."""

    def __init__(self, parquet: pq.ParquetFile) -> None:
        """Index the row groups in the source file.

        Args:
            parquet: Open water shard with an "id" column.
        """
        self.parquet = parquet
        self.ends = np.cumsum(
            [
                parquet.metadata.row_group(i).num_rows
                for i in range(parquet.metadata.num_row_groups)
            ],
            dtype=np.int64,
        )

    def get(self, indices: Sequence[int] | np.ndarray) -> list[str | None]:
        """Read selected feature IDs without opening unrelated row groups.

        Args:
            indices: Global zero-based row numbers with a known length.

        Returns:
            Feature IDs in input order, with None for a null ID.
        """
        groups = {}
        result: list[str | None] = [None] * len(indices)
        for output, row in enumerate(indices):
            group = int(np.searchsorted(self.ends, row, side='right'))
            start = int(self.ends[group - 1]) if group else 0
            groups.setdefault(group, []).append((output, int(row) - start))
        for group, requests in groups.items():
            ids = self.parquet.read_row_group(
                group, columns=['id'], use_threads=False
            ).column('id')
            values = ids.take([row for _, row in requests]).to_pylist()
            for (output, _), value in zip(requests, values):
                result[output] = value
        return result


def gdal_batch(
    kernel: WaterBatch,
    raster: gdal.Dataset,
    batch: pyarrow.RecordBatch,
    counts: Counter[str],
    invalid: list[str | None],
    grid: tuple[int, int, float, float, float],
    tile: int,
    ids: SourceIds,
) -> None:
    """Rasterize one selected batch and update its statistics.

    Args:
        kernel: Batch rasterizer.
        raster: Output raster to update.
        batch: Source rows containing subtypes and WKB.
        counts: Row and classification counts to update.
        invalid: Feature IDs for invalid polygons to append.
        grid: (width, height, west, north, step).
        tile: Tile size in cells.
        ids: Lookup for feature IDs used in diagnostics.

    Raises:
        ValueError: A selected geometry is missing or malformed.
    """
    first = counts['rows']
    eligible, missing, excluded = classifications(batch.column('subtype'))
    counts['rows'] += len(batch)
    if missing:
        counts['missing_classification'] += missing
    if excluded:
        counts['excluded_classification'] += excluded
    status, failed = kernel.burn(raster, batch.column('geometry'), eligible, grid, tile)
    if failed is not None:
        feature_id = ids.get([first + failed])[0]
        message = (
            'missing geometry'
            if status[failed] == GeometryStatus.MISSING
            else 'invalid or empty WKB geometry'
        )
        raise ValueError(f'{message}: {feature_id}')
    for code, name in (
        (GeometryStatus.POLYGON, 'polygons'),
        (GeometryStatus.NON_POLYGON, 'non_polygon'),
        (GeometryStatus.INVALID_POLYGON, 'invalid_polygon'),
    ):
        count = int(np.count_nonzero(status == code))
        if count:
            counts[name] += count
    invalid.extend(
        ids.get(first + np.flatnonzero(status == GeometryStatus.INVALID_POLYGON))
    )


def run(
    source: Path | str,
    expected: str,
    output: Path | str,
    config_path: Path | str,
    grid: Grid,
    *,
    settings: WaterSettings,
    minimum_free_bytes: int,
    files: RunFilePins,
    emit: Callable[..., None] = print,
) -> dict[str, Any]:
    """Verify one water shard and rasterize its eligible polygons.

    Args:
        source: Local source GeoParquet file.
        expected: SHA-256 digest for the source file.
        output: New directory for the shard mask and report.
        config_path: Saved settings and file list used for the report checksum.
        grid: Shared physical build grid.
        settings: Validated inland-water rasterizer options.
        minimum_free_bytes: Shared physical build disk reserve in bytes.
        files: Attempt-local file checksum verifier.
        emit: Progress callback.

    Returns:
        Shard report with counts, input and output digests, and timing.
    """
    source = Path(source).resolve()
    config_path = Path(config_path).resolve()
    output = Path(output).resolve()
    if (
        source == config_path
        or source.is_relative_to(output)
        or config_path.is_relative_to(output)
        or output.is_relative_to(source.parent)
        or output.is_relative_to(config_path.parent)
    ):
        raise ValueError(
            'output must be outside input directories and must not contain inputs'
        )
    config_bytes = config_path.read_bytes()
    policy = settings.get('policy', {'method': 'overture-inland-subtype-v1'})
    width, height = grid.width, grid.height
    west, north, step = grid.west, grid.north, grid.step
    tile = settings.get('tile_size', 1024)
    reserve = minimum_free_bytes
    batch_size = settings.get('batch_size', 8192)
    engine = settings.get('rasterizer', 'gdal')
    if len(expected) != 64 or files.pin(source)['sha256'] != expected.lower():
        raise ValueError('source SHA-256 does not match expected digest')
    pf = pq.ParquetFile(source, pre_buffer=False)
    md = pf.schema_arrow.metadata or {}
    geo = json.loads(md[b'geo'])
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
    kernel = None
    if engine == 'gdal':
        kernel = WaterBatch(settings.get('batch_method', 'hybrid'))
    raster = create_mask(out / 'water.tif', grid)
    srs = raster.GetSpatialRef()
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    counts = Counter()
    invalid = []
    ids = SourceIds(pf) if kernel else None
    # A feature's raster burn is identical across batches because the operation
    # is a monotone union (the mask is initialized to zero and burns only 1).
    for batch in pf.iter_batches(
        batch_size=batch_size,
        columns=['subtype', 'geometry'] if kernel else ['id', 'subtype', 'geometry'],
        use_threads=False,
    ):
        check_cancelled()
        if shutil.disk_usage(out).free < reserve:
            raise ValueError(
                'free disk below configured reserve; partial output preserved'
            )
        dimensions = (width, height, west, north, step)
        if kernel:
            gdal_batch(
                kernel,
                raster,
                batch,
                counts,
                invalid,
                dimensions,
                tile,
                cast(SourceIds, ids),
            )
        else:
            python_batch(raster, batch, counts, invalid, dimensions, tile, srs)
        # The reference path creates Python feature objects. GDAL batches own
        # and release their geometries directly and do not require cyclic GC.
        batch = None
        if kernel is None:
            gc.collect()
            pyarrow.default_memory_pool().release_unused()
        rss = 'unavailable'
        try:
            rss = next(
                (
                    line
                    for line in Path('/proc/self/status').read_text().splitlines()
                    if line.startswith('VmRSS:')
                ),
                'unavailable',
            )
        except OSError:
            pass
        emit(
            json.dumps(
                {
                    'rows': counts['rows'],
                    'polygons': counts['polygons'],
                    'invalid_polygon': counts['invalid_polygon'],
                    'rss': rss,
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
    if config_path.read_bytes() != config_bytes:
        raise ValueError('configuration changed during processing')
    if invalid:
        with (out / 'invalid-feature-ids.json').open('x') as f:
            f.write(json.dumps(invalid, indent=2) + '\n')
    report = {
        'status': (
            'incomplete-input-issues'
            if invalid or counts['missing_classification']
            else 'candidate-only'
        ),
        'source': str(source),
        'source_sha256': expected.lower(),
        'rows_in_source': pf.metadata.num_rows,
        'script_sha256': files.pin(__file__)['sha256'],
        'rasterizer': engine,
        'gdal_kernel': kernel.provenance if kernel else None,
        'batch_timings': kernel.timings if kernel else None,
        'counts': dict(counts),
        'batch_size': batch_size,
        'invalid_feature_ids': 'invalid-feature-ids.json' if invalid else None,
        'policy': policy,
        'selection_notes': settings.get('selection_notes'),
        'configuration_sha256': hashlib.sha256(config_bytes).hexdigest(),
        'geometry_policy': 'GEOS validity checked; invalid geometries excluded and IDs reported; no repair',
        'grid': vars(grid),
        'rasterization': f'GDAL default polygon rasterization, ALL_TOUCHED off; values unioned per batch on {tile}-cell tiles',
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
        'output_sha256': files.pin(out / 'water.tif')['sha256'],
        'limitations': 'Candidate water mask only, not a historical or complete physical mask. Review invalid features and compare against preserved references before use.',
    }
    with (out / 'report.json').open('x') as f:
        f.write(json.dumps(report, indent=2) + '\n')
    return report
