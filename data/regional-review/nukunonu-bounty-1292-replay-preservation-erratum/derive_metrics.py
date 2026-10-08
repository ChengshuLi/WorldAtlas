#!/usr/bin/env python3
"""Materialize the reviewed metric ledger from one authenticated replay vintage."""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

OWNED = Path(__file__).resolve().parent
VINTAGE = "final-verified-a"
ATTEMPT_PATH = OWNED / "vintages" / VINTAGE / "attempt.json"
OUTPUT_PATH = OWNED / "vintages" / VINTAGE / "metrics.json"
RUNNER = OWNED / "reproduce_safe_coverage.py"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def coverage(report, subject_id, family):
    matches = [row for row in report.get("subjects", []) if row.get("indexed_feature_id") == subject_id]
    require(len(matches) == 1, "replay report must contain exactly one pinned subject")
    return matches[0][family]


def fraction(numerator, denominator):
    require(denominator > 0, "metric denominator must be positive")
    return numerator / denominator


def main():
    require(not OUTPUT_PATH.exists() and not OUTPUT_PATH.is_symlink(),
            "refuse an existing metrics output; preserve it and choose a new evidence vintage")
    subprocess.run([sys.executable, str(RUNNER), "check", "--vintage", VINTAGE],
                   cwd=OWNED.parents[2], check=True)
    attempt_raw = ATTEMPT_PATH.read_bytes()
    attempt = json.loads(attempt_raw)
    require(attempt.get("status") == "complete" and attempt.get("exit_code") == 0 and
            attempt.get("exception") is None, "source replay attempt is not a complete success")
    reports = {}
    for name, row in attempt.get("outputs", {}).items():
        raw = base64.b64decode(row["bytes_base64"], validate=True)
        require(len(raw) == row["bytes"] and sha(raw) == row["sha256"],
                "embedded report differs from the authenticated replay receipt")
        reports[name] = json.loads(raw)

    specs = [
        ("nukunonu", "atlas:macro-coverage:location:a0457f0d44c94b71f00d", "osm_current_indexed_coverage", "nukunonu_osm_full_component_fraction", "full"),
        ("bounty-islands", "atlas:macro-coverage:location:73281d3672f84a47a770", "osm_current_indexed_coverage", "bounty_osm_full_component_fraction", "full"),
        ("nukunonu", "atlas:macro-coverage:location:a0457f0d44c94b71f00d", "gshhg_current_indexed_coverage", "nukunonu_gshhg_positive_component_fraction", "positive"),
        ("bounty-islands", "atlas:macro-coverage:location:73281d3672f84a47a770", "gshhg_current_indexed_coverage", "bounty_gshhg_positive_component_fraction", "positive"),
    ]
    metrics = {}
    for report_name, subject_id, family, metric_id, kind in specs:
        cov = coverage(reports[report_name], subject_id, family)
        rows = cov["components"]
        require(rows and len(rows) == cov["source_component_count"],
                "metric component inventory does not match its declared denominator")
        if kind == "full":
            numerator = sum(row["source_component_covered_fraction"] >= 1 - 1e-10 for row in rows)
            denominator = len(rows)
            unit = "fraction of OSM rings fully area-covered"
        else:
            numerator = sum(row["source_component_covered_fraction"] > 0 for row in rows)
            denominator = len(rows)
            unit = "fraction of GSHHG components with positive-area overlap"
        metrics[metric_id] = {"value": fraction(numerator, denominator), "unit": unit,
                              "numerator": numerator, "denominator": denominator}

    for report_name, subject_id, metric_id in [
        ("nukunonu", "atlas:macro-coverage:location:a0457f0d44c94b71f00d", "nukunonu_gshhg_union_coverage_fraction"),
        ("bounty-islands", "atlas:macro-coverage:location:73281d3672f84a47a770", "bounty_gshhg_union_coverage_fraction"),
    ]:
        cov = coverage(reports[report_name], subject_id, "gshhg_current_indexed_coverage")
        metrics[metric_id] = {"value": cov["source_union_covered_fraction"],
                              "unit": "fraction of source-union area covered"}

    result = {
        "schema": "worldatlas-1292-replay-metric-ledger-v1",
        "source_attempt": {"path": str(ATTEMPT_PATH.relative_to(OWNED.parents[2])),
                           "sha256": sha(attempt_raw)},
        "method": "Component counts are computed from each pinned report's per-component covered fractions; GSHHG union values use the report's source-union fraction.",
        "metrics": metrics,
    }
    encoded = (json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(OUTPUT_PATH, flags, 0o644)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        OUTPUT_PATH.unlink(missing_ok=True)
        raise
    print(json.dumps({"status": "complete", "path": str(OUTPUT_PATH.relative_to(OWNED.parents[2])),
                      "bytes": len(encoded), "sha256": sha(encoded)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("FAIL: " + str(exc), file=sys.stderr)
        raise
