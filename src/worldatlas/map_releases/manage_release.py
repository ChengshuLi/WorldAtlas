"""Package, stage, publish, and restore completed WorldAtlas builds.

A preview has its own numbered folder in R2. After review and approval,
publication records the chosen release in Neon and switches the homepage to it.
Restore extracts the saved inputs for a separate map build.
"""

import argparse
import hashlib
import tempfile
from collections.abc import Iterator
from contextlib import closing, contextmanager
from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO

import psycopg

from worldatlas.map_releases.bundle import build_bundle
from worldatlas.map_releases.catalog import (
    CANDIDATE,
    HOMEPAGE,
    RELEASE_BUCKET,
    lookup_release,
    read_manifest,
    release_prefix,
    validate_manifest,
    version,
)
from worldatlas.map_releases.inputs import (
    FILENAME as INPUTS_FILE,
)
from worldatlas.map_releases.inputs import (
    read_inputs,
    restore_inputs,
)
from worldatlas.shared.database import connect_neon, neon_connection_url
from worldatlas.shared.files import json_bytes
from worldatlas.shared.r2 import (
    R2Client,
    R2ObjectMissing,
    make_r2_client,
)


def verify_object(
    storage: R2Client,
    bucket: str,
    key: str,
    expected: dict[str, Any],
    *,
    destination: BinaryIO | None = None,
) -> None:
    """Stream an R2 file and check its metadata and checksum.

    Args:
        storage: Open R2 client.
        bucket: Bucket containing the file.
        key: Exact file key within the bucket.
        expected: Manifest entry with the byte count, content type, and SHA-256.
        destination: Open binary stream to receive the bytes, if needed.
            Use the copied bytes after verification succeeds.

    Raises:
        ValueError: The file's metadata or checksum differs from the manifest.
        R2ObjectMissing: The file is missing.
    """
    checksum = hashlib.sha256()
    with storage.open(bucket, key) as remote:
        if remote.size_bytes != expected["size_bytes"] or remote.content_encoding:
            raise ValueError(f"wrong size or encoding for {key}")
        if remote.content_type != expected["content_type"]:
            raise ValueError(f"wrong content type for {key}")
        while chunk := remote.body.read(1 << 20):
            checksum.update(chunk)
            if destination is not None:
                destination.write(chunk)
    if checksum.hexdigest() != expected["sha256"]:
        raise ValueError(f"published bytes differ from the candidate: {key}")


def read_verified_object(
    storage: R2Client, bucket: str, key: str, expected: dict[str, Any]
) -> bytes:
    """Read an R2 file and return its bytes after verification.

    Args:
        storage: Open R2 client.
        bucket: Bucket containing the file.
        key: Exact file key within the bucket.
        expected: Manifest entry with its size, content type, and checksum.

    Returns:
        The verified file contents.
    """
    with BytesIO() as buffer:
        verify_object(storage, bucket, key, expected, destination=buffer)
        return buffer.getvalue()


def upload_bundle(
    storage: R2Client, bucket: str, bundle: Path, manifest: dict[str, Any]
) -> None:
    """Upload and verify the release assets listed in a prepared manifest.

    Args:
        storage: Open R2 client.
        bucket: Destination bucket.
        bundle: Local directory containing the prepared assets.
        manifest: Asset entries keyed by their relative file names.

    Raises:
        ValueError: A stored asset differs from the manifest.
    """
    for name, asset in manifest["objects"].items():
        key = asset["r2_key"]
        with (bundle / name).open("rb") as body:
            storage.put_if_missing(
                bucket, key, body, content_type=asset["content_type"]
            )
        verify_object(storage, bucket, key, asset)


def retire_previews(
    db: psycopg.Connection, storage: R2Client, map_version: str
) -> list[str]:
    """Remove previews, including partial uploads, after a version is official.

    Args:
        db: Connection holding the release write lock.
        storage: Client for the project's release storage.
        map_version: Version family whose previews can be removed.

    Returns:
        The sorted release IDs removed from the catalog or R2.

    Raises:
        ValueError: The version has no official release or a preview manifest is invalid.
        R2ObjectMissing: A preview has objects but no manifest.
    """
    official = official_candidate(db, map_version)
    if official is None:
        raise ValueError("publish a final candidate before retiring previews")
    rows = db.execute(
        "SELECT id,r2_bucket,manifest_sha256 FROM atlas.map_releases "
        "WHERE map_version=%s AND NOT is_official ORDER BY id",
        (map_version,),
    ).fetchall()
    for candidate, bucket, checksum in rows:
        folder = release_prefix(candidate)
        release = dict(id=candidate, r2_bucket=bucket, manifest_sha256=checksum)
        try:
            manifest = read_manifest(storage, release)
        except R2ObjectMissing:
            # An interrupted cleanup can leave the Neon row after the last
            # object was deleted. A nonempty folder still needs its manifest.
            if storage.has_objects(bucket, folder):
                raise
        else:
            # Keep the list of assets available until every asset is deleted.
            for asset in manifest["objects"].values():
                storage.delete(bucket, asset["r2_key"])
            storage.delete(bucket, folder + "manifest.json")
        db.execute(
            "DELETE FROM atlas.map_releases WHERE id=%s AND NOT is_official",
            (candidate,),
        )

    retired = {row[0] for row in rows}
    # An interrupted stage can leave objects before the catalog row exists.
    # Finish listing each prefix before deleting objects from it.
    family = f"releases/{map_version}-rc."
    for folder in sorted(storage.list_folders(RELEASE_BUCKET, family)):
        candidate = folder.removeprefix("releases/").removesuffix("/")
        match = CANDIDATE.fullmatch(candidate)
        if not match or match["version"] != map_version or candidate == official:
            continue
        for key in storage.list_keys(RELEASE_BUCKET, folder):
            storage.delete(RELEASE_BUCKET, key)
        retired.add(candidate)
    return sorted(retired)


