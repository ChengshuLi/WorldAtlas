"""Resolve immutable release manifests from compact Neon catalog rows."""

import hashlib
import json
import re
from typing import Any

from psycopg import Connection

from worldatlas.shared.r2 import R2Client

RELEASE_BUCKET = "worldatlas"
HOMEPAGE = "index.html"
CANDIDATE = re.compile(r"(?P<version>v[0-9]+\.[0-9]+)-rc\.[1-9][0-9]*")


def release_prefix(release_id: str) -> str:
    """Build the R2 key prefix for a release.

    Args:
        release_id: Exact catalog ID, such as ``v8.4-rc.1``.

    Returns:
        The release folder with a trailing slash, such as ``releases/v8.4-rc.1/``.
    """
    return f"releases/{release_id}/"


def version(candidate: str) -> str:
    """Get the map version from a numbered release candidate.

    Args:
        candidate: Numbered release ID, such as ``v8.4-rc.1``.

    Returns:
        The version shared by its candidates, such as ``v8.4``.

    Raises:
        ValueError: The ID is missing a valid candidate number.
    """
    match = CANDIDATE.fullmatch(candidate)
    if not match:
        raise ValueError("candidate must look like v9.0-rc.1")
    return match["version"]


def lookup_release(database: Connection, identity: str) -> dict[str, Any]:
    """Look up an exact release or the official choice for a map version.

    Args:
        database: Open PostgreSQL connection to the release catalog.
        identity: A release ID such as ``v8.4-rc.1`` or a version such as ``v8.4``.

    Returns:
        Catalog values keyed by column name, including the R2 bucket,
        manifest checksum, and publication flags.

    Raises:
        ValueError: The identity resolves to zero or multiple catalog rows.
    """
    rows = database.execute(
        "SELECT id,map_version,r2_bucket,manifest_sha256,is_official,is_current "
        "FROM atlas.map_releases WHERE id=%s OR (map_version=%s AND is_official)",
        (identity, identity),
    ).fetchall()
    if len(rows) != 1:
        raise ValueError(f"no unique release for {identity}")
    return dict(
        zip(
            (
                "id",
                "map_version",
                "r2_bucket",
                "manifest_sha256",
                "is_official",
                "is_current",
            ),
            rows[0],
        )
    )


def read_manifest(storage: R2Client, release: dict[str, Any]) -> dict[str, Any]:
    """Fetch the manifest from R2 and check it against the catalog.

    Args:
        storage: Open R2 client.
        release: Catalog values containing the release ID, bucket, and manifest checksum.

    Returns:
        The parsed manifest after checking its checksum and asset entries.

    Raises:
        ValueError: The bytes differ from the catalog checksum or the manifest is invalid.
        R2ObjectMissing: The manifest key does not exist.
    """
    key = release_prefix(release["id"]) + "manifest.json"
    with storage.open(release["r2_bucket"], key) as remote:
        raw = remote.body.read()
    if hashlib.sha256(raw).hexdigest() != release["manifest_sha256"]:
        raise ValueError("release manifest does not match its Neon checksum")
    manifest = json.loads(raw)
    return validate_manifest(manifest, release["id"])


def validate_manifest(manifest: dict[str, Any], release_id: str) -> dict[str, Any]:
    """Check where the release files belong and how to verify their bytes.

    Args:
        manifest: Parsed JSON with an ``objects`` mapping keyed by file name.
        release_id: Exact catalog ID used to derive the allowed R2 folder.

    Returns:
        The validated manifest.

    Raises:
        ValueError: An asset key escapes its release, its metadata is invalid,
            or the manifest lacks a required map stream.
    """
    if not isinstance(manifest, dict) or not isinstance(manifest.get("objects"), dict):
        raise ValueError("invalid release manifest")
    folder = release_prefix(release_id)
    for name, asset in manifest["objects"].items():
        if not isinstance(asset, dict):
            raise ValueError(f"invalid release object for {name!r}")
        # Asset names are relative paths such as legend/entities.json.
        if "\\" in name or any(part in ("", ".", "..") for part in name.split("/")):
            raise ValueError(f"invalid release asset path: {name!r}")
        # Cleanup deletes the manifest last so it can retry with the same list.
        if name == "manifest.json":
            raise ValueError("manifest.json must stay outside the asset list")
        # Derive the expected key so cleanup stays inside this release's folder.
        if asset.get("r2_key") != folder + name:
            raise ValueError(f"release asset has the wrong R2 key: {name!r}")

        size_bytes = asset.get("size_bytes")
        if type(size_bytes) is not int or size_bytes < 0:
            raise ValueError(f"invalid byte count for release asset {name!r}")
        sha256 = asset.get("sha256")
        if not isinstance(sha256, str) or not re.fullmatch("[0-9a-f]{64}", sha256):
            raise ValueError(f"invalid SHA-256 for release asset {name!r}")
        content_type = asset.get("content_type")
        if not isinstance(content_type, str) or not content_type.strip():
            raise ValueError(f"missing content type for release asset {name!r}")
    if not {"rows.u32le.gz", "runs.u32le.gz"} <= manifest["objects"].keys():
        raise ValueError("release manifest lacks map streams")
    return manifest
