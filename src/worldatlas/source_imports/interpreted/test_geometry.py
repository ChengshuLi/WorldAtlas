"""Test saving directly selected coordinates without downloading evidence."""

from contextlib import nullcontext, redirect_stdout
import io
import json
import os
import sys
import unittest
from unittest.mock import patch

import psycopg
from psycopg.types.json import Jsonb

from worldatlas.source_imports.run_import import main


@unittest.skipUnless(
    os.environ.get("WORLDATLAS_TEST_DATABASE_URL"), "requires disposable PostgreSQL"
)
class InterpretedGeometryTests(unittest.TestCase):
    """Exercise the interpreted construction through its registry entry."""

    def test_saves_recipe_coordinates_and_links_evidence_without_r2(self):
        geometry = dict(type="Point", coordinates=[10, 20])
        arguments = dict(
            source_ids=["evidence"], basis="Selected point",
            selections=[dict(feature_id="label", geometry=geometry)],
        )
        with psycopg.connect(os.environ["WORLDATLAS_TEST_DATABASE_URL"]) as database:
            with database.transaction(force_rollback=True):
                database.execute(
                    "INSERT INTO atlas.source_assets "
                    "(id,title,provider,source_uri,license_name,license_uri,attribution,"
                    "r2_bucket,r2_key,sha256,size_bytes) "
                    "VALUES ('evidence','Test','Test','test:evidence','Test','test:license','Test',"
                    "'test','figure.pdf',%s,1)",
                    ("a" * 64,),
                )
                database.execute(
                    "INSERT INTO atlas.construction_records VALUES ('recipe','interpreted_geometry',%s)",
                    (Jsonb(arguments),),
                )
                output = io.StringIO()
                with (
                    patch.object(sys, "argv", ["worldatlas-import", "--recipe", "recipe"]),
                    patch.dict(os.environ, NEON_DATABASE_URL=os.environ["WORLDATLAS_TEST_DATABASE_URL"]),
                    patch("psycopg.connect", return_value=nullcontext(database)),
                    patch("boto3.client") as r2_client,
                    redirect_stdout(output),
                ):
                    main()
                r2_client.assert_not_called()
                result = json.loads(output.getvalue())
                self.assertEqual(result["feature_ids"], ["label"])
                self.assertEqual(result["timing"]["download_seconds"], 0)
                self.assertEqual(database.execute(
                    "SELECT geometry, construction_id FROM atlas.source_features WHERE id='label'"
                ).fetchone(), (geometry, "recipe"))
                self.assertEqual(database.execute(
                    "SELECT source_id FROM atlas.construction_sources WHERE construction_id='recipe'"
                ).fetchall(), [("evidence",)])
