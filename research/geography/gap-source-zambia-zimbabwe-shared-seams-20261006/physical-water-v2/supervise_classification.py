#!/usr/bin/env python3
"""Fail-closed process-group monitor for an explicitly authorized GIS run.

The 640 MiB supervisor stop leaves 60 MiB below the producer's unchanged
700 MiB abort and the requested 768 MiB window. Samples are every 250 ms;
no userspace sampler can bound transient allocations between samples.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


POLL_SECONDS = 0.25
SUPERVISOR_STOP_MIB = 640
PRODUCER_ABORT_MIB = 700
REQUESTED_WINDOW_MIB = 768
MIN_HOST_FREE_PERCENT = 40
TERM_GRACE_SECONDS = 2.0
MAX_LOG_FILE_BYTES = 1 * 1024 * 1024


def parse_host_free_percent(output: str) -> int:
    match = re.search(r"System-wide memory free percentage:\s*(\d+)%", output)
    if not match:
        raise RuntimeError("Could not read system-wide free-memory percentage")
    return int(match.group(1))


def sample_host_free_percent() -> int:
    completed = subprocess.run(
        ["/usr/bin/memory_pressure"],
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )
    return parse_host_free_percent(completed.stdout + completed.stderr)


def process_group_rss_mib(pgid: int) -> tuple[float, int]:
    completed = subprocess.run(
        ["/bin/ps", "-axo", "pid=,pgid=,rss="],
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )
    total_kib = 0
    count = 0
    for line in completed.stdout.splitlines():
        fields = line.split()
        if len(fields) != 3:
            continue
        try:
            _, row_pgid, rss_kib = map(int, fields)
        except ValueError:
            continue
        if row_pgid == pgid:
            total_kib += rss_kib
            count += 1
    return total_kib / 1024.0, count


def load_authorization(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "issue": 1234,
        "authorized": True,
        "requested_window_mib": REQUESTED_WINDOW_MIB,
        "producer_abort_mib": PRODUCER_ABORT_MIB,
        "minimum_host_free_percent": MIN_HOST_FREE_PERCENT,
    }
    for key, expected in required.items():
        if record.get(key) != expected:
            raise RuntimeError(f"GIS window authorization must record {key}={expected!r}")
    wall = record.get("maximum_wall_seconds")
    if not isinstance(wall, (int, float)) or wall <= 0:
        raise RuntimeError("GIS window authorization must give a positive maximum_wall_seconds")
    return record


def terminate_group(process: subprocess.Popen, pgid: int) -> str:
    if process.poll() is not None:
        return "leader-already-exited"
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        return "already-exited"
    except PermissionError:
        if process.poll() is not None:
            return "leader-exited-during-group-signal"
        process.terminate()
        try:
            process.wait(timeout=TERM_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
        return "group-signal-denied; leader-only-fallback"
    deadline = time.monotonic() + TERM_GRACE_SECONDS
    while time.monotonic() < deadline:
        if process.poll() is not None:
            break
        time.sleep(0.05)
    try:
        os.killpg(pgid, signal.SIGKILL)
        return "SIGTERM-then-SIGKILL"
    except ProcessLookupError:
        return "SIGTERM"


def supervise(
    command: list[str],
    authorization: dict,
    log_dir: Path,
    *,
    rss_sampler=process_group_rss_mib,
    host_sampler=sample_host_free_percent,
    clock=time.monotonic,
    sleeper=time.sleep,
) -> dict:
    if not command:
        raise RuntimeError("No producer command was supplied")
    if log_dir.exists():
        raise RuntimeError(f"Refusing to overwrite supervisor log directory: {log_dir}")
    initial_free = host_sampler()
    if initial_free < MIN_HOST_FREE_PERCENT:
        raise RuntimeError(
            f"GIS run not launched: host free memory is {initial_free}%, below the fixed {MIN_HOST_FREE_PERCENT}% gate"
        )
    log_dir.mkdir(parents=True, exist_ok=False)
    samples_path = log_dir / "samples.jsonl"
    stdout_path = log_dir / "producer.stdout.log"
    stderr_path = log_dir / "producer.stderr.log"
    started_utc = datetime.now(timezone.utc).isoformat()
    started = clock()
    max_wall = float(authorization["maximum_wall_seconds"])
    max_rss = 0.0
    max_group_count = 0
    reason = "producer-exit"
    termination = "none"
    exit_code: int | None = None
    first_sample = True

    with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr, samples_path.open("x", encoding="utf-8") as samples:
        process = subprocess.Popen(command, stdout=stdout, stderr=stderr, start_new_session=True)
        pgid = process.pid
        try:
            while True:
                now = clock()
                elapsed = now - started
                rss_mib, group_count = rss_sampler(pgid)
                host_free = host_sampler()
                max_rss = max(max_rss, rss_mib)
                max_group_count = max(max_group_count, group_count)
                sample = {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "elapsed_seconds": round(elapsed, 3),
                    "process_group_rss_mib": round(rss_mib, 3),
                    "process_group_process_count": group_count,
                    "host_free_percent": host_free,
                    "thresholds": {
                        "supervisor_stop_mib": SUPERVISOR_STOP_MIB,
                        "producer_abort_mib": PRODUCER_ABORT_MIB,
                        "host_free_min_percent": MIN_HOST_FREE_PERCENT,
                        "wall_seconds": max_wall,
                    },
                }
                samples.write(json.dumps(sample, sort_keys=True) + "\n")
                samples.flush()
                if first_sample:
                    first_sample = False
                if process.poll() is not None:
                    exit_code = process.returncode
                    if stdout_path.stat().st_size > MAX_LOG_FILE_BYTES or stderr_path.stat().st_size > MAX_LOG_FILE_BYTES:
                        reason = "producer-log-file-exceeded-1-mib"
                    break
                if stdout_path.stat().st_size > MAX_LOG_FILE_BYTES or stderr_path.stat().st_size > MAX_LOG_FILE_BYTES:
                    reason = "producer-log-file-exceeded-1-mib"
                    termination = terminate_group(process, pgid)
                    exit_code = process.wait()
                    break
                if rss_mib >= PRODUCER_ABORT_MIB:
                    reason = "producer-rss-abort-700-mib"
                elif rss_mib >= SUPERVISOR_STOP_MIB:
                    reason = "supervisor-rss-stop-640-mib"
                elif host_free < MIN_HOST_FREE_PERCENT:
                    reason = "host-free-memory-below-40-percent"
                elif elapsed >= max_wall:
                    reason = "authorized-wall-time-expired"
                if reason != "producer-exit":
                    termination = terminate_group(process, pgid)
                    exit_code = process.wait()
                    break
                sleeper(POLL_SECONDS)
        except BaseException:
            terminate_group(process, pgid)
            process.wait()
            raise

    ended = clock()
    result = {
        "version": 1,
        "result": "completed" if reason == "producer-exit" and exit_code == 0 else "stopped-or-failed",
        "reason": reason,
        "command": command,
        "started_at_utc": started_utc,
        "elapsed_seconds": round(ended - started, 3),
        "exit_code": exit_code,
        "maximum_sampled_process_group_rss_mib": round(max_rss, 3),
        "maximum_sampled_process_group_process_count": max_group_count,
        "initial_host_free_percent": initial_free,
        "supervisor_stop_mib": SUPERVISOR_STOP_MIB,
        "producer_abort_mib": PRODUCER_ABORT_MIB,
        "requested_window_mib": REQUESTED_WINDOW_MIB,
        "minimum_host_free_percent": MIN_HOST_FREE_PERCENT,
        "maximum_bytes_per_producer_log": MAX_LOG_FILE_BYTES,
        "poll_interval_seconds": POLL_SECONDS,
        "sampling_overshoot_limit": "A 250 ms poll interval is the nominal observation cadence, not a hard memory-growth or log-write bound. ps/memory_pressure calls, OS scheduling, and SIGTERM/SIGKILL delivery add latency; a fast allocation spike can exceed 640 MiB or 700 MiB between samples, and fast log output can cross 1 MiB between file-size checks. The producer's own 700 MiB checks remain enabled as a second guard.",
        "termination": termination,
        "logs": {
            "samples": samples_path.name,
            "stdout": stdout_path.name,
            "stderr": stderr_path.name,
        },
    }
    (log_dir / "supervisor-summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def self_test() -> dict:
    """Exercise allow, memory-stop, host-stop, and wall-time paths with synthetic samples."""
    if sys.platform != "darwin":
        raise RuntimeError("Supervisor self-test expects the macOS process-group interface")
    auth = {"issue": 1234, "authorized": True, "requested_window_mib": 768, "producer_abort_mib": 700, "minimum_host_free_percent": 40, "maximum_wall_seconds": 5}
    cases = []
    with tempfile.TemporaryDirectory(prefix="worldcover-supervisor-test-") as temporary:
        root = Path(temporary)
        ok = supervise(
            [sys.executable, "-c", "print('synthetic supervisor control')"], auth, root / "allow",
            rss_sampler=lambda _: (32.0, 1), host_sampler=lambda: 55,
        )
        if ok["result"] != "completed" or ok["exit_code"] != 0:
            raise RuntimeError("Supervisor allow-path self-test failed")
        cases.append("synthetic child completed and produced logs")

        stopping_samples = iter([(641.0, 1)])
        stopped = supervise(
            [sys.executable, "-c", "import time; time.sleep(20)"], auth, root / "rss-stop",
            rss_sampler=lambda _: next(stopping_samples), host_sampler=lambda: 55,
        )
        if stopped["reason"] != "supervisor-rss-stop-640-mib" or stopped["exit_code"] == 0:
            raise RuntimeError("Supervisor RSS-stop self-test failed")
        cases.append("640 MiB supervisory margin terminates the process group")

        host_samples = iter([55, 39])
        stopped_host = supervise(
            [sys.executable, "-c", "import time; time.sleep(20)"], auth, root / "host-stop",
            rss_sampler=lambda _: (32.0, 1), host_sampler=lambda: next(host_samples),
        )
        if stopped_host["reason"] != "host-free-memory-below-40-percent":
            raise RuntimeError("Supervisor host-pressure self-test failed")
        cases.append("host free-memory decline terminates the process group")

        short_auth = {**auth, "maximum_wall_seconds": 0.03}
        stopped_time = supervise(
            [sys.executable, "-c", "import time; time.sleep(20)"], short_auth, root / "wall-stop",
            rss_sampler=lambda _: (32.0, 1), host_sampler=lambda: 55,
        )
        if stopped_time["reason"] != "authorized-wall-time-expired":
            raise RuntimeError("Supervisor wall-time self-test failed")
        cases.append("authorized wall-time limit terminates the process group")

        large_log = supervise(
            [sys.executable, "-c", "import sys; sys.stdout.write('x' * (2 * 1024 * 1024))"], auth, root / "log-cap",
            rss_sampler=lambda _: (32.0, 1), host_sampler=lambda: 55,
        )
        if large_log["reason"] != "producer-log-file-exceeded-1-mib":
            raise RuntimeError("Supervisor log-cap self-test failed")
        cases.append("oversized producer log is stopped and capped near 1 MiB per stream")

    if parse_host_free_percent("System-wide memory free percentage: 41%\n") != 41:
        raise RuntimeError("Host-pressure parser self-test failed")
    return {"result": "passed", "cases": cases, "source_pixels_read": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization", type=Path, help="root-issued GIS window authorization JSON")
    parser.add_argument("--log-dir", type=Path, help="new directory for sample, stdout, stderr, and summary logs")
    parser.add_argument("--self-test", action="store_true", help="exercise synthetic children; reads no raster pixels")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="producer command after --")
    args = parser.parse_args()
    if args.self_test:
        if args.authorization or args.log_dir or args.command:
            parser.error("--self-test cannot be combined with a launch request")
        print(json.dumps(self_test(), indent=2))
        return 0
    if not args.authorization or not args.log_dir or not args.command or args.command[0] != "--":
        parser.error("launch requires --authorization FILE --log-dir NEW_DIR -- COMMAND...")
    try:
        authorization = load_authorization(args.authorization)
        result = supervise(args.command[1:], authorization, args.log_dir)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"supervisor refused or failed closed: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
