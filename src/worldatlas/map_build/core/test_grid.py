"""Check the global grid origin, window bounds, and longitude seam."""

import math
import unittest

from worldatlas.map_build.core.grid import Grid


class GridTests(unittest.TestCase):
    def test_grid_rejects_bad_origins_steps_and_dimensions(self):
        for change in (
            {"west": 0}, {"north": 80}, {"width": 0}, {"height": 3},
            {"height": 0}, {"width": True}, {"height": 2.0},
            {"step": 0}, {"step": math.inf}, {"step": 91},
        ):
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "aligned"):
                Grid(**(dict(width=4, height=2, step=90) | change))

    def test_cell_lookup_and_extent_respect_retained_rows(self):
        grid = Grid(4, 1, 90)
        self.assertEqual(grid.cell_at(-180, 90), (0, 0))
        self.assertEqual(grid.cell_at(180, 90), (0, 0))
        self.assertEqual(grid.cell_at(math.nextafter(180, 0), 90), (3, 0))
        self.assertIsNone(grid.cell_at(181, 90))
        self.assertIsNone(grid.cell_at(0, 91))
        self.assertIsNone(grid.cell_at(0, -10))
        self.assertEqual(grid.extent((0, 2, 0, 1)), (-180, 0, 0, 90))
        with self.assertRaisesRegex(ValueError, "invalid grid window"):
            grid.extent((0, 2, 0, 2))

    def test_longitude_turn_covers_both_edges_for_nonbinary_steps(self):
        for width in (19, 39, 169):
            with self.subTest(width=width):
                grid = Grid(width, 1, 360 / width)
                self.assertEqual(grid.cell_at(180, 90), (0, 0))
                self.assertEqual(
                    grid.cell_at(math.nextafter(180, 0), 90), (width - 1, 0)
                )
                self.assertEqual(grid.cell_at(math.nextafter(-180, 0), 90), (0, 0))
                self.assertIsNone(grid.cell_at(math.nextafter(180, math.inf), 90))
                self.assertEqual(grid.extent(grid.bounds)[2], 180)
