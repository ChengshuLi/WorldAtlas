#!/usr/bin/env python3
"""Run every deterministic producer for the pinned Portugal–Spain scope."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "research/geography/portugal-spain-gap-source-families-20261007"
SCRIPTS = PACKAGE / "scripts"
OUTPUTS = PACKAGE / "outputs"
RUNS = PACKAGE / "runs"
PRODUCERS = [
    "extract-jrc-scope.py",
    "inventory-jrc-2024.py",
    "summarize-jrc-2024.py",
    "compare-admin-source-products.py",
    "overlay-apa-wfd-lines.py",
    "overlay-mapa-current-snapshot.py",
    "assemble-source-status.py",
    "validate-source-controls.py",
]


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id", choices=("run-1", "run-2", "run-3", "run-4", "run-5", "run-6", "run-7", "run-8"))
    args = parser.parse_args()
    destination = RUNS / args.run_id
    if destination.exists():
        raise SystemExit(f"refusing to overwrite preserved run: {destination}")
    for name in PRODUCERS:
        subprocess.run([sys.executable, str(SCRIPTS / name)], cwd=ROOT, check=True)
    destination.mkdir(parents=True)
    for path in sorted(OUTPUTS.iterdir()):
        if path.is_file():
            shutil.copyfile(path, destination / path.name)
    manifest = {
        "schema": "worldatlas-complete-source-run-v1",
        "run_id": args.run_id,
        "captured_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "python": sys.version,
        "platform": sys.platform,
        "outputs": [
            {"path": path.name, "bytes": path.stat().st_size, "sha256": sha(path)}
            for path in sorted(destination.iterdir()) if path.is_file()
        ],
        "limits": [
            "This run reproduces bounded source diagnostics for the exact pinned 52-family/70-component scope.",
            "Reproduction does not resolve source gaps, water/ice classification, ownership, historical status, cause, or boundary edits.",
        ],
    }
    (destination / "run-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"run_id": args.run_id, "output_count": len(manifest["outputs"]), "run_manifest_sha256": sha(destination / "run-manifest.json")}))


if __name__ == "__main__":
    main()
