#!/usr/bin/env python3
"""Create immutable positive-control and two-run receipts for issue #1365."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
PACKET = ROOT / "data/regional-review/texas-erratum-integrity-1144-followup"
PRODUCTS = ("county-interpretation-erratum.jsonl", "reproduction-summary.json", "validation.json")
METHOD = "immutable-texas-erratum-join"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def exclusive_json(path, value):
    data = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    with path.open("xb") as stream:
        stream.write(data)


def main():
    targets = [PACKET / "positive-control-2026-10-08.json", PACKET / "reproducibility-2026-10-08.json"]
    for target in targets:
        if target.exists() or target.is_symlink():
            raise FileExistsError("receipt destination already exists: " + str(target))
        for parent in target.parents:
            if parent == ROOT.parent:
                break
            if parent.is_symlink():
                raise ValueError("symlink in receipt output path: " + str(parent))
    runs = []
    for run_name in ("2026-10-08-run-1", "2026-10-08-run-2"):
        run_dir = PACKET / "vintages" / run_name
        files = []
        digest = hashlib.sha256()
        for name in PRODUCTS:
            data = (run_dir / name).read_bytes()
            rel = (run_dir / name).relative_to(ROOT).as_posix()
            files.append({"path": rel, "bytes": len(data), "sha256": sha(data)})
            # Length-prefixed path and payload prevents ambiguous concatenations.
            path_bytes = rel.encode()
            digest.update(len(name.encode()).to_bytes(8, "big"))
            digest.update(name.encode())
            digest.update(len(data).to_bytes(8, "big"))
            digest.update(data)
        runs.append({"name": run_name, "sha256": digest.hexdigest(), "files": files})
    if [item["sha256"] for item in runs][0] != runs[1]["sha256"]:
        raise ValueError("two final producer runs differ in their ordered products")
    validation = json.loads((PACKET / "vintages/2026-10-08-run-1/validation.json").read_bytes())
    if not validation.get("output_matches_retained_original"):
        raise ValueError("producer result does not match retained originals")
    positive = {
        "version": 1, "issue": 1365, "method_id": METHOD, "kind": "positive-control", "outcome": "passed",
        "scope_count": validation["scope_count"],
        "identity_joins": validation["identity_joins"],
        "cbf_polygon_components": validation["cbf_polygon_components"],
        "output_matches_retained_original": validation["output_matches_retained_original"],
        "runtime": validation["execution"],
    }
    reproducibility = {
        "version": 1, "issue": 1365, "method_id": METHOD, "kind": "reproducibility", "outcome": "passed",
        "algorithm": "SHA-256 over the ordered products; for each product, append 8-byte big-endian UTF-8 product-name length, product-name bytes, 8-byte big-endian payload length, then exact payload bytes. Product order: erratum JSONL, reproduction summary JSON, validation JSON. Publication receipt is excluded because it contains run-specific vintage paths.",
        "run_one_sha256": runs[0]["sha256"], "run_two_sha256": runs[1]["sha256"], "runs": runs,
    }
    exclusive_json(targets[0], positive)
    try:
        exclusive_json(targets[1], reproducibility)
    except Exception:
        targets[0].unlink()
        raise
    print("positive-control and two-run reproducibility receipts recorded")


if __name__ == "__main__":
    main()
