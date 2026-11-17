from pathlib import Path
import tempfile
import unittest

import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.layers import merge_rows, patch_rows, write_layer
from worldatlas.map_build.core.rle import open_grid
from worldatlas.map_build.water.shared_nearest import crop


class LayersTests(unittest.TestCase):
    def test_wrapped_patch_roundtrip_preserves_unrelated_zero_cells(self):
        grid = Grid(36, 18, 10.0)
        values = np.array([[4321, 4321, 902], [0, 902, 902]], dtype="u4")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "layer"
            write_layer(path, grid, patch_rows(values, (35, 38, 8, 10), grid))
            with open_grid(path, grid) as data:
                self.assertTrue(np.array_equal(crop(*data, 8, 35, 38, 36), values[0]))
                self.assertTrue(np.array_equal(crop(*data, 9, 35, 38, 36), values[1]))
                self.assertFalse(crop(*data, 0, 0, 36, 36).any())

    def test_window_merge_rejects_overlaps(self):
        with self.assertRaisesRegex(ValueError, "overlap"):
            list(merge_rows([iter([(3, [(1, 4, 7)])]), iter([(3, [(3, 5, 8)])])]))

    def test_duplicate_output_rows_are_rejected(self):
        grid = Grid(36, 18, 10.0)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "ordered and unique"):
                write_layer(
                    Path(directory) / "layer",
                    grid,
                    [(3, [(1, 2, 700)]), (3, [(2, 3, 700)])],
                )