def official_candidate(db: psycopg.Connection, map_version: str) -> str | None:
    """Return the selected candidate ID for a map version, if one is official.

    Args:
        db: Connection to the release catalog.
        map_version: Version family, such as ``v9.0``.

    Returns:
        The official release ID, or None if the version is still in review.
    """
    row = db.execute(
        "SELECT id FROM atlas.map_releases WHERE map_version=%s AND is_official",
        (map_version,),
    ).fetchone()
    return row[0] if row else None


def stage(
    db: psycopg.Connection,
    storage: R2Client,
    candidate: str,
    bundle: Path,
    manifest: dict[str, Any],
) -> None:
    """Upload a numbered preview and register its manifest in the catalog.

    Args:
        db: Connection holding the release write lock.
        storage: Client for the project's release storage.
        candidate: Numbered release ID for the preview.
        bundle: Local directory containing the prepared release files.
        manifest: Expected asset keys and checksums for the bundle.

    Raises:
        ValueError: The version has a different official candidate, the saved
            candidate differs from the bundle, or an asset fails verification.
    """
    selected = official_candidate(db, version(candidate))
    if selected is not None and selected != candidate:
        raise ValueError(
            f"{selected} is already official; stage the preview under a new map version"
        )
    validate_manifest(manifest, candidate)
    if INPUTS_FILE not in manifest["objects"]:
        raise ValueError("release has no frozen input archive")
    data = json_bytes(manifest)
    checksum = hashlib.sha256(data).hexdigest()
    row = db.execute(
        "SELECT r2_bucket,manifest_sha256 FROM atlas.map_releases WHERE id=%s",
        (candidate,),
    ).fetchone()
    identity = (RELEASE_BUCKET, checksum)
    if row is not None and row != identity:
        raise ValueError("that candidate already exists with different contents")
    upload_bundle(storage, RELEASE_BUCKET, bundle, manifest)
    asset: dict[str, Any] = dict(
        r2_key=release_prefix(candidate) + "manifest.json",
        sha256=checksum,
        size_bytes=len(data),
        content_type="application/json",
    )
    # Upload the manifest after verifying its assets. The Neon row is added
    # last so a catalog lookup can immediately follow its manifest pin.
    storage.put_if_missing(
        RELEASE_BUCKET, asset["r2_key"], data, content_type="application/json"
    )
    verify_object(storage, RELEASE_BUCKET, asset["r2_key"], asset)
    if row is None:
        db.execute(
            "INSERT INTO atlas.map_releases(id,r2_bucket,manifest_sha256) VALUES (%s,%s,%s)",
            (candidate, *identity),
        )


