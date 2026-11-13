"""Runner contracts, measured parallelism, and actual raw-to-component chaining."""

import json
from contextlib import contextmanager
import gzip
import hashlib
import io
from pathlib import Path
import zipfile
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

from map_build import build as pipeline
from map_build.execution.runtime import elapsed_union


class TimingTests(unittest.TestCase):
    def test_reused_physical_outputs_count_current_verification_only(self):
        with tempfile.TemporaryDirectory() as td:
            timer = pipeline.Timing(Path(td) / 'events.jsonl')
            self.addCleanup(timer.close)
            receipt = {
                'status': 'reused',
                'source_run': '/source/run',
                'processing_elapsed_seconds': 12345,
                'source_download_elapsed_seconds': 54321,
            }
            with timer.measure('physical', 'verify-reused'):
                pass
            timer.mark_complete('physical', physical_report=receipt)
            result = timer.summary(receipt)['physical']
            self.assertTrue(result['complete'])
            self.assertLess(result['processing_elapsed_seconds'], 1)
            self.assertEqual(result['source_download_elapsed_seconds'], 0)
            self.assertEqual(result['reused_from'], '/source/run')
            self.assertIsNone(result['producer_processing_elapsed_seconds'])

    def test_selected_configuration_has_portable_sources_and_working_geographic_revisions(self):
        path = Path(pipeline.__file__).parents[1] / 'config.json'
        cfg = pipeline.read(path)
        self.assertNotIn('/workspace/', path.read_text())
        self.assertNotIn('/tmp/', path.read_text())
        self.assertNotIn('input_root', cfg)
        self.assertEqual(cfg['sources']['raw_manifest']['json']['file_count'], 32)
        self.assertEqual(set(cfg['decision_revisions']), {'mainland', 'regional', 'water', 'ocean'})
        self.assertEqual(set(cfg['sources']), {'land_config', 'water_config', 'raw_manifest'})

    def test_interval_union_excludes_idle_gaps_and_parallel_double_count(self):
        self.assertEqual(elapsed_union([(1, 5), (2, 4), (8, 9), (4, 7)]), 7)
        self.assertEqual(elapsed_union([]), 0)
        with self.assertRaises(ValueError):
            elapsed_union([(2, 1)])

    def test_completed_intervals_survive_and_failures_remain_incomplete(self):
        with tempfile.TemporaryDirectory() as td:
            timer = pipeline.Timing(Path(td) / 'events.jsonl')
            with patch.object(
                pipeline.time, 'monotonic', side_effect=[10, 13, 20, 21, 40, 40, 65, 65]
            ):
                with timer.measure('water', 'basin'):
                    pass
                with self.assertRaises(RuntimeError):
                    with timer.measure('water', 'coast'):
                        raise RuntimeError('interrupted')
                with timer.measure('physical', 'stage-total'):
                    with timer.measure('physical', 'physical', kind='command'):
                        pass
            timer.completed_groups.add('physical')
            doc = timer.summary(
                {
                    'status': 'candidate-only',
                    'processing_elapsed_seconds': 5,
                    'source_download_elapsed_seconds': 20,
                }
            )
            self.assertEqual(doc['water']['processing_elapsed_seconds'], 4)
            self.assertFalse(doc['water']['complete'])
            self.assertEqual(doc['physical']['processing_elapsed_seconds'], 5)
            self.assertEqual(doc['physical']['source_download_elapsed_seconds'], 20)
            records = [json.loads(line) for line in timer.path.read_text().splitlines()]
            self.assertEqual(
                [r['event'] for r in records if r['event'] != 'attempt'],
                ['start', 'complete', 'start', 'failed', 'start', 'start', 'complete', 'complete'],
            )

    def test_invalid_acquisition_timing_cannot_be_a_complete_stage(self):
        with tempfile.TemporaryDirectory() as td:
            timer = pipeline.Timing(Path(td) / 'events.jsonl')
            with patch.object(pipeline.time, 'monotonic', side_effect=[1, 3]):
                with timer.measure('physical', 'stage-total'):
                    pass
            timer.completed_groups.add('physical')
            summary = timer.summary(
                {'status': 'candidate-only', 'source_download_elapsed_seconds': 4}
            )['physical']
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
                    time.sleep(0.06)

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
            self.assertLess(summary['processing_elapsed_seconds'], summed * 0.8)


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.inputs = self.root / 'inputs'
        self.inputs.mkdir()
        self.sentinel = pipeline.write(self.inputs / 'sentinel.json', {})
        required = ('land_config', 'water_config', 'raw_manifest')
        self.cfg = {
            'schema': 'worldatlas-end-to-end-pipeline-v1',
            'selection_notes': 'Synthetic processor integration fixture',
            'input_root': str(self.root),
            'sources': {key: pipeline.pin(self.sentinel) for key in required},
            'land_controls': {'minimum_free_bytes': 2 << 30},
        }

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

    def test_saved_complete_selection_is_used_for_initialization_and_resume(self):
        selected = {
            'schema': 'worldatlas-input-selection-v1',
            'revisions': dict(
                mainland='mainland', regional='regional', water='water', ocean='ocean'
            ),
            'domains': {
                'mainland': {'category_bindings': []},
                'regional': {'category_bindings': []},
                'water': {'features': [], 'basins': [], 'category_bindings': []},
                'ocean': {'category_bindings': []},
            },
            'raw_sources': [],
        }
        config = pipeline.write(self.inputs / 'request.json', self.cfg)
        selection = pipeline.write(self.inputs / 'selection.json', selected)
        with patch.object(
            pipeline, 'read_selection', side_effect=AssertionError('unexpected live database read')
        ):
            runner = pipeline.Pipeline(config, selection=selection)
            original = runner.identity['input_selection_sha256']
            self.assertEqual(pipeline.read(runner.out / 'input-selection.json'), selected)
            runner.close()
            resumed = pipeline.Pipeline(config, resume=True)
            self.assertEqual(resumed.identity['input_selection_sha256'], original)
            resumed.close()

    def test_release_comparison_downloads_and_verifies_both_streams(self):
        config = pipeline.write(self.inputs / 'request.json', self.cfg)
        digest = lambda data: hashlib.sha256(data).hexdigest()
        decoded = {name: name.encode() for name in ('rows', 'runs')}
        stored = {f'review/{name}.u32le.gz': gzip.compress(data) for name, data in decoded.items()}
        catalog = [
            (name, 'worldatlas', key, len(data), digest(data), digest(decoded[name]))
            for name, (key, data) in zip(decoded, stored.items())
        ]
        calls = []
        with (
            patch.object(pipeline, 'read_release_streams', return_value=catalog),
            self.fake_r2(stored, calls),
        ):
            runner = pipeline.Pipeline(config, compare_release='v8.0')
            try:
                for name, data in decoded.items():
                    self.assertEqual(runner.sources['reference_' + name].read_bytes(), data)
            finally:
                runner.close()
            resumed = pipeline.Pipeline(config, compare_release='v8.0', resume=True)
            resumed.close()
        self.assertEqual(calls, list(stored))

    def cloud(self, payload, key='sources/input.json'):
        return {
            'r2_bucket': 'worldatlas',
            'r2_key': key,
            'sha256': hashlib.sha256(payload).hexdigest(),
            'size_bytes': len(payload),
        }

    @contextmanager
    def fake_r2(self, payloads, calls):
        from map_build.physical import build as module

        def download(endpoint, entry, destination):
            calls.append(entry['r2_key'])
            destination.write_bytes(payloads[entry['r2_key']])

        def retrieve(*, Bucket, Key):
            calls.append(Key)
            data = payloads[Key]
            return {'Body': io.BytesIO(data), 'ContentLength': len(data)}

        client = Mock()
        client.get_object.side_effect = retrieve
        with (
            patch.object(module, 'download_r2', side_effect=download),
            patch.object(module, 'make_r2_client', return_value=client),
        ):
            yield client.get_object

    def test_catalog_resolves_exact_versions_before_r2_acquisition(self):
        payload = b'{}'
        raw = self.cloud(payload)
        identity = {'source_id': 'fixture', 'version': 'v1'}
        reference = {'r2_source': identity}
        row = ('fixture', 'v1', raw['r2_bucket'], raw['r2_key'], raw['sha256'], len(payload))
        self.cfg['sources']['water_config'] = reference
        self.cfg['sources']['raw_manifest'] = {
            'json': {'files': [{'path': 'raw/fixture', **reference}]}
        }
        calls = []
        with (
            patch.object(pipeline.Pipeline, 'neon_raw_catalog', return_value=[row]) as lookup,
            self.fake_r2({raw['r2_key']: payload}, calls),
        ):
            runner = self.make()
        lookup.assert_called_once_with([('fixture', 'v1')])
        self.assertEqual(calls, [raw['r2_key']])
        self.assertEqual(runner.sources['water_config'].read_bytes(), payload)
        manifest = pipeline.read(runner.sources['raw_manifest'])
        size = raw.pop('size_bytes')
        self.assertEqual(
            manifest['files'], [{'path': 'raw/fixture', 'size': size, **identity, **raw}]
        )

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
                    source = runner.sources['raw_manifest']
                    self.assertTrue(source.is_relative_to(root))
                    self.assertEqual(source.read_bytes(), payload)
                    self.assertEqual(len(runner.acquisition_intervals), 1)
                    results.append(pipeline.sha(source))
                finally:
                    runner.close()
        self.assertEqual(calls, ['sources/input.json', 'sources/input.json'])
        self.assertEqual(results[0], results[1])

    def test_inline_physical_documents_share_verified_cloud_sources(self):
        payload = b'raw source bytes'
        source = self.cloud(payload, 'sources/land.geojson')
        self.cfg['sources']['land_config'] = {
            'json': {'land': [{'dataset': source, 'files': [source]}]}
        }
        calls = []
        with self.fake_r2({'sources/land.geojson': payload}, calls):
            runner = self.make()
        land = pipeline.read(runner.sources['land_config'])['land'][0]
        self.assertEqual(land['dataset'], land['files'][0]['path'])
        self.assertEqual(land['files'][0]['size_bytes'], len(payload))
        self.assertEqual(calls, ['sources/land.geojson'])

    def test_cloud_zip_members_are_individually_pinned_and_keep_sidecars_together(self):
        buffer = io.BytesIO()
        members = {'land/land.shp': b'geometry', 'land/land.dbf': b'attributes'}
        with zipfile.ZipFile(buffer, 'w') as packed:
            for name, value in members.items():
                packed.writestr(name, value)
        archive = self.cloud(buffer.getvalue(), 'sources/land.zip')
        files = [
            {
                'archive': archive,
                'member': name,
                'sha256': hashlib.sha256(value).hexdigest(),
                'size_bytes': len(value),
            }
            for name, value in members.items()
        ]
        self.cfg['sources']['land_config'] = {
            'json': {'land': [{'dataset': files[0], 'files': files}]}
        }
        calls = []
        with self.fake_r2({'sources/land.zip': buffer.getvalue()}, calls):
            runner = self.make()
        land = pipeline.read(runner.sources['land_config'])['land'][0]
        self.assertEqual(calls, ['sources/land.zip'])
        self.assertEqual(
            Path(land['files'][0]['path']).parent, Path(land['files'][1]['path']).parent
        )
        self.assertEqual(len({item['path'] for item in runner.source_pins}), 5)

    def test_raw_manifest_keeps_shards_deferred_to_existing_physical_stage(self):
        raw = {
            'file_count': 1,
            'files': [
                {
                    'path': 'raw/part.parquet',
                    'sha256': 'a' * 64,
                    'r2_bucket': 'worldatlas',
                    'r2_key': 'raw/part.parquet',
                    'size': 123,
                }
            ],
        }
        self.cfg['sources']['raw_manifest'] = {'json': raw}
        with self.fake_r2({}, []) as download:
            runner = self.make()
        download.assert_not_called()
        self.assertEqual(pipeline.read(runner.sources['raw_manifest']), raw)

    def test_changed_cloud_cache_or_wrong_download_fails_before_run_creation(self):
        payload = b'{}'
        self.cfg['sources']['raw_manifest'] = self.cloud(payload)
        calls = []
        with self.fake_r2({'sources/input.json': b'wrong'}, calls):
            with self.assertRaisesRegex(ValueError, 'cloud input size/SHA-256 mismatch'):
                self.make()
        self.assertFalse((self.root / 'run').exists())
        self.assertEqual(len(list((self.root / 'inputs').rglob('download-*'))), 0)

    def test_import_cache_is_reused_without_network_or_download_time(self):
        payload = b'{}'
        source = self.cloud(payload)
        cached = self.inputs / source['sha256'] / 'source.json'
        cached.parent.mkdir()
        cached.write_bytes(payload)
        self.cfg['sources']['raw_manifest'] = source
        with self.fake_r2({}, []) as download:
            runner = self.make()
        download.assert_not_called()
        self.assertEqual(runner.sources['raw_manifest'].stat().st_ino, cached.stat().st_ino)
        self.assertEqual(runner.acquisition_intervals, [])

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
        self.cfg['sources']['raw_manifest'] = spec
        with self.fake_r2({}, []) as download:
            with self.assertRaisesRegex(ValueError, 'cached cloud input size/SHA-256 mismatch'):
                self.make()
        download.assert_not_called()
        cached.write_bytes(payload)
        self.cfg['sources']['raw_manifest'] = {
            'archive': spec,
            'member': '../outside',
            'sha256': 'a' * 64,
            'size_bytes': 1,
        }
        config = pipeline.write(self.inputs / 'request2.json', self.cfg)
        with self.assertRaisesRegex(ValueError, 'unsafe ZIP member'):
            pipeline.Pipeline(config, self.root / 'run')

    def test_failure_report_is_not_a_completed_stage(self):
        runner = self.make()

        def interrupted():
            with runner.timing.measure('mainland', 'prepare'):
                pass
            raise RuntimeError('fixture failure')

        runner.selection = {'domains': {}}
        with patch.object(runner, 'physical', side_effect=interrupted):
            with self.assertRaisesRegex(RuntimeError, 'fixture failure'):
                runner.run()
        self.assertFalse((runner.out / 'report.json').exists())
        failure = pipeline.read(runner.out / 'failure.json')
        self.assertFalse(failure['stages']['mainland']['complete'])
        self.assertFalse(failure['stages']['water']['complete'])

    def test_actual_raw_sources_to_fresh_components_in_process(self):
        import pyarrow as pa
        import pyarrow.parquet as pq
        from osgeo import ogr
        import numpy as np

        grid = {'width': 8, 'height': 4, 'west': -180, 'north': 90, 'step': 45}
        raw = self.root / 'raw'
        raw.mkdir()
        land_file = pipeline.write(
            raw / 'land.geojson',
            {
                'type': 'FeatureCollection',
                'features': [
                    {
                        'type': 'Feature',
                        'properties': {},
                        'geometry': {
                            'type': 'Polygon',
                            'coordinates': [
                                [[-180, 90], [-45, 90], [-45, 0], [-180, 0], [-180, 90]]
                            ],
                        },
                    }
                ],
            },
        )
        land = pipeline.write(
            self.inputs / 'land.json',
            {
                'schema': 'land-raster-candidate-v1',
                'grid': grid,
                'selection_notes': 'synthetic',
                'strip_rows': 2,
                'minimum_free_bytes': 0,
                'land': [
                    {'dataset': str(land_file), 'where': None, 'files': [pipeline.pin(land_file)]}
                ],
            },
        )
        water = pipeline.write(
            self.inputs / 'water.json',
            {
                'schema': 'water-shard-candidate-v2',
                'grid': grid,
                'tile_size': 4,
                'minimum_free_bytes': 0,
                'selection_notes': 'synthetic',
                'policy': {'method': 'overture-inland-subtype-v1'},
            },
        )
        geometry = bytes(
            ogr.CreateGeometryFromWkt(
                'POLYGON ((-180 90,-135 90,-135 45,-180 45,-180 90))'
            ).ExportToWkb()
        )
        table = pa.Table.from_pylist(
            [
                {
                    'id': 'lake',
                    'subtype': 'lake',
                    'class': 'lake',
                    'sources': [{'property': '', 'dataset': 'OpenStreetMap'}],
                    'geometry': geometry,
                }
            ]
        )
        table = table.replace_schema_metadata(
            {
                b'geo': json.dumps(
                    {'primary_column': 'geometry', 'columns': {'geometry': {'encoding': 'WKB'}}}
                ).encode()
            }
        )
        shard = raw / 'water.parquet'
        pq.write_table(table, shard)
        manifest = pipeline.write(
            raw / 'manifest.json',
            {'file_count': 1, 'files': [{'path': shard.name, 'sha256': pipeline.sha(shard)}]},
        )
        for key, path in [
            ('land_config', land),
            ('water_config', water),
            ('raw_manifest', manifest),
        ]:
            self.cfg['sources'][key] = pipeline.pin(path)
        self.cfg['physical_controls'] = {'minimum_free_bytes': 0, 'max_parallel_shards': 1}
        runner = self.make()
        physical = runner.physical()
        reused = pipeline.Pipeline(
            runner.config_path, self.root / 'reused', physical_from=runner.out
        )
        self.addCleanup(reused.close)
        producer_report = (physical / 'report.json').read_bytes()
        from map_build.physical import build as physical_build

        with patch.object(
            physical_build, 'run', side_effect=AssertionError('physical outputs must be reused')
        ):
            self.assertEqual(reused.physical(), physical)
        self.assertEqual(reused.identity['physical_reuse']['source_run'], str(runner.out))
        self.assertEqual((physical / 'report.json').read_bytes(), producer_report)
        notes = pipeline.read(land)
        notes['selection_notes'] = 'Reworded description of the same selected sources'
        descriptive = pipeline.write(self.inputs / 'same-land-new-notes.json', notes)
        self.assertEqual(
            pipeline.physical_reference(runner.out, {**runner.sources, 'land_config': descriptive})[
                'status'
            ],
            'reused',
        )
        changed = pipeline.write(
            self.inputs / 'different-land.json', {'grid': grid, 'different': True}
        )
        with self.assertRaisesRegex(ValueError, 'physical input differs'):
            pipeline.physical_reference(runner.out, {**runner.sources, 'land_config': changed})
        mask = physical / 'physical-dry.tif'
        original = mask.read_bytes()
        mask.write_bytes(original + b'changed')
        with self.assertRaisesRegex(ValueError, 'checkpoint/input hash mismatch'):
            reused.physical()
        mask.write_bytes(original)
        from map_build.core.grid import Grid
        from map_build.land.connected import build_components

        components = runner.out / 'components'
        result = build_components(Grid(**grid), physical, components)
        self.assertEqual(result['land_cells'], 5)
        self.assertEqual(
            result['output_sha256']['runs.u32le'], pipeline.sha(components / 'runs.u32le')
        )
        np.testing.assert_array_equal(
            np.fromfile(physical / 'rows.u32le', dtype='<u4'), [0, 3, 5, 6, 7]
        )
        self.assertEqual(
            pipeline.read(runner.out / 'physical/report.json')['source_download_elapsed_seconds'], 0
        )

    def test_single_cloud_configuration_matches_local_raw_and_component_streams_in_another_root(
        self,
    ):
        self.test_actual_raw_sources_to_fresh_components_in_process()
        payloads = {
            'sources/land.geojson': (self.root / 'raw/land.geojson').read_bytes(),
            'sources/water.parquet': (self.root / 'raw/water.parquet').read_bytes(),
        }
        land_source = self.cloud(payloads['sources/land.geojson'], 'sources/land.geojson')
        land = pipeline.read(self.inputs / 'land.json')
        land['land'] = [{'dataset': land_source, 'where': None, 'files': [land_source]}]
        water_source = self.cloud(payloads['sources/water.parquet'], 'sources/water.parquet')
        manifest = {
            'file_count': 1,
            'files': [
                {
                    'path': 'raw/water.parquet',
                    'sha256': water_source['sha256'],
                    'size': water_source['size_bytes'],
                    'r2_bucket': water_source['r2_bucket'],
                    'r2_key': water_source['r2_key'],
                }
            ],
        }
        cfg = {
            **self.cfg,
            'input_root': './unused-on-another-computer',
            'sources': {key: {'json': {}} for key in self.cfg['sources']},
            'physical_controls': {
                **self.cfg['physical_controls'],
                'source_staging': {
                    'mode': 'r2-s3',
                    'endpoint_url': 'https://' + '0' * 32 + '.r2.cloudflarestorage.com',
                },
            },
        }
        cfg['sources'].update(
            land_config={'json': land},
            water_config={'json': pipeline.read(self.inputs / 'water.json')},
            raw_manifest={'json': manifest},
        )
        config = pipeline.write(self.inputs / 'single-cloud-config.json', cfg)
        calls = []
        with self.fake_r2(payloads, calls):
            runner = pipeline.Pipeline(config, work_dir=self.root / 'another-computer')
            self.addCleanup(runner.close)
            physical = runner.physical()
        components = runner.out / 'components'
        from map_build.core.grid import Grid
        from map_build.land.connected import build_components

        build_components(Grid(**land['grid']), physical, components)
        for local, cloud in [
            (self.root / 'run/physical/physical', physical),
            (self.root / 'run/components', components),
        ]:
            for name in ('rows.u32le', 'runs.u32le'):
                self.assertEqual(pipeline.sha(local / name), pipeline.sha(cloud / name))
        self.assertEqual(calls, ['sources/land.geojson', 'sources/water.parquet'])


if __name__ == '__main__':
    unittest.main()
