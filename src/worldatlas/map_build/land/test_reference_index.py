"""Reference tiling preserves every supplied cell and never fills interval gaps."""

import tempfile
import unittest
from pathlib import Path

import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.land.reference_index import build_reference_index


class ReferenceIntervals(unittest.TestCase):
    def test_tile_splits_preserve_reference_cells_and_real_witnesses(self):
        grid = Grid(36, 18, 10)
        rows = [
            (0, np.array([[3, 19, 807]])),
            (7, np.array([[0, 36, 101]])),
            (8, np.array([[35, 36, 999]])),
        ]
        expected = {
            (y, x, owner)
            for y, parts in rows
            for a, b, owner in parts
            for x in range(a, b)
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "index"
            report = build_reference_index(grid, iter(rows), root, tile_cells=8)
            observed = set()
            for ty, tx, codes, n, checksum in report["tiles"]:
                parts = np.fromfile(
                    root / f"{ty:05d}-{tx:05d}.bin", dtype="<u4"
                ).reshape(-1, 4)
                for y, a, b, owner in parts:
                    self.assertEqual(int(y) // 8, ty)
                    self.assertEqual(int(a) // 8, tx)
                    self.assertEqual((int(b) - 1) // 8, tx)
                    observed.update(
                        (int(y), x, int(owner)) for x in range(int(a), int(b))
                    )
            self.assertEqual(observed, expected)
            for y, x, owner in np.fromfile(
                root / "representatives.u32le", dtype="<u4"
            ).reshape(-1, 3):
                self.assertIn((int(y), int(x), int(owner)), expected)

    def test_invalid_reference_rows_and_intervals_fail(self):
        for rows in (
            [(1, [[0, 2, 1]]), (0, [[0, 2, 1]])],
            [(0, [[0, 5, 1], [4, 8, 2]])],
            [(0, [[0, 1, 0]])],
        ):
            with self.subTest(rows=rows), tempfile.TemporaryDirectory() as temp:
                with self.assertRaises(ValueError):
                    build_reference_index(Grid(36, 18, 10), rows, Path(temp) / "index")
