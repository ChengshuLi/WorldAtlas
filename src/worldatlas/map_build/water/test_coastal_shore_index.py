from worldatlas.map_build.water.test_shore_reference import (
    centers_for_crop as reference_centers,
)
import unittest
import numpy as np
from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.water.basins import participants
from worldatlas.map_build.water.shore_index import ShoreIndex
from worldatlas.map_build.water.shared_nearest import crop
from worldatlas.map_build.water.test_helpers import rle


class ShoreIndexTest(unittest.TestCase):
    def test_exact_crop_order_against_reference_for_random_global_grids(self):
        rng = np.random.default_rng(200411)
        for _ in range(50):
            width = int(rng.integers(8, 80))
            height = width // 2
            physical = np.where(
                rng.random((height, width)) < rng.uniform(0.01, 0.99), 1, 17
            )
            land = np.where(physical == 17, rng.integers(17, 23, (height, width)), 0)
            p, l = rle(physical), rle(land)
            index = ShoreIndex(p, l, width, height)
            for crop in range(8):
                x0 = int(rng.integers(-2 * width, 2 * width))
                x1 = x0 + (width if crop % 3 == 0 else int(rng.integers(1, width + 1)))
                y0 = int(rng.integers(height))
                y1 = int(rng.integers(y0 + 1, height + 1))
                codes = rng.choice(
                    np.arange(17, 23), int(rng.integers(1, 7)), replace=False
                ).tolist()
                bounds = (x0, x1, y0, y1)
                try:
                    expected = reference_centers(
                        p, l, bounds, width, height, 360 / width, codes
                    )
                except ValueError as error:
                    if str(error) != "no participant shorelines in crop":
                        raise
                    with self.assertRaisesRegex(
                        ValueError, "no participant shorelines"
                    ):
                        index.centers_for_crop(bounds, 360 / width, codes)
                else:
                    actual = index.centers_for_crop(bounds, 360 / width, codes)
                    for key in expected:
                        np.testing.assert_array_equal(actual[key], expected[key])

    def test_seam_poles_and_invalid_inputs(self):
        physical = np.ones((4, 8), dtype=np.uint32)
        physical[0, 0] = physical[3, 7] = 17
        land = np.where(physical == 17, 22, 0)
        index = ShoreIndex(rle(physical), rle(land), 8, 4)
        for bounds in ((-1, 2, 0, 4), (7, 10, 0, 4), (0, 8, 0, 4)):
            expected = reference_centers(
                rle(physical), rle(land), bounds, 8, 4, 45.0, [22]
            )
            actual = index.centers_for_crop(bounds, 45.0, [22])
            for key in expected:
                np.testing.assert_array_equal(actual[key], expected[key])
        land[3, 7] = 0
        with self.assertRaisesRegex(ValueError, "invalid physical or land"):
            ShoreIndex(rle(physical), rle(land), 8, 4)

    def test_invalid_streams_and_crops_never_produce_shore_coordinates(self):
        grid = rle(np.ones((4, 8), dtype=np.uint32))
        index = ShoreIndex(grid, grid, 8, 4)
        with self.assertRaisesRegex(ValueError, "invalid crop"):
            index.centers_for_crop((0, 8, 3, 5), 45, [17])
        with self.assertRaisesRegex(ValueError, "invalid crop"):
            crop(*grid, 4, 0, 8, 8)
        with self.assertRaisesRegex(ValueError, "invalid grid or row batch"):
            ShoreIndex(grid, grid, 8, 4, rows_per_batch=0)
        for broken in ((grid[0][:-1], grid[1]), (grid[0], grid[1] - 1)):
            with self.subTest(offsets=broken[0]):
                with self.assertRaisesRegex(ValueError, "invalid RLE row"):
                    ShoreIndex(broken, grid, 8, 4)

    def test_basin_shore_counts_cross_the_longitude_seam_and_stop_at_the_poles(self):
        grid = Grid(8, 4, 45)
        physical = np.ones((4, 8), dtype=np.uint32)
        physical[0, 7] = physical[1, 0] = 17
        physical[3, 0] = 17
        owners = np.zeros_like(physical)
        owners[0, 7], owners[1, 0], owners[3, 0] = 101, 202, 303
        mask = np.array([[True], [False]])
        bounds = (0, 1, 0, 2)
        pair = [(owner, owner, owner) for owner in (101, 202, 303)]
        self.assertEqual(
            participants(mask, bounds, rle(physical), rle(owners), grid, pair),
            {101: 1, 202: 1},
        )
        with self.assertRaisesRegex(ValueError, "unbound land code 202"):
            participants(mask, bounds, rle(physical), rle(owners), grid, pair[:1])


if __name__ == "__main__":
    unittest.main()
