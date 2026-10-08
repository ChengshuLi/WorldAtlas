#!/usr/bin/env python3
"""Externally sample and bound one existing full-scope source overlay run."""
from __future__ import annotations
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import signal
import subprocess
import sys
import time

import producer

OWNED = producer.OWNED
MAX_LOG_BYTES = 1 * 1024 * 1024
MAX_SAMPLE_LOG_BYTES = 4 * 1024 * 1024
MAX_SAMPLES = 13000

def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def wait_child_nonblocking(child):
    pid, status, usage = os.wait4(child.pid, os.WNOHANG)
    if pid == 0:
        return None, None
    child.returncode = os.waitstatus_to_exitcode(status)
    return child.returncode, usage

def stop_and_reap_child(child):
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    deadline = time.monotonic() + 1.0
    while child.returncode is None:
        exit_code, usage = wait_child_nonblocking(child)
        if exit_code is not None:
            return exit_code, usage
        if time.monotonic() >= deadline:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            pid, status, usage = os.wait4(child.pid, 0)
            child.returncode = os.waitstatus_to_exitcode(status)
            return child.returncode, usage
        time.sleep(0.05)
    raise RuntimeError("Child was reaped without retaining its wait4 resource record")

def tree_rss_bytes(root_pid):
    raw = subprocess.check_output(["ps", "-axo", "pid=,ppid=,pgid=,rss="],
                                  text=True, stderr=subprocess.STDOUT)
    rows = {}
    for line in raw.splitlines():
        fields = line.split()
        if len(fields) != 4:
            continue
        pid, ppid, pgid, rss_kib = map(int, fields)
        rows[pid] = (ppid, pgid, rss_kib * 1024)
    # Popen uses start_new_session, so the child PID is also its process group.
    # Keep counting group members if the leader exits before a descendant.
    group = root_pid
    selected = {pid for pid, (_, pgid, _) in rows.items() if pgid == root_pid}
    if root_pid in rows:
        selected.add(root_pid)
    changed = True
    while changed:
        changed = False
        for pid, (ppid, pgid, _) in rows.items():
            if pid not in selected and (ppid in selected or pgid == group):
                selected.add(pid)
                changed = True
    return sum(rows[pid][2] for pid in selected if pid in rows), sorted(selected)

def require_contained_nonsymlink_path(repo, target):
    repo = pathlib.Path(repo).resolve()
    target = pathlib.Path(target)
    if not target.is_absolute():
        target = repo / target
    try:
        relative = target.relative_to(repo)
    except ValueError as exc:
        raise ValueError("Process-supervision destination escapes repository") from exc
    cursor = repo
    if cursor.is_symlink():
        raise ValueError("Repository root is symlinked")
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError("Symlink ancestor in process-supervision destination")
    return target

def write_supervision(folder, receipt, stdout_path, stderr_path, samples_path):
    raw = canonical(receipt)
    if len(raw) > 32768:
        raise ValueError("Process supervision receipt exceeds its byte bound")
    (folder / "supervision.json").write_bytes(raw)
    outputs = []
    for path in (stdout_path, stderr_path, samples_path, folder / "supervision.json"):
        body = path.read_bytes()
        limit = MAX_SAMPLE_LOG_BYTES if path == samples_path else MAX_LOG_BYTES if path in (stdout_path, stderr_path) else 32768
        if len(body) > limit:
            raise ValueError(f"Process supervision artifact exceeds its byte cap: {path.name}")
        outputs.append({"path": path.relative_to(folder).as_posix(), "bytes": len(body), "sha256": sha(body)})
    (folder / "publication.json").write_bytes(canonical({"version": 1, "status": "complete",
                                                          "outputs": outputs}))

