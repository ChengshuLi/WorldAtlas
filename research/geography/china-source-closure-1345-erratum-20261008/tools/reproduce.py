#!/usr/bin/env python3
"""Reconstruct the accepted China source closure through a pinned legacy CLI.

This wrapper binds the editable inputs to the independent accepted originals,
admits a complete fresh output vintage before calculation, runs the original
assembler in a private Git fixture, and publishes its products exclusively.
It is a bounded evidence runner, not a geographic approval or sandbox.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import sys

BASE = Path(__file__).resolve().parents[4]
OWNED = "research/geography/china-source-closure-1345-erratum-20261008/"
PREDECESSOR = "research/geography/china-fifty-numeric-gap-family-source-fitness-20261007/"
BASELINE_COMMIT = "06471b85b8cf2b2ae1ef3046f3f816e45558567b"
HANDOFF_SHA = "76a236f6354fa3cba4cec1bc2a5717e4aa66ce9842e108c6c1769e41b73c52ae"
CONTRACT_SHA = "74c472f546642bb61a6f68695f17f8d47fbabc6fa20c3d5cad32327a8fc82015"
LOCK_SHA = "058eefa94ab2de9db7b114771ae877f4b0769b3c0b0134d7acb229a536129fe2"
ASSEMBLER_SHA = "daeb6cb71fdb0f8d9b9938bf61259513670204e713214ff542f7f5bd753e5aaa"
IMMUTABLE_SHA = "a3667cecd88b2862e61a3ce72778e179535d92fbf19b5cd7c5b112722926da46"
PYTHON_SHA = "b27e4ef865657c9a8ce607da7cee3a3971170ebd8560675164a17c2c8e40a82a"
NODE_SHA = "9caea9deafcb0c7f22fac3206c32f0dcaf8d1f13460b0be3017fa09e7a4be4f6"
HISTORICAL_OUTPUT_SHA = "ea270f3be4fe993dbe5e9d1d567d8efef4348f3ea1a27505b91b762ea8505340"
CURRENT_OUTPUT_SHA = "d463962c395377be47ce76b8a35d7bdcf8f2eb98e16b620e6a27a87f69f3a55f"
MAX_BYTES = 256 * 1024 * 1024

INPUT_FILES = {
    "handoff": (PREDECESSOR + "inputs/complete-source-ready-handoff.json", HANDOFF_SHA),
    "contract": (PREDECESSOR + "inputs/candidate-contract.json", CONTRACT_SHA),
    "lock": (PREDECESSOR + "inputs/frozen-input-lock.json", LOCK_SHA),
    "assembler": (PREDECESSOR + "tools/assemble-source-closure.mjs", ASSEMBLER_SHA),
    "immutable_helper": ("scripts/evidence/immutable.py", IMMUTABLE_SHA),
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_immutable():
    path = BASE / "scripts/evidence/immutable.py"
    if sha(path.read_bytes()) != IMMUTABLE_SHA:
        raise ValueError("Shared immutable evidence helper differs from pinned baseline")
    spec = importlib.util.spec_from_file_location("worldatlas_immutable", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def node_runtime() -> Path:
    requested = os.environ.get("WORLDATLAS_NODE_BINARY")
    candidates = [Path(requested)] if requested else [
        Path("/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node"),
        Path(shutil.which("node") or "/nonexistent/node"),
    ]
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK) and sha(candidate.read_bytes()) == NODE_SHA:
            return candidate.resolve()
    raise RuntimeError("Required pinned Node executable unavailable; expected SHA-256 " + NODE_SHA)


def pinned_inputs(immutable):
    baseline = immutable.Baseline(str(BASE), BASELINE_COMMIT, [
        {"path": path, "bytes": len((BASE / path).read_bytes()), "sha256": digest, "hash_kind": "file-bytes"}
        for path, digest in INPUT_FILES.values()
    ])
    handoff = json.loads(baseline.pinned_bytes(INPUT_FILES["handoff"][0]))
    contract = json.loads(baseline.pinned_bytes(INPUT_FILES["contract"][0]))
    # These paths and hashes are taken from the independently hash-bound handoff.
    dynamic = [
        handoff["world_index_pin"], handoff["source_metadata_whole_containing_file_pin"],
        handoff["source_attribution_pin"], handoff["source_catalogue_pin"], handoff["terms_pin"],
        *handoff["source_encoded_ordinary_pins"], *handoff["actual_current_main_scoped_whole_byte_equality"],
    ]
    for row in dynamic:
        path = row["path"]
        raw = baseline.read(path)
        if len(raw) != row["bytes"] or sha(raw) != row["sha256"]:
            raise ValueError("Pinned source/current input differs from accepted handoff: " + path)
        if path not in baseline.pins:
            baseline.pins[path] = immutable.descriptor(path, raw)
        baseline.materialized_bytes(path)
    return baseline, handoff, contract


def fixture(root: Path, baseline, handoff: bytes, contract: bytes, lock: bytes, assembler: bytes):
    packet = root / PREDECESSOR
    (packet / "inputs").mkdir(parents=True)
    (packet / "tools").mkdir(parents=True)
    (packet / "inputs/complete-source-ready-handoff.json").write_bytes(handoff)
    (packet / "inputs/candidate-contract.json").write_bytes(contract)
    (packet / "inputs/frozen-input-lock.json").write_bytes(lock)
    (packet / "tools/assemble-source-closure.mjs").write_bytes(assembler)
    helper = root / "scripts/evidence/immutable.py"
    helper.parent.mkdir(parents=True, exist_ok=True)
    helper.write_bytes(baseline.pinned_bytes("scripts/evidence/immutable.py"))
    hand = json.loads(handoff)
    paths = {row["path"] for row in [
        hand["world_index_pin"], hand["source_metadata_whole_containing_file_pin"],
        hand["source_attribution_pin"], hand["source_catalogue_pin"], hand["terms_pin"],
        *hand["source_encoded_ordinary_pins"], *hand["actual_current_main_scoped_whole_byte_equality"],
    ]}
    for rel in sorted(paths):
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(baseline.pinned_bytes(rel))
    gd = root / ".git"
    (gd / "objects/info").mkdir(parents=True)
    (gd / "refs/heads").mkdir(parents=True)
    (gd / "refs/remotes/origin").mkdir(parents=True)
    object_dir = subprocess.check_output(["git", "-C", str(BASE), "rev-parse", "--git-path", "objects"], text=True).strip()
    object_dir = Path(object_dir)
    if not object_dir.is_absolute():
        object_dir = (BASE / object_dir).resolve()
    (gd / "objects/info/alternates").write_text(str(object_dir) + "\n")
    (gd / "config").write_text("[core]\n\trepositoryformatversion = 0\n\tfilemode = true\n\tbare = false\n")
    (gd / "HEAD").write_text("ref: refs/heads/main\n")
    (gd / "refs/heads/main").write_text(BASELINE_COMMIT + "\n")
    (gd / "refs/remotes/origin/main").write_text(BASELINE_COMMIT + "\n")


def report_signature(report):
    # The historical report identifies the frozen main head in several places.
    # Normalize only those declared execution-context fields for content review.
    value = json.loads(json.dumps(report))
    value["input_pins"]["current_main_head"] = "<baseline>"
    value["current_contact_file"]["head"] = "<baseline>"
    for key in ("verified_current_main_source_pins", "verified_current_main_scoped_pins"):
        for row in value.get(key, []):
            row["current_main_head"] = "<baseline>"
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def run(vintage: str):
    immutable = load_immutable()
    baseline, handoff_obj, contract_obj = pinned_inputs(immutable)
    # Recheck both canonical accepted anchors independently of the editable packet.
    handoff_path, contract_path = INPUT_FILES["handoff"][0], INPUT_FILES["contract"][0]
    handoff = baseline.materialized_bytes(handoff_path)
    contract = baseline.materialized_bytes(contract_path)
    lock = baseline.materialized_bytes(INPUT_FILES["lock"][0])
    assembler = baseline.materialized_bytes(INPUT_FILES["assembler"][0])
    node = node_runtime()
    python_bin = Path(sys.executable).resolve()
    if sys.version_info[:3] != (3, 7, 3) or sha(python_bin.read_bytes()) != PYTHON_SHA:
        raise RuntimeError("Required pinned Python 3.7.3 executable differs from recorded runtime")
    runner_path = Path(__file__).resolve()
    runner_sha = sha(runner_path.read_bytes())
    node_version = subprocess.check_output([str(node), "--version"], text=True).strip()
    if node_version != "v24.19.0":
        raise RuntimeError("Pinned Node version mismatch: " + node_version)

    # Explicitly account for decoded source bytes and each producer input before
    # the destination is considered admitted or any computation begins.
    for path in [handoff_path, contract_path, INPUT_FILES["lock"][0], INPUT_FILES["assembler"][0]]:
        baseline.admit(path, len(baseline.pinned_bytes(path)))
    for path in baseline.pins:
        baseline.pinned_bytes(path)
    decoded = __import__("gzip").decompress(baseline.pinned_bytes(handoff_obj["source_encoded_ordinary_pins"][0]["path"]))
    baseline.admit("decoded:" + handoff_obj["source_encoded_ordinary_pins"][0]["path"], len(decoded))
    if len(decoded) != 7018287 or sha(decoded) != "8c7dfa8e40842f9162453d9b0b614276a48bf635559ba371c7982cb288e7b303":
        raise ValueError("Decoded original source identity mismatch")

    outputs = ["reconciliation.json", "execution.json"]
    vintage_writer = immutable.NewVintage(baseline, OWNED, vintage, outputs)
    # No write to the actual checkout occurs before complete NewVintage admission.
    with tempfile.TemporaryDirectory(prefix="source-closure-", dir=BASE / OWNED) as scratch:
        root = Path(scratch) / "fixture"
        root.mkdir()
        fixture(root, baseline, handoff, contract, lock, assembler)
        staging = Path(scratch) / "legacy-output.json"
        completed = subprocess.run([str(node), str(root / PREDECESSOR / "tools/assemble-source-closure.mjs"), str(staging)],
                                   cwd=root, text=True, capture_output=True, timeout=180)
        if completed.returncode:
            raise RuntimeError("Pinned original CLI failed: " + completed.stderr[-4000:])
        result = staging.read_bytes()
        if len(result) > immutable.MAX_FILE_BYTES or sha(result) != CURRENT_OUTPUT_SHA:
            raise ValueError("Original CLI output differs from accepted current-baseline reproduction")
        parsed = json.loads(result)
        if parsed["component_count"] != 50 or parsed["contact_count"] != 14 or len(parsed["families"]) != 2:
            raise ValueError("Full closure roster mismatch")
        execution = {
            "version": 1, "status": "complete", "baseline_commit": BASELINE_COMMIT,
            "accepted_inputs": [immutable.descriptor(path, baseline.pinned_bytes(path)) for path, _ in INPUT_FILES.values()],
            "source_inputs": [immutable.descriptor(path, baseline.pinned_bytes(path)) for path in sorted(baseline.pins) if path not in {p for p, _ in INPUT_FILES.values()}],
            "runtime": {"node_path": str(node), "version": node_version, "sha256": NODE_SHA,
                        "python_path": str(python_bin), "python_version": sys.version, "python_sha256": PYTHON_SHA,
                        "historical_sha256": "27db838bb204ef7c21df2931f5656e4c8fb32e6e947f363a402b49714d32b5b1",
                        "historical_replay": False},
            "runner": {"path": str(runner_path.relative_to(BASE)), "sha256": runner_sha},
            "legacy_cli": {"path": INPUT_FILES["assembler"][0], "sha256": ASSEMBLER_SHA,
                           "exit_code": completed.returncode, "stdout": completed.stdout.strip(),
                           "stderr_sha256": sha(completed.stderr.encode())},
            "output": immutable.descriptor("reconciliation.json", result),
            "roster": {"components": 50, "contacts": 14, "families": 2,
                       "available_numeric_sibling_bindings": 34},
            "limitations": ["Source closure reconstruction only; no boundary overlay or physical validation.",
                            "Source authority, applicable license, precision, current condition and parent #1202 remain unresolved.",
                            "Current Node binary differs from the historically recorded executable; this is not exact historical executable replay."],
        }
        # Compare to both retained successful vintages after normalizing only
        # recorded head labels. This demonstrates substantive stable output.
        predecessor = Path(BASE) / PREDECESSOR / "runs/final-1.json"
        expected = json.loads(predecessor.read_text())
        if report_signature(parsed) != report_signature(expected):
            raise ValueError("Reconstruction changed substantive report content vs retained final-1")
        payloads = {"reconciliation.json": result, "execution.json": immutable.canonical_json(execution)}
        published = vintage_writer.publish_bytes(payloads)
        for name, expected in payloads.items():
            actual = (vintage_writer.root / name).read_bytes()
            if actual != expected or sha(actual) != sha(expected):
                raise ValueError("Published output readback mismatch: " + name)
        receipt = json.loads((vintage_writer.root / "publication.json").read_bytes())
        if receipt.get("status") != "complete" or receipt.get("outputs") != published:
            raise ValueError("Published completion receipt readback mismatch")
    print(json.dumps({"vintage": vintage, "output_sha256": sha(result),
                      "bytes": len(result), "node": node_version, "baseline": BASELINE_COMMIT}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("vintage", help="Fresh lower-case vintage name; never reuse")
    args = parser.parse_args()
    run(args.vintage)
