#!/usr/bin/env python3
"""Exercise rejection paths against the exact #1161 pinned baseline."""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MODULE = HERE / "reproduce-crosswalk.py"
spec = importlib.util.spec_from_file_location("crosswalk_runner", MODULE)
runner = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(runner)

issue, work, descriptors, by_path = runner.issue_contract(HERE)
results = []

def rejects(label, operation):
    try:
        operation()
    except runner.EvidenceError as exc:
        results.append({"control": label, "rejected": True, "reason": str(exc)})
    else:
        raise SystemExit(f"negative control unexpectedly passed: {label}")

def mutated(path, mutate):
    raw = runner.git_bytes(ROOT, runner.BASELINE, path)
    return mutate(raw)

def edit_json(raw, change):
    obj = json.loads(raw)
    change(obj)
    return (json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n").encode()

# A geometry coordinate and its corresponding pinned Atlas part are altered.
atlas_path = "data/geography/part-9.json"
atlas_raw = runner.git_bytes(ROOT, runner.BASELINE, atlas_path)
def alter_geometry(obj):
    for feature in obj["features"]:
        if feature.get("geometry") and feature.get("properties", {}).get("id"):
            feature["geometry"] = None
            return
    raise AssertionError("no geometry found")
altered_atlas = edit_json(atlas_raw, alter_geometry)
rejects("altered Atlas geometry bytes", lambda: runner.checked_bytes(atlas_path, altered_atlas, by_path[atlas_path]))

meta_path = next(p for p in by_path if p.endswith("GRC/ADM3/geoBoundaries-GRC-ADM3-metaData.json"))
meta_raw = runner.git_bytes(ROOT, runner.BASELINE, meta_path)
altered_meta = edit_json(meta_raw, lambda obj: obj.update({"boundaryYear": "2099"}))
rejects("altered source metadata bytes", lambda: runner.checked_bytes(meta_path, altered_meta, by_path[meta_path]))

source_path = next(p for p in by_path if p.endswith("GRC/ADM3/geoBoundaries-GRC-ADM3.geojson"))
source_raw = runner.git_bytes(ROOT, runner.BASELINE, source_path)
altered_source = source_raw + b" "
rejects("altered source bytes", lambda: runner.checked_bytes(source_path, altered_source, by_path[source_path]))

legacy_path = runner.OLD_SCRIPT
legacy_raw = runner.git_bytes(ROOT, runner.BASELINE, legacy_path)
rejects("altered legacy reproduction code", lambda: runner.checked_bytes(legacy_path, legacy_raw + b"\n", by_path[legacy_path]))

rejects("wrong immutable baseline", lambda: runner.check_baseline("0" * 40))
subjects = work["evidence_quality"]["subject_ids"]
rejects("duplicate Atlas subject identity", lambda: runner.exact_occurrences(subjects[:2], [subjects[0], subjects[0], subjects[1]], "Atlas"))
rejects("duplicate source subject identity", lambda: runner.exact_occurrences(subjects[:2], [subjects[0], subjects[0], subjects[1]], "source"))

# The source-layer parser must catch duplicate source feature IDs inside a full layer.
source_doc = json.loads(source_raw)
source_doc["features"].append(dict(source_doc["features"][0]))
duplicate_source_raw = json.dumps(source_doc, ensure_ascii=False).encode()
meta = json.loads(runner.git_bytes(ROOT, runner.BASELINE, meta_path))
rejects("duplicate native source feature ID", lambda: runner.inspect_source_file(source_path, duplicate_source_raw, by_path, subjects, meta))

# Existing output is tested by an actual second invocation with the already-created run ID.
existing_run = "run-author-b"
existing_dir = HERE / "runs" / existing_run
before = {str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(existing_dir.iterdir()) if p.is_file()}
proc = subprocess.run([sys.executable, str(MODULE), "--run-id", existing_run], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
after = {str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(existing_dir.iterdir()) if p.is_file()}
if proc.returncode == 0 or before != after:
    raise SystemExit("existing-output negative control failed or changed existing bytes")
results.append({"control": "existing output directory", "rejected": True, "existing_bytes_unchanged": True,
                "error_tail": proc.stderr.decode("utf-8", "replace")[-500:]})

receipt = {"version": 1, "issue": runner.ISSUE, "method_id": "bounded-reproduction", "kind": "negative-control", "outcome": "passed",
           "checked_at": runner.dt.datetime.now(runner.dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
           "baseline_commit": runner.BASELINE, "runner_sha256": hashlib.sha256(MODULE.read_bytes()).hexdigest(),
           "controls": results, "control_count": len(results), "all_rejected": all(x["rejected"] for x in results)}
if not receipt["all_rejected"]:
    raise SystemExit("one or more negative controls were not rejected")
(HERE / "negative-controls.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(receipt, ensure_ascii=False, indent=2))
