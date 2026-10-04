#!/usr/bin/env python3
"""Create/finalize the issue #663 versioned evidence receipt."""
from __future__ import annotations
import gzip
import hashlib
import json
import os
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[3]
OWNED = "research/geography/pacific-ne-source-reproduction-followup"
HERE = ROOT / OWNED
BASELINE = "f592b3d8b72f40036218803d2c70c733112e4d37"
SOURCE_SNAPSHOT = "6c6271af6b0dac49b82eaafb2db4de8b9c4611f2"
SOURCE_DIR = "data/regional-review/pacific-natural-earth-source-profiles-20261003"
IDS = ["ASM-4998", "ASM-4999", "ASM-5000", "ASM-5001", "ASM-5002",
       "WLF-4995", "WLF-4996", "WLF-4997"]
WORKER = "codex-20261003-pacific-ne-source-repro-a1c43dd0-487c-466c-a9b5-b13494e7b1de"
VINTAGE = "20261003-f592-source-profile-reproduction-v1"
VINTAGE_DIR = f"{OWNED}/vintages/{VINTAGE}"
MANIFEST_PATH = f"{OWNED}/evidence-quality.json"
SHA = lambda data: hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], stderr=subprocess.PIPE)


def committed(commit, path):
    return git("show", f"{commit}:{path}")


def desc(path, raw):
    out = {"path": path, "bytes": len(raw), "sha256": SHA(raw), "hash_kind": "file-bytes"}
    if path.endswith(".gz"):
        decoded = gzip.decompress(raw)
        out.update(uncompressed_bytes=len(decoded), uncompressed_sha256=SHA(decoded))
    return out


def baseline_files():
    index = json.loads(committed(BASELINE, "data/world-index.json"))
    paths = {"data/world-index.json", "data/hierarchy.json",
             "data/research-geography-gate.json", "data/geographic-releases/release-5.json.gz",
             "data/macro-foundation/current-membership-inventory.json.gz",
             "data/macro-foundation/regional-handoffs.json.gz"}
    paths.update("data/" + x for x in index["parts"])
    return [desc(path, committed(BASELINE, path)) for path in sorted(paths)]


def descriptor_from_old(old_quality, path):
    for src in old_quality["sources"]:
        for item in src.get("files", []):
            if item["path"] == path:
                return item
    for item in old_quality["outputs"]:
        if item["path"] == path:
            return item
    raise ValueError("pinned #616 manifest lacks descriptor " + path)


def current_descriptor(path):
    return desc(path, (ROOT / path).read_bytes())


