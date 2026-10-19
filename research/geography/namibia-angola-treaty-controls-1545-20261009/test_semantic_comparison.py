#!/usr/bin/env python3
"""Focused CLI controls using the immutable PR #1545 final findings."""
from __future__ import print_function

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from verify_semantic_comparison import derive

SCRIPT = Path(__file__).with_name("verify_semantic_comparison.py")
PACKET = Path(sys.argv.pop(1)).resolve() if len(sys.argv) > 1 else None


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump(path, value):
    Path(path).write_text(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":"), allow_nan=False) + "\n",
                          encoding="utf-8")


def make_run(root, run_id, findings, positive, negative):
    folder = root / run_id
    folder.mkdir(parents=True)
    findings, positive, negative = (copy.deepcopy(findings), copy.deepcopy(positive),
                                    copy.deepcopy(negative))
    findings["run_id"] = positive["run_id"] = negative["run_id"] = run_id
    rows = []
    for name, value in (("findings.json", findings), ("positive-control.json", positive),
                        ("negative-control.json", negative)):
        path = folder / name
        dump(path, value)
        raw = path.read_bytes()
        rows.append({"path": str(path.relative_to(root)), "bytes": len(raw),
                     "sha256": hashlib.sha256(raw).hexdigest()})
    dump(folder / "publication.json", {"version": 1, "status": "complete", "outputs": rows})
    return folder


class SemanticComparisonControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if PACKET is None:
            raise RuntimeError("usage: python3 test_semantic_comparison.py PATH_TO_PR1545_PACKET")
        packet = PACKET
        cls.run5 = read_json(packet / "vintages/treaty-page-audit-5/findings.json")
        cls.run6 = read_json(packet / "vintages/treaty-page-audit-6/findings.json")
        cls.positive = read_json(packet / "vintages/treaty-page-audit-5/positive-control.json")
        cls.negative = read_json(packet / "vintages/treaty-page-audit-5/negative-control.json")
        cls.positive6 = read_json(packet / "vintages/treaty-page-audit-6/positive-control.json")
        cls.negative6 = read_json(packet / "vintages/treaty-page-audit-6/negative-control.json")

    def invoke(self, root, left, right, output):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(root), "--left", str(left),
             "--right", str(right), "--output", str(Path(output).relative_to(root))],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

    def pair(self, root, second=None, recompute=False):
        left = make_run(root, "fixture-left", self.run5, self.positive, self.negative)
        findings = copy.deepcopy(second if second is not None else self.run6)
        if recompute:
            findings["semantic_result_sha256"] = derive(findings)
        right = make_run(root, "fixture-right", findings, self.positive6, self.negative6)
        return left, right

    def test_retained_final_hashes_recompute(self):
        expected = "a72bf39565ffdc2cf32fc4801dad770807a14b4670f330d81a3484933d8f1c71"
        self.assertEqual(derive(self.run5), expected)
        self.assertEqual(derive(self.run6), expected)

    def test_matching_pair_passes_and_publishes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            left, right = self.pair(root)
            output = root / "passed.json"
            result = self.invoke(root, left, right, output)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(output.read_text())["outcome"], "passed")

    def test_changed_body_with_refreshed_publication_and_stale_result_hash_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            changed = copy.deepcopy(self.run6)
            changed["source_observations"]["beacon_47_printed_page"] = 165
            left, right = self.pair(root, changed)
            output = root / "must-not-exist.json"
            result = self.invoke(root, left, right, output)
            self.assertEqual(result.returncode, 1)
            self.assertIn("does not authenticate actual stable findings", result.stderr)
            self.assertFalse(output.exists())

    def test_successor_method_identity_cannot_be_substituted(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            left, right = self.pair(root)
            findings_path = right / "findings.json"
            findings = read_json(findings_path)
            findings["method"]["path"] = "research/geography/namibia-angola-treaty-controls-1545-20261009/verify_semantic_comparison.py"
            dump(findings_path, findings)
            receipt = read_json(right / "publication.json")
            raw = findings_path.read_bytes()
            row = next(item for item in receipt["outputs"] if item["path"].endswith("findings.json"))
            row["bytes"], row["sha256"] = len(raw), hashlib.sha256(raw).hexdigest()
            dump(right / "publication.json", receipt)
            output = root / "must-not-exist.json"
            result = self.invoke(root, left, right, output)
            self.assertEqual(result.returncode, 1)
            self.assertIn("pinned predecessor validator", result.stderr)
            self.assertFalse(output.exists())

    def test_non_object_findings_json_is_rejected_without_publication(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            left, right = self.pair(root)
            findings_path = right / "findings.json"
            findings_path.write_text("[]\n", encoding="utf-8")
            receipt = read_json(right / "publication.json")
            raw = findings_path.read_bytes()
            row = next(item for item in receipt["outputs"] if item["path"].endswith("findings.json"))
            row["bytes"], row["sha256"] = len(raw), hashlib.sha256(raw).hexdigest()
            dump(right / "publication.json", receipt)
            output = root / "must-not-exist.json"
            result = self.invoke(root, left, right, output)
            self.assertEqual(result.returncode, 1)
            self.assertIn("JSON root must be an object", result.stderr)
            self.assertFalse(output.exists())

    def test_distinct_recomputed_results_report_disagreement_without_success(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            changed = copy.deepcopy(self.run6)
            changed["limitations"] = list(changed["limitations"]) + ["synthetic distinct-result control"]
            left, right = self.pair(root, changed, recompute=True)
            output = root / "must-not-be-passed.json"
            result = self.invoke(root, left, right, output)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)["outcome"], "disagreed")
            self.assertFalse(output.exists())

    def test_existing_destination_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            left, right = self.pair(root)
            output = root / "sentinel.json"
            sentinel = b"preserve preexisting bytes\n"
            output.write_bytes(sentinel)
            result = self.invoke(root, left, right, output)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(output.read_bytes(), sentinel)


if __name__ == "__main__":
    unittest.main()
