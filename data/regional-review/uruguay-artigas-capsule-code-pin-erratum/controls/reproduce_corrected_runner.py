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
    number = 14
    def run_exists(value):
        name = f"verified-run-{value}"
        return ((HERE / "outputs" / name).exists() or
                (CONTROLS / "corrected-baseline-logs" / name).exists())
    while run_exists(number) or run_exists(number + 1):
        number += 2
    run_names = (f"verified-run-{number}", f"verified-run-{number + 1}")
    for name in run_names:
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
    failure_number = 3
    def failure_exists(value):
        candidate = f"failure-captured-safe-{value}"
        return ((HERE / "outputs" / candidate).exists() or
                (CONTROLS / "corrected-baseline-logs" / candidate).exists())
    while failure_exists(failure_number):
        failure_number += 1
    name = f"failure-captured-safe-{failure_number}"
    command = [sys.executable, str(HERE / "reproduce.py"), "--output", name, "--fail-after-compute"]
    process = subprocess.run(command, cwd=HERE, text=True, capture_output=True)
    logdir = CONTROLS / "corrected-baseline-logs" / name
    logdir.mkdir(parents=True)
    (logdir / "stdout.txt").write_text(process.stdout)
    (logdir / "stderr.txt").write_text(process.stderr)
    out = HERE / "outputs" / name
    report = out / "reproduction-results.json"
    failure = out / "failure.json"
    failed_attempt = {"command": command, "exit_code": process.returncode,
                      "stdout_sha256": sha(process.stdout.encode()),
                      "stderr_sha256": sha(process.stderr.encode()),
                      "report_sha256": sha(report.read_bytes()) if report.is_file() else None,
                      "failure": json.loads(failure.read_text()) if failure.is_file() else None,
                      "success_receipt_exists": (out / "publication.json").exists(),
                      "output_name": name}
    if (process.returncode != 1 or not report.is_file() or not failure.is_file() or
            failed_attempt["success_receipt_exists"] or failed_attempt["report_sha256"] != "3970173b2c2050c1099ec427e4d64076e96a3000635ba20db203fa204320e44a"):
        raise AssertionError("failed full run was not safely retained")
    result = {"version": 1, "issue": 1413, "capsule_sha256": "5b3787d9f07373751d2bbd5a94acec41eab79de43732cd4f6c45e2fd72c3d873",
              "retained_report_sha256": "3970173b2c2050c1099ec427e4d64076e96a3000635ba20db203fa204320e44a",
              "runs": rows, "directed_failure": failed_attempt,
              "runtime": {"python": sys.version, "executable": sys.executable}}
    (CONTROLS / "corrected-baseline-runs.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"runs": len(rows), "matched_report": True,
                      "completion_receipts": all(row["publication_sha256"] for row in rows),
                      "failed_attempt_retained_without_receipt": True}, sort_keys=True))


if __name__ == "__main__":
    main()
