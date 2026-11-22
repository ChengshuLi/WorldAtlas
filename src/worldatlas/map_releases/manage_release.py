"""Package, stage, publish, and restore completed WorldAtlas builds.

A preview has its own numbered folder in R2. After review and approval,
publication records the chosen release in Neon and switches the homepage to it.
Restore extracts the saved inputs for a separate map build.
"""

import argparse
import gzip
import hashlib
import mimetypes
import os
import re
import shutil
import tempfile
from contextlib import closing
from pathlib import Path
from typing import Any, Literal, overload

import psycopg
from botocore.client import BaseClient
from botocore.exceptions import ClientError
from psycopg.conninfo import conninfo_to_dict

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.execution.code_archive import read_source
from worldatlas.map_build.inputs.selection import (
    canonical_bytes,
    entity_colors,
    validate_map_code_bindings,
)
from worldatlas.map_build.physical import build as physical
from worldatlas.map_releases.catalog import (
    RELEASE_BUCKET,
    lookup_release,
    read_manifest,
    release_endpoint,
    release_prefix,
    validate_manifest,
)
from worldatlas.map_releases.inputs import (
    FILENAME as INPUTS_FILE,
)
from worldatlas.map_releases.inputs import (
    read_inputs,
    restore_inputs,
    validate_replay_sources,
    write_inputs,
)
from worldatlas.shared.files import (
    json_bytes,
    pin_file,
    read_json,
    sha256_file,
    verify_pins,
)

STREAMS = ("rows", "runs")
CANDIDATE = re.compile(r"(?P<version>v[0-9]+\.[0-9]+)-rc\.[1-9][0-9]*")
HOMEPAGE = "index.html"
# Use Python's built-in media types to keep manifests stable across machines.
MEDIA_TYPES = mimetypes.MimeTypes()


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


def release_categories(selection: dict[str, Any]) -> list[dict[str, Any]]:
    """Build the viewer's category records from the build's frozen geography.

    Args:
        selection: Saved build selection containing entities and category bindings.

    Returns:
        Records sorted by map code, with the entity ID, display name, physical
        class, and RGB color for land categories.

    Raises:
        ValueError: A category binding is invalid or a land entity lacks a color.
    """
    validate_map_code_bindings(selection["geography"])
    snapshot = selection["geography"]
    names = {entity["id"]: entity["name"] for entity in snapshot["entities"]}
    bindings = snapshot["category_bindings"]
    colors = {
        row["entity_id"]: list(bytes.fromhex(row["color_rgb"][1:]))
        for row in entity_colors(selection)
        if row["color_rgb"] is not None
    }
    land_ids = {b["entity_id"] for b in bindings if b["physical_class"] == "land"}
    if missing := sorted(land_ids - colors.keys()):
        raise ValueError(f"Saved colors are missing for land entities {missing}")
    categories = []
    for binding in sorted(bindings, key=lambda b: b["code"]):
        entity_id = binding["entity_id"]
        physical_class = binding["physical_class"]
        category = {
            "id": binding["code"],
            "entity_id": entity_id,
            "name": names[entity_id],
            "physical_class": physical_class,
        }
        if physical_class == "land":
            category["rgb"] = colors[entity_id]
        categories.append(category)
    return categories


