"""Generate construction contracts from signatures and enforce them in PostgreSQL."""

import copy
import os
from typing import Any, TypedDict
import unittest

import psycopg
from psycopg.types.json import Jsonb

from worldatlas.source_imports.contracts import (
    NonEmptyText,
    SourceId,
    parameters,
    recipe_schema,
    source_paths,
)
from worldatlas.source_imports.run_import import IMPORTERS
from worldatlas.source_imports.test_run_import import ARGUMENTS


class ContractTests(unittest.TestCase):
    def test_source_paths_follow_types_instead_of_names(self):
        class Inputs(TypedDict):
            elevation: SourceId
            rivers: list[SourceId]
            source_id: str

        self.assertEqual(source_paths(Inputs), ["$." + '"elevation"', '$."rivers"[*]'])
        self.assertEqual(source_paths(dict[str, SourceId]), ["$.*"])
        self.assertEqual(source_paths(Any), [])

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


@unittest.skipUnless(
    os.environ.get("WORLDATLAS_TEST_DATABASE_URL"), "requires disposable PostgreSQL"
)
class DatabaseContractTests(unittest.TestCase):
    def setUp(self):
        self.database = psycopg.connect(os.environ["WORLDATLAS_TEST_DATABASE_URL"])
        self.addCleanup(self.database.close)
        self.addCleanup(self.database.rollback)
        self.database.execute(
            "INSERT INTO atlas.source_assets(id,title,provider,source_uri,license_name,license_uri,attribution,r2_bucket,r2_key,sha256,size_bytes) "
            "VALUES ('raw','Test','Test','test:raw','Test','test:license','Test','test','raw',%s,1)",
            ("a" * 64,),
        )

    def check(self, method, arguments, expected):
        insert = (
            "INSERT INTO atlas.construction_records(id,method,arguments) "
            "VALUES ('__contract',%s,%s)"
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

    def test_nested_multipart_and_evidence_sources_are_linked_once(self):
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
                "multipart": dict(
                    parts=["raw", "other"],
                    sha256="a" * 64,
                    size_bytes=2,
                    filename="terrain.tif",
                ),
            },
            evidence_sources=["evidence", "raw"],
            geographic_choices={"source_id": "ordinary-untyped-text"},
        )
        self.database.execute(
            "INSERT INTO atlas.construction_records(id,method,arguments) VALUES ('__links','watershed_boundary',%s)",
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
                self.check(method, dict(arguments, basis=False), False)
                self.check(method, dict(arguments, basis=" \t\n"), False)
                self.check(method, dict(arguments, basis="\u0085\u00a0\u3000"), False)
                self.check(method, dict(arguments, basis="\u00a0東京\u3000"), True)
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

    def test_optional_fields_nested_fields_and_numeric_values(self):
        cases = [
            ("osm_way_chain", dict(start_node_id=1.5), False),
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
                            object_version=1.0,
                        )
                    ]
                ),
                True,
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
            ("geodesic_trace", dict(points=[[1, True], [0, 0]]), False),
            ("geodesic_trace", dict(points=[[1, 1, 1], [0, 0]]), False),
        ]
        for method, changes, expected in cases:
            with self.subTest(method=method, changes=changes):
                self.check(
                    method,
                    dict(copy.deepcopy(ARGUMENTS[method]), **changes),
                    expected,
                )
