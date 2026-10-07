#!/usr/bin/env python3
"""Exercise the corrected actual CLI with isolated, hard-linked fixtures."""
import hashlib
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parents[1]
CONTROLS = HERE / "controls"
FIXTURES = CONTROLS / "corrected-runner-fixtures"
LOGS = CONTROLS / "corrected-runner-logs"
CAPSULE = "inputs/code/capsule-reproduce.py"


def ensure_scratch_roots():
    control_root = CONTROLS.resolve()
    if CONTROLS.is_symlink() or control_root != CONTROLS.absolute():
        raise ValueError("unsafe control root")
    for scratch in (FIXTURES, LOGS):
        if (scratch.is_symlink() or scratch.parent.resolve() != control_root or
                (scratch.exists() and not scratch.is_dir())):
            raise ValueError("unsafe fixture/log scratch root")


def prepare_logdir(name):
    ensure_scratch_roots()
    if not name or name in (".", "..") or "/" in name or "\\" in name:
        raise ValueError("control-log name must be one plain child name")
    candidate, suffix = name, 1
    while True:
        logs = LOGS / candidate
        if logs.is_symlink() or logs.exists():
            candidate = name + "-" + str(suffix)
            suffix += 1
            continue
        if logs.parent.resolve() != LOGS.resolve():
            raise ValueError("unsafe control-log path")
        logs.mkdir()
        return logs


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def link_file(source, target):
    os.link(source, target)


def fixture(name):
    ensure_scratch_roots()
    if not name or name in (".", "..") or "/" in name or "\\" in name:
        raise ValueError("fixture name must be one plain child name")
    root = FIXTURES / name
    if root.is_symlink() or root.parent.resolve() != FIXTURES.resolve():
        raise ValueError("unsafe fixture path")
    if root.exists():
        if not root.is_dir():
            raise ValueError("fixture path is not a directory")
        shutil.rmtree(root)
    root.mkdir(parents=True)
    shutil.copytree(HERE / "inputs", root / "inputs", copy_function=link_file)
    shutil.copy2(HERE / "reproduce.py", root / "reproduce.py")
    (root / "outputs").mkdir()
    return root


def replace(path, raw):
    temporary = path.with_name(path.name + ".replacement")
    temporary.write_bytes(raw)
    temporary.replace(path)


def run(name, mutate=None, output="attempt", expected=1, extra=()):
    root = fixture(name)
    if mutate:
        mutate(root)
    command = [sys.executable, str(root / "reproduce.py"), "--output", output, *extra]
    process = subprocess.run(command, cwd=root, text=True, capture_output=True)
    logs = prepare_logdir(name)
    (logs / "stdout.txt").write_text(process.stdout)
    (logs / "stderr.txt").write_text(process.stderr)
    return root, process, {"case": name, "exit_code": process.returncode,
        "expected_exit_code": expected, "stdout_sha256": digest(process.stdout.encode()),
        "stderr_sha256": digest(process.stderr.encode()), "stdout_bytes": len(process.stdout.encode()),
        "stderr_bytes": len(process.stderr.encode()), "command": command,
        "logs_path": logs.relative_to(CONTROLS).as_posix()}


def manifest(root):
    path = root / "inputs/original-manifest.json"
    return path, json.loads(path.read_text())


def remove_capsule_pin(root):
    path, value = manifest(root)
    del value["capsule"][CAPSULE]
    replace(path, json.dumps(value, sort_keys=True).encode() + b"\n")


def alter_capsule(root, refresh=False):
    target = root / CAPSULE
    raw = target.read_bytes() + b"\nopen(sys.argv[1] + '/audit-unreviewed-code.txt','w').write('probe')\n"
    replace(target, raw)
    if refresh:
        path, value = manifest(root)
        value["capsule"][CAPSULE] = digest(raw)
        replace(path, json.dumps(value, sort_keys=True).encode() + b"\n")


def wrong_input(root):
    path = root / "inputs/baseline/data-world-index.json"
    replace(path, path.read_bytes() + b" ")


