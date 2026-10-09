#!/usr/bin/env python3
"""Reproduce the archived control CLI's dangling-output behavior in a private mirror."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

REPO = Path(__file__).resolve().parents[3]
OWNED = Path(__file__).resolve().parent
SOURCE = REPO / "data/regional-review/regional-review-0968ad79c26518d2"
EXPECTED = {
    "vintages/generator-integrity-erratum/integrity_guards.py": "36358f235c6fa28e636217a3f0376f0fbca8729462f8c75d0700b4fa1784c5ef",
    "vintages/generator-integrity-erratum/validate_controls.py": "a547f321341b1a00382fa44c33c63935f7e7520066dc67948e385c1b3a322aae",
    "vintages/generator-integrity-erratum/evaluation-inputs.json": "e2f9c442883ea10768dd8ae4946061c9681cb3b9e15e4c1ff442f80c04e3a098",
}


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(tag: str) -> dict:
    fixture = OWNED / "negative-fixtures" / f"actual-controls-{tag}"
    if fixture.exists() or fixture.is_symlink():
        raise FileExistsError(f"Preserve existing fixture: {fixture}")
    for relative, expected in EXPECTED.items():
        if sha(SOURCE / relative) != expected:
            raise ValueError(f"Pinned archived input changed: {relative}")
    mirror = fixture / "repo" / "data/regional-review/regional-review-0968ad79c26518d2"
    mirror.parent.mkdir(parents=True)
    shutil.copytree(SOURCE, mirror)
    source_files = sorted(SOURCE.rglob("*"))
    file_inventory = []
    for original in source_files:
        if original.is_file() and not original.is_symlink():
            copy = mirror / original.relative_to(SOURCE)
            if sha(original) != sha(copy):
                raise ValueError(f"Mirror copy mismatch: {original.relative_to(SOURCE)}")
            file_inventory.append({"path": original.relative_to(SOURCE).as_posix(),
                                   "bytes": original.stat().st_size, "sha256": sha(original)})
    vintage = mirror / "vintages/generator-integrity-erratum"
    script = vintage / "validate_controls.py"
    guard = vintage / "integrity_guards.py"
    results = []
    created_links = []
    for label, filename in (("summary", f"erratum-summary-actual-summary-{tag}.json"),
                            ("ledger", f"correction-ledger-actual-ledger-{tag}.json")):
        run_id = f"actual-{label}-{tag}"
        link = vintage / filename
        target = fixture / "escaped-targets" / f"{label}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(target)
        created_links.append(link)
        process = subprocess.run([sys.executable, "-B", str(script), "--run-id", run_id],
                                 cwd=REPO, text=True, capture_output=True)
        results.append({"case": f"dangling-{label}", "exit_code": process.returncode,
                        "stdout": process.stdout, "stderr": process.stderr,
                        "entrypoint_sha256": sha(script), "guard_sha256": sha(guard),
                        "link_was_dangling_before": True, "link_still_symlink_after_write": link.is_symlink(),
                        "target_created": target.exists(),
                        "target_sha256": sha(target) if target.exists() else None,
                        "target_bytes": target.stat().st_size if target.exists() else None})
        if process.returncode != 0 or not target.exists():
            break
    run_id = f"actual-existing-sentinel-{tag}"
    summary = vintage / f"erratum-summary-{run_id}.json"
    sentinel = b"preserve-me-summary-sentinel\n"
    summary.write_bytes(sentinel)
    process = subprocess.run([sys.executable, "-B", str(script), "--run-id", run_id],
                             cwd=REPO, text=True, capture_output=True)
    results.append({"case": "ordinary-existing-summary", "exit_code": process.returncode,
                    "stdout": process.stdout, "stderr": process.stderr,
                    "entrypoint_sha256": sha(script),
                    "sentinel_preserved": summary.read_bytes() == sentinel,
                    "output_directory_absent": not (vintage / "controls" / f"run-{run_id}").exists()})
    proof = {"version": 1,
             "method": "Unchanged archived validate_controls.py and integrity_guards.py copied byte-for-byte with the complete retained control input tree into a private issue-owned mirror. No source, predicate, or subprocess was mocked.",
             "evaluation_commit": "cbb829672d18801e4310c30896a7ddb13a79b451",
             "input_tree_relative_to_repo": "data/regional-review/regional-review-0968ad79c26518d2",
             "input_file_count": len(file_inventory), "input_files": file_inventory,
             "results": results,
             "scope": "Output-path behavior only; no geographic or legal conclusion."}
    receipt = OWNED / "validation" / f"actual-controls-symlink-reproduction-{tag}.json"
    receipt.parent.mkdir(exist_ok=True)
    with receipt.open("xb") as stream:
        stream.write((json.dumps(proof, indent=2) + "\n").encode())
    for link in created_links:
        if link.is_symlink():
            link.unlink()
    return {"evidence_file": receipt.relative_to(REPO).as_posix(),
            "cases": len(results), "exit_codes": [item["exit_code"] for item in results]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,35}", args.tag):
        raise SystemExit("tag must be a lowercase alphanumeric/hyphen id")
    print(json.dumps(run(args.tag), sort_keys=True))


if __name__ == "__main__":
    main()
