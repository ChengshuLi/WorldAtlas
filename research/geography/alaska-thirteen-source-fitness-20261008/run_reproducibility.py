#!/usr/bin/env python3
"""Run the pinned evidence producer twice and retain both execution receipts."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[2]
BUILDER = PACKET / "build_evidence.py"
PYTHON = sys.executable
BASELINE = "6c0ea95b7a8214ac1548161368bd952af136b5c2"

def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()

def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()

def run(output: Path, run_number: int) -> dict:
    started = utcnow()
    subprocess.run([PYTHON, str(BUILDER), str(output)], cwd=ROOT, check=True)
    finished = utcnow()
    receipt_path = output / "build-receipt.json"
    receipt_raw = receipt_path.read_bytes()
    receipt = json.loads(receipt_raw)
    entries = []
    output_prefix = output.relative_to(PACKET)
    for item in receipt["outputs"]:
        rel = Path(item["path"]).relative_to(output_prefix).as_posix()
        raw = (output / rel).read_bytes()
        if len(raw) != item["bytes"] or digest(raw) != item["sha256"]:
            raise ValueError(f"builder output receipt mismatch in run {run_number}: {rel}")
        entries.append({"path": rel, "bytes": len(raw), "sha256": digest(raw)})
    entries.sort(key=lambda row: row["path"])
    return {
        "run_number": run_number,
        "started_at_utc": started,
        "finished_at_utc": finished,
        "baseline_commit": BASELINE,
        "builder_sha256": digest(BUILDER.read_bytes()),
        "input_receipts_sha256": digest((output / "input-receipts.json").read_bytes()),
        "output_inventory_sha256": digest(canonical(entries)),
        "output_count": len(entries),
        "output_bytes": sum(row["bytes"] for row in entries),
    }

def main() -> None:
    final = PACKET / "sources"
    run_one_dir = PACKET / "reproducibility-run-one"
    if any(os.path.lexists(path) for path in (final, run_one_dir)):
        raise ValueError("preserve existing vintages; sources/ and reproducibility-run-one/ must be absent")
    one = run(run_one_dir, 1)
    two = run(final, 2)
    if one["builder_sha256"] != two["builder_sha256"]:
        raise ValueError("two producer runs executed different builder bytes")
    if one["output_inventory_sha256"] != two["output_inventory_sha256"]:
        raise ValueError("two real producer runs generated different output inventories")
    if one["input_receipts_sha256"] != two["input_receipts_sha256"]:
        raise ValueError("two producer runs consumed different pinned inputs")
    if not (one["finished_at_utc"] < two["started_at_utc"] and one["run_number"] == 1 and two["run_number"] == 2):
        raise ValueError("two distinct sequential producer executions were not recorded")
    (final / "reproducibility-run-one.json").write_text(json.dumps(one, sort_keys=True, indent=2) + "\n")
    (final / "reproducibility-run-two.json").write_text(json.dumps(two, sort_keys=True, indent=2) + "\n")
    control = {
        "method_id": "packet-generator",
        "kind": "reproducibility",
        "outcome": "passed",
        "run_one_sha256": one["output_inventory_sha256"],
        "run_two_sha256": two["output_inventory_sha256"],
        "run_one_receipt_sha256": digest((final / "reproducibility-run-one.json").read_bytes()),
        "run_two_receipt_sha256": digest((final / "reproducibility-run-two.json").read_bytes()),
    }
    (final / "control-reproducibility.json").write_text(json.dumps(control, sort_keys=True, indent=2) + "\n")
    receipt_path = final / "build-receipt.json"
    receipt = json.loads(receipt_path.read_text())
    for name in ("reproducibility-run-one.json", "reproducibility-run-two.json", "control-reproducibility.json"):
        raw = (final / name).read_bytes()
        receipt["outputs"].append({"path": f"sources/{name}", "bytes": len(raw), "sha256": digest(raw), "readback_sha256": digest((final / name).read_bytes())})
    receipt["outputs"].sort(key=lambda row: row["path"])
    receipt["output_total_bytes"] = sum(row["bytes"] for row in receipt["outputs"])
    if receipt["output_total_bytes"] > 32 * 1024 * 1024:
        raise ValueError("combined source and reproducibility receipts exceed output budget")
    receipt_path.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    # The successful first run is independently bound by its input digest,
    # output inventory digest and timestamps above; discard only those verified
    # regenerable run-one copies after the durable receipts are written.
    shutil.rmtree(run_one_dir)
    print(json.dumps({"run_one": one, "run_two": two, "equal_output_inventory": True}, indent=2))

if __name__ == "__main__":
    main()
