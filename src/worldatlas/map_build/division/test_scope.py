"""Scope bounds skip empty rows without clipping majority-selected components."""

from contextlib import ExitStack
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import numpy as np
from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.layers import patch_rows, write_layer
from worldatlas.map_build.core.rle import open_grid, row
from worldatlas.map_build.division.areas import assign_area, divide_area
from worldatlas.map_build.division.policies import nearest_basin_water, nearest_land
from worldatlas.map_build.division.scope import Scope
from worldatlas.map_build.land.connected import build_components
from worldatlas.map_build.land.components import ComponentGrid
from worldatlas.map_build.division.nearest import nearest
from worldatlas.map_build.division.shores import ShoreGeometry
from worldatlas.map_build.water.shared_nearest import crop


class ScopeRows(unittest.TestCase):
    def test_polygon_rows_reuse_the_rasterizer_beyond_the_first_batch(self):
        grid = Grid(360, 180, 1)
        offsets = np.arange(grid.height + 1, dtype=np.uint32)
        water = offsets, np.tile(np.array([grid.width, 1], dtype=np.uint32), grid.height)
        blank = offsets, np.tile(np.array([grid.width, 0], dtype=np.uint32), grid.height)
        geometry = dict(type="Polygon", coordinates=[[
            [0, -30], [2, -30], [2, 90], [0, 90], [0, -30],
        ]])
        rule = dict(
            physical_class="water", unit="cell", unassigned_only=False,
            features={"scope_area": [{"geometry": geometry}]},
        )
        scope = Scope(rule, grid, water, water, blank, lambda kind: None)
        for y in (0, 100):
            with self.subTest(y=y):
                ends, on = scope.query_row(y)
                self.assertEqual((ends.tolist(), on.tolist()), ([180, 182, 360], [0, 1, 0]))
        self.assertEqual(scope.area_row(150)[1].tolist(), [0])

        rejected = dict(rule, features={"connected_to": [
            {"geometry": dict(type="Point", coordinates=[0, 0])}
        ]})
        scope = Scope(rejected, grid, water, water, blank, lambda kind: None)
        with self.assertRaisesRegex(ValueError, "requires eligible parent connectivity"):
            scope.query_row(0)

        no_land = dict(rule, features={}, physical_class="land")
        scope = Scope(no_land, grid, water, water, blank, lambda kind: None)
        self.assertEqual(list(scope.query_windows()), [])

    def test_points_are_checked_against_grid_physical_class_and_parent(self):
        grid = Grid(24, 6, 15)
        data = [
            (np.arange(grid.height + 1, dtype=np.uint32),
             np.tile(np.array([grid.width, code], dtype=np.uint32), grid.height))
            for code in (0, 1, 17)
        ]
        missing_component = SimpleNamespace(component_at=lambda lon, lat: None)
        for lat, physical, message in (
            (-60, data[2], "outside the grid"),
            (60, data[0], "outside the physical domain"),
            (60, data[1], "incompatible physical class"),
            (60, data[2], "outside the parent"),
        ):
            with self.subTest(message=message):
                rule = dict(
                    physical_class="land", unit="component", unassigned_only=False,
                    features={"scope_component": [{"geometry": dict(type="Point", coordinates=[0, lat])}]},
                )
                with self.assertRaisesRegex(ValueError, message):
                    Scope(rule, grid, physical, data[1], data[0], lambda kind: missing_component)

    def test_polygon_south_of_retained_grid_has_no_claims(self):
        grid = Grid(24, 6, 15)
        geometry = dict(
            type="Polygon",
            coordinates=[[[10, -30], [20, -30], [20, -10], [10, -10], [10, -30]]],
        )
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            root = Path(temp)
            for name, code in (("physical", 1), ("parent", 1), ("snapshot", 0)):
                rows = ((y, [(0, grid.width, code)]) for y in range(grid.height))
                write_layer(root / name, grid, rows if code else ())
            data = [
                stack.enter_context(open_grid(root / name, grid))
                for name in ("physical", "parent", "snapshot")
            ]
            rule = dict(
                id="south",
                physical_class="water",
                unit="cell",
                unassigned_only=False,
                features=dict(scope_area=[dict(geometry=geometry)]),
            )
            scope = Scope(
                rule, grid, *data, lambda kind: self.fail("no components needed")
            )
            self.assertEqual(assign_area(scope, 101, root / "area")["counts"], {})
            self.assertEqual(divide_area(scope, (), (), root / "divide")["counts"], {})
            context = SimpleNamespace(parent_physical=data[0])
            basin = nearest_basin_water(context, scope, root / "basin")
            self.assertEqual(basin["counts"], {})
            components = Scope(dict(rule, unit="component"), grid, *data, scope.components)
            self.assertEqual(assign_area(components, 101, root / "components")["counts"], {})

    def test_prepared_wrapped_queries_preserve_ownership_filters_and_context(self):
        grid = Grid(36, 18, 10)
        physical = np.ones((18, 36), dtype=np.uint32)
        ownership = np.zeros_like(physical)
        for y, x, owner in ((7, 35, 807), (9, 0, 101), (10, 0, 101)):
            physical[y, x] = 17
            ownership[y, x] = owner
        ownership[8, 35] = 807
        geometry = dict(
            type="MultiPolygon",
            coordinates=[
                [[[170, -10], [180, -10], [180, 10], [170, 10], [170, -10]]],
                [[[-180, -10], [-170, -10], [-170, 10], [-180, 10], [-180, -10]]],
            ],
        )
        rule = dict(
            id="wrapped",
            physical_class="water",
            unit="cell",
            unassigned_only=True,
            features=dict(scope_area=[dict(geometry=geometry)]),
        )
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            root = Path(temp)
            for name, values in (
                ("physical", physical),
                ("parent", np.ones_like(physical)),
                ("snapshot", ownership),
            ):
                write_layer(root / name, grid, patch_rows(values, grid.bounds, grid))
            data = [
                stack.enter_context(open_grid(root / name, grid))
                for name in ("physical", "parent", "snapshot")
            ]
            raw = Scope(rule, grid, *data, lambda kind: None)
            prepared = Scope(rule, grid, *data, lambda kind: None)
            x0, x1, y0, y1 = prepared.bounds
            mask = np.stack(
                [crop(*data[0], y, x0, x1, grid.width) == 1 for y in range(y0, y1)]
            )
            with self.assertRaisesRegex(ValueError, "prepared area does not represent"):
                prepared.set_eligible_area(mask[:, :-1], prepared.bounds)
            prepared.set_eligible_area(mask, prepared.bounds)
            windows = list(prepared.query_windows())
            self.assertEqual(len(windows[0][2]), 2)
            for y in prepared.query_rows():
                for a, b in zip(raw.query_row(y), prepared.query_row(y)):
                    np.testing.assert_array_equal(a, b)
                for a, b in zip(raw.context_row(y), prepared.context_row(y)):
                    np.testing.assert_array_equal(a, b)
            shores = ShoreGeometry(data[0], grid)
            with self.assertRaisesRegex(ValueError, "need physical components"):
                shores.attach(data[2], [101, 807], reference_components={0})
            with self.assertRaisesRegex(ValueError, "outside parent land components"):
                shores.attach(
                    data[2], [101, 807], reference_components={0},
                    components=SimpleNamespace(row=lambda _: np.empty((0, 3), dtype=np.uint32)),
                )
            references = shores.attach(data[2], [101, 807])
            first = nearest(raw, references, "cell", directory=root / "raw")
            second = nearest(prepared, references, "cell", directory=root / "prepared")
            self.assertEqual(sum(first["counts"].values()), 2)
            self.assertEqual(first["counts"], second["counts"])
            for name in ("rows.u32le", "runs.u32le"):
                self.assertEqual(
                    (root / "raw" / name).read_bytes(),
                    (root / "prepared" / name).read_bytes(),
                )
            no_gaps = Scope(dict(rule, unassigned_only=False), grid, *data, lambda kind: None)
            no_gaps.set_eligible_area(mask, prepared.bounds)
            self.assertEqual(sum(no_gaps.query_row(8)[1]), 2)
            no_gaps.set_eligible_area(np.zeros_like(mask), prepared.bounds)
            self.assertEqual(list(no_gaps.query_windows()), [])

    def test_component_selection_retains_rows_beyond_polygon_extent(self):
        grid = Grid(36, 18, 10)
        physical = np.ones((18, 36), dtype=np.uint32)
        physical[8:11, 18] = 17
        polygon = dict(
            type="Polygon",
            coordinates=[[[0, -10], [10, -10], [10, 10], [0, 10], [0, -10]]],
        )
        rule = dict(
            id="area",
            physical_class="land",
            unit="component",
            unassigned_only=False,
            features=dict(scope_area=[dict(geometry=polygon)]),
        )
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            root = Path(temp)
            for name, values in [
                ("physical", physical),
                ("parent", np.ones_like(physical)),
                ("snapshot", np.zeros_like(physical)),
            ]:
                write_layer(root / name, grid, patch_rows(values, grid.bounds, grid))
            build_components(grid, root / "physical", root / "components")
            components = stack.enter_context(
                ComponentGrid(root / "physical", root / "components", grid)
            )
            data = [
                stack.enter_context(open_grid(root / name, grid))
                for name in ("physical", "parent", "snapshot")
            ]
            scope = Scope(rule, grid, *data, lambda kind: components)
            self.assertEqual(list(scope.context_rows()), [8, 9])
            self.assertEqual(list(scope.query_rows()), [8, 9, 10])
            result = assign_area(scope, 807, root / "claims")
            self.assertEqual(result["counts"], {"807": 3})

            point = dict(type="Point", coordinates=[5, 5])
            by_point = dict(rule, unit="cell", features={"scope_component": [{"geometry": point}]})
            scope = Scope(by_point, grid, *data, lambda kind: components)
            self.assertEqual(scope.context_row(8)[1].tolist(), [0, 1, 0])
            self.assertEqual(scope.context_row(1)[1].tolist(), [0])
            unrestricted = Scope(dict(rule, features={}), grid, *data, lambda kind: components)
            self.assertEqual(
                unrestricted.eligible_components()["land"].tolist(),
                sorted(components.totals()),
            )
            offshore = dict(
                rule, features={"distance_reference": [
                    {"geometry": dict(type="Point", coordinates=[-45, 45])}
                ]}
            )
            scope = Scope(offshore, grid, *data, lambda kind: components)
            with self.assertRaisesRegex(ValueError, "distance reference does not identify parent land"):
                nearest_land(
                    SimpleNamespace(components=lambda kind: components),
                    scope, root / "offshore",
                )
            with open_grid(result["directory"], grid) as claims:
                ends, owners = row(claims, 10, grid.width)
                self.assertEqual(
                    int(owners[np.searchsorted(ends, 18, side="right")]), 807
                )
