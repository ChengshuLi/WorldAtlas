#!/usr/bin/env python3
"""Authenticate retained native physical source and upstream method bytes."""
import hashlib
import json
import os
import resource
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OWNED = "research/geography/norway-adm2-source-fit-1492/"
COMMIT = "088ab05aeb16ddfa8f0c43e596533f3f11d5fcec"
BASELINE_SHA = "45d4356a46beddea43bfbd20231e0bf3671aa349643de29d0fa088ed5fbf5713"
VINTAGE = "physical-source-custody-20261008"
OUTPUTS = ["physical-source-custody.json"]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    started = time.monotonic()
    script_hash = sha(Path(__file__).read_bytes())
    admission_raw = (ROOT / OWNED / "vintages/baseline-20261008/baseline-admission.json").read_bytes()
    if sha(admission_raw) != BASELINE_SHA:
        raise SystemExit("Pinned baseline admission changed")
    admission = json.loads(admission_raw)
    sys.path.insert(0, str(ROOT / "scripts"))
    from evidence.immutable import Baseline, NewVintage, canonical_json

    baseline = Baseline(ROOT, COMMIT, admission["baseline_files"])
    writer = NewVintage(baseline, OWNED, VINTAGE, OUTPUTS)
    reserve = 1024 * 1024
    baseline.admit("reserved-output:physical-source-custody.json", reserve)
    baseline.admit("reserved-output:publication.json", 4096)

    manifest_path = "coordination/engineering/global-physical-comparison-20261006/evidence-quality.json"
    manifest = json.loads(baseline.pinned_bytes(manifest_path))
    original = next((x for x in manifest["sources"] if x.get("id") == "gshhg-2.3.7-original-binary"), None)
    reader = next((x for x in manifest["sources"] if x.get("id") == "gmt-6.5-native-reader-primary-context"), None)
    if not original or not reader or original.get("retention") != "retained":
        raise SystemExit("Physical comparison manifest lacks retained original source custody")
    upstream = {}
    for x in manifest["outputs"]:
        if x.get("path") in {
            "coordination/engineering/global-physical-comparison-20261006/producer.py",
            "coordination/engineering/global-physical-comparison-20261006/comparison.py",
            "coordination/engineering/global-physical-comparison-20261006/inputs.py",
            "coordination/engineering/global-physical-comparison-20261006/immutable.py",
            "coordination/engineering/global-physical-comparison-20261006/ellipsoidal_area.py",
            "coordination/engineering/global-physical-comparison-20261006/input-config.json",
        }:
            upstream[x["path"]] = x

    additional = []
    for source in (original, reader):
        additional.extend(source.get("files", []))
    additional.extend(upstream.values())
    if len({x["path"] for x in additional}) != len(additional):
        raise SystemExit("Duplicate source/method pins")
    for descriptor in additional:
        name = descriptor["path"]
        if name in baseline.pins:
            if baseline.pins[name] != {k: descriptor[k] for k in ("path", "bytes", "sha256", "hash_kind")}:
                raise SystemExit("Extra source descriptor collides with a baseline pin")
            continue
        baseline.pins[name] = {k: descriptor[k] for k in ("path", "bytes", "sha256", "hash_kind")}
        raw = baseline.pinned_bytes(name)
        if len(raw) != descriptor["bytes"] or sha(raw) != descriptor["sha256"]:
            raise SystemExit("Original physical source or producer code differs from its pinned manifest")

    records = []
    for source in (original, reader):
        files = []
        for descriptor in source["files"]:
            raw = baseline.pinned_bytes(descriptor["path"])
            files.append({"path": descriptor["path"], "bytes": len(raw),
                          "sha256": sha(raw), "role": descriptor.get("role")})
        records.append({"id": source["id"], "role": source.get("role"),
                        "vintage": source.get("vintage"),
                        "retrieved_at": source.get("retrieved_at"),
                        "url": source.get("url"), "license": source.get("license"),
                        "verification": source.get("verification"),
                        "temporal_status": source.get("temporal_status"),
                        "limit": source.get("limit"), "files": files})

    output = {
        "version": 1,
        "status": "physical-source-and-upstream-method-bytes-authenticated",
        "issue": 1492,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "baseline": {"commit": COMMIT, "admission_sha256": BASELINE_SHA,
                     "files": len(admission["baseline_files"]),
                     "initial_pinned_bytes": admission["pinned_file_bytes"]},
        "physical_sources": records,
        "upstream_method_files": [
            {"path": path, "bytes": baseline.pins[path]["bytes"],
             "sha256": baseline.pins[path]["sha256"], "hash_kind": "file-bytes"}
            for path in sorted(upstream)],
        "upstream_method": next((m for m in manifest["methods"] if m.get("id") == "complete-nested-source-comparison"), None),
        "producer": {"path": str(Path(__file__).relative_to(ROOT)), "sha256": script_hash,
                     "python": sys.version, "elapsed_seconds": time.monotonic()-started},
        "admission": {"phase_input_bytes": sum(baseline.consumed.values()),
                      "phase_limit_bytes": baseline.max_phase_bytes,
                      "pre_read_output_reserve_bytes": reserve,
                      "disk_free_after_bytes": shutil.disk_usage(ROOT).free,
                      "physical_memory_bytes": os.sysconf("SC_PAGE_SIZE")*os.sysconf("SC_PHYS_PAGES"),
                      "process_max_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},
        "limits": ["The source-manifest terms preserve the original GSHHG license-text discrepancy and report verification as unverified.",
                   "This verifies exact original native input and method/code byte custody; it does not rerun the global 95,173-component producer or establish physical truth, source accuracy, date, registration, political authority, or water status."]
    }
    raw = canonical_json(output)
    if len(raw) > reserve:
        raise SystemExit("Physical custody output exceeded its admitted reserve")
    if sha(Path(__file__).read_bytes()) != script_hash:
        raise SystemExit("Producer code changed during source admission")
    records = writer.publish({"physical-source-custody.json": output})
    print(json.dumps({"status": output["status"], "sources": [x["id"] for x in output["physical_sources"]],
                      "authenticated_files": len(additional),
                      "phase_bytes": sum(baseline.consumed.values()), "outputs": records}, indent=2))


if __name__ == "__main__":
    main()
