"""Test shared WGS84 GeoJSON validation."""

import unittest

from worldatlas.geodesy.geojson import validate_geometry


class GeometryTests(unittest.TestCase):
    """Check coordinate structure, ranges, and geometric validity."""

    def test_invalid_point_shapes_and_coordinates(self):
        for geometry in (
            {"type": [], "coordinates": [1, 2]},
            {"type": "Point", "coordinates": []},
            {"type": "Point", "coordinates": {1, 2}},
            {"type": "Point", "coordinates": [1, 2], "extra": 3},
            {"type": "Point", "coordinates": [float("nan"), 1]},
            {"type": "Point", "coordinates": [1, 2, 3]},
            {"type": "Point", "coordinates": [True, 2]},
            {"type": "Point", "coordinates": ["1", 2]},
            {"type": "Point", "coordinates": [181, 2]},
            {"type": "Point", "coordinates": [1, -91]},
            {"type": "LineString", "coordinates": [[0, 0], 2]},
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
            with self.subTest(rings=rings), self.assertRaisesRegex(ValueError, "^expected valid geometry$"):
                validate_geometry({"type": "Polygon", "coordinates": rings})

    def test_line_simplicity_is_available_to_boundary_callers(self):
        geometry = validate_geometry({
            "type": "LineString",
            "coordinates": [(0, 0), (2, 2), (0, 2), (2, 0)],
        })
        self.assertTrue(geometry.is_valid)
        self.assertFalse(geometry.is_simple)

    def test_exterior_and_hole_must_close_in_both_polygon_types(self):
        outer = [(0, 0), (4, 0), (4, 4), (0, 4), (0, 0)]
        hole = [(1, 1), (2, 1), (2, 2), (1, 2), (1, 1)]
        for kind in ("Polygon", "MultiPolygon"):
            for rings in ([outer[:-1]], [outer, hole[:-1]]):
                with self.subTest(kind=kind, rings=rings):
                    with self.assertRaisesRegex(
                        ValueError, "polygon rings must be closed"
                    ):
                        validate_geometry(
                            {
                                "type": kind,
                                "coordinates": rings if kind == "Polygon" else [rings],
                            }
                        )
            rings = [outer, hole]
            result = validate_geometry(
                {
                    "type": kind,
                    "coordinates": rings if kind == "Polygon" else [rings],
                }
            )
            self.assertEqual(result.area, 15)
