from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import shutil
import sys
import uuid
import unittest

PACKET = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("guarded_reproduce", PACKET / "guarded_reproduce.py")
guard = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = guard
spec.loader.exec_module(guard)


class GuardedReproducerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pins = guard.load_pins(guard.PIN_FILE.read_bytes())
        cls.blobs = {}
        for item in cls.pins["inputs"]:
            key = (item["commit"], item["path"])
            cls.blobs[key] = guard.git_blob(*key)
        gen = cls.pins["original_generator"]
        cls.blobs[(gen["commit"], gen["path"])] = guard.git_blob(gen["commit"], gen["path"])

    def run_with_mutation(self, relative_output, key, mutate, issue_bytes=None):
        modified = dict(self.blobs)
        modified[key] = mutate(modified[key])
        def reader(commit, path):
            return modified[(commit, path)]
        with self.assertRaises(guard.GuardError):
            guard.run_reproduction(relative_output, reader=reader, issue_bytes=issue_bytes)
        self.assertFalse((PACKET / relative_output).exists(), "rejected input must publish no output directory")
        staging = PACKET / ".scratch" / "guarded-runs"
        self.assertFalse(staging.exists() and any(staging.iterdir()),
                         "preflight rejection must happen before any result staging")

    def test_metadata_boundary_year_complete_file_probe_is_rejected(self):
        path = f"{guard.PRIOR_PACKET}/source/gb/SRB-ADM2-geoBoundaries-SRB-ADM2-metaData.json"
        def mutate(raw):
            value = json.loads(raw)
            value["boundaryYear"] = "AUDITOR_SYNTHETIC_VINTAGE"
            return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
        fixture = mutate(self.blobs[(self.pins["inputs"][0]["commit"], path)])
        self.assertEqual(len(fixture), 919)
        self.assertEqual(guard.sha256(fixture), "83fd350882500111a1ebcfbc6840a119a03097c465a76fde57cf663c1967668e")
        self.assertEqual(fixture, (PACKET / "tests/fixtures/metadata-boundary-year.json").read_bytes())
        self.run_with_mutation("results/run-negative-metadata", (self.pins["inputs"][0]["commit"], path), lambda _: fixture)

    def test_shortened_scope_complete_file_is_rejected_before_output(self):
        path = f"{guard.TARGET_PACKET}/source-issue-998.json"
        key = next((row["commit"], row["path"]) for row in self.pins["inputs"] if row["path"] == path)
        original = self.blobs[key]
        issue = json.loads(original)
        match = re.search(r"<!-- worldatlas-work:v1\s*(\{.*?\})\s*-->", issue["body"], re.S)
        contract = json.loads(match.group(1))
        ids = contract["evidence_quality"]["subject_ids"]
        self.assertEqual(len(ids), 78)
        contract["evidence_quality"]["subject_ids"] = ids[:-1]
        issue["body"] = issue["body"][:match.start(1)] + json.dumps(
            contract, ensure_ascii=False, separators=(",", ":")
        ) + issue["body"][match.end(1):]
        fixture = (json.dumps(issue, ensure_ascii=False, indent=2) + "\n").encode()
        self.assertEqual(fixture, (PACKET / "tests/fixtures/issue-998-77-subjects.json").read_bytes())
        with self.assertRaises(guard.GuardError):
            guard.validate_issue_998(fixture, self.pins["subject_ids"])
        self.run_with_mutation("results/run-negative-short-scope", key, lambda _: fixture)

    def test_wrong_baseline_bytes_are_rejected(self):
        item = next(row for row in self.pins["inputs"] if row["commit"] == self.pins["baseline_commit"])
        key = (item["commit"], item["path"])
        self.run_with_mutation("results/run-negative-baseline", key, lambda raw: raw + b" ")

    def test_wrong_workbook_bytes_are_rejected(self):
        item = next(row for row in self.pins["inputs"] if row["path"].endswith("sors-cities-municipalities-2017.xls"))
        key = (item["commit"], item["path"])
        self.run_with_mutation("results/run-negative-workbook", key, lambda raw: raw[:-1] + bytes([raw[-1] ^ 1]))

    def test_wrong_historical_generator_bytes_are_rejected(self):
        item = self.pins["original_generator"]
        key = (item["commit"], item["path"])
        self.run_with_mutation("results/run-negative-code", key, lambda raw: raw + b"\n# synthetic corruption\n")

    def test_duplicate_or_unmatched_scope_is_rejected(self):
        ids = self.pins["subject_ids"]
        with self.assertRaises(guard.GuardError):
            guard.validate_subject_list(ids[:-1], ids, "short scope")
        with self.assertRaises(guard.GuardError):
            guard.validate_subject_list(ids[:-1] + [ids[0]], ids, "duplicate scope")
        with self.assertRaises(guard.GuardError):
            guard.validate_subject_list(ids[:-1] + ["gb:SRB:ADM2:SYNTHETIC"], ids, "unmatched scope")

    def test_existing_output_is_preserved_and_rejected(self):
        result = PACKET / "results" / "run-existing"
        result.mkdir(parents=True, exist_ok=True)
        sentinel = result / "sentinel.txt"
        sentinel.write_text("preserve this prior result\n")
        with self.assertRaises(guard.GuardError):
            guard.run_reproduction("results/run-existing")
        self.assertEqual(sentinel.read_text(), "preserve this prior result\n")
        self.assertEqual(sorted(path.name for path in result.iterdir()), ["sentinel.txt"])
        sentinel.unlink()
        result.rmdir()
        if not any((PACKET / "results").iterdir()):
            (PACKET / "results").rmdir()

    def test_two_runs_are_byte_reproducible_and_match_historical_outputs(self):
        token = uuid.uuid4().hex
        first_name, second_name = f"run-test-{token}-one", f"run-test-{token}-two"
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                first = guard.run_reproduction(f"results/{first_name}")
                second = guard.run_reproduction(f"results/{second_name}")
            self.assertEqual(first["files"], second["files"])
            self.assertEqual(len(first["files"]), 8)
            historical = guard.historical_output_map(self.pins)
            for row in first["files"]:
                if row["path"] != "reproduction-summary.json":
                    self.assertEqual(row["sha256"], historical[row["path"]]["sha256"])
            current = json.loads((PACKET / "results" / first_name / "reproduction-summary.json").read_text())
            summary = next(x for x in self.pins["historical_outputs"] if x["path"].endswith("reproduction-summary.json"))
            prior = json.loads(self.blobs[(summary["commit"], summary["path"])])
            self.assertEqual(current["python"], "3.12.14")
            self.assertEqual(current["pandas"], "2.2.3")
            current.pop("python")
            current.pop("pandas")
            prior.pop("python")
            prior.pop("pandas")
            self.assertEqual(current, prior)
        finally:
            shutil.rmtree(PACKET / "results" / first_name, ignore_errors=True)
            shutil.rmtree(PACKET / "results" / second_name, ignore_errors=True)
            if (PACKET / "results").exists() and not any((PACKET / "results").iterdir()):
                (PACKET / "results").rmdir()


if __name__ == "__main__":
    unittest.main()
