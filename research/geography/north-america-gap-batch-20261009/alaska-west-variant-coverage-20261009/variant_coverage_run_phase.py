#!/usr/bin/env python3
"""Run one admitted four-candidate source-coverage phase under 512 MiB RSS."""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import signal
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[4]
PACKET = ROOT / "research/geography/north-america-gap-batch-20261009/alaska-west-variant-coverage-20261009"
PHASE = PACKET / "phase-admission.json"
RSS_CAP = 512 * 1024 * 1024
PHASE_CAP = 256 * 1024 * 1024
WALL_CAP = 900
NODE = "/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node"
PYTHON = "/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"
DRIVER = PACKET / "variant_coverage_driver.py"
RECEIPT = PACKET / "execution" / "coverage-run-20261010-01-operating-receipt.json"


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def atomic_exclusive(path: pathlib.Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name("." + path.name + ".incomplete")
    with temporary.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.link(temporary, path)
    temporary.unlink()


def process_usage(process_group: int, self_pid: int) -> tuple[int, list[dict]]:
    result = subprocess.run(["ps", "-axo", "pid=,pgid=,rss="], capture_output=True, text=True, check=True)
    total = 0
    members = []
    for line in result.stdout.splitlines():
        bits = line.split()
        if len(bits) == 3 and bits[0].isdigit() and bits[1].isdigit() and bits[2].isdigit():
            pid, group, rss = int(bits[0]), int(bits[1]), int(bits[2]) * 1024
            if group == process_group:
                total += rss
                members.append({"pid": pid, "rss_bytes": rss})
    own = subprocess.run(["ps", "-o", "rss=", "-p", str(self_pid)], capture_output=True, text=True)
    if own.stdout.strip().isdigit():
        total += int(own.stdout.strip()) * 1024
    return total, members


def terminate_group(group: int) -> None:
    try:
        os.killpg(group, signal.SIGTERM)
    except ProcessLookupError:
        return
    time.sleep(0.5)
    try:
        os.killpg(group, signal.SIGKILL)
    except ProcessLookupError:
        pass


def main() -> int:
    if PHASE.is_symlink() or not PHASE.is_file():
        raise SystemExit("phase-admission.json is absent or not an ordinary file")
    phase_raw = PHASE.read_bytes()
    phase = json.loads(phase_raw)
    if (phase.get("status") != "PASS" or phase.get("scientific_operations_invoked") is not False
            or phase.get("cap_bytes") != PHASE_CAP or phase.get("max_process_bytes") != RSS_CAP
            or phase.get("complete_phase_bytes", PHASE_CAP + 1) > PHASE_CAP):
        raise SystemExit("phase admission or operating caps are invalid")
    if len(phase_raw) > 32 * 1024 * 1024:
        raise SystemExit("phase admission exceeds 32 MiB member cap")
    for row in phase.get("inputs", []) + phase.get("project_code", []):
        path = ROOT / row["path"]
        if path.is_symlink() or not path.is_file():
            raise SystemExit("admitted path is missing or not an ordinary file: " + row["path"])
        raw = path.read_bytes()
        if len(raw) > 32 * 1024 * 1024 or len(raw) != row["bytes"] or digest(raw) != row["sha256"]:
            raise SystemExit("admission drift or 32 MiB file cap violation: " + row["path"])
    runtime = phase.get("runtime_file_closure", [])
    seen = set()
    runtime_bytes = 0
    for row in runtime:
        path = pathlib.Path(row["path"])
        resolved = path.resolve(strict=True)
        raw = resolved.read_bytes()
        if (str(resolved) != row["realpath"] or len(raw) > 32 * 1024 * 1024 or len(raw) != row["bytes"] or digest(raw) != row["sha256"]
                or int(resolved.stat().st_mode & 0o777) != row["mode"] or str(resolved) in seen):
            raise SystemExit("runtime closure drift or alias: " + str(path))
        seen.add(str(resolved))
        runtime_bytes += len(raw)
    totals = phase["component_totals"]
    input_bytes = sum(row["bytes"] for row in phase["inputs"])
    project_bytes = sum(row["bytes"] for row in phase["project_code"])
    accounted = sum(row["bytes"] for row in phase["inputs"] + phase["project_code"])
    accounted += runtime_bytes + totals["scratch_reservation"]
    accounted += totals["generated_output_reservation"] + len(phase_raw)
    if (input_bytes != totals["encoded_inputs"] or project_bytes != totals["project_code_files"]
            or runtime_bytes != totals["imported_runtime_files_and_python_executable"]
            or len(phase_raw) != totals["phase_admission_file_bytes"]
            or accounted != phase["complete_phase_bytes"] or accounted > PHASE_CAP):
        raise SystemExit("actual complete inputs/runtime/scratch/output differ from admission or exceed 256 MiB")
    if totals["generated_output_reservation"] > 32 * 1024 * 1024:
        raise SystemExit("generated output reserve exceeds per-member cap")

    check = subprocess.run([NODE, "scripts/local-workspace.mjs", "check"], cwd=ROOT,
                           capture_output=True, text=True)
    if check.returncode:
        raise SystemExit("managed-workspace storage guard failed before phase launch: " + check.stderr[-2000:])
    if RECEIPT.exists() or RECEIPT.is_symlink():
        raise SystemExit("refusing to overwrite prior operating receipt")

    command = [PYTHON, str(DRIVER)]
    started = time.monotonic()
    process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, start_new_session=True)
    group = process.pid
    print(json.dumps({"pid": process.pid, "process_group": group, "command": command,
                      "rss_cap_bytes": RSS_CAP, "phase_cap_bytes": PHASE_CAP,
                      "wall_deadline_seconds": WALL_CAP}), flush=True)
    peak = 0
    stop_reason = None
    while process.poll() is None:
        sample, _ = process_usage(group, os.getpid())
        peak = max(peak, sample)
        if sample > RSS_CAP:
            stop_reason = "sampled_process_and_wrapper_rss_cap"
            terminate_group(group)
            break
        if time.monotonic() - started > WALL_CAP:
            stop_reason = "wall_deadline"
            terminate_group(group)
            break
        time.sleep(0.2)
    try:
        stdout, stderr = process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        terminate_group(group)
        stdout, stderr = process.communicate()
        stop_reason = stop_reason or "terminal_process_timeout"
    elapsed = round(time.monotonic() - started, 3)
    final_rss, members = process_usage(group, os.getpid()) if process.poll() is not None else (None, None)
    if members:
        terminate_group(group)
        _, members = process_usage(group, os.getpid())
        stop_reason = stop_reason or "descendant_processes_remained_after_leader_exit"
    result = {
        "version": 1,
        "status": "complete" if process.returncode == 0 and stop_reason is None else "failed",
        "phase_admission": {"path": str(PHASE.relative_to(ROOT)), "bytes": len(phase_raw), "sha256": digest(phase_raw),
                            "complete_phase_bytes": phase["complete_phase_bytes"], "cap_bytes": PHASE_CAP},
        "pid": process.pid,
        "process_group": group,
        "command": command,
        "exit_code": process.returncode,
        "natural_terminal": stop_reason is None and process.poll() is not None,
        "owned_processes_absent_after_run": not members,
        "stop_reason": stop_reason,
        "elapsed_seconds": elapsed,
        "peak_sampled_process_and_wrapper_rss_bytes": peak,
        "final_sampled_process_and_wrapper_rss_bytes": final_rss,
        "rss_cap_bytes": RSS_CAP,
        "phase_cap_bytes": PHASE_CAP,
        "wall_deadline_seconds": WALL_CAP,
        "monitoring": "sampled/cooperative; not kernel-enforced",
        "stdout": stdout,
        "stderr": stderr,
    }
    raw_receipt = (json.dumps(result, indent=2, ensure_ascii=False) + "\n").encode()
    atomic_exclusive(RECEIPT, raw_receipt)
    print(json.dumps({key: result[key] for key in ("status", "exit_code", "natural_terminal", "stop_reason",
                  "elapsed_seconds", "peak_sampled_process_and_wrapper_rss_bytes", "rss_cap_bytes")}, sort_keys=True))
    if stdout:
        print(stdout, end="")
    if stderr:
        print(stderr, file=sys.stderr, end="")
    return process.returncode if process.returncode is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
