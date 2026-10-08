#!/usr/bin/env python3
"""Run the frozen #1292 coverage producer into an admitted, immutable new vintage.

This successor never writes either historical packet. The old calculation code is
loaded from its recorded Git commit, its historical Git reads are hash-checked
against source-pins.json, and its output paths are redirected to a private stage.
"""
import argparse
import base64
import contextlib
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess as real_subprocess
import sys
import tempfile
import traceback
import types

ROOT = Path(__file__).resolve().parents[3]
OWNED = "data/regional-review/nukunonu-bounty-1292-replay-preservation-erratum/"
PIN_FILE = OWNED + "source-pins.json"
RUNNER = OWNED + "reproduce_safe_coverage.py"
LEGACY_COMMIT = "c3ac95a5d72258d46c85e94590c8168edf32a3e3"
LEGACY_PATH = "data/regional-review/regional-supplement-e5d72b7004238f80/nukunonu/reproduce_current_coverage.py"
AREA_PATH = "scripts/ellipsoidal_area.py"
NUKU_ASSESSMENT = "data/regional-review/regional-supplement-e5d72b7004238f80/nukunonu/assessment.json"
BOUNTY_ASSESSMENT = "data/regional-review/regional-supplement-b5299df90ec984cc/bounty-islands/assessment.json"
NUKU_RESULT = "data/regional-review/regional-supplement-e5d72b7004238f80/nukunonu/current-coverage.json"
BOUNTY_RESULT = "data/regional-review/regional-supplement-b5299df90ec984cc/bounty-islands/current-coverage.json"
IMMUTABLE_PATH = "scripts/evidence/immutable.py"
SUBJECTS = [
    "atlas:macro-coverage:location:a0457f0d44c94b71f00d",
    "atlas:macro-coverage:location:73281d3672f84a47a770",
]
ISSUE_OPERATION_CAP = 234_809_776


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def stable_json(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def fail(message):
    raise ValueError(message)


def read_pin_table(root):
    raw = (root / PIN_FILE).read_bytes()
    table = json.loads(raw)
    if table.get("issue") != 1469 or table.get("contract_version") != 1:
        fail("source pin inventory does not match issue 1469")
    pins = {}
    for row in table.get("pins", []):
        key = row["commit"] + ":" + row["path"]
        if key in pins or len(row["commit"]) != 40 or len(row["sha256"]) != 64:
            fail("duplicate or malformed immutable pin")
        pins[key] = row["sha256"]
    if len(pins) != 61:
        fail("issue-owned input inventory is incomplete")
    return raw, pins


def helper_module(root, helper_bytes):
    module = types.ModuleType("worldatlas_pinned_immutable")
    module.__file__ = str(root / IMMUTABLE_PATH)
    exec(compile(helper_bytes, module.__file__, "exec"), module.__dict__)
    return module


class GitBlobReader:
    """Only allow historical reads named in issue 1469's immutable pin table."""
    def __init__(self, root, pins, baseline):
        self.root, self.pins, self.baseline = root, pins, baseline
        self.cache = {}

    def read(self, commit, path):
        key = commit + ":" + path
        expected = self.pins.get(key)
        if expected is None:
            fail("unlisted historical input requested: " + key)
        if key not in self.cache:
            raw = real_subprocess.check_output(
                ["git", "-C", str(self.root), "show", key], stderr=real_subprocess.PIPE)
            if digest(raw) != expected:
                fail("historical input hash mismatch: " + key)
            self.baseline.admit("historical:" + key, len(raw))
            self.cache[key] = raw
        return self.cache[key]

    def subprocess_proxy(self):
        owner = self

        def check_output(args, **kwargs):
            if len(args) == 3 and args[:2] == ["git", "show"]:
                commit, sep, path = args[2].partition(":")
                if sep:
                    return owner.read(commit, path)
            fail("frozen producer attempted an unapproved subprocess call")

        def run(args, **kwargs):
            if len(args) == 4 and args[:3] == ["git", "cat-file", "-e"]:
                commit, sep, path = args[3].partition(":")
                if sep:
                    # These two absences are explicit facts inspected by the
                    # frozen method; no bytes are returned or inferred.
                    if (commit, path) in {
                        ("4afe1cb250fe68f5c63022d9583b3b89b9e607a2",
                         "data/geography/source-restoration-additions.json"),
                        ("4afe1cb250fe68f5c63022d9583b3b89b9e607a2",
                         "data/geographic-releases/current-manifest.json"),
                    }:
                        return real_subprocess.CompletedProcess(args, 1)
                    try:
                        owner.read(commit, path)
                        return real_subprocess.CompletedProcess(args, 0)
                    except (ValueError, real_subprocess.CalledProcessError):
                        return real_subprocess.CompletedProcess(args, 1)
            fail("frozen producer attempted an unapproved subprocess call")

        return types.SimpleNamespace(
            check_output=check_output,
            run=run,
            DEVNULL=real_subprocess.DEVNULL,
            CompletedProcess=real_subprocess.CompletedProcess,
        )


def git_blob(root, commit, path):
    return real_subprocess.check_output(
        ["git", "-C", str(root), "show", commit + ":" + path],
        stderr=real_subprocess.PIPE)


def make_baseline(root, helper):
    commit = real_subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    raw = git_blob(root, commit, IMMUTABLE_PATH)
    if raw != helper:
        fail("materialized shared evidence helper differs from immutable HEAD")
    desc = {"path": IMMUTABLE_PATH, "bytes": len(raw), "sha256": digest(raw),
            "hash_kind": "file-bytes"}
    return helper_module(root, raw).Baseline(root, commit, [desc])


def execute_frozen(root, baseline, pins):
    legacy = GitBlobReader(root, pins, baseline)
    code = legacy.read(LEGACY_COMMIT, LEGACY_PATH)
    area = legacy.read(LEGACY_COMMIT, AREA_PATH)
    nuku_assessment = legacy.read(LEGACY_COMMIT, NUKU_ASSESSMENT)
    bounty_assessment = legacy.read(LEGACY_COMMIT, BOUNTY_ASSESSMENT)
    expected_nuku = legacy.read(LEGACY_COMMIT, NUKU_RESULT)
    expected_bounty = legacy.read(LEGACY_COMMIT, BOUNTY_RESULT)

    stage_parent = root / OWNED
    temp_dir = tempfile.TemporaryDirectory(prefix=".private-replay-", dir=stage_parent)
    stage = Path(temp_dir.name)
    packet_nuku = stage / "nukunonu"
    packet_bounty = stage / "bounty-islands"
    packet_nuku.mkdir()
    packet_bounty.mkdir()
    (packet_nuku / "assessment.json").write_bytes(nuku_assessment)
    (packet_bounty / "assessment.json").write_bytes(bounty_assessment)

    old_area = sys.modules.get("ellipsoidal_area")
    area_module = types.ModuleType("ellipsoidal_area")
    area_module.__file__ = str(root / AREA_PATH)
    exec(compile(area, area_module.__file__, "exec"), area_module.__dict__)
    sys.modules["ellipsoidal_area"] = area_module
    namespace = {
        "__name__": "__worldatlas_frozen_1292_reproducer__",
        "__file__": str(root / LEGACY_PATH),
    }
    old_path = list(sys.path)
    stdout, stderr = io.StringIO(), io.StringIO()
    result = {"exit_code": 0, "exception": None}
    try:
        exec(compile(code, namespace["__file__"], "exec"), namespace)
        namespace["ROOT"] = root
        namespace["PACKET"] = packet_nuku
        namespace["BOUNTY"] = packet_bounty
        namespace["subprocess"] = legacy.subprocess_proxy()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            namespace["main"](False)
    except BaseException as exc:
        result["exit_code"] = exc.code if isinstance(exc, SystemExit) and isinstance(exc.code, int) else 1
        result["exception"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    finally:
        sys.path[:] = old_path
        if old_area is None:
            sys.modules.pop("ellipsoidal_area", None)
        else:
            sys.modules["ellipsoidal_area"] = old_area

    produced = {}
    for name, path, expected in [
        ("nukunonu", packet_nuku / "current-coverage.json", expected_nuku),
        ("bounty-islands", packet_bounty / "current-coverage.json", expected_bounty),
    ]:
        if path.exists() and path.is_file() and not path.is_symlink():
            raw = path.read_bytes()
            baseline.admit("private-output:" + name, len(raw))
            produced[name] = {
                "bytes_base64": base64.b64encode(raw).decode("ascii"),
                "bytes": len(raw),
                "sha256": digest(raw),
                "matches_retained_output": raw == expected,
            }
    baseline.admit("private-packet:nukunonu-assessment", len(nuku_assessment))
    baseline.admit("private-packet:bounty-assessment", len(bounty_assessment))
    for rel in [
        "data/macro-improvements/macro-coverage-oceania/osm-2af0d96ae4f6.xml.gz",
        "data/macro-improvements/macro-coverage-oceania/osm-28c1ddf724e1.xml.gz",
        "data/macro-improvements/macro-coverage-oceania/gshhg-selected-full-records.bin.gz",
    ]:
        key = "9be99dfefb5871237ac464c6ef8a23e82be501f6:" + rel
        compressed = legacy.cache[key]
        decoded = gzip.decompress(compressed)
        baseline.admit("decoded:" + key, len(decoded))
    inputs = {
        "legacy_producer": {"commit": LEGACY_COMMIT, "path": LEGACY_PATH,
                            "bytes": len(code), "sha256": digest(code)},
        "area_helper": {"commit": LEGACY_COMMIT, "path": AREA_PATH,
                        "bytes": len(area), "sha256": digest(area)},
        "nukunonu_assessment": {"commit": LEGACY_COMMIT, "path": NUKU_ASSESSMENT,
                                "bytes": len(nuku_assessment), "sha256": digest(nuku_assessment)},
        "bounty_assessment": {"commit": LEGACY_COMMIT, "path": BOUNTY_ASSESSMENT,
                              "bytes": len(bounty_assessment), "sha256": digest(bounty_assessment)},
        "retained_outputs": {
            "nukunonu": {"commit": LEGACY_COMMIT, "path": NUKU_RESULT,
                         "bytes": len(expected_nuku), "sha256": digest(expected_nuku)},
            "bounty-islands": {"commit": LEGACY_COMMIT, "path": BOUNTY_RESULT,
                               "bytes": len(expected_bounty), "sha256": digest(expected_bounty)},
        },
        "historical_git_inputs": [
            {"commit_path": key, "bytes": len(raw), "sha256": digest(raw)}
            for key, raw in sorted(legacy.cache.items())
        ],
    }
    original_paths = {
        NUKU_RESULT: "nukunonu",
        BOUNTY_RESULT: "bounty-islands",
    }
    unchanged = {}
    for rel, name in original_paths.items():
        raw = (root / rel).read_bytes()
        unchanged[rel] = {
            "bytes": len(raw),
            "sha256": digest(raw),
            "still_matches_pre_run_retained_output": raw == (expected_nuku if name == "nukunonu" else expected_bounty),
        }
    result.update({
        "status": "complete" if result["exit_code"] == 0 and len(produced) == 2
            and all(row["matches_retained_output"] for row in produced.values()) else "failed",
        "stdout": stdout.getvalue(),
        "stderr": stderr.getvalue(),
        "outputs": produced,
        "inputs": inputs,
        "historical_outputs_unchanged": unchanged,
        "resource_accounting": {
            "unique_raw_decoded_and_staged_input_bytes": sum(baseline.consumed.values()),
            "phase_limit_bytes": baseline.max_phase_bytes,
            "decoded_source_bytes": {
                key: len(gzip.decompress(legacy.cache[key]))
                for key in sorted(legacy.cache)
                if key.endswith((".xml.gz", ".bin.gz"))
            },
        },
    })
    temp_dir.cleanup()
    result["temporary_output_paths_removed"] = not stage.exists()
    if not result["temporary_output_paths_removed"]:
        result["status"] = "failed"
        result["exception"] = {
            "type": "TemporaryStageCleanupError",
            "message": "private output stage remained after cleanup",
        }
    return result


def verify_vintage(root, vintage):
    if not isinstance(vintage, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", vintage):
        fail("unsafe vintage name")
    run_root = root / OWNED / "vintages" / vintage
    for ancestor in [run_root, *run_root.parents]:
        if ancestor == root.parent:
            break
        if ancestor.is_symlink():
            fail("symlink in retained vintage path")
    if not run_root.is_dir():
        fail("vintage directory is absent or unsafe")
    receipt_path = run_root / "publication.json"
    product_path = run_root / "attempt.json"
    if receipt_path.is_symlink() or product_path.is_symlink():
        fail("symlink in retained vintage")
    receipt = json.loads(receipt_path.read_bytes())
    product = product_path.read_bytes()
    if receipt.get("status") != "complete" or len(receipt.get("outputs", [])) != 1:
        fail("vintage lacks a complete whole-run receipt")
    row = receipt["outputs"][0]
    if row.get("path") != str(product_path.relative_to(root)) or row.get("bytes") != len(product) or row.get("sha256") != digest(product):
        fail("whole-run output does not match publication receipt")
    attempt = json.loads(product)
    if attempt.get("status") != "complete":
        fail("retained attempt is not a successful complete replay")
    if attempt.get("temporary_output_paths_removed") is not True:
        fail("private stage cleanup was not verified")
    if set(attempt.get("outputs", {})) != {"nukunonu", "bounty-islands"}:
        fail("complete run does not include both exact subject reports")
    execution = attempt.get("execution", {})
    runner_raw = Path(__file__).read_bytes()
    pin_raw = (root / PIN_FILE).read_bytes()
    if execution.get("runner", {}).get("sha256") != digest(runner_raw) or execution.get("runner", {}).get("bytes") != len(runner_raw):
        fail("retained run is bound to different safe-runner bytes")
    source_code = base64.b64decode(execution.get("runner", {}).get("source_base64", ""), validate=True)
    if source_code != runner_raw:
        fail("retained run does not preserve the exact executed safe-runner source")
    if execution.get("pin_inventory", {}).get("sha256") != digest(pin_raw) or execution.get("pin_inventory", {}).get("bytes") != len(pin_raw):
        fail("retained run is bound to a different issue pin inventory")
    helper_record = execution.get("shared_helper", {})
    helper_commit, helper_path = helper_record.get("commit"), helper_record.get("path")
    if helper_path != IMMUTABLE_PATH or not helper_commit:
        fail("retained run has no exact shared-helper identity")
    helper_raw = git_blob(root, helper_commit, helper_path)
    if len(helper_raw) != helper_record.get("bytes") or digest(helper_raw) != helper_record.get("sha256"):
        fail("shared output-admission helper changed since execution")
    pins_raw, pins = read_pin_table(root)
    if pins_raw != pin_raw:
        fail("issue pin inventory changed while checking")
    historical = attempt.get("inputs", {}).get("historical_git_inputs", [])
    if not historical:
        fail("retained run has no consumed immutable Git inputs")
    total = 0
    for item in historical:
        key = item.get("commit_path", "")
        commit, sep, path = key.partition(":")
        if not sep or pins.get(key) != item.get("sha256"):
            fail("historical input is not bound to the issue pin inventory")
        raw = git_blob(root, commit, path)
        if len(raw) != item.get("bytes") or digest(raw) != item.get("sha256"):
            fail("historical input changed since execution: " + key)
        total += len(raw)
        if path.endswith((".xml.gz", ".bin.gz")):
            decoded = gzip.decompress(raw)
            if len(decoded) > 32 * 1024 * 1024:
                fail("decoded source exceeds per-file bound")
            total += len(decoded)
    if total > ISSUE_OPERATION_CAP:
        fail("check input phase exceeds issue operation cap")
    for name, record in attempt["outputs"].items():
        raw = base64.b64decode(record["bytes_base64"], validate=True)
        if len(raw) != record["bytes"] or digest(raw) != record["sha256"] or not record["matches_retained_output"]:
            fail("captured report bytes/hash/retained comparison mismatch: " + name)
    if not attempt.get("historical_outputs_unchanged") or not all(
        item.get("still_matches_pre_run_retained_output")
        for item in attempt["historical_outputs_unchanged"].values()
    ):
        fail("original retained report files were changed")
    return {"vintage": vintage, "status": "complete",
            "attempt_sha256": digest(product),
            "reports": {name: row["sha256"] for name, row in attempt["outputs"].items()}}


def run_vintage(root, vintage):
    if not isinstance(vintage, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,56}", vintage):
        fail("vintage must be a fresh lowercase name of at most 57 characters")
    pin_bytes, pins = read_pin_table(root)
    runner_bytes = Path(__file__).read_bytes()
    work_commit = real_subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    helper_raw = git_blob(root, work_commit, IMMUTABLE_PATH)
    baseline_module = helper_module(root, helper_raw)
    baseline = baseline_module.Baseline(
        root, work_commit,
        [{"path": IMMUTABLE_PATH, "bytes": len(helper_raw), "sha256": digest(helper_raw),
          "hash_kind": "file-bytes"}])
    # Count and authenticate the exact candidate-controlled inventory/code too.
    baseline.admit("candidate:" + PIN_FILE, len(pin_bytes))
    baseline.admit("candidate:" + RUNNER, len(runner_bytes))
    baseline.pinned_bytes(IMMUTABLE_PATH)
    # Reserve a conservative whole-run result envelope before computation.
    # Actual bytes are admitted again by NewVintage.publish_bytes.
    result_reservation = 512 * 1024
    baseline.admit("reserved-output:attempt.json", result_reservation)

    success = baseline_module.NewVintage(baseline, OWNED, vintage, ["attempt.json"])
    failure_name = "failed-" + vintage
    failure = baseline_module.NewVintage(baseline, OWNED, failure_name, ["attempt.json"])
    (root / OWNED).mkdir(parents=True, exist_ok=True)
    outcome = execute_frozen(root, baseline, pins)
    outcome["execution"] = {
        "command": "python3 " + RUNNER + " run --vintage " + vintage,
        "runtime": {
            "python": sys.version.split()[0],
            "numpy": __import__("numpy").__version__,
            "shapely": __import__("shapely").__version__,
            "geos": __import__("shapely").geos_version_string,
        },
        "worker_id": os.environ.get("WORLDATLAS_WORKER_ID", "not-recorded"),
        "issue": 1469,
        "baseline_commit": work_commit,
        "runner": {"path": RUNNER, "bytes": len(runner_bytes), "sha256": digest(runner_bytes),
                   "source_base64": base64.b64encode(runner_bytes).decode("ascii")},
        "pin_inventory": {"path": PIN_FILE, "bytes": len(pin_bytes), "sha256": digest(pin_bytes)},
        "shared_helper": {"path": IMMUTABLE_PATH, "commit": work_commit,
                          "bytes": len(helper_raw), "sha256": digest(helper_raw)},
        "subject_ids": sorted(SUBJECTS),
        "geographic_status": "indexed overlap reproduction only; coastline completeness, legal boundaries, hierarchy approval, import and publication remain unresolved",
    }
    summary = {
        "status": outcome["status"],
        "vintage": vintage if outcome["status"] == "complete" else failure_name,
        "reports": {name: row["sha256"] for name, row in outcome.get("outputs", {}).items()},
    }
    outcome["runner_process"] = {
        "exit_code": 0 if outcome["status"] == "complete" else 1,
        "stdout": stable_json(summary).decode() if outcome["status"] == "complete" else "",
        "stderr": "" if outcome["status"] == "complete" else "FAILED: complete failure receipt retained at " + failure_name + "\n",
    }
    outcome["resource_accounting"]["reserved_output_bytes"] = result_reservation
    outcome["resource_accounting"]["issue_cap_bytes"] = ISSUE_OPERATION_CAP
    outcome["resource_accounting"]["complete_operation_bytes_including_receipt"] = 0
    operation_bytes = 0
    for _ in range(4):
        operation_bytes = sum(baseline.consumed.values()) + len(stable_json(outcome)) + 4096
        if outcome["resource_accounting"]["complete_operation_bytes_including_receipt"] == operation_bytes:
            break
        outcome["resource_accounting"]["complete_operation_bytes_including_receipt"] = operation_bytes
    operation_bytes = sum(baseline.consumed.values()) + len(stable_json(outcome)) + 4096
    outcome["resource_accounting"]["complete_operation_bytes_including_receipt"] = operation_bytes
    if operation_bytes > ISSUE_OPERATION_CAP:
        fail("complete operation exceeds issue 1469's 234,809,776-byte admission")
    payload = stable_json(outcome)
    if len(payload) > result_reservation:
        fail("complete attempt exceeds its pre-computation output reservation")
    try:
        if outcome["status"] == "complete":
            success.publish_bytes({"attempt.json": payload})
            print(outcome["runner_process"]["stdout"], end="")
            return 0
        failure.publish_bytes({"attempt.json": payload})
        print("FAILED: complete failure receipt retained at " + failure_name, file=sys.stderr)
        return 1
    except BaseException as exc:
        # Preserve a failure record in a separately pre-admitted destination if
        # whole-run publication fails after the original calculation completed.
        failed = dict(outcome)
        failed["status"] = "failed"
        failed["publication_failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        failed["runner_process"] = {
            "exit_code": 1,
            "stdout": "",
            "stderr": "FAILED: publication failure receipt retained at " + failure_name + "\n",
        }
        failure.publish_bytes({"attempt.json": stable_json(failed)})
        print("FAILED: publication failure receipt retained at " + failure_name, file=sys.stderr)
        return 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    run = sub.add_parser("run", help="execute frozen coverage code and publish a complete new vintage")
    run.add_argument("--vintage", required=True)
    check = sub.add_parser("check", help="validate a retained successful complete vintage without writing")
    check.add_argument("--vintage", required=True)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[3]
    if args.action == "run":
        return run_vintage(root, args.vintage)
    print(stable_json(verify_vintage(root, args.vintage)).decode(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
