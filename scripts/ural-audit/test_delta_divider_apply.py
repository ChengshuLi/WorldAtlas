import unittest
import numpy as np
from delta_divider_apply import sides, update_row


CODEC = {'europe_code': 19, 'asia_code': 18, 'land_codes': [17, 18, 19, 20, 21, 22]}


class DividerApplyTest(unittest.TestCase):
    def test_sides_split_connected_land_and_preserve_water(self):
        bounds = (0, 0, 4, 2)
        europe, asia = sides([(2, -1), (2, 3)], bounds, (1, 1), (3, 1))
        old = np.array([18, 19, 19, 0], dtype=np.uint32)
        physical = np.array([17, 17, 17, 1], dtype=np.uint32)
        new, counts = update_row(old, physical, np.array([.5, 1.5, 2.5, 3.5]), 1, europe, asia, bounds, CODEC)
        self.assertEqual(new.tolist(), [19, 19, 18, 0])
        self.assertEqual((counts['asia_to_europe'], counts['europe_to_asia']), (1, 1))
        with self.assertRaisesRegex(ValueError, 'physical land masks differ'):
            update_row(old, np.array([1,17,17,1]), np.array([.5,1.5,2.5,3.5]), 1, europe, asia, bounds, CODEC)

    def test_tie_is_rejected(self):
        bounds = (0, 0, 4, 2)
        e, a = sides([(2, -1), (2, 3)], bounds, (1, 1), (3, 1))
        with self.assertRaisesRegex(ValueError, 'land center on divider'):
            update_row(np.array([19]), np.array([17]), np.array([2.]), 1, e, a, bounds, CODEC)

    def test_scope_boundary_land_is_rejected_and_water_is_preserved(self):
        bounds = (0, 0, 4, 2)
        europe, asia = sides([(2, -1), (2, 3)], bounds, (1, 1), (3, 1))
        for x, y in [(0, 1), (4, 1), (1, 0), (3, 2),
                     (0, 0), (4, 0), (0, 2), (4, 2), (1e-13, 1)]:
            with self.subTest(x=x, y=y), self.assertRaisesRegex(ValueError, 'scope boundary'):
                update_row(np.array([18]), np.array([17]), np.array([x]), y, europe, asia, bounds, CODEC)
        new, counts = update_row(np.array([0]), np.array([1]), np.array([0.]), 1,
                                 europe, asia, bounds, CODEC)
        self.assertEqual(new.tolist(), [0])
        self.assertEqual(counts['land_centers'], 0)


if __name__ == '__main__': unittest.main()

