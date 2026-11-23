"""Share GDAL's batch geometry writer across geographic pipelines."""

import pyarrow as pa
from osgeo import gdal, ogr, osr


def geometry_layer(
    geometry: pa.Array, srs: osr.SpatialReference | None
) -> tuple[gdal.Dataset, ogr.Layer]:
    """Load a batch of shapes into a temporary GDAL layer in memory.

    Each shape becomes one feature. For example, three river lines become
    three features that the watershed importer can use to mark elevation
    cells. The map builder uses the same layer format for water polygons.

    Args:
        geometry: Arrow array with one shape per element, encoded as WKB
            (Well-Known Binary).
        srs: Coordinate reference of the existing coordinates, or None if
            unspecified. For example, river lines use longitude and latitude.

    Returns:
        (dataset, layer). The dataset owns the temporary data and must stay
        alive while the caller uses the layer.

    Raises:
        ValueError: GDAL reports a write error or the feature count differs
            from the number of input shapes.
    """
    dataset = ogr.GetDriverByName('Memory').CreateDataSource('')
    layer = dataset.CreateLayer('geometry', srs, ogr.wkbUnknown)
    schema = pa.schema(
        [
            pa.field(
                'wkb_geometry',
                geometry.type,
                # GDAL uses this tag to recognize the bytes as shapes.
                metadata={b'ARROW:extension:name': b'ogc.wkb'},
            )
        ]
    )
    if layer.WriteArrow(pa.record_batch([geometry], schema=schema)):
        raise ValueError('GDAL Arrow layer write failed')
    if layer.GetFeatureCount() != len(geometry):
        raise ValueError('GDAL Arrow layer count mismatch')
    return dataset, layer
