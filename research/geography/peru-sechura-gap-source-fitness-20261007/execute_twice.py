#!/usr/bin/env python3
"""Execute the bounded local comparison twice and preserve full output hashes."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "reproduce.py"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

def collect(directory):
    rows = []
    for path in sorted(directory.rglob("*")):
        if path.is_file():
            rows.append({"path": str(path.relative_to(directory)), "bytes": path.stat().st_size, "sha256": sha(path)})
    return rows

def main():
    script_sha = sha(SCRIPT)
    import shapely, pyproj, numpy
    execution = {
        "version": 1,
        "script": {"path": "reproduce.py", "sha256": script_sha},
        "runtime": {
            "python": sys.version,
            "python_executable": sys.executable,
            "shapely": shapely.__version__,
            "pyproj": pyproj.__version__,
            "numpy": numpy.__version__,
            "geos": shapely.geos_version_string,
            "proj": pyproj.proj_version_str,
        },
        "runs": [],
    }
    for number in (1, 2):
        run_dir = ROOT / "runs" / f"run-{number}"
        run_dir.mkdir(parents=True, exist_ok=True)
        started = utc_now()
        monotonic = time.monotonic()
        result = subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        elapsed = time.monotonic() - monotonic
        ended = utc_now()
        (run_dir / "stdout.txt").write_bytes(result.stdout)
        (run_dir / "stderr.txt").write_bytes(result.stderr)
        if result.returncode == 0:
            shutil.copy2(ROOT / "analysis.json", run_dir / "analysis.json")
            if (ROOT / "inputs").exists():
                if (run_dir / "inputs").exists():
                    shutil.rmtree(run_dir / "inputs")
                shutil.copytree(ROOT / "inputs", run_dir / "inputs")
        execution["runs"].append({
            "number": number,
            "started_at_utc": started,
            "ended_at_utc": ended,
            "elapsed_seconds": round(elapsed, 6),
            "exit_code": result.returncode,
            "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(result.stderr).hexdigest(),
            "outputs": collect(run_dir),
        })
        if result.returncode != 0:
            break
        if sha(SCRIPT) != script_sha:
            raise RuntimeError("Analysis script changed during the two bounded executions")
    if len(execution["runs"]) == 2 and all(row["exit_code"] == 0 for row in execution["runs"]):
        execution["output_trees_identical"] = execution["runs"][0]["outputs"] == execution["runs"][1]["outputs"]
    else:
        execution["output_trees_identical"] = False
    (ROOT / "execution.json").write_text(json.dumps(execution, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"exit_codes": [row["exit_code"] for row in execution["runs"]], "identical": execution["output_trees_identical"], "execution_sha256": sha(ROOT / "execution.json")}, sort_keys=True))
    if len(execution["runs"]) != 2 or any(row["exit_code"] != 0 for row in execution["runs"]) or not execution["output_trees_identical"]:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