def existing_sentinel(root):
    target = root / "outputs/attempt"
    target.mkdir()
    (target / "sentinel.txt").write_text("retain")


def broken_symlink(root):
    (root / "outputs/attempt").symlink_to(root / "not-present")


def symlink_parent(root):
    outside = root / "outside"
    outside.mkdir()
    (root / "outputs").rmdir()
    (root / "outputs").symlink_to(outside, target_is_directory=True)


def replace_after_validation(root):
    target = root / CAPSULE
    raw = target.read_bytes() + b"\nopen(sys.argv[1] + '/audit-unreviewed-code.txt','w').write('probe')\n"
    replace(target, raw)
    input_path = root / "inputs/baseline/data-world-index.json"
    replace(input_path, input_path.read_bytes() + b" ")


def check_scratch_symlink_parents():
    probe = Path(tempfile.mkdtemp(prefix="fixture-safety-probe-", dir=str(CONTROLS)))
    outside = probe / "outside"
    victim = outside / "missing-executable-pin"
    outside.mkdir()
    victim.mkdir()
    sentinel = victim / "sentinel.txt"
    sentinel.write_text("retain")
    sentinel_hash = digest(sentinel.read_bytes())
    link = probe / "scratch-link"
    link.symlink_to(outside, target_is_directory=True)
    original_fixtures, original_logs = FIXTURES, LOGS
    fixture_rejected = False
    verifier_log_rejected = False
    reproduction_log_rejected = False
    try:
        globals()["FIXTURES"] = link
        try:
            fixture("missing-executable-pin")
        except ValueError:
            fixture_rejected = True
        globals()["FIXTURES"] = original_fixtures
        globals()["LOGS"] = link
        try:
            ensure_scratch_roots()
        except ValueError:
            verifier_log_rejected = True
        previous_bytecode = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            spec = importlib.util.spec_from_file_location("artigas_reproduction_harness", CONTROLS / "reproduce_corrected_runner.py")
            harness = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(harness)
        finally:
            sys.dont_write_bytecode = previous_bytecode
        harness.LOGS = link
        try:
            harness.ensure_scratch_roots()
        except ValueError:
            reproduction_log_rejected = True
    finally:
        globals()["FIXTURES"] = original_fixtures
        globals()["LOGS"] = original_logs
    sentinel_ok = sentinel.is_file() and digest(sentinel.read_bytes()) == sentinel_hash
    shutil.rmtree(probe)
    return {"case": "fixture-and-log-symlink-parents-rejected",
            "fixture_parent_rejected": fixture_rejected,
            "verifier_log_parent_rejected": verifier_log_rejected,
            "reproduction_log_parent_rejected": reproduction_log_rejected,
            "external_sentinel_sha256": sentinel_hash,
            "external_sentinel_preserved": sentinel_ok,
            "stdout_sha256": digest(b""), "stderr_sha256": digest(b"")}