def build_bundle(
    candidate: str, run: Path, viewer: Path, bundle: Path
) -> dict[str, Any]:
    """Package a completed build and its captured inputs in a local directory.

    Args:
        candidate: Numbered release ID used in asset URLs.
        run: Directory containing the completed build and its frozen inputs.
        viewer: Directory containing the unbundled website files.
        bundle: Empty directory that will receive the release files.

    Returns:
        The manifest of packaged files and their verified checksums.

    Raises:
        ValueError: The build is incomplete, a pinned input or output differs,
            or a release asset fails validation.
    """
    report = read_json(run / "report.json")
    if (
        report.get("schema") != "worldatlas-end-to-end-report-v2"
        or report.get("status") != "complete"
        or any(
            not report["stages"].get(name, {}).get("outputs_complete")
            for name in ("physical", "division", "package", "verification")
        )
    ):
        raise ValueError("a completed map build is required")
    identity_pin = report["original_run_identity"]
    if identity_pin != pin_file(run / "run-identity.json"):
        raise ValueError("build identity does not match the report")
    identity = read_json(run / "run-identity.json")
    request_pin = report["request"]
    if request_pin != identity["request"]:
        raise ValueError("build configuration does not match the run")
    final = report["final"]
    verify_pins([request_pin, final["report"]])
    # The report identifies the final outputs. A run can also contain streams
    # from physical rasterization and intermediate divisions.
    final_directory = Path(final["report"]["path"]).parent
    for name, filename in (
        ("rows", "rows.u32le"),
        ("runs", "runs.u32le"),
        ("report", "report.json"),
    ):
        path = Path(final[name]["path"]).resolve(strict=True)
        if not path.is_relative_to(run.resolve()) or path != final_directory / filename:
            raise ValueError(
                "expected final outputs together inside the build directory"
            )
    # The build already validated the rules. Packaging uses the frozen selection
    # as provenance and reads the category bindings needed by the viewer.
    selection = read_json(run / "input-selection.json")
    if (
        hashlib.sha256(canonical_bytes(selection)).hexdigest()
        != identity["input_selection_sha256"]
    ):
        raise ValueError("the saved geographic selection changed after the build")

    request = read_json(Path(request_pin["path"]))
    validate_replay_sources(request, selection)
    summary = read_json(final_directory / "report.json")
    grid = vars(Grid(**summary["grid"]))
    counts = summary["counts"]
    if sum(counts.values()) != grid["width"] * grid["height"]:
        raise ValueError("the output counts must cover the entire grid")
    categories = release_categories(selection)
    if {code for code, count in counts.items() if count} - {
        str(c["id"]) for c in categories
    }:
        raise ValueError("geographic snapshot is missing categories used by the map")

    attempts, source_code = [], {}
    for producer in sorted((run / "attempts").glob("*/producer.json")):
        attempt_id = producer.parent.name
        attempt = read_json(producer)
        source = attempt.get("source_archive")
        if not source:
            raise ValueError(
                f"build attempt {attempt_id} has no captured code snapshot"
            )
        if (
            Path(source["path"]).resolve()
            != (producer.parent / "source-code.json.gz").resolve()
        ):
            raise ValueError("source archive must be inside its build attempt")
        verify_pins([source])
        attempts.append(dict(attempt, attempt_id=attempt_id))
        # A resumed build can use different code. Keep each attempt's reference
        # while storing identical captured bytes just once.
        source_code[source["sha256"]] = read_source(Path(source["path"]))
    if not attempts:
        raise ValueError("completed build has no captured code snapshot")
    captured_run = dict(identity, attempts=attempts)

    for source in sorted(viewer.rglob("*")):
        rel = source.relative_to(viewer)
        if source.is_symlink() or not all(
            re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9_.-]*", part) for part in rel.parts
        ):
            raise ValueError(f"invalid viewer asset path: {rel}")
        if source.is_dir() or source.suffix == ".md":
            continue
        destination = bundle / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)

    index = bundle / "index.html"
    html = index.read_text()
    if html.count("<head>") != 1 or re.search(r"<base\b", html, re.I):
        raise ValueError("the viewer homepage must have a single head and no base URL")
    # The same HTML is served at / and under the candidate URL. In both places,
    # relative script, legend, and map URLs must resolve inside this release.
    index.write_text(
        html.replace("<head>", f'<head><base href="/{release_prefix(candidate)}">', 1)
    )

    combined = hashlib.sha256()
    grid_config = {"run_count": summary["run_count"]}
    # There is one 32-bit offset per row plus a final end offset. Each run
    # has two 32-bit values, its end column and its category code.
    stream_sizes = {"rows": 4 * (grid["height"] + 1), "runs": 8 * summary["run_count"]}
    decoded = {}
    for stream in STREAMS:
        output = bundle / f"{stream}.u32le.gz"
        raw = Path(final[stream]["path"])
        checksum = hashlib.sha256()
        size = 0
        with (
            raw.open("rb") as src,
            output.open("xb") as dst,
            gzip.GzipFile(filename="", fileobj=dst, mode="wb", mtime=0) as compressed,
        ):
            # Hash the decoded bytes during compression to verify the streams
            # without reading the large uncompressed files a second time.
            while chunk := src.read(4 << 20):
                size += len(chunk)
                checksum.update(chunk)
                combined.update(chunk)
                compressed.write(chunk)
        if (
            size != stream_sizes[stream]
            or checksum.hexdigest() != final[stream]["sha256"]
        ):
            raise ValueError(
                f"{stream} size or checksum differs from the completed build"
            )
        decoded[stream] = checksum.hexdigest()
        grid_config[stream] = output.name
        grid_config[stream + "_sha256"] = decoded[stream]

    config = bundle / "config.json"
    viewer_config = read_json(config)
    # A mixed entity has separate land and water codes but one legend entry.
    # Add the counts for both codes and use the entity's land color in the legend.
    legend = {}
    for category in categories:
        entity_id = category["entity_id"]
        entry = legend.setdefault(
            entity_id,
            {
                "id": entity_id,
                "name": category["name"],
                "color": viewer_config["water_rgb"],
                "count": 0,
            },
        )
        entry["count"] += counts.get(str(category["id"]), 0)
        if category["physical_class"] == "land":
            entry["color"] = category["rgb"]
    legend_path = bundle / "legend" / "entities.json"
    legend_path.parent.mkdir(exist_ok=True)
    legend_path.write_bytes(json_bytes(list(legend.values())))
    viewer_config.update(
        width=grid["width"],
        height=grid["height"],
        step=grid["step"],
        map_version=version(candidate),
        local_grid=grid_config,
        combined_sha256=combined.hexdigest(),
        legend="legend/entities.json",
        categories=[
            {key: category[key] for key in ("id", "entity_id", "physical_class")}
            for category in categories
        ],
    )
    config.write_bytes(json_bytes(viewer_config))

    write_inputs(
        bundle / INPUTS_FILE,
        release_id=candidate,
        configuration=request,
        selection=selection,
        run=captured_run,
        report=report,
        source_code=source_code,
    )
    # The manifest pins stored object bytes. The decoded stream hashes above
    # let the viewer and a later rebuild verify the uncompressed map.
    objects = {
        path.relative_to(bundle).as_posix(): {
            "r2_key": release_prefix(candidate) + path.relative_to(bundle).as_posix(),
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
            "content_type": (
                "application/gzip"
                if path.suffix == ".gz"
                else MEDIA_TYPES.guess_file_type(path)[0] or "application/octet-stream"
            ),
        }
        for path in sorted(bundle.rglob("*"))
        if path.is_file()
    }
    return {
        "inputs": {"archive": INPUTS_FILE},
        "decoded_sha256": decoded,
        "objects": objects,
    }


