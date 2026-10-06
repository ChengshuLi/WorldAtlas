#!/usr/bin/env python3
"""Retrieve and losslessly partition the exact geoBoundaries source objects."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.request

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / ".cache" / "geo4-sources"
SOURCES = ROOT / "sources"
PART_BYTES = 16_000_000
COMMIT = "9469f09592ced973a3448cf66b6100b741b64c0d"
ROWS = [
    {
        "id": "gb:IND:ADM3:simplified:2018",
        "label": "IND-ADM3-simplified",
        "country": "IND",
        "tier": "ADM3",
        "boundary_year": "2018",
        "file": "geoBoundaries-IND-ADM3_simplified.geojson",
        "bytes": 40040002,
        "sha256": "4ea6807d0a0c5aac0b46ee8e31ed7c30fbec273b44345bba1e4a2bb5f299f5fb",
        "git_blob_sha1": "c2947eafd9bfcc60e2835e05f182927e6186c815",
        "lfs_oid_sha256": "4ea6807d0a0c5aac0b46ee8e31ed7c30fbec273b44345bba1e4a2bb5f299f5fb",
        "path": "releaseData/gbOpen/IND/ADM3/geoBoundaries-IND-ADM3_simplified.geojson",
        "metadata": "geoBoundaries-IND-ADM3-metaData.json",
    },
    {
        "id": "gb:IND:ADM2:2021",
        "label": "IND-ADM2",
        "country": "IND",
        "tier": "ADM2",
        "boundary_year": "2021",
        "file": "geoBoundaries-IND-ADM2.geojson",
        "bytes": 48317735,
        "sha256": "8bef6929fd65432e7dc775e7c44473e84efff064ebddbfd6b834e6291546db40",
        "git_blob_sha1": "e968822bc8d5f29cf4ffe00ffdd48f7b312bd0bc",
        "lfs_oid_sha256": "8bef6929fd65432e7dc775e7c44473e84efff064ebddbfd6b834e6291546db40",
        "path": "releaseData/gbOpen/IND/ADM2/geoBoundaries-IND-ADM2.geojson",
        "metadata": "geoBoundaries-IND-ADM2-metaData.json",
    },
    {
        "id": "gb:PAK:ADM2:2019",
        "label": "PAK-ADM2",
        "country": "PAK",
        "tier": "ADM2",
        "boundary_year": "2019",
        "file": "geoBoundaries-PAK-ADM2.geojson",
        "bytes": 1082661,
        "sha256": "108eeaa75a6de678f022e0b6d8fd8ab4c93e4b4d1a9c6a28995afe7c0731182c",
        "git_blob_sha1": "782c1025c3dc150116801f9d2f2587b7043340c4",
        "lfs_oid_sha256": "108eeaa75a6de678f022e0b6d8fd8ab4c93e4b4d1a9c6a28995afe7c0731182c",
        "path": "releaseData/gbOpen/PAK/ADM2/geoBoundaries-PAK-ADM2.geojson",
        "metadata": "geoBoundaries-PAK-ADM2-metaData.json",
    },
]


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def git_blob_sha1(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "WorldAtlas-geography-source-research/1.0"})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def source_url(row):
    return "https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/{}/{}".format(COMMIT, row["path"])


def metadata_url(row):
    path = "releaseData/gbOpen/{}/{}/{}".format(row["country"], row["tier"], row["metadata"])
    return "https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/{}/{}".format(COMMIT, path)


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-dir", type=Path, default=CACHE)
    args = parser.parse_args()
    cache = args.cache_dir.resolve()
    part_dir = SOURCES / "original-byte-parts"
    meta_dir = SOURCES / "upstream-metadata"
    part_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)
    retrieved = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    sources = []
    metadata = []
    for row in ROWS:
        raw_path = cache / row["file"]
        if not raw_path.is_file():
            raw = fetch(source_url(row))
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(raw)
        raw = raw_path.read_bytes()
        if len(raw) != row["bytes"] or sha256(raw) != row["sha256"] or row["sha256"] != row["lfs_oid_sha256"]:
            raise SystemExit("whole source byte count, SHA-256 or LFS OID mismatch: " + row["label"])
        parts = []
        for index, offset in enumerate(range(0, len(raw), PART_BYTES)):
            part = raw[offset:offset + PART_BYTES]
            name = "{}-{:03d}.source-bytes".format(row["label"].lower(), index)
            path = part_dir / name
            if path.exists() and path.read_bytes() != part:
                raise SystemExit("refusing to overwrite different source part: " + str(path))
            path.write_bytes(part)
            parts.append({"path": str(path.relative_to(ROOT)), "offset": offset, "bytes": len(part), "sha256": sha256(part)})
        restored = b"".join((ROOT / part["path"]).read_bytes() for part in parts)
        if len(restored) != row["bytes"] or sha256(restored) != row["lfs_oid_sha256"]:
            raise SystemExit("partition reassembly does not equal pinned LFS object: " + row["label"])
        metadata_raw = fetch(metadata_url(row))
        metadata_obj = json.loads(metadata_raw.decode("utf-8"))
        metadata_path = meta_dir / row["metadata"]
        if metadata_path.exists() and metadata_path.read_bytes() != metadata_raw:
            raise SystemExit("refusing to overwrite different source metadata: " + str(metadata_path))
        metadata_path.write_bytes(metadata_raw)
        metadata.append({
            "path": str(metadata_path.relative_to(ROOT)),
            "url": metadata_url(row),
            "retrieved_at_utc": retrieved,
            "bytes": len(metadata_raw),
            "sha256": sha256(metadata_raw),
            "metadata": metadata_obj,
        })
        pointer = ("version https://git-lfs.github.com/spec/v1\n"
                   "oid sha256:{}\nsize {}\n".format(row["lfs_oid_sha256"], row["bytes"])).encode()
        if git_blob_sha1(pointer) != row["git_blob_sha1"]:
            raise SystemExit("GitHub source pointer blob SHA-1 mismatch: " + row["label"])
        sources.append({
            "id": row["id"], "country": row["country"], "tier": row["tier"],
            "boundary_year": row["boundary_year"], "file_name": row["file"],
            "upstream_repository": "https://github.com/wmgeolab/geoBoundaries",
            "upstream_commit": COMMIT, "upstream_path": row["path"],
            "retrieval_url": source_url(row), "retrieved_at_utc": retrieved,
            "bytes": row["bytes"], "encoded_bytes": row["bytes"], "decoded_bytes": row["bytes"],
            "source_content_encoding": "identity (uncompressed GeoJSON); decoded bytes equal original bytes",
            "sha256": row["sha256"],
            "github_git_blob_sha1": row["git_blob_sha1"],
            "github_lfs_oid_sha256": row["lfs_oid_sha256"],
            "lfs_pointer_bytes": len(pointer), "lfs_pointer_sha256": sha256(pointer),
            "retention": "complete original bytes partitioned at fixed offsets; byte-for-byte reassembly verified",
            "parts": parts,
        })
        print("verified {}: {} bytes in {} part(s)".format(row["label"], len(raw), len(parts)))
    license_url = "https://raw.githubusercontent.com/wmgeolab/geoBoundaries/{}/LICENSE".format(COMMIT)
    license_raw = fetch(license_url)
    license_path = meta_dir / "geoBoundaries-LICENSE"
    if license_path.exists() and license_path.read_bytes() != license_raw:
        raise SystemExit("refusing to overwrite different upstream project license")
    license_path.write_bytes(license_raw)
    license_receipt = {"path": str(license_path.relative_to(ROOT)), "url": license_url,
                       "retrieved_at_utc": retrieved, "bytes": len(license_raw), "sha256": sha256(license_raw)}
    receipt = {
        "version": "worldatlas-source-custody-v1",
        "retrieved_at_utc": retrieved,
        "upstream_repository": "https://github.com/wmgeolab/geoBoundaries",
        "upstream_commit": COMMIT,
        "git_lfs_pointer": "Each source Git tree entry is a pointer whose Git blob SHA-1, declared LFS object SHA-256 and byte count are independently verified.",
        "partition_policy": {"kind": "lossless-fixed-offset-byte-partition", "part_bytes": PART_BYTES,
                              "interpretation": "Parts are contiguous original byte ranges, not parsed/reformatted or feature-level extracts."},
        "sources": sources,
        "metadata_files": metadata,
        "project_license_file": license_receipt,
        "license_reading": "IND boundary metadata names ODbL 1.0; PAK boundary metadata names Public Domain. The project LICENSE says individual data files use license(s) identified in their metadata.",
    }
    target = SOURCES / "source-custody.json"
    encoded = (json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    if target.exists() and target.read_bytes() != encoded:
        raise SystemExit("refusing to overwrite different source-custody receipt")
    target.write_bytes(encoded)
    print("wrote {}".format(target.relative_to(ROOT)))


if __name__ == "__main__":
    run()
