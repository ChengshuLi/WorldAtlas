"""Test signature-derived contracts and their enforcement in PostgreSQL."""

from contextlib import redirect_stderr
from io import StringIO
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, TypedDict
import unittest
from unittest.mock import patch

import psycopg
from psycopg.types.json import Jsonb

from worldatlas.source_imports.shared.contracts import (
    main,
    parameters,
    recipe_schema,
    source_paths,
)
from worldatlas.source_imports.shared.recipe_types import NonEmptyText, SourceId
from worldatlas.source_imports.run_import import IMPORTERS
from worldatlas.source_imports.test_run_import import ARGUMENTS


class ContractTests(unittest.TestCase):
    """Test how the generator reads types and defaults from signatures."""

    def test_source_paths_follow_types_instead_of_names(self):
        class Inputs(TypedDict):
            elevation: SourceId
            rivers: list[SourceId]
            source_id: str

        self.assertEqual(source_paths(Inputs), ['$."elevation"', '$."rivers"[*]'])
        self.assertEqual(source_paths(dict[str, SourceId]), ["$.*"])
        self.assertEqual(source_paths(Any), [])

    def test_source_ids_must_be_object_values(self):
        with self.assertRaisesRegex(TypeError, 'source IDs must be values'):
            source_paths(dict[SourceId, str])

    def test_signature_distinguishes_required_parameters_from_defaults(self):
        def example(runtime, *, title: NonEmptyText, enabled: bool = True):
            return title, enabled

        self.assertEqual(
            parameters(example),
            {"title": (NonEmptyText, True), "enabled": (bool, False)},
        )

    def test_untyped_or_variadic_parameters_are_not_silently_ignored(self):
        def untyped(runtime, *, field):
            pass

        def variadic(runtime, **fields: str):
            pass

        for function in (untyped, variadic):
            with self.assertRaises(TypeError):
                parameters(function)

    def test_signature_requires_leading_runtime(self):
        def example(*, title: str):
            return title

        with self.assertRaisesRegex(TypeError, 'must start with runtime'):
            parameters(example)

    def test_contract_command_generates_and_checks_sql(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'construction_contracts.sql'
            command = [sys.executable, '-m', 'worldatlas.source_imports.shared.contracts', str(path)]
            subprocess.run(command, check=True)
            self.assertIn('CREATE FUNCTION atlas.construction_source_ids', path.read_text())

            # Check both file states without starting Python again for each check.
            with patch.object(sys, 'argv', ['contracts', str(path), '--check']):
                main()
                path.write_text('stale SQL\n')
                stderr = StringIO()
                with redirect_stderr(stderr), self.assertRaises(SystemExit) as failure:
                    main()
                self.assertEqual(failure.exception.code, 1)
                self.assertIn('Construction checks are stale', stderr.getvalue())
                self.assertEqual(path.read_text(), 'stale SQL\n')


@unittest.skipUnless(
    os.environ.get("WORLDATLAS_TEST_DATABASE_URL"), "requires disposable PostgreSQL"
)
class DatabaseContractTests(unittest.TestCase):
    """Exercise argument validation and source links in a disposable database."""

    def setUp(self):
        """Open a connection and add a raw source within a test transaction."""
        self.database = psycopg.connect(os.environ["WORLDATLAS_TEST_DATABASE_URL"])
        self.addCleanup(self.database.close)
        self.addCleanup(self.database.rollback)
        self.database.execute(
            "INSERT INTO atlas.source_assets(id,title,provider,source_uri,license_name,license_uri,attribution,r2_bucket,r2_key,sha256,size_bytes) "
            "VALUES ('raw','Test','Test','test:raw','Test','test:license','Test','test','raw',%s,1)",
            ("a" * 64,),
        )

    def check(self, method, arguments, expected):
        """Check whether the argument constraint accepts a construction.

        Args:
            method: Construction method name to insert.
            arguments: JSON arguments to insert for the method.
            expected: Whether the database should accept the row.
        """
        insert = (
            "INSERT INTO atlas.construction_records(id,method,arguments,basis) "
            "VALUES ('__contract',%s,%s,'Test construction')"
        )
        with self.subTest(method=method, arguments=arguments, expected=expected):
            if expected:
                with self.database.transaction(force_rollback=True):
                    self.database.execute(insert, (method, Jsonb(arguments)))
                return
            with (
                self.assertRaises(psycopg.errors.CheckViolation) as error,
                self.database.transaction(),
            ):
                self.database.execute(insert, (method, Jsonb(arguments)))
            self.assertEqual(error.exception.diag.constraint_name, "construction_arguments_valid")

    def test_requires_a_source_when_inserting_or_editing(self):
        insert = ("INSERT INTO atlas.construction_records(id,method,arguments,basis) VALUES "
                  "('__evidence_required','osm_way_chain',%s,'Join source ways')")
        update = ("UPDATE atlas.construction_records SET arguments=%s "
                  "WHERE id='__evidence_required'")
        arguments = ARGUMENTS["osm_way_chain"]
        source_free = Jsonb(dict(arguments, way_source_ids=[], evidence_source_ids=[]))

        with self.assertRaises(psycopg.errors.CheckViolation) as failure, self.database.transaction():
            self.database.execute(insert, (source_free,))
        self.assertEqual(failure.exception.diag.constraint_name, "construction_requires_source")

        self.database.execute(insert, (Jsonb(arguments),))
        with self.assertRaises(psycopg.errors.CheckViolation) as failure, self.database.transaction():
            self.database.execute(update, (source_free,))
        self.assertEqual(failure.exception.diag.constraint_name, "construction_requires_source")
        self.assertEqual(self.database.execute(
            "SELECT source_id FROM atlas.construction_sources WHERE construction_id='__evidence_required'"
        ).fetchall(), [("raw",)])

    def test_invalid_nested_watershed_settings_are_rejected_in_neon(self):
        base = ARGUMENTS["watershed_boundary"]
        cases = (
            {"lines": {"river": {"source": "raw", "geojson_feature": -1}}},
            {"lines": {"river": {"source": "raw", "ways": 42}}},
            {"start": {"point": [0, 0], "coords": [0, 0]}},
        )
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(psycopg.errors.CheckViolation):
                with self.database.transaction():
                    self.database.execute(
                        "INSERT INTO atlas.construction_records(id,method,arguments,basis) "
                        "VALUES ('__bad_recipe','watershed_boundary',%s,'Invalid test input')",
                        (Jsonb(base | changes),),
                    )

    def test_file_and_evidence_sources_are_linked_once(self):
        for ident in ("other", "evidence"):
            self.database.execute(
                "INSERT INTO atlas.source_assets(id,title,provider,source_uri,license_name,license_uri,attribution,r2_bucket,r2_key,sha256,size_bytes) "
                "VALUES (%s,'Test','Test','test:raw','Test','test:license','Test','test',%s,%s,1)",
                (ident, ident, "a" * 64),
            )
        arguments = dict(
            ARGUMENTS["watershed_boundary"],
            sources={
                "single": "raw",
                "same": "raw",
                "terrain.tif": "other",
            },
            evidence_sources=["evidence", "raw"],
            lines={"boundary": {"source": "single", "way": 1}},
            start={"source": "single", "node": 1},
        )
        self.database.execute(
            "INSERT INTO atlas.construction_records(id,method,arguments,basis) "
            "VALUES ('__links','watershed_boundary',%s,'Test drainage divide')",
            (Jsonb(arguments),),
        )

        def links():
            return [
                row[0]
                for row in self.database.execute(
                    "SELECT source_id FROM atlas.construction_sources WHERE construction_id='__links' ORDER BY source_id"
                )
            ]

        self.assertEqual(links(), ["evidence", "other", "raw"])
        with (
            self.assertRaises(psycopg.errors.ForeignKeyViolation),
            self.database.transaction(),
        ):
            self.database.execute("DELETE FROM atlas.source_assets WHERE id='other'")
        changed = dict(arguments, sources={"only": "raw"}, evidence_sources=[])
        self.database.execute(
            "UPDATE atlas.construction_records SET arguments=%s WHERE id='__links'",
            (Jsonb(changed),),
        )
        self.assertEqual(links(), ["raw"])
        with (
            self.assertRaises(psycopg.errors.ForeignKeyViolation),
            self.database.transaction(),
        ):
            self.database.execute(
                "UPDATE atlas.construction_records SET arguments=%s WHERE id='__links'",
                (Jsonb(dict(changed, sources={"missing": "absent"})),),
            )
        self.assertEqual(links(), ["raw"])
        self.assertEqual(
            self.database.execute(
                "SELECT arguments FROM atlas.construction_records WHERE id='__links'"
            ).fetchone()[0],
            changed,
        )
        self.database.execute(
            "UPDATE atlas.construction_records SET method='osm_way_chain',arguments=%s WHERE id='__links'",
            (Jsonb(dict(ARGUMENTS["osm_way_chain"], way_source_ids=["evidence"])),),
        )
        self.assertEqual(links(), ["evidence"])
        self.database.execute(
            "DELETE FROM atlas.construction_records WHERE id='__links'"
        )
        self.assertEqual(links(), [])

    def test_watershed_source_requires_a_catalog_id(self):
        method = "watershed_boundary"
        split_file = dict(
            parts=["raw"], sha256="a" * 64, size_bytes=1, filename="terrain.tif"
        )
        self.check(method, dict(ARGUMENTS[method], sources={"terrain.tif": split_file}), False)

    def test_every_method_rejects_missing_required_fields_wrong_types_and_unknown_keys(
        self,
    ):
        for method, constructor in IMPORTERS.items():
            arguments = ARGUMENTS[method]
            with self.subTest(method=method):
                self.check(method, arguments, True)
                for name, (_, required) in parameters(constructor).items():
                    if required:
                        self.check(
                            method,
                            {k: v for k, v in arguments.items() if k != name},
                            False,
                        )
                self.check(method, dict(arguments, method=method), False)
                self.check(method, dict(arguments, runtime="unexpected"), False)
                self.check(method, dict(arguments, unexpected="unused"), False)
                self.check(method, dict(arguments, basis="Explanation belongs on the row"), False)
        self.check("unknown", ARGUMENTS["osm_way_chain"], False)

    def test_required_freeform_json_cannot_be_omitted(self):
        schema = recipe_schema("example", {"value": (Any, True)})
        for document, expected in [
            ({}, False),
            ({"value": None}, True),
            ({"value": {"anything": [1, 2]}}, True),
        ]:
            with self.subTest(document=document):
                (actual,) = self.database.execute(
                    "SELECT public.jsonb_matches_schema(%s::json, %s::jsonb)",
                    (Jsonb(schema), Jsonb(document)),
                ).fetchone()
                self.assertIs(actual, expected)

    def test_watershed_lines_and_crops_require_the_new_object_format(self):
        method = 'watershed_boundary'
        line = {'source': 'raw', 'way': 42}
        bounds = [0, 0, 1, 1]
        drainage = dict(basins=['raw'], basin_attribute='ID', groups={'1': [40], '2': [50]})
        terrain = dict(domains=[{'bounds': bounds}], primary=['raw'], drainage='local', interfaces=[[1, 2]])
        arguments = dict(ARGUMENTS[method], lines={'coast': line}, terrains={'divide': terrain},
                         drainage={'local': drainage})
        self.check(method, arguments, True)
        self.check(method, dict(arguments, terrains={'divide': dict(terrain, drainage=' ')}), False)
        self.check(method, dict(arguments, drainage={'local': dict(drainage, basin_attribute=42)}), False)
        self.check(method, dict(arguments, lines={'coast': [line]}), False)
        self.check(method, dict(arguments, lines={'coast': dict(line, geojson_feature=0)}), False)
        river = {'source': 'raw', 'relation': 42, 'role': 'main_stream'}
        self.check(method, dict(arguments, lines={'river': river}, end={'source': 'raw', 'node': 20}), True)
        self.check(method, dict(arguments, lines={'river': dict(river, start_node=10)}), False)
        for domain in (bounds, {'bounds': bounds[:3]}, {'bounds': bounds, 'projection': 4326}):
            with self.subTest(domain=domain):
                self.check(method, dict(arguments, terrains={'divide': dict(terrain, domains=[domain])}), False)

    def test_optional_fields_nested_fields_and_numeric_values(self):
        cases = [
            ("osm_way_chain", dict(start_node_id=1), False),
            ("osm_way_chain", dict(way_source_ids=[1]), False),
            ("osm_way_chain", dict(way_source_ids=[" \t"]), False),
            ("watershed_boundary", dict(sources={" ": "raw"}), False),
            ("watershed_boundary", dict(sources={"\u00a0": "raw"}), False),
            ("watershed_boundary", dict(sources={"valid": None}), False),
            (
                "selected_vector_features",
                dict(member="source.shp", layer="points"),
                True,
            ),
            ("selected_vector_features", dict(member=None), True),
            (
                "selected_vector_features",
                dict(selections=[dict(feature_id="feature", source_feature_id="1", fill_holes=True)]),
                True,
            ),
            (
                "selected_vector_features",
                dict(selections=[dict(feature_id="feature", source_feature_id="1", fill_holes="true")]),
                False,
            ),
            (
                "selected_vector_features",
                dict(selections=[dict(feature_id="feature", source_feature_id="1", holes="outer_envelope")]),
                False,
            ),
            ("selected_vector_features", dict(coordinate_operation="unused"), False),
            (
                "selected_vector_features",
                dict(selections=[dict(feature_id="feature", source_feature_id="1", collection=True)]),
                False,
            ),
            (
                "selected_vector_features",
                dict(selections=[dict(feature_id="feature", source_feature_id="1", expected_feature_count=1)]),
                False,
            ),
            (
                "selected_vector_features",
                dict(selections=[dict(feature_id="feature")]),
                False,
            ),
            (
                "selected_vector_features",
                dict(
                    selections=[
                        dict(feature_id="feature", source_feature_id="1", unused=True)
                    ]
                ),
                False,
            ),
            (
                "selected_osm_features",
                dict(
                    selections=[
                        dict(
                            feature_id="f",
                            source_feature_id=123,
                            object_type="way",
                            expected_tags={"name": "Selected way"},
                        )
                    ]
                ),
                True,
            ),
            (
                "selected_osm_features",
                dict(selections=[dict(ARGUMENTS["selected_osm_features"]["selections"][0], object_version=1)]),
                False,
            ),
            (
                "selected_osm_features",
                dict(selections=[dict(ARGUMENTS["selected_osm_features"]["selections"][0], ignored_member_roles=[])]),
                False,
            ),
            (
                "s130_areas",
                dict(
                    selections=[
                        dict(
                            feature_id="f",
                            source_feature_id="urn:mrn:1",
                            expected_properties={},
                        )
                    ]
                ),
                False,
            ),
            ("s130_areas", dict(gml_sha256="a" * 64), False),
            ("geodesic_trace", dict(points=[[1, True], [0, 0]]), False),
            ("geodesic_trace", dict(points=[[1, 1, 1], [0, 0]]), False),
            ("geodesic_trace", dict(source_feature_id="Figure 1"), False),
            ("geodesic_trace", dict(source_location="Page 2"), False),
        ]
        for method, changes, expected in cases:
            with self.subTest(method=method, changes=changes):
                self.check(
                    method,
                    dict(ARGUMENTS[method], **changes),
                    expected,
                )
