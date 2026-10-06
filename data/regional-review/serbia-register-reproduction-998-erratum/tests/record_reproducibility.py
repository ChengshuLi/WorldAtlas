#!/usr/bin/env python3
"""Produce two fresh runs and an exclusive deterministic-comparison receipt."""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
import re
import sys

PACKET = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("guarded_reproduce", PACKET / "guarded_reproduce.py")
guard = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = guard
spec.loader.exec_module(guard)

parser = argparse.ArgumentParser()
parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
args = parser.parse_args()
if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,39}", args.run_id):
    raise SystemExit("--run-id must be a short lowercase letters/numbers/hyphens identifier")
first_path, second_path = f"results/run-{args.run_id}-a", f"results/run-{args.run_id}-b"
source_receipt_path = PACKET / "controls" / f"guard-controls-{args.run_id}.json"
if not source_receipt_path.is_file() or source_receipt_path.is_symlink():
    raise SystemExit(f"run source controls first with --run-id {args.run_id}")
receipt_path = PACKET / "controls" / f"reproducibility-{args.run_id}.json"
with contextlib.redirect_stdout(io.StringIO()):
    first = guard.run_reproduction(first_path)
    second = guard.run_reproduction(second_path)
if first["files"] != second["files"]:
    raise SystemExit("fresh run output inventories or whole-file bytes differ")
run_one_sha = hashlib.sha256(json.dumps(first["files"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
run_two_sha = hashlib.sha256(json.dumps(second["files"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
if run_one_sha != run_two_sha:
    raise SystemExit("canonical full-run results differ")
pins = guard.load_pins(guard.PIN_FILE.read_bytes())
historical = guard.historical_output_map(pins)
exact = [row["path"] for row in first["files"] if row["path"] != "reproduction-summary.json"
         and row["sha256"] == historical[row["path"]]["sha256"]]
summary = next(row for row in first["files"] if row["path"] == "reproduction-summary.json")
result = {
    "method_id": "serbia-guarded-two-run-reproduction-v1",
    "kind": "reproducibility",
    "outcome": "passed",
    "run_one_sha256": run_one_sha,
    "run_two_sha256": run_two_sha,
    "run_one_path": first_path,
    "run_two_path": second_path,
    "files_per_run": len(first["files"]),
    "historical_exact_file_matches": len(exact),
    "historical_exact_files": sorted(exact),
    "summary_runtime_only_difference": {
        "path": "reproduction-summary.json",
        "sha256": summary["sha256"],
        "runtime": guard.check_runtime(),
        "comparison": "All findings equal after excluding only historical/current Python and pandas version fields.",
    },
    "run_one_files": first["files"],
    "run_two_files": second["files"],
}
receipt_path.parent.mkdir(parents=True, exist_ok=True)
with receipt_path.open("x", encoding="utf-8") as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write("\n")
guard_controls = json.loads(source_receipt_path.read_text())
generator_controls = {
    "method_id": "serbia-guarded-two-run-reproduction-v1",
    "kind": "generator",
    "outcome": "passed",
    "run_one_sha256": run_one_sha,
    "run_two_sha256": run_two_sha,
    "positive_control": {"paths": [first_path, second_path], "files_per_run": len(first["files"]),
                         "historical_exact_file_matches": len(exact)},
    "negative_controls": guard_controls["controls"],
    "source_control_receipt_sha256": hashlib.sha256(source_receipt_path.read_bytes()).hexdigest(),
}
generator_path = PACKET / "controls" / f"generator-controls-{args.run_id}.json"
with generator_path.open("x", encoding="utf-8") as stream:
    json.dump(generator_controls, stream, ensure_ascii=False, indent=2)
    stream.write("\n")
print(json.dumps({"outcome": "passed", "run_one_sha256": run_one_sha,
                  "run_two_sha256": run_two_sha, "files_per_run": len(first["files"]),
                  "historical_exact_file_matches": len(exact),
                  "receipt": str(receipt_path)}, indent=2))
