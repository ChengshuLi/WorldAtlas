"""Candidate and official lookups read a pinned manifest outside the database transaction."""

import hashlib
import io
import json
import os
import unittest
from unittest.mock import patch
import psycopg

from worldatlas.map_build.inputs.releases import read_release_streams


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
                "INSERT INTO atlas.map_releases(id,r2_bucket,r2_prefix,manifest_sha256) VALUES (%s,%s,%s,%s)",
                (identity, "test", folder, hashlib.sha256(raw).hexdigest()),
            )
            try:
                with (
                    patch.dict(os.environ, NEON_DATABASE_URL=url),
                    patch(
                        "worldatlas.map_build.physical.build.make_r2_client",
                        return_value=storage,
                    ),
                ):
                    candidate = read_release_streams(identity)
                    self.assertEqual(
                        candidate[0][1:4], ("test", folder + "rows.u32le.gz", 12)
                    )
                    self.assertEqual(storage.key, folder + "manifest.json")
                    with self.assertRaisesRegex(ValueError, "no unique release"):
                        read_release_streams("v97.0")
                    database.execute(
                        "UPDATE atlas.map_releases SET is_official=true WHERE id=%s",
                        (identity,),
                    )
                    self.assertEqual(read_release_streams("v97.0"), candidate)
                    database.execute(
                        "UPDATE atlas.map_releases SET manifest_sha256=manifest_sha256 WHERE id=%s",
                        (identity,),
                    )
            finally:
                database.execute(
                    "DELETE FROM atlas.map_releases WHERE id=%s", (identity,)
                )
