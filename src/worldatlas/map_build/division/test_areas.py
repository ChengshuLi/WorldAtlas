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

    def solve(self, root, labels, *, unit="cell"):
        grid = self.grid
        scope_area = self.geometry(
            "Polygon", [(4, 2), (20, 2), (20, 10), (4, 10), (4, 2)]
        )
        rule = dict(
            id="four-faces",
            physical_class="mixed",
            unit=unit,
            unassigned_only=False,
            features={"scope_area": [dict(geometry=scope_area)]},
        )
        physical = np.ones((12, 24), dtype=np.uint32)
        physical[3:5, 6:10] = 17
        physical[7:9, 15:18] = 17
        for name, data in [
            ("physical", physical),
            ("parent", np.ones_like(physical)),
            ("snapshot", np.zeros_like(physical)),
        ]:
            write_layer(root / name, grid, patch_rows(data, grid.bounds, grid))
        with ExitStack() as stack:
            data = [
                stack.enter_context(open_grid(root / name, grid))
                for name in ("physical", "parent", "snapshot")
            ]
            scope = Scope(
                rule,
                grid,
                *data,
                lambda kind: self.fail("cell mode needs no components"),
            )
            lines = [
                dict(geometry=self.geometry("LineString", positions))
                for positions in ([(12, 2), (12, 10)], [(4, 6), (12, 6), (20, 6)])
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
