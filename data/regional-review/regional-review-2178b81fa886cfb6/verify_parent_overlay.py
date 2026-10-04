#!/usr/bin/env python3
"""Bind the README parent-overlay table to generated assessment metrics."""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
BEGIN = "<!-- parent-overlay-metrics:begin -->"
END = "<!-- parent-overlay-metrics:end -->"


def build_table(assessment):
    rows = [
        "| State | Compared union | Intersection / 2018 ADM1 | 2018 ADM1 denominator (km²) | Union area (km²) | Symmetric difference (km²) |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    fields = [
        ("2018 ADM2 county union", "source_adm1_county_union_area_km2",
         "source_adm2_union_symdiff_km2", "source_adm2_union_intersection_over_adm1_pct"),
        ("current parent cohort union", "current_parent_cohort_union_area_km2",
         "current_parent_union_symdiff_km2", "current_parent_union_intersection_over_adm1_pct"),
    ]
    cohorts = assessment["complete_state_parent_cohorts"]
    for state in ("California", "Washington"):
        cohort = cohorts[state]
        denominator = cohort["source_adm1_area_km2"]
        for label, union_field, difference_field, percent_field in fields:
            union_area = cohort[union_field]
            difference = cohort[difference_field]
            percent = cohort[percent_field]
            intersection_area = (union_area + denominator - difference) / 2
            computed_percent = round(intersection_area / denominator * 100, 6)
            if computed_percent != percent:
                raise ValueError(f"{state} {label} percentage does not match its areas")
            rows.append(
                f"| {state} | {label} | {percent:.6f}% | {denominator:.6f} | "
                f"{union_area:.6f} | {difference:.6f} |"
            )
    return "\n".join(rows)


def check_narrative(assessment, readme):
    if readme.count(BEGIN) != 1 or readme.count(END) != 1:
        raise ValueError("README must contain exactly one parent-overlay table marker pair")
    actual = readme.split(BEGIN, 1)[1].split(END, 1)[0].strip()
    expected = build_table(assessment)
    if actual != expected:
        raise ValueError("README parent-overlay table differs from generated assessment metrics")
    return expected


