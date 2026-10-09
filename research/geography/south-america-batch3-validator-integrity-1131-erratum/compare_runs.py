#!/usr/bin/env python3
"""Run the unchanged validator twice and publish only a byte-matched pair."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone

from reproduce import OUTPUTS, ROOT, OWNED, Invalid, canonical, sha, validate_runtime


def pair_root(pair_id: str) -> Path:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", pair_id):
        raise Invalid("pair ID must be a safe lowercase slug")
    parent = ROOT / OWNED / "pairs"
    target = parent / pair_id
    for path in (target, *target.parents):
        if path == ROOT:
            break
        if path.is_symlink():
            raise Invalid("symlink in pair output path")
    base = parent.resolve()
    if target.resolve(strict=False).parent != base or os.path.lexists(target):
        raise FileExistsError("pair destination exists or escapes the owned namespace")
    return target


def execute(pair_id: str) -> dict:
    validate_runtime()
    destination = pair_root(pair_id)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination = pair_root(pair_id)
    destination.mkdir(exist_ok=False)
    first_id, second_id = f"{pair_id}-run-one", f"{pair_id}-run-two"
    script = ROOT / OWNED / "reproduce.py"
    python = sys.executable
    runs = []
    for run_id in (first_id, second_id):
        completed = subprocess.run([python, str(script), "--run-id", run_id], cwd=ROOT,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if completed.returncode:
            raise Invalid(f"{run_id} failed ({completed.returncode}): {completed.stderr.strip()}")
        try:
            runs.append(json.loads(completed.stdout.strip().splitlines()[-1]))
        except (json.JSONDecodeError, IndexError) as exc:
            raise Invalid(f"{run_id} returned no parseable publication receipt") from exc
    left_root, right_root = destination.parent.parent / "runs" / first_id, destination.parent.parent / "runs" / second_id
    left = {name: (left_root / name).read_bytes() for name in OUTPUTS}
    right = {name: (right_root / name).read_bytes() for name in OUTPUTS}
    if left != right:
        raise Invalid("independently executed full seven-product output sets differ")
    # The original seventh product falsely labels a single invocation as a pair.
    # Bind both original copies for the audit, but replace that claim in the
    # published pair with this receipt computed only after exact set equality.
    products = {name: raw for name, raw in left.items() if name != "reproducibility.json"}
    pair_receipt = {
        "version": 1,
        "method_id": "batch3-provenance-crossfield-validator",
        "kind": "reproducibility",
        "outcome": "passed",
        "comparison": "all seven original entry-point product files compared byte-for-byte",
        "run_one": {"id": runs[0]["run_id"], "execution_id": runs[0]["execution_id"],
                    "python_version": runs[0]["python_version"], "shapely_version": runs[0]["shapely_version"], "geos_version": runs[0]["geos_version"],
                    "wrapper_sha256": runs[0]["wrapper_sha256"], "shared_helper_sha256": runs[0]["shared_helper_sha256"],
                    "outputs": runs[0]["outputs"]},
        "run_two": {"id": runs[1]["run_id"], "execution_id": runs[1]["execution_id"],
                    "python_version": runs[1]["python_version"], "shapely_version": runs[1]["shapely_version"], "geos_version": runs[1]["geos_version"],
                    "wrapper_sha256": runs[1]["wrapper_sha256"], "shared_helper_sha256": runs[1]["shared_helper_sha256"],
                    "outputs": runs[1]["outputs"]},
        "pair_runner": str(OWNED / "compare_runs.py"),
        "pair_runner_sha256": sha(Path(__file__).read_bytes()),
        "run_wrapper_sha256": runs[0]["wrapper_sha256"],
        "shared_helper_sha256": runs[0]["shared_helper_sha256"],
        "legacy_entry_point_sha256": runs[0]["entry_point_sha256"],
        "original_single-run_receipt_sha256": sha(left["reproducibility.json"]),
        "published_products": [{"path": name, "bytes": len(raw), "sha256": sha(raw)} for name, raw in products.items()],
        "basis": "Two separately started Python processes ran the unchanged actual entry point. All seven complete outputs, including its historical single-run reproducibility file, matched byte-for-byte; this replacement receipt is issued only after that comparison.",
        "geographic_approval": "not established",
    }
    products["reproducibility.json"] = canonical(pair_receipt)
    descriptors = []
    for name in OUTPUTS:
        raw = products[name]
        with (destination / name).open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        descriptors.append({"path": name, "bytes": len(raw), "sha256": sha(raw)})
    publication = {
        "version": 1, "status": "complete", "pair_id": pair_id,
        "pair_execution_id": str(uuid.uuid4()),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "entry_point_sha256": sha(script.read_bytes()),
        "run_ids": [first_id, second_id], "outputs": descriptors,
        "pair_runner_sha256": sha(Path(__file__).read_bytes()),
    }
    temp = destination / ".publication-incomplete"
    with temp.open("xb") as stream:
        stream.write(canonical(publication))
        stream.flush()
        os.fsync(stream.fileno())
    os.link(temp, destination / "publication.json")
    temp.unlink()
    return publication


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair-id", required=True)
    args = parser.parse_args()
    print(json.dumps(execute(args.pair_id), sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Invalid, FileExistsError) as exc:
        print(f"pair reproduction rejected: {exc}", file=sys.stderr)
        raise SystemExit(2)
