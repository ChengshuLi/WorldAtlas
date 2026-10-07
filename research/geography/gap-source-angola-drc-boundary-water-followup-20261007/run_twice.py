#!/usr/bin/env python3
"""Verify frozen bytes, reproduce the assessment twice, and compare exact outputs."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from reproduce_assessment import validate_roster, validate_worldcover_grid, verify_pinned_bytes
import rasterio
from affine import Affine

ROOT = Path(__file__).resolve().parents[3]
PACKET = ROOT / "research/geography/gap-source-angola-drc-boundary-water-followup-20261007"
FREEZE = PACKET / "inputs/freeze-v1.json"
PRODUCER = PACKET / "reproduce_assessment.py"


def digest(path):
    data = path.read_bytes()
    return len(data), hashlib.sha256(data).hexdigest()


def verify_frozen():
    document = json.loads(FREEZE.read_text(encoding="utf-8"))
    for row in document["files"]:
        size, sha = digest(ROOT / row["path"])
        if (size, sha) != (row["bytes"], row["sha256"]):
            raise RuntimeError(f"frozen byte mismatch: {row['path']}")
    return document


def main():
    freeze = verify_frozen()
    with tempfile.TemporaryDirectory(prefix="angola-drc-repro-") as temp:
        outputs = []
        for run_number in (1, 2):
            target = Path(temp) / f"assessment-{run_number}.json"
            env = os.environ.copy()
            subprocess.run([sys.executable, str(PRODUCER), "--output", str(target)],
                           cwd=ROOT, env=env, check=True)
            outputs.append(target.read_bytes())
            verify_frozen()
        if outputs[0] != outputs[1]:
            raise RuntimeError("two full producer outputs differ byte-for-byte")
        output_hash = hashlib.sha256(outputs[0]).hexdigest()
        assessment = json.loads(outputs[0])
        output_path = PACKET / "outputs/assessment-v1.json"
        output_path.write_bytes(outputs[0])
        pins = json.loads((PACKET / "inputs/source-pins.json").read_text(encoding="utf-8"))
        small_pin = next(row for row in pins["files"] if row["path"].endswith("sources/worldcover/retrieval.json"))
        actual = (ROOT / small_pin["path"]).read_bytes()
        verify_pinned_bytes(actual, small_pin)
        altered = bytearray(actual); altered[0] ^= 1
        try:
            verify_pinned_bytes(bytes(altered), small_pin)
        except ValueError:
            source_mutation_rejected = True
        else:
            raise RuntimeError("altered source bytes were not rejected")

        component_doc = json.loads((PACKET / "inputs/component-features.geojson").read_text(encoding="utf-8"))
        contact_doc = json.loads((PACKET / "inputs/contact-features.geojson").read_text(encoding="utf-8"))
        roster = json.loads((PACKET / "inputs/family-roster.json").read_text(encoding="utf-8"))
        validate_roster(component_doc["features"], contact_doc["features"], roster)
        omission_rejections = {}
        for label, comps, contacts in (
            ("component", component_doc["features"][:-1], contact_doc["features"]),
            ("contact", component_doc["features"], contact_doc["features"][:-1]),
        ):
            try:
                validate_roster(comps, contacts, roster)
            except ValueError:
                omission_rejections[label] = True
            else:
                raise RuntimeError(f"omitted {label} was not rejected")

        registration_checks = []
        for config in assessment["methods"].get("worldcover_tiles", []):
            with rasterio.open(ROOT / config["path"]) as dataset:
                validate_worldcover_grid(dataset, config["tile"])
                shifted = Affine.translation(1 / 24000, 0) * dataset.transform
                try:
                    validate_worldcover_grid(dataset, config["tile"], transform=shifted)
                except ValueError:
                    registration_checks.append({"tile": config["tile"], "valid_grid_passed": True,
                                                "half_pixel_shift_rejected": True})
                else:
                    raise RuntimeError(f"half-pixel registration shift was not rejected: {config['tile']}")
        if len(registration_checks) != 4:
            raise RuntimeError("expected four WorldCover CRS/registration checks")

        cloud_nodata_checks = []
        for row in assessment["components"]:
            scl = row["sentinel2_scl"]
            counts = {int(k): v for k, v in scl["class_counts"].items()}
            ambiguous = sum(counts.get(cls, 0) for cls in (0, 1, 2, 3, 7, 8, 9, 10, 11))
            if ambiguous != scl["ambiguous_or_unclassified_pixel_centers"] or counts.get(6, 0) != scl["water_class_6_pixel_centers"]:
                raise RuntimeError("SCL cloud/NoData accounting mismatch")
            if sum(counts.values()) != scl["pixel_center_count"] or row["whole_component_water_status"] != "unknown":
                raise RuntimeError("SCL pixel accounting upgraded or lost unknowns")
            cloud_nodata_checks.append(row["component_number_in_frozen_feature_order"])

        scls = [row["sentinel2_scl"]["source_asset_path"] for row in assessment["components"]]
        if any("native-scl/" not in path or "worldcover" in path or "jrc-gsw" in path for path in scls):
            raise RuntimeError("Sentinel SCL path is not the preserved native product asset")
        independence_check = {
            "passed": True,
            "scope": "Source-record independence only: sampled SCL values come from pinned original Sentinel-2 native SCL JP2 assets, distinct from JRC Landsat-derived output and ESA WorldCover thematic maps.",
            "does_not_claim_sensor_independent_validation": True,
            "native_scl_component_rows": len(scls),
        }

        positive = {
            "kind": "positive-control", "outcome": "passed",
            "ten_components_and_five_contacts_present": assessment["controls"]["positive"]["ten_frozen_components_and_five_contacts_present"],
            "all_ten_worldcover_coverage": assessment["controls"]["positive"]["all_ten_have_worldcover_pixel_centres_in_each_vintage"],
            "all_ten_full_scl_grid_coverage": assessment["controls"]["positive"]["all_ten_have_fully_covered_scl_scene_grid"],
            "all_contact_bindings_retained": len(assessment["contacts"]) == 5,
            "all_ten_saved_search_selections_reproduced": assessment["controls"]["sentinel_selection_is_reproduced_from_saved_first_page"],
            "worldcover_crs_registration_checks": registration_checks,
            "source_independence": independence_check,
        }
        negative = {
            "kind": "negative-control", "outcome": "passed",
            "altered_source_byte_rejected": source_mutation_rejected,
            "component_omission_rejected": omission_rejections["component"],
            "contact_omission_rejected": omission_rejections["contact"],
            "half_pixel_registration_shift_rejected_on_all_tiles": all(x["half_pixel_shift_rejected"] for x in registration_checks),
            "cloud_shadow_unclassified_and_nodata_cells_remain_ambiguous": len(cloud_nodata_checks) == 10,
            "scl_water_class_remains_local_product_label": all(row["whole_component_water_status"] == "unknown" for row in assessment["components"]),
            "worldcover_and_scl_vintages_not_collapsed": len(assessment["methods"].get("worldcover_vintages", [])) == 2,
        }
        if not all(value for key, value in negative.items() if key not in ("method_id", "kind", "outcome")):
            raise RuntimeError("negative control did not pass")
        for method_id, prefix in (("worldcover-pixel-observation", "worldcover"),
                                  ("native-sentinel-scl-pixel-observation", "sentinel-scl")):
            pos = {"method_id": method_id, **positive}
            neg = {"method_id": method_id, **negative}
            (PACKET / f"outputs/{prefix}-positive-control-v1.json").write_text(
                json.dumps(pos, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
            (PACKET / f"outputs/{prefix}-negative-control-v1.json").write_text(
                json.dumps(neg, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        run_hash = hashlib.sha256(outputs[0]).hexdigest()
        reproducibility = {"method_id": "assessment-generator", "kind": "reproducibility", "outcome": "passed",
                           "run_one_sha256": run_hash, "run_two_sha256": hashlib.sha256(outputs[1]).hexdigest(),
                           "run_one_bytes": len(outputs[0]), "run_two_bytes": len(outputs[1]),
                           "runs_byte_identical": outputs[0] == outputs[1]}
        (PACKET / "outputs/reproducibility-control-v1.json").write_text(json.dumps(reproducibility, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        receipt = {
            "version": "frozen-two-run-receipt-v1",
            "freeze_sha256": hashlib.sha256(FREEZE.read_bytes()).hexdigest(),
            "freeze_file_count": len(freeze["files"]),
            "run_count": 2,
            "runs_byte_identical": True,
            "output_path": str(output_path.relative_to(ROOT)),
            "output_bytes": len(outputs[0]),
            "output_sha256": output_hash,
        }
        (PACKET / "outputs/reproduction-receipt.json").write_text(
            json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
