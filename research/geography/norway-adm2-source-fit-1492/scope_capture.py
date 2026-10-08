#!/usr/bin/env python3
"""Bounded, immutable capture of the complete Norway family scope."""
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
BASELINE_COMMIT = "088ab05aeb16ddfa8f0c43e596533f3f11d5fcec"
BASELINE_SHA = "45d4356a46beddea43bfbd20231e0bf3671aa349643de29d0fa088ed5fbf5713"
WORKER = "01a112b9-e2b7-7d03-8000-eb2890649612"
FAMILY = "gap-source-batch:3f21c83705d3cef5988b1295"
SELECTED = [
    "physical-component:153efbdb9c28eaba9ef8c4c834577ea44c875c2412493c2581530c2d9c7085f1",
    "physical-component:1f453e7a436aa2f6a68edfb7433d3d1ec05c72b37ba78fac9b3d2542bc085efb",
    "physical-component:1f5426f5180aa4f5b7fd9991b5ae4816d56cb642c31d0937a4977da516f28f2b",
    "physical-component:4f57d0af8235d8f547395c5d94bfeeb57e8e11168f65b7a566407213d17f1e5c",
    "physical-component:764b247eb21da38adac0b925bededbbb4dccaefa4b52b16976f20543a7ac3384",
    "physical-component:7bad7bdf9b1203fe6c676eb2efde10b09ce394ad7d6d554eb557709d7704df35",
    "physical-component:8fb9f3f0d7df1c96ac452792fd4a9dbc7a45a576437550dd5b198424ceca14a9",
    "physical-component:a82c3dc9980bf083cf15fb0edf1b98301259afb93761549c97ec57d73a41c5ce",
    "physical-component:a92cac9c4c3d3a91286eca0e4890becd63441647c7fe7c4cdcc5e1aa167d4803",
    "physical-component:b6ba064b4525f0c75459a8d1aa05c25e9740cc46b9964f96983d61d6a9b4253a",
    "physical-component:cc11d3c9c7f82d8c9073539568d8af915da17e21904a60a75d49eb5d2e63ae94",
    "physical-component:dc92c796890cece117d3a70e1422fc2682a46caf3db64f06b2935b46e31b7a9f",
    "physical-component:e0bd74d0efc769aa5b98ba28ca22d0b37692f3387d344e32c14516b0fe062904",
    "physical-component:eb2b6c25d1a2b8ead2bcb67f7e0423b5f1cc5609ac3f600bb98cd6d5cb11db40",
    "physical-component:f082e1ba3a2d1267b17f803511ec164c9c8649fd3fb9cc2bc752a4c833659508",
]
VINTAGE = "family-scope-corrected-20261008"
OUTPUTS = ["family-scope.json"]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def process_snapshot():
    raw = subprocess.check_output(["ps", "-Ao", "pid,ppid,etime,comm,rss,%cpu,args"], text=True)
    return [line.strip() for line in raw.splitlines()[1:]
            if "physical-continuation.py" in line or "supervise-query-" in line or "supervise-numerical-cohort-" in line]


def iter_fragment_records(chunks):
    decoder = json.JSONDecoder()
    buffer = ""
    for path, chunk in chunks:
        buffer += chunk
        index = 0
        while index < len(buffer):
            while index < len(buffer) and (buffer[index].isspace() or buffer[index] in "[],"):
                index += 1
            if index >= len(buffer):
                buffer = ""
                break
            try:
                value, end = decoder.raw_decode(buffer, index)
            except json.JSONDecodeError as exc:
                # Corpus shards are byte slices of a single JSON stream and can
                # end inside a record. Retain only that incomplete suffix; a
                # farther-behind error is malformed evidence, not a shard seam.
                if len(buffer) - exc.pos > 8 * 1024 * 1024:
                    raise
                buffer = buffer[index:]
                break
            index = end
            if isinstance(value, list):
                for item in value:
                    yield path, item
            else:
                yield path, value
        else:
            buffer = buffer[index:]
    if buffer.strip(" \t\r\n[],"):
        raise ValueError("Incomplete trailing JSON after all family shards")


