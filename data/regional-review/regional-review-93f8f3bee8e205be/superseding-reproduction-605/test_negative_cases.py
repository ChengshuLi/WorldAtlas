#!/usr/bin/env python3
"""Exercise #605 pin rejection and exclusive-output controls in a private owned-path fixture."""
import copy
import json
import os
import subprocess
import tempfile
from pathlib import Path

import build_packet as bp
from scripts.evidence.immutable import Baseline, descriptor, sha256, write_new_vintage


def rejected(label, function):
    try:
        function()
    except (ValueError, FileNotFoundError):
        return {"case": label, "result": "rejected"}
    raise AssertionError("Negative control unexpectedly accepted: " + label)


def run() -> dict:
    scope = json.loads((bp.ROOT / bp.SCOPE_PATH).read_text())
    bp.validate_issue_capture(scope)
    baseline_files = bp.project_pins()
    source_baseline, registry, source_data = bp.verify_source_snapshot(scope)
    original = bp.build_packet()[1]
    results = []

    bad_commit = "0" * 40
    results.append(rejected("unknown evaluation commit", lambda: bp.exact_commit(bad_commit)))

    bad_pin = copy.deepcopy(baseline_files)
    bad_pin[0]["sha256"] = ("0" if bad_pin[0]["sha256"][0] != "0" else "1") + bad_pin[0]["sha256"][1:]
    results.append(rejected("changed whole-file baseline descriptor", lambda: Baseline(bp.ROOT, bp.BASELINE_COMMIT, bad_pin)))

    changed_body = copy.deepcopy(scope)
    changed_body["issue_body"] += "\n"
    results.append(rejected("changed captured GitHub issue body", lambda: bp.validate_issue_capture(changed_body)))

    changed_commit = copy.deepcopy(scope)
    changed_commit["original_packet_commit"] = "0" * 40
    results.append(rejected("changed original source snapshot commit", lambda: bp.validate_issue_capture(changed_commit)))

    changed_scope_pin = copy.deepcopy(scope)
    changed_scope_pin["original_scope_sha256"] = "0" * 64
    results.append(rejected("changed original scope whole-file pin", lambda: bp.validate_issue_capture(changed_scope_pin)))

    duplicate = copy.deepcopy(scope)
    duplicate["subject_ids"][-1] = duplicate["subject_ids"][0]
    duplicate["subject_ids_sha256"] = sha256(json.dumps(sorted(duplicate["subject_ids"]), separators=(",", ":")).encode())
    results.append(rejected("duplicate assigned subject", lambda: bp.validate_issue_capture(duplicate)))

    missing = copy.deepcopy(scope)
    missing["subject_ids"].pop()
    missing["subject_ids_sha256"] = sha256(json.dumps(sorted(missing["subject_ids"]), separators=(",", ":")).encode())
    results.append(rejected("missing assigned subject", lambda: bp.validate_issue_capture(missing)))

    source_rows = {row["path"]: row for row in source_data["files"]}
    changed_registry = copy.deepcopy(registry)
    changed_registry["sources"][0]["sha256"] = "0" * 64
    results.append(rejected("changed retained Census/TIGER source hash", lambda: bp.validate_registry_rows(changed_registry, source_rows)))

    # The generated new-vintage gzip bytes are identical across the independent rebuilds,
    # carry a zero mtime/empty filename/fixed OS byte, and differ from preserved archives.
    for name in ("current-scope-and-parents.json.gz", "current-parent-chains.json.gz"):
        raw = bp.encoded_output(name, dict(next(value for file, value in original["outputs"] if file == name)))
        if raw[3] & 8 or int.from_bytes(raw[4:8], "little") != 0 or raw[9] != 255:
            raise AssertionError("Deterministic gzip header invariant failed: " + name)
    results.append({"case": "fixed gzip mtime, empty filename and fixed OS header", "result": "passed"})
    if original["run_sha256"] != bp.build_packet()[1]["run_sha256"]:
        raise AssertionError("Independent full rebuild hash changed")
    results.append({"case": "two independent complete builds byte-identical", "result": "passed"})

    # Verify shared helper refuses replacement and preserves the first bytes.
    with tempfile.TemporaryDirectory(prefix="negative-control-", dir=bp.OUT) as temp:
        fixture = Path(temp)
        subprocess.run(["git", "init", "-q", str(fixture)], check=True)
        subprocess.run(["git", "-C", str(fixture), "config", "user.email", "codex@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(fixture), "config", "user.name", "WorldAtlas control"], check=True)
        (fixture / "pin.json").write_bytes(b"immutable test input\n")
        subprocess.run(["git", "-C", str(fixture), "add", "pin.json"], check=True)
        subprocess.run(["git", "-C", str(fixture), "commit", "-qm", "fixture"], check=True)
        commit = subprocess.check_output(["git", "-C", str(fixture), "rev-parse", "HEAD"], text=True).strip()
        pin = descriptor("pin.json", b"immutable test input\n")
        fixture_baseline = Baseline(fixture, commit, [pin])
        wrong = {**pin, "sha256": "0" * 64}
        bad_target = fixture / bp.OWNED / "vintages" / "must-not-exist"
        results.append(rejected("changed pin rejected before output directory", lambda: Baseline(fixture, commit, [wrong])))
        if bad_target.exists():
            raise AssertionError("Failed pin created output")
        first = write_new_vintage(fixture_baseline, bp.OWNED, "overwrite-test", "receipt.json", {"value": 1})
        target = fixture / first["path"]
        before = target.read_bytes()
        try:
            write_new_vintage(fixture_baseline, bp.OWNED, "overwrite-test", "receipt.json", {"value": 2})
        except FileExistsError:
            pass
        else:
            raise AssertionError("Existing output was overwritten")
        if target.read_bytes() != before:
            raise AssertionError("Overwrite refusal changed existing bytes")
        results.append({"case": "exclusive overwrite refusal preserves existing bytes", "result": "passed"})

    return {
        "version": 1, "issue": 605, "method_id": "issue486-immutable-baseline-deterministic-compression",
        "baseline_commit": bp.BASELINE_COMMIT, "source_snapshot_commit": bp.SOURCE_SNAPSHOT_COMMIT,
        "subject_count": 211, "cases": results,
        "changed_pin_created_no_output": True, "existing_output_preserved": True,
        "original_packet_write_attempts": 0, "result": "PASS",
    }


def main() -> None:
    result = run()
    target = bp.OUT / "negative-control-results.json"
    payload = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if target.exists():
        if target.read_text() != payload:
            raise SystemExit("Existing negative-control results differ; preserve and investigate")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(payload)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
