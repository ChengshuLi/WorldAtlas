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
from worldatlas.map_build.division.policies import nearest_basin_water
from worldatlas.map_build.division.scope import Scope
from worldatlas.map_build.land.connected import build_components
from worldatlas.map_build.land.components import ComponentGrid
from worldatlas.map_build.division.nearest import nearest
from worldatlas.map_build.division.shores import ShoreGeometry
from worldatlas.map_build.water.shared_nearest import crop


class ScopeRows(unittest.TestCase):
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
            prepared.set_eligible_area(mask, prepared.bounds)
            windows = list(prepared.query_windows())
            self.assertEqual(len(windows[0][2]), 2)
            for y in prepared.query_rows():
                for a, b in zip(raw.query_row(y), prepared.query_row(y)):
                    np.testing.assert_array_equal(a, b)
                for a, b in zip(raw.context_row(y), prepared.context_row(y)):
                    np.testing.assert_array_equal(a, b)
            references = ShoreGeometry(data[0], grid).attach(data[2], [101, 807])
            first = nearest(raw, references, "cell", directory=root / "raw")
            second = nearest(prepared, references, "cell", directory=root / "prepared")
            self.assertEqual(sum(first["counts"].values()), 2)
            self.assertEqual(first["counts"], second["counts"])
            for name in ("rows.u32le", "runs.u32le"):
                self.assertEqual(
                    (root / "raw" / name).read_bytes(),
                    (root / "prepared" / name).read_bytes(),
                )

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
            with open_grid(result["directory"], grid) as claims:
                ends, owners = row(claims, 10, grid.width)
                self.assertEqual(
                    int(owners[np.searchsorted(ends, 18, side="right")]), 807
                )
