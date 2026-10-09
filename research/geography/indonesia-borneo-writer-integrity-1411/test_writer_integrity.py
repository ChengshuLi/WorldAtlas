"""Focused adverse controls for the #1557 standalone output writers."""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock
OWNED = Path(__file__).resolve().parent
REPO = OWNED.parents[2]
import sys
sys.path.insert(0, str(OWNED))

import big_writer
import identity_writer
from output_admission import reserve_output_set, verify_receipt


SOURCE_PACKET = REPO / "research/geography/indonesia-borneo-source-fitness-20261007/sources/v1"
EXPECTED_IDS = sorted((SOURCE_PACKET / "component-roster.txt").read_text().splitlines())
FAMILY = json.loads((SOURCE_PACKET / "family-row.json").read_bytes().rstrip(b"\n"))


def _sandbox_identity():
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name).resolve()
    repo = root / "repo"
    packet = repo / "research/geography/indonesia-borneo-writer-integrity-1411"
    packet.mkdir(parents=True)
    (packet / "inputs").mkdir()
    files = [
        "family-row.json", "component-roster.txt", "subject-inventory.json",
        "subject-registry.json", "build-subject-inventory.py",
    ]
    for name in files:
        (packet / "unused").mkdir(exist_ok=True)
        source = SOURCE_PACKET / name
        target = repo / "research/geography/indonesia-borneo-source-fitness-20261007/sources/v1" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    code_dir = repo / "research/geography/indonesia-borneo-writer-integrity-1411"
    for name in ("identity_writer.py", "output_admission.py"):
        shutil.copyfile(OWNED / name, code_dir / name)
    return tmp, repo, packet


