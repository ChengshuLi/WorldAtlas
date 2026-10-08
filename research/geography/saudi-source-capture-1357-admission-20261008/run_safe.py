#!/usr/bin/env python3
"""Bounded additive successor for the preserved Saudi source extractor.

This wrapper does not mutate or replace the historical packet. It refuses the
known oversized full replay from authenticated frozen metadata. If a future
reviewed lock is admissible, it reserves every output before invoking the
preserved extractor and records a bounded failure/success receipt last.
"""
from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
from datetime import datetime, timezone

import admission

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
PREDECESSOR = "research/geography/saudi-fortynine-numeric-gap-family-source-fitness-20261007"
RUNTIME_RESERVE_BYTES = 32 * 1024 * 1024
HISTORICAL_RECEIPTS = {
    "run-1": "a27a2271a54ed42033edbafe28712b184117058291bb7d9be149a65db71e38b7",
    "run-2": "a829fc698136fde7cac7f5229755a8f9447c7c45dba8ea312b708e5e79d9e934",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _receipt_inventory(packet: Path) -> tuple[dict[str, dict], list[dict]]:
    """Authenticate both frozen complete product inventories without extraction."""
    inventories = []
    receipt_rows = []
    for run_id in ("run-1", "run-2"):
        receipt_path = packet / "runs" / f"{run_id}-execution.json"
        raw = admission.read_regular(receipt_path)
        if admission.sha256(raw) != HISTORICAL_RECEIPTS[run_id]:
            raise admission.AdmissionError(f"Historical {run_id} receipt differs from the accepted preserved bytes")
        value = json.loads(raw)
        if value.get("run_id") != run_id or value.get("complete_source_pass") is not True or value.get("exit_code") != 0:
            raise admission.AdmissionError(f"Historical {run_id} is not a successful complete run")
        rows = value.get("outputs")
        if not isinstance(rows, list) or len(rows) != 14:
            raise admission.AdmissionError(f"Historical {run_id} does not inventory fourteen products")
        normalized = {}
        for row in rows:
            path = admission.safe_relative(row.get("path"))
            prefix = f"runs/{run_id}/output/"
            if not path.startswith(prefix):
                raise admission.AdmissionError("Historical product escaped its run directory")
            name = path[len(prefix):]
            if "/" in name or name in normalized:
                raise admission.AdmissionError("Historical product inventory is not a unique flat set")
            size = admission._integer(row.get("bytes"), "historical output bytes")
            digest = admission._hash(row.get("sha256"), "historical output SHA-256")
            if size > admission.PER_FILE_BYTES:
                raise admission.AdmissionError(f"Historical output exceeds the accepted per-file cap: {name}")
            normalized[name] = {"bytes": size, "sha256": digest}
        inventories.append(normalized)
        receipt_rows.append({"path": f"{PREDECESSOR}/runs/{run_id}-execution.json",
                             "bytes": len(raw), "sha256": admission.sha256(raw)})
    if inventories[0] != inventories[1]:
        raise admission.AdmissionError("Historical two-run product inventories are not byte-identical")
    return inventories[0], receipt_rows


def load_plan(repo_root: Path, *, invocation_script: Path | None = None) -> tuple[dict, dict, dict[str, dict], list[dict]]:
    packet = repo_root / PREDECESSOR
    lock_path = packet / "frozen-execution.json"
    lock_raw = admission.read_regular(lock_path)
    lock_hash = admission.sha256(lock_raw)
    if lock_hash != admission.LOCK_SHA256:
        raise admission.AdmissionError("Preserved frozen execution manifest does not match issue 1511's pin")
    lock = json.loads(lock_raw)
    for bucket_name in ("code", "local_inputs"):
        rows = lock.get(bucket_name)
        if not isinstance(rows, list) or not rows:
            raise admission.AdmissionError(f"Frozen {bucket_name} inventory is missing")
        for row in rows:
            relative = admission.safe_relative(row.get("path"))
            raw = admission.read_regular(packet / relative)
            if len(raw) != row.get("bytes") or admission.sha256(raw) != row.get("sha256"):
                raise admission.AdmissionError(f"Frozen {bucket_name} bytes changed: {relative}")
    expected_outputs, receipts = _receipt_inventory(packet)
    output_reserve = sum(row["bytes"] for row in expected_outputs.values())
    helper_paths = [HERE / "admission.py", HERE / "run_safe.py"]
    if invocation_script is not None:
        helper_paths.append(invocation_script.resolve(strict=True))
    helper_rows = []
    seen_helpers = set()
    for path in helper_paths:
        real = path.resolve(strict=True)
        raw = admission.read_regular(real)
        identity = admission.sha256(raw)
        if identity not in seen_helpers:
            helper_rows.append({"path": "code/" + real.name, "bytes": len(raw), "sha256": identity})
            seen_helpers.add(identity)
    runtime_path = Path(sys.executable).resolve(strict=True)
    runtime_raw = admission.read_regular(runtime_path)
    runtime_row = {"path": "runtime/python-interpreter", "bytes": len(runtime_raw),
                   "sha256": admission.sha256(runtime_raw)}
    supplemental = receipts + helper_rows + [runtime_row]
    plan = admission.plan_from_lock(
        lock,
        lock_sha256=lock_hash,
        lock_bytes=len(lock_raw),
        output_reserve_bytes=output_reserve,
        runtime_reserve_bytes=RUNTIME_RESERVE_BYTES,
        supplemental_files=supplemental,
    )
    plan["supplemental_inputs"] = supplemental
    plan["runtime"] = {"implementation": platform.python_implementation(),
                       "version": platform.python_version(), "executable": str(runtime_path),
                       "executable_sha256": runtime_row["sha256"],
                       "executable_bytes": runtime_row["bytes"],
                       "reserve_bytes": RUNTIME_RESERVE_BYTES}
    plan["invocation_script_sha256"] = next((row["sha256"] for row in helper_rows
                                              if invocation_script and row["path"] == "code/" + invocation_script.resolve().name),
                                             helper_rows[-1]["sha256"])
    plan["historical_output_file_count"] = len(expected_outputs)
    plan["historical_output_receipts"] = receipts
    return lock, plan, expected_outputs, receipts


def _inspect_output(output: Path, expected: dict[str, dict], *, successful: bool) -> list[dict]:
    if not output.exists():
        if successful:
            raise admission.AdmissionError("Successful producer did not create its admitted output directory")
        return []
    info = output.lstat()
    if not stat.S_ISDIR(info.st_mode):
        raise admission.AdmissionError("Producer output is not an ordinary directory")
    rows = []
    for child in sorted(output.iterdir()):
        item = child.lstat()
        if not stat.S_ISREG(item.st_mode) or item.st_size > admission.PER_FILE_BYTES:
            raise admission.AdmissionError(f"Unexpected or oversized output object: {child.name}")
        if child.name not in expected:
            raise admission.AdmissionError(f"Unadmitted output product: {child.name}")
        raw = admission.read_regular(child)
        actual = {"bytes": len(raw), "sha256": admission.sha256(raw)}
        if actual["bytes"] > expected[child.name]["bytes"]:
            raise admission.AdmissionError(f"Output product exceeds its authenticated expected size: {child.name}")
        if successful and actual != expected[child.name]:
            raise admission.AdmissionError(f"Output product differs from its authenticated expected bytes: {child.name}")
        rows.append({"path": child.name, **actual})
    names = {row["path"] for row in rows}
    if successful and names != set(expected):
        raise admission.AdmissionError("Successful producer output set is incomplete")
    if sum(row["bytes"] for row in rows) > sum(row["bytes"] for row in expected.values()):
        raise admission.AdmissionError("Producer output exceeds the admitted aggregate reserve")
    return rows


def run_admitted_child(repo_root: Path, run_id: str, child: list[str],
                       expected_outputs: dict[str, dict], plan: dict) -> dict:
    """Run a child only after all paths have been admitted; receipt is written last."""
    if re.fullmatch(r"[a-z0-9][a-z0-9-]{0,40}", run_id) is None:
        raise admission.AdmissionError("Unsafe run identifier")
    run_dir = f"{HERE.relative_to(repo_root).as_posix()}/execution/runs/{run_id}"
    output_dir = f"{run_dir}/output"
    receipt_path = f"{run_dir}/execution.json"
    leaves = [receipt_path] + [f"{output_dir}/{name}" for name in expected_outputs]
    admission.admit_destinations(repo_root, leaves, directory_paths=[run_dir, output_dir])

    started = utc_now()
    tick = time.monotonic()
    try:
        proc = subprocess.run(child, cwd=repo_root, text=True, capture_output=True, check=False)
        exit_code = proc.returncode
        stdout, stderr = proc.stdout, proc.stderr
    except BaseException as exc:
        exit_code = 127
        stdout, stderr = "", f"child launch failed: {type(exc).__name__}: {exc}"
    output_path = repo_root / output_dir
    inspection_error = ""
    try:
        products = _inspect_output(output_path, expected_outputs, successful=exit_code == 0)
    except (admission.AdmissionError, OSError) as exc:
        products = []
        inspection_error = f"{type(exc).__name__}: {exc}"[:512]
    complete = exit_code == 0 and not inspection_error
    receipt = {
        "version": 1,
        "run_id": run_id,
        "status": "complete" if complete else "failed-attempt",
        "started_utc": started,
        "ended_utc": utc_now(),
        "elapsed_seconds": round(time.monotonic() - tick, 6),
        "child_argv": child,
        "exit_code": exit_code,
        "complete_source_pass": complete,
        "output_validation_error": inspection_error,
        "plan": plan,
        "products": products,
        "products_sha256": admission.sha256(json.dumps(products, sort_keys=True, separators=(",", ":")).encode()),
        "stdout": stdout[:256],
        "stderr": stderr[:256],
        "stdout_truncated": len(stdout) > 256,
        "stderr_truncated": len(stderr) > 256,
        "scientific_or_geographic_approval": False,
    }
    receipt_raw = (json.dumps(receipt, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
    if len(receipt_raw) > admission.RECEIPT_BYTES:
        raise admission.AdmissionError("Execution receipt exceeds its 4 KiB reserve")
    admission.write_exclusive(repo_root, receipt_path, receipt_raw)
    return {"run_id": run_id, "exit_code": exit_code if exit_code != 0 else (1 if inspection_error else 0),
            "child_exit_code": exit_code, "receipt_path": receipt_path, "products": len(products),
            "complete_source_pass": complete, "output_validation_error": inspection_error}


def refusal_record(repo_root: Path, run_id: str, plan: dict, error: str) -> str:
    path = f"{HERE.relative_to(repo_root).as_posix()}/execution/refusals/{run_id}-admission.json"
    admission.admit_destinations(repo_root, [path])
    value = {
        "version": 1,
        "run_id": run_id,
        "status": "refused-before-source-read",
        "recorded_utc": utc_now(),
        "reason": error,
        "invocation": {"argv": sys.argv, "python": platform.python_version(),
                       "script_sha256": plan.get("invocation_script_sha256")},
        "plan": plan,
        "source_bodies_read": False,
        "source_data_blobs_read": False,
        "small_frozen_code_and_local_inputs_authenticated": True,
        "decompression_started": False,
        "producer_started": False,
        "geographic_approval": False,
        "publication_authority": False,
    }
    admission.write_exclusive_json(repo_root, path, value)
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--repo", default=str(REPO_ROOT))
    args = parser.parse_args()
    if re.fullmatch(r"run-[1-9][0-9]*", args.run_id) is None:
        parser.error("--run-id must be run-<positive integer>")
    root = Path(args.repo).resolve(strict=True)
    try:
        _lock, plan, expected, _receipts = load_plan(root, invocation_script=Path(__file__))
    except admission.AdmissionError as exc:
        print(json.dumps({"status": "refused-before-source-read", "reason": str(exc)}))
        return 2
    if not plan["admitted"]:
        try:
            path = refusal_record(root, args.run_id, plan,
                                  "Complete raw/decoded source closure plus runtime and output reserves exceeds 256 MiB")
        except (admission.AdmissionError, FileExistsError) as exc:
            print(json.dumps({"status": "refused", "reason": str(exc), "source_bodies_read": False}))
            return 2
        print(json.dumps({"status": "refused-before-source-read", "refusal_path": path, "plan": plan}))
        return 78

    packet = root / PREDECESSOR
    child = [sys.executable, str(packet / "source_extract.py"), "--repo", str(root),
             "--run-id", args.run_id, "--output",
             str(HERE / "execution" / "runs" / args.run_id / "output")]
    try:
        result = run_admitted_child(root, args.run_id, child, expected, plan)
    except (admission.AdmissionError, FileExistsError) as exc:
        print(json.dumps({"status": "refused-before-producer", "reason": str(exc)}))
        return 2
    print(json.dumps(result))
    return result["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
