"""Construction contracts apply equally to command calls and direct SQL writes."""

import copy
import inspect
import os
from typing import Any, Literal, NotRequired, TypedDict
import unittest

import psycopg
from psycopg.types.json import Jsonb

from worldatlas.source_imports.contracts import (
    NonEmptyText,
    SourceId,
    Runtime,
    matches,
    parameters,
    source_paths,
    sql_type,
    validate_arguments,
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

    def test_defaults_define_optional_fields_and_python_supplies_the_default(self):
        def example(runtime, *, title: NonEmptyText, enabled: bool = True):
            return title, enabled

        arguments = dict(title="Valid")
        validate_arguments(example, arguments)
        self.assertEqual(example(None, **arguments), ("Valid", True))
        with self.assertRaisesRegex(ValueError, "missing construction field: title"):
            validate_arguments(example, {})
        self.assertEqual(parameters(example)["enabled"], (bool, True))

    def test_runtime_parameters_do_not_leak_into_the_document(self):
        function = IMPORTERS["osm_way_chain"]
        for name in ("method", "runtime", "recipe_id", "recipe_version", "revision", "work_dir"):
            with (
                self.subTest(name=name),
                self.assertRaisesRegex(ValueError, "unknown construction fields"),
            ):
                validate_arguments(
                    function,
                    dict(
                        ARGUMENTS["osm_way_chain"],
                        **{name: "unexpected"},
                    ),
                )
        runtime = Runtime(None, None, "construction", "osm_way_chain")
        self.assertEqual(
            runtime.recipe(dict(runtime=runtime, title="Hello", optional=None)),
            dict(recipe_id="construction", title="Hello"),
        )

    def test_supported_annotations_do_not_coerce_json_values(self):
        class Object(TypedDict):
            title: NonEmptyText
            flag: NotRequired[bool]

        cases = [
            (NonEmptyText, "Hi", True),
            (NonEmptyText, " \t\n", False),
            (NonEmptyText, 3, False),
            (int, 1.0, True),
            (int, True, False),
            (int, 1.5, False),
            (float, 1, True),
            (float, True, False),
            (float, float("inf"), False),
            (bool, 1, False),
            (Literal["node", "way"], "way", True),
            (Literal["node"], "relation", False),
            (str | None, None, True),
            (list[int], [1, 2], True),
            (list[int], [1, "2"], False),
            (tuple[float, float], [1, 2, 3], False),
            (dict[str, bool], {"a": False}, True),
            (dict[str, bool], {"a": 0}, False),
            (Object, {"title": "A"}, True),
            (Object, {"flag": True}, False),
            (Object, {"title": "A", "unused": 1}, False),
            (Any, {"a": [1, None]}, True),
            (Any, {"a": float("nan")}, False),
        ]
        for annotation, value, expected in cases:
            with self.subTest(annotation=annotation, value=value):
                self.assertEqual(matches(value, annotation), expected)

    def test_untyped_or_variadic_parameters_are_not_silently_ignored(self):
        def untyped(runtime, *, field):
            pass

        def variadic(runtime, **fields: str):
            pass

        def invalid_default(runtime, *, enabled: bool = 1):
            pass

        for function in (untyped, variadic, invalid_default):
            with self.assertRaises(TypeError):
                parameters(function)
        with self.assertRaises(TypeError):
            sql_type("value", set[str])


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
        if method in IMPORTERS:
            try:
                validate_arguments(IMPORTERS[method], arguments)
                python_valid = True
            except ValueError:
                python_valid = False
            self.assertEqual(python_valid, expected, (method, arguments))
        (database_valid,) = self.database.execute(
            "SELECT atlas.valid_construction_record(%s,%s)", (method, Jsonb(arguments))
        ).fetchone()
        self.assertIs(database_valid, expected, (method, arguments))
        if expected:
            with self.database.transaction(force_rollback=True):
                self.database.execute(
                    "INSERT INTO atlas.construction_records(id,method,arguments) VALUES ('__contract',%s,%s)",
                    (method, Jsonb(arguments)),
                )
        else:
            with (
                self.assertRaises(psycopg.errors.CheckViolation),
                self.database.transaction(),
            ):
                self.database.execute(
                    "INSERT INTO atlas.construction_records(id,method,arguments) VALUES ('__contract',%s,%s)",
                    (method, Jsonb(arguments)),
                )

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
        validate_arguments(IMPORTERS["watershed_boundary"], arguments)
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
                for name, (annotation, default) in parameters(constructor).items():
                    if default is inspect.Parameter.empty:
                        self.check(
                            method,
                            {k: v for k, v in arguments.items() if k != name},
                            False,
                        )
                        for bad in (False, 123, "wrong type", None, [], {}):
                            if not matches(bad, annotation):
                                self.check(method, dict(arguments, **{name: bad}), False)
                self.check(method, dict(arguments, method=method), False)
                self.check(method, dict(arguments, unexpected="unused"), False)
                self.check(method, dict(arguments, basis=" \t\n"), False)
        self.check("unknown", ARGUMENTS["osm_way_chain"], False)

    def test_required_freeform_json_cannot_be_omitted(self):
        from worldatlas.source_imports.contracts import sql_object

        fields = {"value": (Any, inspect.Parameter.empty)}
        expression = sql_object("input.document", fields)
        for document, expected in [
            ({}, False),
            ({"value": None}, True),
            ({"value": {"anything": [1, 2]}}, True),
        ]:
            with self.subTest(document=document):
                (actual,) = self.database.execute(
                    "SELECT "
                    + expression
                    + " FROM (SELECT %s::jsonb AS document) input",
                    (Jsonb(document),),
                ).fetchone()
                self.assertIs(actual, expected)

    def test_optional_fields_nested_fields_and_numeric_values(self):
        cases = [
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
