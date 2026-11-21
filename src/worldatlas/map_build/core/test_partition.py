"""Continuous line-face identity and missing-label behavior on a numerical grid."""

import math
from pathlib import Path
import tempfile
import unittest
import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.partition import (
    divide_regions, geographic_cuts, rasterize_barriers,
)


class ExactCrossings(unittest.TestCase):
    grid = Grid(24, 12, 15)

    def test_one_float_step_to_each_side_of_a_cell_centre(self):
        for longitude, edge in (
            (math.nextafter(7.5, -math.inf), 11),
            (math.nextafter(7.5, math.inf), 12),
        ):
            with self.subTest(longitude=longitude):
                line = dict(type="LineString", coordinates=[[longitude, 45], [longitude, 0]])
                cuts = geographic_cuts([line], self.grid)
                self.assertEqual(cuts.horizontal[4], {edge})

    def test_exact_centre_hits_are_independent_of_line_direction(self):
        line = [(12.5, 2), (12.5, 10)]
        forward = rasterize_barriers([line], self.grid.width, self.grid.height)
        reverse = rasterize_barriers([line[::-1]], self.grid.width, self.grid.height)
        self.assertTrue(forward.horizontal)
        self.assertEqual(forward.horizontal, reverse.horizontal)
        self.assertEqual(forward.vertical, reverse.vertical)
        self.assertEqual(forward.wrap, reverse.wrap)

    def test_a_boundary_at_the_antimeridian_cuts_the_wrap_edges(self):
        line = dict(type="LineString", coordinates=[[-180, 45], [-180, 0]])
        cuts = geographic_cuts([line], self.grid)
        self.assertEqual(cuts.wrap, {3, 4, 5})

    def test_horizontal_centre_hits_are_independent_of_path_direction(self):
        line = [(2, 4.5), (5, 4.5), (5, 4.5), (8, 4.5)]
        forward = rasterize_barriers([line], self.grid.width, self.grid.height)
        reverse = rasterize_barriers([line[::-1]], self.grid.width, self.grid.height)
        self.assertEqual(dict(forward.vertical), {3: set(range(2, 8))})
        self.assertEqual(forward.vertical, reverse.vertical)
        self.assertEqual(forward.horizontal, reverse.horizontal)

    def test_antimeridian_crossings_do_not_cut_across_the_whole_map(self):
        line = [[-172.5, 45], [172.5, 30], [-172.5, 15]]
        forward = geographic_cuts([dict(type="LineString", coordinates=line)], self.grid)
        reverse = geographic_cuts([dict(type="LineString", coordinates=line[::-1])], self.grid)
        self.assertEqual(forward.wrap, reverse.wrap)
        self.assertEqual(forward.vertical, reverse.vertical)
        self.assertEqual(forward.horizontal, reverse.horizontal)
        self.assertTrue(forward.wrap)
        self.assertTrue(all(x in (0, 23) for xs in forward.vertical.values() for x in xs))

    def test_backtracking_segment_at_exact_centres_is_direction_independent(self):
        line = [(2, 8), (8, 8), (4, 4)]
        forward = rasterize_barriers([line], self.grid.width, self.grid.height)
        reverse = rasterize_barriers([line[::-1]], self.grid.width, self.grid.height)
        self.assertEqual(forward.horizontal, reverse.horizontal)
        self.assertEqual(forward.vertical, reverse.vertical)
        self.assertIn(4, forward.vertical[4])
        self.assertIn(3, forward.horizontal[4])

    def test_off_grid_line_copies_do_not_cut_visible_cells(self):
        outside = [
            [(-4, 2.5), (-2, 2.5)],
            [(-0.5, 1.5), (-0.5, 4.5)],
            [(3.5, 12), (7.5, 13)],
        ]
        cuts = rasterize_barriers(outside, self.grid.width, self.grid.height)
        self.assertFalse(cuts.horizontal)
        self.assertFalse(cuts.vertical)
        self.assertFalse(cuts.wrap)


