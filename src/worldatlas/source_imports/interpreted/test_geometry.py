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

from worldatlas.source_imports.run_import import main, run_import


@unittest.skipUnless(
    os.environ.get("WORLDATLAS_TEST_DATABASE_URL"), "requires disposable PostgreSQL"
)
class InterpretedGeometryTests(unittest.TestCase):
    """Exercise the interpreted construction through its registry entry."""

    def setUp(self):
        self.database_url = os.environ["WORLDATLAS_TEST_DATABASE_URL"]
        self.database = psycopg.connect(self.database_url)
        self.addCleanup(self.database.close)
        self.addCleanup(self.database.rollback)
        self.point = dict(type="Point", coordinates=[10, 20])
        self.polygon = dict(
            type="Polygon",
            coordinates=[[[9, 18], [11, 18], [11, 21], [9, 21], [9, 18]]],
        )
        self.arguments = dict(
            source_ids=["evidence"],
            selections=[
                dict(feature_id="label", geometry=self.point),
                dict(feature_id="area", geometry=self.polygon),
            ],
        )
        self.database.execute(
            "INSERT INTO atlas.source_assets "
            "(id,title,provider,source_uri,license_name,license_uri,attribution,"
            "r2_bucket,r2_key,sha256,size_bytes) "
            "VALUES ('evidence','Test','Test','test:evidence','Test','test:license','Test',"
            "'test','figure.pdf',%s,1)",
            ("a" * 64,),
        )
        self.store_arguments(self.arguments)

    def store_arguments(self, arguments):
        """Save the arguments for the test recipe.

        Args:
            arguments: JSON-compatible constructor arguments.
        """
        self.database.execute(
            "INSERT INTO atlas.construction_records(id,method,arguments,basis) "
            "VALUES ('recipe','interpreted_geometry',%s,'Reviewed point and area') "
            "ON CONFLICT (id) DO UPDATE SET arguments=EXCLUDED.arguments",
            (Jsonb(arguments),),
        )

    def saved_features(self):
        """Return saved feature IDs, geometry, and construction IDs in ID order."""
        return self.database.execute(
            "SELECT id, geometry, construction_id FROM atlas.source_features "
            "WHERE construction_id='recipe' ORDER BY id"
        ).fetchall()

    def test_saves_point_and_polygon_and_links_evidence_without_r2(self):
        output = io.StringIO()
        with (
            patch.object(sys, "argv", ["worldatlas-import", "--recipe", "recipe"]),
            patch.dict(os.environ, NEON_DATABASE_URL=self.database_url),
            patch("psycopg.connect", return_value=nullcontext(self.database)),
            patch("boto3.client") as r2_client,
            redirect_stdout(output),
        ):
            main()

        r2_client.assert_not_called()
        result = json.loads(output.getvalue())
        self.assertEqual(result["feature_ids"], ["label", "area"])
        self.assertEqual(result["timing"]["download_seconds"], 0)
        self.assertEqual(
            self.saved_features(),
            [("area", self.polygon, "recipe"), ("label", self.point, "recipe")],
        )
        self.assertEqual(
            self.database.execute(
                "SELECT source_id FROM atlas.construction_sources WHERE construction_id='recipe'"
            ).fetchall(),
            [("evidence",)],
        )

    def test_invalid_arguments_preserve_saved_features(self):
        def connect():
            return nullcontext(self.database)

        run_import(connect, "recipe")
        before = self.saved_features()
        cases = (
            (dict(source_ids=["evidence", "evidence"]), "distinct source IDs"),
            (dict(selections=[]), "at least one selection"),
        )
        for changes, message in cases:
            with self.subTest(changes=changes):
                self.store_arguments(dict(self.arguments, **changes))
                with self.assertRaisesRegex(ValueError, message):
                    run_import(connect, "recipe")
                self.assertEqual(self.saved_features(), before)

    def test_recipe_rejects_invalid_geojson(self):
        geometries = (
            dict(type="Point", coordinates=[181, 20]),
            dict(type="Point", coordinates=[10, 91]),
            dict(type="Polygon", coordinates=[]),
            dict(type="Polygon", coordinates=[[[9, 18], [11, 18], [9, 18]]]),
            dict(type="LineString", coordinates=[[9, 18], [11, 18]]),
        )
        for geometry in geometries:
            with (
                self.subTest(geometry=geometry),
                self.assertRaises(psycopg.errors.CheckViolation) as rejected,
                self.database.transaction(),
            ):
                selection = dict(feature_id="invalid", geometry=geometry)
                self.store_arguments(dict(self.arguments, selections=[selection]))
            self.assertEqual(
                rejected.exception.diag.constraint_name, "construction_arguments_valid"
            )
