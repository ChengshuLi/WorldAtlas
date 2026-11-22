"""Resolve official releases and candidates through their pinned R2 manifests."""

import gzip
import hashlib
import shutil
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast

import psycopg

from worldatlas.map_releases.catalog import (
    lookup_release,
    read_manifest,
)
from worldatlas.shared.database import connect_neon
from worldatlas.shared.files import json_bytes, sha256_file, verify_pins
from worldatlas.shared.r2 import make_r2_client
from worldatlas.source_assets.cache import FileSpec, SourceCache

type ComparisonPins = dict[str, dict[str, str]]
type ReleaseStream = tuple[str, FileSpec, str]


def read_release_assets(
    identity: str,
) -> tuple[list[ReleaseStream], FileSpec]:
    """Read the map stream locations from a verified release manifest.

    Args:
        identity: Exact release ID or official map version.

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
    with closing(make_r2_client()) as storage:
        manifest = read_manifest(storage, release)
    bucket = release["r2_bucket"]
    objects = manifest["objects"]
    config = objects.get("config.json")
    if config is None:
        raise ValueError(f"comparison release {release['id']} is missing config.json")
    streams: list[ReleaseStream] = [
        (
            name,
            dict(objects[f"{name}.u32le.gz"], r2_bucket=bucket),
            manifest["decoded_sha256"][name],
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
        Path and SHA-256 pins for ``reference_rows``, ``reference_runs``,
        and ``reference_config``. The stream pins describe decoded bytes.

    Raises:
        ValueError: The manifest is invalid or a file fails checksum verification.
    """
    streams, config = read_release_assets(version)
    # Releases with the same decoded streams can share the comparison files.
    decoded_hashes = {name: decoded_hash for name, _, decoded_hash in streams}
    digest = hashlib.sha256(json_bytes(decoded_hashes)).hexdigest()
    directory = cache.directory / ("release-" + digest)
    directory.mkdir(parents=True, exist_ok=True)
    reference: ComparisonPins = {}
    for name, source, decoded_hash in streams:
        path = directory / f"{name}.u32le"
        pin = {"path": str(path), "sha256": decoded_hash}
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
        reference[f"reference_{name}"] = pin
    reference["reference_config"] = {
        "path": str(cache.acquire(config)),
        "sha256": cast(str, config["sha256"]),
    }
    return reference
