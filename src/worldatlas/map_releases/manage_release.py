"""Stage immutable release bundles; publish only at the user's instruction."""

import argparse
from contextlib import closing
import gzip
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import re
import shutil
import tempfile

from worldatlas.map_build.execution.runtime import digest, json_bytes, pin, verify_pins
from worldatlas.map_build.inputs.selection import (
    entity_colors,
    canonical_bytes,
    read_saved,
    validate_bindings,
)
from worldatlas.map_releases.inputs import (
    FILENAME as INPUTS_FILE,
    read_inputs,
    restore_inputs,
    write_inputs,
)

STREAMS = ("rows", "runs")
CANDIDATE = re.compile(r"(?P<version>v[0-9]+\.[0-9]+)-rc\.[1-9][0-9]*")
HOMEPAGE = "index.html"


def version(candidate):
    match = CANDIDATE.fullmatch(candidate)
    if not match:
        raise ValueError("candidate must look like v9.0-rc.1")
    return match["version"]


def prefix(candidate):
    return f"releases/{candidate}"


def read(path):
    return json.loads(path.read_bytes())


def release_categories(selection):
    validate_bindings(selection["geography"])
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


def build_bundle(candidate, run, viewer, bundle):
    report = read(run / "report.json")
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
    if identity_pin != pin(run / "run-identity.json"):
        raise ValueError("build identity does not match the report")
    identity = read(run / "run-identity.json")
    request_pin = report["request"]
    if request_pin != identity["request"]:
        raise ValueError("build configuration does not match the run")
    final = report["final"]
    verify_pins([request_pin, *final.values()])
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
    selection = read_saved(run / "input-selection.json")
    if (
        hashlib.sha256(canonical_bytes(selection)).hexdigest()
        != identity["input_selection_sha256"]
    ):
        raise ValueError("the saved geographic selection changed after the build")

    request = read(Path(request_pin["path"]))
    summary = read(final_directory / "report.json")
    from worldatlas.map_build.core.grid import Grid

    grid = vars(Grid(**summary["grid"]))
    counts = summary["counts"]
    if sum(counts.values()) != grid["width"] * grid["height"]:
        raise ValueError("the output counts must cover the entire grid")
    categories = release_categories(selection)
    if {code for code, count in counts.items() if count} - {
        str(c["id"]) for c in categories
    }:
        raise ValueError("geographic snapshot is missing categories used by the map")

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
    index.write_text(
        html.replace("<head>", f'<head><base href="/{prefix(candidate)}/">', 1)
    )

    combined = hashlib.sha256()
    grid_config = {"run_count": summary["run_count"]}
    decoded = {}
    for stream in STREAMS:
        output = bundle / f"{stream}.u32le.gz"
        raw = Path(final[stream]["path"])
        checksum = hashlib.sha256()
        with (
            raw.open("rb") as src,
            output.open("xb") as dst,
            gzip.GzipFile(filename="", fileobj=dst, mode="wb", mtime=0) as compressed,
        ):
            while chunk := src.read(4 << 20):
                checksum.update(chunk)
                combined.update(chunk)
                compressed.write(chunk)
        if checksum.hexdigest() != final[stream]["sha256"]:
            raise ValueError(f"{stream} changed while preparing the release")
        decoded[stream] = checksum.hexdigest()
        grid_config[stream] = output.name
        grid_config[stream + "_sha256"] = decoded[stream]

    config = bundle / "config.json"
    viewer_config = read(config)
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

    from worldatlas.map_build.execution.code_archive import read_source

    attempts, source_code = [], {}
    for producer in sorted((run / "attempts").glob("*/producer.json")):
        attempt = read(producer)
        attempts.append(dict(attempt, attempt_id=producer.parent.name))
        if source := attempt.get("source_archive"):
            if (
                Path(source["path"]).resolve()
                != (producer.parent / "source-code.json.gz").resolve()
            ):
                raise ValueError("source archive must be inside its build attempt")
            verify_pins([source])
            source_code[source["sha256"]] = read_source(Path(source["path"]))
    captured_run = dict(identity, attempts=attempts)
    write_inputs(
        bundle / INPUTS_FILE,
        release_id=candidate,
        configuration=request,
        selection=selection,
        run=captured_run,
        report=report,
        source_code=source_code,
    )
    endpoint = (
        request.get("physical_controls", {})
        .get("source_staging", {})
        .get("endpoint_url")
    )
    inputs = {"archive": INPUTS_FILE}
    if endpoint is not None:
        inputs["r2_endpoint"] = endpoint

    objects = {
        path.relative_to(bundle).as_posix(): {
            "r2_key": f"{prefix(candidate)}/{path.relative_to(bundle).as_posix()}",
            "sha256": digest(path),
            "size_bytes": path.stat().st_size,
            "content_type": (
                "application/gzip"
                if path.suffix == ".gz"
                else mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            ),
        }
        for path in sorted(bundle.rglob("*"))
        if path.is_file()
    }
    manifest = {"inputs": inputs, "decoded_sha256": decoded, "objects": objects}
    (bundle / "manifest.json").write_bytes(json_bytes(manifest))
    return manifest


