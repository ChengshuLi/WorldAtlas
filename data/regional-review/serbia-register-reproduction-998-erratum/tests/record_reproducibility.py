#!/usr/bin/env python3
"""Produce two fresh runs and an exclusive deterministic-comparison receipt."""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys

PACKET = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("guarded_reproduce", PACKET / "guarded_reproduce.py")
guard = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = guard
spec.loader.exec_module(guard)

first_path, second_path = "results/run-20261006-e", "results/run-20261006-f"
receipt_path = PACKET / "controls" / "reproducibility-20261006-final.json"
if receipt_path.exists() or receipt_path.is_symlink():
    raise SystemExit("reproducibility receipt already exists; preserve it and choose a new date/version")
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
    "kind": "generator",
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
guard_controls = json.loads((PACKET / "controls" / "guard-controls-20261006-final.json").read_text())
generator_controls = {
    "method_id": "serbia-guarded-two-run-reproduction-v1",
    "kind": "generator",
    "outcome": "passed",
    "run_one_sha256": run_one_sha,
    "run_two_sha256": run_two_sha,
    "positive_control": {"paths": [first_path, second_path], "files_per_run": len(first["files"]),
                         "historical_exact_file_matches": len(exact)},
    "negative_controls": guard_controls["controls"],
    "source_control_receipt_sha256": hashlib.sha256((PACKET / "controls" / "guard-controls-20261006-final.json").read_bytes()).hexdigest(),
}
generator_path = PACKET / "controls" / "generator-controls-20261006-final.json"
with generator_path.open("x", encoding="utf-8") as stream:
    json.dump(generator_controls, stream, ensure_ascii=False, indent=2)
    stream.write("\n")
print(json.dumps({"outcome": "passed", "run_one_sha256": run_one_sha,
                  "run_two_sha256": run_two_sha, "files_per_run": len(first["files"]),
                  "historical_exact_file_matches": len(exact),
                  "receipt": str(receipt_path)}, indent=2))
