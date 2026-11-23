"""Package, stage, publish, and restore completed WorldAtlas builds.

A preview has its own numbered folder in R2. After review and approval,
publication records the chosen release in Neon and switches the homepage to it.
Restore extracts the saved inputs for a separate map build.
"""

import argparse
import hashlib
import tempfile
from contextlib import closing
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
    """Switch the homepage to an approved candidate.

    Args:
        db: Connection holding the release write lock.
        storage: Client for the project's release storage.
        candidate: Exact numbered candidate ID approved for publication.

    Returns:
        True if the homepage was written, or False if this release is already
        official and another release is selected for the homepage.

    Raises:
        ValueError: The candidate cannot be published or an asset fails verification.
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
    storage.put(
        bucket,
        HOMEPAGE,
        html,
        content_type="text/html",
        cache_control="no-cache",
        expected_etag=etag,
    )
    return True


def main() -> None:
    """Run the requested release operation and print its result.

    Stage prepares a local bundle before taking the shared release lock.
    Publish uses the same lock for the homepage switch and preview cleanup.
    Restore reads the catalog and archive and writes only to the local output directory.
    """
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
    restoring = args.action == "restore-inputs"
    map_version = None if restoring else version(args.candidate)
    try:
        url = neon_connection_url(direct=not restoring)
    except ValueError as exc:
        parser.error(str(exc))

    if map_version is None:
        with connect_neon(url=url, autocommit=True) as db:
            release = lookup_release(db, args.candidate)
        with closing(make_r2_client()) as storage:
            asset = read_manifest(storage, release)["objects"].get(INPUTS_FILE)
            if asset is None:
                raise ValueError("release has no input archive")
            raw = read_verified_object(
                storage, release["r2_bucket"], asset["r2_key"], asset
            )
        restore_inputs(read_inputs(raw, release["id"]), args.output)
        print(f"Restored inputs to {args.output}")
        return

    with tempfile.TemporaryDirectory() as temp:
        bundle = Path(temp)
        manifest = None
        if args.action == "stage":
            manifest = build_bundle(
                args.candidate, args.run.resolve(), args.viewer.resolve(), bundle
            )
        with (
            connect_neon(url=url, autocommit=True) as db,
            closing(make_r2_client()) as storage,
        ):
            # Stage and publish share a lock so preview retirement cannot race an upload.
            db.execute("SELECT pg_advisory_lock(hashtext('atlas.release_publication'))")
            if manifest is not None:
                stage(db, storage, args.candidate, bundle, manifest)
                print(f"Preview: /{release_prefix(args.candidate)}index.html")
                return
            if publish(db, storage, args.candidate):
                print(f"Published {args.candidate} at /", flush=True)
            retire_previews(db, storage, map_version)
            print(f"Finished preview cleanup for {args.candidate}")
