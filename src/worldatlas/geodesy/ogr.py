"""Share GDAL's batch geometry writer across geographic pipelines."""

from osgeo import ogr
import pyarrow as pa


def geometry_layer(geometry, srs):
    """Populate an in-memory GDAL layer from an Arrow WKB column.

    Args:
        geometry: Arrow array of Well-Known Binary geometries.
        srs: Coordinate reference of those geometries.

    Returns:
        The owning dataset and its layer. Keep the dataset alive while using the layer.

    Raises:
        ValueError: GDAL failed to write the complete batch.
    """
    dataset = ogr.GetDriverByName('Memory').CreateDataSource('')
    layer = dataset.CreateLayer('geometry', srs, ogr.wkbUnknown)
    schema = pa.schema(
        [pa.field('wkb_geometry', geometry.type, metadata={b'ARROW:extension:name': b'ogc.wkb'})]
    )
    if layer.WriteArrow(pa.record_batch([geometry], schema=schema)):
        raise ValueError('GDAL Arrow layer write failed')
    if layer.GetFeatureCount() != len(geometry):
        raise ValueError('GDAL Arrow layer count mismatch')
    return dataset, layer
