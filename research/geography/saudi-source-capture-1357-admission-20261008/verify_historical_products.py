#!/usr/bin/env python3
"""Verify the two retained fourteen-product Saudi runs by whole-file bytes."""
from __future__ import annotations

import json
import argparse
from pathlib import Path

import admission
import run_safe


def verify(repo_root: Path) -> dict:
    packet = repo_root / run_safe.PREDECESSOR
    expected, receipts = run_safe._receipt_inventory(packet)
    runs = []
    for run_id in ("run-1", "run-2"):
        value = json.loads(admission.read_regular(packet / "runs" / f"{run_id}-execution.json"))
        actual = {}
        for entry in value["outputs"]:
            raw = admission.read_regular(packet / entry["path"])
            if len(raw) != entry["bytes"] or admission.sha256(raw) != entry["sha256"]:
                raise admission.AdmissionError(f"Actual historical product mismatch: {entry['path']}")
            name = entry["path"].rsplit("/", 1)[-1]
            actual[name] = {"bytes": len(raw), "sha256": admission.sha256(raw)}
        if actual != expected:
            raise admission.AdmissionError(f"Actual {run_id} product inventory differs from its full receipt")
        runs.append({"run_id": run_id, "products": len(actual),
                     "bytes": sum(row["bytes"] for row in actual.values()),
                     "products_sha256": admission.sha256(json.dumps(actual, sort_keys=True, separators=(",", ":")).encode())})
    if runs[0]["products_sha256"] != runs[1]["products_sha256"]:
        raise admission.AdmissionError("Retained full product inventories differ")
    return {
        "version": 1,
        "status": "verified-preserved-products",
        "runs": runs,
        "product_count_per_run": len(expected),
        "bytes_per_run": sum(row["bytes"] for row in expected.values()),
        "historical_receipts": receipts,
        "source_replay_performed": False,
        "geographic_or_source_approval": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=str(run_safe.REPO_ROOT))
    parser.add_argument("--output")
    args = parser.parse_args()
    root = Path(args.repo).resolve(strict=True)
    result = verify(root)
    if args.output:
        admission.write_exclusive_json(root, args.output, result)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
