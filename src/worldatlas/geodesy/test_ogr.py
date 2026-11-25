"""Check the shared GDAL layer writer's geometry and failure handling."""

import unittest
from unittest.mock import patch

from osgeo import ogr, osr
import pyarrow as pa

from worldatlas.geodesy.ogr import geometry_layer


class GeometryLayerTests(unittest.TestCase):
    def setUp(self):
        point = ogr.CreateGeometryFromWkt("POINT (12 34)")
        self.geometry = pa.array([bytes(point.ExportToWkb())])

    def test_persists_the_batch_with_its_coordinate_reference(self):
        crs = osr.SpatialReference()
        crs.SetFromUserInput("OGC:CRS84")
        dataset, layer = geometry_layer(self.geometry, crs)
        with dataset:
            self.assertTrue(layer.GetSpatialRef().IsSame(crs))
            feature = layer.GetNextFeature()
            point = feature.GetGeometryRef()
            self.assertEqual(point.GetPoint_2D(), (12, 34))

    def test_reports_failed_or_incomplete_gdal_batches(self):
        for result, message in (
            (1, "GDAL Arrow layer write failed"),
            (0, "GDAL Arrow layer count mismatch"),
        ):
            with self.subTest(result=result):
                with patch.object(ogr.Layer, "WriteArrow", return_value=result):
                    with self.assertRaisesRegex(ValueError, message):
                        geometry_layer(self.geometry, None)
