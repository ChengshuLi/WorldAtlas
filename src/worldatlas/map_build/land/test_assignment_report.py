"""The source-area review uses production component-majority semantics."""

from pathlib import Path
import tempfile
import unittest

import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.layers import patch_rows, write_layer
from worldatlas.map_build.land.assignment_report import write_report
from worldatlas.map_build.land.components import ComponentGrid
from worldatlas.map_build.land.connected import build_components
from worldatlas.map_build.test_support import selection


class AssignmentReportTests(unittest.TestCase):
    def test_component_only_rules_are_skipped_and_area_majority_is_reported(self):
        data = selection()
        geo = data["geography"]
        geo["entities"].append(
            dict(
                id=81,
                name="Owner",
                parent_id=0,
                physical_class="land",
                color_rgb="#123456",
            )
        )
        geo["features"] = [
            dict(id="point", geometry=dict(type="Point", coordinates=[-75, 5])),
            dict(
                id="area",
                geometry=dict(
                    type="Polygon",
                    coordinates=[[[-80, 0], [-60, 0], [-60, 10], [-80, 10], [-80, 0]]],
                ),
            ),
        ]
        for ident, role, feature in [
            ("component", "scope_component", "point"),
            ("group", "scope_area", "area"),
        ]:
            geo["rules"].append(
                dict(
                    id=ident,
                    parent_id=0,
                    operation="assign_area",
                    physical_class="land",
                    unit="component",
                    unassigned_only=False,
                    rationale="Select this component.",
                )
            )
            geo["rule_features"].append(
                dict(rule_id=ident, role=role, feature_id=feature)
            )
            geo["rule_targets"].append(
                dict(rule_id=ident, entity_id=81, label_point_id=None)
            )
        grid = Grid(36, 18, 10.0)
        values = np.ones((18, 36), dtype=np.uint32)
        values[8, 10:13] = 17
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_layer(root / "physical", grid, patch_rows(values, grid.bounds, grid))
            build_components(grid, root / "physical", root / "components")
            with ComponentGrid(
                root / "physical", root / "components", grid
            ) as components:
                report = write_report(data, components, root / "report")
            self.assertEqual(len(report["rules"]), 1)
            self.assertEqual(report["rules"][0]["assignment_id"], "group")
            self.assertEqual(report["rules"][0]["cell_count"], 3)
            self.assertTrue((root / "report/index.html").is_file())
