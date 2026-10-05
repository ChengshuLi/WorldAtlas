#!/usr/bin/env python3
"""Verify final #428 scope/source/geometry outputs and write immutable controls."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
BASELINE = "bfa1c56ef72c1bc3a9d1fcf8263d073a966bf46f"
RUNS = [ROOT / "runs/packet-nine", ROOT / "runs/packet-ten"]
FILES = ["county-assessments.json", "comparison-summary.json", "scope-and-control-checks.json"]


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def run_hash(directory: Path) -> str:
    digest = hashlib.sha256()
    for name in FILES:
        digest.update(name.encode() + b"\0" + sha((directory / name).read_bytes()).encode() + b"\n")
    return digest.hexdigest()


def scope_from_issue(body: str) -> dict:
    start = body.find("<!-- worldatlas-work:v1")
    if start < 0:
        raise ValueError("The actual issue machine contract is missing")
    raw = body[start:].split("\n", 1)[1].split("-->\n", 1)[0]
    contract = json.loads(raw)
    if contract.get("mode") != "geography" or contract.get("owned_paths") != [
        "data/regional-review/regional-review-528e53393a4376b4/"
    ]:
        raise ValueError("Issue ownership contract changed")
    return contract


def main() -> None:
    if subprocess.check_output(["git", "rev-parse", BASELINE], cwd=REPO, text=True).strip() != BASELINE:
        raise ValueError("Pinned baseline commit is unavailable")
    snapshot = json.loads((ROOT / "issue-snapshot.json").read_bytes())
    contract = scope_from_issue(snapshot["body"])
    if snapshot["number"] != 428 or contract["max_prs"] != 2:
        raise ValueError("Wrong issue or PR budget")
    scope = json.loads((ROOT / "scope.json").read_bytes())
    ids = scope["member_location_ids"]
    if len(ids) != 279 or len(set(ids)) != 279 or scope["location_count"] != 279:
        raise ValueError("Issue scope must contain exactly 279 unique IDs")
    digest = sha(("\n".join(ids)).encode())
    if digest != scope["member_location_ids_sha256"]:
        raise ValueError("Exact frozen issue roster hash mismatch")

    outputs = []
    for directory in RUNS:
        rows = json.loads((directory / "county-assessments.json").read_bytes())
        if len(rows) != 279 or len({row["subject_id"] for row in rows}) != 279:
            raise ValueError("Assessment rows are not the exact 279 unique county IDs")
        if {row["subject_id"] for row in rows} != set(ids):
            raise ValueError("Assessment IDs differ from the issue scope")
        summary = json.loads((directory / "comparison-summary.json").read_bytes())
        checks = json.loads((directory / "scope-and-control-checks.json").read_bytes())
        if summary["baseline_commit"] != BASELINE or checks["baseline_commit"] != BASELINE:
            raise ValueError("Result baseline commit differs from the pinned current-main baseline")
        if summary["classification_counts"] != {"insufficient-evidence": 103, "justified": 176}:
            raise ValueError("Expected scoped review classifications changed")
        semantic = summary["unit_identity_semantics_screen"]
        if semantic["nonempty_atlas_and_2018_census_names"] != 279 or semantic["source_shape_type_counts"] != {"ADM2": 279} or semantic["source_role"] != "Counties":
            raise ValueError("County tier/name screen did not pass")
        if semantic["source_atlas_component_count_difference_ids"]:
            raise ValueError("Source and Atlas multipart counts differ for a scoped county")
        if not checks["region_issue_partition_exact"] or checks["region_features_exact"] != 1422:
            raise ValueError("Regional partition/feature checks did not pass")
        if checks["source_national_feature_count"] != 3233 or not checks["source_shape_ids_all_unique"]:
            raise ValueError("National source completeness checks did not pass")
        if checks["source_missing_lookup_negative_control"] != "passed" or checks["shared_helper_positive_negative_controls"] != "passed":
            raise ValueError("Source or shared-helper controls did not pass")
        outputs.append((directory.name, run_hash(directory)))
    if outputs[0][1] != outputs[1][1]:
        raise ValueError("Two complete independent output directories are not byte-identical")

    # Reusing an existing output path must fail before changing preserved evidence.
    before = {name: sha((RUNS[0] / name).read_bytes()) for name in FILES}
    result = subprocess.run(
        [sys.executable, str(ROOT / "reproduce.py"), "--output-dir", "runs/packet-nine"],
        cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False,
    )
    if result.returncode == 0 or "FileExistsError" not in result.stderr:
        raise ValueError("Existing-output negative control did not refuse to overwrite")
    if before != {name: sha((RUNS[0] / name).read_bytes()) for name in FILES}:
        raise ValueError("Existing-output refusal changed prior results")

    control_root = ROOT / "runs"
    controls = [
        {
            "method_id": "issue-scope-and-source-identities",
            "kind": "source",
            "outcome": "passed",
            "positive_control": "All 279 issue IDs match the source shapeIDs, Census crosswalk, and exact state-parent roster.",
            "negative_control": "An unknown source ID and an incomplete issue roster are rejected.",
            "source_count": 3233,
            "issue_scope_sha256_newline_roster": digest,
        },
        {
            "method_id": "equal-area-geometry-screen",
            "kind": "geography",
            "outcome": "passed",
            "positive_control": "Identical polygons return IoU 1; the shared longitude-first transform and positive area control pass.",
            "negative_control": "Disjoint polygons return IoU 0; swapped coordinates differ; the helper rejects a Point as land.",
            "helper_version": "worldatlas-evidence-geometry-v1",
            "control_output_sha256": sha((RUNS[0] / "scope-and-control-checks.json").read_bytes()),
        },
        {
            "method_id": "packet-generator-reproducibility",
            "kind": "generator",
            "outcome": "passed",
            "positive_control": "Two complete output directories have identical hashes and each has 279 unique exact-scope rows.",
            "negative_control": "An existing output directory is refused; previously generated bytes remain unchanged.",
            "run_one_sha256": outputs[0][1],
            "run_two_sha256": outputs[1][1],
        },
    ]
    for row in controls:
        (control_root / f"validation-{row['kind']}.json").write_text(
            json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        )
    summary = {
        "version": 1,
        "issue": 428,
        "baseline_commit": BASELINE,
        "scope_ids": len(ids),
        "scope_roster_sha256_newline_joined": digest,
        "output_directories": [{"name": name, "sha256": value} for name, value in outputs],
        "identical_outputs": True,
        "refuse_existing_output_control": "passed",
        "controls": [f"runs/validation-{row['kind']}.json" for row in controls],
    }
    (control_root / "validation-controls.json").write_text(
        json.dumps(summary, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    )
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