def run(repo, baseline_commit, vintage, window_id):
    repo = pathlib.Path(repo).resolve()
    if not vintage or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in vintage):
        raise ValueError("Unsafe run vintage")
    if not isinstance(window_id, str) or not producer.re.fullmatch(r"[A-Za-z0-9._:-]{8,128}", window_id):
        raise ValueError("An explicit coordinator-issued memory-window ID is required")
    # Verify this wrapper and all execution inputs against the exact immutable commit.
    producer.bootstrap(repo, baseline_commit, phase="overlay")
    folder = require_contained_nonsymlink_path(
        repo, repo / OWNED / "vintages" / "process-supervision" / vintage)
    folder.parent.mkdir(parents=True, exist_ok=True)
    # Recheck after creating missing parents, then claim the entire vintage atomically.
    require_contained_nonsymlink_path(repo, folder)
    folder.mkdir(exist_ok=False)
    stdout_path, stderr_path = folder / "stdout.txt", folder / "stderr.txt"
    samples_path = folder / "rss-samples.jsonl"
    command = [sys.executable, str(repo / OWNED / "producer.py"), "--repo", str(repo),
               "--baseline-commit", baseline_commit, "--vintage", vintage,
               "--coordinated-window-id", window_id]
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env[producer.SUPERVISION_ENV] = producer.SUPERVISION_ENV_VALUE
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    clock = time.monotonic()
    samples = []
    stop_reason = None
    child_usage = None
    exit_code = None
    with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
        child = subprocess.Popen(command, cwd=repo, stdin=subprocess.DEVNULL,
                                 stdout=stdout, stderr=stderr, env=env,
                                 start_new_session=True)
        while child.returncode is None:
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            try:
                rss, pids = tree_rss_bytes(child.pid)
            except (OSError, subprocess.CalledProcessError) as exc:
                rss, pids = 0, []
                stop_reason = "external process-tree RSS sampler failed: " + type(exc).__name__
            samples.append({"at": now, "process_tree_rss_bytes": rss, "pids": pids})
            exit_code, usage = wait_child_nonblocking(child)
            if exit_code is not None:
                child_usage = usage
                break
            elapsed = time.monotonic() - clock
            if stop_reason is None and rss >= producer.EXTERNAL_RSS_STOP_BYTES:
                stop_reason = "external process-tree RSS stop threshold reached"
            elif stop_reason is None and elapsed >= producer.MAX_SECONDS:
                stop_reason = "external walltime limit reached"
            elif stop_reason is None and len(samples) >= MAX_SAMPLES:
                stop_reason = "external RSS sample-count limit reached"
            elif stop_reason is None and (stdout_path.stat().st_size > MAX_LOG_BYTES or
                                          stderr_path.stat().st_size > MAX_LOG_BYTES):
                stop_reason = "child log byte cap reached"
            if stop_reason:
                exit_code, child_usage = stop_and_reap_child(child)
                break
            time.sleep(producer.EXTERNAL_RSS_SAMPLE_SECONDS)
    if child_usage is None:
        raise ValueError("OS wait4 did not return terminal child resource usage")
    # Re-sample only after wait4 has reaped the leader, avoiding a stale ps row
    # racing with child.poll() and distinguishing a real surviving descendant.
    try:
        terminal_tree_rss, terminal_pids = tree_rss_bytes(child.pid)
        samples.append({"at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        "process_tree_rss_bytes": terminal_tree_rss, "pids": terminal_pids,
                        "after_child_reap": True})
    except (OSError, subprocess.CalledProcessError) as exc:
        terminal_tree_rss, terminal_pids = 0, []
        stop_reason = stop_reason or ("post-reap process-tree RSS sampler failed: " + type(exc).__name__)
    if terminal_pids:
        stop_reason = stop_reason or "process-group descendants remained after child reap"
        try:
            os.killpg(child.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        time.sleep(0.1)
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        cleanup_deadline = time.monotonic() + 2.0
        while True:
            try:
                terminal_tree_rss, terminal_pids = tree_rss_bytes(child.pid)
            except (OSError, subprocess.CalledProcessError):
                terminal_pids = [-1]
                break
            samples.append({"at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                            "process_tree_rss_bytes": terminal_tree_rss, "pids": terminal_pids,
                            "after_descendant_termination": True})
            if not terminal_pids or time.monotonic() >= cleanup_deadline:
                break
            time.sleep(0.1)
    if terminal_pids:
        stop_reason = stop_reason or "process-group descendants remained after termination attempt"
    terminal_child_rss = int(child_usage.ru_maxrss) if sys.platform == "darwin" else int(child_usage.ru_maxrss * 1024)
    samples_raw = b"".join(canonical(row) for row in samples)
    if len(samples_raw) > MAX_SAMPLE_LOG_BYTES:
        stop_reason = stop_reason or "external RSS sample-log byte cap reached"
        samples_raw = canonical({"status": "sample log exceeded cap", "sample_count": len(samples),
                                 "maximum_sampled_process_tree_rss_bytes": max(
                                     (row["process_tree_rss_bytes"] for row in samples), default=0)})
    samples_path.write_bytes(samples_raw)
    run_dir = repo / OWNED / "vintages" / vintage
    summary_path = run_dir / "run-summary.json"
    publication_path = run_dir / "publication.json"
    producer_summary = None
    if summary_path.is_file() and not summary_path.is_symlink() and summary_path.stat().st_size <= 32768:
        producer_summary = json.loads(summary_path.read_bytes())
    sampled_peak = max((row["process_tree_rss_bytes"] for row in samples), default=0)
    producer_prepublication_peak = (producer_summary.get("prepublication_ru_maxrss_bytes")
                                    if isinstance(producer_summary, dict) else None)
    qualified = (exit_code == 0 and stop_reason is None and
                 isinstance(producer_prepublication_peak, int) and
                 producer_prepublication_peak <= producer.MAX_RSS_BYTES and
                 terminal_child_rss <= producer.MAX_RSS_BYTES and
                 sampled_peak < producer.EXTERNAL_RSS_STOP_BYTES and
                 bool(samples) and
                 time.monotonic() - clock <= producer.MAX_SECONDS and
                 summary_path.is_file() and publication_path.is_file())
    receipt = {
        "version": 1,
        "status": "pass" if qualified else "failed",
        "baseline_commit": baseline_commit,
        "coordinated_window_id": window_id,
        "vintage": vintage,
        "command": command,
        "pid": child.pid,
        "process_group": child.pid,
        "started_at": started,
        "finished_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "elapsed_seconds": time.monotonic() - clock,
        "exit_code": exit_code,
        "stop_reason": stop_reason,
        "rss_sample_interval_seconds": producer.EXTERNAL_RSS_SAMPLE_SECONDS,
        "maximum_sampled_process_tree_rss_bytes": sampled_peak,
        "external_rss_measurement": "Sum of ps RSS bytes for producer and all observed descendants/process-group members; shared pages may be counted more than once.",
        "external_stop_bytes": producer.EXTERNAL_RSS_STOP_BYTES,
        "external_margin_below_768mib_bytes": producer.EXTERNAL_RSS_MARGIN_BYTES,
        "producer_prepublication_ru_maxrss_bytes": producer_prepublication_peak,
        "terminal_child_lifetime_ru_maxrss_bytes": terminal_child_rss,
        "terminal_child_pid": child.pid,
        "no_live_descendants_after_reap": not bool(terminal_pids),
        "producer_rss_limit_bytes": producer.MAX_RSS_BYTES,
        "sample_count": len(samples),
        "samples_are_polling_not_a_kernel_hard_limit": True,
        "source_run_summary_sha256": sha(summary_path.read_bytes()) if summary_path.is_file() else None,
        "source_run_publication_sha256": sha(publication_path.read_bytes()) if publication_path.is_file() else None,
    }
    write_supervision(folder, receipt, stdout_path, stderr_path, samples_path)
    print(json.dumps({"status": receipt["status"], "vintage": vintage,
                      "supervision_path": str(folder.relative_to(repo)),
                      "pid": child.pid, "exit_code": exit_code,
                      "maximum_sampled_process_tree_rss_bytes": sampled_peak,
                      "producer_prepublication_ru_maxrss_bytes": producer_prepublication_peak,
                      "terminal_child_lifetime_ru_maxrss_bytes": terminal_child_rss,
                      "stop_reason": stop_reason}, sort_keys=True))
    if not qualified:
        raise SystemExit(exit_code or 1)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--baseline-commit", required=True)
    parser.add_argument("--vintage", required=True)
    parser.add_argument("--coordinated-window-id", required=True)
    args = parser.parse_args()
    run(args.repo, args.baseline_commit, args.vintage, args.coordinated_window_id)

if __name__ == "__main__":
    main()
