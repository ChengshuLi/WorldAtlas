#!/usr/bin/env python3
"""Reproduce the retained #1162 descriptor and ZIP-member admission arithmetic."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[3]
OWNED = "data/regional-review/southeastern-county-vintage-978-erratum/"
PACKET = ROOT / OWNED
ZIP_PATH = "data/regional-review/regional-review-599d6fe712bbbcae/sources/census-2018-cartographic-boundaries/cb_2018_us_county_500k.zip"
EXPECTED_BASELINE = "a1cf4cd86fd07d00ae592b4705e4b39f50628df7"
EXPECTED_ORIGINAL_DESCRIPTORS = 26
EXPECTED_ORIGINAL_BYTES = 65550965
EXPECTED_DECODED_ZIP_BYTES = 17480047
RESERVE_BYTES = 8 * 1024 * 1024
PER_FILE_LIMIT = 32 * 1024 * 1024


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--script-sha256", required=True)
    parser.add_argument("--inventory-sha256", required=True)
    args = parser.parse_args()
    script = Path(__file__).read_bytes()
    inventory_path = PACKET / "baseline-inventory-v2.json"
    inventory_raw = inventory_path.read_bytes()
    if sha(script) != args.script_sha256 or sha(inventory_raw) != args.inventory_sha256:
        raise SystemExit("Archive check code/inventory differs from explicit pins")
    inventory = json.loads(inventory_raw)
    if inventory["commit"] != EXPECTED_BASELINE or inventory["original_1162_descriptor_count"] != EXPECTED_ORIGINAL_DESCRIPTORS:
        raise SystemExit("Wrong immutable baseline or original descriptor count")
    if sum(f["bytes"] for f in inventory["files"][:EXPECTED_ORIGINAL_DESCRIPTORS]) != EXPECTED_ORIGINAL_BYTES:
        raise SystemExit("Original #1162 encoded size differs from the checked issue admission")
    sys.path.insert(0, str(ROOT))
    from scripts.evidence.immutable import Baseline
    baseline = Baseline(ROOT, inventory["commit"], inventory["files"])
    raw = baseline.read(ZIP_PATH)
    members = []
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            name = info.filename
            if name.startswith("/") or ".." in Path(name).parts or "\\" in name:
                raise ValueError(f"Unsafe ZIP member name: {name}")
            data = archive.read(info)
            if len(data) > PER_FILE_LIMIT:
                raise ValueError(f"ZIP member exceeds per-file cap: {name}")
            members.append({"path":name,"encoded_bytes":info.compress_size,"decoded_bytes":len(data),"sha256":sha(data)})
    decoded_total = sum(item["decoded_bytes"] for item in members)
    if decoded_total != EXPECTED_DECODED_ZIP_BYTES or max(item["decoded_bytes"] for item in members) >= PER_FILE_LIMIT:
        raise ValueError("ZIP decoded size or member cap differs from the checked issue admission")
    result = {
        "version": 1,
        "baseline_commit": baseline.commit,
        "reproduction_script_sha256": sha(script),
        "immutable_reader_sha256": next(f["sha256"] for f in inventory["files"] if f["path"] == "scripts/evidence/immutable.py"),
        "original_1162_descriptor_count": EXPECTED_ORIGINAL_DESCRIPTORS,
        "original_1162_encoded_bytes": EXPECTED_ORIGINAL_BYTES,
        "zip_path": ZIP_PATH,
        "zip_sha256": sha(raw),
        "zip_encoded_bytes": len(raw),
        "member_count": len(members),
        "decoded_member_bytes": decoded_total,
        "largest_decoded_member_bytes": max(item["decoded_bytes"] for item in members),
        "member_limit_bytes": PER_FILE_LIMIT,
        "all_members_below_32_mib": True,
        "members": members,
        "reserve_bytes": RESERVE_BYTES,
        "original_encoded_plus_decoded_zip_plus_reserve_bytes": EXPECTED_ORIGINAL_BYTES + decoded_total + RESERVE_BYTES,
        "evidence_caps": {"single_file_bytes":PER_FILE_LIMIT,"total_descriptor_bytes":256*1024*1024,"descriptor_count":512},
    }
    encoded = (json.dumps(result, sort_keys=True, indent=2) + "\n").encode()
    relative = OWNED + "archive-admission-reproduction-v2.json"
    target = PACKET / "archive-admission-reproduction-v2.json"
    root = ROOT / relative
    root.parent.mkdir(parents=True, exist_ok=True)
    with root.open("xb") as stream:
        stream.write(encoded)
        stream.flush()
    print(json.dumps({"output":relative,"sha256":sha(encoded),"members":len(members),"decoded_bytes":decoded_total,"admitted_bytes":result["original_encoded_plus_decoded_zip_plus_reserve_bytes"]},sort_keys=True))


if __name__ == "__main__":
    main()