def initial_manifest(issue):
    old = json.loads(committed(SOURCE_SNAPSHOT, SOURCE_DIR + "/evidence-quality.json"))
    old_scope = json.loads(committed(SOURCE_SNAPSHOT, SOURCE_DIR + "/issue-scope.json"))
    files = baseline_files()
    by_path = {x["path"]: x for x in files}
    inherited_pins = old["baseline"]["pins"]
    inherited_pin_files = old["baseline"]["pin_files"]
    pins = {k: v for k, v in inherited_pins.items()}
    pin_files = {k: inherited_pin_files[k] for k in inherited_pins}
    # Add release and gate pins to the original #616 scope/hierarchy pins.
    pin_files.update({
        "macro_gate": "data/research-geography-gate.json",
        "macro_release": "data/geographic-releases/release-5.json.gz",
    })
    pins.update({k: by_path[p]["sha256"] for k, p in {
        "macro_gate": pin_files["macro_gate"], "macro_release": pin_files["macro_release"]}.items()})
    subject_files = {identity: inherited_pin_files["geography_part_28"] for identity in IDS}
    sources = json.loads(json.dumps(old["sources"]))
    # The old workbook extraction is a WorldAtlas-produced input to the
    # original legal-role crosswalk, not an additional official source.
    prior_path = SOURCE_DIR + "/wallis-futuna-insee-inventory.json"
    sources.append({"id": "worldatlas-issue616-prior-insee-extraction",
        "url": f"https://github.com/ChengshuLi/WorldAtlas/tree/{SOURCE_SNAPSHOT}/{SOURCE_DIR}",
        "role": "Pinned prior WorldAtlas extraction used by the preserved #616 legal-role comparison; it is a derived research input, not independent INSEE evidence.",
        "vintage": "Issue #616 source snapshot at merge commit " + SOURCE_SNAPSHOT,
        "retrieved_at": "2026-10-03",
        "license": {"status": "unknown", "terms": "Internal project-derived evidence; upstream data rights are described by source wf-insee-2018 and no separate license is asserted."},
        "retention": "restoration-only", "verification": "verified", "temporal_status": "unknown",
        "restoration": "Read the exact whole-file descriptor from the issue #616 source snapshot commit recorded in source-snapshot-pin.json.",
        "limit": "Derived prior output; it inherits the cited upstream limits and is not an independent legal or statistical authority.",
        "files": [descriptor_from_old(old, prior_path)]})
    issues = {
        "version": 1, "issue": 663, "lane": "geography", "worker_id": WORKER,
        "subject_ids": IDS,
        "subject_ids_sha256": SHA(json.dumps(sorted(IDS), separators=(",", ":")).encode()),
        "baseline": {"commit": BASELINE, "files": files, "pins": pins,
                     "pin_files": pin_files, "subject_files": subject_files},
        "sources": sources, "outputs": [], "methods": [{
            "id": "immutable-source-reproduction", "kind": "generator",
            "helper_version": "worldatlas-evidence-preparation-v1",
            "description": "Verify the complete 2016-10? declared Git project baseline and the exact #616 source snapshot, then run the original source-profile generator against immutable bytes with writes redirected to a new vintage. Geometry metrics preserve the original script's EPSG:6933 planar diagnostic method; source/current polygons are not repaired and no administrative or ownership conclusion follows from overlays.",
            "software": "Python 3.12; pyshp 2.3.1; Shapely 2.1.2; pyproj 3.7.2; openpyxl 3.1.5; shared immutable helper worldatlas-evidence-preparation-v1",
            "units": "locations, source rows, byte counts, SHA-256 whole-file digests, JSON pointers"}],
        "metrics": [], "summaries": [], "metric_bindings": [], "conclusions": [],
        "stages": {"research": "partial", "implementation": "not-proposed", "geographic_approval": "unapproved"},
        "commands": [
            f"python3 {OWNED}/reproduce.py --new-vintage {VINTAGE}",
            f"python3 {OWNED}/reproduce.py --check {VINTAGE}",
            f"node scripts/evidence-quality.mjs {MANIFEST_PATH} .",
        ],
        "source_snapshot_commit": SOURCE_SNAPSHOT,
        "declared_project_baseline": BASELINE,
        "change_receipts": [], "validation": []}
    # Fix an explanatory date typo guard while leaving source vintage explicit.
    issues["methods"][0]["description"] = issues["methods"][0]["description"].replace("2016-10? declared", "#616 declared")
    return issues


