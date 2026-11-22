#!/usr/bin/env python3
"""Rasterize hash-pinned EPSG:4326 polygon land into a one-bit candidate mask."""

import hashlib
import json
import math
import os
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

from osgeo import gdal, ogr, osr

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.physical.sources import checked_files, open_layer
from worldatlas.shared.files import sha256_file

gdal.UseExceptions()


def run(
    config_path: Path | str,
    output: Path | str,
    grid: Grid,
    *,
    emit: Callable[..., None] = print,
) -> dict[str, Any]:
    """Mark each grid cell whose centre lies in a selected coastline polygon.

    Args:
        config_path: JSON settings with pinned coastline layers.
        output: New directory for the land raster and report.
        grid: Shared physical build grid.
        emit: Progress callback.

    Returns:
        Report with selected layer counts, the grid, and the land raster's SHA-256.
    """
    config_path = Path(config_path).resolve()
    data = config_path.read_bytes()
    cfg = json.loads(data)
    if cfg.get('schema') != 'land-raster-candidate-v1' or not cfg.get(
        'selection_notes'
    ):
        raise ValueError('explicit schema and selection notes required')
    width, height = grid.width, grid.height
    west, north, step = grid.west, grid.north, grid.step
    specs = cfg['land']
    if not isinstance(specs, list) or not specs:
        raise ValueError('nonempty explicitly pinned land inputs required')
    strip = cfg.get('strip_rows', 512)
    reserve = cfg.get('minimum_free_bytes', 2 * (1 << 30))
    if not isinstance(strip, int) or isinstance(strip, bool) or strip < 1:
        raise ValueError('invalid strip_rows')
    if not isinstance(reserve, int) or isinstance(reserve, bool) or reserve < 0:
        raise ValueError('invalid free-space reserve')
    feature_index = cfg.get('feature_index', 'row-fids')
    if feature_index not in ('row-fids', 'scan'):
        raise ValueError('feature_index must be row-fids or scan')
    output = Path(output).resolve()
    paths = [config_path] + [
        Path(f['path']).resolve() for spec in specs for f in spec['files']
    ]
    if len(set(paths)) != len(paths):
        raise ValueError('input paths must be unique')
    if any(p.is_relative_to(output) or output.is_relative_to(p.parent) for p in paths):
        raise ValueError(
            'output must be outside input directories and must not contain inputs'
        )
    # Validate all files, CRS, selection and geometries before creating outputs.
    for spec in specs:
        checked_files(spec)
    opened = []
    indexes = []
    for spec in specs:
        rows = (
            [[] for _ in range((height + strip - 1) // strip)]
            if feature_index == 'row-fids'
            else None
        )
        usable = True

        def index_feature(feat: ogr.Feature, geometry: ogr.Geometry) -> None:
            """Index a selected polygon in the tiles it can affect.

            Args:
                feat: Feature from the source vector layer.
                geometry: Polygon or multipolygon attached to the feature.
            """
            nonlocal usable
            fid = feat.GetFID()
            assert rows is not None
            if fid < 0:
                usable = False
                return
            xmin, xmax, ymin, ymax = geometry.GetEnvelope()
            if xmax < west or xmin > west + width * step:
                return
            first = max(0, math.floor((north - ymax) / step))
            last = min(height - 1, math.floor((north - ymin) / step))
            if first <= last:
                for row in range(first // strip, last // strip + 1):
                    rows[row].append(fid)

        item = open_layer(
            spec, feature_callback=index_feature if rows is not None else None
        )
        opened.append(item)
        indexes.append(
            rows if usable and item[1].TestCapability(ogr.OLCRandomRead) else None
        )
    feature_counts = [item[2] for item in opened]
    os.mkdir(output)
    ds = gdal.GetDriverByName('GTiff').Create(
        str(output / 'land.tif'),
        width,
        height,
        1,
        gdal.GDT_Byte,
        options=[
            'TILED=YES',
            'BLOCKXSIZE=512',
            'BLOCKYSIZE=512',
            'NBITS=1',
            'COMPRESS=DEFLATE',
            'SPARSE_OK=YES',
            'BIGTIFF=YES',
        ],
    )
    ds.SetGeoTransform((west, step, 0, north, 0, -step))
    sr = osr.SpatialReference()
    sr.ImportFromEPSG(4326)
    ds.SetSpatialRef(sr)
    land_cells = 0
    for y in range(0, height, strip):
        if shutil.disk_usage(output).free < reserve:
            raise ValueError(
                'free disk below configured reserve; partial output preserved'
            )
        n = min(strip, height - y)
        top = north - y * step
        mem = gdal.GetDriverByName('MEM').Create('', width, n, 1, gdal.GDT_Byte)
        mem.SetGeoTransform((west, step, 0, top, 0, -step))
        for (_, layer, _), index in zip(opened, indexes):
            if index is None:
                layer.SetSpatialFilterRect(
                    west, top - n * step, west + width * step, top
                )
                layer.ResetReading()
                gdal.RasterizeLayer(mem, [1], layer, burn_values=[1])
                layer.SetSpatialFilter(None)
            else:
                # Preserve source order and coordinates. Envelope candidates may
                # include a polygon that burns no pixels; GDAL clips it exactly.
                vector = ogr.GetDriverByName('Memory').CreateDataSource('')
                selected_layer = vector.CreateLayer(
                    'land', layer.GetSpatialRef(), ogr.wkbUnknown
                )
                definition = selected_layer.GetLayerDefn()
                for fid in index[y // strip]:
                    source = layer.GetFeature(fid)
                    if source is None:
                        raise ValueError(f'indexed land feature missing: {fid}')
                    feature = ogr.Feature(definition)
                    feature.SetGeometry(source.GetGeometryRef())
                    selected_layer.CreateFeature(feature)
                gdal.RasterizeLayer(mem, [1], selected_layer, burn_values=[1])
                selected_layer = None
                vector = None
        values = mem.ReadAsArray()
        land_cells += int(values.sum())
        ds.GetRasterBand(1).WriteArray(values, 0, y)
        emit(json.dumps({'rows_done': y + n, 'land_cells': land_cells}), flush=True)
    ds.FlushCache()
    ds = None
    opened = []
    for spec in specs:
        checked_files(spec)
    if config_path.read_bytes() != data:
        raise ValueError('configuration changed during processing')
    report = {
        'status': 'candidate-only',
        'configuration_sha256': hashlib.sha256(data).hexdigest(),
        'grid': vars(grid),
        'feature_counts': feature_counts,
        'feature_index': feature_index,
        'indexed_layers': [index is not None for index in indexes],
        'land_cells': land_cells,
        'land_sha256': sha256_file(output / 'land.tif'),
        'gdal': gdal.VersionInfo('--version'),
        'rasterization': 'GDAL default polygon rasterization, ALL_TOUCHED off',
        'limitations': 'Candidate mask only; source decisions and geographic correctness require review.',
    }
    with (output / 'config.json').open('xb') as f:
        f.write(data)
    with (output / 'report.json').open('x') as f:
        json.dump(report, f, indent=2)
        f.write('\n')
    return report
