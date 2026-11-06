import unittest

from geodesic_nearest import nearest_cell


class NearestCellTest(unittest.TestCase):
    def test_uses_ellipsoidal_distance_not_coordinate_degrees(self):
        # In degrees, the northern candidate is closer (.009 < .01). At 60N,
        # WGS84 ground distance makes the eastern candidate much closer.
        result = nearest_cell((0.0, 60.0), [
            ((0, 0), 0.01, 60.0),
            ((0, 1), 0.0, 60.009),
        ])
        self.assertEqual(result, (0, 0))

    def test_ties_use_cell_id_order(self):
        self.assertEqual(nearest_cell((0.0, 0.0), [
            ((0, 2), 1.0, 0.0), ((0, 1), -1.0, 0.0),
        ]), (0, 1))

    def test_rejects_invalid_coordinates_and_empty_candidates(self):
        with self.assertRaises(ValueError):
            nearest_cell((181.0, 0.0), [((0, 0), 0.0, 0.0)])
        with self.assertRaises(ValueError):
            nearest_cell((0.0, 0.0), [])


if __name__ == '__main__':
    unittest.main()
