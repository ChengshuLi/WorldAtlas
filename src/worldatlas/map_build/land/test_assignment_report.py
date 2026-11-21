"""The source-area review uses production component-majority semantics."""

from contextlib import ExitStack
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.layers import patch_rows, write_layer
from worldatlas.map_build.land.assignment_report import main
from worldatlas.map_build.division.engine import (
    ParentDivision,
    execute_rule,
    rule_directory,
)
from worldatlas.map_build.test_support import selection


class AssignmentReportTests(unittest.TestCase):
    def test_report_uses_saved_claims_after_connectivity_filtering(self):
        data = selection()
        geo = data["geography"]
        geo["entities"] += [
            dict(id=32, name="Parent", parent_id=0, physical_class="mixed"),
            dict(
                id=81,
                name="Owner",
                parent_id=32,
                physical_class="land",
                color_rgb="#123456",
            ),
        ]
        geo["features"] = [
            dict(id="point", geometry=dict(type="Point", coordinates=[-75, 5])),
            dict(
                id="area",
                geometry=dict(
                    type="Polygon",
                    coordinates=[[[-80, 0], [-20, 0], [-20, 10], [-80, 10], [-80, 0]]],
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
                    parent_id=32,
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
        geo["rule_features"].append(
            dict(rule_id="group", role="connected_to", feature_id="point")
        )
        grid = Grid(36, 18, 10.0)
        values = np.ones((18, 36), dtype=np.uint32)
        values[8, 10:13] = 17
        values[8, 14] = 17
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            root = Path(temp)
            write_layer(root / "physical", grid, patch_rows(values, grid.bounds, grid))
            membership = root / "membership"
            rows = ((y, [(0, grid.width, 1)]) for y in range(grid.height))
            write_layer(membership, grid, rows)
            calculation = root / "calculation"
            context = ParentDivision(
                geo, 32, grid, root / "physical", calculation, {},
                parent_directory=membership,
            )
            stack.callback(context.close)
            rule = next(rule for rule in context.rules if rule["id"] == "group")
            claims = execute_rule(
                context, rule, context.current, rule_directory(calculation, "group")
            )
            (root / "input-selection.json").write_text(json.dumps(data))
            (root / "division").mkdir()
            (root / "division/report.json").write_text(json.dumps({
                "grid": vars(grid),
                "parents": {"32": {"land": {"directory": str(calculation / "explicit")}}},
            }))
            command = [
                "assignment_report",
                "--run", str(root),
                "--parent", "32",
                "--output", str(root / "report"),
            ]
            with patch("sys.argv", command):
                main()
            report = json.loads((root / "report/summary.json").read_bytes())
            self.assertEqual(len(report["rules"]), 1)
            self.assertEqual(report["rules"][0]["assignment_id"], "group")
            self.assertEqual(claims["counts"], {"81": 3})
            self.assertEqual(report["rules"][0]["cell_count"], claims["counts"]["81"])
            self.assertEqual(report["rules"][0]["component_count"], 1)
            self.assertTrue((root / "report/index.html").is_file())
