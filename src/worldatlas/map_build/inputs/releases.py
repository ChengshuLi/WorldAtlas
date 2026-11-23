"""Resolve official releases and candidates through their pinned R2 manifests."""

import gzip
import hashlib
import re
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import psycopg
from typing_extensions import TypedDict

from worldatlas.map_releases.catalog import (
    lookup_release,
    read_manifest,
)
from worldatlas.shared.database import connect_neon
from worldatlas.shared.files import json_bytes, sha256_file, verify_pins
from worldatlas.shared.r2 import R2Client
from worldatlas.source_assets.cache import FileSpec, SourceCache


class StreamPin(TypedDict, closed=True):
    """A local comparison file with checksummed, decoded bytes."""

    path: str
    sha256: str


class ComparisonPins(TypedDict):
    """Verified map streams and category mapping for the reference release."""

    reference_rows: StreamPin
    reference_runs: StreamPin
    reference_config: Path


type ReleaseStream = tuple[str, FileSpec, str]


def read_release_assets(
    identity: str, storage: R2Client
) -> tuple[list[ReleaseStream], FileSpec]:
    """Read the map stream locations from a verified release manifest.

    Args:
        identity: Exact release ID or official map version.
        storage: Open R2 client shared with the comparison cache.

    Returns:
        (streams, config). Each stream contains its name, a ready-to-use R2
        file reference for the gzip file, and the SHA-256 of its decoded bytes.
        Config is the R2 file reference for the viewer's category mapping.

    Raises:
        ValueError: The release cannot be found or its inputs are invalid or incomplete.
    """
    try:
        with connect_neon() as database:
            database.execute("SET TRANSACTION READ ONLY")
            release = lookup_release(database, identity)
    except psycopg.Error:
        raise ValueError("Neon release lookup failed; check database access") from None
    manifest = read_manifest(storage, release)
    bucket = release["r2_bucket"]
    objects = manifest["objects"]
    config = objects.get("config.json")
    if config is None:
        raise ValueError(f"comparison release {release['id']} is missing config.json")
    hashes = manifest.get("decoded_sha256", {})
    if not isinstance(hashes, dict) or any(
        not isinstance(hashes.get(name), str)
        or not re.fullmatch("[0-9a-f]{64}", hashes[name])
        for name in ("rows", "runs")
    ):
        raise ValueError("comparison release requires both decoded stream checksums")
    streams: list[ReleaseStream] = [
        (
            name,
            dict(objects[f"{name}.u32le.gz"], r2_bucket=bucket),
            hashes[name],
        )
        for name in ("rows", "runs")
    ]
    return streams, dict(config, r2_bucket=bucket)


def cache_release_reference(version: str, cache: SourceCache) -> ComparisonPins:
    """Cache and verify a published map's comparison files.

    Args:
        version: Official version or numbered preview.
        cache: Open cache for downloading release files.

    Returns:
        Pins for the decoded row and run streams, and the verified local path to
        the reference release configuration.

    Raises:
        ValueError: The manifest is invalid or a file fails checksum verification.
    """
    streams, config = read_release_assets(version, cache.client)
    # Releases with the same decoded streams can share the comparison files.
    decoded_hashes = {name: decoded_hash for name, _, decoded_hash in streams}
    digest = hashlib.sha256(json_bytes(decoded_hashes)).hexdigest()
    directory = cache.directory / ("release-" + digest)
    directory.mkdir(parents=True, exist_ok=True)
    reference: dict[str, StreamPin] = {}
    for name, source, decoded_hash in streams:
        path = directory / f"{name}.u32le"
        pin: StreamPin = {"path": str(path), "sha256": decoded_hash}
        if path.exists():
            verify_pins([pin])
        else:
            compressed = cache.acquire(source)
            # Publish under the final name only after verifying the full file.
            with TemporaryDirectory(dir=directory) as staging:
                pending = Path(staging) / path.name
                with gzip.open(compressed, "rb") as src, pending.open("wb") as dst:
                    shutil.copyfileobj(src, dst, 1 << 20)
                if sha256_file(pending) != decoded_hash:
                    raise ValueError("decoded reference stream hash mismatch")
                pending.replace(path)
        reference[name] = pin
    return {
        "reference_rows": reference["rows"],
        "reference_runs": reference["runs"],
        "reference_config": cache.acquire(config),
    }
