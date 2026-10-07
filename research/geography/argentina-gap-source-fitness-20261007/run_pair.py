#!/usr/bin/env python3
"""Run two fresh bounded extractions and retain actual process receipts."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
OWNED = ROOT / "research/geography/argentina-gap-source-fitness-20261007"
RUNNER = OWNED / "reproduce.py"

if sys.version_info[:3] != (3, 12, 14):
    raise RuntimeError("Use the recorded CPython 3.12.14 runtime")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


pair_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f") + "-" + uuid.uuid4().hex[:8]
runs = ("argentina-run-replay-" + pair_id, "argentina-run-replay-" + pair_id + "-b")
check_vintage = "argentina-repro-check-" + pair_id
processes = []
for run in runs:
    command = [sys.executable, str(RUNNER), "--run", run]
    started = now()
    result = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    ended = now()
    processes.append({
        "run": run,
        "command": command,
        "cwd": str(ROOT),
        "started_at_utc": started,
        "ended_at_utc": ended,
        "exit_code": result.returncode,
        "stdout_sha256": digest(result.stdout),
        "stderr_sha256": digest(result.stderr),
        "stdout": result.stdout.decode("utf-8", errors="replace"),
        "stderr": result.stderr.decode("utf-8", errors="replace"),
    })
    if result.returncode:
        print(json.dumps({"processes": processes}, indent=2), file=sys.stderr)
        raise SystemExit(result.returncode)

fit_paths = [ROOT / "research/geography/argentina-gap-source-fitness-20261007/vintages" / run / "source-fit.json"
             for run in runs]
fits = [path.read_bytes() for path in fit_paths]
if fits[0] != fits[1]:
    raise ValueError("fresh source-fit outputs differ")
fit = json.loads(fits[0])
receipt = {
    "version": 1,
    "kind": "actual-execution-receipt",
    "outcome": "passed",
    "wrapper": {"path": str(Path(__file__).resolve().relative_to(ROOT)),
                "sha256": digest(Path(__file__).read_bytes())},
    "runtime": {"python_executable": sys.executable, "python_version": sys.version,
                "platform": sys.platform},
    "execution_binding": fit["execution_binding"],
    "processes": processes,
    "outputs": [{"path": str(path.relative_to(ROOT)), "bytes": len(raw), "sha256": digest(raw)}
                for path, raw in zip(fit_paths, fits)],
    "equal_source_fit_bytes": True,
}
with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json", delete=False) as handle:
    handle.write(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    log_path = handle.name
try:
    command = [sys.executable, str(RUNNER), "--finalize-reproducibility", "--execution-log", log_path,
               "--run-one", runs[0], "--run-two", runs[1], "--check-vintage", check_vintage]
    finalizer = subprocess.run(command, cwd=ROOT, check=False)
    if finalizer.returncode:
        raise SystemExit(finalizer.returncode)
finally:
    Path(log_path).unlink(missing_ok=True)
print(json.dumps({"reproducibility_vintage": "research/geography/argentina-gap-source-fitness-20261007/vintages/" + check_vintage,
                  "runs": [{"run": p["run"], "exit_code": p["exit_code"],
                            "started_at_utc": p["started_at_utc"], "ended_at_utc": p["ended_at_utc"]}
                           for p in processes]}, indent=2, sort_keys=True))
