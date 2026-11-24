"""Verify and open selected physical raster and vector inputs."""

from pathlib import Path
from typing import Literal

from osgeo import gdal, ogr, osr

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.execution.runtime import RunFilePins
from worldatlas.map_build.inputs.configuration import LandLayer
from worldatlas.shared.files import FilePin


class ShardMask(FilePin):
    """Pin one completed water mask and its report."""

    status: Literal['candidate-only']
    report: FilePin


def checked_files(spec: LandLayer[FilePin], pins: RunFilePins) -> dict[str, str]:
    """Verify all files that can affect the selected vector dataset.

    Args:
        spec: Dataset path and checksums for every required file.
        pins: Attempt-local file checksum verifier.

    Returns:
        Absolute path strings mapped to SHA-256 digests.

    Raises:
        ValueError: A file path is repeated within the layer, or a required file
            or Shapefile companion is unpinned or changed.
    """
    files = {str(Path(f['path']).resolve()): f['sha256'] for f in spec['files']}
    if len(files) != len(spec['files']):
        raise ValueError('coastline file paths must be unique within each layer')
    dataset = str(Path(spec['dataset']).resolve())
    if dataset not in files:
        raise ValueError('dataset must be among hash-pinned files')
    if dataset.lower().endswith('.shp'):
        shapefile = Path(dataset)
        stem = shapefile.with_suffix('')
        for ext in ('.shp', '.shx', '.dbf', '.prj'):
            if str(shapefile.with_suffix(ext)) not in files:
                raise ValueError('shapefile needs pinned .shp, .shx, .dbf and .prj')
        # Sidecars may change interpretation; no untracked companion permitted.
        for p in stem.parent.glob(stem.name + '.*'):
            if p.is_file() and str(p.resolve()) not in files:
                raise ValueError(f'unpinned shapefile companion: {p}')
    for p, expected in files.items():
        if pins.pin(p)['sha256'] != expected:
            raise ValueError(f'input digest mismatch: {p}')
    return files


def open_coastline_layer(spec: LandLayer[FilePin]) -> tuple[gdal.Dataset, ogr.Layer]:
    """Open a coastline layer in longitude and latitude and apply its selection.

    Args:
        spec: Dataset path, optional layer name, and explicit filter.

    Returns:
        The dataset and selected layer. Keep the dataset alive while reading the layer.

    Raises:
        ValueError: The layer, coordinate reference, filter, or ID lookup is unavailable.
    """
    ds = ogr.Open(spec['dataset'], 0)
    if ds is None:
        raise ValueError(f"cannot open dataset: {spec['dataset']}")
    layer_name = spec.get('layer')
    layer = ds.GetLayerByName(layer_name) if layer_name else ds.GetLayer(0)
    if layer is None:
        raise ValueError('layer not found')
    if not layer.TestCapability(ogr.OLCRandomRead):
        raise ValueError(
            f"coastline layer must support lookup by feature ID: {spec['dataset']}"
        )
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
    return ds, layer


def create_mask(path: Path, grid: Grid) -> gdal.Dataset:
    """Create a tiled, one-bit GeoTIFF on the shared physical grid.

    Args:
        path: New TIFF file.
        grid: Validated WGS84 physical grid.

    Returns:
        Writable single-band GDAL dataset.
    """
    dataset = gdal.GetDriverByName('GTiff').Create(
        str(path),
        grid.width,
        grid.height,
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
    dataset.SetGeoTransform((grid.west, grid.step, 0, grid.north, 0, -grid.step))
    spatial_reference = osr.SpatialReference()
    spatial_reference.ImportFromEPSG(4326)
    dataset.SetSpatialRef(spatial_reference)
    return dataset


def open_mask(entry: FilePin, grid: Grid, files: RunFilePins) -> gdal.Dataset:
    """Open a physical mask after checking its grid and file contents.

    Args:
        entry: File path and expected SHA-256.
        grid: Shared raster dimensions, origin and step.
        files: Attempt-local file checksum verifier.

    Returns:
        GDAL dataset for the aligned WGS84 raster.

    Raises:
        ValueError: The hash, grid or coordinate reference differs.
    """
    path = Path(entry['path']).resolve()
    if files.pin(path)['sha256'] != entry['sha256']:
        raise ValueError(f'input hash mismatch: {path}')
    ds = gdal.Open(str(path))
    if (
        ds is None
        or ds.RasterXSize != grid.width
        or ds.RasterYSize != grid.height
        or ds.GetGeoTransform() != (grid.west, grid.step, 0, grid.north, 0, -grid.step)
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
