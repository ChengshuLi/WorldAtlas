#!/usr/bin/env python3
"""Hash-gated, non-destructive reproduction of the retained #981 audit."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OWNED = ROOT / "data/regional-review/usa-adm2-lineage-981-erratum"
PIN_FILE = OWNED / "source/pinned-inputs.json"
IDS_FILE = OWNED / "source/subject-ids.json"
OLD_SCRIPT = ROOT / "data/regional-review/usa-adm2-lineage-428/scripts/audit_lineage.py"
OLD_OUTPUTS = {
    ROOT / "data/regional-review/usa-adm2-lineage-428/findings/input-manifest.json": "input-manifest.json",
    ROOT / "data/regional-review/usa-adm2-lineage-428/findings/subject-crosswalk.jsonl": "subject-crosswalk.jsonl",
    ROOT / "data/regional-review/usa-adm2-lineage-428/findings/source-lineage-audit.json": "source-lineage-audit.json",
}

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def load_json(path: Path):
    data = path.read_bytes()
    expected = {PIN_FILE: "ace7608d519d56341a5260644a2379292f40685401147998143313daad6d242a",
                IDS_FILE: "6560f1e577551195d16b4c3c049c11972f40c4f5b2046175bb3bb0ce521c7a01"}.get(path)
    if expected and digest(data) != expected:
        raise ValueError(f"issue-pinned control file changed: {path.name}")
    return json.loads(data)

def validate_ids(ids):
    if not isinstance(ids, list) or len(ids) != 279 or any(not isinstance(x, str) for x in ids) or len(set(ids)) != len(ids):
        raise ValueError("scope must contain exactly 279 unique string IDs")

def verify_inputs(pins, root=ROOT, *, expected_count=72, check_git=True, check_script=True):
    if pins.get("baseline_commit") != "c42f4b7465964245ecbcd8eed4961eb76af3106b":
        raise ValueError("unexpected immutable baseline")
    rows = pins.get("files")
    if not isinstance(rows, list) or len(rows) != expected_count:
        raise ValueError(f"expected {expected_count} pinned input files")
    seen = set()
    for row in rows:
        rel = row.get("path")
        if not isinstance(rel, str) or rel in seen or Path(rel).is_absolute() or ".." in Path(rel).parts:
            raise ValueError("unsafe or duplicate pin path")
        seen.add(rel)
        if row.get("commit") != pins["baseline_commit"]:
            raise ValueError(f"non-baseline commit pin: {rel}")
        path = root / rel
        try:
            data = path.read_bytes()
        except FileNotFoundError as exc:
            raise ValueError(f"missing pinned input: {rel}") from exc
        if len(data) != row.get("bytes") or digest(data) != row.get("sha256"):
            raise ValueError(f"pinned input drift: {rel}")
        if check_git:
            blob = subprocess.check_output(["git", "show", f"{row['commit']}:{rel}"], cwd=root)
            if len(blob) != row["bytes"] or digest(blob) != row["sha256"]:
                raise ValueError(f"immutable Git blob differs from declared pin: {rel}")
    if check_script:
        old_desc = next((x for x in rows if x["path"] == OLD_SCRIPT.relative_to(ROOT).as_posix()), None)
        if old_desc is None or digest(OLD_SCRIPT.read_bytes()) != old_desc["sha256"]:
            raise ValueError("retained reproducer does not match its immutable source pin")

def exclusive_write(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as out:
        out.write(data)

def reproduce(run_name: str):
    pins = load_json(PIN_FILE)
    ids = load_json(IDS_FILE)
    verify_inputs(pins)
    validate_ids(ids)
    dest = OWNED / "runs" / run_name / "findings"
    if dest.exists() and any(dest.iterdir()):
        raise FileExistsError(f"refusing nonempty existing output directory: {dest}")
    dest.mkdir(parents=True, exist_ok=True)
    original_bytes = Path.write_bytes
    original_text = Path.write_text
    def redirected_bytes(path, data):
        absolute = path.resolve()
        if absolute not in OLD_OUTPUTS:
            raise PermissionError(f"unexpected write from retained reproducer: {absolute}")
        exclusive_write(dest / OLD_OUTPUTS[absolute], data)
        return len(data)
    def redirected_text(path, data, encoding=None, errors=None, newline=None):
        absolute = path.resolve()
        if absolute not in OLD_OUTPUTS:
            raise PermissionError(f"unexpected write from retained reproducer: {absolute}")
        exclusive_write(dest / OLD_OUTPUTS[absolute], data.encode(encoding or "utf-8", errors or "strict"))
        return len(data)
    try:
        Path.write_bytes = redirected_bytes
        Path.write_text = redirected_text
        spec = importlib.util.spec_from_file_location("retained_audit_lineage", OLD_SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.main()
    finally:
        Path.write_bytes = original_bytes
        Path.write_text = original_text
    expected = {
        "input-manifest.json": "d582b787f663988ad908ff14329a9aac271c9b7b3b659ce285ce19f063a74b1f",
        "subject-crosswalk.jsonl": "c7ae095791268a05e266b450229f99b7b86546fdd7d644dcbf5876d6eea313c3",
        "source-lineage-audit.json": "1160ac4e2491182853659a4115199f56583c281dd5efe0d9d9d45797434f892d",
    }
    actual = {}
    for name, sha in expected.items():
        data = (dest / name).read_bytes()
        actual[name] = {"bytes": len(data), "sha256": digest(data), "matches_retained_output": digest(data) == sha}
        if digest(data) != sha:
            raise ValueError(f"reproduced output differs from retained original: {name}")
    record = {"run": run_name, "baseline_commit": pins["baseline_commit"], "checked_inputs": 72,
              "checked_input_bytes": sum(x["bytes"] for x in pins["files"]),
              "script_sha256": digest(Path(__file__).read_bytes()), "outputs": actual,
              "written_exclusively_under_owned_path": True}
    exclusive_write(dest.parent / "reproduction-record.json", (json.dumps(record, indent=2) + "\n").encode())
    print(json.dumps(record, indent=2))

def self_test_controls():
    fixture_dir = OWNED / "fixtures"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    fixture = fixture_dir / "control-input.txt"
    if not fixture.exists():
        exclusive_write(fixture, b"OK\n")
    base = {"pin": "fixture", "commit": "c42f4b7465964245ecbcd8eed4961eb76af3106b",
            "path": "control-input.txt", "bytes": 3, "sha256": digest(b"OK\n")}
    results = []
    def rejected_before_output(label, check):
        out = OWNED / "runs/controls" / (label.replace(" ", "-") + ".out")
        try:
            check()
            exclusive_write(out, b"should not be created")
        except (ValueError, FileNotFoundError, FileExistsError):
            if out.exists():
                raise AssertionError(f"failed preflight created output: {label}")
            results.append({"control": label, "rejected_before_output": True})
        else:
            raise AssertionError(f"negative control unexpectedly passed: {label}")
    run_root = fixture_dir
    good_manifest = {"baseline_commit": base["commit"], "files": [base]}
    rejected_before_output("modified input bytes hash rejected", lambda: verify_inputs(
        {"baseline_commit": base["commit"], "files": [{**base, "sha256": "0"*64}]},
        run_root, expected_count=1, check_git=False, check_script=False))
    rejected_before_output("missing input rejected", lambda: verify_inputs(
        {"baseline_commit": base["commit"], "files": [{**base, "path": "absent.txt"}]},
        run_root, expected_count=1, check_git=False, check_script=False))
    rejected_before_output("duplicate scoped IDs rejected", lambda: validate_ids(["x"] * 279))
    existing = OWNED / "runs/controls/preexisting.txt"
    existing.parent.mkdir(parents=True, exist_ok=True)
    if not existing.exists(): exclusive_write(existing, b"existing\n")
    before = existing.read_bytes()
    try:
        exclusive_write(existing, b"overwrite\n")
    except FileExistsError:
        if existing.read_bytes() != before: raise AssertionError("existing output was modified")
        results.append({"control": "existing output preserved", "rejected_before_overwrite": True})
    else: raise AssertionError("existing output was overwritten")
    out = OWNED / "runs/controls/negative-controls.json"
    exclusive_write(out, (json.dumps({"method_id": "immutable-source-reproduction", "kind": "source", "outcome": "passed", "version": 1, "fixture_bytes": 3, "controls": results}, indent=2) + "\n").encode())
    print(json.dumps({"negative_controls": results}, indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["reproduce", "self-test-controls"])
    parser.add_argument("--run", default="run-01")
    args = parser.parse_args()
    if args.command == "reproduce": reproduce(args.run)
    else: self_test_controls()
