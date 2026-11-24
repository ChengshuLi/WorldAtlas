"""Prepared polygons retain holes/wrapping and do not repeat source parsing."""

import math
from unittest.mock import patch
import unittest
import numpy as np
from osgeo import gdal, ogr
from shapely.geometry import Point, Polygon, box, shape
from worldatlas.map_build.core.geometry import (
    PolygonRasterizer,
    polygon_grid_bounds,
)
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
            "worldatlas.map_build.core.geometry.ogr.CreateGeometryFromWkb",
            wraps=ogr.CreateGeometryFromWkb,
        ) as parse:
            prepared = PolygonRasterizer(shape(geometry), grid)
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
        prepared = PolygonRasterizer(box(0, -80, 10, -70), grid)
        self.assertFalse(prepared.rasterize((0, 36, 0, 10))[1].any())
        bounds, mask = prepared.rasterize()
        self.assertEqual(bounds, (18, 19, 10, 10))
        self.assertEqual(mask.shape, (0, 1))
        self.assertEqual(prepared.rasterize()[0], bounds)

    def test_rasterization_rejects_invalid_windows_and_propagates_gdal_errors(self):
        grid = Grid(36, 18, 10)
        prepared = PolygonRasterizer(box(0, 0, 20, 20), grid)
        with self.assertRaisesRegex(ValueError, "invalid rasterization window"):
            prepared.rasterize((0, 37, 0, 18))
        with patch.object(gdal, "RasterizeLayer", return_value=1):
            with self.assertRaisesRegex(ValueError, "polygon rasterization failed"):
                prepared.rasterize()


class PolygonBounds(unittest.TestCase):
    def test_touching_longitude_spans_cover_the_entire_grid(self):
        geometry = dict(
            type="MultiPolygon",
            coordinates=[[ring(-180, 0, 0, 30)], [ring(0, -30, 180, 0)]],
        )
        self.assertEqual(
            polygon_grid_bounds(shape(geometry), Grid(24, 12, 15)),
            (0, 24, 4, 8),
        )

    def test_window_rounded_outwards_can_cover_entire_width(self):
        self.assertEqual(
            polygon_grid_bounds(box(-179, 0, 179, 30), Grid(24, 12, 15)),
            (0, 24, 4, 6),
        )

    def test_requires_a_nonempty_polygon_with_a_longitude_span(self):
        grid = Grid(24, 12, 15)
        for geometry in (Point(0, 0), Polygon()):
            with self.subTest(geometry=geometry), self.assertRaisesRegex(
                ValueError, "nonempty Polygon"
            ):
                polygon_grid_bounds(geometry, grid)
        # The shape has area, but its tiny longitude span collapses when
        # the coordinates are measured from the grid's western edge.
        with self.assertRaisesRegex(ValueError, "invalid polygon grid bounds"):
            polygon_grid_bounds(box(0, 0, math.ulp(1.0), 30), grid)
