#!/usr/bin/env python3
"""Restore exact public ESA WorldCover COGs from the pinned official object URLs."""
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[3]
PACKET = ROOT / "research/geography/gap-source-angola-drc-boundary-water-followup-20261007"
RECEIPT = PACKET / "sources/worldcover/retrieval.json"


def main():
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    for row in receipt["tiles"]:
        target = ROOT / row["path"]
        if target.is_file():
            data = target.read_bytes()
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            request = Request(row["url"], headers={"If-Match": row["etag"]})
            with urlopen(request, timeout=180) as response:
                if response.status != 200 or response.headers.get("ETag") != row["etag"]:
                    raise RuntimeError(f"ESA source response changed: {row['tile']}")
                data = response.read()
            target.write_bytes(data)
        if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise RuntimeError(f"WorldCover source bytes differ from the immutable receipt: {row['tile']}")
        print(f"verified {row['tile']} {len(data)} bytes {row['sha256']}")


if __name__ == "__main__":
    main()