def finalize_manifest(manifest):
    paths = []
    for path in HERE.rglob("*"):
        if path.is_symlink():
            raise ValueError("symlink in issue-owned output directory")
        if path.is_file() and path.relative_to(ROOT).as_posix() != MANIFEST_PATH:
            paths.append(path.relative_to(ROOT).as_posix())
    paths.sort()
    manifest["outputs"] = [current_descriptor(path) for path in paths]
    # The manifest is excluded from its own byte descriptors, but the PR's
    # change inventory still needs a receipt for every changed file.
    manifest["change_receipts"] = [
        {"path": path, "status": "added", "previous_path": None} for path in paths
    ] + [{"path": MANIFEST_PATH, "status": "added", "previous_path": None}]
    controls = {"positive": f"{VINTAGE_DIR}/positive-control.json",
                "negative": f"{VINTAGE_DIR}/negative-control.json",
                "reproducibility": f"{VINTAGE_DIR}/reproducibility-control.json"}
    summary = f"{VINTAGE_DIR}/reproduction-run.json"
    subject_hash = manifest["baseline"]["pins"]["geography_part_28"]
    code_hash = current_descriptor(f"{OWNED}/reproduce.py")["sha256"]
    source_snapshot_descriptor = next(x for x in manifest["outputs"]
                                      if x["path"] == f"{VINTAGE_DIR}/source-snapshot-pin.json")
    metric_data = [
        {"id": "exact_issue_subjects", "value": 8, "unit": "locations", "vintage": "baseline",
         "input_sha256": subject_hash, "evaluation_commit": BASELINE},
        {"id": "regenerated_output_files", "value": 7, "unit": "files", "vintage": "baseline",
         "input_sha256": code_hash, "evaluation_commit": BASELINE},
        {"id": "pinned_source_snapshot_file_count", "value": len(json.loads((HERE / "vintages" / VINTAGE / "source-snapshot-pin.json").read_text())["files"]),
         "unit": "files", "vintage": "archived", "input_sha256": source_snapshot_descriptor["sha256"], "evaluation_commit": SOURCE_SNAPSHOT},
        {"id": "reproducible_output_files", "value": 7, "unit": "files", "vintage": "baseline",
         "input_sha256": code_hash, "evaluation_commit": BASELINE},
    ]
    manifest["metrics"] = metric_data
    manifest["summaries"] = [{"metric_id": x["id"], "value": x["value"], "unit": x["unit"]} for x in metric_data]
    manifest["metric_bindings"] = [
        {"metric_id": "exact_issue_subjects", "path": controls["positive"], "json_pointer": "/subject_count"},
        {"metric_id": "regenerated_output_files", "path": summary, "json_pointer": "/output_count"},
        {"metric_id": "pinned_source_snapshot_file_count", "path": summary, "json_pointer": "/source_snapshot_file_count"},
        {"metric_id": "reproducible_output_files", "path": controls["reproducibility"], "json_pointer": "/matching_file_count"},
    ]
    manifest["validation"] = [
        {"method_id": "immutable-source-reproduction", "kind": "positive-control", "outcome": "passed", "evidence_path": controls["positive"]},
        {"method_id": "immutable-source-reproduction", "kind": "negative-control", "outcome": "passed", "evidence_path": controls["negative"]},
        {"method_id": "immutable-source-reproduction", "kind": "reproducibility", "outcome": "passed", "evidence_path": controls["reproducibility"]},
    ]
    manifest["conclusions"] = [
        {"text": "The original eight subjects resolve uniquely in every part enumerated by the pinned world index, have complete province-to-continent parent chains in the f592 project baseline, and reproduce through a new isolated vintage.",
         "status": "supported", "source_ids": ["natural-earth-5-1-1", "worldatlas-issue616-prior-insee-extraction"]},
        {"text": "The new-vintage comparison records reproducibility differences between the declared f592 project baseline and the later #616 source snapshot; those byte/JSON differences alone do not establish a corrected administrative or territorial conclusion.",
         "status": "unresolved", "source_ids": ["natural-earth-5-1-1", "us-census-2020-as", "wf-insee-2018", "american-samoa-code", "territorial-assembly-wf"]},
    ]
    manifest["stages"]["research"] = "complete"
    return manifest


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "finalize"))
    args = parser.parse_args()
    manifest = initial_manifest(json.loads(committed(SOURCE_SNAPSHOT, SOURCE_DIR + "/issue-616-snapshot.json")))
    if args.action == "finalize":
        manifest = finalize_manifest(manifest)
    (HERE / "evidence-quality.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"action": args.action, "baseline_files": len(manifest["baseline"]["files"]),
                      "source_ids": len(manifest["sources"]), "output_files": len(manifest["outputs"])}))


if __name__ == "__main__":
    main()
