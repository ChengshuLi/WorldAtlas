"""Ownership filtering and conflict checks over compact row intervals."""

import unittest
import numpy as np

from worldatlas.map_build.division.intervals import Eligibility, combine, prepare
from worldatlas.map_build.division.scope import complete_row


def rle(ends, values):
    return np.array(ends, dtype=np.uint32), np.array(values, dtype=np.uint32)


class ScopeAndClaims(unittest.TestCase):
    def test_sparse_arrays_preserve_gaps_and_merge_adjacent_equal_values(self):
        records = np.array([[1, 3, 807], [3, 5, 807], [6, 7, 101]], dtype=np.uint32)
        ends, values = complete_row(8, records)
        self.assertEqual(ends.tolist(), [1, 5, 6, 7, 8])
        self.assertEqual(values.tolist(), [0, 807, 0, 101, 0])
        dense = np.repeat(values, np.diff(np.r_[0, ends]))
        self.assertEqual(dense.tolist(), [0, 807, 807, 807, 807, 0, 101, 0])

    def test_sparse_arrays_reject_overlap_and_out_of_range_values(self):
        with self.assertRaises(ValueError):
            complete_row(8, [[0, 4, 1], [3, 5, 2]])
        with self.assertRaises(ValueError):
            complete_row(8, [[0, 1, 2**32]])
        ends, values = complete_row(8, [[0, 8, 2**32 - 1]])
        self.assertEqual(values.tolist(), [2**32 - 1])
        self.assertEqual(ends.tolist(), [8])

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
