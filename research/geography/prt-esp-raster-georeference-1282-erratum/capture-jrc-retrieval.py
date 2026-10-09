#!/usr/bin/env python3
"""Re-fetch and hash the 24 pinned JRC assets without writing duplicate rasters."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[3]
PACKET = ROOT / "research/geography/portugal-spain-gap-source-families-20261007"
OWN = Path(__file__).resolve().parent
CAPTURE = PACKET / "sources/jrc/monthlyhistory-v1_5-2024-capture.json"
OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else OWN / "jrc-current-retrieval.json"
MAX_FILE = 32 * 1024 * 1024
MAX_TOTAL = 256 * 1024 * 1024
CHUNK = 1024 * 1024

def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()

def main() -> None:
    assets = json.loads(CAPTURE.read_text())["assets"]
    assert len(assets) == 24
    total_expected = sum(a["bytes"] for a in assets)
    assert all(a["bytes"] <= MAX_FILE for a in assets)
    code_bytes = Path(__file__).stat().st_size
    reserve = 256 * 1024
    assert total_expected + code_bytes + reserve <= MAX_TOTAL
    out_parent = OUT.parent.resolve()
    assert (out_parent == OWN or OWN in out_parent.parents) and not OUT.exists() and not OUT.is_symlink(), "refuse overwrite/symlink or output outside owned packet"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat()
    results = []
    bytes_read = 0
    for a in assets:
        req = Request(a["url"], headers={"User-Agent": "WorldAtlas geography research; source audit"})
        with urlopen(req, timeout=60) as response:
            length = response.headers.get("Content-Length")
            declared = int(length) if length is not None else None
            if declared is not None:
                assert declared <= MAX_FILE and bytes_read + declared <= MAX_TOTAL
            h = hashlib.sha256()
            count = 0
            while True:
                chunk = response.read(CHUNK)
                if not chunk:
                    break
                count += len(chunk)
                assert count <= MAX_FILE and bytes_read + count <= MAX_TOTAL
                h.update(chunk)
            digest = h.hexdigest()
            bytes_read += count
            assert count == a["bytes"] and digest == a["sha256"], f"Retrieval differs from immutable source pin: {a['filename']}"
            results.append({"filename": a["filename"], "url": a["url"], "status": response.status,
                            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                            "response_headers": {key.lower(): response.headers.get(key) for key in
                                                  ("Content-Length", "Content-Type", "ETag", "Last-Modified", "Date")},
                            "bytes": count, "sha256": digest, "matches_retained_original": True})
    payload = json.dumps({"schema": "worldatlas-jrc-current-retrieval-v1", "started_at_utc": started,
                               "completed_at_utc": datetime.now(timezone.utc).isoformat(), "asset_count": len(results),
                               "bytes_streamed_without_duplicate_storage": bytes_read,
                               "admission": {"per_file_limit": MAX_FILE, "aggregate_limit": MAX_TOTAL,
                                             "encoded_source_bytes": total_expected, "code_bytes": code_bytes,
                                             "output_reserve_bytes": reserve, "status": "admitted"},
                               "results": results}, indent=2, sort_keys=True) + "\n"
    assert len(payload.encode()) <= reserve
    with OUT.open("x", encoding="utf-8") as f:
        f.write(payload)
    print(f"Verified {len(results)} assets / {bytes_read} bytes; receipt {OUT}")

if __name__ == "__main__":
    main()
