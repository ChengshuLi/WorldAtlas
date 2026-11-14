"""Document contracts apply equally to command calls and direct SQL writes."""

import copy
import inspect
import os
from typing import Any, Literal, NotRequired, TypedDict
import unittest

import psycopg
from psycopg.types.json import Jsonb

from worldatlas.source_imports.contracts import (
    NonEmptyText,
    Runtime,
    bind_document,
    matches,
    parameters,
    sql_type,
)
from worldatlas.source_imports.run_import import IMPORTERS
from worldatlas.source_imports.test_run_import import DOCUMENTS


class ContractTests(unittest.TestCase):
    def test_defaults_define_optional_fields_and_python_supplies_the_default(self):
        def example(runtime, *, title: NonEmptyText, enabled: bool = True):
            return title, enabled

        arguments = bind_document(example, dict(method="example", title="Valid"))
        self.assertEqual(example(None, **arguments), ("Valid", True))
        with self.assertRaisesRegex(ValueError, "missing construction field: title"):
            bind_document(example, dict(method="example"))
        self.assertEqual(parameters(example)["enabled"], (bool, True))

    def test_runtime_parameters_do_not_leak_into_the_document(self):
        function = IMPORTERS["osm_way_chain"]
        for name in ("runtime", "recipe_id", "recipe_version", "revision", "work_dir"):
            with (
                self.subTest(name=name),
                self.assertRaisesRegex(ValueError, "unknown construction fields"),
            ):
                bind_document(
                    function,
                    dict(
                        DOCUMENTS["osm_way_chain"],
                        method="osm_way_chain",
                        **{name: "unexpected"},
                    ),
                )
        runtime = Runtime(None, None, "construction", "osm_way_chain")
        self.assertEqual(
            runtime.recipe(dict(runtime=runtime, title="Hello", optional=None)),
            dict(method="osm_way_chain", recipe_id="construction", title="Hello"),
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

    def check(self, method, document, expected):
        try:
            bind_document(IMPORTERS[method], document)
            python_valid = True
        except ValueError:
            python_valid = False
        self.assertEqual(python_valid, expected, (method, document))
        (database_valid,) = self.database.execute(
            "SELECT atlas.valid_construction_record(%s)", (Jsonb(document),)
        ).fetchone()
        self.assertIs(database_valid, expected, (method, document))
        if expected:
            with self.database.transaction(force_rollback=True):
                self.database.execute(
                    "INSERT INTO atlas.construction_records VALUES ('__contract',%s)",
                    (Jsonb(document),),
                )
        else:
            with (
                self.assertRaises(psycopg.errors.CheckViolation),
                self.database.transaction(),
            ):
                self.database.execute(
                    "INSERT INTO atlas.construction_records VALUES ('__contract',%s)",
                    (Jsonb(document),),
                )

    def test_every_method_rejects_missing_required_fields_wrong_types_and_unknown_keys(
        self,
    ):
        for method, constructor in IMPORTERS.items():
            document = dict(DOCUMENTS[method], method=method)
            with self.subTest(method=method):
                self.check(method, document, True)
                for name, (annotation, default) in parameters(constructor).items():
                    if default is inspect.Parameter.empty:
                        self.check(
                            method,
                            {k: v for k, v in document.items() if k != name},
                            False,
                        )
                        for bad in (False, 123, "wrong type", None, [], {}):
                            if not matches(bad, annotation):
                                self.check(method, dict(document, **{name: bad}), False)
                self.check(method, dict(document, method="unknown"), False)
                self.check(method, dict(document, unexpected="unused"), False)
                self.check(method, dict(document, basis=" \t\n"), False)

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
                "selected_table_points",
                dict(
                    bounds_lon_lat=[0, 0, 1, 1],
                    where={"kind": "island"},
                    feature_id_prefix="island-",
                ),
                True,
            ),
            ("selected_table_points", dict(bounds_lon_lat=[0, 0, 1]), False),
            ("selected_table_points", dict(where={"kind": 1}), False),
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
            (
                "s130_rhumb_routes",
                dict(
                    routes=[
                        dict(
                            route_id="r",
                            construction_line_id="c",
                            reverse=1,
                            endpoint_names=["A", "B"],
                        )
                    ]
                ),
                False,
            ),
            ("smooth_latitude_trace", dict(points=[[1, True], [0, 0]]), False),
            ("smooth_latitude_trace", dict(points=[[1, 1, 1], [0, 0]]), False),
        ]
        for method, changes, expected in cases:
            with self.subTest(method=method, changes=changes):
                self.check(
                    method,
                    dict(copy.deepcopy(DOCUMENTS[method]), method=method, **changes),
                    expected,
                )
