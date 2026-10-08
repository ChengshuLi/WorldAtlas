#!/usr/bin/env python3
"""Fail-closed successor for the predecessor's standalone freeze writer."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from typing import Callable

import admission
import run_safe


class DestinationAdmission:
    """In-process receipt that one exact ordinary lock path was pre-admitted."""
    __slots__ = ("root", "relative_path", "_seal")

    def __init__(self, root: Path, relative_path: str, seal: object):
        self.root = root.resolve(strict=True)
        self.relative_path = admission.safe_relative(relative_path)
        self._seal = seal


class FreezeRefused(admission.AdmissionError):
    def __init__(self, plan: dict):
        super().__init__("Complete phase was refused before freeze destination reservation")
        self.plan = plan


_SEAL = object()


def preadmit_lock_destination(repo_root: Path, relative_path: str) -> DestinationAdmission:
    owned = run_safe.HERE.relative_to(repo_root.resolve(strict=True)).as_posix() + "/"
    if not relative_path.startswith(owned):
        raise admission.AdmissionError("Freeze lock must stay inside issue 1511's owned path")
    normalized = admission.admit_destinations(repo_root, [relative_path])[0]
    return DestinationAdmission(repo_root, normalized, _SEAL)


def write_lock_exclusive(repo_root: Path, relative_path: str, lock: dict,
                         *, destination: DestinationAdmission) -> dict:
    root = repo_root.resolve(strict=True)
    relative_path = admission.safe_relative(relative_path)
    if (not isinstance(destination, DestinationAdmission) or destination._seal is not _SEAL or
            destination.root != root or destination.relative_path != relative_path):
        raise admission.AdmissionError("A matching lock destination must be pre-admitted first")
    raw = (json.dumps(lock, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
    if len(raw) > admission.PER_FILE_BYTES:
        raise admission.AdmissionError("Freeze lock exceeds the bounded file cap")
    admission.write_exclusive(root, relative_path, raw)
    return {"path": relative_path, "bytes": len(raw), "sha256": admission.sha256(raw)}


def _derive_preserved_lock(repo_root: Path) -> dict:
    """Import only after admission; caller has authenticated the pinned code bytes."""
    packet = repo_root / run_safe.PREDECESSOR
    source = packet / "source_extract.py"
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(packet))
    try:
        spec = importlib.util.spec_from_file_location("_saudi_preserved_source_extract", source)
        if spec is None or spec.loader is None:
            raise admission.AdmissionError("Cannot load the authenticated predecessor freezer")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.derive_source_closure(repo_root)
    finally:
        try:
            sys.path.remove(str(packet))
        except ValueError:
            pass


def run_freeze(repo_root: Path, run_id: str, derive_lock: Callable[[Path], dict] | None = None) -> dict:
    """Authenticate/admit first; then derive and write the lock and truthful report."""
    if not isinstance(run_id, str) or not run_id.isalnum() and "-" not in run_id:
        raise admission.AdmissionError("Unsafe freeze run identifier")
    if not run_id or len(run_id) > 40 or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789-" for ch in run_id):
        raise admission.AdmissionError("Unsafe freeze run identifier")
    root = repo_root.resolve(strict=True)
    _old_lock, plan, _outputs, _receipts = run_safe.load_plan(root, invocation_script=Path(__file__))
    if not plan.get("admitted"):
        raise FreezeRefused(plan)

    owned = run_safe.HERE.relative_to(root).as_posix()
    run_dir = f"{owned}/execution/freezes/{run_id}"
    lock_path = f"{run_dir}/frozen-execution.json"
    receipt_path = f"{run_dir}/execution.json"
    admission.admit_destinations(root, [lock_path, receipt_path], directory_paths=[run_dir])
    lock_admission = DestinationAdmission(root, lock_path, _SEAL)
    receipt_admission = DestinationAdmission(root, receipt_path, _SEAL)
    start = run_safe.utc_now()
    try:
        lock = (derive_lock or _derive_preserved_lock)(root)
        lock_record = write_lock_exclusive(root, lock_path, lock, destination=lock_admission)
        receipt = {"version": 1, "run_id": run_id, "status": "complete", "started_utc": start,
                   "ended_utc": run_safe.utc_now(), "invocation": sys.argv,
                   "runtime": plan["runtime"], "plan": plan, "lock": lock_record,
                   "source_data_blobs_read": True, "complete_source_pass": True,
                   "geographic_approval": False, "publication_authority": False}
        complete = True
    except Exception as exc:
        receipt = {"version": 1, "run_id": run_id, "status": "failed-attempt",
                   "started_utc": start, "ended_utc": run_safe.utc_now(),
                   "invocation": sys.argv, "runtime": plan["runtime"], "plan": plan,
                   "error": f"{type(exc).__name__}: {exc}"[:512],
                   "source_data_blobs_read": "may-have-started", "complete_source_pass": False,
                   "geographic_approval": False, "publication_authority": False}
        complete = False
    raw = (json.dumps(receipt, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
    if len(raw) > admission.RECEIPT_BYTES:
        raise admission.AdmissionError("Freeze execution receipt exceeds its 4 KiB reserve")
    if receipt_admission.root != root or receipt_admission.relative_path != receipt_path or receipt_admission._seal is not _SEAL:
        raise admission.AdmissionError("Freeze receipt destination lost its admission")
    admission.write_exclusive(root, receipt_path, raw)
    if not complete:
        raise admission.AdmissionError("Freeze attempt failed; a truthful failure receipt was retained")
    return {"status": "complete", "lock": lock_record, "receipt_path": receipt_path}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=str(run_safe.REPO_ROOT))
    parser.add_argument("--run-id", default="freeze")
    args = parser.parse_args()
    root = Path(args.repo).resolve(strict=True)
    try:
        result = run_freeze(root, args.run_id)
    except FreezeRefused as exc:
        try:
            path = run_safe.refusal_record(
                root, args.run_id, {**exc.plan, "operation": "freeze"},
                "Complete raw/decoded source closure plus runtime and output reserves exceeds 256 MiB")
        except (admission.AdmissionError, FileExistsError) as error:
            print(json.dumps({"status": "refused-before-freeze", "reason": str(error),
                              "source_data_blobs_read": False, "lock_written": False}))
            return 2
        print(json.dumps({"status": "refused-before-freeze", "refusal_path": path,
                          "plan": exc.plan, "source_data_blobs_read": False, "lock_written": False}))
        return 78
    except admission.AdmissionError as exc:
        print(json.dumps({"status": "failed-freeze", "reason": str(exc),
                          "source_data_blobs_read": False, "lock_written": False}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
