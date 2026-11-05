import unittest
import numpy as np
from delta_divider_apply import sides, update_row


class DividerApplyTest(unittest.TestCase):
    def test_sides_split_connected_land_and_preserve_water(self):
        bounds = (0, 0, 4, 2)
        europe, asia = sides([(2, -1), (2, 3)], bounds, (1, 1), (3, 1))
        old = np.array([18, 19, 19, 0], dtype=np.uint32)
        physical = np.array([17, 17, 17, 1], dtype=np.uint32)
        new, counts = update_row(old, physical, np.array([.5, 1.5, 2.5, 3.5]), 1, europe, asia, bounds)
        self.assertEqual(new.tolist(), [19, 19, 18, 0])
        self.assertEqual((counts['asia_to_europe'], counts['europe_to_asia']), (1, 1))
        with self.assertRaisesRegex(ValueError, 'physical land masks differ'):
            update_row(old, np.array([1,17,17,1]), np.array([.5,1.5,2.5,3.5]), 1, europe, asia, bounds)

    def test_tie_is_rejected(self):
        bounds = (0, 0, 4, 2)
        e, a = sides([(2, -1), (2, 3)], bounds, (1, 1), (3, 1))
        with self.assertRaisesRegex(ValueError, 'land center on divider'):
            update_row(np.array([19]), np.array([17]), np.array([2.]), 1, e, a, bounds)


if __name__ == '__main__': unittest.main()
