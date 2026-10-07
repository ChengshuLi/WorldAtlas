#!/usr/bin/env python3
"""Run the frozen measurement twice and retain individual execution receipts."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

import controls
from measure import bounded_candidate, runtime_receipt, sha

PACKET = Path(__file__).parent


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def main():
    freeze_bytes = bounded_candidate(PACKET, "closure-freeze.json")
    freeze_hash = sha(freeze_bytes)
    verification = PACKET / "verification"
    verification.mkdir(exist_ok=True)
    executable = sys.executable
    resolved_executable = str(Path(sys.executable).resolve())
    cwd = str(PACKET.parents[2].resolve())
    frozen_runtime = runtime_receipt()
    if json.loads(freeze_bytes).get("runtime") != frozen_runtime:
        raise ValueError("Runtime receipt differs from frozen closure before run pair")
    runs = []
    for ordinal, name in enumerate(("run-one", "run-two"), start=1):
        result_path = verification / name / "result.json"
        result_path.parent.mkdir(parents=True, exist_ok=True)
        command = [executable, "-I", "-B", str(PACKET / "measure.py"), "--packet", str(PACKET),
                   "--result", str(result_path)]
        started = utc_now()
        completed = subprocess.run(command, cwd=cwd, text=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, check=False)
        ended = utc_now()
        if completed.returncode != 0:
            raise RuntimeError(name + " failed: " + completed.stderr[-1000:])
        result_bytes = bounded_candidate(PACKET, str(result_path.relative_to(PACKET)))
        result = json.loads(result_bytes)
        if result.get("closure_freeze_sha256") != freeze_hash or result.get("runtime") != frozen_runtime:
            raise ValueError(name + " did not execute the exact frozen code/runtime closure")
        runs.append({"id": name, "command": command, "cwd": cwd,
                     "invoked_interpreter": executable, "resolved_interpreter": resolved_executable,
                     "start_utc": started, "end_utc": ended, "exit_status": completed.returncode,
                     "stdout_sha256": sha(completed.stdout.encode()), "stderr_sha256": sha(completed.stderr.encode()),
                     "result_path": str(result_path.relative_to(PACKET)), "result_sha256": sha(result_bytes),
                     "runtime_receipt": frozen_runtime})
    if runs[0]["result_sha256"] != runs[1]["result_sha256"]:
        raise ValueError("Frozen run pair produced different result bytes")
    receipt = {"version": 2, "method_id": "frozen-bounded-source-fitness-measurement",
               "outcome": "passed", "execution_commit": json.loads(freeze_bytes)["execution_commit"],
               "closure_freeze_sha256": freeze_hash, "runs": runs,
               "byte_identical_results": True}
    target = verification / "execution-reproducibility.json"
    target.write_bytes(controls.canonical(receipt))
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
