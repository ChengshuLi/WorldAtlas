from pathlib import Path
import tempfile
import unittest

import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.layers import merge_rows, patch_rows, write_layer
from worldatlas.map_build.core.rle import open_grid, row
from worldatlas.map_build.water.shared_nearest import crop


class LayersTests(unittest.TestCase):
    def test_sparse_rows_keep_gaps_and_merge_adjacent_equal_codes(self):
        grid = Grid(8, 4, 45)
        records = [(1, []), (2, [(2, 3, 7), (3, 5, 7)])]
        with tempfile.TemporaryDirectory() as directory:
            layer = Path(directory) / "layer"
            report = write_layer(layer, grid, merge_rows([iter(records)]))
            self.assertEqual(report["counts"], {"7": 3})
            self.assertEqual(report["assigned_bounds"], [2, 5, 2, 3])
            with open_grid(layer, grid) as streams:
                ends, codes = row(streams, 2, grid.width)
                self.assertEqual(ends.tolist(), [2, 5, 8])
                self.assertEqual(codes.tolist(), [0, 7, 0])

    def test_writer_rejects_invalid_spans_and_extra_rows(self):
        grid = Grid(4, 1, 90)
        cases = (
            ("invalid output span", [(0, [(1, 5, 7)])]),
            ("invalid output span", [(0, [(1, 2, 0)])]),
            ("assignment row outside", [(0, [(0, 4, 7)]), (1, [(0, 4, 7)])]),
        )
        with tempfile.TemporaryDirectory() as directory:
            for index, (error, records) in enumerate(cases):
                with self.subTest(records=records), self.assertRaisesRegex(ValueError, error):
                    write_layer(Path(directory) / str(index), grid, records)

    def test_patch_rejects_shape_mismatch_and_skips_empty_rows(self):
        grid = Grid(4, 2, 90)
        values = np.zeros((2, 4), dtype=np.uint32)
        self.assertEqual(list(patch_rows(values, grid.bounds, grid)), [])
        with self.assertRaisesRegex(ValueError, "dimensions"):
            list(patch_rows(values, (0, 3, 0, 2), grid))

    def test_malformed_rows_and_offset_streams_are_rejected(self):
        grid = Grid(4, 2, 90)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "layer"
            write_layer(path, grid, [(0, [(0, 2, 7), (2, 4, 8)])])
            np.array([2, 7, 2, 8, 4, 0], dtype="<u4").tofile(path / "runs.u32le")
            with open_grid(path, grid) as streams:
                with self.assertRaisesRegex(ValueError, "invalid row-run row"):
                    row(streams, 0, grid.width)
            np.array([0, 4, 3], dtype="<u4").tofile(path / "rows.u32le")
            with self.assertRaisesRegex(ValueError, "invalid row-run stream offsets"):
                with open_grid(path, grid):
                    self.fail("Unordered offsets were accepted")
            (path / "runs.u32le").write_bytes(b"short")
            with self.assertRaisesRegex(ValueError, "incomplete u32 stream"):
                with open_grid(path, grid):
                    self.fail("Incomplete run was accepted")

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
