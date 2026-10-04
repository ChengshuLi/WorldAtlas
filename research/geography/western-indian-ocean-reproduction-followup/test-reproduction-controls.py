#!/usr/bin/env python3
"""Positive and fail-closed controls for the #662 reproduction path."""
import hashlib
import json
import sys
import unittest

from shapely.geometry import Polygon

import reproduction_common as common


class ReproductionControls(unittest.TestCase):
    def test_valid_geometry_is_preserved_without_repair(self):
        square = Polygon([(0, 0), (2, 0), (2, 2), (0, 2)])
        result = common.metric(square, square)
        self.assertTrue(result["source_valid_original"])
        self.assertFalse(result["source_repair_applied"])
        self.assertEqual(result["symmetric_difference_of_union_percent"], 0)

    def test_invalid_bowtie_repair_reports_raw_validity(self):
        bowtie = Polygon([(0, 0), (2, 2), (0, 2), (2, 0), (0, 0)])
        square = Polygon([(0, 0), (2, 0), (2, 2), (0, 2)])
        self.assertFalse(bowtie.is_valid)
        result = common.metric(bowtie, square)
        self.assertFalse(result["source_valid_original"])
        self.assertTrue(result["source_repair_applied"])
        self.assertTrue(common.repaired_areal(bowtie).is_valid)
        self.assertFalse(bowtie.is_valid, "comparison must not mutate retained geometry")

    def test_duplicate_subject_is_rejected(self):
        found = {}
        common.add_scoped_features(found, [{"id": "same"}], {"same"})
        with self.assertRaisesRegex(ValueError, "duplicate scoped subject across baseline parts"):
            common.add_scoped_features(found, [{"id": "same"}], {"same"})

    def test_changed_input_hash_is_rejected(self):
        path = "data/world-index.json"
        expected = common.INPUT_PINS["sha256"]["geography_baseline"][path]
        common.INPUT_PINS["sha256"]["geography_baseline"][path] = "0" * 64
        try:
            with self.assertRaisesRegex(ValueError, "changed baseline input"):
                common.pinned_bytes(path)
        finally:
            common.INPUT_PINS["sha256"]["geography_baseline"][path] = expected

    def test_existing_candidate_is_not_overwritten(self):
        target = common.HERE / "geometry-comparison.json"
        before = hashlib.sha256(target.read_bytes()).hexdigest()
        with self.assertRaises(FileExistsError):
            common.write_candidate(target.name, {"overwrite": True})
        self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), before)

    def test_check_only_performs_no_write(self):
        sys.argv.append("--check-only")
        try:
            common.write_candidate("check-only-control-output.json", {"checked": True})
        finally:
            sys.argv.pop()
        self.assertFalse((common.HERE / "check-only-control-output.json").exists())


if __name__ == "__main__":
    result = unittest.main(exit=False).result
    if not result.wasSuccessful():
        raise SystemExit(1)

    # The manifest binds these exact successful control receipts. Exclusive
    # writes prevent a later run from silently replacing the reviewed vintage.
    def record_control(name, receipt):
        target = common.HERE / name
        expected = json.dumps(receipt, ensure_ascii=False, indent=2) + "\n"
        if target.exists():
            if target.read_text(encoding="utf-8") != expected:
                raise RuntimeError(f"existing control receipt differs: {name}")
            print(f"verified existing candidate {name}; no output replaced")
            return
        common.write_candidate(name, receipt)

    record_control("validation/positive-control.json", {
        "method_id": "assigned_geometry_overlay",
        "kind": "positive-control",
        "outcome": "passed",
        "cases": ["valid-square-identical-overlay", "exact-zero-symmetric-difference"],
    })
    record_control("validation/negative-control.json", {
        "method_id": "assigned_geometry_overlay",
        "kind": "negative-control",
        "outcome": "passed",
        "cases": ["invalid-bowtie-preserves-raw-validity-and-source", "duplicate-subject",
                  "changed-input-hash", "exclusive-output-overwrite", "check-only-no-write"],
    })
