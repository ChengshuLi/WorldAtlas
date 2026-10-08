#!/usr/bin/env python3
"""Authenticate the 15 actual component delivery geometries under bounded admission."""
import gzip
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
BASELINE_COMMIT = "088ab05aeb16ddfa8f0c43e596533f3f11d5fcec"
BASELINE_SHA = "45d4356a46beddea43bfbd20231e0bf3671aa349643de29d0fa088ed5fbf5713"
VINTAGE = "component-geometries-20261008"
OUTPUTS = ["selected-components.json"]
PHYSICAL = "coordination/engineering/global-physical-comparison-20261006/"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    started = time.monotonic()
    script_raw = Path(__file__).read_bytes()
    script_hash = sha(script_raw)
    admission_raw = (ROOT / OWNED / "vintages/baseline-20261008/baseline-admission.json").read_bytes()
    if sha(admission_raw) != BASELINE_SHA:
        raise SystemExit("Pinned baseline admission changed")
    admission = json.loads(admission_raw)
    sys.path.insert(0, str(ROOT / "scripts"))
    from evidence.immutable import Baseline, NewVintage, canonical_json

    base = Baseline(ROOT, BASELINE_COMMIT, admission["baseline_files"])
    writer = NewVintage(base, OWNED, VINTAGE, OUTPUTS)
    reserve = 4 * 1024 * 1024
    base.admit("reserved-output:selected-components.json", reserve)
    base.admit("reserved-output:publication.json", 4096)

    config_path = PHYSICAL + "input-config.json"
    manifest = json.loads(base.pinned_bytes(PHYSICAL + "evidence-quality.json"))
    cfg_pin = next(x for x in manifest["outputs"] if x.get("path") == config_path)
    base.pins[config_path] = {k: cfg_pin[k] for k in ("path", "bytes", "sha256", "hash_kind")}
    config_raw = base.pinned_bytes(config_path)
    config = json.loads(config_raw)
    descriptors = [x for x in config["inputs"] if x.get("kind") == "components"]
    if len(descriptors) != 11 or sum(x["uncompressed_bytes"] for x in descriptors) != 90_788_892:
        raise SystemExit("Unexpected original component delivery inventory")
    # Authenticate descriptor authority to the pinned upstream evidence manifest.
    if cfg_pin["sha256"] != sha(config_raw):
        raise SystemExit("Input configuration differs from pinned evidence manifest")
    for d in descriptors:
        if d["path"] in base.pins:
            raise SystemExit("Component payload unexpectedly collides with baseline pin")
        base.pins[d["path"]] = {k: d[k] for k in ("path", "bytes", "sha256", "hash_kind")}

    selected_stage = json.loads((ROOT / OWNED / "vintages/official-source-capture-20261008/selected-source-rows.json").read_bytes())
    selected_ids = selected_stage["family_context"]["selected_component_ids"]
    if len(selected_ids) != 15 or len(set(selected_ids)) != 15:
        raise SystemExit("Selected source roster is not 15 unique component IDs")
    wanted = set(selected_ids)
    # Source rows and family-scope output bytes are explicit phase inputs.
    selected_path = OWNED + "vintages/official-source-capture-20261008/selected-source-rows.json"
    family_path = OWNED + "vintages/family-scope-20261008/family-scope.json"
    for path in (selected_path, family_path):
        raw = (ROOT / path).read_bytes()
        base.admit(path, len(raw))
    family = json.loads((ROOT / family_path).read_bytes())
    family_ids = set(family["scope"]["complete_component_ids"])
    if len(family_ids) != 400 or not wanted <= family_ids:
        raise SystemExit("Selected components do not fit the preserved complete family")

    # Only after complete inventory/output reservation, admit, decompress and decode inputs.
    rows = {}
    all_ids = set()
    duplicate_ids = []
    shard_stats = []
    total_records = 0
    for d in descriptors:
        raw = base.pinned_bytes(d["path"])
        if len(raw) != d["bytes"] or sha(raw) != d["sha256"]:
            raise SystemExit("Component source raw bytes differ from descriptor")
        decoded_size = d["uncompressed_bytes"]
        base.admit("decoded:" + d["path"], decoded_size)
        decoded = gzip.decompress(raw)
        if len(decoded) != decoded_size or sha(decoded) != d["uncompressed_sha256"]:
            raise SystemExit("Component source decoded bytes differ from descriptor")
        collection = json.loads(decoded)
        features = collection.get("features") if isinstance(collection, dict) else None
        if collection.get("type") != "FeatureCollection" or not isinstance(features, list):
            raise SystemExit("Original component delivery is not a GeoJSON FeatureCollection")
        count = 0
        for record in features:
            total_records += 1
            count += 1
            identity = record.get("id")
            if identity in all_ids:
                duplicate_ids.append(identity)
            all_ids.add(identity)
            if identity in wanted:
                if identity in rows:
                    raise SystemExit("Duplicate selected identity in original delivery")
                if not isinstance(record.get("geometry"), dict):
                    raise SystemExit("Selected component record lacks geometry")
                rows[identity] = record
        shard_stats.append({"path": d["path"], "original_logical_path": d["original_logical_path"],
                            "commit": d["commit"], "raw_bytes": len(raw), "raw_sha256": sha(raw),
                            "decoded_bytes": len(decoded), "decoded_sha256": sha(decoded),
                            "records": count})
    if set(rows) != wanted or len(duplicate_ids) != 0:
        raise SystemExit(f"Selected/unique source scan mismatch records={total_records}, unique={len(all_ids)}, selected={len(rows)}")

    result = {
        "version": 1,
        "status": "selected-original-component-delivery-geometries-authenticated",
        "issue": 1492,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "baseline_commit": BASELINE_COMMIT,
        "baseline_admission_sha256": BASELINE_SHA,
        "candidate_delivery_commit": config["candidate_delivery"],
        "component_delivery_inventory": {"shards": shard_stats, "declared_current_components": config["current_components"],
                                          "total_records": total_records,
                                          "unique_component_ids": len(all_ids),
                                          "duplicate_ids": duplicate_ids,
                                          "declared_vs_captured_unique_difference": len(all_ids) - config["current_components"],
                                          "raw_bytes": sum(d["bytes"] for d in descriptors),
                                          "decoded_bytes": sum(d["uncompressed_bytes"] for d in descriptors)},
        "selected_component_ids": selected_ids,
        "complete_family_member_count": len(family_ids),
        "complete_family_scope_sha256": sha((ROOT / family_path).read_bytes()),
        "selected_components": [rows[i] for i in selected_ids],
        "producer": {"path": str(Path(__file__).relative_to(ROOT)), "sha256": script_hash,
                     "python": sys.version, "elapsed_seconds": time.monotonic() - started},
        "admission": {"phase_input_bytes": sum(base.consumed.values()),
                      "phase_limit_bytes": base.max_phase_bytes,
                      "reserved_output_bytes": reserve,
                      "disk_free_bytes": shutil.disk_usage(ROOT).free,
                      "physical_memory_bytes": os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"),
                      "process_max_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},
        "limits": ["The pinned input-config declares 95,173 components, but the authenticated 11 delivery shards contain 95,174 unique component IDs; this one-record mismatch is retained and prevents a whole-delivery count claim.",
                   "These are exact source delivery records, not a physical/geopolitical classification.",
                   "The separate upstream physical-comparison result shards contain no candidate geometries; this capture uses the manifest-pinned original components-v3 delivery inputs."]
    }
    if len(canonical_json(result)) > reserve:
        raise SystemExit("Selected geometry output exceeds pre-admitted reserve")
    if sha(Path(__file__).read_bytes()) != script_hash:
        raise SystemExit("Producer changed during capture")
    published = writer.publish({"selected-components.json": result})
    print(json.dumps({"status": result["status"], "records": total_records,
                      "selected": len(rows), "phase_bytes": sum(base.consumed.values()),
                      "max_rss": result["admission"]["process_max_rss_bytes"], "outputs": published}, indent=2))


if __name__ == "__main__":
    main()
