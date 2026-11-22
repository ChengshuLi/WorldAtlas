"""Rule filters may overlap physical classes without changing owner eligibility."""

import unittest

from worldatlas.map_build.division.contracts import compile_rules
from worldatlas.map_build.test_support import selection


class PhysicalEligibility(unittest.TestCase):
    def setUp(self):
        self.rule = dict(
            id="area", parent_id=0, operation="assign_area", physical_class="land",
            unit="cell", unassigned_only=False,
        )
        self.target = dict(rule_id="area", entity_id=807, label_point_id=None)
        self.link = dict(rule_id="area", feature_id="inside", role="scope_component")
        self.geo = selection()["geography"]
        self.geo["entities"].append(dict(id=807, parent_id=0, physical_class="mixed"))
        self.geo["rules"].append(self.rule)
        self.geo["rule_targets"].append(self.target)
        self.geo["features"].append(dict(id="inside", geometry={"type": "Point"}))

    def test_missing_parent_and_parent_without_rules_fail(self):
        with self.assertRaisesRegex(ValueError, "missing geographic parent"):
            compile_rules(self.geo, 404)
        with self.assertRaisesRegex(ValueError, "needs child entities and rules"):
            compile_rules(self.geo, 807)

    def test_links_for_other_parents_are_outside_this_division(self):
        self.geo["rule_features"].extend([dict(self.link, rule_id="elsewhere"), self.link])
        self.geo["rule_targets"].append(dict(self.target, rule_id="elsewhere"))
        compiled = compile_rules(self.geo, 0)
        self.assertEqual(compiled.children_by_id[807], self.geo["entities"][-1])
        self.assertEqual(
            compiled.rules[0]["features"]["scope_component"], self.geo["features"]
        )

    def test_feature_roles_and_target_points_are_checked(self):
        for link, error in (
            (dict(self.link, role="typo"), "unresolved rule feature"),
            (dict(self.link, role="scope_area"), "invalid scope_area geometry"),
            (dict(self.link, role="distance_reference"), "invalid distance-reference"),
            (dict(self.link, feature_id="missing"), "unresolved rule feature"),
        ):
            self.geo["rule_features"][:] = [link]
            with self.subTest(link=link), self.assertRaisesRegex(ValueError, error):
                compile_rules(self.geo, 0)
        self.geo["rule_features"].clear()
        for overrides, error in (
            ({"entity_id": 0}, "not a direct child"),
            ({"label_point_id": "missing"}, "must reference a Point"),
            ({"label_point_id": "inside"}, "invalid target contract"),
        ):
            self.geo["rule_targets"][:] = [self.target | overrides]
            with self.subTest(overrides=overrides), self.assertRaisesRegex(ValueError, error):
                compile_rules(self.geo, 0)

    def test_operation_validates_required_roles_and_output_class(self):
        original = self.rule.copy()
        cases = (
            ({"unit": "row"}, [], "invalid operation settings"),
            ({"operation": "divide_area"}, [], "invalid boundary links"),
            ({"operation": "nearest_land"}, [], "invalid distance-reference"),
            ({"operation": "nearest_basin_water"}, [], "requires exactly one area"),
            ({"operation": "assign_area"}, [], "invalid target contract"),
            ({"operation": "nearest_water"}, [], "water distance rules require water cells"),
        )
        for overrides, links, error in cases:
            self.geo["rules"][:] = [original | overrides]
            self.geo["rule_features"][:] = links
            self.geo["rule_targets"].clear()
            with self.subTest(overrides=overrides), self.assertRaisesRegex(ValueError, error):
                compile_rules(self.geo, 0)
        self.geo["rules"][:] = [original | {"operation": "nearest_land"}]
        self.geo["rule_features"][:] = [self.link | {"role": "distance_reference"}]
        with self.assertRaisesRegex(ValueError, "nearest_land requires land components"):
            compile_rules(self.geo, 0)

    def test_rule_cannot_assign_incompatible_physical_class_within_parent(self):
        self.geo["entities"][0]["physical_class"] = "water"
        with self.assertRaisesRegex(ValueError, "incompatible with its parent"):
            compile_rules(self.geo, 0)

    def test_duplicate_rule_ids_are_rejected_in_saved_input(self):
        geo = selection()["geography"]
        geo["rules"] = [dict(id="shared", parent_id=parent) for parent in (0, 101)]
        with self.assertRaisesRegex(ValueError, "duplicate .* rule identity"):
            compile_rules(geo, 0)

    def test_mixed_filter_can_target_a_water_only_child(self):
        geo = selection()["geography"]
        geo["entities"].append(dict(id=807, parent_id=0, physical_class="water"))
        geo["rules"].append(
            dict(
                id="area",
                parent_id=0,
                operation="assign_area",
                physical_class="mixed",
                unit="cell",
                unassigned_only=False,
            )
        )
        geo["rule_targets"].append(
            dict(rule_id="area", entity_id=807, label_point_id=None)
        )
        self.assertEqual(compile_rules(geo, 0).rules[0]["targets"][0]["entity_id"], 807)
        geo["rules"][0]["physical_class"] = "land"
        with self.assertRaisesRegex(ValueError, "incompatible with its target"):
            compile_rules(geo, 0)
