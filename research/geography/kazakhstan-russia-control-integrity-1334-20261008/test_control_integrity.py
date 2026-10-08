#!/usr/bin/env python3
"""Credential-free tests for the documented #1491 CLI and actual control predicates."""

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid

from control_integrity import (
    EXPECTED_OUTPUTS, check_candidate_rows, check_contacts, check_family_rows, check_products, check_output_comparison,
    load_json, source_id_rows, ORIGINAL, OWNED,
)

REPO = Path(__file__).resolve().parents[3]
PACKET = REPO / ORIGINAL
OWNED_DIR = Path(__file__).resolve().parent
BASE = json.loads((OWNED_DIR / "evidence-quality.json").read_text())["baseline"]["commit"]
PYTHON = sys.executable


def read_run(n):
    root = PACKET / f"executions/run-{n}"
    manifest = json.loads((root / "output-manifest.json").read_text())
    products = {row["path"]: (root / row["path"]).read_bytes() for row in manifest["outputs"]}
    return manifest, products


class ControlIntegrityTests(unittest.TestCase):
    def test_complete_outputs_and_manifest_are_verified_from_bytes(self):
        for n in (1, 2):
            manifest, products = read_run(n)
            check_products(manifest, products)
            self.assertEqual(set(products), EXPECTED_OUTPUTS)

    def test_actual_mutated_or_missing_run_two_product_is_rejected(self):
        manifest, products = read_run(2)
        changed = dict(products)
        changed["candidate-assessment.jsonl"] += b"\n"
        with self.assertRaisesRegex(ValueError, "actual output bytes"):
            check_products(manifest, changed)
        with self.assertRaisesRegex(ValueError, "inventory"):
            check_products(manifest, {k: v for k, v in products.items() if k != "source-products.json"})
        wrong_hash = json.loads(json.dumps(manifest))
        wrong_hash["outputs"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "actual output bytes"):
            check_products(wrong_hash, products)

    def test_source_relative_28_24_classifications_are_preserved(self):
        rows = [json.loads(line) for line in (PACKET / "executions/run-1/candidate-assessment.jsonl").read_text().splitlines() if line.strip()]
        handoff = json.loads((PACKET / "inputs/complete-kazakhstan-russia-handoff.json").read_text())
        check_candidate_rows(rows, sorted(handoff["component_ids"]))
        changed = json.loads(json.dumps(rows))
        changed[0]["source_fitness_class"] = "partial/unbound original source-fitness case"
        with self.assertRaisesRegex(ValueError, "28/24 scope"):
            check_candidate_rows(changed, sorted(handoff["component_ids"]))

    def test_stale_run_comparison_hash_is_rejected_against_actual_manifests(self):
        m1, p1 = read_run(1)
        m2, p2 = read_run(2)
        r1 = (json.loads((PACKET / "executions/run-1-receipt.json").read_text()),
              (PACKET / "executions/run-1/output-manifest.json").read_bytes(), p1)
        r2 = (json.loads((PACKET / "executions/run-2-receipt.json").read_text()),
              (PACKET / "executions/run-2/output-manifest.json").read_bytes(), p2)
        comparison = json.loads((PACKET / "executions/output-comparison.json").read_text())
        check_output_comparison(comparison, r1, r2)
        changed = dict(comparison)
        changed["run2_output_manifest_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "hashes differ"):
            check_output_comparison(changed, r1, r2)

    def test_complete_contact_identity_and_feature_join_rejects_omission_duplicate_rebinding(self):
        handoff = json.loads((PACKET / "inputs/complete-kazakhstan-russia-handoff.json").read_text())
        contacts = json.loads((PACKET / "executions/run-1/contact-lineage.json").read_text())["contacts"]
        expected = sorted(handoff["contact_ids"])
        source = handoff["full_current_contacts"]
        check_contacts(contacts, expected, source)
        for changed in (contacts[:-1], contacts + [contacts[0]]):
            with self.assertRaises(ValueError):
                check_contacts(changed, expected, source)
        rebound = json.loads(json.dumps(contacts))
        rebound[0]["id"] = "gb:KAZ:ADM2:foreign-control"
        with self.assertRaisesRegex(ValueError, "roster"):
            check_contacts(rebound, expected, source)
        altered = json.loads(json.dumps(contacts))
        altered[0]["feature"]["properties"]["name"] = "controlled mutation"
        with self.assertRaisesRegex(ValueError, "feature differs"):
            check_contacts(altered, expected, source)

    def test_duplicate_empty_family_cannot_hide_behind_same_membership_union(self):
        handoff = json.loads((PACKET / "inputs/complete-kazakhstan-russia-handoff.json").read_text())
        report = json.loads((PACKET / "executions/run-1/family-reconciliation.json").read_text())
        expected_ids = sorted(handoff["component_ids"])
        expected_families = sorted(handoff["complete_family_ids"])
        check_family_rows(report["families"], expected_families, expected_ids)
        duplicate = json.loads(json.dumps(report["families"]))
        empty = json.loads(json.dumps(duplicate[0]))
        empty["candidate_ids"] = []
        empty["component_count"] = 0
        duplicate.append(empty)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            check_family_rows(duplicate, expected_families, expected_ids)
        rebound = json.loads(json.dumps(report["families"]))
        rebound[0]["candidate_ids"][0] = "physical-component:foreign-control"
        with self.assertRaises(ValueError):
            check_family_rows(rebound, expected_families, expected_ids)

    def test_real_native_kazakhstan_id_reader_detects_changed_id(self):
        full = (PACKET / "inputs/geoboundaries-kaz-adm2-2017-full-source.geojson").read_bytes()
        simplified = (PACKET / "inputs/geoboundaries-kaz-adm2-2017-simplified-full-source.geojson").read_bytes()
        ids = source_id_rows(full, simplified)
        self.assertEqual(len(ids), 174)
        changed = json.loads(simplified)
        changed["features"][0]["properties"]["shapeID"] += ":changed"
        with self.assertRaisesRegex(ValueError, "rosters differ"):
            source_id_rows(full, json.dumps(changed).encode())

    def invoke(self, vintage):
        return subprocess.run([PYTHON, str(OWNED_DIR / "control_integrity.py"), "--repo", str(REPO),
                               "--baseline", BASE, "--vintage", vintage], cwd=REPO,
                              text=True, capture_output=True)

    def test_documented_cli_twice_with_fresh_names_reconciles_complete_runs(self):
        names = ("pytest-live-one", "pytest-live-two")
        try:
            results = [self.invoke(name) for name in names]
            for result in results:
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)["historical_runs"], 2)
            files = []
            for name in names:
                root = OWNED_DIR / "vintages" / name
                receipt = json.loads((root / "publication.json").read_text())
                self.assertEqual(receipt["status"], "complete")
                self.assertEqual({Path(row["path"]).name for row in receipt["outputs"]},
                                 {"positive-control.json", "negative-control.json", "reproducibility-control.json"})
                files.append({p.name: p.read_bytes() for p in root.glob("*.json") if p.name != "publication.json"})
            self.assertEqual(files[0], files[1])
        finally:
            for name in names:
                shutil.rmtree(OWNED_DIR / "vintages" / name, ignore_errors=True)

    def test_cli_rejects_ordinary_collision_and_preserves_sentinel(self):
        root = OWNED_DIR / "vintages" / "pytest-occupied-file"
        root.parent.mkdir(parents=True, exist_ok=True)
        root.write_bytes(b"sentinel")
        try:
            result = self.invoke(root.name)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(root.read_bytes(), b"sentinel")
        finally:
            root.unlink(missing_ok=True)

    def test_cli_rejects_directory_and_dangling_symlink_before_publication(self):
        parent = OWNED_DIR / "vintages"
        parent.mkdir(parents=True, exist_ok=True)
        directory = parent / "pytest-occupied-directory"
        directory.mkdir(exist_ok=True)
        live = parent / "pytest-live-vintage"
        live_target = parent / "pytest-live-target"
        link = parent / "pytest-dangling-vintage"
        target = parent / "pytest-dangling-target"
        if live.exists() or live.is_symlink():
            live.unlink()
        live_target.write_bytes(b"live-target-sentinel")
        live.symlink_to(live_target)
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(target)
        try:
            self.assertNotEqual(self.invoke(directory.name).returncode, 0)
            self.assertNotEqual(self.invoke(live.name).returncode, 0)
            self.assertTrue(live.is_symlink())
            self.assertEqual(live_target.read_bytes(), b"live-target-sentinel")
            result = self.invoke(link.name)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(link.is_symlink())
            self.assertFalse(target.exists())
            self.assertFalse((OWNED_DIR / "vintages" / link.name / "publication.json").exists())
        finally:
            live.unlink(missing_ok=True)
            live_target.unlink(missing_ok=True)
            link.unlink(missing_ok=True)
            directory.rmdir()

    def test_cli_rejects_unsafe_ancestor_and_escaped_vintage(self):
        vintages = OWNED_DIR / "vintages"
        held = OWNED_DIR / "vintages-pytest-held"
        target = OWNED_DIR / "vintages-pytest-target"
        if held.exists() or held.is_symlink() or target.exists() or target.is_symlink():
            self.fail("refusing to replace pre-existing ancestor-test paths")
        vintages.rename(held)
        target.mkdir()
        vintages.symlink_to(target, target_is_directory=True)
        try:
            result = self.invoke("pytest-ancestor-child")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Symlink in output path", result.stderr)
            self.assertEqual(list(target.iterdir()), [])
        finally:
            vintages.unlink(missing_ok=True)
            target.rmdir()
            held.rename(vintages)
        escaped = OWNED_DIR.parent / "pytest-escaped-vintage"
        if escaped.exists() or escaped.is_symlink():
            self.fail("refusing to use pre-existing escaped test destination")
        result = self.invoke("../pytest-escaped-vintage")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(escaped.exists())

    def test_partial_publication_failure_never_installs_completion_receipt(self):
        spec = importlib.util.spec_from_file_location("immutable_partial_test", REPO / "scripts/evidence/immutable.py")
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        desc = helper.descriptor
        pinned = helper.Baseline(REPO, BASE, [desc("scripts/evidence/immutable.py", (REPO / "scripts/evidence/immutable.py").read_bytes())])
        vintage = "pytest-partial-failure-" + uuid.uuid4().hex
        writer = helper.NewVintage(pinned, OWNED, vintage, ["one.json", "two.json"])
        original_link = helper.os.link

        def fail_link(*args, **kwargs):
            raise OSError("injected final-receipt failure")

        helper.os.link = fail_link
        try:
            with self.assertRaisesRegex(OSError, "injected"):
                writer.publish({"one.json": {"ok": True}, "two.json": {"ok": True}})
        finally:
            helper.os.link = original_link
        failed = writer.root
        self.assertTrue((failed / "one.json").is_file())
        self.assertFalse((failed / "publication.json").exists())
        self.assertTrue((failed / ".publication-incomplete").is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
