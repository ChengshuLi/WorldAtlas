#!/usr/bin/env python3
"""Compare a fresh bounded native extraction and remove its scratch copy."""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
CAMPAIGN = ROOT / "research/geography/alaska-thirteen-geometry-measurement-20261008"


def sha(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    scratch = CAMPAIGN / ".scratch/native-selected-replay"
    original = CAMPAIGN / "sources/native-selected"
    first = json.loads((original / "receipt.json").read_text())
    second = json.loads((scratch / "receipt.json").read_text())
    first_path, second_path = original / "records.bin", scratch / "records.bin"
    if first["status"] != "bytes-verified" or second["status"] != "bytes-verified":
        raise RuntimeError("both native extraction runs must pass full-member verification")
    if first["whole_native_member"] != second["whole_native_member"]:
        raise RuntimeError("the two runs authenticated different complete native members")
    if first["selected_output"]["bytes"] != second["selected_output"]["bytes"]:
        raise RuntimeError("selected extraction output sizes differ")
    first_hash, second_hash = sha(first_path), sha(second_path)
    if first_hash != first["selected_output"]["sha256"] or second_hash != second["selected_output"]["sha256"]:
        raise RuntimeError("selected output differs from its own whole-file receipt")
    if first_hash != second_hash or first_path.read_bytes() != second_path.read_bytes():
        raise RuntimeError("fresh-destination selected native extraction is not byte-identical")
    if first["selected_output"]["records"] != second["selected_output"]["records"]:
        raise RuntimeError("per-record offsets, native flags or digests differ")
    second_receipt = dict(second)
    second_receipt["replay_policy"] = "fresh output under owned .scratch; byte-compared to run one; binary removed after comparison"
    execution = CAMPAIGN / "execution"
    execution.mkdir(parents=True, exist_ok=True)
    run_two_path = execution / "native-extraction-run-two.json"
    comparison_path = execution / "native-extraction-reproducibility.json"
    if run_two_path.exists() or comparison_path.exists():
        raise RuntimeError("refusing to overwrite native extraction reproducibility evidence")
    run_two_path.write_text(json.dumps(second_receipt, indent=2) + "\n")
    comparison = {
        "version": 1,
        "status": "byte-identical",
        "whole_native_member_sha256": first["whole_native_member"]["sha256"],
        "whole_native_member_bytes": first["whole_native_member"]["bytes"],
        "records_authenticated_per_run": first["whole_native_member"]["records_authenticated"],
        "selected_record_count": len(first["selected_output"]["records"]),
        "run_one": {"path": first["selected_output"]["path"],
                    "bytes": first["selected_output"]["bytes"], "sha256": first_hash},
        "run_two": {"receipt_path": run_two_path.relative_to(ROOT).as_posix(),
                    "original_scratch_path": second["selected_output"]["path"],
                    "bytes": second["selected_output"]["bytes"], "sha256": second_hash,
                    "fresh_destination": True, "whole_file_verified": True},
        "scratch_cleanup": {"path": scratch.relative_to(ROOT).as_posix(),
                            "bytes_removed": sum(p.stat().st_size for p in scratch.rglob("*") if p.is_file()),
                            "removed_after_byte_equality": True},
    }
    shutil.rmtree(scratch)
    comparison_path.write_text(json.dumps(comparison, indent=2) + "\n")
    print(json.dumps({"status": comparison["status"], "records": comparison["selected_record_count"],
                      "bytes": comparison["run_one"]["bytes"], "sha256": first_hash,
                      "scratch_removed_bytes": comparison["scratch_cleanup"]["bytes_removed"]}))


if __name__ == "__main__":
    main()
