"""Continuous line-face identity and missing-label behavior on a numerical grid."""

import math
from fractions import Fraction
from pathlib import Path
import tempfile
import unittest
import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.partition import (
    divide_regions,
    geographic_cuts,
    rasterize_barriers,
)


class ExactCrossings(unittest.TestCase):
    grid = Grid(24, 12, 15)

    def test_one_float_step_to_each_side_of_a_cell_centre(self):
        for longitude, edge in (
            (math.nextafter(7.5, -math.inf), 11),
            (math.nextafter(7.5, math.inf), 12),
        ):
            with self.subTest(longitude=longitude):
                line = dict(
                    type="LineString", coordinates=[[longitude, 45], [longitude, 0]]
                )
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

    def test_split_boundary_preserves_labels_when_the_join_hits_a_cell_centre(self):
        grid = Grid(8, 4, 45)
        line = [(-90, 90), (-157.5, 22.5), (-90, -90)]
        unchanged = dict(type="LineString", coordinates=[(0, 90), (0, -90)])
        representations = (
            dict(type="LineString", coordinates=line),
            dict(type="MultiLineString", coordinates=[line[2:0:-1], line[:2]]),
        )
        streams = []
        with tempfile.TemporaryDirectory() as temp:
            for index, boundary in enumerate(representations):
                output = Path(temp) / str(index)
                owners = divide_regions(
                    lambda _: [(0, 8)],
                    grid,
                    geographic_cuts([boundary, unchanged], grid),
                    [(11, 2, 1), (22, 6, 1)],
                    output,
                )
                self.assertEqual(sorted(owners.values()), [11, 22])
                records = np.fromfile(output / "nodes.u32le", dtype="<u4").reshape(
                    -1, 3
                )
                streams.append(
                    [(start, end, owners[node]) for start, end, node in records]
                )
        self.assertEqual(*streams)

    def test_horizontal_centre_hits_are_independent_of_path_direction(self):
        line = [(2, 4.5), (5, 4.5), (5, 4.5), (8, 4.5)]
        forward = rasterize_barriers([line], self.grid.width, self.grid.height)
        reverse = rasterize_barriers([line[::-1]], self.grid.width, self.grid.height)
        self.assertEqual(dict(forward.vertical), {3: set(range(2, 8))})
        self.assertEqual(forward.vertical, reverse.vertical)
        self.assertEqual(forward.horizontal, reverse.horizontal)

    def test_antimeridian_crossings_do_not_cut_across_the_whole_map(self):
        line = [[-172.5, 45], [172.5, 30], [-172.5, 15]]
        forward = geographic_cuts(
            [dict(type="LineString", coordinates=line)], self.grid
        )
        reverse = geographic_cuts(
            [dict(type="LineString", coordinates=line[::-1])], self.grid
        )
        self.assertEqual(forward.wrap, reverse.wrap)
        self.assertEqual(forward.vertical, reverse.vertical)
        self.assertEqual(forward.horizontal, reverse.horizontal)
        self.assertTrue(forward.wrap)
        self.assertTrue(
            all(x in (0, 23) for xs in forward.vertical.values() for x in xs)
        )

    def test_boundary_can_make_more_than_one_turn_around_the_globe(self):
        line = [
            (-170, 85),
            (-50, 79),
            (70, 73),
            (170, 67),
            (-170, 61),
            (-50, 55),
            (70, 49),
            (170, 43),
            (-170, 37),
            (-50, 31),
        ]
        tail = geographic_cuts(
            [dict(type="LineString", coordinates=line[-2:])], self.grid
        )
        self.assertEqual(tail.vertical[3], set(range(1, 9)))
        for coordinates in (line, line[::-1]):
            cuts = geographic_cuts(
                [dict(type="LineString", coordinates=coordinates)], self.grid
            )
            self.assertEqual(cuts.vertical[3], tail.vertical[3])

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
            with (
                self.subTest(intervals=intervals),
                tempfile.TemporaryDirectory() as temp,
            ):
                with self.assertRaisesRegex(ValueError, message):
                    divide_regions(
                        lambda y: intervals,
                        self.grid,
                        cuts,
                        [(101, 1, 2)],
                        Path(temp) / "faces",
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
                lambda y: [(0, 24)],
                self.grid,
                geographic_cuts([], self.grid),
                [(101, 1, 3)],
                Path(temp) / "faces",
            )
        self.assertEqual(list(roots.values()), [101])

    def test_disjoint_scope_areas_keep_their_own_labels_without_a_boundary(self):
        with tempfile.TemporaryDirectory() as temp:
            roots = divide_regions(
                lambda y: [(1, 3), (10, 13)],
                self.grid,
                geographic_cuts([], self.grid),
                [(101, 1, 3), (807, 11, 3)],
                Path(temp) / "faces",
            )
            self.assertEqual(sorted(roots.values()), [101, 807])

    def test_boundary_outside_the_scope_cannot_connect_disjoint_faces(self):
        grid = Grid(12, 6, 30)
        cuts = rasterize_barriers([[(3, 0), (3, 6)]], grid.width, grid.height)
        with tempfile.TemporaryDirectory() as temp:
            roots = divide_regions(
                lambda y: [(1, 2)] if y in (1, 3) else [],
                grid,
                cuts,
                [(11, 1, 1), (22, 1, 3)],
                Path(temp) / "faces",
            )
        self.assertEqual(sorted(roots.values()), [11, 22])

    def test_seam_boundary_keeps_opposite_faces_separate(self):
        grid = Grid(8, 4, 45)
        cuts = geographic_cuts(
            [
                {"type": "LineString", "coordinates": [(-180, 90), (-180, -90)]},
                {"type": "LineString", "coordinates": [(0, 90), (0, -90)]},
            ],
            grid,
        )
        with tempfile.TemporaryDirectory() as temp:
            owners = divide_regions(
                lambda _: [(0, 8)],
                grid,
                cuts,
                [(11, 0, 0), (22, 7, 0)],
                Path(temp) / "faces",
            )
        self.assertEqual(sorted(owners.values()), [11, 22])

    def test_nearby_branch_endpoint_does_not_join_either_side_of_main_boundary(self):
        grid = Grid(12, 6, 30)
        cuts = rasterize_barriers(
            [[(3, 0), (3, 6)], [(5, 3), (4, 3)]], grid.width, grid.height
        )
        with tempfile.TemporaryDirectory() as temp:
            owners = divide_regions(
                lambda _: [(0, 10)],
                grid,
                cuts,
                [(11, 1, 1), (22, 8, 1)],
                Path(temp) / "faces",
            )
        self.assertEqual(sorted(owners.values()), [11, 22])

    def test_two_disjoint_runs_can_join_through_the_next_row(self):
        def intervals(y):
            return [(3, 4), (6, 7)] if y == 0 else [(3, 7)] if y == 1 else []

        with tempfile.TemporaryDirectory() as temp:
            roots = divide_regions(
                intervals,
                self.grid,
                geographic_cuts([], self.grid),
                [(101, 6, 0), (101, 4, 1)],
                Path(temp) / "faces",
            )
            self.assertEqual(list(roots.values()), [101])

    def test_touching_input_spans_join_only_when_the_common_edge_is_open(self):
        grid = Grid(8, 4, 45)

        def intervals(y):
            return [(1, 3), (3, 5)] if y == 1 else []

        with tempfile.TemporaryDirectory() as temp:
            open_directory = Path(temp) / "open"
            owners = divide_regions(
                intervals,
                grid,
                geographic_cuts([], grid),
                [(11, 1, 1)],
                open_directory,
            )
            nodes = np.fromfile(open_directory / "nodes.u32le", dtype="<u4")
            self.assertEqual([owners[root] for root in nodes[2::3]], [11, 11])

            cuts = rasterize_barriers([[(3, 0), (3, 4)]], grid.width, grid.height)
            divided_directory = Path(temp) / "divided"
            owners = divide_regions(
                intervals, grid, cuts, [(11, 1, 1), (22, 3, 1)], divided_directory
            )
            nodes = np.fromfile(divided_directory / "nodes.u32le", dtype="<u4")
            self.assertEqual([owners[root] for root in nodes[2::3]], [11, 22])

    def test_repeated_boundary_vertices_do_not_change_face_assignment(self):
        clean = [(0, 6), (12, 6), (24, 6)]
        repeats = [(0, 6), (0, 6), (12, 6), (12, 6), (24, 6), (24, 6)]
        results = []
        with tempfile.TemporaryDirectory() as temp:
            for index, path in enumerate((clean, repeats, repeats[::-1])):
                cuts = rasterize_barriers(
                    [path, [(3, 6), (3, 6)]], self.grid.width, self.grid.height
                )
                directory = Path(temp) / str(index)
                owners = divide_regions(
                    lambda _: [(0, 24)],
                    self.grid,
                    cuts,
                    [(101, 1, 2), (807, 1, 10)],
                    directory,
                )
                self.assertEqual(sorted(owners.values()), [101, 807])
                results.append((owners, (directory / "nodes.u32le").read_bytes()))
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0], results[2])

    def test_a_cut_can_survive_even_if_its_endpoints_round_to_one_float(self):
        centre = Fraction(3, 2)
        delta = Fraction(1, 2**100)
        cuts = rasterize_barriers(
            [[(centre - delta, 1.5), (centre + delta, 1.5)]],
            self.grid.width,
            self.grid.height,
        )
        self.assertEqual(cuts.horizontal[1], {0, 1})
        with tempfile.TemporaryDirectory() as temp:
            owners = divide_regions(
                lambda y: [(0, 3)] if y == 1 else [],
                self.grid,
                cuts,
                [(11, 0, 1), (22, 1, 1), (33, 2, 1)],
                Path(temp) / "faces",
            )
        self.assertEqual(sorted(owners.values()), [11, 22, 33])