class ContinuousFaces(unittest.TestCase):
    grid = Grid(24, 12, 15)

    @staticmethod
    def intervals(y):
        return [(0, 5), (15, 24)] if 6 <= y < 9 else [(0, 24)]

    def solve(self, labels, directory):
        # The bend leaves land-cell centres between the curve and an excluded
        # water interval. The geographic side is continuous despite the missing
        # four-neighbour centre path through those cells.
        path = [(-1, 6), (5, 6), (5, 4.8), (15, 4.8), (15, 6), (25, 6)]
        cuts = rasterize_barriers([path], self.grid.width, self.grid.height)
        owners = divide_regions(self.intervals, self.grid, cuts, labels, directory)
        offsets = np.fromfile(directory / "rows.u64le", dtype="<u8")
        nodes = np.fromfile(directory / "nodes.u32le", dtype="<u4").reshape(-1, 3)
        return owners, offsets, nodes

    def test_narrow_same_face_strip_needs_no_additional_geographic_label(self):
        with tempfile.TemporaryDirectory() as temp:
            owners, offsets, nodes = self.solve(
                [(101, 1, 2), (807, 1, 10)], Path(temp) / "faces"
            )
            self.assertTrue(set(map(int, nodes[:, 2])) <= owners.keys())
            row = nodes[int(offsets[5]) : int(offsets[6])]
            root = int(row[(row[:, 0] <= 10) & (row[:, 1] > 10)][0, 2])
            self.assertEqual(owners[root], 807)

    def test_a_missing_label_is_never_inferred_from_distance(self):
        with tempfile.TemporaryDirectory() as temp:
            owners, _, nodes = self.solve([(101, 1, 2)], Path(temp) / "faces")
            self.assertTrue(set(map(int, nodes[:, 2])) - owners.keys())

    def test_conflicting_face_labels_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "conflicting labels"):
                self.solve([(101, 1, 2), (807, 2, 2)], Path(temp) / "faces")

    def test_conflicting_labels_in_separate_fragments_of_the_same_face_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "conflicting labels"):
                self.solve(
                    [(101, 1, 2), (807, 1, 10), (999, 10, 5)],
                    Path(temp) / "faces",
                )

    def test_invalid_scope_intervals_fail_before_label_assignment(self):
        cuts = geographic_cuts([], self.grid)
        for intervals, message in (
            ([(3, 9), (8, 12)], "intervals overlap"),
            ([(8, 12), (3, 6)], "intervals overlap or are unordered"),
            ([(0, 25)], "invalid eligible interval"),
        ):
            with self.subTest(intervals=intervals), tempfile.TemporaryDirectory() as temp:
                with self.assertRaisesRegex(ValueError, message):
                    divide_regions(
                        lambda y: intervals, self.grid, cuts,
                        [(101, 1, 2)], Path(temp) / "faces",
                    )

    def test_label_must_identify_an_eligible_cell(self):
        cuts = geographic_cuts([], self.grid)
        for label, message in (
            ((0, 1, 1), "invalid divided-face label"),
            ((101, 10, 7), "outside the computational scope"),
        ):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temp:
                with self.assertRaisesRegex(ValueError, message):
                    divide_regions(
                        self.intervals, self.grid, cuts, [label], Path(temp) / "faces"
                    )

    def test_no_boundary_preserves_one_connected_face(self):
        with tempfile.TemporaryDirectory() as temp:
            roots = divide_regions(
                lambda y: [(0, 24)], self.grid, geographic_cuts([], self.grid),
                [(101, 1, 3)], Path(temp) / "faces",
            )
        self.assertEqual(list(roots.values()), [101])

    def test_disjoint_scope_areas_keep_their_own_labels_without_a_boundary(self):
        with tempfile.TemporaryDirectory() as temp:
            roots = divide_regions(
                lambda y: [(1, 3), (10, 13)], self.grid, geographic_cuts([], self.grid),
                [(101, 1, 3), (807, 11, 3)], Path(temp) / "faces",
            )
            self.assertEqual(sorted(roots.values()), [101, 807])

    def test_two_disjoint_runs_can_join_through_the_next_row(self):
        def intervals(y):
            return [(3, 4), (6, 7)] if y == 0 else [(3, 7)] if y == 1 else []

        with tempfile.TemporaryDirectory() as temp:
            roots = divide_regions(
                intervals, self.grid, geographic_cuts([], self.grid),
                [(101, 6, 0), (101, 4, 1)], Path(temp) / "faces",
            )
            self.assertEqual(list(roots.values()), [101])

    def test_repeated_boundary_endpoint_fails_before_face_assignment(self):
        with tempfile.TemporaryDirectory() as temp:
            cuts = rasterize_barriers(
                [[(0, 6), (0, 6), (24, 6)]], self.grid.width, self.grid.height
            )
            with self.assertRaisesRegex(ValueError, "endpoint has a repeated coordinate"):
                divide_regions(
                    self.intervals, self.grid, cuts,
                    [(101, 1, 2), (807, 1, 10)], Path(temp) / "faces",
                )