def main():
    ensure_scratch_roots()
    FIXTURES.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    original_manifest = json.loads((HERE / "inputs/original-manifest.json").read_text())
    original_pins = {}
    for rel, expected in original_manifest["capsule"].items():
        path = HERE / ("inputs/code/original-wrapper.py" if rel == "reproduce.py" else rel)
        original_pins[rel] = digest(path.read_bytes())
        if original_pins[rel] != expected:
            raise AssertionError("original packet pin mismatch before control: " + rel)
    original_pins["issue-1413-api.json"] = digest((HERE / "inputs/issue-1413-api.json").read_bytes())
    cases = []
    for name, mutate in [
        ("missing-executable-pin", remove_capsule_pin),
        ("altered-code-unchanged-manifest", lambda root: alter_capsule(root)),
        ("coherently-refreshed-manifest", lambda root: alter_capsule(root, True)),
        ("wrong-complete-input", wrong_input),
        ("existing-output-sentinel", existing_sentinel),
        ("broken-symlink", broken_symlink),
        ("symlink-parent-escape", symlink_parent),
    ]:
        root, process, row = run(name, mutate)
        row["destination_created"] = (root / "outputs/attempt").exists() and not (root / "outputs/attempt").is_symlink()
        row["probe_created"] = (root / "outputs/attempt/audit-unreviewed-code.txt").exists()
        row["output_names"] = sorted(p.name for p in (root / "outputs").iterdir())
        if name == "existing-output-sentinel":
            row["sentinel_sha256"] = digest((root / "outputs/attempt/sentinel.txt").read_bytes())
        if process.returncode != 1 or (name != "existing-output-sentinel" and row["destination_created"]) or row["probe_created"]:
            raise AssertionError("rejected fixture mutated output: " + name)
        if name == "existing-output-sentinel" and row["sentinel_sha256"] != digest(b"retain"):
            raise AssertionError("sentinel changed")
        cases.append(row)
    root = fixture("replacement-after-validation")
    spec = importlib.util.spec_from_file_location("artigas_corrected_runner", root / "reproduce.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    original_destination = runner.destination
    def mutate_after_capture(name):
        replace_after_validation(root)
        return original_destination(name)
    runner.destination = mutate_after_capture
    previous_argv = sys.argv
    stdout, stderr = io.StringIO(), io.StringIO()
    try:
        sys.argv = [str(root / "reproduce.py"), "--output", "attempt"]
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            runner.main()
    finally:
        sys.argv = previous_argv
    out = root / "outputs/attempt"
    race_row = {"case": "capsule-and-input-replaced-after-validation",
                "exit_code": 0, "expected_exit_code": 0,
                "capsule_sha256_after_replacement": digest((root / CAPSULE).read_bytes()),
                "input_sha256_after_replacement": digest((root / "inputs/baseline/data-world-index.json").read_bytes()),
                "retained_report_sha256": digest((out / "reproduction-results.json").read_bytes()),
                "success_receipt_exists": (out / "publication.json").is_file(),
                "probe_created": (out / "audit-unreviewed-code.txt").exists(),
                "stdout_sha256": digest(stdout.getvalue().encode()),
                "stderr_sha256": digest(stderr.getvalue().encode()),
                "stdout_bytes": len(stdout.getvalue().encode()),
                "stderr_bytes": len(stderr.getvalue().encode()),
                "execution": "actual reproduce.py main() with capsule/input paths replaced by the destination-admission hook after validate() returned"}
    logs = prepare_logdir("capsule-and-input-replaced-after-validation")
    race_row["logs_path"] = logs.relative_to(CONTROLS).as_posix()
    (logs / "stdout.txt").write_text(stdout.getvalue())
    (logs / "stderr.txt").write_text(stderr.getvalue())
    if race_row["retained_report_sha256"] != "3970173b2c2050c1099ec427e4d64076e96a3000635ba20db203fa204320e44a" or not race_row["success_receipt_exists"] or race_row["probe_created"]:
        raise AssertionError("runner did not consume the captured code/input bytes")
    cases.append(race_row)
    root = fixture("publication-sync-failure")
    spec = importlib.util.spec_from_file_location("artigas_sync_failure_runner", root / "reproduce.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    original_fsync = os.fsync
    sync_calls = []
    def fail_publication_sync(fd):
        sync_calls.append(fd)
        if len(sync_calls) == 2:
            raise OSError("directed publication receipt fsync failure")
        return original_fsync(fd)
    previous_argv = sys.argv
    stdout, stderr = io.StringIO(), io.StringIO()
    error = None
    try:
        sys.argv = [str(root / "reproduce.py"), "--output", "attempt"]
        os.fsync = fail_publication_sync
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                runner.main()
            except OSError as exc:
                error = str(exc)
    finally:
        os.fsync = original_fsync
        sys.argv = previous_argv
    out = root / "outputs/attempt"
    sync_row = {"case": "publication-receipt-sync-failure", "exit_code": 1,
                "expected_exit_code": 1, "fsync_calls": len(sync_calls),
                "error": error, "report_exists": (out / "reproduction-results.json").is_file(),
                "failure_exists": (out / "failure.json").is_file(),
                "publication_exists": (out / "publication.json").exists(),
                "output_names": sorted(p.name for p in out.iterdir()),
                "failure": json.loads((out / "failure.json").read_text()) if (out / "failure.json").is_file() else None,
                "stdout_sha256": digest(stdout.getvalue().encode()),
                "stderr_sha256": digest(stderr.getvalue().encode()),
                "execution": "actual reproduce.py main() with os.fsync forced to fail on publication temp file after report sync"}
    logs = prepare_logdir("publication-receipt-sync-failure")
    sync_row["logs_path"] = logs.relative_to(CONTROLS).as_posix()
    (logs / "stdout.txt").write_text(stdout.getvalue())
    (logs / "stderr.txt").write_text(stderr.getvalue())
    if (error != "directed publication receipt fsync failure" or len(sync_calls) != 3 or
            not sync_row["report_exists"] or not sync_row["failure_exists"] or
            sync_row["publication_exists"] or sync_row["output_names"] != ["failure.json", "reproduction-results.json"]):
        raise AssertionError("publication sync failure exposed a success receipt or unsafe output")
    cases.append(sync_row)
    scratch_row = check_scratch_symlink_parents()
    if (not scratch_row["fixture_parent_rejected"] or
            not scratch_row["verifier_log_parent_rejected"] or
            not scratch_row["reproduction_log_parent_rejected"] or
            not scratch_row["external_sentinel_preserved"]):
        raise AssertionError("control harness accepted a symlinked scratch parent")
    cases.append(scratch_row)
    logs = prepare_logdir("fixture-and-log-symlink-parents-rejected")
    scratch_row["logs_path"] = logs.relative_to(CONTROLS).as_posix()
    (logs / "stdout.txt").write_text("")
    (logs / "stderr.txt").write_text("")
    root, process, row = run("traversal", output="../escape")
    row["escape_created"] = (root.parent / "escape").exists()
    row["outputs"] = sorted(p.name for p in (root / "outputs").iterdir())
    if process.returncode != 1 or row["escape_created"] or row["outputs"]:
        raise AssertionError("traversal fixture was not rejected safely")
    cases.append(row)
    root, process, row = run("failure-after-compute", expected=1, extra=("--fail-after-compute",))
    out = root / "outputs/attempt"
    row["retained_report_sha256"] = digest((out / "reproduction-results.json").read_bytes())
    row["failure_record"] = json.loads((out / "failure.json").read_text())
    row["success_receipt_exists"] = (out / "publication.json").exists()
    if process.returncode != 1 or row["success_receipt_exists"] or row["retained_report_sha256"] != "3970173b2c2050c1099ec427e4d64076e96a3000635ba20db203fa204320e44a":
        raise AssertionError("failed run lacks durable failure state")
    cases.append(row)
    after_pins = {}
    for rel in original_manifest["capsule"]:
        path = HERE / ("inputs/code/original-wrapper.py" if rel == "reproduce.py" else rel)
        after_pins[rel] = digest(path.read_bytes())
    after_pins["issue-1413-api.json"] = digest((HERE / "inputs/issue-1413-api.json").read_bytes())
    if after_pins != original_pins:
        raise AssertionError("original issue/source/code closure changed during controls")
    audit = {"version": 1, "issue": 1413, "originals_unchanged": after_pins,
             "cases": cases, "runtime": {"python": sys.version, "executable": sys.executable},
             "limits": ["Fixtures use hard links for unchanged inputs; changed manifest/code/input paths are atomically replaced before invocation.",
                        "The directed race hook replaces both executable and consumed input paths after validation; the runner still executes and reads the captured byte values.",
                        "The publication failure control injects an fsync error immediately before atomic success-receipt publication; no publication receipt appears.",
                        "The probes write only inside their isolated fixture output directory; generated fixture copies are removed after the retained outcome records are written."]}
    (CONTROLS / "corrected-runner-audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")
    shutil.rmtree(FIXTURES)
    print(json.dumps({"cases": len(cases), "originals_unchanged": after_pins,
                      "all_adverse_cases_safe": True,
                      "retained_failure_without_success_receipt": True}, sort_keys=True))


if __name__ == "__main__":
    main()
