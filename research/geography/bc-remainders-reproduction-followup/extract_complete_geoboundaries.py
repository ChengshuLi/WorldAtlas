#!/usr/bin/env python3
"""Losslessly partition the complete oversized #485 geoBoundaries input."""
from __future__ import annotations
import gzip, hashlib, json, subprocess
from pathlib import Path

OWNED = Path(__file__).resolve().parent
REPO = OWNED.parents[2]
BASELINE = "24629e5918a144a1979db80ba7012baea42036e7"
INPUTS = OWNED / "inputs/parent/geoboundaries-complete"
SOURCE = "data/regional-review/regional-review-4254da254d94f450/sources/geoboundaries-CAN-ADM3-2016.geojson"

def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def main() -> None:
    if INPUTS.exists():
        raise SystemExit("Refusing to overwrite the retained complete-source extract")
    baseline = json.loads((OWNED / "input-baseline.json").read_text())
    pin = next(row for row in baseline["files"] if row["path"] == SOURCE)
    raw = subprocess.check_output(["git", "-C", str(REPO), "show", f"{BASELINE}:{SOURCE}"])
    if len(raw) != pin["bytes"] or digest(raw) != pin["sha256"]:
        raise ValueError("Full geoBoundaries input does not match the immutable #485 Git blob")
    if digest((REPO / SOURCE).read_bytes()) != pin["sha256"]:
        raise ValueError("Working-tree geoBoundaries source differs from the immutable input")
    source = json.loads(raw)
    features = source["features"]
    INPUTS.mkdir()
    files = []
    for start in range(0, len(features), 500):
        part = {"type": "FeatureCollection", "features": features[start:start + 500]}
        canonical = (json.dumps(part, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode()
        if len(canonical) > 32 * 1024 * 1024:
            raise ValueError("A full-source feature chunk exceeds the shared byte ceiling")
        encoded = gzip.compress(canonical, compresslevel=9, mtime=0)
        path = INPUTS / f"part-{start // 500:04d}.geojson.gz"
        path.write_bytes(encoded)
        files.append({"path": path.relative_to(OWNED).as_posix(), "bytes": len(encoded), "sha256": digest(encoded), "uncompressed_bytes": len(canonical), "uncompressed_sha256": digest(canonical), "hash_kind": "file-bytes", "source_feature_start": start, "source_feature_count": len(part["features"])})
    receipt = {
        "version": 1,
        "source_baseline_commit": BASELINE,
        "source_path": SOURCE,
        "source_bytes": pin["bytes"],
        "source_sha256": pin["sha256"],
        "source_feature_count": len(features),
        "feature_order_preserved": True,
        "chunk_size": 500,
        "files": files,
        "method": "Read and hash the complete immutable source blob, then partition its FeatureCollection.features array by source order into deterministic UTF-8 JSON gzip chunks. This is a lossless partition of the entire source; no geometry filtering or simplification is applied.",
    }
    (OWNED / "complete-geoboundaries-extraction-receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({"features": len(features), "chunks": len(files), "retained_bytes": sum(x["bytes"] for x in files)}, indent=2))

if __name__ == "__main__":
    main()
