#!/usr/bin/env python3
"""Search one bounded batch of exact physical-component result shards."""
import gzip
import hashlib
import json
import os
import resource
import shutil
import struct
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OWNED = "research/geography/norway-adm2-source-fit-1492/"
COMMIT = "088ab05aeb16ddfa8f0c43e596533f3f11d5fcec"
BASELINE_SHA = "45d4356a46beddea43bfbd20231e0bf3671aa349643de29d0fa088ed5fbf5713"
SOURCE_ROWS_SHA = "af4d0927d2e9eb8c9053ccf13969b1205b91cc1df3ed799190210f4a717ce12e"
VINTAGE_PREFIX = "physical-rows-20261008-b"
OUTPUTS = ["physical-row-search.json"]
CORPUS_PREFIX = "coordination/engineering/global-physical-comparison-20261006/results/components-"
BATCH_SIZE = 12
OUTPUT_RESERVE = 24 * 1024 * 1024


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_stage(name, expected_sha):
    path = ROOT / OWNED / "vintages" / name
    raw = path.read_bytes()
    if sha(raw) != expected_sha:
        raise ValueError("Stage input drift: " + str(path))
    receipt = json.loads((path.parent / "publication.json").read_bytes())
    desc = next((x for x in receipt.get("outputs", []) if x.get("path") == str(path.relative_to(ROOT))), None)
    if not desc or desc.get("bytes") != len(raw) or desc.get("sha256") != sha(raw):
        raise ValueError("Stage input does not match publication receipt")
    return raw


def process_snapshot():
    raw = subprocess.check_output(["ps", "-Ao", "pid,ppid,etime,comm,rss,%cpu,args"], text=True)
    return [line.strip() for line in raw.splitlines()[1:]
            if "physical-continuation.py" in line or "supervise-query-" in line]


