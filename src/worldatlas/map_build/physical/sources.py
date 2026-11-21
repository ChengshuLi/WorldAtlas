"""Verify selected vector inputs and read physical comparison streams."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
from osgeo import gdal, ogr, osr

from worldatlas.shared.files import sha256_file


def checked_files(spec: dict[str, Any]) -> dict[str, str]:
    """Verify all files that can affect the selected vector dataset.

    Args:
        spec: Dataset path and checksums for every required file.

    Returns:
        Absolute path strings mapped to SHA-256 digests.

    Raises:
        ValueError: A required file or Shapefile companion is unpinned or changed.
    """
    files = {str(Path(f['path']).resolve()): f['sha256'] for f in spec['files']}
    dataset = str(Path(spec['dataset']).resolve())
    if dataset not in files:
        raise ValueError('dataset must be among hash-pinned files')
    if dataset.lower().endswith('.shp'):
        stem = Path(dataset).with_suffix('')
        for ext in ('.shp', '.shx', '.dbf', '.prj'):
            if str(stem.with_suffix(ext)) not in files:
                raise ValueError('shapefile needs pinned .shp, .shx, .dbf and .prj')
        # Sidecars may change interpretation; no untracked companion permitted.
        for p in stem.parent.glob(stem.name + '.*'):
            if p.is_file() and str(p.resolve()) not in files:
                raise ValueError(f'unpinned shapefile companion: {p}')
    for p, expected in files.items():
        if len(expected) != 64 or sha256_file(p) != expected.lower():
            raise ValueError(f'input digest mismatch: {p}')
    return files


def open_layer(
    spec: dict[str, Any],
    *,
    feature_callback: Callable[[ogr.Feature, ogr.Geometry], None] | None = None,
) -> tuple[gdal.Dataset, ogr.Layer, int]:
    """Read and validate a selected polygon layer.

    Args:
        spec: Dataset path, optional layer name, and explicit filter.
        feature_callback: Optional function called with each selected feature
            and polygon.

    Returns:
        (dataset, layer, feature_count). Keep dataset alive while reading layer.

    Raises:
        ValueError: The layer, CRS, filter or selected polygon is invalid.
    """
    ds = ogr.Open(spec['dataset'], 0)
    if ds is None:
        raise ValueError(f"cannot open dataset: {spec['dataset']}")
    layer = ds.GetLayerByName(spec['layer']) if spec.get('layer') else ds.GetLayer(0)
    if layer is None:
        raise ValueError('layer not found')
    srs = layer.GetSpatialRef()
    expected = osr.SpatialReference()
    expected.ImportFromEPSG(4326)
    if srs is not None:
        srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    expected.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    if srs is None or not srs.IsSame(expected):
        raise ValueError(
            'layer must explicitly declare EPSG:4326; reprojection is not implicit'
        )
    if 'where' not in spec:
        raise ValueError(
            'selection predicate must be explicit; null means all features'
        )
    if spec['where'] is not None:
        if layer.SetAttributeFilter(spec['where']) != ogr.OGRERR_NONE:
            raise ValueError('invalid source selection predicate')
    count = 0
    for feat in layer:
        geom = feat.GetGeometryRef()
        if geom is None or geom.IsEmpty():
            raise ValueError(f'empty geometry at feature {feat.GetFID()}')
        if ogr.GT_Flatten(geom.GetGeometryType()) not in (
            ogr.wkbPolygon,
            ogr.wkbMultiPolygon,
        ):
            raise ValueError(f'nonpolygon geometry at feature {feat.GetFID()}')
        if not geom.IsValid():
            raise ValueError(
                f'invalid geometry at feature {feat.GetFID()} (no repair performed)'
            )
        if feature_callback is not None:
            feature_callback(feat, geom)
        count += 1
    layer.ResetReading()
    if not count:
        raise ValueError('selection yielded no features')
    return ds, layer, count


def open_mask(entry: dict[str, Any], grid: dict[str, Any]) -> gdal.Dataset:
    """Open a physical mask after checking its grid and file contents.

    Args:
        entry: File path and expected SHA-256.
        grid: Shared raster dimensions, origin and step.

    Returns:
        GDAL dataset for the aligned WGS84 raster.

    Raises:
        ValueError: The hash, grid or coordinate reference differs.
    """
    path = Path(entry['path']).resolve()
    if sha256_file(path) != entry['sha256']:
        raise ValueError(f'input hash mismatch: {path}')
    ds = gdal.Open(str(path))
    w, h, west, north, step = (
        grid[k] for k in ('width', 'height', 'west', 'north', 'step')
    )
    if (
        ds is None
        or ds.RasterXSize != w
        or ds.RasterYSize != h
        or ds.GetGeoTransform() != (west, step, 0, north, 0, -step)
    ):
        raise ValueError(f'grid mismatch: {path}')
    actual = ds.GetSpatialRef()
    expected = osr.SpatialReference()
    expected.ImportFromEPSG(4326)
    if actual is None:
        raise ValueError(f'missing CRS: {path}')
    actual.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    expected.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    if not actual.IsSame(expected):
        raise ValueError(f'CRS mismatch: {path}')
    return ds


def validate_reference(
    ref: dict[str, Any], width: int, height: int
) -> tuple[np.ndarray, np.ndarray]:
    """Verify the physical reference files and load their run arrays.

    Args:
        ref: Pins for the reference rows and runs.
        width: Expected row width.
        height: Expected number of rows.

    Returns:
        Row-offset array and N-by-2 array of (end_column, physical_code).
    """
    for key in ('rows', 'runs'):
        if sha256_file(ref[key]['path']) != ref[key]['sha256']:
            raise ValueError(f'reference {key} digest mismatch')
    rows = np.memmap(ref['rows']['path'], dtype='<u4', mode='r')
    runs = np.memmap(ref['runs']['path'], dtype='<u4', mode='r')
    if (
        len(rows) != height + 1
        or len(runs) % 2
        or rows[0] != 0
        or rows[-1] != len(runs) // 2
    ):
        raise ValueError('invalid reference stream lengths/offsets')
    if np.any(rows[1:] < rows[:-1]):
        raise ValueError('reference offsets not monotone')
    return rows, runs.reshape(-1, 2)


def compare_row(
    values: np.ndarray, ref_runs: np.ndarray, width: int
) -> tuple[int, list[tuple[int, int, int, int]]]:
    """Compare one physical row with its reference runs.

    Args:
        values: One physical code per candidate cell.
        ref_runs: N-by-2 reference run array with end columns and codes.
        width: Number of cells in this row.

    Returns:
        (changed_cell_count, changes), with each change recorded as
        (first_column, end_column, old_code, new_code).
    """
    ends = ref_runs[:, 0]
    codes = ref_runs[:, 1]
    if (
        not len(ends)
        or ends[0] == 0
        or ends[-1] != width
        or np.any(ends[1:] <= ends[:-1])
        or np.any(~np.isin(codes, [1, 17]))
    ):
        raise ValueError('invalid reference row')
    actual_ends = np.flatnonzero(np.r_[values[1:] != values[:-1], True]) + 1
    cuts = np.unique(np.r_[0, ends, actual_ends])
    x = cuts[:-1]
    old = codes[np.searchsorted(ends, x, side='right')]
    new = values[x]
    bad = old != new
    return int(np.diff(cuts)[bad].sum()), [
        (int(a), int(b), int(c), int(d))
        for a, b, c, d in zip(x[bad], cuts[1:][bad], old[bad], new[bad])
    ]
