"""Check the two production shore steps against edge neighbors in a small grid."""

import unittest
from unittest.mock import patch

import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.division.shores import ShoreGeometry
from worldatlas.map_build.water.shore_index import ShoreIndex
from worldatlas.map_build.water.test_helpers import rle


def expected_shores(physical):
    water = physical == 1
    neighboring_water = np.roll(water, 1, axis=1) | np.roll(water, -1, axis=1)
    neighboring_water[1:] |= water[:-1]
    neighboring_water[:-1] |= water[1:]
    return (physical == 17) & neighboring_water


def expand_spans(index, values):
    expanded = np.zeros((index.height, index.width), dtype=np.uint32)
    for y in range(index.height):
        first, last = map(int, index.offsets[y : y + 2])
        for a, b, value in zip(
            index.starts[first:last], index.ends[first:last], values[first:last]
        ):
            expanded[y, a:b] = value
    return expanded


class BatchIndexTests(unittest.TestCase):
    def compare(self, physical, land, rows_per_batch):
        height, width = physical.shape
        grid = Grid(width, height, 360 / width)
        source = ShoreGeometry(rle(physical), grid, rows_per_batch=rows_per_batch)
        shores = expected_shores(physical)
        np.testing.assert_array_equal(
            expand_spans(source.spans, np.ones(len(source.spans.starts))), shores
        )
        owners = source.attach(rle(land), range(17, 23))
        np.testing.assert_array_equal(
            expand_spans(owners, owners.codes), np.where(shores, land, 0)
        )
        return owners

    def test_arbitrary_grids_categories_seams_poles_and_batch_boundaries(self):
        rng = np.random.default_rng(20261111)
        for trial in range(120):
            width = int(rng.integers(2, 80))
            height = int(rng.integers(1, width // 2 + 1))
            physical = np.where(
                rng.random((height, width)) < rng.uniform(0, 1), 1, 17
            ).astype(np.uint32)
            land = np.where(
                physical == 17, rng.integers(17, 23, (height, width)), 0
            ).astype(np.uint32)
            with self.subTest(trial=trial):
                self.compare(physical, land, int(rng.integers(1, height + 3)))

    def test_all_land_all_water_and_an_empty_band_between_shores(self):
        for height, width in ((1, 2), (1, 8), (3, 8)):
            for code in (1, 17):
                physical = np.full((height, width), code, dtype=np.uint32)
                self.compare(physical, np.where(physical == 17, 22, 0), 1)
        physical = np.ones((20, 40), dtype=np.uint32)
        physical[0, :] = physical[-1, :] = 17
        land = np.where(physical == 17, 22, 0)
        for batch in (1, 2, 4, 8, 20, 100):
            actual = self.compare(physical, land, batch)
            self.assertEqual(actual.offsets[1:-1].tolist(), [1] * 19)

    def test_run_batching_does_not_narrow_columns_or_expand_the_whole_grid(self):
        width = 2**32 - 1
        half = width // 2
        offsets = np.asarray([0, 2, 3, 5], dtype=np.uint32)
        physical = offsets, np.asarray(
            [half, 17, width, 1, width, 1, half, 1, width, 17], dtype=np.uint32
        )
        with patch.object(
            np, "searchsorted", side_effect=AssertionError("reuse common cut ranks")
        ):
            actual = ShoreIndex(physical, width, 3, rows_per_batch=2)
        self.assertEqual(actual.offsets.tolist(), [0, 1, 1, 2])
        self.assertEqual(actual.starts.tolist(), [0, half])
        self.assertEqual(actual.ends.tolist(), [half, width])
