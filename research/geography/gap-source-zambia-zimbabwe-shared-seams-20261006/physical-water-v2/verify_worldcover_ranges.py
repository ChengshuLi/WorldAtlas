#!/usr/bin/env python3
"""Verify retained WorldCover byte ranges against their HTTP receipts.

This verifies local file identity/length and manifest consistency only. It does
not decompress TIFF blocks, classify pixels, or perform spatial operations.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


BASE = Path(__file__).resolve().parent
PACKET = BASE.parent
MANIFEST = BASE / "worldcover-source-ranges.json"
OUTPUT = BASE / "worldcover-range-integrity.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    manifest_bytes = MANIFEST.read_bytes()
    manifest = json.loads(manifest_bytes)
    source = manifest["source"]
    before, after = manifest["head_before"], manifest["head_after"]
    if before != after:
        raise RuntimeError("Source object metadata changed during the recorded acquisition")
    if source["whole_object_sha256"] is not None:
        raise RuntimeError("A whole-object digest must not be inferred from the multipart ETag")

    rows = [manifest["ifd_metadata_range"], *[block["http"] | {"file": block["file"], "sha256": block["sha256"], "content_length": block["encoded_bytes"]} for block in manifest["blocks"]]]
    seen_files: set[str] = set()
    files = []
    encoded_bytes = 0
    for row in rows:
        name = row["file"]
        if name in seen_files:
            raise RuntimeError(f"Duplicate retained file: {name}")
        seen_files.add(name)
        path = (BASE / name).resolve()
        if not path.is_relative_to(BASE.resolve()):
            raise RuntimeError(f"Retained path escapes source directory: {name}")
        if not path.is_file():
            raise RuntimeError(f"Missing retained range: {name}")
        actual_size = path.stat().st_size
        actual_hash = sha256(path)
        if actual_size != row["content_length"] or actual_hash != row["sha256"]:
            raise RuntimeError(f"Retained bytes differ from receipt: {name}")
        if row["status"] != 206 or row["if_match"] != source["etag"]:
            raise RuntimeError(f"Range was not conditionally pinned: {name}")
        if row["etag"] != source["etag"] or row["last_modified"] != source["last_modified"]:
            raise RuntimeError(f"Range metadata differs from pinned source: {name}")
        expected = f"bytes {row['request_range'][6:]}/{source['whole_object_bytes']}"
        if row["content_range"] != expected:
            raise RuntimeError(f"Content-Range mismatch: {name}")
        encoded_bytes += actual_size
        files.append({"path": str(path.relative_to(PACKET)), "bytes": actual_size, "sha256": actual_hash})

    if len(manifest["blocks"]) != 60:
        raise RuntimeError("Expected exactly 60 selected original TIFF blocks")
    if encoded_bytes != manifest["selected_encoded_bytes"] + manifest["ifd_metadata_range"]["content_length"]:
        raise RuntimeError("Recorded encoded byte total differs from retained blocks")
    if sum(block["decoded_bytes"] for block in manifest["blocks"]) != manifest["selected_decoded_bytes"]:
        raise RuntimeError("Recorded decoded block capacity differs from block grid")

    result = {
        "version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "method": "verify local exact HTTP range bytes against each manifest SHA-256, length, If-Match, Content-Range, ETag and Last-Modified; no TIFF decompression or GIS",
        "manifest": {"path": str(MANIFEST.relative_to(PACKET.parent)), "bytes": len(manifest_bytes), "sha256": hashlib.sha256(manifest_bytes).hexdigest()},
        "source": {"url": source["url"], "etag": source["etag"], "last_modified": source["last_modified"], "whole_object_bytes": source["whole_object_bytes"], "whole_object_sha256": None},
        "retained_range_count": len(files),
        "retained_encoded_bytes": encoded_bytes,
        "selected_original_block_count": len(manifest["blocks"]),
        "selected_original_block_decoded_bytes": manifest["selected_decoded_bytes"],
        "files": files,
        "result": "all retained exact range bytes match their pinned HTTP receipts",
        "limits": ["The multipart ETag is not a whole-object digest.", "The complete COG was not downloaded or hashed.", "Byte integrity does not validate decoded pixel values, classification, geolocation accuracy, or physical conditions."],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("retained_range_count", "retained_encoded_bytes", "selected_original_block_count", "selected_original_block_decoded_bytes", "result")}, indent=2))


if __name__ == "__main__":
    main()
