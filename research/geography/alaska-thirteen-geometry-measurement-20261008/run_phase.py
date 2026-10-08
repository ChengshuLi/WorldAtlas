#!/usr/bin/env python3
"""Run one admitted bounded phase with sampled cooperative process limits."""
from __future__ import annotations

import json
import hashlib
import os
import pathlib
import re
import signal
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]
CAMPAIGN = ROOT / "research/geography/alaska-thirteen-geometry-measurement-20261008"
RSS_CAP = 805_306_368
WALL_CAP = 900


def group_state(group: int, own_pid: int) -> tuple[int, list[dict]]:
    result = subprocess.run(["ps", "-axo", "pid=,pgid=,rss="], capture_output=True, text=True, check=True)
    total = 0
    members = []
    for line in result.stdout.splitlines():
        bits = line.split()
        if len(bits) == 3 and bits[1].isdigit() and int(bits[1]) == group and bits[2].isdigit():
            total += int(bits[2]) * 1024
            members.append({"pid": int(bits[0]), "rss_bytes": int(bits[2]) * 1024})
    own = subprocess.run(["ps", "-o", "rss=", "-p", str(own_pid)], capture_output=True, text=True)
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
    argv = sys.argv[1:]
    if argv and argv[0] == "--":
        argv = argv[1:]
    if not argv:
        raise SystemExit("usage: run_phase.py -- COMMAND [ARGS ...]")
    phase_target = next((arg for arg in reversed(argv) if arg.endswith(".py")), argv[0])
    phase_name = pathlib.Path(phase_target).stem.replace("_", "-")
    phase = json.loads((CAMPAIGN / "phase-admission.json").read_text())
    if phase.get("status") != "PASS" or phase.get("complete_phase_bytes", RSS_CAP + 1) > 268_435_456:
        raise SystemExit("complete phase admission is missing or failed")
    for descriptor in phase.get("inputs", []) + phase.get("project_code", []):
        path = ROOT / descriptor["path"]
        if path.is_symlink() or not path.is_file():
            raise SystemExit(f"phase admission input is missing or not an ordinary file: {descriptor['path']}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if path.stat().st_size != descriptor["bytes"] or digest != descriptor["sha256"]:
            raise SystemExit(f"phase admission is stale for {descriptor['path']}; rerun admission")
    node = pathlib.Path("/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node")
    workspace_check = subprocess.run([str(node), "scripts/local-workspace.mjs", "check"],
                                      cwd=ROOT, capture_output=True, text=True)
    if workspace_check.returncode != 0:
        raise SystemExit("managed-workspace storage/reservation guard failed; no phase launched")
    start = time.monotonic()
    process = subprocess.Popen(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, start_new_session=True)
    group = process.pid
    print(json.dumps({"phase_pid": process.pid, "process_group": group,
                      "command": argv, "rss_cap_bytes": RSS_CAP,
                      "wall_deadline_seconds": WALL_CAP}), flush=True)
    peak = 0
    stop_reason = None
    while process.poll() is None:
        sample, _ = group_state(group, os.getpid())
        peak = max(peak, sample)
        elapsed = time.monotonic() - start
        if sample > RSS_CAP:
            stop_reason = "sampled_process_group_rss_cap"
            terminate_group(group)
            break
        if elapsed > WALL_CAP:
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
    elapsed = round(time.monotonic() - start, 3)
    terminal = process.poll() is not None
    final_rss, members = group_state(group, os.getpid()) if terminal else (None, None)
    if members:
        terminate_group(group)
        _, members = group_state(group, os.getpid())
        stop_reason = stop_reason or "descendant_processes_remained_after_leader_exit"
    result = {
        "version": 1,
        "pid": process.pid,
        "process_group": group,
        "command": argv,
        "exit_code": process.returncode,
        "natural_terminal": stop_reason is None and terminal,
        "owned_processes_absent_after_run": not members,
        "stop_reason": stop_reason,
        "elapsed_seconds": elapsed,
        "peak_sampled_group_rss_bytes": peak,
        "final_sampled_group_rss_bytes": final_rss,
        "rss_cap_bytes": RSS_CAP,
        "wall_deadline_seconds": WALL_CAP,
        "monitoring": "sampled/cooperative, not kernel-enforced",
        "stdout": stdout,
        "stderr": stderr,
    }
    receipt_name = os.environ.get("CODEX_PHASE_RECEIPT_NAME", phase_name)
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", receipt_name):
        raise ValueError("unsafe operating receipt name")
    receipt = CAMPAIGN / "execution" / f"{receipt_name}-operating-receipt.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    if receipt.exists():
        raise RuntimeError(f"refusing to overwrite prior operating receipt: {receipt.name}")
    receipt.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("exit_code", "natural_terminal", "stop_reason",
          "elapsed_seconds", "peak_sampled_group_rss_bytes", "rss_cap_bytes", "wall_deadline_seconds")}))
    if stdout:
        print(stdout, end="")
    if stderr:
        print(stderr, file=sys.stderr, end="")
    return process.returncode if process.returncode is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
