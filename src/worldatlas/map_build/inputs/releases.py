"""Resolve official releases and candidates through their pinned R2 manifests."""

from contextlib import closing
import os

import psycopg

from worldatlas.map_build.physical import build as physical_build
from worldatlas.map_releases.catalog import lookup_release, read_manifest, release_endpoint


def read_release_assets(identity):
    connection = os.environ.get("NEON_DATABASE_URL")
    if not connection:
        raise ValueError("set NEON_DATABASE_URL to the release catalog database")
    try:
        with psycopg.connect(connection) as database:
            database.execute("SET TRANSACTION READ ONLY")
            release = lookup_release(database, identity)
    except psycopg.Error:
        raise ValueError("Neon release lookup failed; check database access") from None
    with closing(physical_build.make_r2_client(release_endpoint())) as storage:
        manifest = read_manifest(storage, release)
    result = []
    for stream in ("rows", "runs"):
        asset = manifest["objects"][stream + ".u32le.gz"]
        result.append(
            (
                stream,
                release["r2_bucket"],
                asset["r2_key"],
                asset["size_bytes"],
                asset["sha256"],
                manifest["decoded_sha256"][stream],
            )
        )
    config = manifest["objects"].get("config.json")
    if config is not None:
        config = dict(config, r2_bucket=release["r2_bucket"])
    return result, config
