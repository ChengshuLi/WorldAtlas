#!/usr/bin/env python3
"""Exercise real #633 CLI output admission without touching retained evidence."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
import uuid


PACKET = Path(__file__).resolve().parent
ROOT = next(parent for parent in PACKET.parents if (parent / "AGENTS.md").is_file())
SCRIPT = PACKET / "reproduce.py"
VINTAGES = PACKET / "vintages"
STATIC_OUTPUTS = [PACKET / name for name in
                  ("subject-findings.json", "district-comparison.json", "results.json")]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReproductionAdmissionTests(unittest.TestCase):
    def setUp(self):
        VINTAGES.mkdir(exist_ok=True)
        self.prefix = "safety-test-" + uuid.uuid4().hex[:12]
        self.static_hashes = {path: digest(path) for path in STATIC_OUTPUTS}

    def tearDown(self):
        for path in VINTAGES.glob(self.prefix + "*"):
            if path.is_symlink() or path.is_file():
                path.unlink()
            elif path.is_dir():
                for child in path.iterdir():
                    if child.is_file() or child.is_symlink():
                        child.unlink()
                path.rmdir()
        self.assertEqual(self.static_hashes, {path: digest(path) for path in STATIC_OUTPUTS})

    def run_cli(self, vintage: str, *extra: str):
        return subprocess.run([sys.executable, str(SCRIPT), "--vintage", vintage, *extra],
                              cwd=ROOT, capture_output=True, text=True, check=False)

    def test_existing_ordinary_run_is_preserved(self):
        vintage = self.prefix + "-existing"
        target = VINTAGES / vintage
        target.mkdir()
        sentinel = target / "sentinel.txt"
        sentinel.write_bytes(b"keep existing evidence\n")
        result = self.run_cli(vintage)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FileExistsError", result.stderr)
        self.assertEqual(sentinel.read_bytes(), b"keep existing evidence\n")
        self.assertEqual([path.name for path in target.iterdir()], ["sentinel.txt"])

    def test_broken_symlink_run_is_rejected_without_following_it(self):
        vintage = self.prefix + "-broken-link"
        target = VINTAGES / vintage
        target.symlink_to(VINTAGES / (self.prefix + "-missing-target"))
        result = self.run_cli(vintage)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Symlink", result.stderr)
        self.assertTrue(target.is_symlink())
        self.assertFalse(target.resolve(strict=False).exists())

    def test_failure_after_calculation_has_no_output_vintage_or_receipt(self):
        vintage = self.prefix + "-late-failure"
        target = VINTAGES / vintage
        result = self.run_cli(vintage, "--simulate-post-computation-failure")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("failed after computation", result.stderr)
        self.assertFalse(target.exists())
        self.assertFalse((target / "publication.json").exists())

    def test_path_traversal_is_rejected(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--vintage", "../" + self.prefix],
                                cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((PACKET.parent / self.prefix).exists())

    def test_parent_roster_uses_authenticated_reader_bytes(self):
        spec = importlib.util.spec_from_file_location("wio_reproduce_under_test", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        identity = "gb:MUS:ADM1:65221844B12885462064369"
        captured = (json.dumps({"id": identity, "sentinel": "authenticated snapshot"}) + "\n").encode()

        class CapturedBaseline:
            def materialized_bytes(self, _path):
                return captured

        previous = module.BASELINE
        module.BASELINE = CapturedBaseline()
        try:
            rows = module.parent_inventory_for_scope(PACKET.parent / "regional-review-4f180b98473f1071" / "subject-inventory.jsonl", {identity})
        finally:
            module.BASELINE = previous
        self.assertEqual(rows[identity]["sentinel"], "authenticated snapshot")


if __name__ == "__main__":
    unittest.main(verbosity=2)
