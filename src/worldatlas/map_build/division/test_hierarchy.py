"""Parent selection, operative reuse identity and exact descendant membership."""

import copy
from pathlib import Path
import tempfile
import unittest

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.layers import write_layer
from worldatlas.map_build.core.rle import open_grid, row
from worldatlas.map_build.division.hierarchy import (
    definition,
    selected_parents,
    substitute,
)
from worldatlas.map_build.test_support import selection


class HierarchyTests(unittest.TestCase):
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
        self.assertEqual(selected_parents(geo, [503]), [0, 101, 503])
        geo["rules"] = [r for r in geo["rules"] if r["parent_id"] != 101]
        with self.assertRaisesRegex(ValueError, "ancestor has no selected"):
            selected_parents(geo, [503])

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
