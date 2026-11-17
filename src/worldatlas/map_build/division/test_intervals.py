"""Ownership filtering and conflict checks over compact row intervals."""

import unittest
import numpy as np

from worldatlas.map_build.division.intervals import Eligibility, combine, prepare


def rle(ends, values):
    return np.array(ends, dtype=np.uint32), np.array(values, dtype=np.uint32)


class ScopeAndClaims(unittest.TestCase):
    def setUp(self):
        self.physical = rle([3, 8], [17, 1])
        self.parent = rle([7, 8], [1, 0])
        self.selected = rle([8], [1])
        self.snapshot = rle([2, 8], [101, 0])
        self.allowed = Eligibility({101: "mixed", 807: "water"})

    def test_physical_and_parent_filter_preserves_existing_claims(self):
        self.assertEqual(
            prepare(
                self.physical,
                self.parent,
                self.selected,
                self.snapshot,
                physical_class="mixed",
                unassigned_only=False,
            ),
            [(0, 7, 1)],
        )
        self.assertEqual(
            prepare(
                self.physical,
                self.parent,
                self.selected,
                self.snapshot,
                physical_class="water",
                unassigned_only=False,
            ),
            [(3, 7, 1)],
        )

    def test_only_scope_preparation_filters_unassigned_cells(self):
        self.assertEqual(
            prepare(
                self.physical,
                self.parent,
                self.selected,
                self.snapshot,
                physical_class="mixed",
                unassigned_only=True,
            ),
            [(2, 7, 1)],
        )

    def test_agreement_can_overlap_and_conflicts_identify_both_claims(self):
        claim = rle([3, 7, 8], [101, 807, 0])
        result = combine(
            self.physical,
            self.parent,
            self.snapshot,
            [claim, claim],
            y=9,
            rules=["first", "second"],
            allowed=self.allowed,
            complete=True,
        )
        self.assertEqual(result, [(0, 3, 101), (3, 7, 807)])
        conflicting = rle([3, 7, 8], [101, 101, 0])
        with self.assertRaisesRegex(ValueError, r"first -> 807; second -> 101"):
            combine(
                self.physical,
                self.parent,
                self.snapshot,
                [claim, conflicting],
                y=9,
                rules=["first", "second"],
                allowed=self.allowed,
            )

    def test_water_child_cannot_claim_land(self):
        with self.assertRaisesRegex(ValueError, "ineligible"):
            combine(
                self.physical,
                self.parent,
                self.snapshot,
                [rle([8], [807])],
                y=0,
                rules=["water"],
                allowed=self.allowed,
            )

    def test_completion_rejects_an_unowned_parent_cell(self):
        with self.assertRaisesRegex(ValueError, "no child owner at 2,0"):
            combine(
                self.physical,
                self.parent,
                self.snapshot,
                [],
                y=0,
                rules=[],
                allowed=self.allowed,
                complete=True,
            )
