"""Runner contracts, measured parallelism, and actual raw-to-component chaining."""
import json
import os
from pathlib import Path
import struct
import subprocess
import zipfile
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import run_pipeline as pipeline


class TimingTests(unittest.TestCase):
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
        self.cfg = {'schema': 'worldatlas-end-to-end-pipeline-v1', 'research_only': True,
                    'selection_notes': 'Synthetic processor integration fixture',
                    'input_root': str(self.root),
                    'sources': {key: pipeline.pin(self.sentinel) for key in required},
                    'land_controls': {'minimum_free_bytes': 2 << 30}}

    def make(self):
        config = pipeline.write(self.inputs / 'request.json', self.cfg)
        runner = pipeline.Pipeline(config, self.root / 'run', allow_provisional=True)
        self.addCleanup(runner.close)
        return runner

    def test_no_implicit_research_optin(self):
        config = pipeline.write(self.inputs / 'request.json', self.cfg)
        with self.assertRaisesRegex(ValueError, 'explicit'):
            pipeline.Pipeline(config, self.root / 'run')
        self.assertFalse((self.root / 'run').exists())

    def test_invalid_source_fails_before_any_processing(self):
        self.cfg['sources']['land_config']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'source pin mismatch'):
            self.make()
        self.assertFalse((self.root / 'run').exists())

    def test_child_temporary_files_stay_in_workspace_and_outputs_are_fresh(self):
        runner = self.make()
        for key in ('TMPDIR', 'TMP', 'TEMP', 'CPL_TMPDIR', 'SQLITE_TMPDIR'):
            self.assertEqual(runner.env[key], str(runner.out / 'scratch'))
        self.assertEqual(runner.env['PYTHONPATH'].split(os.pathsep)[:3],
                         [str(pipeline.SCRIPTS), str(pipeline.SCRIPTS / pipeline.REPLAY),
                          str(pipeline.SCRIPTS / pipeline.OCEAN)])
        runner.command('setup', 'coast-import', 'v7-replay/batch_coastal_tiles.py', '--help')
        self.assertIn('usage:', (runner.out / 'logs/coast-import.log').read_text())
        with self.assertRaisesRegex(ValueError, 'new output'):
            pipeline.Pipeline(runner.config_path, runner.out, allow_provisional=True)

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
        with patch.object(runner, 'coast', side_effect=coast), \
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
        subprocess.run(['ogr2ogr', '-f', 'ESRI Shapefile', str(shape), str(source)],
                       check=True, capture_output=True)
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
        original_command = runner.command
        def stop_after_extraction(*args, **kwargs):
            result = original_command(*args, **kwargs)
            if args[1] == 'extract-tiny-sea':
                raise KeyboardInterrupt('simulated workspace interruption between stages')
            return result
        with patch.object(runner, 'command', side_effect=stop_after_extraction):
            with self.assertRaises(KeyboardInterrupt):
                runner.basin(decision, physical, land, snapshot)
        extraction_receipt = pipeline.pin(runner.out / 'checkpoints/extract-tiny-sea/complete.json')
        runner.close()
        runner = pipeline.Pipeline(runner.config_path, runner.out, allow_provisional=True, resume=True)
        self.addCleanup(runner.close)
        result = runner.basin(decision, physical, land, snapshot)
        self.assertEqual(extraction_receipt, pipeline.pin(extraction_receipt['path']))
        manifest = pipeline.read(result['manifest_path'])
        self.assertGreater(manifest['physical_water_cells'], 0)
        self.assertEqual(result['manifest_sha256'], pipeline.sha(result['manifest_path']))
        coverage = json.loads((runner.out / 'logs/verify-basin-tiny-sea.log').read_text())
        self.assertEqual(coverage['status'], 'raster-to-span-match')
        self.assertEqual(coverage['cells'], manifest['physical_water_cells'])
        self.assertTrue(any(r['id'] == 'water/verify-basin-tiny-sea' and r['event'] == 'complete'
                            for r in runner.timing.records))

    def test_actual_raw_sources_to_fresh_components_via_stage_clis(self):
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
        runner.command('mainland', 'components',
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


if __name__ == '__main__':
    unittest.main()
