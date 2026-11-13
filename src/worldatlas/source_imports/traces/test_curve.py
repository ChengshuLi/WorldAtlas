import unittest

from worldatlas.source_imports.traces.curve import construct


class CurveTests(unittest.TestCase):
    def test_preserves_endpoints_and_north_to_south_order(self):
        points = [[10., 1.], [9., 0.], [8., -1.]]
        coordinates = construct(points, .001, .08)['coordinates']
        self.assertEqual(coordinates[0], points[0])
        self.assertEqual(coordinates[-1], points[-1])
        self.assertEqual(len(coordinates), 2001)
        self.assertTrue(all(a[1] > b[1] for a, b in zip(coordinates, coordinates[1:])))

    def test_smooths_a_corner(self):
        coordinates = construct([[0., 1.], [1., 0.], [0., -1.]], .001, .08)['coordinates']
        self.assertGreater(coordinates[1000][0], 0)
        self.assertLess(coordinates[1000][0], 1)

    def test_constant_longitude_stays_constant(self):
        result = construct([[125., 2.], [125., -2.]], .01, .08)
        self.assertTrue(all(abs(lon - 125) < 1e-12 for lon, lat in result['coordinates']))

    def test_rejects_invalid_points(self):
        for points in ([], [[0, 0]], [[0, 0], [1, 0]], [[0, 0], [1, 1]],
                       [[181, 1], [1, 0]], [[0, 91], [1, 0]],
                       [[0, 1], [float('nan'), 0]], [[0, 1], [True, 0]],
                       [[-179, 1], [179, 0]]):
            with self.subTest(points=points), self.assertRaises(ValueError):
                construct(points, .01, .08)

    def test_rejects_invalid_spacing_and_smoothing(self):
        for value in (0, -1, True, float('inf'), float('nan'), None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                construct([[0, 1], [1, 0]], value, .08)
            with self.subTest(value=value), self.assertRaises(ValueError):
                construct([[0, 1], [1, 0]], .01, value)

    def test_endpoint_correction_cannot_create_invalid_longitudes(self):
        with self.assertRaisesRegex(ValueError, 'smoothed trace'):
            construct([[180., 2.], [179., 1.], [180., 0.]], .01, 1.)

    def test_coarse_sampling_cannot_create_a_longitude_discontinuity(self):
        with self.assertRaisesRegex(ValueError, 'longitude discontinuity'):
            construct([[-170., 1.], [0., 0.], [170., -1.]], 3., .08)


if __name__ == '__main__':
    unittest.main()
