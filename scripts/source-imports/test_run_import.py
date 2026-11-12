"""The construction method, not the record's name, selects the importer."""
from contextlib import nullcontext
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from run_import import run_import


class ImportSelectionTests(unittest.TestCase):
    def setUp(self):
        self.database = object()
        self.connect = lambda: nullcontext(self.database)
        self.storage = Mock()

    def test_each_method_selects_its_constructor(self):
        cases = [
            ('smooth_latitude_trace', 'traces.build_boundary.build_boundary'),
            ('osm_way_chain', 'osm.build_boundary.build_boundary'),
            ('s130_rhumb_routes', 'iho.build_routes.build_routes'),
            ('watershed_boundary', 'watersheds.build_boundary.build_boundary'),
        ]
        for method, target in cases:
            with self.subTest(method=method), patch('run_import.read_recipe', return_value={'method': method}), \
                    patch(target, return_value={'chosen': method}) as constructor:
                result = run_import(self.connect, 'arbitrary-record-name', '7', storage=self.storage,
                                    revision='editing', work_dir=Path('/test/cache'))
                self.assertEqual(result, {'chosen': method})
                constructor.assert_called_once()
                self.assertIn('arbitrary-record-name', constructor.call_args.args)
                self.assertIn('7', constructor.call_args.args)

    def test_trace_needs_no_storage_revision_or_cache(self):
        with patch('run_import.read_recipe', return_value={'method': 'smooth_latitude_trace'}), \
                patch('traces.build_boundary.build_boundary', return_value={'sha256': 'result'}) as constructor:
            result = run_import(self.connect, 'chosen-trace', '2')
        self.assertEqual(result, {'sha256': 'result'})
        constructor.assert_called_once_with(self.database, 'chosen-trace', '2', None)

    def test_changing_method_changes_constructor_for_the_same_record(self):
        with patch('run_import.read_recipe', side_effect=[
                {'method': 'smooth_latitude_trace'}, {'method': 'osm_way_chain'}]), \
                patch('traces.build_boundary.build_boundary') as trace, \
                patch('osm.build_boundary.build_boundary') as osm:
            options = dict(storage=self.storage, revision='editing', work_dir=Path('/test/cache'))
            run_import(self.connect, 'same-record', '1', **options)
            run_import(self.connect, 'same-record', '2', **options)
        trace.assert_called_once()
        osm.assert_called_once()

    def test_unsupported_methods_stop_before_importing_or_downloading(self):
        for method in (None, {}, ['osm_way_chain'], 'some.python.function'):
            with self.subTest(method=method), patch('run_import.read_recipe', return_value={'method': method}):
                with self.assertRaisesRegex(ValueError, 'unsupported source construction method'):
                    run_import(self.connect, 'record', '1', storage=self.storage)
        self.storage.get_object.assert_not_called()

    def test_required_download_inputs_are_checked_before_constructor_runs(self):
        options = dict(storage=self.storage, revision='editing', work_dir=Path('/test/cache'))
        with patch('run_import.read_recipe', return_value={'method': 'osm_way_chain'}), \
                patch('osm.build_boundary.build_boundary') as constructor:
            for name in options:
                with self.subTest(missing=name):
                    with self.assertRaisesRegex(ValueError, 'requires'):
                        run_import(self.connect, 'record', '1', **dict(options, **{name: None}))
        constructor.assert_not_called()

    def test_expected_checksum_reaches_trace_and_osm_constructors(self):
        for method, target in [('smooth_latitude_trace', 'traces.build_boundary.build_boundary'),
                               ('osm_way_chain', 'osm.build_boundary.build_boundary')]:
            with self.subTest(method=method), patch('run_import.read_recipe', return_value={'method': method}), \
                    patch(target) as constructor:
                run_import(self.connect, 'record', '1', storage=self.storage, revision='editing',
                           work_dir=Path('/test/cache'), expected_geometry_sha256='expected')
                self.assertEqual(constructor.call_args.args[-1], 'expected')

    def test_inapplicable_checksum_is_rejected_before_constructor_runs(self):
        with patch('run_import.read_recipe', return_value={'method': 's130_rhumb_routes'}), \
                patch('iho.build_routes.build_routes') as constructor:
            with self.assertRaisesRegex(ValueError, 'checksum applies'):
                run_import(self.connect, 'record', '1', storage=self.storage, revision='editing',
                           work_dir=Path('/test/cache'), expected_geometry_sha256='expected')
        constructor.assert_not_called()


if __name__ == '__main__':
    unittest.main()
