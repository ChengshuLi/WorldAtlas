"""Resolve immutable release manifests from compact Neon catalog rows."""

from contextlib import closing
import hashlib
from importlib.resources import files
import json
from pathlib import PurePosixPath
import re

RELEASE_BUCKET = "worldatlas"


def release_endpoint():
    """Return the R2 account endpoint used for the project's release bucket."""
    config = json.loads(files("worldatlas.map_build").joinpath("config.json").read_bytes())
    return config["physical_controls"]["source_staging"]["endpoint_url"]


def release_prefix(release_id):
    return f"releases/{release_id}/"


def lookup_release(database, identity):
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


def read_manifest(storage, release):
    response = storage.get_object(
        Bucket=release["r2_bucket"], Key=release_prefix(release["id"]) + "manifest.json"
    )
    with closing(response["Body"]) as stream:
        raw = stream.read()
    if hashlib.sha256(raw).hexdigest() != release["manifest_sha256"]:
        raise ValueError("release manifest does not match its Neon checksum")
    manifest = json.loads(raw)
    return validate_manifest(manifest, release["id"])


def validate_manifest(manifest, release_id):
    """Validate paths and byte identities before reading or retiring any asset."""
    if not isinstance(manifest, dict) or not isinstance(manifest.get("objects"), dict):
        raise ValueError("invalid release manifest")
    folder = release_prefix(release_id)
    for name, asset in manifest["objects"].items():
        if not isinstance(name, str) or not isinstance(asset, dict):
            raise ValueError("invalid release object")
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
