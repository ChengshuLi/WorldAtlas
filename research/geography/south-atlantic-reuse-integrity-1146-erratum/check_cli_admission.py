#!/usr/bin/env python3
"""Exercise the real CLI's rejected-destination paths in disposable trees."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


PACKET = Path(__file__).resolve().parent
CLI = PACKET / "reproduce_integrity.py"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(script: Path, run_name: str, receipt: str | None = None) -> subprocess.CompletedProcess:
    args = [sys.executable, str(script), run_name]
    if receipt is not None:
        args.append(receipt)
    return subprocess.run(args, capture_output=True, text=True, timeout=10)


def main() -> None:
    results = {}
    with tempfile.TemporaryDirectory(prefix="worldatlas-1369-cli-admission-") as temp:
        root = Path(temp)
        packet = root / "research/geography/packet"
        (packet / "runs").mkdir(parents=True)
        script = packet / "reproduce_integrity.py"
        shutil.copyfile(CLI, script)

        existing = packet / "runs/existing"
        existing.mkdir()
        sentinel = existing / "sentinel.txt"
        sentinel.write_text("preserve-existing-output\n")
        before = digest(sentinel)
        rejected = run(script, "existing")
        results["existing_output"] = {
            "rejected": rejected.returncode != 0,
            "sentinel_unchanged": digest(sentinel) == before,
            "no_success_receipt": not (existing / "receipt.json").exists(),
        }

        dangling = packet / "runs/dangling"
        dangling.symlink_to(root / "missing-target")
        rejected = run(script, "dangling")
        results["dangling_symlink"] = {
            "rejected": rejected.returncode != 0,
            "symlink_preserved": dangling.is_symlink(),
            "target_not_created": not (root / "missing-target").exists(),
        }

        rejected = run(script, "invalid-receipt", "../receipt.json")
        results["invalid_receipt"] = {
            "rejected": rejected.returncode != 0,
            "output_not_created": not (packet / "runs/invalid-receipt").exists(),
            "no_success_receipt": not (packet / "runs/receipt.json").exists(),
        }
        rejected = run(script, "invalid-extension", "receipt.txt")
        results["invalid_extension"] = {
            "rejected": rejected.returncode != 0,
            "output_not_created": not (packet / "runs/invalid-extension").exists(),
        }
        for case in results.values():
            if not all(case.values()):
                raise SystemExit("CLI destination admission control failed")

    print(json.dumps({"version": 1, "issue": 1369, "method_id": "exact-source-crosswalk-integrity",
                      "kind": "negative-control", "outcome": "passed", "controls": results},
                     sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
