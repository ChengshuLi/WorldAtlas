"""Compare the reusable distance engine with complete independent cell searches."""

from collections import defaultdict
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from pyproj import Geod
from scipy.spatial import cKDTree

from worldatlas.map_build.core.rle import open_grid, row
from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.layers import patch_rows, write_layer
from worldatlas.map_build.land.assignments import assign_components
from worldatlas.map_build.land.components import ComponentGrid
from worldatlas.map_build.land.connected import build_components
from worldatlas.geodesy.wgs84 import unit_sphere
from worldatlas.map_build.land import hints
from worldatlas.map_build.land.reference_index import build_reference_index
from worldatlas.map_build.land.search_engine import (
    blocks,
    certificate_pass,
    component_witnesses,
    exact_pass,
    expanded,
    finalize,
    first_points,
)
from worldatlas.shared.files import read_json, sha256_file


def reference_rows(path, grid):
    with open_grid(path, grid) as data:
        for y in range(grid.height):
            ends, owners = row(data, y, grid.width)
            starts = np.r_[0, ends[:-1]]
            active = owners != 0
            if active.any():
                yield y, np.column_stack((starts[active], ends[active], owners[active]))


class AssignmentTests(unittest.TestCase):
    def fixture(self, extra):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        grid = Grid(36, 18, 10.0)
        seed_cells = [(8, 2, 301, 81), (8, 17, 999, 42), (8, 32, 5555, 707)]
        physical = np.ones((18, 36), dtype=np.uint32)
        seeds = np.zeros_like(physical)
        for y, x, code, _ in seed_cells:
            physical[y, x], seeds[y, x] = 17, code
        for y, x in extra:
            physical[y, x] = 17
        for name, values in [("physical", physical), ("seeds", seeds)]:
            write_layer(root / name, grid, patch_rows(values, grid.bounds, grid))
        build_components(grid, root / "physical", root / "components")
        bindings = [
            dict(entity_id=entity, code=code, physical_class="land")
            for _, _, code, entity in seed_cells
        ]
        return root, grid, seed_cells, bindings

    def test_complete_component_distances_match_brute_force(self):
        root, grid, seed_cells, bindings = self.fixture(
            [(10, 1), (10, 2), (7, 16), (13, 29), (13, 30), (8, 35)]
        )
        build_reference_index(
            grid, reference_rows(root / "seeds", grid), root / "index", tile_cells=8
        )
        with ComponentGrid(root / "physical", root / "components", grid) as components:
            mainland = {
                components.component_at(
                    float(grid.longitude(x)), float(grid.latitude(y))
                )
                for y, x, _, _ in seed_cells
            }
            report = assign_components(
                components,
                root / "index",
                root / "assignments",
                roots=set(components.totals()) - mainland,
            )
            report, roots, owners = report
            observed = dict(zip(roots.tolist(), owners.tolist(), strict=True))
            for key, dtype, values in (("roots", "<u4", roots), ("entities", "<i8", owners)):
                path = Path(report[key])
                self.assertEqual(sha256_file(path), report["output_sha256"][path.name])
                np.testing.assert_array_equal(np.fromfile(path, dtype=dtype), values)
            cells = defaultdict(list)
            for y in range(grid.height):
                for a, b, ident in components.row(y):
                    cells[int(ident)] += [(y, x) for x in range(int(a), int(b))]
        geod = Geod(ellps="WGS84")
        expected = {}
        for ident, points in cells.items():
            if ident in mainland:
                continue
            distances = {
                code: min(
                    geod.inv(
                        float(grid.longitude(x)),
                        float(grid.latitude(y)),
                        float(grid.longitude(xx)),
                        float(grid.latitude(yy)),
                    )[2]
                    for y, x in points
                )
                for yy, xx, code, _ in seed_cells
            }
            winner = min(distances, key=lambda code: (distances[code], code))
            expected[ident] = winner
        self.assertEqual(observed, expected)

    def test_island_with_certified_owner_skips_exact_search(self):
        root, grid, seeds, _ = self.fixture([(10, 2)])
        reference_code = seeds[0][2]
        build_reference_index(
            grid, ((y, records[records[:, 2] == reference_code])
                   for y, records in reference_rows(root / "seeds", grid)
                   if reference_code in records[:, 2]),
            root / "index", tile_cells=8,
        )
        with ComponentGrid(root / "physical", root / "components", grid) as components:
            island = components.component_at(float(grid.longitude(2)), float(grid.latitude(10)))
            with patch('worldatlas.map_build.land.assignments.engine.exact_pass', side_effect=AssertionError('one owner is already certified')):
                _, roots, owners = assign_components(components, root / "index", root / "assignments", roots={island})
        self.assertEqual(roots.tolist(), [island])
        self.assertEqual(owners.tolist(), [seeds[0][2]])

    def test_all_land_already_seeded_needs_no_island_distance_search(self):
        root, grid, seed_cells, bindings = self.fixture([])
        build_reference_index(
            grid, reference_rows(root / "seeds", grid), root / "index", tile_cells=8
        )
        with ComponentGrid(root / "physical", root / "components", grid) as components:
            mainland = {
                components.component_at(
                    float(grid.longitude(x)), float(grid.latitude(y))
                )
                for y, x, _, _ in seed_cells
            }
            result, roots, owners = assign_components(
                components,
                root / "index",
                root / "assignments",
                roots=[],
            )
        self.assertEqual((roots.tolist(), owners.tolist()), ([], []))
        self.assertEqual(result["exact_queries"], 0)
        self.assertEqual(result["assigned_components"], 0)
        self.assertEqual(Path(result["roots"]).stat().st_size, 0)

    def test_component_search_checks_grid_samples_and_selected_roots(self):
        root, grid, _, bindings = self.fixture([(10, 1)])
        directory = root / "index"
        build_reference_index(grid, reference_rows(root / "seeds", grid), directory)
        with ComponentGrid(root / "physical", root / "components", grid) as components:
            config = directory / "report.json"
            data = read_json(config)
            original = config.read_bytes()
            data["grid"]["height"] -= 1
            config.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "seed index grid differs"):
                assign_components(
                    components, directory, root / "result", roots=[]
                )
            config.write_bytes(original)
            with self.assertRaisesRegex(
                ValueError, "roots must identify existing parent"
            ):
                assign_components(
                    components, directory, root / "result", roots=[999]
                )
            (directory / "representatives.u32le").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "representative seed cells differ"):
                assign_components(
                    components, directory, root / "result", roots=[]
                )

    def test_a_smaller_distance_wins_even_below_the_old_tie_threshold(self):
        values = finalize(
            [301, 301],
            [True, True],
            np.array([[10.0, 10.0 - 1e-6], [10.0, 10.0]]),
            [301, 999],
        )
        self.assertEqual(values.tolist(), [999, 301])

    def test_exact_ties_use_order_of_eligible_reference_owners(self):
        result = finalize(
            [301, 301],
            [True, False],
            np.array([[10.0, 10.0], [1.0, 2.0]]),
            [301, 999],
            priority_codes=[42, 999, 301],
        )
        self.assertEqual(result.tolist(), [999, 301])
        np.testing.assert_array_equal(
            finalize([301], [False], np.array([[10.0, 1.0]]), [301, 999]), [301]
        )
        with self.assertRaisesRegex(ValueError, "tie order must cover every reference"):
            finalize(
                [301],
                [True],
                np.array([[10.0, 10.0]]),
                [301, 999],
                priority_codes=[999, 999],
            )

    def test_invalid_final_state_and_unresolved_components_raise(self):
        for best, owners, message in (
            (np.array([[1.0, 2.0]]), [999, 301], "invalid final state"),
            (np.array([[1.0]]), [301, 999], "invalid final state"),
            (np.array([[np.inf, np.inf]]), [301, 999], "no WGS84 witness"),
        ):
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    finalize([301], [True], best, owners)


