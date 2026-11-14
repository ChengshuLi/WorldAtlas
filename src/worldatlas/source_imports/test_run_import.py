"""Dispatch and validate stored constructions before calling an algorithm."""
from contextlib import nullcontext
from functools import wraps
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from worldatlas.source_imports.run_import import IMPORTERS, run_import


DOCUMENTS = {
    'smooth_latitude_trace': dict(source_id='raw', basis='Chosen points',
        feature_id='line', source_feature_id='Figure 1', points=[[1, 1], [0, 0]], step_latitude_degrees=.01, smoothing_latitude_degrees=.1),
    'osm_way_chain': dict(source_id='raw', basis='Join ways', boundary_id='boundary'),
    's130_rhumb_routes': dict(source_id='raw', basis='Selected routes',
        gml_member='source.gml', gml_sha256='a'*64, max_step_km=.05,
        routes=[dict(route_id='route', construction_line_id='line', reverse=False, endpoint_names=['A', 'B'])]),
    'watershed_boundary': dict(boundary_id='boundary', basis='Drainage divide', sources={}, lines={},
        sections=[], joins=[], start={}, end={}),
    'selected_vector_features': dict(source_id='raw', basis='Selected features',
        id_field='id', selections=[dict(feature_id='feature', source_feature_id='123')]),
    'selected_table_points': dict(source_id='raw', basis='Selected points',
        id_field='id', longitude_field='lon', latitude_field='lat',
        selections=[dict(feature_id='feature', source_feature_id='123')]),
    'selected_osm_features': dict(source_id='raw', basis='Selected OSM features',
        selections=[dict(feature_id='feature', source_feature_id='123', object_type='way', object_version='1')]),
    's130_areas': dict(source_id='raw', basis='Complete areas',
        gml_member='source.gml', gml_sha256='a'*64,
        selections=[dict(feature_id='feature', source_feature_id='urn:mrn:123')]),
}


class ImportSelectionTests(unittest.TestCase):
    def setUp(self):
        self.connect = lambda: nullcontext(object())
        self.storage = Mock()
        self.options = dict(storage=self.storage, work_dir=Path('/test/cache'))

    def test_every_registered_signature_receives_document_arguments_and_separate_runtime(self):
        self.assertEqual(set(DOCUMENTS), set(IMPORTERS))
        for method, constructor in IMPORTERS.copy().items():
            @wraps(constructor)
            def record(runtime, **arguments):
                return runtime, arguments
            document = dict(DOCUMENTS[method], method=method)
            with self.subTest(method=method), patch.dict(IMPORTERS, {method: record}), \
                    patch('worldatlas.source_imports.run_import.read_recipe', return_value=document):
                runtime, arguments = run_import(self.connect, 'arbitrary-record-name', **self.options)
                self.assertEqual(arguments, DOCUMENTS[method])
                self.assertEqual(runtime.recipe_id, 'arbitrary-record-name')
                self.assertIs(runtime.storage, self.storage)

    def test_trace_needs_no_storage_revision_or_cache(self):
        constructor = IMPORTERS['smooth_latitude_trace']
        @wraps(constructor)
        def trace(runtime, **arguments):
            return runtime
        with patch.dict(IMPORTERS, {'smooth_latitude_trace': trace}), \
                patch('worldatlas.source_imports.run_import.read_recipe',
                      return_value=dict(DOCUMENTS['smooth_latitude_trace'], method='smooth_latitude_trace')):
            runtime = run_import(self.connect, 'trace')
        self.assertIsNone(runtime.storage)
        self.assertIsNone(runtime.expected_geometry_sha256)

    def test_unsupported_methods_stop_before_downloading(self):
        for method in (None, {}, ['osm_way_chain'], 'some.python.function'):
            with self.subTest(method=method), patch('worldatlas.source_imports.run_import.read_recipe', return_value={'method': method}):
                with self.assertRaisesRegex(ValueError, 'unsupported source construction method'):
                    run_import(self.connect, 'record', **self.options)
        self.storage.get_object.assert_not_called()

    def test_invalid_fields_stop_before_constructor_or_download(self):
        for changes in ({'basis': ''}, {'boundary_id': None}, {'extra': 'unused'}, {'source_id': 1}):
            with self.subTest(changes=changes), patch('worldatlas.source_imports.run_import.read_recipe',
                    return_value=dict(DOCUMENTS['osm_way_chain'], method='osm_way_chain', **changes)):
                with self.assertRaisesRegex(ValueError, 'construction field'):
                    run_import(self.connect, 'record', **self.options)
        self.storage.get_object.assert_not_called()

    def test_required_download_inputs_and_inapplicable_checksum_are_rejected(self):
        with patch('worldatlas.source_imports.run_import.read_recipe', return_value=dict(DOCUMENTS['osm_way_chain'], method='osm_way_chain')):
            for name in self.options:
                with self.subTest(missing=name), self.assertRaisesRegex(ValueError, 'requires'):
                    run_import(self.connect, 'record', **dict(self.options, **{name: None}))
        with patch('worldatlas.source_imports.run_import.read_recipe', return_value=dict(DOCUMENTS['s130_areas'], method='s130_areas')):
            with self.assertRaisesRegex(ValueError, 'checksum applies'):
                run_import(self.connect, 'record', **self.options, expected_geometry_sha256='expected')
        self.storage.get_object.assert_not_called()
