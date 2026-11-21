"""Area operations preserve geometric context and label all eligible cells."""

from contextlib import ExitStack
from pathlib import Path
import tempfile
import unittest

import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.layers import patch_rows, write_layer
from worldatlas.map_build.core.rle import open_grid, row
from worldatlas.map_build.division.areas import divide_area
from worldatlas.map_build.division.scope import Scope
from worldatlas.map_build.land.components import ComponentGrid
from worldatlas.map_build.land.connected import build_components


class AreaOperations(unittest.TestCase):
    grid = Grid(24, 12, 15)

    def coordinate(self, x, y):
        return [
            self.grid.west + x * self.grid.step,
            self.grid.north - y * self.grid.step,
        ]

    def geometry(self, kind, positions):
        coordinates = [self.coordinate(x, y) for x, y in positions]
        return dict(
            type=kind, coordinates=[coordinates] if kind == "Polygon" else coordinates
        )

    def solve(self, root, labels, *, unit="cell", physical=None, cuts=None, scope_area=None):
        grid = self.grid
        if scope_area is None:
            scope_area = self.geometry(
                "Polygon", [(4, 2), (20, 2), (20, 10), (4, 10), (4, 2)]
            )
        rule = dict(
            id="four-faces",
            physical_class="land" if unit == "component" else "mixed",
            unit=unit,
            unassigned_only=False,
            features={"scope_area": [dict(geometry=scope_area)]},
        )
        if physical is None:
            physical = np.ones((12, 24), dtype=np.uint32)
            physical[3:5, 6:10] = 17
            physical[7:9, 15:18] = 17
        if cuts is None:
            cuts = ([(12, 2), (12, 10)], [(4, 6), (12, 6), (20, 6)])
        for name, data in [
            ("physical", physical),
            ("parent", np.ones_like(physical)),
            ("snapshot", np.zeros_like(physical)),
        ]:
            write_layer(root / name, grid, patch_rows(data, grid.bounds, grid))
        with ExitStack() as stack:
            components = None
            if unit == "component":
                build_components(grid, root / "physical", root / "components")
                components = stack.enter_context(
                    ComponentGrid(root / "physical", root / "components", grid)
                )

            def component_grid(kind):
                self.assertEqual(kind, "land")
                self.assertIsNotNone(components)
                return components

            data = [
                stack.enter_context(open_grid(root / name, grid))
                for name in ("physical", "parent", "snapshot")
            ]
            scope = Scope(
                rule,
                grid,
                *data,
                component_grid,
            )
            lines = [
                dict(geometry=self.geometry("LineString", positions))
                for positions in cuts
            ]
            targets = [
                dict(
                    entity_id=entity,
                    point=dict(
                        geometry=dict(
                            type="Point", coordinates=self.coordinate(x + 0.5, y + 0.5)
                        )
                    ),
                )
                for entity, x, y in labels
            ]
            return divide_area(scope, lines, targets, root / "division")

    def test_two_lines_label_four_faces_including_land_and_context_water(self):
        with tempfile.TemporaryDirectory() as temp:
            result = self.solve(
                Path(temp), [(101, 8, 4), (807, 16, 4), (503, 8, 8), (999, 16, 8)]
            )
            self.assertEqual(
                result["counts"], {str(code): 32 for code in (101, 807, 503, 999)}
            )
            with open_grid(result["directory"], self.grid) as data:
                ends, owners = row(data, 4, self.grid.width)
                self.assertEqual(
                    int(owners[np.searchsorted(ends, 8, side="right")]), 101
                )
                self.assertEqual(
                    int(owners[np.searchsorted(ends, 16, side="right")]), 807
                )

    def test_missing_fourth_label_rejects_eligible_unowned_cells(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "has no face label"):
                self.solve(Path(temp), [(101, 8, 4), (807, 16, 4), (503, 8, 8)])

    def test_label_outside_the_grid_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "label is outside the grid"):
                self.solve(Path(temp), [(101, -1, 4)])

    def test_boundary_segments_may_meet_inside_the_division_scope(self):
        with tempfile.TemporaryDirectory() as temp:
            result = self.solve(
                Path(temp), [(101, 8, 4), (807, 16, 4), (503, 8, 8), (999, 16, 8)],
                cuts=([(12, 2), (12, 10)], [(4, 6), (12, 6)], [(12, 6), (20, 6)]),
            )
        self.assertEqual(result["counts"], {str(code): 32 for code in (101, 807, 503, 999)})

    def test_disjoint_scope_keeps_empty_rows_between_faces(self):
        patches = [
            self.geometry("Polygon", [(4, y), (20, y), (20, y + 2), (4, y + 2), (4, y)])
            for y in (2, 8)
        ]
        scope = dict(type="MultiPolygon", coordinates=[p["coordinates"] for p in patches])
        physical = np.ones((12, 24), dtype=np.uint32)
        physical[3, 5:7] = physical[8, 15:18] = 17
        for unit, counts in (
            ("cell", {"101": 32, "202": 32}),
            ("component", {"101": 2, "202": 3}),
        ):
            with self.subTest(unit=unit), tempfile.TemporaryDirectory() as temp:
                result = self.solve(
                    Path(temp), [(101, 6, 3), (202, 16, 8)],
                    unit=unit, physical=physical, cuts=([(4, 6), (20, 6)],),
                    scope_area=scope,
                )
                self.assertEqual(result["counts"], counts)

    def test_component_majority_requires_a_single_face(self):
        physical = np.ones((12, 24), dtype=np.uint32)
        physical[4, 5:15] = 17
        labels = [(101, 6, 4), (202, 10, 4), (101, 14, 4)]

        def solve(root, second_cut):
            return self.solve(
                root,
                labels,
                unit="component",
                physical=physical,
                cuts=([(8, 2), (8, 10)], [(second_cut, 2), (second_cut, 10)]),
            )

        with tempfile.TemporaryDirectory() as temp:
            # The two 3-cell faces with the same owner cannot win together.
            with self.assertRaisesRegex(ValueError, "lacks one majority face"):
                solve(Path(temp), 12)
        with tempfile.TemporaryDirectory() as temp:
            # The middle face now contains 6 of the component's 10 cells.
            self.assertEqual(solve(Path(temp), 14)["counts"], {"202": 10})
