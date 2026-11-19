"""Test how the importer dispatches saved construction records."""

from contextlib import nullcontext
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from worldatlas.source_imports.run_import import IMPORTERS, run_import


# The database contract tests also use these valid argument shapes.
ARGUMENTS = {
    "interpreted_geometry": dict(
        source_ids=["raw"],
        basis="Selected context",
        selections=[
            dict(feature_id="context", geometry=dict(type="Point", coordinates=[1, 2]))
        ],
    ),
    "geodesic_trace": dict(
        source_ids=["raw"],
        basis="Chosen points",
        feature_id="line",
        source_feature_id="Figure 1",
        points=[[1, 1], [0, 0]],
        max_step_metres=1000,
    ),
    "osm_way_chain": dict(
        way_source_ids=["raw"],
        start_node_id=1,
        basis="Join ways",
        feature_id="boundary",
    ),
    "watershed_boundary": dict(
        feature_id="boundary",
        basis="Drainage divide",
        sources={},
        lines={},
        sections=[],
        joins=[],
        start={},
        end={},
    ),
    "selected_vector_features": dict(
        source_id="raw",
        basis="Selected features",
        id_field="id",
        selections=[dict(feature_id="feature", source_feature_id="123")],
    ),
    "selected_osm_features": dict(
        source_id="raw",
        basis="Selected OSM features",
        selections=[
            dict(
                feature_id="feature",
                source_feature_id="123",
                object_type="way",
                object_version="1",
            )
        ],
    ),
    "s130_areas": dict(
        source_id="raw",
        basis="Complete areas",
        gml_member="source.gml",
        gml_sha256="a" * 64,
        selections=[dict(feature_id="feature", source_feature_id="urn:mrn:123")],
    ),
}


class ImportSelectionTests(unittest.TestCase):
    """Check argument forwarding and resource requirements for dispatch."""

    def setUp(self):
        """Supply stand-ins for the database connection and R2 cache options."""
        self.connect = lambda: nullcontext(object())
        self.storage = Mock()
        self.options = dict(storage=self.storage, work_dir=Path("/test/cache"))

    def test_every_registered_signature_receives_arguments_and_separate_runtime(
        self,
    ):
        self.assertEqual(set(ARGUMENTS), set(IMPORTERS))
        for method in IMPORTERS.copy():

            def record(runtime, **arguments):
                return runtime, arguments

            with (
                self.subTest(method=method),
                patch.dict(IMPORTERS, {method: record}),
                patch(
                    "worldatlas.source_imports.run_import.read_recipe",
                    return_value=(method, ARGUMENTS[method]),
                ),
            ):
                runtime, arguments = run_import(
                    self.connect, "arbitrary-record-name", **self.options
                )
                self.assertEqual(arguments, ARGUMENTS[method])
                self.assertEqual(runtime.recipe_id, "arbitrary-record-name")
                self.assertEqual(runtime.method, method)
                self.assertEqual(runtime.arguments, ARGUMENTS[method])
                self.assertIs(runtime.storage, self.storage)
                self.assertEqual(runtime.work_dir, self.options["work_dir"])

    def test_trace_needs_no_storage_or_cache(self):
        def trace(runtime, **arguments):
            return runtime

        with (
            patch.dict(IMPORTERS, {"geodesic_trace": trace}),
            patch(
                "worldatlas.source_imports.run_import.read_recipe",
                return_value=("geodesic_trace", ARGUMENTS["geodesic_trace"]),
            ),
        ):
            runtime = run_import(self.connect, "trace")
        self.assertIsNone(runtime.storage)
        self.assertIsNone(runtime.work_dir)

    def test_unsupported_methods_stop_before_downloading(self):
        for method in (None, {}, ["osm_way_chain"], "some.python.function"):
            with (
                self.subTest(method=method),
                patch(
                    "worldatlas.source_imports.run_import.read_recipe",
                    return_value=(method, {}),
                ),
            ):
                with self.assertRaisesRegex(
                    ValueError, "unsupported source construction method"
                ):
                    run_import(self.connect, "record", **self.options)
        self.storage.get_object.assert_not_called()

    def test_missing_recipe_stops_before_downloading(self):
        database = Mock()
        database.execute.return_value.fetchone.return_value = None
        with self.assertRaisesRegex(ValueError, "construction record is missing"):
            run_import(lambda: nullcontext(database), "absent", **self.options)
        self.storage.get_object.assert_not_called()

    def test_missing_required_download_inputs_are_rejected(self):
        with patch(
            "worldatlas.source_imports.run_import.read_recipe",
            return_value=("osm_way_chain", ARGUMENTS["osm_way_chain"]),
        ):
            for name in self.options:
                with (
                    self.subTest(missing=name),
                    self.assertRaisesRegex(ValueError, "requires"),
                ):
                    run_import(
                        self.connect, "record", **dict(self.options, **{name: None})
                    )
        self.storage.get_object.assert_not_called()
