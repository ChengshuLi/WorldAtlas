#!/usr/bin/env python3
"""Run the owned fail-closed controls and write one exclusive evidence receipt."""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
import re
import sys
import unittest

PACKET = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
args = parser.parse_args()
if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,39}", args.run_id):
    raise SystemExit("--run-id must be a short lowercase letters/numbers/hyphens identifier")
sys.path.insert(0, str(PACKET / "tests"))
loader = unittest.TestLoader()
suite = loader.discover(str(PACKET / "tests"), pattern="test_guarded_reproduce.py")
stream = io.StringIO()
class TrackingResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_ids = []

    def startTest(self, test):
        self.test_ids.append(test.id().rsplit(".", 1)[-1])
        super().startTest(test)

class TrackingRunner(unittest.TextTestRunner):
    resultclass = TrackingResult

result = TrackingRunner(stream=stream, verbosity=2).run(suite)
if not result.wasSuccessful():
    sys.stderr.write(stream.getvalue())
    raise SystemExit(1)

fixtures = []
for name in ("metadata-boundary-year.json", "issue-998-77-subjects.json"):
    path = PACKET / "tests" / "fixtures" / name
    raw = path.read_bytes()
    fixtures.append({"path": str(path.relative_to(PACKET)), "bytes": len(raw),
                     "sha256": hashlib.sha256(raw).hexdigest()})

descriptions = {
    "test_metadata_boundary_year_complete_file_probe_is_rejected": "A complete changed 919-byte source-metadata file is rejected before staging.",
    "test_shortened_scope_complete_file_is_rejected_before_output": "A complete captured issue with 77 of 78 IDs is rejected before output; direct scope validation also rejects it.",
    "test_wrong_baseline_bytes_are_rejected": "Changed bytes at an immutable baseline path are rejected before output.",
    "test_wrong_workbook_bytes_are_rejected": "A one-byte change to the original XLS workbook is rejected before output.",
    "test_wrong_historical_generator_bytes_are_rejected": "Changed original generator code bytes are rejected before output.",
    "test_duplicate_or_unmatched_scope_is_rejected": "Short, duplicate, and substituted IDs are rejected by the exact ordered roster validator.",
    "test_existing_output_is_preserved_and_rejected": "An existing exclusive destination is refused and its sentinel remains byte-identical.",
    "test_two_runs_are_byte_reproducible_and_match_historical_outputs": "Two private full reproductions match each other; seven products match historical bytes and summary findings match after truthful runtime fields are excluded.",
}
tests = []
for test_id in result.test_ids:
    tests.append({"id": test_id, "outcome": "passed", "expected": descriptions[test_id]})
receipt = {
    "method_id": "serbia-immutable-source-and-scope-controls-v1",
    "kind": "source",
    "outcome": "passed",
    "tests_run": result.testsRun,
    "failure_count": len(result.failures),
    "error_count": len(result.errors),
    "fixtures": fixtures,
    "controls": tests,
    "test_command": f"python3 data/regional-review/serbia-register-reproduction-998-erratum/tests/run_controls.py --run-id {args.run_id}",
}
destination = PACKET / "controls" / f"guard-controls-{args.run_id}.json"
destination.parent.mkdir(parents=True, exist_ok=True)
with destination.open("x", encoding="utf-8") as stream:
    json.dump(receipt, stream, ensure_ascii=False, indent=2)
    stream.write("\n")
print(json.dumps({"outcome": "passed", "tests_run": result.testsRun, "receipt": str(destination)}, indent=2))
