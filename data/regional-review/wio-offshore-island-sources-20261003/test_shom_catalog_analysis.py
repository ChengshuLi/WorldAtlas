#!/usr/bin/env python3
"""Adverse catalog membership controls for the retained Shom tile analysis."""
import copy
import json
import unittest
from pathlib import Path
import analyze_shom_tiles as analysis
from shapely.geometry import shape

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

    def test_authenticated_package_listing_body_is_required(self):
        _, listings=analysis.validate_capture_membership(self.capture)
        target=next(iter(listings))
        mutated=copy.deepcopy(listings)
        mutated[target].pop("raw_member",None)
        with self.assertRaisesRegex(ValueError,"raw package-file listing member missing"):
            analysis.authenticate_listings(mutated)

    def test_actual_eparses_tile_bbox_intersects_juan_component(self):
        records,_=analysis.validate_capture_membership(self.capture)
        features,_=analysis.get_features()
        geometry=features["atlas:coverage:ATF-5919"]
        components=list(geometry.geoms) if geometry.geom_type=="MultiPolygon" else [geometry]
        row=analysis.parse_metadata(records[("eparses","0255_8115")])
        result=analysis.screen_component_bbox(components[0],row["bbox_wgs84"])
        self.assertEqual(result,{"direct_intersection":True,"within_buffer":True,"buffer_m":1000,"analysis_crs":"EPSG:6933"})

    def test_real_tromelin_tile_bbox_is_adverse_for_juan_component(self):
        records,_=analysis.validate_capture_membership(self.capture)
        features,_=analysis.get_features()
        geometry=features["atlas:coverage:ATF-5919"]
        components=list(geometry.geoms) if geometry.geom_type=="MultiPolygon" else [geometry]
        row=analysis.parse_metadata(records[("eparses","0230_8245")])
        result=analysis.screen_component_bbox(components[0],row["bbox_wgs84"])
        self.assertEqual(result,{"direct_intersection":False,"within_buffer":False,"buffer_m":1000,"analysis_crs":"EPSG:6933"})

if __name__=="__main__":
    unittest.main()
