"""Parent selection, operative reuse identity and exact descendant membership."""

import copy
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.layers import write_layer, patch_rows
from worldatlas.map_build.core.rle import open_grid, row
from worldatlas.map_build.division.hierarchy import (
    definition,
    selected_parents,
    substitute,
    HierarchyDivision,
)
from worldatlas.map_build.division.engine import ParentDivision
from worldatlas.map_build.execution.control import check_cancelled, stage
from worldatlas.map_build.execution.runtime import Checkpoints, Timing
from worldatlas.map_build.test_support import selection
from worldatlas.shared.files import sha256_file


class HierarchyTests(unittest.TestCase):
    def test_failed_rule_skips_queued_rules(self):
        calculate = Mock(side_effect=ValueError("invalid geography"))
        context = SimpleNamespace(
            input_pins=[],
            pins=lambda _: [],
            parent_directory=None,
            directory=Path("."),
            configuration={"division_workers": 1},
            task=calculate,
        )
        rules = [{"id": ident} for ident in ("first", "second", "third")]
        with self.assertRaisesRegex(ValueError, "invalid geography"):
            ParentDivision.calculate(context, rules, None)
        self.assertEqual(calculate.call_count, 1)
        context.configuration["division_workers"] = 0
        with self.assertRaisesRegex(ValueError, "division_workers must be positive"):
            ParentDivision.calculate(context, rules, None)
        self.assertEqual(calculate.call_count, 1)

    def test_failed_rule_preserves_cause_when_a_peer_stops(self):
        peer_started = threading.Event()
        cancelled = threading.Event()

        def calculate(_name, _function, args, _outputs, **kwargs):
            if args[1]["id"] == "first":
                peer_started.set()
                self.assertTrue(cancelled.wait(timeout=5))
                check_cancelled()
            self.assertTrue(peer_started.wait(timeout=5))
            raise ValueError("invalid geography")

        context = SimpleNamespace(
            input_pins=[],
            pins=lambda _: [],
            parent_directory=None,
            directory=Path("."),
            configuration={"division_workers": 2},
            task=calculate,
        )
        with stage(cancelled), self.assertRaisesRegex(ValueError, "invalid geography"):
            ParentDivision.calculate(context, [{"id": "first"}, {"id": "second"}], None)

    def test_coastal_rule_leaves_water_for_later_rules_when_no_shore_can_own_it(self):
        grid = Grid(24, 12, 15)
        geography = selection()["geography"]
        geography["entities"] += [
            dict(id=101, parent_id=0, physical_class="land"),
            dict(id=202, parent_id=0, physical_class="water"),
        ]
        geography["category_bindings"] = [
            dict(code=1, entity_id=101, physical_class="land"),
            dict(code=2, entity_id=202, physical_class="water"),
        ]
        geography["rules"] = [
            dict(
                id=ident, parent_id=0, operation=operation,
                physical_class=kind, unit="cell", unassigned_only=unassigned,
            )
            for ident, operation, kind, unassigned in (
                ("land", "assign_area", "land", False),
                ("coastal", "nearest_coastal_water", "water", False),
                ("water", "assign_area", "water", True),
            )
        ]
        geography["rule_targets"] = [
            dict(rule_id=ident, entity_id=owner, label_point_id=None)
            for ident, owner in (("land", 101), ("water", 202))
        ]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_layer(
                root / "physical", grid,
                ((y, [(0, 12, 17), (12, 24, 1)]) for y in range(grid.height)),
            )
            configuration = {"coastal_band_metres": 22224}
            built = HierarchyDivision(
                geography, grid, root / "physical", root / "division", configuration,
            ).run()
            with open_grid(built["directory"], grid) as owners:
                ends, ids = row(owners, 0, grid.width)
                self.assertEqual(ends.tolist(), [12, 24])
                self.assertEqual(ids.tolist(), [101, 202])

            write_layer(
                root / "all-land", grid,
                ((y, [(0, grid.width, 17)]) for y in range(grid.height)),
            )
            all_land = HierarchyDivision(
                geography, grid, root / "all-land", root / "all-land-division", configuration,
            ).run()
            with open_grid(all_land["directory"], grid) as owners:
                self.assertEqual(row(owners, 0, grid.width)[1].tolist(), [101])

            geography["rules"][1]["operation"] = "nearest_water"
            geography["rules"].pop()
            geography["rule_targets"].pop()
            with self.assertRaisesRegex(ValueError, "no eligible reference shores"):
                HierarchyDivision(
                    geography, grid, root / "physical", root / "unbounded", configuration,
                ).run()

    def test_finished_division_rejects_unassigned_parent_water(self):
        grid = Grid(24, 12, 15)
        geo = selection()["geography"]
        geo["entities"].append(dict(id=101, parent_id=0, physical_class="land"))
        geo["category_bindings"].append(
            dict(code=17, entity_id=101, physical_class="land")
        )
        geo["rules"].append(
            dict(
                id="land",
                parent_id=0,
                operation="assign_area",
                physical_class="land",
                unit="cell",
                unassigned_only=False,
            )
        )
        geo["rule_targets"].append(
            dict(rule_id="land", entity_id=101, label_point_id=None)
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            physical = np.ones((grid.height, grid.width), dtype=np.uint32)
            physical[0, 0] = 17
            write_layer(
                root / "physical", grid, patch_rows(physical, grid.bounds, grid)
            )
            with self.assertRaisesRegex(ValueError, "unassigned geographic cell 1,0"):
                HierarchyDivision(
                    geo, grid, root / "physical", root / "division", {}
                ).run()

    def test_water_edit_reuses_verified_land_and_a_land_edit_invalidates_it(self):
        grid = Grid(24, 12, 15)
        geo = selection()["geography"]
        geo["entities"] += [
            dict(id=101, parent_id=0, physical_class="land"),
            dict(id=807, parent_id=0, physical_class="water"),
        ]
        geo["features"] = [
            dict(id="reference", geometry=dict(type="Point", coordinates=[0, 0])),
        ]
        geo["category_bindings"] = [
            dict(code=17, entity_id=101, physical_class="land"),
            dict(code=1, entity_id=807, physical_class="water"),
        ]
        for ident, kind, remaining, entity in (
            ("land", "land", False, 101),
            ("water", "water", True, 807),
        ):
            geo["rules"].append(
                dict(
                    id=ident,
                    parent_id=0,
                    operation="assign_area",
                    physical_class=kind,
                    unit="cell",
                    unassigned_only=remaining,
                )
            )
            geo["rule_targets"].append(
                dict(rule_id=ident, entity_id=entity, label_point_id=None)
            )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            physical = np.ones((12, 24), dtype=np.uint32)
            physical[5, 3:5] = 17
            write_layer(
                root / "physical", grid, patch_rows(physical, grid.bounds, grid)
            )
            first = HierarchyDivision(
                geo, grid, root / "physical", root / "first", {}
            ).run()
            geo["rule_features"].append(
                dict(rule_id="water", feature_id="reference", role="connected_to")
            )
            with patch.object(
                ParentDivision,
                "land",
                side_effect=AssertionError("unchanged land was recomputed"),
            ):
                second = HierarchyDivision(
                    geo,
                    grid,
                    root / "physical",
                    root / "second",
                    {},
                    reuse=root / "first",
                ).run()
            self.assertFalse(second["parents"]["0"]["reused"])
            self.assertTrue(second["parents"]["0"]["land"]["reused"])
            for name in ("rows.u32le", "runs.u32le"):
                self.assertEqual(
                    sha256_file(Path(first["directory"]) / name),
                    sha256_file(Path(second["directory"]) / name),
                )
            geo["rules"][0]["unassigned_only"] = True
            third = HierarchyDivision(
                geo, grid, root / "physical", root / "third", {}, reuse=root / "second"
            ).run()
            self.assertFalse(third["parents"]["0"]["land"]["reused"])

    def test_requested_parent_includes_ancestors_without_sibling_divisions(self):
        geo = dict(
            entities=[
                dict(id=0, parent_id=None),
                dict(id=101, parent_id=0),
                dict(id=807, parent_id=0),
                dict(id=503, parent_id=101),
            ],
            rules=[dict(parent_id=p) for p in (0, 101, 807, 503)],
        )
        self.assertEqual(selected_parents(geo, [503, 101]), [0, 101, 503])
        with self.assertRaisesRegex(ValueError, "requested parent has no selected"):
            selected_parents(geo, [999])
        geo["rules"] = [r for r in geo["rules"] if r["parent_id"] != 101]
        with self.assertRaisesRegex(ValueError, "ancestor has no selected"):
            selected_parents(geo, [503])

    def test_invalid_ancestor_graph_cannot_be_divided(self):
        for parent, message in ((999, "missing ancestor"), (0, "contains a cycle")):
            with self.subTest(parent=parent):
                geography = dict(entities=[dict(id=0, parent_id=parent)], rules=[dict(parent_id=0)])
                with self.assertRaisesRegex(ValueError, message):
                    selected_parents(geography, [0])

    def test_child_division_changes_only_its_parent_cells_and_can_resume(self):
        grid = Grid(24, 12, 15)
        geography = selection()["geography"]
        geography["entities"] += [
            dict(id=101, parent_id=0, physical_class="land"),
            dict(id=202, parent_id=0, physical_class="water"),
            dict(id=303, parent_id=101, physical_class="land"),
            dict(id=404, parent_id=101, physical_class="land"),
        ]
        for ident, parent, kind, owner in (
            ("land", 0, "land", 101),
            ("water", 0, "water", 202),
        ):
            geography["rules"].append(
                dict(id=ident, parent_id=parent, operation="assign_area",
                     physical_class=kind, unit="cell", unassigned_only=False)
            )
            geography["rule_targets"].append(
                dict(rule_id=ident, entity_id=owner, label_point_id=None)
            )
            geography["category_bindings"].append(
                dict(code=owner, entity_id=owner, physical_class=kind)
            )
        geography["rules"].append(
            dict(id="split", parent_id=101, operation="divide_area",
                 physical_class="land", unit="cell", unassigned_only=False)
        )
        geography["features"].append(
            dict(id="boundary", geometry=dict(type="LineString", coordinates=[[0, 55], [0, 5]]))
        )
        geography["rule_features"].append(
            dict(rule_id="split", feature_id="boundary", role="boundary_line")
        )
        for name, longitude, owner in (("west", -15, 303), ("east", 15, 404)):
            geography["features"].append(
                dict(id=name, geometry=dict(type="Point", coordinates=[longitude, 30]))
            )
            geography["rule_targets"].append(
                dict(rule_id="split", entity_id=owner, label_point_id=name)
            )
            geography["category_bindings"].append(
                dict(code=owner, entity_id=owner, physical_class="land")
            )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            physical = np.ones((grid.height, grid.width), dtype=np.uint32)
            physical[3:5, 10:14] = 17
            write_layer(root / "physical", grid, patch_rows(physical, grid.bounds, grid))
            with self.assertRaisesRegex(ValueError, "requires inherited parent membership"):
                ParentDivision(
                    geography, 101, grid, root / "physical", root / "no-membership", {},
                )
            parent = ParentDivision(
                geography, 0, grid, root / "physical", root / "parent", {},
            )
            try:
                with self.assertRaisesRegex(ValueError, "land ownership must be complete"):
                    parent.water_shores()
                with self.assertRaisesRegex(ValueError, "prepare land ownership"):
                    parent.water()
                previous = parent.current
                parent.consolidate("empty-group", previous, [])
                self.assertEqual(parent.current, previous)
            finally:
                parent.close()
            direct = HierarchyDivision(
                geography, grid, root / "physical", root / "direct", {},
                requested=[101],
            )
            self.assertIs(direct.shores(), direct.shores())
            completed = direct.run()
            timing = Timing(root / "timing-events.jsonl")
            try:
                build = HierarchyDivision(
                    geography, grid, root / "physical", root / "division", {},
                    requested=[101], checkpoints=Checkpoints(root / "checkpoints", "attempt"),
                    timing=timing,
                )
                result = build.run()
                for name in ("rows.u32le", "runs.u32le"):
                    self.assertEqual(
                        sha256_file(Path(completed["directory"]) / name),
                        sha256_file(Path(result["directory"]) / name),
                    )
                with open_grid(result["directory"], grid) as owners:
                    ends, ids = row(owners, 3, grid.width)
                    self.assertEqual(ends.tolist(), [10, 12, 14, 24])
                    self.assertEqual(ids.tolist(), [202, 303, 404, 202])
                    self.assertEqual(row(owners, 0, grid.width)[1].tolist(), [202])
                resumed = build.run()
                self.assertEqual(resumed["directory"], result["directory"])
                self.assertTrue(all(p["reused"] for p in resumed["parents"].values()))
                geography["features"][0]["geometry"]["coordinates"] = [[1, 55], [1, 5]]
                with self.assertRaisesRegex(ValueError, "parent definition changed"):
                    build.run()
            finally:
                timing.close()

    def test_division_without_selected_rules_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(ValueError, "no geographic division selected"):
                HierarchyDivision(
                    selection()["geography"], Grid(24, 12, 15), root / "physical",
                    root / "division", {},
                ).run()

    def test_reuse_ignores_display_and_notes_but_tracks_operative_rules(self):
        geo = selection()["geography"]
        geo["entities"].append(
            dict(id=101, parent_id=0, physical_class="mixed", color_rgb="#112233")
        )
        geo["rules"].append(
            dict(
                id="area",
                parent_id=0,
                operation="assign_area",
                physical_class="mixed",
                unit="cell",
                unassigned_only=False,
                rationale="Explanation",
            )
        )
        geo["rule_targets"].append(
            dict(rule_id="area", entity_id=101, label_point_id=None)
        )
        grid = Grid(24, 12, 15)
        with tempfile.TemporaryDirectory() as temp:
            physical = Path(temp) / "physical"
            write_layer(physical, grid, [(0, [(0, 24, 17)])])
            original = definition(geo, 0, grid, physical, None, {})
            changed = copy.deepcopy(geo)
            changed["entities"][1]["color_rgb"] = "#998877"
            changed["rules"][0]["rationale"] = "Clearer explanation"
            self.assertEqual(definition(changed, 0, grid, physical, None, {}), original)
            changed["rules"][0]["unassigned_only"] = True
            self.assertNotEqual(
                definition(changed, 0, grid, physical, None, {}), original
            )

    def test_descendant_substitution_preserves_every_other_parent(self):
        grid = Grid(24, 12, 15)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_layer(root / "prior", grid, [(3, [(2, 5, 101), (5, 9, 807)])])
            write_layer(root / "membership", grid, [(3, [(2, 5, 1)])])
            write_layer(root / "children", grid, [(3, [(2, 3, 503), (3, 5, 999)])])
            result = substitute(
                grid,
                root / "prior",
                root / "membership",
                root / "children",
                root / "result",
            )
            with open_grid(result["directory"], grid) as data:
                ends, owners = row(data, 3, grid.width)
                self.assertEqual(
                    list(zip(map(int, ends), map(int, owners))),
                    [(2, 0), (3, 503), (5, 999), (9, 807), (24, 0)],
                )
            write_layer(root / "incomplete", grid, [(3, [(2, 3, 503)])])
            with self.assertRaisesRegex(ValueError, "exact parent membership"):
                substitute(
                    grid,
                    root / "prior",
                    root / "membership",
                    root / "incomplete",
                    root / "bad",
                )
