#!/usr/bin/env python3
"""Run the retained Artigas representation check into a fresh, owned directory."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
PREFIX = "data/regional-review/uruguay-artigas-contested-guard-erratum"
CODE = HERE / "inputs/code"
BASELINE = HERE / "inputs/baseline"
SOURCES = HERE / "inputs/sources"
PINNED = {
    "inputs/code/original-reproduce.py": "c6abb1d4b2ba662d2b7318db55d4fb9943945257a754ee8e42ff17d4ac0d79f8",
    "inputs/original-source-inventory.json": "83c6a22703baedab022144d3284e4b6434043c91e04dccd1573c02473c576675",
    "inputs/baseline/data-world-index.json": "a62d4a74f0f969e228dfcdeb2797bb689ce9836c2498cadd31ed622ad2c38c03",
    "inputs/baseline/data-hierarchy.json": "568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b",
    "inputs/baseline/data-administrative-sources.json": "ed0051d2956271c72f8917e7da0c6f53e5dfb595bee5920cac489a65a747d633",
    "inputs/baseline/data-macro-publication-v5.json": "aae3967fde4f5bf92b3cb0b42c490c6c6a5921c7421dcdc9533f242afbd6a674",
    "inputs/baseline/data-geography-part-25.json": "dada55df1b7f0f2a2b307f4aea071d0e48791e3105875755fe74a292a6763394",
    "inputs/sources/ury-gb-2017.geojson": "9f4887205e7b359af2ef1e4f484ad071d2dc0d12d068f1d7b6c1cc6c2624d1cf",
    "inputs/sources/ury-igm-current.geojson": "3cfa19c6be9d12bd159b236e15839f958656fdbe66ef19e38379cb54c141b3a7",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_capsule():
    manifest = json.loads((HERE / "evidence-quality.json").read_text())
    expected = manifest["capsule"]
    for rel, sha256 in expected.items():
        path = HERE / rel
        if not path.is_file() or path.is_symlink() or digest(path) != sha256:
            raise ValueError("capsule hash mismatch: " + rel)
    for rel, sha256 in PINNED.items():
        path = HERE / rel
        if not path.is_file() or digest(path) != sha256:
            raise ValueError("input pin mismatch: " + rel)
    if json.loads((BASELINE / "data-geography-part-25.json").read_text())["features"] is None:
        raise ValueError("subject input malformed")


def fresh_destination(raw):
    # Require a lexical path below the owned packet, and an already-existing
    # non-symlink parent. Only the final directory may be created by this run.
    requested = Path(raw)
    if not requested.is_absolute():
        requested = Path.cwd() / requested
    root = HERE.resolve()
    lexical = Path(os.path.abspath(str(requested)))
    try:
        rel = lexical.relative_to(root)
    except ValueError:
        raise ValueError("output must be inside the owned packet")
    if len(rel.parts) != 2 or rel.parts[0] != "outputs" or rel.parts[1] in ("", ".", ".."):
        raise ValueError("output must be a direct child of owned outputs/")
    parent = root / "outputs"
    if parent.is_symlink() or not parent.is_dir() or parent.resolve() != parent:
        raise ValueError("unsafe output parent")
    dest = parent / rel.parts[1]
    if dest.exists() or dest.is_symlink():
        raise FileExistsError("output already exists")
    # mkdir is the exclusive reservation: it fails if another process wins.
    dest.mkdir()
    if dest.resolve() != dest:
        dest.rmdir()
        raise ValueError("output destination changed")
    return dest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, help="fresh outputs/<name> directory")
    args = parser.parse_args()
    validate_capsule()
    dest = fresh_destination(args.output)
    try:
        command = [sys.executable, str(CODE / "capsule-reproduce.py"), str(dest)]
        completed = subprocess.run(command, check=True, text=True, capture_output=True)
        report = dest / "reproduction-results.json"
        if not report.is_file() or report.is_symlink():
            raise ValueError("reproduction did not create its report")
        original = HERE / "inputs/original-reproduction-results.json"
        if report.read_bytes() != original.read_bytes():
            raise ValueError("reproduced report differs from retained original")
        print(completed.stdout.strip())
        print(json.dumps({"output": str(report.relative_to(HERE)), "sha256": digest(report)}, sort_keys=True))
    except Exception:
        shutil.rmtree(dest, ignore_errors=True)
        raise


if __name__ == "__main__":
    main()