@overload
def verify_object(
    storage: BaseClient,
    bucket: str,
    key: str,
    expected: dict[str, Any],
    *,
    return_bytes: Literal[True],
) -> bytes:
    """Return the verified object's bytes."""


@overload
def verify_object(
    storage: BaseClient,
    bucket: str,
    key: str,
    expected: dict[str, Any],
    *,
    return_bytes: Literal[False] = False,
) -> None:
    """Verify the object without keeping its bytes."""


def verify_object(
    storage: BaseClient,
    bucket: str,
    key: str,
    expected: dict[str, Any],
    *,
    return_bytes: bool = False,
) -> bytes | None:
    """Verify an R2 object's size, content type, encoding, and checksum.

    Args:
        storage: Open R2 client.
        bucket: Bucket containing the object.
        key: Exact object key within that bucket.
        expected: Manifest entry containing the byte size, content type, and SHA-256.
        return_bytes: Keep the verified body in memory for callers that need it.

    Returns:
        The object's bytes if requested, or None after streaming the checksum.

    Raises:
        ValueError: The object's metadata or bytes differ from the manifest.
        ClientError: R2 could not return the object.
    """
    response = storage.get_object(Bucket=bucket, Key=key)
    with closing(response["Body"]) as body:
        if response["ContentLength"] != expected["size_bytes"] or response.get(
            "ContentEncoding"
        ):
            raise ValueError(f"wrong size or encoding for {key}")
        if response.get("ContentType") != expected["content_type"]:
            raise ValueError(f"wrong content type for {key}")
        data = body.read() if return_bytes else None
        checksum = (
            hashlib.sha256(data)
            if data is not None
            else hashlib.file_digest(body, "sha256")
        )
    if checksum.hexdigest() != expected["sha256"]:
        raise ValueError(f"published bytes differ from the candidate: {key}")
    return data


