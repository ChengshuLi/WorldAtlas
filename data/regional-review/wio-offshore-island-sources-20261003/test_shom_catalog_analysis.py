#!/usr/bin/env python3
"""Adverse catalog membership controls for the retained Shom tile analysis."""
import copy
import json
import unittest
from pathlib import Path
import analyze_shom_tiles as analysis

class CaptureMembershipTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.capture=json.loads(analysis.CAPTURE.read_text())

    def test_full_captured_catalog_has_exact_product_membership(self):
        records,listings=analysis.validate_capture_membership(self.capture)
        self.assertEqual(len(records),406)
        self.assertEqual(len(listings),406)

    def test_missing_actual_package_metadata_is_rejected(self):
        mutated=copy.deepcopy(self.capture)
        target=next(i for i,row in enumerate(mutated["metadata_records"]) if row["area"]=="eparses")
        mutated["metadata_records"].pop(target)
        with self.assertRaisesRegex(ValueError,"package metadata membership mismatch"):
            analysis.validate_capture_membership(mutated)

    def test_duplicate_actual_package_metadata_is_rejected(self):
        mutated=copy.deepcopy(self.capture)
        mutated["metadata_records"].append(copy.deepcopy(mutated["metadata_records"][0]))
        with self.assertRaisesRegex(ValueError,"package metadata membership mismatch"):
            analysis.validate_capture_membership(mutated)

    def test_missing_actual_package_listing_is_rejected(self):
        mutated=copy.deepcopy(self.capture)
        target=next(i for i,row in enumerate(mutated["package_file_listings"]) if row["area"]=="mayotte")
        mutated["package_file_listings"].pop(target)
        with self.assertRaisesRegex(ValueError,"package file-list membership mismatch"):
            analysis.validate_capture_membership(mutated)

if __name__=="__main__":
    unittest.main()
