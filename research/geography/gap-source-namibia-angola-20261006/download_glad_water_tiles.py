#!/usr/bin/env python3
"""Fetch the exact public GLAD tile generations pinned in this packet."""

import argparse
import base64
import concurrent.futures
import hashlib
import json
import time
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE = ROOT / "sources" / "glad-water-1999-2023"
parser = argparse.ArgumentParser()
parser.add_argument("--cache-dir", required=True, type=Path, help="Write the 2.38 GB tile cache here; it is not stored in Git.")
parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE)
args = parser.parse_args()

source = args.source_dir.resolve()
cache = args.cache_dir.resolve()
metadata = json.loads((source / "object-metadata.json").read_text())
analysis = json.loads((ROOT / "glad-water-1999-2023-analysis.json").read_text())
expected = {x["tile"] + "/" + x["name"]: x for x in analysis["source_files"]}
cache.mkdir(parents=True, exist_ok=True)


def fetch(obj):
    name = obj["name"]
    key = name.split("/", 1)[1]
    record = expected[key]
    if obj["generation"] != record["generation"]:
        raise RuntimeError(f"generation mismatch for {name}")
    target = cache / "tiles" / key
    target.parent.mkdir(parents=True, exist_ok=True)
    sha = hashlib.sha256()
    md5 = hashlib.md5()
    size = 0
    with requests.get(obj["mediaLink"], stream=True, timeout=(30, 300)) as response:
        response.raise_for_status()
        with target.open("wb") as stream:
            for block in response.iter_content(1024 * 1024):
                if not block:
                    continue
                stream.write(block)
                sha.update(block)
                md5.update(block)
                size += len(block)
    expected_md5 = base64.b64decode(obj["md5Hash"]).hex()
    result = {
        "name": name,
        "path": "tiles/" + key,
        "bytes": size,
        "generation": obj["generation"],
        "md5_hex": md5.hexdigest(),
        "expected_md5_hex": expected_md5,
        "sha256": sha.hexdigest(),
        "expected_sha256": record["sha256"],
        "verified": size == int(obj["size"])
        and size == record["bytes"]
        and md5.hexdigest() == expected_md5
        and sha.hexdigest() == record["sha256"],
    }
    if not result["verified"]:
        raise RuntimeError(json.dumps(result, sort_keys=True))
    return result


receipts = []
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    for number, result in enumerate(pool.map(fetch, metadata["files"]), start=1):
        receipts.append(result)
        if number % 10 == 0:
            print(f"{number}/{len(metadata['files'])} objects verified", flush=True)

report = {
    "retrieved_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "source": "Generation-pinned Google Cloud Storage public objects",
    "verified_objects": len(receipts),
    "total_bytes": sum(x["bytes"] for x in receipts),
    "files": sorted(receipts, key=lambda x: x["name"]),
}
output = cache / "download-receipts.json"
output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
print(json.dumps({"verified_objects": report["verified_objects"], "total_bytes": report["total_bytes"], "receipt_sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))
