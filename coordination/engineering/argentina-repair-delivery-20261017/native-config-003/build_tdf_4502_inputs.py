#!/usr/bin/env python3
import gzip, hashlib, json
from collections import Counter, defaultdict
from pathlib import Path
from shapely.geometry import Point, shape

PKG = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent
REC = PKG / "recovered-4502-scope-20261021"
strata_path = REC / "exact-residual-and-research-strata.json"
comparison_path = REC / "official-key-comparison.json"
intervals_path = PKG / "original-scope/original-intervals.json.gz"
stage_path = PKG / "source-stage-001/original-stage-inputs.json"
physical_path = PKG / "physical-001/whole-target-support.json"
base_config_path = PKG / "native-config-002/source-evidence-config.json"

def read_json(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

strata = read_json(strata_path)
comparison = read_json(comparison_path)
scope = next(s for s in strata["research_strata"] if s["label"] == "same_department_context_without_original_foreign_flag")
keys_list = scope["keys_y_x_owner"]
keys = [tuple(k) for k in keys_list]
assert len(keys) == 4502 and len(set(keys)) == 4502
assert Counter(k[2] for k in keys) == {8100: 537, 8196: 3965}
assert sum(s["cells"] for s in strata["research_strata"]) == 6149
assert [(s["label"], s["cells"]) for s in strata["research_strata"]] == [
    ("same_department_context_without_original_foreign_flag", 4502),
    ("same_department_context_with_retained_CHL_contact", 1),
    ("no_current_IGN_department_contact", 586),
    ("other_residual_not_in_this_comparison", 1060),
]
comparison_rows = {(r["y"], r["x"], r["owner"]): r for r in comparison["keys"]}
assert len(comparison_rows) == 5089 and all(k in comparison_rows for k in keys)
for k in keys:
    r = comparison_rows[k]
    assert r["physical_class"] == "land"
    assert len(r["official_hits"]) == 1 and r["official_ties"] == []
    assert not any("foreign" in reason for reason in r["retained_hold_reasons"])

intervals = json.loads(gzip.decompress(intervals_path.read_bytes()))
interval_owner = {}
for ordinal, row in enumerate(intervals):
    y, x0, x1, owners, source_indices, klass = row
    for owner in owners:
        interval_owner[(y, x0, owner)] = ordinal
ordinals = set()
for y, x, owner in keys:
    assert any(row[0] == y and row[1] <= x < row[2] and owner in row[3] and row[5] == "land" for row in intervals)
    ordinals.add(next(i for i, row in enumerate(intervals)
                      if row[0] == y and row[1] <= x < row[2] and owner in row[3]))
assert len(ordinals) == 1110

stage = read_json(stage_path)
stage_rows = {r["target"]: r for r in stage}
target_ids = {
    8100: "gb:ARG:ADM2:61730980B7053808465014",
    8196: "gb:ARG:ADM2:61730980B87507155551581",
}
assert set(target_ids.values()) <= set(stage_rows)
physical = read_json(physical_path)
physical_rows = {r["target"]: r for r in physical["results"]}
classes = Counter()
issue_hits = Counter()
for owner, target_id in target_ids.items():
    row = physical_rows[target_id]
    land = shape(row["support"]["mapped_land_support"])
    water = shape(row["support"]["mapped_inland_water_support"])
    outside = shape(row["support"]["outside_mapped_L1_context"])
    issue = shape(row["issues"][0]["geometry"])
    owner_keys = [k for k in keys if k[2] == owner]
    for k in owner_keys:
        record = comparison_rows[k]
        point = Point(record["longitude"], record["latitude"])
        land_hit, water_hit, outside_hit, issue_hit = (
            land.covers(point), water.covers(point), outside.covers(point), issue.intersects(point))
        assert land_hit and not water_hit and not outside_hit and not issue_hit
        classes["mapped_land_support"] += 1
        issue_hits["no_center_issue_hit"] += 1

candidate_rows = []
by_y = defaultdict(list)
for y, x, owner in sorted(keys):
    by_y[y].append((x, owner))
for y, rowkeys in sorted(by_y.items()):
    runs = []
    for x, owner in rowkeys:
        if runs and runs[-1][1] == x and runs[-1][2] == owner:
            runs[-1][1] = x + 1
        else:
            runs.append([x, x + 1, owner])
    candidate_rows.append({"y": y, "runs": runs})
assert sum(run[1] - run[0] for row in candidate_rows for run in row["runs"]) == 4502

coverage_by_owner = defaultdict(list)
for y, rowkeys in sorted(by_y.items()):
    for owner in (8100, 8196):
        xs = [x for x, o in rowkeys if o == owner]
        if not xs:
            continue
        runs = []
        for x in xs:
            if runs and runs[-1][1] == x:
                runs[-1][1] = x + 1
            else:
                runs.append([x, x + 1, "mapped_land_support"])
        coverage_by_owner[owner].append({"y": y, "runs": runs})

base = read_json(base_config_path)
stage_target_records = []
for owner, target_id in target_ids.items():
    s = stage_rows[target_id]
    stage_target_records.append({
        "id": target_id,
        "target_id": target_id,
        "pixelIndex": owner,
        "base_geometry": s["selected"]["geometry"],
        "source_family": "gb:ARG:ADM2",
        "source_receipt_sha256": physical["source_metadata_receipts"][0]["sha256"] if False else "5465e326f125749494f4cf4c15dab8fce955f3513e551019d6af34934d901565",
        "coverage_classes": ["mapped_land_support"],
        "territorial_exclusions": [],
        "coverage_rows": coverage_by_owner[owner],
    })
config = json.loads(json.dumps(base))
config["selector"] = {"commit": "b163f0c1a496dd8a341d646458e5f8ecac076e12",
                      "path": "data/ownership-selection.json"}
config["source_evidence"]["targets"] = stage_target_records
config["source_evidence"]["families"] = [{
    "source_id": "gb:ARG:ADM2",
    "parts": base["source_evidence"]["families"][0]["parts"],
}]
patch = {"rows": candidate_rows}
summary = {
    "kind": "arg-tdf-exact-4502-candidate-input-binding-v1",
    "package_id": strata["package_id"],
    "roster": {"cells": len(keys), "owners": {"8100": 537, "8196": 3965},
               "original_interval_ordinals": len(ordinals),
               "canonical_tuple_sha256": hashlib.sha256(json.dumps(keys_list, separators=(",", ":")).encode()).hexdigest()},
    "strata_complement": {"CHL_contact": 1, "no_department_contact": 586, "other_residual": 1060,
                          "held_total": 1647, "credit": 0},
    "physical_center_check": {"mapped_land_support": dict(Counter({str(k): v for k, v in classes.items()})),
                              "contradictory_issue_center_hits": 0, "whole_target_issue_preserved": True,
                              "whole_cell_qualification": False},
    "input_pins": {
        "exact_residual_and_research_strata": {"bytes": strata_path.stat().st_size, "sha256": sha(strata_path)},
        "official_key_comparison": {"bytes": comparison_path.stat().st_size, "sha256": sha(comparison_path)},
        "original_intervals_gzip": {"bytes": intervals_path.stat().st_size, "sha256": sha(intervals_path)},
        "physical_whole_target_support": {"bytes": physical_path.stat().st_size, "sha256": sha(physical_path)},
        "original_stage_inputs": {"bytes": stage_path.stat().st_size, "sha256": sha(stage_path)},
        "selector_commit": "b163f0c1a496dd8a341d646458e5f8ecac076e12",
    },
    "limits": ["Candidate input only; no credit, accepted repair, present-day authority, or whole-cell claim.",
               "The 1 CHL-contact key, 586 no-department-contact keys, and 1,060 other residual keys remain outside this candidate.",
               "The original target-level contradictory land/water issue geometries are retained; the center join only found 4,502 land-support hits and no issue-line hits."],
}
(OUT / "native-patch.json").write_text(json.dumps(patch, separators=(",", ":")) + "\n")
(OUT / "source-evidence-config.json").write_text(json.dumps(config, separators=(",", ":")) + "\n")
(OUT / "candidate-binding.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps({"keys": len(keys), "owners": dict(Counter(k[2] for k in keys)),
                  "intervals": len(ordinals), "patch_rows": len(candidate_rows),
                  "coverage_rows": {str(k): len(v) for k,v in coverage_by_owner.items()},
                  "physical_centers": dict(classes), "issue_center_hits": sum(v for k,v in issue_hits.items()),
                  "config_sha256": sha(OUT/"source-evidence-config.json"),
                  "patch_sha256": sha(OUT/"native-patch.json"),
                  "binding_sha256": sha(OUT/"candidate-binding.json")}, sort_keys=True))