def verify_object(storage, bucket, key, expected, *, return_bytes=False):
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
            if return_bytes
            else hashlib.file_digest(body, "sha256")
        )
    if checksum.hexdigest() != expected["sha256"]:
        raise ValueError(f"published bytes differ from the candidate: {key}")
    return data


def upload_bundle(storage, bucket, candidate, bundle, manifest):
    from botocore.exceptions import ClientError

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
                if exc.response["ResponseMetadata"]["HTTPStatusCode"] != 412:
                    raise
        verify_object(storage, bucket, key, asset)


def retire_previews(db, storage, map_version):
    """Retire unpublished siblings only after a final candidate is official."""
    from botocore.exceptions import ClientError

    from worldatlas.map_releases.catalog import read_manifest

    official = db.execute(
        "SELECT id FROM atlas.map_releases WHERE map_version=%s AND is_official",
        (map_version,),
    ).fetchone()
    if official is None:
        raise ValueError("publish a final candidate before retiring previews")
    rows = db.execute(
        "SELECT id,r2_bucket,r2_prefix,manifest_sha256 FROM atlas.map_releases "
        "WHERE map_version=%s AND NOT is_official ORDER BY id",
        (map_version,),
    ).fetchall()
    for candidate, bucket, folder, checksum in rows:
        release = dict(
            id=candidate, r2_bucket=bucket, r2_prefix=folder, manifest_sha256=checksum
        )
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
            for asset in manifest["objects"].values():
                storage.delete_object(Bucket=bucket, Key=asset["r2_key"])
            storage.delete_object(Bucket=bucket, Key=folder + "manifest.json")
        db.execute(
            "DELETE FROM atlas.map_releases WHERE id=%s AND NOT is_official",
            (candidate,),
        )
    return [r[0] for r in rows]


def put_homepage(storage, bucket, key, html, **condition):
    storage.put_object(
        Bucket=bucket,
        Key=key,
        Body=html,
        ContentType="text/html",
        CacheControl="no-cache",
        **condition,
    )


def homepage_condition(storage, bucket):
    from botocore.exceptions import ClientError

    try:
        return {"IfMatch": storage.head_object(Bucket=bucket, Key=HOMEPAGE)["ETag"]}
    except ClientError as exc:
        if exc.response["ResponseMetadata"]["HTTPStatusCode"] != 404:
            raise
        return {"IfNoneMatch": "*"}


def stage(db, storage, bucket, candidate, bundle, manifest):
    version(candidate)
    from worldatlas.map_releases.catalog import validate_manifest

    validate_manifest(manifest, dict(r2_prefix=prefix(candidate) + "/"))
    if INPUTS_FILE not in manifest["objects"]:
        raise ValueError("release has no frozen input archive")
    data = json_bytes(manifest)
    checksum = hashlib.sha256(data).hexdigest()
    row = db.execute(
        "SELECT r2_bucket,r2_prefix,manifest_sha256 FROM atlas.map_releases WHERE id=%s",
        (candidate,),
    ).fetchone()
    identity = (bucket, prefix(candidate) + "/", checksum)
    if row is not None and row != identity:
        raise ValueError("that candidate already exists with different contents")
    upload_bundle(storage, bucket, candidate, bundle, manifest)
    asset = dict(
        r2_key=prefix(candidate) + "/manifest.json",
        sha256=checksum,
        size_bytes=len(data),
        content_type="application/json",
    )
    # Publish the manifest after all its immutable assets exist.
    from botocore.exceptions import ClientError

    try:
        storage.put_object(
            Bucket=bucket,
            Key=asset["r2_key"],
            Body=data,
            ContentType="application/json",
            IfNoneMatch="*",
        )
    except ClientError as exc:
        if exc.response["ResponseMetadata"]["HTTPStatusCode"] != 412:
            raise
    verify_object(storage, bucket, asset["r2_key"], asset)
    if row is None:
        db.execute(
            "INSERT INTO atlas.map_releases(id,r2_bucket,r2_prefix,manifest_sha256) VALUES (%s,%s,%s,%s)",
            (candidate, *identity),
        )


