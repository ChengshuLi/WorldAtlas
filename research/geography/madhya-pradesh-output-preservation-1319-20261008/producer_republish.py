#!/usr/bin/env python3
"""Safely republish retained #1319 producer bytes; does not rerun geometry science."""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import re
import sys

from safe_outputs import (
    EVIDENCE_PATH, OWNED_PATH, admitted_baseline, exact_report_inputs,
    new_vintage_with_api, safe_output_root, verify_historical_manifest,
)

REPO = Path(__file__).resolve().parents[3]
PRODUCTS = ["assessments.json.gz"]


def produce_vintage(run_id: str, *, repo: Path = REPO, state=None, before_publish=None):
    # Complete inventory and all ancestors are checked before reading reports.
    safe_output_root(repo, run_id, PRODUCTS)
    state = state or admitted_baseline(repo)
    issue, contract, baseline, module, commit, files, pins = state
    vintage = new_vintage_with_api(repo, baseline, module, run_id, PRODUCTS)
    historical = verify_historical_manifest(repo, baseline)
    original, run_one, run_two = exact_report_inputs(baseline)
    decoded = gzip.decompress(run_one)
    if len(decoded) > module.MAX_FILE_BYTES:
        raise ValueError("Retained report exceeds the ordinary decoded-file limit")
    report = json.loads(decoded)
    expected_ids = contract["evidence_quality"]["subject_ids"]
    rows = report.get("exact_subjects", [])
    if (len(rows) != 224 or len({row.get("id") for row in rows}) != 224 or
            set(row.get("id") for row in rows) != set(expected_ids) or
            len(report.get("province_assessments", [])) != 27):
        raise ValueError("Retained producer report no longer matches the complete issue roster")
    if before_publish is not None:
        before_publish(vintage.root)
    records = vintage.publish_bytes({"assessments.json.gz": run_one})
    return {"issue": issue["number"], "baseline_commit": commit,
            "historical_evaluation": historical, "output": records[0],
            "retained_report_pair_equal": run_one == run_two,
            "retained_full_report_republished": True,
            "new_scientific_generation": False,
            "geographic_approval": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", args.run_id):
        parser.error("run-id must be 1-64 lowercase letters, digits or interior hyphens")
    try:
        result = produce_vintage(args.run_id)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as error:
        print(f"producer output admission failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
