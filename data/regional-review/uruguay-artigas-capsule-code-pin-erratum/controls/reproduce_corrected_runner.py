#!/usr/bin/env python3
"""Run the current corrected entry point twice and retain complete process results."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parents[1]
CONTROLS = HERE / "controls"
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def main():
    rows = []
    for name in ("verified-run-six", "verified-run-seven"):
        command = [sys.executable, str(HERE / "reproduce.py"), "--output", name]
        process = subprocess.run(command, cwd=HERE, text=True, capture_output=True)
        logdir = CONTROLS / "corrected-baseline-logs" / name
        logdir.mkdir(parents=True)
        (logdir / "stdout.txt").write_text(process.stdout)
        (logdir / "stderr.txt").write_text(process.stderr)
        report = HERE / "outputs" / name / "reproduction-results.json"
        receipt = HERE / "outputs" / name / "publication.json"
        row = {"command": command, "exit_code": process.returncode,
               "stdout_sha256": sha(process.stdout.encode()),
               "stderr_sha256": sha(process.stderr.encode()),
               "stdout_bytes": len(process.stdout.encode()), "stderr_bytes": len(process.stderr.encode()),
               "report_sha256": sha(report.read_bytes()) if report.is_file() else None,
               "publication_sha256": sha(receipt.read_bytes()) if receipt.is_file() else None,
               "output_name": name}
        if process.returncode or row["report_sha256"] != "3970173b2c2050c1099ec427e4d64076e96a3000635ba20db203fa204320e44a" or not receipt.is_file():
            raise AssertionError("full corrected reproduction did not complete: " + name)
        rows.append(row)
    result = {"version": 1, "issue": 1413, "capsule_sha256": "5b3787d9f07373751d2bbd5a94acec41eab79de43732cd4f6c45e2fd72c3d873",
              "retained_report_sha256": "3970173b2c2050c1099ec427e4d64076e96a3000635ba20db203fa204320e44a",
              "runs": rows, "runtime": {"python": sys.version, "executable": sys.executable}}
    (CONTROLS / "corrected-baseline-runs.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"runs": len(rows), "matched_report": True,
                      "completion_receipts": all(row["publication_sha256"] for row in rows)}, sort_keys=True))


if __name__ == "__main__":
    main()
