"""Small geographic fixtures exercise current-shore discovery and precedence."""

import unittest
from types import SimpleNamespace

import numpy as np

from map_build.core.grid import Grid
from map_build.water.tests.helpers import rle
from map_build.water.basins import Shorelines, assign, participants, rasterize
from map_build.water import shared_nearest as nearest


class BasinTests(unittest.TestCase):
    def setUp(self):
        self.grid = Grid(36, 18, 10.0)
        self.physical = np.ones((18, 36), dtype='u4')
        self.land = np.zeros((18, 36), dtype='u4')
        self.physical[7:11, 10] = 17
        self.physical[7:11, 16] = 17
        self.land[7:11, 10] = 301
        self.land[7:11, 16] = 999
        self.pairs = [(81, 301, 17), (42, 999, 4321)]
        self.p, self.l = rle(self.physical), rle(self.land)

    def shores(self):
        return Shorelines(self.p, self.l, self.grid, self.pairs)

    def test_participants_are_discovered_before_coastal_exclusion(self):
        bounds = (11, 16, 7, 11)
        water = np.ones((4, 5), dtype=bool)
        counts = participants(water, bounds, self.p, self.l, self.grid, self.pairs)
        self.assertEqual(counts, {81: 4, 42: 4})
        coast = np.zeros_like(self.physical)
        coast[7:11, 11] = 17
        coast[7:11, 15] = 4321
        result = assign(water, bounds, self.grid, self.shores(), counts, 1e-5, coastal=rle(coast))
        self.assertTrue(np.all(result[:, [0, -1]] == 0))
        self.assertTrue(np.all(result[:, 1] == 17))
        self.assertTrue(np.all(result[:, -2] == 4321))

    def test_land_edit_changes_participants(self):
        bounds = (11, 16, 7, 11)
        water = np.ones((4, 5), dtype=bool)
        self.land[7:11, 16] = 301
        counts = participants(water, bounds, self.p, rle(self.land), self.grid, self.pairs)
        self.assertEqual(counts, {81: 8})
        result = assign(water, bounds, self.grid, SimpleNamespace(pairs=self.pairs), counts, 1e-5)
        self.assertTrue(np.all(result == 17))

    def test_an_inland_entity_does_not_require_an_ocean_shore(self):
        self.physical[2:5, 2:5] = 17
        self.land[2:5, 2:5] = 301
        self.land[3, 3] = 70000
        pairs = [*self.pairs, (99, 70000, 90000)]
        shores = Shorelines(rle(self.physical), rle(self.land), self.grid, pairs)
        self.assertEqual(set(shores.indexes), {301, 999})

    def test_missing_participant_fails_only_if_water_remains(self):
        water = np.ones((4, 5), dtype=bool)
        with self.assertRaisesRegex(ValueError, 'no source-backed'):
            assign(water, (11, 16, 7, 11), self.grid, SimpleNamespace(pairs=self.pairs), {}, 1e-5)
        coast = np.full_like(self.physical, 17)
        result = assign(
            water,
            (11, 16, 7, 11),
            self.grid,
            SimpleNamespace(pairs=self.pairs),
            {},
            1e-5,
            coastal=rle(coast),
        )
        self.assertFalse(result.any())

    def test_complete_search_matches_independent_wgs84_distances(self):
        shores = self.shores()
        water = np.ones((4, 5), dtype=bool)
        result = assign(water, (11, 16, 7, 11), self.grid, shores, {81: 4, 42: 4}, 1e-5)
        for y in range(7, 11):
            for x in range(11, 16):
                minima = []
                for _, code, _ in self.pairs:
                    yy, xx = np.nonzero(self.land == code)
                    distances = nearest.GEOD.inv(
                        np.full(len(xx), float(self.grid.longitude(x))),
                        np.full(len(yy), float(self.grid.latitude(y))),
                        self.grid.longitude(xx),
                        self.grid.latitude(yy),
                    )[2]
                    minima.append(float(np.min(distances)))
                expected = self.pairs[
                    next(i for i, d in enumerate(minima) if d <= min(minima) + 1e-5)
                ][2]
                self.assertEqual(result[y - 7, x - 11], expected)

    def test_dateline_and_holes_are_rasterized_at_cell_centers(self):
        geometry = {
            'type': 'MultiPolygon',
            'coordinates': [
                [[[170, -10], [180, -10], [180, 10], [170, 10], [170, -10]]],
                [[[-180, -10], [-170, -10], [-170, 10], [-180, 10], [-180, -10]]],
            ],
        }
        bounds, mask = rasterize(geometry, self.grid)
        self.assertEqual(bounds, (35, 37, 8, 10))
        self.assertEqual(int(mask.sum()), 4)
        geometry = {
            'type': 'Polygon',
            'coordinates': [
                [[-20, -20], [20, -20], [20, 20], [-20, 20], [-20, -20]],
                [[-10, -10], [10, -10], [10, 10], [-10, 10], [-10, -10]],
            ],
        }
        _, mask = rasterize(geometry, self.grid)
        self.assertEqual(int(mask.sum()), 12)
