#!/usr/bin/env python3
"""Fail-closed parser, immutable pin, subject, and exclusive-output controls."""
from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SCRIPT = pathlib.Path(__file__).with_name("build_packet.py")
SPEC = importlib.util.spec_from_file_location("bolivia_packet", SCRIPT)
bp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bp)


def rejects(label, action):
    try:
        action()
    except (ValueError, FileExistsError, KeyError, subprocess.CalledProcessError):
        return label
    raise AssertionError("Negative control unexpectedly passed: " + label)


def committed_repo(files: dict[str, bytes]) -> tuple[tempfile.TemporaryDirectory, str]:
    temp = tempfile.TemporaryDirectory(prefix="worldatlas-675-negative-")
    root = pathlib.Path(temp.name)
    for name, raw in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    def run(*args):
        subprocess.run(["git", "-C", str(root), *args], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    run("init", "-q")
    run("config", "user.name", "WorldAtlas evidence test")
    run("config", "user.email", "evidence-test@example.invalid")
    run("add", "--all")
    run("commit", "-qm", "fixture")
    commit = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    return temp, commit


def main():
    rejected = []
    fields = ["expected_km2", "current_km2"]
    valid = "OGRFeature(result):\n  expected_km2 (Real) = 12.5\n  current_km2 (Real) = 9.25\n"
    assert bp.parse_sql_output(valid, fields) == [12.5, 9.25]
    rejected.append(rejects("missing SQL result", lambda: bp.parse_sql_output("expected_km2 (Real) = 12.5\n", fields)))
    rejected.append(rejects("null metric", lambda: bp.parse_sql_output("expected_km2 (Real) = (null)\ncurrent_km2 (Real) = 2\n", fields)))
    rejected.append(rejects("malformed SQL metric", lambda: bp.parse_sql_output("expected_km2 (Real) = twelve\ncurrent_km2 (Real) = 2\n", fields)))
    rejected.append(rejects("duplicate SQL field", lambda: bp.parse_sql_output("expected_km2 (Real) = 1\nexpected_km2 (Real) = 2\ncurrent_km2 (Real) = 3\n", fields)))
    rejected.append(rejects("nonfinite SQL metric", lambda: bp.parse_sql_output("expected_km2 (Real) = nan\ncurrent_km2 (Real) = 2\n", fields)))

    manifest = json.loads(bp.MANIFEST.read_text())
    changed = json.loads(json.dumps(manifest))
    changed["baseline"]["files"][0]["sha256"] = "0" * 64
    rejected.append(rejects("changed baseline descriptor", lambda: bp.check_manifest(changed)))
    wrong_part = json.loads(json.dumps(manifest))
    wrong_part["baseline"]["subject_files"][bp.IDS[0]] = "data/geography/part-3.json"
    rejected.append(rejects("wrong actual containing part", lambda: bp.check_manifest(wrong_part)))

    duplicate_feature = {"type": "Feature", "properties": {"id": bp.IDS[0]}, "geometry": {"type": "Point", "coordinates": [0, 0]}}
    index = json.dumps({"parts": ["geography/a.json", "geography/b.json"]}).encode()
    first = json.dumps({"features": [duplicate_feature]}).encode()
    second = json.dumps({"features": [duplicate_feature]}).encode()
    temp, commit = committed_repo({
        "data/world-index.json": index,
        "data/geography/a.json": first,
        "data/geography/b.json": second,
    })
    try:
        from evidence.immutable import Baseline, descriptor
        base = Baseline(temp.name, commit, [descriptor("data/world-index.json", index)])
        rejected.append(rejects("duplicate subject in full indexed scan", lambda: base.subjects([bp.IDS[0]])))
        rejected.append(rejects("missing subject in full indexed scan", lambda: base.subjects([bp.IDS[1]])))
    finally:
        temp.cleanup()

    temp, commit = committed_repo({"data/pin.json": b"pinned"})
    try:
        from evidence.immutable import Baseline, descriptor, write_new_vintage
        base = Baseline(temp.name, commit, [descriptor("data/pin.json", b"pinned")])
        target = pathlib.Path(temp.name) / "research/geography/fixture/vintages/immutable/output.json"
        target.parent.mkdir(parents=True)
        target.write_text('{"original":true}\n')
        rejected.append(rejects("exclusive overwrite", lambda: write_new_vintage(base, "research/geography/fixture/", "immutable", "output.json", {"replace": True})))
        assert target.read_text() == '{"original":true}\n'
    finally:
        temp.cleanup()

    expected = {
        "missing SQL result", "null metric", "malformed SQL metric", "duplicate SQL field",
        "nonfinite SQL metric", "changed baseline descriptor", "wrong actual containing part",
        "duplicate subject in full indexed scan", "missing subject in full indexed scan", "exclusive overwrite",
    }
    assert set(rejected) == expected
    print(json.dumps({"result": "PASS", "rejected_controls": sorted(rejected), "existing_output_preserved": True}, sort_keys=True))


if __name__ == "__main__":
    main()
