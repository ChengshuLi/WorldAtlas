from pathlib import Path
import tempfile
import unittest

import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.layers import (
    merge_rows,
    patch_rows,
    write_layer,
    write_run_rows,
)
from worldatlas.map_build.core.rle import open_grid, open_mapped_array, row
from worldatlas.map_build.core.rle import crop


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
                with (
                    self.subTest(records=records),
                    self.assertRaisesRegex(ValueError, error),
                ):
                    write_layer(Path(directory) / str(index), grid, records)

    def test_complete_rows_match_sparse_output_with_uint32_codes_and_gaps(self):
        grid = Grid(12, 5, 30)
        high = 2**32 - 1
        with tempfile.TemporaryDirectory() as temp:
            sparse = Path(temp) / "sparse"
            arrays = Path(temp) / "arrays"
            expected = write_layer(
                sparse, grid, [(1, [(2, 4, high), (4, 6, high), (8, 12, 7)])]
            )
            result = write_run_rows(
                arrays,
                grid,
                [
                    (
                        1,
                        np.array([2, 4, 6, 8, 12], dtype="u4"),
                        np.array([0, high, high, 0, 7], dtype="u4"),
                    ),
                    (3, np.array([12], dtype="u4"), np.array([0], dtype="u4")),
                ],
            )
            self.assertEqual(result, dict(expected, directory=str(arrays.resolve())))
            self.assertEqual(result["counts"], {str(high): 4, "7": 4})
            self.assertEqual(result["assigned_bounds"], [2, 12, 1, 2])
            for name in ("rows.u32le", "runs.u32le"):
                self.assertEqual(
                    (sparse / name).read_bytes(), (arrays / name).read_bytes()
                )

    def test_complete_rows_reject_wrong_types_shapes_and_ends(self):
        grid = Grid(4, 1, 90)
        valid = np.array([2, 4], dtype="u4")
        cases = (
            (valid.reshape(1, 2), valid),
            (valid, valid[:1]),
            (valid.astype("i8"), valid),
            (valid, valid.astype("i8")),
            (valid[:0], valid[:0]),
            (np.array([0, 4], dtype="u4"), valid),
            (np.array([2, 3], dtype="u4"), valid),
            (np.array([4, 4], dtype="u4"), valid),
        )
        with tempfile.TemporaryDirectory() as directory:
            for index, (ends, codes) in enumerate(cases):
                with self.subTest(ends=ends, codes=codes):
                    with self.assertRaisesRegex(
                        ValueError, "invalid complete output row"
                    ):
                        write_run_rows(
                            Path(directory) / str(index), grid, [(0, ends, codes)]
                        )

    def test_patch_rejects_shape_mismatch_and_skips_empty_rows(self):
        grid = Grid(4, 2, 90)
        values = np.zeros((2, 4), dtype=np.uint32)
        self.assertEqual(list(patch_rows(values, grid.bounds, grid)), [])
        self.assertEqual(list(patch_rows(values[:, :0], (3, 3, 0, 2), grid)), [])
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
            with self.assertRaisesRegex(ValueError, "incomplete integer stream"):
                with open_grid(path, grid):
                    self.fail("Incomplete run was accepted")

    def test_mapped_arrays_close_and_persist_edits(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "values.u32le"
            path.write_bytes(b"\x01\x00\x00\x00")
            with open_mapped_array(path, "<u4", writable=True) as values:
                mapping = values.base
                values[0] = 513
            self.assertTrue(mapping.closed)
            self.assertEqual(path.read_bytes(), b"\x01\x02\x00\x00")

            with self.assertRaisesRegex(RuntimeError, "stop reading"):
                with open_mapped_array(path, "<u4") as values:
                    mapping = values.base
                    self.assertFalse(values.flags.writeable)
                    self.assertEqual(values[0], 513)
                    raise RuntimeError("stop reading")
            self.assertTrue(mapping.closed)

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

    def test_writer_rejects_overlaps_in_merged_windows(self):
        streams = [[(3, [(3, 5, 8)])], [(3, [(1, 4, 7)])]]
        self.assertEqual(list(merge_rows(streams)), [(3, [(1, 4, 7), (3, 5, 8)])])
        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaisesRegex(ValueError, "invalid output span"),
        ):
            write_layer(Path(directory) / "layer", Grid(8, 4, 45), merge_rows(streams))

    def test_duplicate_output_rows_are_rejected(self):
        grid = Grid(36, 18, 10.0)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "ordered and unique"):
                write_layer(
                    Path(directory) / "layer",
                    grid,
                    [(3, [(1, 2, 700)]), (3, [(2, 3, 700)])],
                )
