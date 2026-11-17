"""Scope bounds skip empty rows without clipping majority-selected components."""

from contextlib import ExitStack
from pathlib import Path
import tempfile
import unittest
import numpy as np
from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.layers import patch_rows, write_layer
from worldatlas.map_build.core.rle import open_grid, row
from worldatlas.map_build.division.areas import assign_area
from worldatlas.map_build.division.scope import Scope
from worldatlas.map_build.land.connected import build_components
from worldatlas.map_build.land.components import ComponentGrid


class ScopeRows(unittest.TestCase):
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
