"""Rule filters may overlap physical classes without changing owner eligibility."""

import unittest

from worldatlas.map_build.division.contracts import compile_rules
from worldatlas.map_build.test_support import selection


class PhysicalEligibility(unittest.TestCase):
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
        self.assertEqual(compile_rules(geo, 0)[1][0]["targets"][0]["entity_id"], 807)
        geo["rules"][0]["physical_class"] = "land"
        with self.assertRaisesRegex(ValueError, "incompatible with its target"):
            compile_rules(geo, 0)
