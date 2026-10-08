#!/usr/bin/env python3
"""Retain compressed byte-identical AAFC comparison layers for issue #1481."""
from __future__ import annotations
import gzip
import hashlib
import io
import json
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKET = Path(__file__).resolve().parent
SOURCES = PACKET / "sources"
REGISTRY = ROOT / "data/semantic-sources.json"
MANIFEST = ROOT / "data/regional-review/regional-review-a9f03b364bdefa4a/sources-manifest.json"
V22 = ROOT / "data/regional-review/regional-review-a9f03b364bdefa4a/sources/aafc-terrestrial-ecoregions-v2.2.geojson"
PROVINCES = ROOT / "data/regional-review/regional-review-a9f03b364bdefa4a/sources/aafc-ecoprovinces-baseline-arcgis-layer0.geojson"
NATIVE = SOURCES / "aafc-ecoregions.native.geojson"

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def descriptor(path: Path, data: bytes, *, decoded: bytes | None = None) -> dict:
    row = {"path": path.relative_to(PACKET).as_posix(), "bytes": len(data),
           "sha256": sha(data), "hash_kind": "file-bytes"}
    if decoded is not None:
        row["uncompressed_bytes"] = len(decoded)
        row["uncompressed_sha256"] = sha(decoded)
    return row

def deterministic_gzip(data: bytes) -> bytes:
    out = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=out, compresslevel=9, mtime=0) as stream:
        stream.write(data)
    return out.getvalue()

def main() -> None:
    SOURCES.mkdir(parents=True, exist_ok=True)
    registry_bytes = REGISTRY.read_bytes()
    registry = json.loads(registry_bytes)
    source_manifest = json.loads(MANIFEST.read_bytes())
    registry_member = next(x for x in registry["files"] if x["path"] == "aafc-ecoregions.geojson")
    native_bytes = NATIVE.read_bytes()
    assert sha(native_bytes) == registry_member["sha256"] == "a565563a6aef794df831dc9251fb4108018e20a4f0172acbc36b599f9b7f4abf"
    native_fc = json.loads(native_bytes)
    assert len(native_fc["features"]) == 218
    assert sum(f["properties"].get("ECOREGION_ID") == 15 for f in native_fc["features"]) == 1
    assert sum(f["properties"].get("ECOREGION_ID") == 25 for f in native_fc["features"]) == 1
    # Reconstruct the registered archive from its six content-addressed baseline blobs.
    # This independently proves the retained member bytes are the original archive member.
    source_commit = "960ba2f4fef0fc9881b8a106a944e6e3874e98c9"
    archive_chunks = []
    for part in registry["archive_parts"]:
        path = "data/semantic-evidence/" + part["path"].split("/", 1)[-1]
        payload = subprocess.check_output(["git", "show", f"{source_commit}:{path}"])
        assert sha(payload) == part["sha256"]
        archive_chunks.append(payload)
    archive_bytes = b"".join(archive_chunks)
    assert sha(archive_bytes) == registry["archive_sha256"]
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as archive:
        member = archive.extractfile("aafc-ecoregions.geojson")
        assert member is not None and member.read() == native_bytes

    citations = {x["path"].removeprefix("sources/"): x for x in source_manifest["sources"] if isinstance(x.get("path"), str)}
    v22 = V22.read_bytes()
    provinces = PROVINCES.read_bytes()
    for name, raw, expected in [
        ("aafc-terrestrial-ecoregions-v2.2.geojson", v22,
         "f2c7ac1cabc601c364479c4616c245c993443ac61f6842f01a12078844a71e6b"),
        ("aafc-ecoprovinces-baseline-arcgis-layer0.geojson", provinces,
         "5602aa328b64c3db9236cf610056d8375f164a51651dec34dc63334ecd4bc51f"),
    ]:
        citation = citations[name]
        assert sha(raw) == citation["sha256"] == expected
        target = SOURCES / (name + ".gz")
        packed = deterministic_gzip(raw)
        target.write_bytes(packed)
        assert gzip.decompress(packed) == raw
        assert packed[9] == 255, "Gzip OS byte must remain deterministic"

    copies = []
    for name, original in [
        ("aafc-terrestrial-ecoregions-v2.2.geojson.gz", v22),
        ("aafc-ecoprovinces-baseline-arcgis-layer0.geojson.gz", provinces),
    ]:
        packed = (SOURCES / name).read_bytes()
        copies.append({"file": descriptor(SOURCES / name, packed, decoded=original),
                       "citation": citations[name.removesuffix(".gz")]})

    record = {
        "version": 1,
        "purpose": "Exact, bounded source inputs for the seven Arctic component fit checks; compressed comparison files decode byte-for-byte to their pinned baseline originals.",
        "native_member": {
            "archive_sha256": registry["archive_sha256"],
            "archive_bytes": 45601680,
            "archive_member_path": "aafc-ecoregions.geojson",
            "archive_member_bytes": len(native_bytes),
            "archive_member_sha256": sha(native_bytes),
            "registry_file_sha256": sha(registry_bytes),
            "archive_piece_records": registry["archive_parts"],
            "archive_piece_baseline_commit": source_commit,
            "archive_reconstruction_sha256": sha(archive_bytes),
            "archive_piece_transport_bytes_are_not_duplicated_here": True,
            "member_extraction_verified_against_reconstructed_archive": True,
            "note": "The retained candidate source is byte-identical to the exact member extracted from the reconstructed, six-part registered source archive. Archive custody does not establish legal or temporal authority."
        },
        "native_candidate_source": descriptor(NATIVE, native_bytes),
        "compressed_comparison_sources": copies,
        "native_feature_count": len(native_fc["features"]),
        "native_unique_ecoregion_id_count": len({f["properties"].get("ECOREGION_ID") for f in native_fc["features"]}),
        "native_ECO15_count": 1,
        "native_ECO25_count": 1,
    }
    raw = (json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    (PACKET / "source-copies.json").write_bytes(raw)
    print(json.dumps({"status": "source-copies-prepared", "native_sha256": sha(native_bytes),
                      "v22_compressed_bytes": copies[0]["file"]["bytes"],
                      "ecoprovinces_compressed_bytes": copies[1]["file"]["bytes"],
                      "source_copies_record_sha256": sha(raw)}, sort_keys=True))

if __name__ == "__main__":
    main()