def main():
    if len(sys.argv) != 2 or not sys.argv[1].isdigit():
        raise SystemExit("usage: capture_physical_rows.py BATCH_INDEX")
    batch_index = int(sys.argv[1])
    batch_id = f"{batch_index:03d}"
    start = batch_index * BATCH_SIZE
    end = start + BATCH_SIZE
    script_hash = sha(Path(__file__).read_bytes())
    admission_raw = (ROOT / OWNED / "vintages/baseline-20261008/baseline-admission.json").read_bytes()
    if sha(admission_raw) != BASELINE_SHA:
        raise SystemExit("Baseline admission changed")
    admission = json.loads(admission_raw)
    sys.path.insert(0, str(ROOT / "scripts"))
    from evidence.immutable import Baseline, NewVintage, canonical_json, MAX_FILE_BYTES

    core = Baseline(ROOT, COMMIT, admission["baseline_files"])
    quality = json.loads(core.pinned_bytes("coordination/engineering/global-physical-comparison-20261006/evidence-quality.json"))
    shards = sorted((x for x in quality["outputs"] if x.get("path", "").startswith(CORPUS_PREFIX)
                     and x["path"].endswith(".jsonl.gz")), key=lambda x: x["path"])
    if len(shards) != 71:
        raise SystemExit("Expected complete 71-file physical component result corpus")
    if start >= len(shards):
        raise SystemExit("Batch index exceeds the complete physical result corpus")
    selected_descriptors = shards[start:min(end, len(shards))]
    pinned = admission["baseline_files"] + [
        {k: d[k] for k in ("path", "bytes", "sha256", "hash_kind")}
        for d in selected_descriptors]
    baseline = Baseline(ROOT, COMMIT, pinned)
    vintage = VINTAGE_PREFIX + batch_id
    writer = NewVintage(baseline, OWNED, vintage, OUTPUTS)
    baseline.admit("reserved-output:physical-row-search.json", OUTPUT_RESERVE)
    baseline.admit("reserved-output:publication.json", 4096)

    source_path = "official-source-capture-20261008/selected-source-rows.json"
    source_raw = read_stage(source_path, SOURCE_ROWS_SHA)
    baseline.admit("captured-input:selected-source-rows.json", len(source_raw))
    selected_result = json.loads(source_raw)
    selected = selected_result["family_context"]["selected_component_ids"]
    if len(selected) != 15 or len(set(selected)) != 15:
        raise SystemExit("Source capture does not include exact 15 selected component identities")
    targets = set(selected)

    started = time.monotonic()
    rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    disk_before = shutil.disk_usage(ROOT).free
    memory_before = subprocess.check_output(["memory_pressure"], text=True)
    live_before = process_snapshot()
    matches = []
    record_count = 0
    shard_receipts = []
    for descriptor in selected_descriptors:
        path = descriptor["path"]
        compressed = baseline.pinned_bytes(path)
        decoded_size = struct.unpack("<I", compressed[-4:])[0]
        baseline.admit(path + ":decoded", decoded_size)
        decoded = gzip.decompress(compressed)
        if len(decoded) != decoded_size:
            raise SystemExit("Physical result decoded size differs from gzip trailer")
        for line in decoded.splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            record_count += 1
            identity = record.get("component") or record.get("id")
            if identity in targets:
                matches.append({"path": path, "descriptor": {k: descriptor[k] for k in ("path", "bytes", "sha256", "hash_kind")},
                                "record": record})
        shard_receipts.append({"path": path, "bytes": len(compressed), "sha256": sha(compressed),
                               "decoded_bytes": len(decoded), "records": sum(1 for line in decoded.splitlines() if line.strip())})
        del decoded

    body = {
        "version": 1,
        "status": "physical-result-batch-searched",
        "issue": 1492,
        "batch_index": batch_index,
        "batch_range_zero_based": [start, min(end, len(shards))],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "baseline": {"commit": COMMIT, "admission_sha256": BASELINE_SHA,
                     "initial_pinned_bytes": admission["pinned_file_bytes"]},
        "selected_component_ids": selected,
        "corpus": {"expected_shards": len(shards), "searched_shards": shard_receipts,
                   "searched_count": len(shard_receipts), "records_scanned": record_count},
        "matches": matches,
        "producer": {"path": str(Path(__file__).relative_to(ROOT)), "sha256": script_hash,
                     "python": sys.version, "elapsed_seconds": time.monotonic()-started},
        "admission": {"pre_read_output_reserve_bytes": OUTPUT_RESERVE,
                      "phase_input_bytes_before_publish": sum(baseline.consumed.values()),
                      "phase_limit_bytes": baseline.max_phase_bytes,
                      "disk_free_before_bytes": disk_before,
                      "disk_free_after_bytes": shutil.disk_usage(ROOT).free,
                      "physical_memory_bytes": os.sysconf("SC_PAGE_SIZE")*os.sysconf("SC_PHYS_PAGES"),
                      "memory_pressure_before": memory_before,
                      "root_global_metadata_processes_before": live_before,
                      "process_max_rss_before_bytes": rss_before,
                      "process_max_rss_after_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},
        "limits": ["This batch search authenticates and locates complete archived physical-comparison rows; it does not perform GIS or infer any physical/political status.",
                   "The complete 71-shard corpus is searched across six separately admitted batch vintages."]
    }
    raw = canonical_json(body)
    if len(raw) > OUTPUT_RESERVE or len(raw) > MAX_FILE_BYTES:
        raise SystemExit("Physical row batch result exceeded its pre-read output reserve")
    if sha(Path(__file__).read_bytes()) != script_hash:
        raise SystemExit("Producer code changed during bounded source read")
    records = writer.publish({"physical-row-search.json": body})
    print(json.dumps({"status": body["status"], "batch": batch_index,
                      "shards": len(shard_receipts), "records_scanned": record_count,
                      "matches": [x["record"].get("component") or x["record"].get("id") for x in matches],
                      "phase_bytes": sum(baseline.consumed.values()), "outputs": records}, indent=2))


if __name__ == "__main__":
    main()
