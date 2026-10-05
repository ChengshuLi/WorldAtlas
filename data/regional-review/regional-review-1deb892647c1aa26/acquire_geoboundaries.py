#!/usr/bin/env python3
"""Restore the exact geoBoundaries gbOpen ADM2 files cited by issue #472.

Pinned to geoBoundaries commit 9469f09592ced973a3448cf66b6100b741b64c0d.
Retrievals use the Git LFS media endpoint for bytes and raw.githubusercontent.com
for the Git LFS pointer receipts. It writes only beside this script under the
issue-owned packet directory.
"""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import urllib.request

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "sources" / "geoboundaries-9469f09"
COMMIT = "9469f09592ced973a3448cf66b6100b741b64c0d"
COUNTRIES = ["GHA", "GIN", "GNB", "LBR"]
# ADM0/ADM1 are held strictly as boundary-comparison context for completeness
# and parent overlays; ADM2 is the exact issue-cited source vintage.
LEVELS = ["ADM0", "ADM1", "ADM2"]
FILES = ["geoBoundaries-{iso}-{level}.geojson", "geoBoundaries-{iso}-{level}-metaData.json", "geoBoundaries-{iso}-{level}-metaData.txt"]
OUT.mkdir(parents=True, exist_ok=True)
rows = []
for iso in COUNTRIES:
  for level in LEVELS:
    prefix = f"releaseData/gbOpen/{iso}/{level}/"
    for template in FILES:
        name = template.format(iso=iso, level=level)
        # These exact LBR ADM1/ADM2 geometries are already retained once in
        # the merged West Africa packet. Reuse that licensed, hash-pinned copy.
        if iso == "LBR" and level in ("ADM1", "ADM2") and name.endswith(".geojson"):
            continue
        path = prefix + name
        raw_url = f"https://raw.githubusercontent.com/wmgeolab/geoBoundaries/{COMMIT}/{path}"
        media_url = f"https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/{COMMIT}/{path}"
        req = urllib.request.Request(raw_url, headers={"User-Agent": "WorldAtlas-geography-research/1"})
        with urllib.request.urlopen(req, timeout=90) as response:
            pointer = response.read()
        target = OUT / (iso + "-" + name)
        pointer_receipt = OUT / (iso + "-" + name + ".lfs-pointer.txt")
        pointer_receipt.write_bytes(pointer)
        pointer_text = pointer.decode("utf-8", "replace")
        if pointer_text.startswith("version https://git-lfs.github.com/spec/v1"):
            lfs_oid = next((line.split(":", 1)[1].strip() for line in pointer_text.splitlines() if line.startswith("oid sha256:")), None)
            lfs_size = next((int(line.split(None, 1)[1].strip()) for line in pointer_text.splitlines() if line.startswith("size ")), None)
            req = urllib.request.Request(media_url, headers={"User-Agent": "WorldAtlas-geography-research/1"})
            with urllib.request.urlopen(req, timeout=180) as response:
                payload = response.read()
                status, content_type = response.status, response.headers.get("Content-Type")
        else:
            payload, lfs_oid, lfs_size, status, content_type = pointer, None, len(pointer), 200, "text/plain"
        if len(payload) != lfs_size or lfs_oid and sha256(payload).hexdigest() != lfs_oid:
            raise SystemExit(f"LFS content disagrees with pinned pointer: {iso}/{name}")
        target.write_bytes(payload)
        rows.append({"iso": iso, "level": level, "path": path, "commit": COMMIT, "git_lfs_pointer_url": raw_url,
                     "media_url": media_url if lfs_oid else None, "pointer_path": pointer_receipt.relative_to(ROOT).as_posix(),
                     "pointer_bytes": len(pointer), "pointer_sha256": sha256(pointer).hexdigest(),
                     "lfs_oid_sha256": lfs_oid, "source_bytes": len(payload), "source_sha256": sha256(payload).hexdigest(),
                     "http_status": status, "content_type": content_type, "saved_path": target.relative_to(ROOT).as_posix()})
receipt = {"version": 1, "retrieved_at_utc": datetime.now(timezone.utc).isoformat(), "repository": "https://github.com/wmgeolab/geoBoundaries",
           "commit": COMMIT, "commit_date": "2023-12-13T04:03:07Z", "release_line": "gbOpen", "files": rows}
(ROOT / "geoboundaries-restoration.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps({"restored_files": len(rows), "source_bytes": sum(r["source_bytes"] for r in rows), "receipts": [r["saved_path"] for r in rows if r["path"].endswith("metaData.json")]}, indent=2))
