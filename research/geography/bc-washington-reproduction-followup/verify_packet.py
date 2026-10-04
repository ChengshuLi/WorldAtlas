#!/usr/bin/env python3
"""Run positive repeatability and negative write/pin controls for this packet."""
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "reproduce.py"
OUTPUT = ROOT / "assessment.json"

def main():
    runs = [subprocess.check_output([sys.executable, str(SCRIPT)], text=True).strip() for _ in range(2)]
    receipts = [json.loads(run) for run in runs]
    if receipts[0]["sha256"] != receipts[1]["sha256"] or any(r["mode"] != "read-only-verified" for r in receipts):
        raise SystemExit("two read-only runs were not byte-identical")
    before = OUTPUT.read_bytes()
    spec = importlib.util.spec_from_file_location("bcwa_reproduce", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    path = next(iter(module.PINNED))
    size, digest = module.PINNED[path]
    module.PINNED[path] = (size, "0" * 64)
    try:
        module.verify_pins()
        raise SystemExit("negative pin control unexpectedly passed")
    except ValueError as error:
        if "baseline pin mismatch" not in str(error):
            raise
    if OUTPUT.read_bytes() != before:
        raise SystemExit("pin rejection changed stored output")
    refused = subprocess.run([sys.executable, str(SCRIPT), "--new-vintage"], capture_output=True, text=True)
    if refused.returncode == 0 or OUTPUT.read_bytes() != before:
        raise SystemExit("exclusive creation did not preserve existing assessment")
    report = {
        "positive": {"runs": 2, "identical_output_sha256": receipts[0]["sha256"], "all_rows": receipts[0]["samples"], "strict_noncontainments": receipts[0]["uncontained"]},
        "negative": {"changed_baseline_pin_rejected_before_output_change": True, "existing_vintage_exclusive_create_refused_without_change": True},
        "original_packet": "not modified; input comes from immutable Git baseline blobs",
    }
    (ROOT / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    method_id = "inherited-sample-ledger-audit"
    controls = {
        "positive-control.json": {"method_id": method_id, "kind": "positive-control", "outcome": "passed", "sample_count": receipts[0]["samples"], "strict_noncontainment_count": receipts[0]["uncontained"], "output_sha256": receipts[0]["sha256"]},
        "negative-control.json": {"method_id": method_id, "kind": "negative-control", "outcome": "passed", "changed_baseline_pin_rejected_before_output_change": True, "existing_vintage_exclusive_create_refused_without_change": True},
        "reproducibility-control.json": {"method_id": method_id, "kind": "reproducibility", "outcome": "passed", "run_one_sha256": receipts[0]["sha256"], "run_two_sha256": receipts[1]["sha256"]},
    }
    validation_dir = ROOT / "validation"
    validation_dir.mkdir(exist_ok=True)
    for filename, evidence in controls.items():
        (validation_dir / filename).write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))

if __name__ == "__main__":
    main()
