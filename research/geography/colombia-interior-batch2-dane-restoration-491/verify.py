#!/usr/bin/env python3
"""Verify retained DANE bytes and the full 190-location current-code/settlement join."""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

from build_evidence import ROOT, build_records, render_outputs


def need(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify() -> dict:
    registry = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
    for source in registry["retained_files"]:
        path = ROOT / source["path"]
        need(path.is_file(), f"retained source missing: {source['path']}")
        need(path.stat().st_size == source["bytes"], f"byte count mismatch: {source['path']}")
        need(sha(path) == source["sha256"], f"SHA-256 mismatch: {source['path']}")
        if source.get("content_encoding") == "gzip":
            restored = gzip.decompress(path.read_bytes())
            need(len(restored) == source["uncompressed_bytes"] and
                 hashlib.sha256(restored).hexdigest() == source["uncompressed_sha256"],
                 f"compressed source does not restore original bytes: {source['path']}")
    for source in registry["derived_inputs"]:
        path = ROOT / source["path"]
        need(path.is_file() and path.stat().st_size == source["bytes"] and sha(path) == source["sha256"],
             f"derived input receipt mismatch: {source['path']}")

    license_html = gzip.decompress((ROOT / "sources/dane-geoportal-license.html.gz").read_bytes()).decode("utf-8")
    need("creativecommons.org/licenses/by/4.0/" in license_html, "DANE CC BY 4.0 terms citation missing")
    need("Departamento Administrativo Nacional de Estadística - DANE: www.dane.gov.co" in license_html,
         "DANE required attribution wording missing")

    subject_input = json.loads((ROOT / "subject-inputs.json").read_text(encoding="utf-8"))
    subjects = subject_input["subjects"]
    need(len(subjects) == 190 and len({row["location_id"] for row in subjects}) == 190,
         "pinned assignment does not contain 190 unique IDs")
    need(subject_input["member_ids_sha256"] == "6032775e1f381a259382697c034ab51f61dcc1bbdc8ef90d51bb3bbb36c0037d",
         "subject snapshot does not bind to issue #587's member digest")
    baseline = subject_input["baseline_commit"]
    scope_path = subject_input["source_scope_path"]
    assessment_path = subject_input["source_assessment_path"]
    scope_raw = subprocess.check_output(["git", "show", f"{baseline}:{scope_path}"])
    assessment_raw = subprocess.check_output(["git", "show", f"{baseline}:{assessment_path}"])
    need(hashlib.sha256(scope_raw).hexdigest() == subject_input["source_scope_sha256"],
         "parent scope snapshot source hash differs")
    need(hashlib.sha256(assessment_raw).hexdigest() == subject_input["source_assessment_sha256"],
         "parent assessment snapshot source hash differs")
    parent_scope, parent_assessment = json.loads(scope_raw), json.loads(assessment_raw)
    need(set(row["location_id"] for row in subjects) == set(parent_scope["member_location_ids"]),
         "snapshot subjects differ from the pinned parent scope")
    parent_rows = {row["location_id"]: row for row in parent_assessment["locations"]}
    need(all(subject["source_name"] == parent_rows[subject["location_id"]]["source_identity"]["shape_name"] and
             subject["atlas_department"] == parent_rows[subject["location_id"]]["full_parent_chain"][0]["name"]
             for subject in subjects), "subject source names/department parents differ from the pinned parent assessment")
    access = json.loads((ROOT / "source-access.json").read_text(encoding="utf-8"))
    failed = {row["url"].rsplit("layers=", 1)[-1]: row for row in access["attempts"]
              if row.get("result") == "HTTP 500"}
    need(set(failed) == {"317", "319"} and all(not row["returned_feature_bytes"] for row in failed.values()),
         "MGN 2024 feature-access blocker is incomplete or changed")
    need(bool(access.get("restoration_request", "").strip()), "exact restoration request is missing")
    crosswalk, settlements = build_records()
    need(len(crosswalk) == 190, "municipality join incomplete")
    need(len({row["dane_municipality_code"] for row in crosswalk}) == 190,
         "municipality codes are not one-to-one")
    need(len({row["location_id"] for row in crosswalk}) == 190, "crosswalk subject IDs are not unique")
    need(Counter(row["match_method"] for row in crosswalk) == {
        "department+accent/case-normalized exact name": 182,
        "department+explicit source-name alias; unique DANE row": 8,
    }, "unexpected exact-name/alias balance")
    need(Counter(row["dane_department_name"] for row in crosswalk) == {
        "CAUCA": 42, "PUTUMAYO": 13, "VALLE DEL CAUCA": 42,
        "RISARALDA": 14, "CÓRDOBA": 30, "QUINDÍO": 12, "HUILA": 37,
    }, "the seven complete department cohorts do not match the pinned parent scope")
    need(len(settlements) == 2431, "assigned DANE settlement-row count differs")
    need(Counter(row["dane_type"] for row in settlements) == {"CM": 190, "CP": 2241},
         "assigned settlement type counts differ")
    cm = Counter(row["municipality_code"] for row in settlements if row["dane_type"] == "CM")
    need(len(cm) == 190 and set(cm.values()) == {1}, "each assigned municipality must have exactly one CM point")
    need({row["municipality_code"] for row in settlements} == {row["dane_municipality_code"] for row in crosswalk},
         "settlement rows do not cover all 190 assigned municipality codes")
    cm_points = {row["municipality_code"]: (row["longitude"], row["latitude"])
                 for row in settlements if row["dane_type"] == "CM"}
    need(all((row["dane_municipality_localization"]["longitude"],
              row["dane_municipality_localization"]["latitude"]) == cm_points[row["dane_municipality_code"]]
             for row in crosswalk), "municipal-seat coordinates differ between the two DANE workbooks")

    for name, expected in render_outputs().items():
        path = ROOT / name
        need(path.is_file(), f"generated output missing: {name}")
        need(path.read_bytes() == expected, f"generated output is stale or nondeterministic: {name}")
    output_rows = list(csv.DictReader((ROOT / "settlement-records.csv").open(encoding="utf-8", newline="")))
    need(len(output_rows) == 2431, "retained CSV row count differs")

    # Negative control: a duplicate current administrative code must be rejected.
    altered = [dict(row) for row in crosswalk]
    altered[1]["dane_municipality_code"] = altered[0]["dane_municipality_code"]
    rejected = len({row["dane_municipality_code"] for row in altered}) != 190
    need(rejected, "duplicate-code negative control did not reject")
    return {"members": 190, "departments": 7, "municipality_matches": 190,
            "exact_name_matches": 182, "explicit_aliases": 8,
            "settlement_rows": 2431, "municipal_seats": 190,
            "named_centers": 2241, "municipal_seat_coordinate_matches": 190,
            "duplicate_code_negative_control": "rejected",
            "current_MGN_2024_polygon_rows": "unavailable; do not infer geometry from code/point list"}


if __name__ == "__main__":
    print("PASS: " + json.dumps(verify(), ensure_ascii=False, sort_keys=True))
