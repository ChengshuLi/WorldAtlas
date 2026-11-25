"""Check that connected runs cover exactly the selected physical cells."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np
from shapely.geometry import box, shape

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.layers import patch_rows, write_layer
from worldatlas.map_build.land import connected
from worldatlas.map_build.land.components import ComponentGrid


class ComponentFiles(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def test_invalid_physical_runs_are_rejected_before_writing_results(self):
        source_rows = self.root / "input-rows"
        source_runs = self.root / "input-runs"
        output_rows = self.root / "rows"
        output_runs = self.root / "runs"
        for offsets, runs, message in (
            ([0, 2], [4, 17], "invalid stream lengths"),
            ([0, 2, 1], [4, 17], "nonmonotonic row offsets"),
            ([0, 1], [4, 99], "invalid or noncanonical physical run"),
            ([0, 2], [2, 1, 4, 1], "invalid or noncanonical physical run"),
            ([0, 1], [3, 17], "incomplete physical row"),
        ):
            with self.subTest(message=message):
                np.array(offsets, dtype="<u4").tofile(source_rows)
                np.array(runs, dtype="<u4").tofile(source_runs)
                with self.assertRaisesRegex(ValueError, message):
                    connected.build(
                        4, len(offsets) - 1, source_rows, source_runs, output_rows, output_runs
                    )
                self.assertFalse(output_rows.exists())
                self.assertFalse(output_runs.exists())
        source_rows.write_bytes(b"\0")
        with self.assertRaisesRegex(ValueError, "misaligned u32 stream"):
            connected.build(4, 1, source_rows, source_runs, output_rows, output_runs)
        with self.assertRaisesRegex(ValueError, "invalid dimensions"):
            connected.build(0, 1, source_rows, source_runs, output_rows, output_runs)
        with self.assertRaisesRegex(ValueError, "physical land or water class"):
            connected.build(
                4, 1, source_rows, source_runs, output_rows, output_runs, physical_code=42
            )

    def fixture(self):
        grid = Grid(24, 12, 15)
        physical = self.root / "physical"
        components = self.root / "components"
        codes = np.ones((grid.height, grid.width), dtype=np.uint32)
        codes[5, [0, 23]] = 17
        write_layer(physical, grid, patch_rows(codes, grid.bounds, grid))
        connected.build_components(grid, physical, components)
        return grid, physical, components

    def test_polygon_on_both_sides_of_date_line_counts_one_component(self):
        grid, physical, components = self.fixture()
        geometry = dict(type="MultiPolygon", coordinates=[
            [[[west, 0], [east, 0], [east, 15], [west, 15], [west, 0]]]
            for west, east in [(-180, -165), (165, 180)]
        ])
        with ComponentGrid(physical, components, grid) as opened:
            roots = opened.totals()
            self.assertEqual(list(roots.values()), [2])
            self.assertEqual(opened.profile(shape(geometry)), roots)
            partial = dict(type="Polygon", coordinates=[
                [[-180, 0], [-173, 0], [-173, 15], [-180, 15], [-180, 0]]
            ])
            self.assertEqual(opened.profile(shape(partial)), {})
            self.assertEqual(opened.row_bounds([]), (0, 0))
            with self.assertRaisesRegex(ValueError, "row batch must be positive"):
                opened.profile(shape(geometry), rows_per_batch=0)
            with self.assertRaisesRegex(ValueError, "component row outside grid"):
                opened.row(grid.height)

    def test_polygon_profile_follows_gdal_for_cell_centers_on_an_edge(self):
        grid = Grid(24, 12, 15)
        physical, components = self.root / "physical", self.root / "components"
        write_layer(physical, grid, [(5, [(0, 12, 1), (12, 13, 17), (13, 24, 1)])])
        connected.build_components(grid, physical, components)
        with ComponentGrid(physical, components, grid) as opened:
            (root,) = opened.totals()
            # The cell at 7.5°E is on the east edge of the first box and
            # the west edge of the second. GDAL counts it in the first box.
            self.assertEqual(opened.profile(box(-30, 0, 7.5, 15)), {root: 1})
            self.assertEqual(opened.profile(box(7.5, 0, 30, 15)), {})

    def test_component_files_must_match_the_physical_grid(self):
        grid, physical, components = self.fixture()
        runs = components / "runs.u32le"
        original = np.fromfile(runs, dtype="<u4").reshape(-1, 3)
        for end, message in (
            (25, "invalid component row"),
            (2, "component coverage differs"),
        ):
            with self.subTest(end=end):
                modified = original.copy()
                modified[0, 1] = end
                modified.tofile(runs)
                with ComponentGrid(physical, components, grid) as opened:
                    with self.assertRaisesRegex(ValueError, message):
                        opened.row(5)
        np.array([0], dtype="<u4").tofile(components / "rows.u32le")
        with self.assertRaisesRegex(ValueError, "invalid component stream offsets"):
            ComponentGrid(physical, components, grid)
        runs.write_bytes(b"\0")
        with self.assertRaisesRegex(ValueError, "incomplete integer stream"):
            ComponentGrid(physical, components, grid)

    def test_saved_physical_grid_cannot_contain_unrecognized_map_codes(self):
        grid, _, components = self.fixture()
        wrong_grid = self.root / "nonphysical"
        write_layer(wrong_grid, grid, [(0, [(0, grid.width, 42)])])
        with ComponentGrid(wrong_grid, components, grid) as opened:
            with self.assertRaisesRegex(ValueError, "invalid physical class"):
                opened.row(0)

    def test_two_separate_runs_join_through_a_contiguous_row(self):
        grid = Grid(8, 4, 45)
        physical = self.root / "joined"
        output = self.root / "components"
        classes = np.ones((grid.height, grid.width), dtype=np.uint32)
        classes[0, [2, 4]] = 17
        classes[1, 2:5] = 17
        write_layer(physical, grid, patch_rows(classes, grid.bounds, grid))
        connected.build_components(grid, physical, output)
        with ComponentGrid(physical, output, grid) as result:
            self.assertEqual(list(result.totals().values()), [5])
