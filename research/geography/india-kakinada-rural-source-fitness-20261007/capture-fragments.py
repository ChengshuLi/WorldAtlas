#!/usr/bin/env python3
"""Capture exact encoded and decoded source fragments from the immutable ancestor."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zlib

ANCESTOR = "83bed8c4c49e8f54077bb4abf0f32d41d0992f81"
SOURCE_PATH = "data/regional-review/regional-review-d0984f717127fb3e/sources/geoBoundaries-IND-ADM3-2018-retained.geojson.gz"
METADATA_PATH = "data/regional-review/regional-review-d0984f717127fb3e/sources/geoBoundaries-IND-ADM3-2018-retained-metadata.json"
INVENTORY_PATH = "data/regional-review/regional-review-d0984f717127fb3e/source-inventory.json"
SOURCE_SHA = "211a72c2c80bb60d10214944fa8cc4764e9ba888116e802ce6d87084872f5301"
SOURCE_BYTES = 13_794_274
RAW_SHA = "4ea6807d0a0c5aac0b46ee8e31ed7c30fbec273b44345bba1e4a2bb5f299f5fb"
RAW_BYTES = 40_040_002
ENCODED_BOUNDS = (8_388_608, 5_405_666)
DECODED_BOUNDS = (16_777_216, 16_777_216, 6_485_570)
MAX_PART = 32 * 1024 * 1024


def blob(repo, commit, path, expected_sha, expected_size):
    raw = subprocess.check_output(["git", "-C", str(repo), "show", f"{commit}:{path}"])
    if len(raw) != expected_size or hashlib.sha256(raw).hexdigest() != expected_sha:
        raise ValueError(f"Ancestor byte identity mismatch: {path}")
    return raw


def capture(repo, outdir):
    repo = Path(repo).resolve()
    if outdir.exists():
        raise FileExistsError(f"Refusing to replace fragment directory: {outdir}")
    metadata = json.loads(blob(repo, ANCESTOR, METADATA_PATH,
                              "f7bb99ddfcadaa1091c4b634b48c8843ee9d8b636af4f6da1cefccb0d424fc33", 2206))
    inventory = json.loads(blob(repo, ANCESTOR, INVENTORY_PATH,
                                "ef561241b2c81afe4eaea501963a955d7d57d06cc925cc8090310205e2e55e56", 5547))
    if metadata.get("compressed_sha256") != SOURCE_SHA or metadata.get("sha256") != RAW_SHA:
        raise ValueError("Pinned ancestor metadata does not bind both whole-stream identities")
    source_rows = [x for x in inventory.get("sources", []) if x.get("path") == "sources/geoBoundaries-IND-ADM3-2018-retained.geojson.gz"]
    if len(source_rows) != 1 or source_rows[0].get("sha256") != SOURCE_SHA or source_rows[0].get("bytes") != SOURCE_BYTES:
        raise ValueError("Pinned source inventory does not bind the original encoded stream")
    source_blob = subprocess.check_output(["git", "-C", str(repo), "ls-tree", "-z", ANCESTOR, "--", SOURCE_PATH])
    row = source_blob.decode().rstrip("\0")
    if not row.startswith("100644 blob ") or row.split()[2] == "":
        raise ValueError("Original source must be a regular ancestor file")
    oid = row.split()[2]
    size = int(subprocess.check_output(["git", "-C", str(repo), "cat-file", "-s", oid]).decode())
    if size != SOURCE_BYTES:
        raise ValueError("Original encoded source length differs from metadata")

    outdir.mkdir(parents=True)
    encoded_specs = []
    decoded_specs = []
    encoded_hasher = hashlib.sha256()
    decoded_hasher = hashlib.sha256()
    encoded_total = decoded_total = 0
    encoded_ordinal = 0
    encoded_part_written = 0
    encoded_part_hash = hashlib.sha256()
    encoded_part_path = outdir / f"encoded-{encoded_ordinal:03d}.bin"
    encoded_stream = encoded_part_path.open("xb")
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    decoded_ordinal = 0
    decoded_part_written = 0
    decoded_part_hash = hashlib.sha256()
    decoded_part_path = outdir / f"decoded-{decoded_ordinal:03d}.bin"
    decoded_stream = decoded_part_path.open("xb")

    def add_decoded(raw):
        nonlocal decoded_total, decoded_ordinal, decoded_part_written, decoded_part_hash, decoded_part_path, decoded_stream
        cursor = 0
        while cursor < len(raw):
            limit = DECODED_BOUNDS[decoded_ordinal]
            take = min(limit - decoded_part_written, len(raw) - cursor)
            segment = raw[cursor:cursor + take]
            decoded_stream.write(segment)
            decoded_hasher.update(segment)
            decoded_part_hash.update(segment)
            decoded_part_written += take
            decoded_total += take
            cursor += take
            if decoded_part_written == limit:
                decoded_stream.close()
                decoded_specs.append({"ordinal": decoded_ordinal, "offset": decoded_total - limit,
                                      "bytes": limit, "sha256": decoded_part_hash.hexdigest(),
                                      "role": "decoded-raw-source-fragment", "path": decoded_part_path.name})
                decoded_ordinal += 1
                if decoded_ordinal < len(DECODED_BOUNDS):
                    decoded_part_written = 0
                    decoded_part_hash = hashlib.sha256()
                    decoded_part_path = outdir / f"decoded-{decoded_ordinal:03d}.bin"
                    decoded_stream = decoded_part_path.open("xb")

    stream = subprocess.Popen(["git", "-C", str(repo), "cat-file", "blob", oid], stdout=subprocess.PIPE)
    try:
        while True:
            block = stream.stdout.read(64 * 1024)
            if not block:
                break
            encoded_hasher.update(block)
            encoded_total += len(block)
            cursor = 0
            while cursor < len(block):
                limit = ENCODED_BOUNDS[encoded_ordinal]
                take = min(limit - encoded_part_written, len(block) - cursor)
                segment = block[cursor:cursor + take]
                encoded_stream.write(segment)
                encoded_part_hash.update(segment)
                encoded_part_written += take
                cursor += take
                if encoded_part_written == limit:
                    encoded_stream.close()
                    encoded_specs.append({"ordinal": encoded_ordinal,
                                          "offset": encoded_total - len(block) + cursor - limit,
                                          "bytes": limit, "sha256": encoded_part_hash.hexdigest(),
                                          "role": "encoded-gzip-opaque-fragment", "path": encoded_part_path.name})
                    encoded_ordinal += 1
                    if encoded_ordinal < len(ENCODED_BOUNDS):
                        encoded_part_written = 0
                        encoded_part_hash = hashlib.sha256()
                        encoded_part_path = outdir / f"encoded-{encoded_ordinal:03d}.bin"
                        encoded_stream = encoded_part_path.open("xb")
            produced = decoder.decompress(block)
            if produced:
                add_decoded(produced)
        if stream.wait() != 0:
            raise RuntimeError("Git could not read the immutable original source blob")
        tail = decoder.flush()
        if tail:
            add_decoded(tail)
        if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
            raise ValueError("Original gzip has a truncated, concatenated or trailing stream")
    finally:
        if stream.stdout:
            stream.stdout.close()
        if stream.poll() is None:
            stream.kill()
            stream.wait()
        if not encoded_stream.closed:
            encoded_stream.close()
        if not decoded_stream.closed:
            decoded_stream.close()

    if encoded_total != SOURCE_BYTES or encoded_hasher.hexdigest() != SOURCE_SHA:
        raise ValueError("Captured encoded source identity mismatch")
    if decoded_total != RAW_BYTES or decoded_hasher.hexdigest() != RAW_SHA:
        raise ValueError("Captured decoded source identity mismatch")
    if encoded_ordinal != len(ENCODED_BOUNDS) or decoded_ordinal != len(DECODED_BOUNDS):
        raise ValueError("Incomplete source fragmentation")
    if any(x["bytes"] > MAX_PART for x in encoded_specs + decoded_specs):
        raise ValueError("Fragment exceeds the ordinary file bound")
    index = {
        "version": 1,
        "ancestor": {"commit": ANCESTOR, "metadata_path": METADATA_PATH,
                     "metadata_sha256": "f7bb99ddfcadaa1091c4b634b48c8843ee9d8b636af4f6da1cefccb0d424fc33",
                     "inventory_path": INVENTORY_PATH,
                     "inventory_sha256": "ef561241b2c81afe4eaea501963a955d7d57d06cc925cc8090310205e2e55e56"},
        "original_source": {"path": SOURCE_PATH, "vintage": "represented 2018", "features": 6822,
                            "metadata_admUnitCount": 6836, "count_difference": 14,
                            "count_difference_status": "unresolved"},
        "streams": [
            {"id": "original-encoded-gzip", "role": "opaque-encoded-original-source",
             "bytes": SOURCE_BYTES, "sha256": SOURCE_SHA, "part_bytes": sum(ENCODED_BOUNDS), "parts": encoded_specs},
            {"id": "original-decoded-json", "role": "complete-decoded-original-source",
             "bytes": RAW_BYTES, "sha256": RAW_SHA, "part_bytes": sum(DECODED_BOUNDS), "parts": decoded_specs}
        ],
        "literal_part_body_bytes": sum(ENCODED_BOUNDS) + sum(DECODED_BOUNDS),
        "ordinary_file_limit_bytes": MAX_PART,
        "note": "Parts are contiguous literal byte ranges. Whole gzip remains historical restoration/provenance evidence and is not an executable scientific input."
    }
    (outdir / "fragment-index.json").write_text(json.dumps(index, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return index


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()
    result = capture(Path(args.repo), Path(args.outdir))
    print(json.dumps({"ok": True, "index": result}, sort_keys=True))
