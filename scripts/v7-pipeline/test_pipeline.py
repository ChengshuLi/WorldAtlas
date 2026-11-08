"""Runner contracts, measured parallelism, and actual raw-to-component chaining."""
import json
import hashlib
import io
import os
from pathlib import Path
import struct
import subprocess
import sys
import zipfile
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import run_pipeline as pipeline


class TimingTests(unittest.TestCase):
    def test_selected_configuration_has_portable_pins_and_complete_new_coastal_partition(self):
        path = Path(pipeline.__file__).with_name('config.json')
        cfg = pipeline.read(path)
        self.assertNotIn('/workspace/', path.read_text())
        self.assertNotIn('/tmp/', path.read_text())
        self.assertNotIn('input_root', cfg)
        self.assertEqual(cfg['sources']['raw_manifest']['json']['file_count'], 32)
        prepare = pipeline.stage_module(pipeline.SCRIPTS / pipeline.REGIONAL / 'prepare_fresh_handoff.py')
        codes = cfg['sources']['regional_template']['json']['regional']['request']['code']
        self.assertEqual(set(prepare.bind_regional_code(codes)), set(codes))
        batch = pipeline.stage_module(pipeline.SCRIPTS / pipeline.REPLAY / 'batch_coastal_tiles.py')
        entries = batch.validate_plan(cfg['sources']['coastal_plan']['json'], 131072, 54614)
        self.assertEqual(sum((e['core'][1]-e['core'][0])*(e['core'][3]-e['core'][2]) for e in entries), 131072*54614)

    def test_interval_union_excludes_idle_gaps_and_parallel_double_count(self):
        self.assertEqual(pipeline.elapsed_union([(1, 5), (2, 4), (8, 9), (4, 7)]), 7)
        self.assertEqual(pipeline.elapsed_union([]), 0)
        with self.assertRaises(ValueError):
            pipeline.elapsed_union([(2, 1)])

    def test_completed_intervals_survive_and_failures_remain_incomplete(self):
        with tempfile.TemporaryDirectory() as td:
            timer = pipeline.Timing(Path(td) / 'events.jsonl')
            with patch.object(pipeline.time, 'monotonic', side_effect=[10, 13, 20, 21, 40, 40, 65, 65]):
                with timer.measure('water', 'basin'):
                    pass
                with self.assertRaises(RuntimeError):
                    with timer.measure('water', 'coast'):
                        raise RuntimeError('interrupted')
                with timer.measure('physical', 'stage-total'):
                    with timer.measure('physical', 'physical', kind='command'):
                        pass
            timer.completed_groups.add('physical')
            doc = timer.summary({'status': 'candidate-only', 'processing_elapsed_seconds': 5,
                                 'source_download_elapsed_seconds': 20})
            self.assertEqual(doc['water']['processing_elapsed_seconds'], 4)
            self.assertFalse(doc['water']['complete'])
            self.assertEqual(doc['physical']['processing_elapsed_seconds'], 5)
            self.assertEqual(doc['physical']['source_download_elapsed_seconds'], 20)
            records = [json.loads(line) for line in timer.path.read_text().splitlines()]
            self.assertEqual([r['event'] for r in records if r['event'] != 'attempt'], ['start', 'complete', 'start', 'failed', 'start', 'start', 'complete', 'complete'])

    def test_invalid_acquisition_timing_cannot_be_a_complete_stage(self):
        with tempfile.TemporaryDirectory() as td:
            timer = pipeline.Timing(Path(td) / 'events.jsonl')
            with patch.object(pipeline.time, 'monotonic', side_effect=[1, 3]):
                with timer.measure('physical', 'stage-total'):
                    pass
            timer.completed_groups.add('physical')
            summary = timer.summary({'status': 'candidate-only',
                                     'source_download_elapsed_seconds': 4})['physical']
            self.assertFalse(summary['complete'])
            self.assertIsNone(summary['processing_elapsed_seconds'])
            self.assertIsNotNone(summary['timing_error'])

    def test_parallel_jobs_are_measured_as_union_not_sum(self):
        with tempfile.TemporaryDirectory() as td:
            timer = pipeline.Timing(Path(td) / 'events.jsonl')
            entered = threading.Barrier(3)
            def job(name):
                with timer.measure('water', name):
                    entered.wait()
                    time.sleep(.06)
            threads = [threading.Thread(target=job, args=(name,)) for name in ('sea', 'coast')]
            for thread in threads:
                thread.start()
            entered.wait()
            for thread in threads:
                thread.join()
            timer.completed_groups.add('water')
            summary = timer.summary(None)['water']
            self.assertTrue(summary['complete'])
            completed = [r for r in timer.records if r['event'] == 'complete']
            summed = sum(r['monotonic_seconds'] - r['start_monotonic_seconds'] for r in completed)
            self.assertLess(summary['processing_elapsed_seconds'], summed * .8)


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs = self.root / 'inputs'
        self.inputs.mkdir()
        self.sentinel = pipeline.write(self.inputs / 'sentinel.json', {})
        required = ('land_config water_config raw_manifest land_snapshot resolution_template '
                    'regional_template water_snapshot seavox_archive coastal_plan neon_selection osm_receipt').split()
        self.cfg = {'schema': 'worldatlas-end-to-end-pipeline-v1',
                    'selection_notes': 'Synthetic processor integration fixture',
                    'input_root': str(self.root),
                    'sources': {key: pipeline.pin(self.sentinel) for key in required},
                    'land_controls': {'minimum_free_bytes': 2 << 30}}

    def make(self):
        config = pipeline.write(self.inputs / 'request.json', self.cfg)
        runner = pipeline.Pipeline(config, self.root / 'run')
        self.addCleanup(runner.close)
        return runner

    def test_invalid_source_fails_before_any_processing(self):
        self.cfg['sources']['land_config']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'source pin mismatch'):
            self.make()
        self.assertFalse((self.root / 'run').exists())

    def cloud(self, payload, key='sources/input.json'):
        return {'r2_bucket': 'worldatlas', 'r2_key': key,
                'sha256': hashlib.sha256(payload).hexdigest(), 'size_bytes': len(payload)}

    def fake_r2(self, payloads, calls):
        module = pipeline.stage_module(pipeline.SCRIPTS / 'v7-raw-mask/build_physical.py')
        def download(endpoint, entry, destination):
            calls.append(entry['r2_key'])
            destination.write_bytes(payloads[entry['r2_key']])
        return patch.object(module, 'download_r2', side_effect=download)

    def test_one_configuration_fetches_pinned_r2_inputs_into_selected_work_directory(self):
        payload = b'{}'
        self.cfg['sources'] = {key: self.cloud(payload) for key in self.cfg['sources']}
        self.cfg['input_root'] = '/not-this-computer'
        config = pipeline.write(self.inputs / 'cloud-config.json', self.cfg)
        calls, results = [], []
        with self.fake_r2({'sources/input.json': payload}, calls):
            for name in ('computer-one', 'computer-two'):
                root = self.root / name
                runner = pipeline.Pipeline(config, work_dir=root)
                try:
                    self.assertEqual(runner.out, root / 'run')
                    self.assertEqual(len(runner.source_pins), 1)
                    source = runner.sources['land_snapshot']
                    self.assertTrue(source.is_relative_to(root))
                    self.assertEqual(source.read_bytes(), payload)
                    self.assertEqual(len(runner.acquisition_intervals), 1)
                    results.append(pipeline.sha(source))
                finally:
                    runner.close()
        self.assertEqual(calls, ['sources/input.json', 'sources/input.json'])
        self.assertEqual(results[0], results[1])

    def test_inline_stage_documents_share_verified_cloud_sources_and_nested_pins(self):
        payload = b'raw source bytes'
        source = self.cloud(payload, 'sources/land.geojson')
        self.cfg['sources']['land_config'] = {'json': {'land': [
            {'dataset': source, 'files': [source]}]}}
        self.cfg['sources']['regional_template'] = {'json': {
            'point_request': {'json': {'source_files': [dict(source, source_id='raw', version='v1')]}},
            'evidence_source_files': [source], 'regional': {'request': {'sources': {'raw': dict(source, version='v1')}}}}}
        calls = []
        with self.fake_r2({'sources/land.geojson': payload}, calls):
            runner = self.make()
        land = pipeline.read(runner.sources['land_config'])['land'][0]
        self.assertEqual(land['dataset'], land['files'][0]['path'])
        template = pipeline.read(runner.sources['regional_template'])
        point = pipeline.read(template['point_request']['path'])
        self.assertEqual(point['source_files'][0]['source_id'], 'raw')
        self.assertEqual(point['source_files'][0]['path'], land['dataset'])
        self.assertEqual(template['regional']['request']['sources']['raw']['version'], 'v1')
        self.assertEqual(calls, ['sources/land.geojson'])

    def test_inline_neon_record_metadata_is_not_mistaken_for_a_file_reference(self):
        metadata = self.cloud(b'not a requested file')
        self.cfg['sources']['coastal_plan'] = {'json': {'source_asset': metadata}}
        with self.fake_r2({}, []) as download:
            runner = self.make()
        download.assert_not_called()
        self.assertEqual(pipeline.read(runner.sources['coastal_plan'])['source_asset'], metadata)

    def test_neon_reader_is_read_only_and_requires_exact_reconstructed_bytes(self):
        value = {'name': 'Sørkapp', 'number': 1.0}
        payload = pipeline.source_json_bytes(value, 'canonical-utf8')
        expected = hashlib.sha256(payload).hexdigest()
        statements = []
        class Database:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def execute(self, query, parameters=None):
                statements.append((query, parameters)); return self
            def fetchone(self): return (expected, len(payload), json.dumps(value, ensure_ascii=False))
        fake = SimpleNamespace(connect=lambda connection: Database())
        runner = pipeline.Pipeline.__new__(pipeline.Pipeline)
        with patch.dict(sys.modules, {'psycopg': fake}), patch.dict(os.environ, {'NEON_DATABASE_URL': 'fixture-only'}):
            self.assertEqual(runner.neon_source({'source_id': 'selected', 'version': 'v1'}, expected, len(payload)), payload)
            value['number'] = 2.0
            with self.assertRaisesRegex(ValueError, 'cannot reconstruct'):
                runner.neon_source({'source_id': 'selected', 'version': 'v1'}, expected, len(payload))
        self.assertEqual(statements[0][0], 'SET TRANSACTION READ ONLY')
        self.assertEqual(statements[1][1], ('selected', 'v1'))

        self.assertIn("COALESCE(provenance->'snapshot',provenance->'document')::text", statements[1][0])

    def test_spaced_neon_json_reconstructs_original_without_changing_compact_serialization(self):
        value = {'name': 'Sørkapp', 'number': 1.0}
        payload = (json.dumps(value, sort_keys=True, ensure_ascii=True) + '\n').encode()
        self.assertEqual(pipeline.source_json_bytes(value, 'spaced-ascii'), payload)
        self.assertNotEqual(pipeline.source_json_bytes(value, 'canonical-ascii'), payload)
        self.assertEqual(pipeline.source_json_bytes(value, 'spaced-utf8'),
                         (json.dumps(value, sort_keys=True, ensure_ascii=False) + '\n').encode())
        expected = hashlib.sha256(payload).hexdigest()
        class Database:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def execute(self, *args): return self
            def fetchone(self): return (expected, len(payload), json.dumps(value))
        fake = SimpleNamespace(connect=lambda connection: Database())
        runner = pipeline.Pipeline.__new__(pipeline.Pipeline)
        with patch.dict(sys.modules, {'psycopg': fake}), patch.dict(os.environ, {'NEON_DATABASE_URL': 'fixture-only'}):
            self.assertEqual(runner.neon_source({'source_id': 'selected', 'version': 'v1',
                'serialization': 'spaced-ascii'}, expected, len(payload)), payload)

    def test_neon_jsonb_text_fetches_exact_bytes_from_empty_roots_and_reuses_verified_cache(self):
        # PostgreSQL text preserves decimal spelling, Unicode and key order.
        # This selected representation has no trailing newline.
        payload = '{"b": 1.2300, "a": "Sørkapp"}'.encode()
        expected = hashlib.sha256(payload).hexdigest()
        source = {'neon': {'source_id': 'selected', 'version': 'v1', 'serialization': 'jsonb-text'},
                  'sha256': expected, 'size_bytes': len(payload)}
        self.cfg['sources'] = {key: source for key in self.cfg['sources']}
        config = pipeline.write(self.inputs / 'neon-config.json', self.cfg)
        statements = []
        class Database:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def execute(self, query, parameters=None):
                statements.append((query, parameters)); return self
            def fetchone(self): return (expected, len(payload), payload.decode())
        fake = SimpleNamespace(connect=lambda connection: Database())
        with patch.dict(sys.modules, {'psycopg': fake}), patch.dict(os.environ, {'NEON_DATABASE_URL': 'fixture-only'}):
            for name in ('computer-one', 'computer-two'):
                root = self.root / name
                self.assertFalse(root.exists())
                runner = pipeline.Pipeline(config, work_dir=root)
                try:
                    self.assertEqual(runner.sources['land_snapshot'].read_bytes(), payload)
                    self.assertEqual(len(runner.acquisition_intervals), 1)
                finally:
                    runner.close()
                with patch.object(fake, 'connect', side_effect=AssertionError('cache must not reconnect')):
                    runner = pipeline.Pipeline(config, root / 'second-run', work_dir=root)
                    try:
                        self.assertEqual(runner.sources['land_snapshot'].read_bytes(), payload)
                        self.assertEqual(runner.acquisition_intervals, [])
                    finally:
                        runner.close()
        self.assertEqual([query for query, _ in statements[::2]], ['SET TRANSACTION READ ONLY'] * 2)
        self.assertEqual([parameters for _, parameters in statements[1::2]], [('selected', 'v1')] * 2)

    def test_neon_jsonb_text_changed_document_or_catalog_pin_fails_closed(self):
        payload = b'{"value": 1.00}'
        expected = hashlib.sha256(payload).hexdigest()
        row = [expected, len(payload), '{"value": 2.00}']
        class Database:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def execute(self, *args): return self
            def fetchone(self): return row
        fake = SimpleNamespace(connect=lambda connection: Database())
        runner = pipeline.Pipeline.__new__(pipeline.Pipeline)
        source = {'source_id': 'selected', 'version': 'v1', 'serialization': 'jsonb-text'}
        with patch.dict(sys.modules, {'psycopg': fake}), patch.dict(os.environ, {'NEON_DATABASE_URL': 'fixture-only'}):
            with self.assertRaisesRegex(ValueError, 'cannot reconstruct'):
                runner.neon_source(source, expected, len(payload))
            row[:] = ['0' * 64, len(payload), payload.decode()]
            with self.assertRaisesRegex(ValueError, 'catalog identity/SHA-256/size mismatch'):
                runner.neon_source(source, expected, len(payload))
            row[:] = [expected, len(payload) + 1, payload.decode()]
            with self.assertRaisesRegex(ValueError, 'catalog identity/SHA-256/size mismatch'):
                runner.neon_source(source, expected, len(payload))

    def test_cloud_zip_members_are_individually_pinned_and_keep_sidecars_together(self):
        buffer = io.BytesIO()
        members = {'land/land.shp': b'geometry', 'land/land.dbf': b'attributes'}
        with zipfile.ZipFile(buffer, 'w') as packed:
            for name, value in members.items():
                packed.writestr(name, value)
        archive = self.cloud(buffer.getvalue(), 'sources/land.zip')
        files = [{'archive': archive, 'member': name, 'sha256': hashlib.sha256(value).hexdigest(),
                  'size_bytes': len(value)} for name, value in members.items()]
        self.cfg['sources']['land_config'] = {'json': {
            'land': [{'dataset': files[0], 'files': files}]}}
        calls = []
        with self.fake_r2({'sources/land.zip': buffer.getvalue()}, calls):
            runner = self.make()
        land = pipeline.read(runner.sources['land_config'])['land'][0]
        self.assertEqual(calls, ['sources/land.zip'])
        self.assertEqual(Path(land['files'][0]['path']).parent, Path(land['files'][1]['path']).parent)
        self.assertEqual(len({item['path'] for item in runner.source_pins}), 5)

    def test_raw_manifest_keeps_shards_deferred_to_existing_physical_stage(self):
        raw = {'file_count': 1, 'files': [{'path': 'raw/part.parquet', 'sha256': 'a' * 64,
               'r2_bucket': 'worldatlas', 'r2_key': 'raw/part.parquet', 'size': 123}]}
        self.cfg['sources']['raw_manifest'] = {'json': raw}
        with self.fake_r2({}, []) as download:
            runner = self.make()
        download.assert_not_called()
        self.assertEqual(pipeline.read(runner.sources['raw_manifest']), raw)

    def test_changed_cloud_cache_or_wrong_download_fails_before_run_creation(self):
        payload = b'{}'
        self.cfg['sources']['land_snapshot'] = self.cloud(payload)
        calls = []
        with self.fake_r2({'sources/input.json': b'wrong'}, calls):
            with self.assertRaisesRegex(ValueError, 'cloud input size/SHA-256 mismatch'):
                self.make()
        self.assertFalse((self.root / 'run').exists())
        self.assertEqual(len(list((self.root / 'inputs').rglob('*.partial'))), 1)

    def test_relative_input_root_is_relative_to_the_configuration(self):
        self.cfg['input_root'] = '..'
        runner = self.make()
        self.assertEqual(runner.root, self.root)

    def test_cached_cloud_corruption_and_zip_path_escapes_fail_closed(self):
        payload = b'{}'
        spec = self.cloud(payload)
        cached = self.root / 'inputs' / spec['sha256'] / 'input.json'
        cached.parent.mkdir(parents=True)
        cached.write_bytes(b'xx')
        self.cfg['sources']['land_snapshot'] = spec
        with self.fake_r2({}, []) as download:
            with self.assertRaisesRegex(ValueError, 'cached cloud input size/SHA-256 mismatch'):
                self.make()
        download.assert_not_called()
        cached.write_bytes(payload)
        self.cfg['sources']['land_snapshot'] = {'archive': spec, 'member': '../outside',
            'sha256': 'a' * 64, 'size_bytes': 1}
        config = pipeline.write(self.inputs / 'request2.json', self.cfg)
        with self.assertRaisesRegex(ValueError, 'unsafe ZIP member'):
            pipeline.Pipeline(config, self.root / 'run')

    def regional_template(self, value):
        template = pipeline.write(self.inputs / 'regional.json', value)
        self.cfg['sources']['regional_template'] = pipeline.pin(template)

    def test_active_proj_database_outside_input_root_and_offline_children(self):
        import pyproj
        database = pipeline.pin(Path(pyproj.datadir.get_data_dir()) / 'proj.db')
        self.assertFalse(Path(database['path']).is_relative_to(self.root))
        self.regional_template({'bering_proj_db': database})
        original_network = pyproj.network.is_network_enabled()
        self.addCleanup(pyproj.network.set_network_enabled, original_network)
        pyproj.network.set_network_enabled(True)
        with patch.dict(os.environ, {'PROJ_NETWORK': 'ON'}):
            runner = self.make()
            self.assertEqual(os.environ['PROJ_NETWORK'], 'OFF')
            self.assertFalse(pyproj.network.is_network_enabled())
            self.assertEqual(runner.identity['runtime']['proj_database'], database)
            self.assertFalse(runner.identity['runtime']['proj_network_enabled'])
            self.assertIn(database, runner.source_pins)
            result = subprocess.run([sys.executable, '-c',
                'import os, pyproj; assert os.environ["PROJ_NETWORK"] == "OFF"; '
                'assert not pyproj.network.is_network_enabled()'],
                check=True, capture_output=True)
            self.assertEqual(result.returncode, 0)

    def test_another_proj_database_path_is_rejected_even_with_correct_bytes(self):
        import pyproj
        database = Path(pyproj.datadir.get_data_dir()) / 'proj.db'
        copy = self.inputs / 'other-proj.db'
        copy.write_bytes(database.read_bytes())
        self.regional_template({'bering_proj_db': pipeline.pin(copy)})
        with self.assertRaisesRegex(ValueError, 'does not match active runtime database'):
            self.make()
        self.assertFalse((self.root / 'run').exists())

    def test_proj_exception_does_not_allow_other_external_sources(self):
        import pyproj
        database = pipeline.pin(Path(pyproj.datadir.get_data_dir()) / 'proj.db')
        self.regional_template({'bering_source_files': [database]})
        with self.assertRaisesRegex(ValueError, 'outside input root'):
            self.make()
        self.assertFalse((self.root / 'run').exists())

    def test_selected_proj_hash_is_verified_before_processing(self):
        import pyproj
        database = pipeline.pin(Path(pyproj.datadir.get_data_dir()) / 'proj.db')
        database['sha256'] = '0' * 64
        self.regional_template({'bering_proj_db': database})
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            self.make()
        self.assertFalse((self.root / 'run').exists())

    def test_stage_temporary_files_stay_in_workspace_and_outputs_are_fresh(self):
        runner = self.make()
        runner.stage('setup', 'fixture', 'v7-pipeline/fixtures/partial_stage.py',
                       self.sentinel, runner.out / 'fixture', _outputs=[runner.out / 'fixture'])
        self.assertIn(str(runner.out / 'scratch'), (runner.out / 'logs/fixture.log').read_text())
        with self.assertRaisesRegex(ValueError, 'new output'):
            pipeline.Pipeline(runner.config_path, runner.out)

    def test_failure_report_is_not_a_completed_stage(self):
        runner = self.make()
        def interrupted():
            with runner.timing.measure('mainland', 'prepare'):
                pass
            raise RuntimeError('fixture failure')
        with patch.object(runner, 'physical', side_effect=interrupted):
            with self.assertRaisesRegex(RuntimeError, 'fixture failure'):
                runner.run()
        self.assertFalse((runner.out / 'report.json').exists())
        failure = pipeline.read(runner.out / 'failure.json')
        self.assertFalse(failure['stages']['mainland']['complete'])
        self.assertFalse(failure['stages']['water']['complete'])

    def test_coastal_failure_cancels_basins_without_waiting_for_all_results(self):
        snapshot = pipeline.write(self.inputs / 'water.json',
                                  {'basins': [{'id': f'b{i}'} for i in range(12)]})
        self.cfg['sources']['water_snapshot'] = pipeline.pin(snapshot)
        self.cfg['basin_workers'] = 1
        runner = self.make()
        entered, released = threading.Event(), threading.Event()
        seen = []
        def coast(*args):
            if not entered.wait(.5):
                raise RuntimeError('basin did not start')
            raise ValueError('coastal failure')
        def basin(decision, *args):
            seen.append(decision['id'])
            entered.set()
            if not released.wait(.5):
                raise RuntimeError('coastal failure was hidden behind basin results')
            return {}
        original_cancel = runner.cancel
        def cancel():
            original_cancel()
            released.set()
        with patch.object(runner, 'extract_basins', return_value=runner.out / 'extractions'), \
                patch.object(runner, 'coast', side_effect=coast), \
                patch.object(runner, 'basin', side_effect=basin), \
                patch.object(runner, 'cancel', side_effect=cancel):
            with self.assertRaisesRegex(ValueError, 'coastal failure'):
                runner.water(self.inputs, self.inputs)
        self.assertLess(len(seen), 12)

    def test_actual_archive_to_basin_to_coverage_via_runner(self):
        import numpy as np
        import sys
        sys.path.insert(0, str(pipeline.SCRIPTS / 'v7-replay'))
        import extract_seavox_feature as extract
        source = pipeline.write(self.inputs / 'basin.geojson', {
            'type': 'FeatureCollection', 'features': [{'type': 'Feature',
                'properties': {'MRGID_SR': '24063'}, 'geometry': {'type': 'Polygon',
                    'coordinates': [[[0, 0], [0.006, 0], [0.006, 0.006], [0, 0.006], [0, 0]]]}}]})
        shape = self.inputs / 'shape'
        from osgeo import gdal
        with gdal.VectorTranslate(str(shape), str(source), format='ESRI Shapefile'):
            pass
        archive = self.inputs / 'sea.zip'
        with zipfile.ZipFile(archive, 'w') as zipped:
            for component in shape.iterdir():
                zipped.write(component, component.name)
        feature = extract.extract_feature(archive, '24063')
        decision = {'id': 'tiny-sea', 'source_id': 'seavox', 'source_version': 'fixture',
                    'source_feature_id': '24063', 'geometry_sha256': extract.canonical_hash(feature['geometry']),
                    'assignment_method': 'single_continent_named_basin', 'participant_entity_ids': [101]}
        snapshot = pipeline.write(self.inputs / 'snapshot.json', {
            'schema': 'worldatlas-geography-decision-export-v1', 'source': 'neon-export',
            'decision_revision': {'id': 'r1', 'entity_revision': 'e1', 'status': 'accepted'},
            'entity_revision': {'id': 'e1', 'status': 'accepted'}, 'basins': [decision],
            'category_bindings': [{'entity_id': 101, 'code': 6, 'physical_class': 'water'}],
            'sources': [{'source_id': 'seavox', 'version': 'fixture', 'sha256': pipeline.sha(archive)}]})
        self.cfg['sources']['seavox_archive'] = pipeline.pin(archive)
        self.cfg['sources']['water_snapshot'] = pipeline.pin(snapshot)
        runner = self.make()
        width, height = 131072, 54614
        physical, land = self.inputs / 'physical', self.inputs / 'land'
        for directory, water_code in [(physical, 1), (land, 0)]:
            directory.mkdir()
            np.arange(height + 1, dtype='<u4').tofile(directory / 'rows.u32le')
            np.tile(np.array([width, water_code], dtype='<u4'), height).tofile(directory / 'runs.u32le')
        original_stage = runner.stage
        def stop_after_extraction(*args, **kwargs):
            result = original_stage(*args, **kwargs)
            if args[1] == 'extract-basins':
                raise KeyboardInterrupt('simulated workspace interruption between stages')
            return result
        with patch.object(runner, 'stage', side_effect=stop_after_extraction):
            with self.assertRaises(KeyboardInterrupt):
                runner.extract_basins(snapshot)
        extraction_receipt = pipeline.pin(runner.out / 'checkpoints/extract-basins/complete.json')
        runner.close()
        runner = pipeline.Pipeline(runner.config_path, runner.out, resume=True)
        self.addCleanup(runner.close)
        extraction = runner.extract_basins(snapshot)
        result = runner.basin(decision, physical, land, snapshot, extraction)
        self.assertEqual(extraction_receipt, pipeline.pin(extraction_receipt['path']))
        manifest = pipeline.read(result['manifest_path'])
        self.assertGreater(manifest['physical_water_cells'], 0)
        self.assertEqual(result['manifest_sha256'], pipeline.sha(result['manifest_path']))
        coverage = json.loads((runner.out / 'logs/verify-basin-tiny-sea.log').read_text())
        self.assertEqual(coverage['status'], 'raster-to-span-match')
        self.assertEqual(coverage['cells'], manifest['physical_water_cells'])
        self.assertTrue(any(r['id'] == 'water/verify-basin-tiny-sea' and r['event'] == 'complete'
                            for r in runner.timing.records))

    def test_actual_raw_sources_to_fresh_components_in_process(self):
        import pyarrow as pa
        import pyarrow.parquet as pq
        from osgeo import ogr
        import numpy as np
        grid = {'width': 8, 'height': 4, 'west': -180, 'north': 90, 'step': 45}
        raw = self.root / 'raw'
        raw.mkdir()
        land_file = pipeline.write(raw / 'land.geojson', {'type': 'FeatureCollection', 'features': [
            {'type': 'Feature', 'properties': {}, 'geometry': {'type': 'Polygon', 'coordinates': [
                [[-180, 90], [-45, 90], [-45, 0], [-180, 0], [-180, 90]]]}}]})
        land = pipeline.write(self.inputs / 'land.json', {'schema': 'land-raster-candidate-v1',
            'grid': grid, 'selection_notes': 'synthetic', 'strip_rows': 2, 'minimum_free_bytes': 0,
            'land': [{'dataset': str(land_file), 'where': None, 'files': [pipeline.pin(land_file)]}]})
        water = pipeline.write(self.inputs / 'water.json', {'schema': 'water-shard-candidate-v2',
            'grid': grid, 'tile_size': 4, 'minimum_free_bytes': 0, 'selection_notes': 'synthetic',
            'policy': {'method': 'overture-inland-subtype-v1'}})
        geometry = bytes(ogr.CreateGeometryFromWkt(
            'POLYGON ((-180 90,-135 90,-135 45,-180 45,-180 90))').ExportToWkb())
        table = pa.Table.from_pylist([{'id': 'lake', 'subtype': 'lake', 'class': 'lake',
            'sources': [{'property': '', 'dataset': 'OpenStreetMap'}], 'geometry': geometry}])
        table = table.replace_schema_metadata({b'geo': json.dumps({'primary_column': 'geometry',
            'columns': {'geometry': {'encoding': 'WKB'}}}).encode()})
        shard = raw / 'water.parquet'
        pq.write_table(table, shard)
        manifest = pipeline.write(raw / 'manifest.json', {'file_count': 1,
            'files': [{'path': shard.name, 'sha256': pipeline.sha(shard)}]})
        for key, path in [('land_config', land), ('water_config', water), ('raw_manifest', manifest)]:
            self.cfg['sources'][key] = pipeline.pin(path)
        self.cfg['physical_controls'] = {'minimum_free_bytes': 0, 'max_parallel_shards': 1}
        runner = self.make()
        physical = runner.physical()
        spec = pipeline.rle_spec(physical, physical=True)
        self.assertEqual(spec['physical_mask_sha256'], pipeline.sha(physical / 'physical-dry.tif'))
        self.assertEqual(spec['report_sha256'], pipeline.sha(physical / 'report.json'))
        mask = physical / 'physical-dry.tif'
        original = mask.read_bytes()
        mask.write_bytes(original + b'changed')
        with self.assertRaisesRegex(ValueError, 'physical mask'):
            pipeline.rle_spec(physical, physical=True)
        mask.write_bytes(original)
        request = runner.document('components', {'schema': 'fresh-physical-components-v1',
            'grid': grid, 'controls': self.cfg['land_controls'], 'inputs': {key: pipeline.pin(path)
                for key, path in {'physical_rows': physical / 'rows.u32le',
                    'physical_runs': physical / 'runs.u32le', 'physical_report': physical / 'report.json',
                    'component_source': pipeline.SCRIPTS / 'v7-recovery/land/simple-v2-baseline/build_components.cpp'}.items()}})
        components = runner.out / 'components'
        if sys.platform != 'linux':
            self.skipTest('component publication requires Linux renameat2')
        runner.stage('mainland', 'components',
            'v7-recovery/land/fresh-components-20261104/build_components.py',
            request, runner.out / 'work/components', components)
        report = pipeline.read(components / 'report.json')
        self.assertEqual(report['land_cells'], 5)
        self.assertEqual(report['component_runs_sha256'], pipeline.sha(components / 'runs.u32le'))
        manifest = pipeline.read(components / 'manifest.json')
        self.assertEqual(manifest['physical_report'], pipeline.pin(physical / 'report.json'))
        self.assertFalse((components / 'monitor.json').exists())
        np.testing.assert_array_equal(np.fromfile(physical / 'rows.u32le', dtype='<u4'), [0, 3, 5, 6, 7])
        self.assertEqual(pipeline.read(runner.out / 'physical/report.json')['source_download_elapsed_seconds'], 0)

    def test_single_cloud_configuration_matches_local_raw_and_component_streams_in_another_root(self):
        self.test_actual_raw_sources_to_fresh_components_in_process()
        payloads = {'sources/land.geojson': (self.root / 'raw/land.geojson').read_bytes(),
                    'sources/water.parquet': (self.root / 'raw/water.parquet').read_bytes()}
        land_source = self.cloud(payloads['sources/land.geojson'], 'sources/land.geojson')
        land = pipeline.read(self.inputs / 'land.json')
        land['land'] = [{'dataset': land_source, 'where': None, 'files': [land_source]}]
        water_source = self.cloud(payloads['sources/water.parquet'], 'sources/water.parquet')
        manifest = {'file_count': 1, 'files': [{'path': 'raw/water.parquet',
            'sha256': water_source['sha256'], 'size': water_source['size_bytes'],
            'r2_bucket': water_source['r2_bucket'], 'r2_key': water_source['r2_key']}]}
        cfg = {**self.cfg, 'input_root': './unused-on-another-computer',
            'sources': {key: {'json': {}} for key in self.cfg['sources']},
            'physical_controls': {**self.cfg['physical_controls'], 'source_staging': {
                'mode': 'r2-s3', 'endpoint_url': 'https://' + '0' * 32 + '.r2.cloudflarestorage.com'}}}
        cfg['sources'].update(land_config={'json': land}, water_config={'json': pipeline.read(self.inputs / 'water.json')},
                              raw_manifest={'json': manifest})
        config = pipeline.write(self.inputs / 'single-cloud-config.json', cfg)
        calls = []
        with self.fake_r2(payloads, calls):
            runner = pipeline.Pipeline(config, work_dir=self.root / 'another-computer')
            self.addCleanup(runner.close)
            physical = runner.physical()
        components = runner.out / 'components'
        request = runner.document('components', {'schema': 'fresh-physical-components-v1',
            'grid': land['grid'], 'controls': cfg['land_controls'], 'inputs': {key: pipeline.pin(path)
                for key, path in {'physical_rows': physical / 'rows.u32le', 'physical_runs': physical / 'runs.u32le',
                    'physical_report': physical / 'report.json', 'component_source': pipeline.SCRIPTS /
                    'v7-recovery/land/simple-v2-baseline/build_components.cpp'}.items()}})
        runner.stage('mainland', 'components', 'v7-recovery/land/fresh-components-20261104/build_components.py',
                     request, runner.out / 'work/components', components)
        for local, cloud in [(self.root / 'run/physical/physical', physical), (self.root / 'run/components', components)]:
            for name in ('rows.u32le', 'runs.u32le'):
                self.assertEqual(pipeline.sha(local / name), pipeline.sha(cloud / name))
        self.assertEqual(calls, ['sources/land.geojson', 'sources/water.parquet'])


if __name__ == '__main__':
    unittest.main()
