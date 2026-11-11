import unittest

import numpy as np

from watersheds.drainage import compute_flow, destinations, neighbor_distances
from watersheds.terrain import Grid


class DrainageTests(unittest.TestCase):
    def grid(self, values, crs='EPSG:4326', transform=(44., .001, 0., 43., 0., -.001)):
        return Grid(np.array(values, dtype=float), transform, crs)

    def test_edge_can_flow_toward_a_lower_interior_cell(self):
        grid = self.grid([[4, 3, 4], [3, 2, 3], [2, 1, 2]])
        _, flow = compute_flow(grid)
        self.assertEqual(flow[0, 1], 4)

    def test_all_eight_downhill_directions(self):
        for neighbor in (0, 1, 2, 3, 5, 6, 7, 8):
            with self.subTest(neighbor=neighbor):
                heights = np.full((3, 3), 5.)
                heights[1, 1] = 4.
                heights.ravel()[neighbor] = 0.
                _, flow = compute_flow(self.grid(heights))
                self.assertEqual(flow[1, 1], neighbor)

    def test_fill_preserves_source_and_routes_flats_to_an_exit(self):
        raw = np.full((5, 5), 10.)
        raw[2, 2] = 0.
        grid = self.grid(raw)
        working, flow = compute_flow(grid)
        np.testing.assert_array_equal(grid.elevation, raw)
        self.assertEqual(working[2, 2], 10.)
        seen = set()
        index = 12
        while index >= 0:
            self.assertNotIn(index, seen)
            seen.add(index)
            other = int(flow.ravel()[index])
            if other >= 0:
                self.assertGreaterEqual(working.ravel()[index], working.ravel()[other])
            index = other
        self.assertGreater(len(seen), 1)

    def test_source_backed_closed_sink_is_not_filled(self):
        raw = np.full((5, 5), 10.)
        raw[2, 2] = 0.
        working, flow = compute_flow(self.grid(raw), closed_sinks=[(2, 2)])
        self.assertEqual(working[2, 2], 0.)
        self.assertEqual(flow[2, 2], -1)
        seeds = np.full(raw.shape, -1, dtype='int64')
        seeds[2, 2] = 17
        labels = destinations(flow, seeds)
        np.testing.assert_array_equal(labels[1:4, 1:4], np.full((3, 3), 17))
        # Flat cells at the crop edge can exit the domain; their destination is
        # not established merely by the presence of a known sink farther in.
        self.assertEqual(labels[0, 0], -1)

    def test_geographic_and_projected_neighbor_distances_are_supported(self):
        geographic = neighbor_distances(self.grid(np.zeros((3, 3))))
        projected = neighbor_distances(self.grid(np.zeros((3, 3)), 'EPSG:32640',
                                               (500000., 15., 0., 7000000., 0., -15.)))
        self.assertTrue(70 < geographic[0, 1, 1] < 100)
        self.assertTrue(14 < projected[0, 1, 1] < 16)
        self.assertGreater(projected[2, 1, 1], projected[0, 1, 1])

    def test_actual_group_ids_include_zero_three_and_large_numbers(self):
        flow = np.array([[1, 2, -1], [4, 5, -1], [7, 8, -1]])
        seeds = np.array([[-1, -1, 0], [-1, -1, 3], [-1, -1, 3120001840]])
        expected = np.array([[0, 0, 0], [3, 3, 3], [3120001840] * 3])
        np.testing.assert_array_equal(destinations(flow, seeds), expected)

    def test_unknown_exit_is_not_a_third_basin(self):
        flow = np.array([[1, -1], [3, -1]])
        seeds = np.full(flow.shape, -1, dtype='int64')
        terminals = seeds.copy()
        terminals[0, 1] = 3
        np.testing.assert_array_equal(destinations(flow, seeds, terminals), [[3, 3], [-1, -1]])

    def test_river_seed_precedes_the_later_terminal_destination(self):
        flow = np.array([[1, 2, -1]])
        seeds = np.array([[-1, 9, -1]])
        terminals = np.array([[-1, -1, 4]])
        np.testing.assert_array_equal(destinations(flow, seeds, terminals), [[9, 9, 4]])

    def test_cycle_remains_unknown(self):
        np.testing.assert_array_equal(destinations(np.array([[1, 0]]),
                                                  np.array([[-1, -1]])), [[-1, -1]])

    def test_missing_height_and_bad_links_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'complete finite'):
            compute_flow(self.grid([[1, np.nan]]))
        with self.assertRaisesRegex(ValueError, 'invalid flow'):
            destinations(np.array([[2]]), np.array([[-1]]))
        with self.assertRaisesRegex(ValueError, 'integers'):
            destinations(np.array([[-1]]), np.array([[1.5]]))

    def test_invalid_coordinate_is_rejected(self):
        with self.assertRaises((ValueError, RuntimeError)):
            neighbor_distances(self.grid([[0, 0]], transform=(44., .001, 0., 100., 0., -.001)))


if __name__ == '__main__':
    unittest.main()