def publish(db, storage, candidate):
    from worldatlas.map_releases.catalog import lookup_release, read_manifest

    release = lookup_release(db, candidate)
    manifest = read_manifest(storage, release)
    bucket = release["r2_bucket"]
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
    with db.transaction():
        existing = db.execute(
            "SELECT id FROM atlas.map_releases WHERE map_version=%s AND is_official FOR UPDATE",
            (release["map_version"],),
        ).fetchone()
        if existing is not None and existing[0] != candidate:
            raise ValueError("this version already has a different official candidate")
        # R2 and PostgreSQL are separate services. A retry of this same candidate
        # reconciles metadata if the website switch succeeds before a DB failure.
        put_homepage(storage, bucket, HOMEPAGE, html, **condition)
        db.execute(
            "UPDATE atlas.map_releases SET is_current=false WHERE is_current AND id<>%s",
            (candidate,),
        )
        db.execute(
            "UPDATE atlas.map_releases SET is_official=true,is_current=true WHERE id=%s",
            (candidate,),
        )
    retire_previews(db, storage, release["map_version"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    stage_args = actions.add_parser("stage")
    stage_args.add_argument("candidate")
    stage_args.add_argument("run", type=Path)
    stage_args.add_argument("--viewer", type=Path, required=True)
    stage_args.add_argument("--bucket", default="worldatlas")
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

    import psycopg
    from psycopg.conninfo import conninfo_to_dict

    if "-pooler." in conninfo_to_dict(connection).get("host", ""):
        parser.error("use a direct Neon connection for the release lock")

    with tempfile.TemporaryDirectory() as temp:
        bundle = Path(temp)
        with psycopg.connect(connection, autocommit=True) as db:
            if args.action == "restore-inputs":
                from worldatlas.map_releases.catalog import (
                    lookup_release,
                    read_manifest,
                )

                release = lookup_release(db, args.candidate)
                bucket = release["r2_bucket"]
                from worldatlas.map_build.physical import build as physical
                from worldatlas.map_build import build as map_build

                endpoint = read(Path(map_build.__file__).with_name("config.json"))[
                    "physical_controls"
                ]["source_staging"]["endpoint_url"]
                with closing(physical.make_r2_client(endpoint)) as storage:
                    saved = read_manifest(storage, release)
                    asset = saved["objects"].get(INPUTS_FILE)
                    if asset is None:
                        raise ValueError("release has no input archive")
                    raw = verify_object(
                        storage, bucket, asset["r2_key"], asset, return_bytes=True
                    )
                restore_inputs(
                    read_inputs(raw, saved["inputs"].get("release_id", release["id"])),
                    args.output,
                )
                print(f"Restored inputs to {args.output}")
                return
            if args.action == "stage":
                manifest = build_bundle(
                    args.candidate, args.run.resolve(), args.viewer.resolve(), bundle
                )
            if args.action == "publish":
                db.execute(
                    "SELECT pg_advisory_lock(hashtext('atlas.release_publication'))"
                )
            from worldatlas.map_build.physical import build as physical

            if args.action == "stage":
                endpoint = manifest["inputs"].get("r2_endpoint")
            else:
                endpoint = None
            if endpoint is None:
                from worldatlas.map_build import build as map_build

                endpoint = read(Path(map_build.__file__).with_name("config.json"))[
                    "physical_controls"
                ]["source_staging"]["endpoint_url"]
            with closing(physical.make_r2_client(endpoint)) as storage:
                if args.action == "stage":
                    stage(db, storage, args.bucket, args.candidate, bundle, manifest)
                    print(f"Preview: /{prefix(args.candidate)}/index.html")
                else:
                    publish(db, storage, args.candidate)
                    print(f"Published {args.candidate} at /")


if __name__ == "__main__":
    main()
