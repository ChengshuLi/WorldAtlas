"""Resolve immutable release manifests from compact Neon catalog rows."""

import hashlib
import json
import re
from contextlib import closing
from importlib.resources import files
from pathlib import PurePosixPath
from typing import Any

from botocore.client import BaseClient
from psycopg import Connection

RELEASE_BUCKET = "worldatlas"


def release_endpoint() -> str:
    """Read the project's release endpoint from the installed configuration.

    Returns:
        The R2 account URL used by the release commands and map comparisons.
    """
    config = json.loads(
        files("worldatlas.map_build").joinpath("config.json").read_bytes()
    )
    return config["physical_controls"]["source_staging"]["endpoint_url"]


def release_prefix(release_id: str) -> str:
    """Build the R2 key prefix for a release.

    Args:
        release_id: Exact catalog ID, such as ``v8.4-rc.1``.

    Returns:
        The release folder with a trailing slash, such as ``releases/v8.4-rc.1/``.
    """
    return f"releases/{release_id}/"


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


def read_manifest(storage: BaseClient, release: dict[str, Any]) -> dict[str, Any]:
    """Fetch the manifest from R2 and check it against the catalog.

    Args:
        storage: Open R2 client.
        release: Catalog values containing the release ID, bucket, and manifest checksum.

    Returns:
        The parsed manifest after checking its checksum and asset entries.

    Raises:
        ValueError: The bytes differ from the catalog checksum or the manifest is invalid.
        ClientError: R2 could not return the manifest.
    """
    response = storage.get_object(
        Bucket=release["r2_bucket"], Key=release_prefix(release["id"]) + "manifest.json"
    )
    with closing(response["Body"]) as stream:
        raw = stream.read()
    if hashlib.sha256(raw).hexdigest() != release["manifest_sha256"]:
        raise ValueError("release manifest does not match its Neon checksum")
    manifest = json.loads(raw)
    return validate_manifest(manifest, release["id"])


def validate_manifest(manifest: dict[str, Any], release_id: str) -> dict[str, Any]:
    """Check the manifest paths and file metadata before using its asset keys.

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
        if not isinstance(name, str) or not isinstance(asset, dict):
            raise ValueError("invalid release object")
        # Cleanup uses these keys for deletion. Each must match its own folder
        # and the relative filename, such as ``legend/entities.json``.
        path = PurePosixPath(name)
        if (
            not name
            or "\\" in name
            or path.is_absolute()
            or ".." in path.parts
            or path.as_posix() != name
            or name == "manifest.json"
            or asset.get("r2_key") != folder + name
        ):
            raise ValueError("release object escapes its own immutable folder")
        if (
            type(asset.get("size_bytes")) is not int
            or asset["size_bytes"] < 0
            or not isinstance(asset.get("sha256"), str)
            or not re.fullmatch("[0-9a-f]{64}", asset["sha256"])
            or not isinstance(asset.get("content_type"), str)
            or not asset["content_type"].strip()
        ):
            raise ValueError("invalid release object byte identity")
    if not {"rows.u32le.gz", "runs.u32le.gz"} <= manifest["objects"].keys():
        raise ValueError("release manifest lacks map streams")
    return manifest
