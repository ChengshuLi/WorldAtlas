import unittest

from geodesic_fixture import fixture_boundary_filter


class Boundary:
    geom_type = 'LineString'
    coords = ((0.0, 0.0), (1.0, 0.0))


class Point:
    def __init__(self, x, y):
        self.x, self.y = x, y


class GeodesicFixtureTests(unittest.TestCase):
    def test_geodesic_clearance_selects_far_and_near_points(self):
        near_boundary = fixture_boundary_filter(Boundary())
        self.assertTrue(near_boundary(Point(0.5, 0.5)))
        self.assertFalse(near_boundary(Point(0.5, 2.0)))


if __name__ == '__main__':
    unittest.main()
