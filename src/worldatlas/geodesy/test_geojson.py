"""Test shared WGS84 GeoJSON validation."""

import unittest

from worldatlas.geodesy.geojson import validate_geometry


class GeometryTests(unittest.TestCase):
    """Check coordinate structure, ranges, and geometric validity."""

    def test_invalid_point_shapes_and_coordinates(self):
        for geometry in (
            {"type": [], "coordinates": [1, 2]},
            {"type": "Point", "coordinates": []},
            {"type": "Point", "coordinates": [float("nan"), 1]},
            {"type": "Point", "coordinates": [1, 2, 3]},
            {"type": "Point", "coordinates": [True, 2]},
            {"type": "Point", "coordinates": ["1", 2]},
            {"type": "Point", "coordinates": [181, 2]},
            {"type": "Point", "coordinates": [1, -91]},
        ):
            with self.subTest(geometry=geometry), self.assertRaises(ValueError):
                validate_geometry(geometry)

    def test_rejects_crossing_polygon_and_hole_outside_outer_ring(self):
        for rings in (
            [[(0, 0), (2, 2), (0, 2), (2, 0), (0, 0)]],
            [
                [(0, 0), (2, 0), (2, 2), (0, 2), (0, 0)],
                [(3, 3), (4, 3), (4, 4), (3, 4), (3, 3)],
            ],
        ):
            with self.subTest(rings=rings), self.assertRaisesRegex(ValueError, "valid"):
                validate_geometry({"type": "Polygon", "coordinates": rings})

    def test_line_simplicity_is_available_to_boundary_callers(self):
        geometry = validate_geometry({
            "type": "LineString",
            "coordinates": [(0, 0), (2, 2), (0, 2), (2, 0)],
        })
        self.assertTrue(geometry.is_valid)
        self.assertFalse(geometry.is_simple)
