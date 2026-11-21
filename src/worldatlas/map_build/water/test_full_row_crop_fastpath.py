import unittest
import numpy as np
from worldatlas.map_build.water.shared_nearest import crop


class FullRowCropFastPath(unittest.TestCase):
    def test_full_row_matches_rle_values_and_dtype(self):
        rows = np.array([0, 3], dtype=np.uint32)
        runs = np.array([2, 1, 4, 17, 7, 1], dtype=np.uint32)
        actual = crop(rows, runs, 0, 0, 7, 7)
        np.testing.assert_array_equal(actual, np.array([1, 1, 17, 17, 1, 1, 1], dtype=np.uint32))
        self.assertEqual(actual.dtype, np.dtype(np.uint32))

    def test_random_full_rows_match_expanded_rle_reference(self):
        rng = np.random.default_rng(314159)
        for width in range(1, 129):
            ends = []
            vals = []
            pos = 0
            while pos < width:
                pos = min(width, pos + int(rng.integers(1, 10)))
                ends.append(pos)
                vals.append(int(rng.integers(0, 2**16)))
            rows = np.array([0, len(ends)], dtype=np.uint32)
            runs = np.asarray([item for pair in zip(ends, vals) for item in pair], dtype=np.uint32)
            expected = np.repeat(
                np.asarray(vals, dtype=np.uint32),
                np.diff(np.concatenate(([0], np.asarray(ends, dtype=np.uint32)))),
            )
            actual = crop(rows, runs, 0, 0, width, width)
            np.testing.assert_array_equal(actual, expected)
            self.assertEqual(actual.dtype, np.dtype(np.uint32))

    def test_partial_wrapped_crop_keeps_general_path_behavior(self):
        rows = np.array([0, 3], dtype=np.uint32)
        runs = np.array([2, 1, 4, 17, 7, 1], dtype=np.uint32)
        np.testing.assert_array_equal(
            crop(rows, runs, 0, -2, 3, 7), np.array([1, 1, 1, 1, 17], dtype=np.uint32)
        )

    def test_random_partial_and_wrapped_crops_match_dense_indexing(self):
        rng = np.random.default_rng(90072)
        for width in range(1, 129):
            values = rng.integers(0, 2**32, size=width, dtype=np.uint32)
            ends = np.r_[np.flatnonzero(values[1:] != values[:-1]) + 1, width]
            rows = np.array([0, len(ends)], dtype=np.uint32)
            runs = np.column_stack((ends, values[ends - 1])).astype(np.uint32).ravel()
            for _ in range(6):
                start = int(rng.integers(-3 * width, 3 * width))
                stop = start + int(rng.integers(1, width + 1))
                np.testing.assert_array_equal(
                    crop(rows, runs, 0, start, stop, width), values[np.arange(start, stop) % width]
                )

    def test_full_row_still_rejects_malformed_rle(self):
        rows = np.array([0, 2], dtype=np.uint32)
        runs = np.array([2, 1, 6, 17], dtype=np.uint32)
        with self.assertRaisesRegex(ValueError, 'invalid RLE row'):
            crop(rows, runs, 0, 0, 7, 7)


if __name__ == '__main__':
    unittest.main()
