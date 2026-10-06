#!/usr/bin/env python3
"""Run the follow-up generator twice and retain the observed byte comparison."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

OWNED = Path(__file__).resolve().parent
ROOT = OWNED.parents[2]
GENERATOR = OWNED / "reproduce-followup.py"
OUTPUTS = [OWNED / "findings/followup-assessments.json", OWNED / "baseline/issue-contract.json"]

def run():
    subprocess.run([sys.executable, str(GENERATOR)], cwd=ROOT, check=True, capture_output=True, text=True)
    return hashlib.sha256(b"\0".join(p.read_bytes() for p in OUTPUTS)).hexdigest()

first = run()
second = run()
if first != second:
    raise SystemExit(f"reproduction mismatch: {first} != {second}")
result = {
    "method_id": "followup-generator",
    "kind": "reproducibility",
    "outcome": "passed",
    "run_one_sha256": first,
    "run_two_sha256": second,
}
(OWNED / "findings/reproduction-result.json").write_text(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n")
print(json.dumps(result, sort_keys=True))
