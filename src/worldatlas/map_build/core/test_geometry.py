"""Prepared polygons retain holes/wrapping and do not repeat source parsing."""

import math
from unittest.mock import patch
import unittest
import numpy as np
from osgeo import ogr
from worldatlas.map_build.core.geometry import PolygonRasterizer
from worldatlas.map_build.core.grid import Grid


def ring(west, south, east, north):
    return [[west, south], [east, south], [east, north], [west, north], [west, south]]


class PreparedRasterization(unittest.TestCase):
    def test_point_lookup_wraps_only_the_actual_antimeridian(self):
        grid = Grid(36, 9, 10)
        self.assertEqual(grid.cell_at(-180, 5), (0, 8))
        self.assertEqual(grid.cell_at(180, 5), (0, 8))
        self.assertEqual(grid.cell_at(math.nextafter(180, -math.inf), 5), (35, 8))
        self.assertIsNone(grid.cell_at(0, -5))

    def test_repeated_windows_match_known_cells_including_holes_and_seam(self):
        grid = Grid(36, 18, 10)
        geometry = dict(
            type="MultiPolygon",
            coordinates=[
                [ring(-20, -20, 20, 20), ring(-10, -10, 10, 10)],
                [ring(160, 0, 180, 10)],
                [ring(-180, 0, -160, 10)],
            ],
        )
        with patch(
            "worldatlas.map_build.core.geometry.ogr.CreateGeometryFromJson",
            wraps=ogr.CreateGeometryFromJson,
        ) as parse:
            prepared = PolygonRasterizer(geometry, grid)
            expected = np.zeros((18, 36), dtype=bool)
            expected[7:11, 16:20] = True
            expected[8:10, 17:19] = False
            expected[8, 0:2] = True
            expected[8, 34:36] = True
            for first, last in ((9, 18), (0, 9), (0, 18), (7, 11)):
                _, actual = prepared.rasterize((0, 36, first, last))
                np.testing.assert_array_equal(actual, expected[first:last])
            self.assertEqual(parse.call_count, 1)
            _, wrapped = prepared.rasterize((34, 38, 8, 9))
            self.assertTrue(wrapped.all())

    def test_explicit_window_can_be_outside_the_source_polygon(self):
        grid = Grid(36, 10, 10)
        prepared = PolygonRasterizer(
            dict(type="Polygon", coordinates=[ring(0, -80, 10, -70)]), grid
        )
        self.assertFalse(prepared.rasterize((0, 36, 0, 10))[1].any())