def check_current_baseline(scope, correction):
    repo = ROOT.parents[2]
    baseline = correction["baseline_commit"]
    v5 = "277b8ecbb3199ae3d5fb07bab96353d17a049b1c"

    def git_blob(commit, path):
        return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=repo)

    if subprocess.run(["git", "merge-base", "--is-ancestor", baseline, "HEAD"], cwd=repo,
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0:
        raise ValueError("Recorded current baseline is not an ancestor of this checkout")
    for file in correction["preserved_original_files"]:
        raw = git_blob(baseline, file["path"])
        if len(raw) != file["bytes"] or hashlib.sha256(raw).hexdigest() != file["sha256"]:
            raise ValueError(f"Preserved issue-baseline bytes do not match: {file['path']}")

    pins = correction["current_geographic_baseline"]
    if hashlib.sha256(git_blob(baseline, "data/world-index.json")).hexdigest() != pins["current_main_world_index_sha256"]:
        raise ValueError("World index bytes differ from the recorded current main baseline")
    if hashlib.sha256(git_blob(baseline, "data/hierarchy.json")).hexdigest() != pins["current_main_hierarchy_sha256"]:
        raise ValueError("Hierarchy bytes differ from the recorded current main baseline")
    v5_hierarchy = git_blob(v5, "data/hierarchy.json")
    if hashlib.sha256(v5_hierarchy).hexdigest() != scope["release"]["hierarchy_sha256"]:
        raise ValueError("Assigned V5 hierarchy bytes disagree with the preserved scope pin")

    ids = set(scope["member_location_ids"])

    def assigned_features(commit):
        index = json.loads(git_blob(commit, "data/world-index.json"))
        found = {}
        for part in index["parts"]:
            for feature in json.loads(git_blob(commit, f"data/{part}"))["features"]:
                location_id = feature["properties"]["id"]
                if location_id in ids:
                    if location_id in found:
                        raise ValueError(f"Duplicate pinned location ID: {location_id}")
                    found[location_id] = feature
            if len(found) == len(ids):
                break
        if set(found) != ids:
            raise ValueError(f"Current baseline is missing assigned IDs: {sorted(ids-set(found))[:5]}")
        return found

    current = assigned_features(baseline)
    pinned = assigned_features(v5)
    if current != pinned:
        changed = sorted(location_id for location_id in ids if current[location_id] != pinned[location_id])
        raise ValueError(f"Assigned V5/current baseline location features differ: {changed[:5]}")

    current_hierarchy = {row["id"]: row for row in json.loads(git_blob(baseline, "data/hierarchy.json"))}
    pinned_hierarchy = {row["id"]: row for row in json.loads(v5_hierarchy)}
    for location_id in ids:
        current_node = current[location_id]["properties"]
        pinned_node = pinned[location_id]["properties"]
        while current_node.get("parent_id"):
            parent_id = current_node["parent_id"]
            current_node = current_hierarchy.get(parent_id)
            pinned_node = pinned_hierarchy.get(parent_id)
            if current_node is None or pinned_node is None or current_node != pinned_node:
                raise ValueError(f"Assigned V5/current baseline parent chain differs: {location_id} -> {parent_id}")

    stamp = subprocess.check_output(["node", "scripts/stamp-prepared.mjs", "--hash"], cwd=repo, text=True).strip()
    if stamp != pins["current_main_footprints_recomputed"] or stamp != scope["release"]["footprints_sha256"]:
        raise ValueError("Current baseline footprint hash differs from the assigned V5 release pin")
    return len(ids)


def check_correction_record(assessment, scope, correction):
    if correction["issue"] != 600 or correction["parent_packet_issue"] != 487:
        raise ValueError("Correction record does not identify issue #600 and parent packet #487")
    release = scope["release"]
    pins = correction["current_geographic_baseline"]
    if (release["id"], release["version"], release["hierarchy_sha256"], release["footprints_sha256"]) != (
        pins["region_release_id"], pins["region_release_version"],
        pins["region_hierarchy_sha256"], pins["region_footprints_sha256"]
    ):
        raise ValueError("Correction record release pins differ from the original assigned scope")
    actual_rows = []
    for state in ("California", "Washington"):
        cohort = assessment["complete_state_parent_cohorts"][state]
        actual_rows.extend([
            {"state": state, "cohort": "2018 ADM2 county union",
             "intersection_pct": cohort["source_adm2_union_intersection_over_adm1_pct"],
             "denominator_2018_adm1_km2": cohort["source_adm1_area_km2"],
             "union_area_km2": cohort["source_adm1_county_union_area_km2"],
             "symmetric_difference_km2": cohort["source_adm2_union_symdiff_km2"]},
            {"state": state, "cohort": "current parent cohort union",
             "intersection_pct": cohort["current_parent_union_intersection_over_adm1_pct"],
             "denominator_2018_adm1_km2": cohort["source_adm1_area_km2"],
             "union_area_km2": cohort["current_parent_cohort_union_area_km2"],
             "symmetric_difference_km2": cohort["current_parent_union_symdiff_km2"]},
        ])
    if actual_rows != correction["reproduced_metrics"]["rows"]:
        raise ValueError("Correction record metric rows differ from generated assessment values")


def main():
    assessment = json.loads((ROOT / "assessment.json").read_text(encoding="utf-8"))
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    scope = json.loads((ROOT / "scope.json").read_text(encoding="utf-8"))
    correction = json.loads((ROOT / "parent-overlay-correction.json").read_text(encoding="utf-8"))
    check_narrative(assessment, readme)
    check_correction_record(assessment, scope, correction)
    check_current_baseline(scope, correction)

    # Mutation control: a changed Washington result must invalidate the retained prose.
    changed = copy.deepcopy(assessment)
    changed["complete_state_parent_cohorts"]["Washington"][
        "current_parent_union_intersection_over_adm1_pct"
    ] += 0.001
    try:
        check_narrative(changed, readme)
    except ValueError:
        pass
    else:
        raise SystemExit("FAIL: negative control accepted a changed Washington metric")
    print("PASS: four per-state overlay rows match the assessment; changed-metric negative control rejected")


if __name__ == "__main__":
    main()
