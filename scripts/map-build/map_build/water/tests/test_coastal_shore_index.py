import unittest
import numpy as np
from map_build.water import shared_nearest as shore
from map_build.water.coastal_shore_index import CoastalShoreIndex
from map_build.water.tests.helpers import rle


class ShoreIndexTest(unittest.TestCase):
    def test_exact_crop_order_against_reference_for_random_global_grids(self):
        rng = np.random.default_rng(200411)
        for _ in range(50):
            width = int(rng.integers(8, 80))
            height = width // 2
            physical = np.where(rng.random((height, width)) < rng.uniform(.01, .99), 1, 17)
            land = np.where(physical == 17, rng.integers(17, 23, (height, width)), 0)
            p, l = rle(physical), rle(land)
            index = CoastalShoreIndex(p, l, width, height)
            for crop in range(8):
                x0 = int(rng.integers(-2 * width, 2 * width))
                x1 = x0 + (width if crop % 3 == 0 else int(rng.integers(1, width + 1)))
                y0 = int(rng.integers(height))
                y1 = int(rng.integers(y0 + 1, height + 1))
                codes = rng.choice(np.arange(17, 23), int(rng.integers(1, 7)), replace=False).tolist()
                bounds = (x0, x1, y0, y1)
                try:
                    expected = shore.centers_for_crop(p, l, bounds, width, height, 360 / width, codes)
                except ValueError as error:
                    if str(error) != 'no participant shorelines in crop':
                        raise
                    with self.assertRaisesRegex(ValueError, 'no participant shorelines'):
                        index.centers_for_crop(bounds, 360 / width, codes)
                else:
                    actual = index.centers_for_crop(bounds, 360 / width, codes)
                    for key in expected:
                        np.testing.assert_array_equal(actual[key], expected[key])

    def test_seam_poles_and_invalid_inputs(self):
        physical = np.ones((4, 8), dtype=np.uint32)
        physical[0, 0] = physical[3, 7] = 17
        land = np.where(physical == 17, 22, 0)
        index = CoastalShoreIndex(rle(physical), rle(land), 8, 4)
        for bounds in ((-1, 2, 0, 4), (7, 10, 0, 4), (0, 8, 0, 4)):
            expected = shore.centers_for_crop(rle(physical), rle(land), bounds, 8, 4, 45., [22])
            actual = index.centers_for_crop(bounds, 45., [22])
            for key in expected:
                np.testing.assert_array_equal(actual[key], expected[key])
        land[3, 7] = 0
        with self.assertRaisesRegex(ValueError, 'invalid physical or land'):
            CoastalShoreIndex(rle(physical), rle(land), 8, 4)


if __name__ == '__main__':
    unittest.main()