class OutputAdmissionTests(unittest.TestCase):
    def test_traversal_dangling_leaf_ordinary_file_and_symlink_ancestor_refuse(self):
        with tempfile.TemporaryDirectory() as directory:
            packet = Path(directory).resolve() / "packet"
            packet.mkdir()
            with self.assertRaises(ValueError):
                reserve_output_set(packet, "run-../escape", ("result.json", "completion.json"))
            self.assertFalse((Path(directory) / "escape").exists())

            runs = packet / "runs"
            runs.mkdir()
            outside = Path(directory).resolve() / "outside"
            outside.mkdir()
            (runs / "run-dangling").symlink_to(outside / "missing")
            with self.assertRaises(FileExistsError):
                reserve_output_set(packet, "run-dangling", ("result.json", "completion.json"))
            self.assertFalse((outside / "missing").exists())

            (runs / "run-occupied").mkdir()
            sentinel = runs / "run-occupied" / "result.json"
            sentinel.write_bytes(b"keep this exact sentinel")
            with self.assertRaises(FileExistsError):
                reserve_output_set(packet, "run-occupied", ("result.json", "completion.json"))
            self.assertEqual(sentinel.read_bytes(), b"keep this exact sentinel")

            runs.rename(packet / "runs-real")
            (packet / "runs").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(OSError):
                reserve_output_set(packet, "run-ancestor", ("result.json", "completion.json"))
            self.assertFalse((outside / "run-ancestor").exists())

    def test_successful_synthetic_big_writer_fixture_receipt_detects_changed_product(self):
        with tempfile.TemporaryDirectory() as directory:
            packet = Path(directory).resolve() / "owned"
            packet.mkdir()
            with reserve_output_set(packet, "run-synthetic-writer-only",
                                    big_writer.OUTPUTS) as reservation:
                original = {"fixture_kind": "synthetic-writer-only", "features": []}
                body = (json.dumps(original, sort_keys=True) + "\n").encode()
                reservation.publish({"big-ksp-overlay-assessment.json": body}, {
                    "version": 1, "status": "complete", "issue": 1557,
                    "limits": ["Synthetic publication fixture; no geographic computation or source claim."],
                })
            run = packet / "runs" / "run-synthetic-writer-only"
            receipt = verify_receipt(run)
            self.assertEqual(receipt["status"], "complete")
            product = run / "big-ksp-overlay-assessment.json"
            product.write_bytes(product.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "Changed comparison product"):
                verify_receipt(run)

    def test_big_refusal_precedes_both_source_reader_and_geometry_computer(self):
        calls = {"read": 0, "compute": 0}

        def load(*args):
            calls["read"] += 1
            raise AssertionError("source access ran before output admission")

        def compute(*args):
            calls["compute"] += 1
            raise AssertionError("geometry computation ran before output admission")

        with tempfile.TemporaryDirectory() as directory:
            packet = Path(directory).resolve() / "owned"
            packet.mkdir()
            (packet / "runs").mkdir()
            (packet / "runs" / "run-occupied").mkdir()
            with self.assertRaises(FileExistsError):
                big_writer.execute("run-occupied", "/does/not/exist",
                                   packet_root=packet, repo_root=Path(directory),
                                   load_inputs=load, compute=compute)
            with self.assertRaises(ValueError):
                big_writer.execute("run-../escaped", "/does/not/exist",
                                   packet_root=packet, repo_root=Path(directory),
                                   load_inputs=load, compute=compute)
        self.assertEqual(calls, {"read": 0, "compute": 0})

    def test_persistent_occupied_output_sentinels_and_dangling_link_survive_both_writers(self):
        fixture_root = OWNED / "controls" / "fixtures"
        occupied = fixture_root / "runs" / "run-occupied"
        paths = [occupied / name for name in (
            "subject-inventory.json", "subject-registry.json",
            "big-ksp-overlay-assessment.json", "completion.json")]
        sentinels = {path: path.read_bytes() for path in paths}
        calls = {"identity": 0, "big_read": 0, "big_compute": 0}

        def forbidden_identity_read(*args):
            calls["identity"] += 1
            raise AssertionError("identity inputs were read before output refusal")

        def forbidden_big_read(*args):
            calls["big_read"] += 1
            raise AssertionError("BIG inputs were read before output refusal")

        def forbidden_big_compute(*args):
            calls["big_compute"] += 1
            raise AssertionError("BIG computation ran before output refusal")

        with self.assertRaises(FileExistsError):
            identity_writer.execute("run-occupied", repo_root=REPO, packet_root=fixture_root,
                                    load_inputs=forbidden_identity_read)
        with self.assertRaises(FileExistsError):
            big_writer.execute("run-occupied", "/does/not/exist", repo_root=REPO,
                               packet_root=fixture_root, load_inputs=forbidden_big_read,
                               compute=forbidden_big_compute)
        for path, original in sentinels.items():
            self.assertEqual(path.read_bytes(), original)

        self.assertEqual(calls, {"identity": 0, "big_read": 0, "big_compute": 0})

    def test_big_selection_tamper_refuses_before_external_source_read(self):
        with tempfile.TemporaryDirectory() as directory:
            packet = Path(directory).resolve() / "owned"
            selection = packet / "inputs" / "big-selection-response.json"
            selection.parent.mkdir(parents=True)
            selection.write_bytes((OWNED / "inputs" / "big-selection-response.json").read_bytes() + b" ")
            with mock.patch.object(big_writer, "read_external_regular",
                                   side_effect=AssertionError("external source read occurred")) as source_read:
                with self.assertRaisesRegex(ValueError, "Pinned input changed: selection-response"):
                    big_writer.execute("run-selection-tamper", "/missing/source.geojson",
                                       repo_root=REPO, packet_root=packet)
                source_read.assert_not_called()
            run = packet / "runs" / "run-selection-tamper"
            self.assertEqual(list(run.iterdir()), [])

    def test_big_source_subject_controls_reject_missing_duplicate_fabricated(self):
        fixtures = [{"properties": {"objectid": value}} for value in big_writer.SELECTION_IDS]
        self.assertEqual(big_writer.validate_source_features(fixtures), fixtures)
        for label, candidate in [
            ("missing", fixtures[:-1]),
            ("duplicate", fixtures[:-1] + [fixtures[0]]),
            ("fabricated", fixtures[:-1] + [{"properties": {"objectid": 999999}}]),
        ]:
            with self.subTest(label=label):
                with self.assertRaises(ValueError):
                    big_writer.validate_source_features(candidate)

    def test_identity_refuses_tampered_pinned_input_without_product_or_receipt(self):
        tmp, repo, packet = _sandbox_identity()
        try:
            family_path = repo / identity_writer.INPUTS["family-row"][0]
            family_path.write_bytes(family_path.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "Pinned input changed"):
                identity_writer.execute("run-input-tamper", repo_root=repo, packet_root=packet)
            run = packet / "runs" / "run-input-tamper"
            self.assertTrue(run.is_dir())
            self.assertEqual(list(run.iterdir()), [])
        finally:
            tmp.cleanup()

    def test_identity_semantics_reject_missing_duplicate_and_fabricated_subjects(self):
        for label, mutate in [
            ("missing", lambda ids: ids[:-1]),
            ("duplicate", lambda ids: ids[:-1] + [ids[0]]),
            ("fabricated", lambda ids: ids[:-1] + ["physical-component:" + "f" * 64]),
        ]:
            with self.subTest(label=label):
                ids = list(EXPECTED_IDS)
                family = dict(FAMILY)
                family["complete_component_ids"] = mutate(ids)
                with self.assertRaises(ValueError):
                    identity_writer.identity_products(family, EXPECTED_IDS)

    def test_identity_changed_comparison_product_is_rejected(self):
        family = dict(FAMILY)
        family["complete_component_ids"] = list(EXPECTED_IDS)
        products = identity_writer.identity_products(family, EXPECTED_IDS)
        changed = dict(products)
        changed["subject-registry.json"] += b" "
        with self.assertRaisesRegex(ValueError, "Changed comparison product"):
            identity_writer.compare_original_products(products, changed)

    def test_big_component_identity_controls_reject_missing_duplicate_fabricated(self):
        expected = list(EXPECTED_IDS)
        rows = [{"type": "Feature", "properties": {"role": "original_pinned_component",
                 "component_id": value}} for value in expected]
        for label, candidate in [
            ("missing", rows[:-1]),
            ("duplicate", rows[:-1] + [rows[0]]),
            ("fabricated", rows[:-1] + [{"type": "Feature",
             "properties": {"role": "original_pinned_component",
                            "component_id": "physical-component:" + "f" * 64}}]),
        ]:
            with self.subTest(label=label):
                loaded = {"original-components": {"features": candidate}, "component-ids": expected}
                with self.assertRaises(ValueError):
                    big_writer._component_features(loaded)

    def test_big_changed_comparison_product_is_rejected(self):
        baseline = {"scope": {"component_count": 45, "source_feature_count": 12,
                              "candidate_pair_count": 540},
                    "summary": {"components_with_intersection": 43},
                    "component_results": [{"component_id": "synthetic-a", "intersection_count": 1}]}
        changed = json.loads(json.dumps(baseline))
        changed["component_results"][0]["intersection_count"] = 2
        with self.assertRaisesRegex(ValueError, "Changed comparison product"):
            big_writer.compare_original_assessment(changed, baseline)


if __name__ == "__main__":
    unittest.main(verbosity=2)
