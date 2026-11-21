"""Continuous line-face identity and missing-label behavior on a numerical grid."""

import math
from pathlib import Path
import tempfile
import unittest
import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.partition import geographic_cuts, divide_regions, rasterize_barriers


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
