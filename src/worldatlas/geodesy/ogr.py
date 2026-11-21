"""Share GDAL's batch geometry writer across geographic pipelines."""

import pyarrow as pa
from osgeo import gdal, ogr, osr


def geometry_layer(
    geometry: pa.Array, srs: osr.SpatialReference | None
) -> tuple[gdal.Dataset, ogr.Layer]:
    """Write an Arrow geometry column to an in-memory GDAL layer.

    Args:
        geometry: Column of binary WKB geometry values.
        srs: Coordinate reference for the column.

    Returns:
        (dataset, layer). Keep the dataset alive while using the layer.

    Raises:
        ValueError: The layer could not write the full batch.
    """
    dataset = ogr.GetDriverByName('Memory').CreateDataSource('')
    layer = dataset.CreateLayer('geometry', srs, ogr.wkbUnknown)
    schema = pa.schema(
        [
            pa.field(
                'wkb_geometry',
                geometry.type,
                metadata={b'ARROW:extension:name': b'ogc.wkb'},
            )
        ]
    )
    if layer.WriteArrow(pa.record_batch([geometry], schema=schema)):
        raise ValueError('GDAL Arrow layer write failed')
    if layer.GetFeatureCount() != len(geometry):
        raise ValueError('GDAL Arrow layer count mismatch')
    return dataset, layer
