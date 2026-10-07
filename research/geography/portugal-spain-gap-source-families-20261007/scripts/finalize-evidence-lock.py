#!/usr/bin/env python3
"""Compare preserved complete runs and freeze source/input/code byte inventory."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "research/geography/portugal-spain-gap-source-families-20261007"
MAX_FILE = 32 * 1024 * 1024
MAX_TOTAL = 256 * 1024 * 1024
PRODUCERS = [
    "extract-jrc-scope.py", "inventory-jrc-2024.py", "summarize-jrc-2024.py",
    "compare-admin-source-products.py", "overlay-apa-wfd-lines.py",
    "overlay-mapa-current-snapshot.py", "assemble-source-status.py",
    "validate-source-controls.py",
]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def inventory(*directories: Path) -> list[dict[str, object]]:
    lock_path = PACKAGE / "inputs/frozen-input-code-manifest.json"
    files = sorted(path for directory in directories for path in directory.rglob("*")
                   if path.is_file() and path != lock_path)
    rows = []
    for path in files:
        size = path.stat().st_size
        if size > MAX_FILE:
            raise SystemExit(f"ordinary file exceeds 32 MiB: {path.relative_to(ROOT)} ({size})")
        rows.append({"path": str(path.relative_to(ROOT)), "bytes": size, "sha256": sha(path)})
    total = sum(int(row["bytes"]) for row in rows)
    if total > MAX_TOTAL:
        raise SystemExit(f"source/input/code closure exceeds 256 MiB: {total}")
    return rows


def main() -> None:
    runs = PACKAGE / "runs"
    run_ids = ("run-9", "run-10")
    first = json.loads((runs / f"{run_ids[0]}/run-manifest.json").read_text())
    second = json.loads((runs / f"{run_ids[1]}/run-manifest.json").read_text())
    left = {row["path"]: row for row in first["outputs"]}
    right = {row["path"]: row for row in second["outputs"]}
    if left != right:
        raise SystemExit("complete-scope run outputs differ")
    reproducibility = {
        "schema": "worldatlas-source-run-reproducibility-v1",
        "scope": {"families": 52, "components": 70, "contacts": 57},
        "run_ids": list(run_ids),
        "output_count": len(left),
        "identical_output_sha256": True,
        "outputs": list(left.values()),
        "run_manifests": {
            name: {"path": f"research/geography/portugal-spain-gap-source-families-20261007/runs/{name}/run-manifest.json",
                  "sha256": sha(runs / name / "run-manifest.json")}
            for name in run_ids
        },
        "limits": [
            "Capture timestamps differ by design; every complete analysis output file has an identical whole-file hash across both runs.",
            "Determinism confirms computational reproducibility only and does not resolve source availability, licensing, historical coverage, or classification.",
        ],
    }
    out = PACKAGE / "outputs/reproducibility.json"
    out.write_text(json.dumps(reproducibility, indent=2, sort_keys=True) + "\n")
    index = json.loads((PACKAGE / "inputs/complete-input-index.json").read_text())
    descriptors = index["ordinary_git_descriptors"]
    desc_bytes = sum(int(row["bytes"]) for row in descriptors)
    closure = inventory(PACKAGE / "inputs", PACKAGE / "sources", PACKAGE / "scripts")
    closure_bytes = sum(int(row["bytes"]) for row in closure)
    combined_bytes = desc_bytes + closure_bytes
    if combined_bytes > MAX_TOTAL:
        raise SystemExit(f"pinned scope descriptors plus local source/code closure exceed 256 MiB: {combined_bytes}")
    lock = {
        "schema": "worldatlas-source-input-code-lock-v1",
        "scope": index["scope"],
        "source_index_descriptor_count": len(descriptors),
        "source_index_declared_bytes": desc_bytes,
        "package_file_count": len(closure),
        "package_declared_bytes": closure_bytes,
        "scope_descriptors_plus_package_bytes": combined_bytes,
        "caps": {"maximum_file_bytes": MAX_FILE, "maximum_inventory_bytes": MAX_TOTAL},
        "all_files_within_caps": True,
        "scope_and_package_within_aggregate_cap": True,
        "files": closure,
        "baseline_scope_descriptors": descriptors,
        "selected_source_product_descriptors": index["source_product_payload_descriptors"],
        "source_registry_descriptor": index["source_registry_descriptor"],
        "explicit_missing_originals": index["explicit_missing_originals"],
        "limits": [
            "The source index descriptors identify exact original Git blobs and original source product shards; the local closure inventories the retained capture bytes and analysis code.",
            "Non-retained historical MAPA originals remain missing; the current MAPA service snapshot does not replace them.",
            "APA reuse terms and current MAPA geometry terms remain unresolved; MITECO vectors were not acquired.",
        ],
    }
    lock_path = PACKAGE / "inputs/frozen-input-code-manifest.json"
    lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")
    producer_paths = [f"research/geography/portugal-spain-gap-source-families-20261007/scripts/{name}"
                      for name in ["run-complete-analysis.py", *PRODUCERS]]
    producer_rows = [next(row for row in closure if row["path"] == path) for path in producer_paths]
    reproducibility["frozen_input_code_manifest"] = {
        "path": str(lock_path.relative_to(ROOT)), "sha256": sha(lock_path),
        "producer_code_paths": producer_paths,
        "producer_code_sha256": hashlib.sha256(json.dumps(producer_rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "binding_timing": "Computed after both runs from the exact preserved input and producer bytes; the producer and source-input bytes listed here are the bytes used by both runs.",
    }
    reproducibility_path = PACKAGE / "outputs/reproducibility.json"
    reproducibility_path.write_text(json.dumps(reproducibility, indent=2, sort_keys=True) + "\n")
    binding = {
        "schema": "worldatlas-source-execution-binding-v1",
        "frozen_input_code_manifest": reproducibility["frozen_input_code_manifest"],
        "runs": reproducibility["run_manifests"],
        "output_count": len(left),
        "all_run_outputs_identical": True,
        "output_sha256": list(left.values()),
        "limits": reproducibility["limits"],
    }
    binding_path = PACKAGE / "outputs/execution-code-input-binding.json"
    binding_path.write_text(json.dumps(binding, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"runs_equal": True, "run_output_count": len(left), "source_index_bytes": desc_bytes,
                      "local_closure_bytes": lock["package_declared_bytes"], "closure_files": len(closure),
                      "max_file_bytes": max(int(row["bytes"]) for row in closure),
                      "combined_bytes": combined_bytes, "reproducibility_sha256": sha(reproducibility_path),
                      "execution_binding_sha256": sha(binding_path), "lock_sha256": sha(lock_path),
                      "producer_code_sha256": reproducibility["frozen_input_code_manifest"]["producer_code_sha256"]}))


if __name__ == "__main__":
    main()