def publish(db: psycopg.Connection, storage: R2Client, candidate: str) -> bool:
    """Make the approved candidate the release served at the homepage.

    Args:
        db: Connection holding the release write lock.
        storage: Client for the project's release storage.
        candidate: Exact numbered candidate ID approved for publication.

    Returns:
        True after the homepage write succeeds, including when retrying a
        candidate already marked current in Neon. False when the candidate is
        already official and its ``is_current`` flag is false. For example, if
        v8.4 is current, retrying an official v8.3 leaves the homepage on v8.4.

    Raises:
        ValueError: The candidate cannot be published or a file fails verification.
        ClientError: R2 rejects the homepage write.
    """
    release = lookup_release(db, candidate)
    map_version = release["map_version"]
    if release["is_official"] and not release["is_current"]:
        return False
    selected = official_candidate(db, map_version)
    if selected is not None and selected != candidate:
        raise ValueError("this version already has a different official candidate")
    bucket = release["r2_bucket"]
    if bucket != RELEASE_BUCKET:
        raise ValueError(
            f"the website serves releases from the {RELEASE_BUCKET!r} bucket"
        )
    objects = read_manifest(storage, release)["objects"]
    if INPUTS_FILE not in objects:
        raise ValueError("release has no frozen input archive")
    homepage = objects.get(HOMEPAGE)
    if homepage is None:
        raise ValueError("release has no viewer homepage")
    etag = storage.etag(bucket, HOMEPAGE)
    html = read_verified_object(storage, bucket, homepage["r2_key"], homepage)
    for name, asset in objects.items():
        if name != HOMEPAGE:
            verify_object(storage, bucket, asset["r2_key"], asset)
    # Commit the approved choice before updating R2. If R2 fails, a retry can
    # update the homepage while this choice is current, even after a restart.
    with db.transaction():
        db.execute(
            "UPDATE atlas.map_releases SET is_current=false WHERE is_current AND id<>%s",
            (candidate,),
        )
        db.execute(
            "UPDATE atlas.map_releases SET is_official=true,is_current=true WHERE id=%s",
            (candidate,),
        )
    storage.put_if_unchanged(
        bucket,
        HOMEPAGE,
        html,
        content_type="text/html",
        cache_control="no-cache",
        expected_etag=etag,
    )
    return True


@contextmanager
def _release_writer(url: str) -> Iterator[tuple[psycopg.Connection, R2Client]]:
    """Hold the lock shared by preview uploads and publication.

    Args:
        url: Direct Neon connection string.

    Yields:
        Open Neon connection and R2 client. Closing the connection releases
        the lock so another release command can write.
    """
    with (
        connect_neon(url=url, autocommit=True) as db,
        closing(make_r2_client()) as storage,
    ):
        # Publication can retire previews, so it must wait for an upload to finish.
        db.execute("SELECT pg_advisory_lock(hashtext('atlas.release_publication'))")
        yield db, storage


def _stage_command(candidate: str, run: Path, viewer: Path, url: str) -> None:
    """Prepare a bundle locally, then upload and register it as a preview.

    Args:
        candidate: Numbered release ID, such as v9.0-rc.1.
        run: Completed map build directory.
        viewer: Directory containing the website source files.
        url: Direct Neon connection string.
    """
    with tempfile.TemporaryDirectory() as temp:
        bundle = Path(temp)
        manifest = build_bundle(candidate, run.resolve(), viewer.resolve(), bundle)
        with _release_writer(url) as (db, storage):
            stage(db, storage, candidate, bundle, manifest)
    print(f"Preview: /{release_prefix(candidate)}index.html")


def _publish_command(candidate: str, url: str) -> None:
    """Publish a candidate and retire its version's other previews under one lock.

    Args:
        candidate: Numbered release ID approved for publication.
        url: Direct Neon connection string.
    """
    map_version = version(candidate)
    with _release_writer(url) as (db, storage):
        if publish(db, storage, candidate):
            print(f"Published {candidate} at /", flush=True)
        retire_previews(db, storage, map_version)
    print(f"Finished preview cleanup for {candidate}")


def _restore_command(identity: str, output: Path, url: str) -> None:
    """Look up a release, verify its input archive, and extract it locally.

    Args:
        identity: Exact release ID or map version, such as v9.0.
        output: New directory for the saved inputs and code.
        url: Neon connection string. A pooled connection is sufficient.

    Raises:
        ValueError: The release lacks an input archive or its bytes cannot be verified.
    """
    with connect_neon(url=url, autocommit=True) as db:
        release = lookup_release(db, identity)
    with closing(make_r2_client()) as storage:
        asset = read_manifest(storage, release)["objects"].get(INPUTS_FILE)
        if asset is None:
            raise ValueError("release has no input archive")
        raw = read_verified_object(
            storage, release["r2_bucket"], asset["r2_key"], asset
        )
    restore_inputs(read_inputs(raw, release["id"]), output)
    print(f"Restored inputs to {output}")


def main() -> None:
    """Parse command-line arguments and run the selected release command."""
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    stage_args = actions.add_parser("stage")
    stage_args.add_argument("candidate")
    stage_args.add_argument("run", type=Path)
    stage_args.add_argument("--viewer", type=Path, required=True)
    publish_args = actions.add_parser("publish")
    publish_args.add_argument("candidate")
    restore_args = actions.add_parser("restore-inputs")
    restore_args.add_argument("candidate")
    restore_args.add_argument("output", type=Path)
    args = parser.parse_args()

    try:
        url = neon_connection_url(direct=args.action != "restore-inputs")
    except ValueError as exc:
        parser.error(str(exc))

    if args.action == "restore-inputs":
        _restore_command(args.candidate, args.output, url)
    elif args.action == "stage":
        _stage_command(args.candidate, args.run, args.viewer, url)
    else:
        _publish_command(args.candidate, url)
