#!/usr/bin/env python3
"""Prove failed or mismatched second runs cannot publish a passed pair."""
import json
import subprocess
from pathlib import Path
from unittest.mock import patch

from compare_runs import execute
from reproduce import OUTPUTS, ROOT, OWNED, canonical


def fake_result(code, run_id=None):
    payload = {"run_id": run_id, "execution_id": "fixture-" + str(run_id), "outputs": []}
    return subprocess.CompletedProcess([], code, json.dumps(payload) if code == 0 else "", "injected second-run failure")


def no_success(pair_id):
    target = ROOT / OWNED / "pairs" / pair_id
    return not (target / "publication.json").exists() and not any(target.iterdir())


def main():
    results = []
    failed_id = "failed-second-run-control"
    responses = iter((fake_result(0, failed_id + "-run-one"), fake_result(2, failed_id + "-run-two")))
    caught = None
    try:
        with patch("compare_runs.subprocess.run", side_effect=lambda *a, **k: next(responses)):
            execute(failed_id)
    except ValueError as exc:
        caught = str(exc)
    results.append({"id": failed_id, "passed": "failed (2)" in (caught or "") and no_success(failed_id),
                    "observed": caught, "publication_absent": no_success(failed_id)})

    mismatch_id = "mismatched-products-control"
    left_root = ROOT / OWNED / "runs" / (mismatch_id + "-run-one")
    right_root = ROOT / OWNED / "runs" / (mismatch_id + "-run-two")
    left_root.mkdir(); right_root.mkdir()
    for name in OUTPUTS:
        (left_root / name).write_bytes(("same-" + name).encode())
        (right_root / name).write_bytes(("changed-" + name).encode() if name == OUTPUTS[-1] else ("same-" + name).encode())
    responses = iter((fake_result(0, mismatch_id + "-run-one"), fake_result(0, mismatch_id + "-run-two")))
    caught = None
    try:
        with patch("compare_runs.subprocess.run", side_effect=lambda *a, **k: next(responses)):
            execute(mismatch_id)
    except ValueError as exc:
        caught = str(exc)
    results.append({"id": mismatch_id, "passed": "output sets differ" in (caught or "") and no_success(mismatch_id),
                    "observed": caught, "publication_absent": no_success(mismatch_id)})
    report = {"version": 1, "kind": "pair-failure-controls", "outcome": "passed" if all(x["passed"] for x in results) else "failed",
              "method_id": "batch3-provenance-crossfield-validator", "controls": results}
    output = ROOT / OWNED / "pair-failure-controls.json"
    with output.open("xb") as stream:
        stream.write(canonical(report))
    print(json.dumps(report, sort_keys=True))
    return 0 if all(x["passed"] for x in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