def main():
    started = time.monotonic()
    script_bytes = Path(__file__).read_bytes()
    script_hash = sha(script_bytes)
    admission_path = ROOT / OWNED / "vintages/baseline-20261008/baseline-admission.json"
    admission_bytes = admission_path.read_bytes()
    if sha(admission_bytes) != BASELINE_SHA:
        raise SystemExit("Baseline admission bytes drifted")
    admission = json.loads(admission_bytes)
    if admission["commit"] != BASELINE_COMMIT or admission["worker_id"] != WORKER:
        raise SystemExit("Unexpected baseline identity")

    sys.path.insert(0, str(ROOT / "scripts"))
    from evidence.immutable import Baseline, NewVintage, canonical_json, MAX_FILE_BYTES

    baseline = Baseline(ROOT, BASELINE_COMMIT, admission["baseline_files"])
    if baseline.consumed != {name: row["bytes"] for name, row in
                             ((x["path"], x) for x in admission["baseline_files"])}:
        raise SystemExit("Baseline raw-byte admission differs from the recorded inventory")

    # The entire output set and conservative output/receipt reserves are admitted
    # before any family shard is decoded or any family record is parsed.
    writer = NewVintage(baseline, OWNED, VINTAGE, OUTPUTS)
    baseline.admit("reserved-output:family-scope.json", 1024 * 1024)
    baseline.admit("reserved-output:publication.json", 4096)
    disk_before = shutil.disk_usage(ROOT)
    rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    memory_before = subprocess.check_output(["memory_pressure"], text=True)
    live_before = process_snapshot()

    shard_prefix = "coordination/engineering/global-actionability-routing-20261007/results/families-"
    matches = []
    scanned = []
    scanned_records = 0
    def fragments():
        for shard_no in range(14):
            path = f"{shard_prefix}{shard_no:03d}.bin.gz"
            compressed = baseline.pinned_bytes(path)
            declared_decoded_bytes = struct.unpack("<I", compressed[-4:])[0]
            baseline.admit(path + ":decoded", declared_decoded_bytes)
            decoded_bytes = gzip.decompress(compressed)
            if len(decoded_bytes) != declared_decoded_bytes:
                raise SystemExit("Decoded family-shard size disagrees with its gzip trailer")
            # The complete decoded file is released after the streaming parser
            # consumes it; only an incomplete JSON suffix crosses a shard seam.
            text = decoded_bytes.decode("utf-8")
            scanned.append({"path": path, "sha256": baseline.pins[path]["sha256"],
                            "bytes": baseline.pins[path]["bytes"],
                            "decoded_bytes": declared_decoded_bytes})
            yield path, text
            del text, decoded_bytes

    for path, row in iter_fragment_records(fragments()):
        scanned_records += 1
        if isinstance(row, dict) and row.get("id") == FAMILY:
            matches.append((path, row))
    if len(matches) != 1:
        raise SystemExit(f"Expected exactly one matching complete family record, got {len(matches)}")

    family_path, family_record = matches[0]
    members = family_record.get("complete_component_ids")
    neighbors = family_record.get("complete_positive_length_neighbor_ids")
    if members is None or neighbors is None:
        print(json.dumps({"family_record_keys": sorted(family_record),
                          "component_fields": {k: len(v) for k, v in family_record.items()
                                               if isinstance(v, list) and ("component" in k or "member" in k or "neighbor" in k)},
                          "family_id": family_record.get("id")}, indent=2))
    if not isinstance(members, list) or len(members) != 400 or len(set(members)) != 400:
        raise SystemExit("Family record lacks the exact 400 unique members")
    if not isinstance(neighbors, list) or len(neighbors) != 36 or len(set(neighbors)) != 36:
        raise SystemExit("Family record lacks the exact 36 unique neighbors")
    selected_in_family = sorted(set(SELECTED) & set(members))
    selected_outside_family = sorted(set(SELECTED) - set(members))

    correction_path = OWNED + "vintages/issue-scope-correction-20261008/correction.json"
    correction_raw = (ROOT / correction_path).read_bytes()
    correction_publication = json.loads((ROOT / Path(correction_path).parent / "publication.json").read_bytes())
    correction_descriptor = next((row for row in correction_publication["outputs"]
                                  if row.get("path") == correction_path), None)
    if not correction_descriptor or correction_descriptor.get("sha256") != sha(correction_raw) or correction_descriptor.get("bytes") != len(correction_raw):
        raise SystemExit("Selected-ID correction artifact does not match its completion receipt")
    correction = json.loads(correction_raw)
    if correction.get("correction", {}).get("new_id") not in SELECTED or correction.get("correction", {}).get("old_id") in members:
        raise SystemExit("Pinned issue identifier correction does not reconcile against the family roster")
    baseline.admit("captured-input:" + correction_path, len(correction_raw))

    result = {
        "version": 1,
        "status": "complete-family-scope-captured",
        "supersedes": "family-scope-20261008",
        "issue": 1492,
        "worker_id": WORKER,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "baseline": {"commit": BASELINE_COMMIT, "admission_sha256": BASELINE_SHA,
                     "files": len(admission["baseline_files"]),
                     "pinned_file_bytes": admission["pinned_file_bytes"]},
        "producer": {"path": str(Path(__file__).relative_to(ROOT)), "sha256": script_hash,
                     "python": sys.version, "elapsed_seconds": time.monotonic() - started},
        "scope": {"family_id": FAMILY,
                  "expected_family_envelope": [11.76142546602688, 65.06317643639146, 17.7099, 69.315253],
                  "complete_member_count": len(members), "complete_component_ids": members,
                  "selected_component_ids": SELECTED, "selected_count": len(SELECTED),
                  "selected_ids_in_family": selected_in_family,
                  "selected_ids_outside_family": selected_outside_family,
                  "selected_family_membership_complete": not selected_outside_family,
                  "complete_positive_length_neighbor_count": len(neighbors),
                  "complete_positive_length_neighbor_ids": neighbors,
                  "family_record_source": family_path,
                  "family_record": family_record},
        "selection_correction": {"path": correction_path, "sha256": sha(correction_raw),
                                 "old_id": correction["correction"]["old_id"],
                                 "corrected_id": correction["correction"]["new_id"],
                                 "family_membership_after_correction": correction["correction"]["new_id"] in members,
                                 "previous_capture_selected_id": correction["correction"]["old_id"]},
        "scan": {"shards_scanned": len(scanned), "records_scanned": scanned_records,
                 "shards": scanned, "decoded_input_bytes": sum(x["decoded_bytes"] for x in scanned)},
        "admission": {"pre_read_output_reserve_bytes": 1024 * 1024,
                      "pre_read_publication_reserve_bytes": 4096,
                      "phase_bytes_before_write": sum(baseline.consumed.values()),
                      "phase_limit_bytes": baseline.max_phase_bytes,
                      "disk_free_before_bytes": disk_before.free,
                      "physical_memory_bytes": os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"),
                      "memory_pressure_before": memory_before,
                      "live_root_global_processes_before": live_before,
                      "process_max_rss_before_bytes": rss_before,
                      "process_max_rss_after_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                      "disk_free_after_bytes": shutil.disk_usage(ROOT).free},
        "limits": ["This captures family/member/neighbor scope only; it is not a GIS result or eligibility decision.",
                   "The original family-scope vintage used the pre-correction Vevelstad ID and reported 14 of 15 selected IDs in the family. This superseding scan uses the pinned corrected ID; it does not change the 400-member family or 15-item selected roster.",
                   "All component geometries, source feature contacts, cause, authority, history, rights, water/ice, and ownership remain unassessed here."]
    }
    encoded = canonical_json(result)
    if len(encoded) > MAX_FILE_BYTES or len(encoded) > 1024 * 1024:
        raise SystemExit("Family-scope output exceeded its pre-read reserve")
    if sha(Path(__file__).read_bytes()) != script_hash:
        raise SystemExit("Producer code changed during the run")
    records = writer.publish({"family-scope.json": result})
    print(json.dumps({"status": result["status"], "supersedes": result["supersedes"],
                      "selected_in_family": len(selected_in_family), "selected_outside_family": selected_outside_family,
                      "family_members": len(members),
                      "neighbors": len(neighbors), "scanned_records": scanned_records,
                      "phase_consumed_bytes": sum(baseline.consumed.values()),
                      "output": records}, indent=2))


if __name__ == "__main__":
    main()