def upload_bundle(
    storage: BaseClient, bucket: str, bundle: Path, manifest: dict[str, Any]
) -> None:
    """Upload and verify the release assets listed in a prepared manifest.

    Args:
        storage: Open R2 client.
        bucket: Destination bucket.
        bundle: Local directory containing the prepared assets.
        manifest: Asset entries keyed by their relative file names.

    Raises:
        ValueError: A stored asset differs from the manifest.
        ClientError: An upload or verification request fails.
    """
    for name, asset in manifest["objects"].items():
        key = asset["r2_key"]
        with (bundle / name).open("rb") as body:
            try:
                storage.put_object(
                    Bucket=bucket,
                    Key=key,
                    Body=body,
                    IfNoneMatch="*",
                    ContentType=asset["content_type"],
                )
            except ClientError as exc:
                # On a staging retry this key may already exist. Leave those
                # bytes in place and verify them against the same manifest.
                if exc.response["ResponseMetadata"]["HTTPStatusCode"] != 412:
                    raise
        verify_object(storage, bucket, key, asset)


def retire_previews(
    db: psycopg.Connection, storage: BaseClient, map_version: str
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
        ClientError: R2 listing, verification, or deletion fails.
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
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "NoSuchKey":
                raise
            # An interrupted cleanup can leave the Neon row after the last
            # object was deleted. A nonempty folder still needs its manifest.
            remaining = storage.list_objects_v2(Bucket=bucket, Prefix=folder, MaxKeys=1)
            if remaining.get("Contents") or remaining.get("IsTruncated"):
                raise
        else:
            # Keep the list of assets available until every asset is deleted.
            for asset in manifest["objects"].values():
                storage.delete_object(Bucket=bucket, Key=asset["r2_key"])
            storage.delete_object(Bucket=bucket, Key=folder + "manifest.json")
        db.execute(
            "DELETE FROM atlas.map_releases WHERE id=%s AND NOT is_official",
            (candidate,),
        )

    retired = {row[0] for row in rows}
    # An interrupted stage can leave objects before the catalog row exists.
    # Finish listing each prefix before deleting objects from it.
    family = f"releases/{map_version}-rc."
    pages = storage.get_paginator("list_objects_v2")
    folders = sorted(
        item["Prefix"]
        for page in pages.paginate(Bucket=RELEASE_BUCKET, Prefix=family, Delimiter="/")
        for item in page.get("CommonPrefixes", ())
    )
    for folder in folders:
        candidate = folder.removeprefix("releases/").removesuffix("/")
        match = CANDIDATE.fullmatch(candidate)
        if not match or match["version"] != map_version or candidate == official:
            continue
        keys = [
            item["Key"]
            for page in pages.paginate(Bucket=RELEASE_BUCKET, Prefix=folder)
            for item in page.get("Contents", ())
        ]
        for key in keys:
            storage.delete_object(Bucket=RELEASE_BUCKET, Key=key)
        retired.add(candidate)
    return sorted(retired)


def put_homepage(
    storage: BaseClient, bucket: str, key: str, html: bytes, **condition: str
) -> None:
    """Serve the released HTML at the homepage key with cache revalidation.

    Args:
        storage: Open R2 client.
        bucket: Bucket read by the website Worker.
        key: Homepage object key, normally ``index.html``.
        html: Verified HTML bytes from the candidate bundle.
        **condition: R2 precondition from ``homepage_condition``.

    Raises:
        ClientError: The write fails or its precondition no longer holds.
    """
    storage.put_object(
        Bucket=bucket,
        Key=key,
        Body=html,
        ContentType="text/html",
        CacheControl="no-cache",
        **condition,
    )


def homepage_condition(storage: BaseClient, bucket: str) -> dict[str, str]:
    """Get the precondition for replacing or creating the homepage object.

    Args:
        storage: Open R2 client.
        bucket: Bucket containing the homepage.

    Returns:
        An ``IfMatch`` condition for the observed ETag, or ``IfNoneMatch``
        to create the homepage only if the key is still empty.

    Raises:
        ClientError: R2 returned an error other than a missing homepage.
    """
    try:
        return {"IfMatch": storage.head_object(Bucket=bucket, Key=HOMEPAGE)["ETag"]}
    except ClientError as exc:
        if exc.response["ResponseMetadata"]["HTTPStatusCode"] != 404:
            raise
        return {"IfNoneMatch": "*"}


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
    storage: BaseClient,
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
        ClientError: A required R2 operation fails.
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
    try:
        storage.put_object(
            Bucket=RELEASE_BUCKET,
            Key=asset["r2_key"],
            Body=data,
            ContentType="application/json",
            IfNoneMatch="*",
        )
    except ClientError as exc:
        if exc.response["ResponseMetadata"]["HTTPStatusCode"] != 412:
            raise
    verify_object(storage, RELEASE_BUCKET, asset["r2_key"], asset)
    if row is None:
        db.execute(
            "INSERT INTO atlas.map_releases(id,r2_bucket,manifest_sha256) VALUES (%s,%s,%s)",
            (candidate, *identity),
        )


def publish(db: psycopg.Connection, storage: BaseClient, candidate: str) -> bool:
    """Publish an approved candidate or finish cleanup for an older release.

    Args:
        db: Connection holding the release write lock.
        storage: Client for the project's release storage.
        candidate: Exact numbered candidate ID approved for publication.

    Returns:
        True if the homepage was written, or False for a cleanup-only retry.

    Raises:
        ValueError: The candidate cannot be published or an asset fails verification.
        ClientError: A required R2 operation fails.
    """
    release = lookup_release(db, candidate)
    map_version = release["map_version"]
    if release["is_official"] and not release["is_current"]:
        retire_previews(db, storage, map_version)
        return False
    selected = official_candidate(db, map_version)
    if selected is not None and selected != candidate:
        raise ValueError("this version already has a different official candidate")
    bucket = release["r2_bucket"]
    if bucket != RELEASE_BUCKET:
        raise ValueError(
            f"the website serves releases from the {RELEASE_BUCKET!r} bucket"
        )
    manifest = read_manifest(storage, release)
    if INPUTS_FILE not in manifest["objects"]:
        raise ValueError("release has no frozen input archive")
    condition = homepage_condition(storage, bucket)
    html = None
    for name, asset in manifest["objects"].items():
        data = verify_object(
            storage, bucket, asset["r2_key"], asset, return_bytes=name == "index.html"
        )
        if name == "index.html":
            html = data
    if html is None:
        raise ValueError("release has no viewer homepage")
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
    put_homepage(storage, bucket, HOMEPAGE, html, **condition)
    retire_previews(db, storage, map_version)
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
    if args.action != "restore-inputs":
        version(args.candidate)
    if not (connection := os.environ.get("NEON_DATABASE_URL")):
        parser.error("set NEON_DATABASE_URL to the release catalog database")

    if args.action != "restore-inputs" and "-pooler." in str(
        conninfo_to_dict(connection).get("host", "")
    ):
        parser.error("use a direct Neon connection for the release lock")

    with tempfile.TemporaryDirectory() as temp:
        bundle = Path(temp)
        manifest = None
        if args.action == "stage":
            manifest = build_bundle(
                args.candidate, args.run.resolve(), args.viewer.resolve(), bundle
            )
        with (
            psycopg.connect(connection, autocommit=True) as db,
            closing(physical.make_r2_client(release_endpoint())) as storage,
        ):
            if args.action == "restore-inputs":
                release = lookup_release(db, args.candidate)
                saved = read_manifest(storage, release)
                asset = saved["objects"].get(INPUTS_FILE)
                if asset is None:
                    raise ValueError("release has no input archive")
                raw = verify_object(
                    storage,
                    release["r2_bucket"],
                    asset["r2_key"],
                    asset,
                    return_bytes=True,
                )
                restore_inputs(
                    read_inputs(raw, saved["inputs"].get("release_id", release["id"])),
                    args.output,
                )
                print(f"Restored inputs to {args.output}")
                return
            # Stage and publish share a lock so preview retirement cannot race an upload.
            db.execute("SELECT pg_advisory_lock(hashtext('atlas.release_publication'))")
            if manifest is not None:
                stage(db, storage, args.candidate, bundle, manifest)
                print(f"Preview: /{release_prefix(args.candidate)}index.html")
            elif publish(db, storage, args.candidate):
                print(f"Published {args.candidate} at /")
            else:
                print(f"Finished preview cleanup for {args.candidate}")
