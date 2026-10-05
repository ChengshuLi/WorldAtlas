#!/usr/bin/env python3
"""Reproduce the scoped source crosswalk and immutable-baseline checks.

Run from repository root with the Python standard library. This deliberately
does not infer legal boundary correctness from row counts or geometry validity.
"""
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path.cwd()
PACKET = Path("data/regional-review/regional-review-f834434be524dfdb")
scope = json.loads((ROOT / PACKET / "issue-scope.json").read_text())
pins = json.loads((ROOT / PACKET / "baseline-inputs.json").read_text())
assert pins["baseline_commit"] == "0c6232db2b2f9531a479f0c752f66c4d12013f3b"


def pinned_bytes(path):
    return subprocess.check_output(["git", "show", f"{pins['baseline_commit']}:{path}"], cwd=ROOT)


for entry in pins["files"]:
    raw = pinned_bytes(entry["path"])
    assert len(raw) == entry["bytes"], entry["path"]
    assert hashlib.sha256(raw).hexdigest() == entry["sha256"], entry["path"]

wanted = set(scope["member_location_ids"])
features = {}
for entry in pins["files"]:
    if not entry["path"].startswith("data/geography/") or not entry["path"].endswith(".json"):
        continue
    data = json.loads(pinned_bytes(entry["path"]))
    for feat in data.get("features", []):
        props = feat["properties"]
        if props.get("id") in wanted:
            features[props["id"]] = props

assert len(wanted) == scope["location_count"] == 228
assert set(features) == wanted, (len(features), len(wanted - set(features)))
assert sum(i.startswith("gb:NER:ADM3:") for i in wanted) == 204
assert sum(i.startswith("gb:MRT:ADM2:") for i in wanted) == 13
assert sum(i.startswith("atlas:physical:") for i in wanted) == 10
assert sum(i.startswith("atlas:city:") for i in wanted) == 1

# Negative controls: a fabricated subject and a corrupted pin must not pass.
assert "gb:NER:ADM3:NOT-A-REAL-SHAPE" not in features
sample = pins["files"][0]
assert hashlib.sha256((ROOT / sample["path"]).read_bytes() + b"x").hexdigest() != sample["sha256"]

print(json.dumps({"baseline_commit": pins["baseline_commit"],
                  "pinned_files_verified": len(pins["files"]),
                  "scoped_subjects_reproduced": len(features),
                  "source_class_counts": {"NER_ADM3": 204, "MRT_ADM2": 13,
                                           "physical_ecoregion_fragments": 10,
                                           "city_composite": 1},
                  "positive_controls": "all pinned inputs hash and size match; all 228 exact IDs found",
                  "negative_controls": "unknown ID absent; modified bytes fail pinned digest",
                  "limits": "structural reproduction only; not proof of boundary, role, completeness, license, or parent correctness"},
                 indent=2))