class ComponentRunTests(unittest.TestCase):
    def test_queries_preserve_columns_above_the_signed_limit(self):
        limit = 2**31
        width = 2**32 - 1
        runs = np.array(
            [[limit - 3, limit + 252, 0], [width - 2, width, 1]], dtype="<u4"
        )
        offsets = np.array([0, 2])
        roots = np.array([0, 1], dtype="<u4")
        batches = list(expanded(runs, 0, offsets, roots, 1, 128))
        self.assertEqual([len(batch[0]) for batch in batches], [128, 127, 2])
        _, starts, ends, _ = map(np.concatenate, zip(*batches))
        expected = [*range(limit - 3, limit + 252), width - 2, width - 1]
        self.assertEqual(starts.tolist(), expected)
        self.assertEqual(ends.tolist(), [column + 1 for column in expected])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "runs.u32le"
            runs.tofile(path)
            _, first_columns = first_points(path, offsets, roots, width)
        self.assertEqual(first_columns.tolist(), [limit - 3, width - 2])

    def test_large_component_is_split_without_gaps_and_unresolved_mask_is_optional(
        self,
    ):
        runs = np.array([[0, 260, 0], [262, 270, 1], [2, 6, 2]], dtype=np.uint32)
        roots = np.array([0, 1, 2], dtype=np.uint32)
        offsets = np.array([0, 2, 3])
        for ambiguity, expected in (
            (None, [130, 4, 2]),
            (np.array([True, False, True]), [130, 0, 2]),
        ):
            with self.subTest(expected=expected):
                batches = list(
                    expanded(runs, 0, offsets, roots, 2, 128, ambiguous=ambiguity)
                )
                self.assertTrue(all(0 < len(batch[0]) <= 128 for batch in batches))
                rows, starts, ends, positions = map(np.concatenate, zip(*batches))
                self.assertEqual(np.bincount(positions).tolist(), expected)
                for i, (lo, hi, _) in enumerate(runs):
                    if expected[i]:
                        match = positions == i
                        self.assertEqual(set(rows[match]), {int(i == 2)})
                        self.assertEqual(starts[match].tolist(), list(range(lo, hi, 2)))
                        self.assertEqual(
                            ends[match].tolist(), list(range(lo + 2, hi + 1, 2))
                        )

    def test_invalid_intervals_or_chunk_size_are_rejected(self):
        for run, chunk, message in (
            ([0, 1, 0], 0, "invalid query chunk"),
            ([1, 1, 0], 1, "bad component interval"),
        ):
            with self.subTest(run=run, chunk=chunk):
                with self.assertRaisesRegex(ValueError, message):
                    list(
                        expanded(
                            np.array([run]), 0, np.array([0, 1]), np.array([0]), chunk
                        )
                    )

    def test_first_points_require_complete_and_valid_component_stream(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "runs.u32le"
            offsets = np.array([0, 1])
            np.array([[0, 3, 0]], dtype="<u4").tofile(path)
            with self.assertRaisesRegex(ValueError, "invalid component run"):
                first_points(path, offsets, [0], 2)
            with self.assertRaisesRegex(ValueError, "incomplete component coverage"):
                first_points(path, offsets, [5], 3)
            rows, columns = first_points(path, offsets, [], 3)
            self.assertEqual((rows.tolist(), columns.tolist()), ([], []))
            with self.assertRaisesRegex(ValueError, "invalid component stream or block size"):
                list(blocks(path, block_records=0))
            path.write_bytes(b"truncated")
            with self.assertRaisesRegex(ValueError, "invalid component stream or block size"):
                list(blocks(path))

    def test_stream_detects_record_truncated_between_batches(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "runs.u32le"
            np.array([[0, 1, 0], [1, 2, 1]], dtype="<u4").tofile(path)

            def truncate_after_stat():
                path.write_bytes(path.read_bytes()[:13])

            records = blocks(path, block_records=1, guard=truncate_after_stat)
            offset, batch = next(records)
            self.assertEqual((offset, batch.tolist()), (0, [[0, 1, 0]]))
            with self.assertRaisesRegex(ValueError, "truncated component runs"):
                next(records)

    def test_distance_passes_do_not_accept_partial_data_or_unknown_hints(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "runs.u32le"
            np.array([[0, 1, 0]], dtype="<u4").tofile(path)
            offsets = np.array([0, 1])
            roots = np.array([0])
            hints_by_root = np.array([17])
            index = SimpleNamespace(
                codes=(17,),
                witnesses=lambda *_: (np.array([10.0]), None),
                certify_runs=lambda *_: np.array([True]),
                nearest_run=lambda *_: ({17: -1}, 1),
            )
            for runs, columns, hints_value, message in (
                (offsets, 1, [999], "invalid witness hints"),
                (offsets, 0, [17], "invalid component run"),
                (np.array([0]), 1, [17], "invalid witness row"),
                (np.array([0, 2]), 1, [17], "incomplete component witness coverage"),
            ):
                with self.subTest(message=message):
                    with self.assertRaisesRegex(ValueError, message):
                        component_witnesses(
                            path,
                            runs,
                            roots,
                            columns,
                            index,
                            np.array(hints_value),
                        )
            with patch.object(
                index, "witnesses", return_value=(np.array([np.nan]), None)
            ):
                with self.assertRaisesRegex(ValueError, "invalid WGS84 witness bound"):
                    component_witnesses(path, offsets, roots, 1, index, hints_by_root)

            ambiguous = np.array([True])
            with self.assertRaisesRegex(ValueError, "bad certificate state"):
                certificate_pass(
                    path, offsets, roots, index, [-1], hints_by_root, ambiguous
                )
            with self.assertRaisesRegex(ValueError, "incomplete certificate stream"):
                certificate_pass(
                    path, [0, 2], roots, index, [1], hints_by_root, ambiguous
                )
            for best, hints_value, message in (
                (np.array([1.0]), hints_by_root, "bad exact state"),
                (np.array([[1.0]]), [999], "missing real upper witness"),
                (np.array([[np.inf]]), hints_by_root, "missing real upper witness"),
                (np.array([[1.0]]), hints_by_root, "invalid exact distance"),
            ):
                with self.subTest(message=message):
                    with self.assertRaisesRegex(ValueError, message):
                        exact_pass(
                            path, offsets, roots, index, hints_value, ambiguous, best
                        )
            with self.assertRaisesRegex(ValueError, "incomplete exact stream"):
                exact_pass(
                    path,
                    [0, 2],
                    roots,
                    index,
                    hints_by_root,
                    np.array([False]),
                    np.array([[1.0]]),
                )


class ShoreHints(unittest.TestCase):
    def test_batched_candidate_search_matches_independent_geodesic_distances(self):
        latitudes = [0, 0, 0, 0, 89]
        longitudes = [-2, -1, 0, 2, 0]
        owners = [303, 101, 202, 404, 505]
        points = [(0, -0.5), (0, 0), (89.5, 0)]
        tree = cKDTree(unit_sphere(latitudes, longitudes))
        geod = Geod(ellps="WGS84")
        expected = [
            min(
                (
                    geod.inv(lon, lat, shore_lon, shore_lat)[2],
                    owner,
                )
                for shore_lat, shore_lon, owner in zip(latitudes, longitudes, owners)
            )[1]
            for lat, lon in points
        ]
        with patch.object(hints, "DISTANCE_BATCH", 1):
            result = hints.wgs84_nearest_categories(
                tree, latitudes, longitudes, owners, *zip(*points)
            )
        self.assertEqual(result.tolist(), expected)

    def test_empty_query_returns_no_codes_and_invalid_coordinates_raise(self):
        tree = cKDTree(unit_sphere([0], [0]))
        self.assertEqual(
            hints.wgs84_nearest_categories(tree, [0], [0], [17], [], []).tolist(), []
        )
        with self.assertRaisesRegex(ValueError, "invalid geodesic nearest inputs"):
            hints.wgs84_nearest_categories(tree, [0], [0], [17], [91], [0])

    def test_candidate_hint_keeps_the_nearest_cell_even_if_radius_scan_omits_it(self):
        tree = cKDTree(unit_sphere([0], [0]))
        search = SimpleNamespace(query=tree.query, query_ball_point=lambda *_, **__: [])
        self.assertEqual(
            hints.wgs84_nearest_categories(search, [0], [0], [17], [0], [0]).tolist(),
            [17],
        )

    def test_failed_geodesic_cannot_produce_a_hint(self):
        tree = cKDTree(unit_sphere([0], [0]))
        for measured, message in (
            ([np.array([np.nan])], "invalid WGS84 upper bound"),
            ([np.array([0.0]), np.array([np.nan])], "invalid WGS84 distance"),
        ):
            with self.subTest(message=message):
                with patch.object(hints, "geodesic_distances", side_effect=measured):
                    with self.assertRaisesRegex(ValueError, message):
                        hints.wgs84_nearest_categories(tree, [0], [0], [17], [0], [0])


if __name__ == "__main__":
    unittest.main()
