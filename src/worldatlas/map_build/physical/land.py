#!/usr/bin/env python3
"""Rasterize hash-pinned EPSG:4326 polygon land into a one-bit candidate mask."""

import json
import math
import os
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from osgeo import gdal, ogr

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.execution.control import check_cancelled
from worldatlas.map_build.execution.runtime import RunFilePins
from worldatlas.map_build.inputs.configuration import LandLayer, LandSettings
from worldatlas.map_build.physical.sources import (
    checked_files,
    create_mask,
    open_coastline_layer,
)
from worldatlas.shared.files import FilePin

gdal.UseExceptions()


@dataclass
class _IndexedLandLayer:
    """Keep an open coastline layer and its polygon IDs for each strip."""

    dataset: gdal.Dataset  # The layer depends on this dataset staying open.
    layer: ogr.Layer
    feature_count: int
    feature_ids_by_strip: list[list[int]]


def _index_land_layer(
    spec: LandLayer[FilePin], grid: Grid, strip_rows: int
) -> _IndexedLandLayer:
    """List which coastline polygons could touch each horizontal strip.

    Args:
        spec: Coastline dataset and selection to index.
        grid: Shared physical build grid.
        strip_rows: Maximum number of map rows per strip.

    Returns:
        The open source layer and ordered lists of polygon IDs, one per strip.

    Raises:
        ValueError: The selection is empty or contains a missing ID or invalid polygon.
    """
    strip_count = (grid.height + strip_rows - 1) // strip_rows
    feature_ids_by_strip: list[list[int]] = [[] for _ in range(strip_count)]
    west = grid.west
    east = west + grid.width * grid.step
    dataset, layer = open_coastline_layer(spec)
    feature_count = 0
    for feature in layer:
        feature_id = feature.GetFID()
        if feature_id < 0:
            raise ValueError(
                f"coastline polygon is missing a feature ID: {spec['dataset']}"
            )
        geometry = feature.GetGeometryRef()
        if geometry is None or geometry.IsEmpty():
            raise ValueError(f'empty geometry at feature {feature_id}')
        if ogr.GT_Flatten(geometry.GetGeometryType()) not in (
            ogr.wkbPolygon,
            ogr.wkbMultiPolygon,
        ):
            raise ValueError(f'nonpolygon geometry at feature {feature_id}')
        if not geometry.IsValid():
            raise ValueError(f'invalid geometry at feature {feature_id}')
        feature_count += 1

        # Index bounds so GDAL only fetches polygons that might touch the strip.
        xmin, xmax, ymin, ymax = geometry.GetEnvelope()
        if xmax < west or xmin > east:
            continue
        first_row = max(0, math.floor((grid.north - ymax) / grid.step))
        last_row = min(grid.height - 1, math.floor((grid.north - ymin) / grid.step))
        if first_row <= last_row:
            for strip in range(first_row // strip_rows, last_row // strip_rows + 1):
                feature_ids_by_strip[strip].append(feature_id)

    if not feature_count:
        raise ValueError('selection yielded no features')
    return _IndexedLandLayer(dataset, layer, feature_count, feature_ids_by_strip)


def _rasterize_strip(
    target: gdal.Dataset, source: _IndexedLandLayer, strip: int
) -> None:
    """Draw the candidate coastline polygons for one strip.

    Args:
        target: Writable raster for this strip. Land cells are set to 1 in place.
        source: Coastline layer and its lists of polygon IDs.
        strip: Zero-based strip index.

    Raises:
        ValueError: A polygon ID from the index cannot be read from the layer.
    """
    with ogr.GetDriverByName('Memory').CreateDataSource('') as vector:
        selected = vector.CreateLayer(
            'land', source.layer.GetSpatialRef(), ogr.wkbUnknown
        )
        definition = selected.GetLayerDefn()
        # Retain the original order and coordinates. GDAL clips each polygon to the strip.
        for feature_id in source.feature_ids_by_strip[strip]:
            polygon = source.layer.GetFeature(feature_id)
            if polygon is None:
                raise ValueError(f'indexed land feature missing: {feature_id}')
            feature = ogr.Feature(definition)
            feature.SetGeometry(polygon.GetGeometryRef())
            selected.CreateFeature(feature)
        gdal.RasterizeLayer(target, [1], selected, burn_values=[1])


def run(
    configuration_sha256: str,
    output: Path | str,
    grid: Grid,
    *,
    settings: LandSettings[FilePin],
    minimum_free_bytes: int,
    files: RunFilePins,
    emit: Callable[..., None] = print,
) -> dict[str, Any]:
    """Mark each grid cell whose centre lies in a selected coastline polygon.

    Args:
        configuration_sha256: Checksum of the saved stage settings.
        output: New directory for the land raster and report.
        grid: Shared physical build grid.
        settings: Local coastline files, selection, and rasterization options.
        minimum_free_bytes: Shared physical build disk reserve in bytes.
        files: Attempt-local file checksum verifier.
        emit: Progress callback.

    Returns:
        Report with selected layer counts, the grid, and the land raster's SHA-256.
    """
    width, height = grid.width, grid.height
    west, north, step = grid.west, grid.north, grid.step
    specs = settings['land']
    if not specs:
        raise ValueError('nonempty explicitly pinned land inputs required')
    strip_rows = settings.get('strip_rows', 512)
    output = Path(output).resolve()
    # Check the input files and index the selected polygons before creating outputs.
    for spec in specs:
        checked_files(spec, files)
    layers = [_index_land_layer(spec, grid, strip_rows) for spec in specs]
    feature_counts = [source.feature_count for source in layers]
    os.mkdir(output)
    land_mask = create_mask(output / 'land.tif', grid)
    land_cells = 0
    for strip, first_row in enumerate(range(0, height, strip_rows)):
        check_cancelled()
        if shutil.disk_usage(output).free < minimum_free_bytes:
            raise ValueError(
                'free disk below configured reserve; partial output preserved'
            )
        row_count = min(strip_rows, height - first_row)
        top = north - first_row * step
        strip_raster = gdal.GetDriverByName('MEM').Create(
            '', width, row_count, 1, gdal.GDT_Byte
        )
        strip_raster.SetGeoTransform((west, step, 0, top, 0, -step))
        for source in layers:
            _rasterize_strip(strip_raster, source, strip)
        values = strip_raster.ReadAsArray()
        land_cells += int(values.sum())
        land_mask.GetRasterBand(1).WriteArray(values, 0, first_row)
        emit(
            json.dumps({'rows_done': first_row + row_count, 'land_cells': land_cells}),
            flush=True,
        )
    check_cancelled()
    land_mask.Close()
    for spec in specs:
        checked_files(spec, files)
    report = {
        'status': 'candidate-only',
        'configuration_sha256': configuration_sha256,
        'grid': vars(grid),
        'feature_counts': feature_counts,
        'land_cells': land_cells,
        'land_sha256': files.pin(output / 'land.tif')['sha256'],
        'gdal': gdal.VersionInfo('--version'),
    }
    with (output / 'report.json').open('x') as f:
        json.dump(report, f, indent=2)
        f.write('\n')
    return report
