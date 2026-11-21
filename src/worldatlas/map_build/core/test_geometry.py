"""Prepared polygons retain holes/wrapping and do not repeat source parsing."""

import math
from unittest.mock import patch
import unittest
import numpy as np
from osgeo import gdal, ogr
from worldatlas.map_build.core.geometry import PolygonRasterizer, reject_boundary_centers
from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.wrapping import wrapped_grid_bounds


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
        bounds, mask = prepared.rasterize()
        self.assertEqual(bounds, (18, 19, 10, 10))
        self.assertEqual(mask.shape, (0, 1))
        self.assertEqual(prepared.rasterize()[0], bounds)

    def test_degenerate_rings_and_invalid_windows_are_rejected(self):
        grid = Grid(36, 18, 10)
        crossed = [[0, 0], [20, 20], [0, 20], [20, 0], [0, 0]]
        with self.assertRaisesRegex(ValueError, "invalid polygon geometry"):
            PolygonRasterizer(dict(type="Polygon", coordinates=[crossed]), grid)
        prepared = PolygonRasterizer(
            dict(type="Polygon", coordinates=[ring(0, 0, 20, 20)]), grid
        )
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
            wrapped_grid_bounds(geometry, 24, 12, 15),
            ((0, 24, 4, 8), ((0, 24),)),
        )

    def test_window_rounded_outwards_can_cover_entire_width(self):
        geometry = dict(type="Polygon", coordinates=[ring(-179, 0, 179, 30)])
        self.assertEqual(
            wrapped_grid_bounds(geometry, 24, 12, 15),
            ((0, 24, 4, 6), ((0, 24),)),
        )

    def test_rejects_malformed_geometry_and_inconsistent_grid(self):
        polygon = dict(type="Polygon", coordinates=[ring(-30, -30, 30, 30)])
        with self.assertRaisesRegex(ValueError, "invalid grid"):
            wrapped_grid_bounds(polygon, 24, 12, 14)
        for geometry, message in (
            (dict(type="Point", coordinates=[0, 0]), "expected Polygon"),
            (dict(type="MultiPolygon", coordinates=[]), "empty geometry"),
            (dict(type="Polygon", coordinates=[]), "empty polygon"),
            (dict(type="Polygon", coordinates=[ring(-181, 0, 0, 30)]), "invalid coordinates"),
            (dict(type="Polygon", coordinates=["bad"]), "invalid coordinates"),
            (dict(type="Polygon", coordinates=[ring(0, 0, 0, 30)]), "invalid polygon grid bounds"),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                wrapped_grid_bounds(geometry, 24, 12, 15)


class PolygonCentreHits(unittest.TestCase):
    grid = Grid(24, 10, 15)

    def test_horizontal_edge_checks_only_centres_selected_by_caller(self):
        polygon = dict(type="Polygon", coordinates=[ring(0, 30, 30, 37.5)])
        with self.assertRaisesRegex(ValueError, "crosses grid cell center"):
            reject_boundary_centers(polygon, self.grid)
        reject_boundary_centers(polygon, self.grid, selected=lambda x, y: x < 12)
        with self.assertRaisesRegex(ValueError, "crosses grid cell center"):
            reject_boundary_centers(
                polygon, self.grid, selected=lambda x, y: (x, y) == (13, 3)
            )

    def test_sloping_edge_centres_follow_the_exact_line_in_either_direction(self):
        for ring, expected in (
            ([[0, 0], [45, 45], [45, 0], [0, 0]], {(12, 5), (13, 4), (14, 3)}),
            ([[0, 45], [45, 0], [0, 0], [0, 45]], {(12, 3), (13, 4), (14, 5)}),
        ):
            for points in (ring, ring[::-1]):
                with self.subTest(points=points):
                    geometry = dict(type="Polygon", coordinates=[points])
                    for selected in (None, lambda x, y: (x, y) == (13, 4)):
                        with self.assertRaisesRegex(ValueError, "crosses grid cell center"):
                            reject_boundary_centers(geometry, self.grid, selected=selected)
                    hits = set()

                    def record(x, y):
                        hits.add((x, y))
                        return False

                    reject_boundary_centers(geometry, self.grid, selected=record)
                    self.assertEqual(hits, expected)

    def test_row_limited_grid_ignores_edges_south_of_its_cells(self):
        geometry = dict(
            type="MultiPolygon",
            coordinates=[[ring(-30, -80, 30, -67.5)], [ring(-180, 20, -170, 30)]],
        )
        reject_boundary_centers(geometry, self.grid)

    def test_full_height_grid_works_when_the_stored_step_rounds_up(self):
        grid = Grid(14, 7, 360 / 14)
        geometry = dict(type="Polygon", coordinates=[ring(-30, -80, 30, -60)])
        reject_boundary_centers(geometry, grid)

    def test_slanted_edges_without_centres_do_not_trigger_the_boundary_check(self):
        for points in (
            [[-180, 45], [-177, 0], [-180, 0], [-180, 45]],
            [[-153.75, 90], [-146.25, 75], [-140, 90], [-153.75, 90]],
        ):
            with self.subTest(points=points):
                reject_boundary_centers(dict(type="Polygon", coordinates=[points]), self.grid)

    def test_empty_coordinate_ring_has_no_segments_to_check(self):
        self.assertEqual(
            reject_boundary_centers(dict(type="Polygon", coordinates=[[]]), self.grid), 0
        )
