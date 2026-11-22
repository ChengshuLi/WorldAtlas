"""Candidate and official lookups read a pinned manifest outside the database transaction."""

import hashlib
import io
import json
import os
import unittest
from unittest.mock import patch
import psycopg

from worldatlas.shared.r2 import R2Client
from worldatlas.map_build.inputs.releases import read_release_assets
from worldatlas.map_releases.catalog import lookup_release


class ReleaseAccessTests(unittest.TestCase):
    def test_missing_or_unavailable_catalog_is_reported_without_credentials(self):
        with patch.dict(os.environ, NEON_DATABASE_URL=""):
            with self.assertRaisesRegex(ValueError, "set NEON_DATABASE_URL"):
                read_release_assets("v97.0")
        with (
            patch.dict(os.environ, NEON_DATABASE_URL="invalid"),
            patch.object(psycopg, "connect", side_effect=psycopg.OperationalError("failed")),
        ):
            with self.assertRaisesRegex(ValueError, "Neon release lookup failed"):
                read_release_assets("v97.0")


@unittest.skipUnless(
    os.environ.get("WORLDATLAS_TEST_DATABASE_URL"), "requires disposable PostgreSQL"
)
class ReleaseLookupTests(unittest.TestCase):
    def test_candidate_and_official_resolve_the_same_pinned_streams(self):
        url = os.environ["WORLDATLAS_TEST_DATABASE_URL"]
        identity = "v97.0-rc.1"
        folder = "releases/" + identity + "/"
        objects = {
            name: dict(
                r2_key=folder + name,
                sha256="a" * 64,
                size_bytes=12,
                content_type="application/gzip",
            )
            for name in ("rows.u32le.gz", "runs.u32le.gz")
        }
        objects["config.json"] = dict(
            r2_key=folder + "config.json", sha256="d" * 64, size_bytes=50,
            content_type="application/json",
        )
        raw = json.dumps(
            dict(objects=objects, decoded_sha256=dict(rows="b" * 64, runs="c" * 64))
        ).encode()

        class Storage:
            def close(self):
                pass

            def get_object(self, **kw):
                self.key = kw["Key"]
                return dict(Body=io.BytesIO(raw))

        storage = Storage()
        with psycopg.connect(url, autocommit=True) as database:
            database.execute(
                "INSERT INTO atlas.map_releases(id,r2_bucket,manifest_sha256) VALUES (%s,%s,%s)",
                (identity, "test", hashlib.sha256(raw).hexdigest()),
            )
            try:
                with (
                    patch.dict(os.environ, NEON_DATABASE_URL=url),
                    patch(
                        "worldatlas.map_build.inputs.releases.make_r2_client",
                        return_value=R2Client(storage),
                    ),
                ):
                    candidate = read_release_assets(identity)
                    streams, config = candidate
                    self.assertEqual(
                        streams,
                        [
                            (
                                "rows",
                                dict(objects["rows.u32le.gz"], r2_bucket="test"),
                                "b" * 64,
                            ),
                            (
                                "runs",
                                dict(objects["runs.u32le.gz"], r2_bucket="test"),
                                "c" * 64,
                            ),
                        ],
                    )
                    self.assertEqual(config, dict(objects["config.json"], r2_bucket="test"))
                    self.assertEqual(storage.key, folder + "manifest.json")
                    without_config = json.loads(raw)
                    without_config["objects"].pop("config.json")
                    with patch(
                        "worldatlas.map_build.inputs.releases.read_manifest",
                        return_value=without_config,
                    ):
                        self.assertEqual(read_release_assets(identity), (streams, None))
                    with self.assertRaisesRegex(ValueError, "no unique release"):
                        read_release_assets("v97.0")
                with database.transaction(force_rollback=True):
                    database.execute(
                        "UPDATE atlas.map_releases SET is_official=true WHERE id=%s",
                        (identity,),
                    )
                    self.assertEqual(
                        lookup_release(database, "v97.0"), lookup_release(database, identity)
                    )
            finally:
                database.execute(
                    "DELETE FROM atlas.map_releases WHERE id=%s", (identity,)
                )
