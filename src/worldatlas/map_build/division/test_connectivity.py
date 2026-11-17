"""Connectivity scopes exclude disconnected pockets without changing geometry."""

from contextlib import ExitStack
from pathlib import Path
import tempfile
import unittest

import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.layers import patch_rows, write_layer
from worldatlas.map_build.core.rle import open_grid, row
from worldatlas.map_build.division.connectivity import reference_points
from worldatlas.map_build.division.engine import ParentDivision, execute_rule
from worldatlas.map_build.test_support import selection


class ConnectedScopes(unittest.TestCase):
    grid = Grid(24, 12, 15)

    def point(self, x, y):
        return dict(type="Point", coordinates=[-180 + x * 15, 90 - y * 15])

    def setup_scope(self, root, stack, *, point=None, assigned=False, parent=None):
        grid = self.grid
        physical = np.ones((12, 24), dtype=np.uint32)
        snapshot = np.full_like(physical, 101) if assigned else np.zeros_like(physical)
        if not assigned:
            snapshot[5, [7, 9]] = 101
            snapshot[[4, 6], 8] = 101
        for name, data in (("physical", physical), ("snapshot", snapshot)):
            write_layer(root / name, grid, patch_rows(data, grid.bounds, grid))
        polygon = dict(
            type="Polygon",
            coordinates=[[[-90, -45], [60, -45], [60, 45], [-90, 45], [-90, -45]]],
        )
        geo = selection()["geography"]
        geo["entities"] += [
            dict(id=e, parent_id=0, physical_class="mixed") for e in (101, 807)
        ]
        geo["features"] = [dict(id="extent", geometry=polygon)]
        if point:
            geo["features"].append(dict(id="reference", geometry=point))
        for ident in ("first", "second"):
            geo["rules"].append(
                dict(
                    id=ident,
                    parent_id=0,
                    operation="assign_area",
                    physical_class="water",
                    unit="cell",
                    unassigned_only=True,
                )
            )
            geo["rule_targets"].append(
                dict(rule_id=ident, entity_id=807, label_point_id=None)
            )
            geo["rule_features"] += [
                dict(rule_id=ident, feature_id="extent", role="scope_area"),
                dict(
                    rule_id=ident,
                    feature_id="reference" if point else "extent",
                    role="connected_to",
                ),
            ]
        parent_directory = None
        if parent is not None:
            parent_directory = root / "parent"
            write_layer(parent_directory, grid, patch_rows(parent, grid.bounds, grid))
        context = ParentDivision(
            geo,
            0,
            grid,
            root / "physical",
            root / "calculation",
            {},
            parent_directory=parent_directory,
        )
        stack.callback(context.close)
        return context

    def values(self, directory, stack):
        data = stack.enter_context(open_grid(directory, self.grid))
        return lambda x, y: int(
            row(data, y, self.grid.width)[1][
                np.searchsorted(row(data, y, self.grid.width)[0], x, side="right")
            ]
        )

    def test_area_reference_excludes_pocket_and_shares_snapshot_components(self):
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            root = Path(temp)
            context = self.setup_scope(root, stack)
            results = [
                execute_rule(context, rule, root / "snapshot", root / rule["id"])
                for rule in context.rules
            ]
            self.assertEqual(len(context.scope_component_grids), 1)
            for result in results:
                value = self.values(result["directory"], stack)
                self.assertEqual(value(8, 5), 0)  # Unassigned, disconnected pocket.
                self.assertEqual(value(7, 5), 0)  # Already assigned ring.
                self.assertEqual(value(12, 5), 807)
                self.assertEqual(value(0, 0), 0)  # Outside source area.
                self.assertEqual(len(result["connectivity_references"]), 1)

    def test_explicit_point_can_select_the_other_component(self):
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            root = Path(temp)
            context = self.setup_scope(root, stack, point=self.point(8.5, 5.5))
            result = execute_rule(
                context, context.rules[0], root / "snapshot", root / "claims"
            )
            self.assertEqual(result["counts"], {"807": 1})

    def test_ineligible_reference_fails_but_an_empty_query_is_valid(self):
        for assigned in (False, True):
            with (
                self.subTest(assigned=assigned),
                tempfile.TemporaryDirectory() as temp,
                ExitStack() as stack,
            ):
                root = Path(temp)
                context = self.setup_scope(
                    root, stack, point=self.point(7.5, 5.5), assigned=assigned
                )
                if assigned:
                    result = execute_rule(
                        context, context.rules[0], root / "snapshot", root / "claims"
                    )
                    self.assertEqual(result["counts"], {})
                else:
                    with self.assertRaisesRegex(
                        ValueError, "not eligible parent territory"
                    ):
                        execute_rule(
                            context,
                            context.rules[0],
                            root / "snapshot",
                            root / "claims",
                        )

    def test_reference_connectivity_wraps_and_stays_inside_parent(self):
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            root = Path(temp)
            parent = np.zeros((12, 24), dtype=np.uint32)
            parent[3, [0, 23]] = 1
            context = self.setup_scope(
                root, stack, point=self.point(0.5, 3.5), parent=parent
            )
            # No area restriction: use the exact inherited parent membership.
            for rule in context.rules:
                rule["features"]["scope_area"] = []
            result = execute_rule(
                context, context.rules[0], root / "snapshot", root / "claims"
            )
            self.assertEqual(result["counts"], {"807": 2})

    def test_polygon_reference_point_is_inside_holed_combined_geometry(self):
        from shapely.geometry import Point, shape

        polygon = dict(
            type="Polygon",
            coordinates=[
                [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]],
                [[2, 2], [8, 2], [8, 8], [2, 8], [2, 2]],
            ],
        )
        points = reference_points([dict(geometry=polygon)])
        self.assertEqual(len(points), 1)
        self.assertTrue(shape(polygon).contains(Point(points[0])))
