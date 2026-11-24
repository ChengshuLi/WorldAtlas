from base64 import b64encode
from functools import wraps
from contextlib import contextmanager, ExitStack
import fcntl
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock
from pathlib import Path
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from osgeo import gdal, ogr
from worldatlas.shared import r2
from worldatlas.shared.r2 import R2Client
from worldatlas.map_build.execution import runtime
from worldatlas.map_build.execution.code_archive import read_source, source_files
from worldatlas.map_build.execution.runtime import RunFilePins
from worldatlas.map_build.physical import build as b
from worldatlas.map_build.test_support import cache_fixture_file, r2_file_pin
from worldatlas.shared.files import pin_file, sha256_file, write_json


LAND = b.land.run
WATER = b.water.run
UNION = b.water_union.run
COMPOSE = b.composition.run


@contextmanager
def intercept_stages(effect):
    """Observe or interrupt a real stage without changing the production runner."""
    def wrap_stage(original):
        @wraps(original)
        def intercepted(*args, **kwargs):
            if callable(effect):
                return effect(original, *args, **kwargs)
            raise effect

        return intercepted

    with ExitStack() as stack:
        for module, name, original in (
            (b.land, 'run', LAND), (b.water, 'run', WATER),
            (b.water_union, 'run', UNION), (b.composition, 'run', COMPOSE),
        ):
            stack.enter_context(mock.patch.object(module, name, wrap_stage(original)))
        yield


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.config_dir = self.root / 'configs'
        self.config_dir.mkdir()
        self.land_dir = self.root / 'land-input'
        self.land_dir.mkdir()
        self.raw = self.root / 'raw'
        self.raw.mkdir()
        self.cache = self.root / 'inputs'
        self.grid = {'width': 8, 'height': 4, 'west': -180, 'north': 90, 'step': 45}
        land = self.land_dir / 'land.geojson'
        land.write_text(
            json.dumps(
                {
                    'type': 'FeatureCollection',
                    'features': [
                        {
                            'type': 'Feature',
                            'properties': {},
                            'geometry': {
                                'type': 'Polygon',
                                'coordinates': [
                                    [
                                        [-180, 90],
                                        [-45, 90],
                                        [-45, 0],
                                        [-180, 0],
                                        [-180, 90],
                                    ]
                                ],
                            },
                        }
                    ],
                }
            )
        )
        coastline_source = r2_file_pin(land)
        self.cached_coastline = cache_fixture_file(self.cache, land, coastline_source)
        land_cfg = {
            'schema': 'land-raster-candidate-v1',
            'selection_notes': 'synthetic',
            'strip_rows': 2,
            'land': [
                {
                    'dataset': coastline_source['r2_key'],
                    'where': None,
                    'files': [coastline_source],
                }
            ],
        }
        water_cfg = {
            'schema': 'water-shard-candidate-v2',
            'tile_size': 4,
            'selection_notes': 'synthetic',
        }
        geom = bytes(
            ogr.CreateGeometryFromWkt(
                'POLYGON ((-180 90,-135 90,-135 45,-180 45,-180 90))'
            ).ExportToWkb()
        )
        rows = [
            {
                'id': 'lake',
                'subtype': 'lake',
                'class': 'lake',
                'sources': [{'property': '', 'dataset': 'OpenStreetMap'}],
                'geometry': geom,
            }
        ]
        table = pa.Table.from_pylist(rows).replace_schema_metadata(
            {
                b'geo': json.dumps(
                    {
                        'primary_column': 'geometry',
                        'columns': {'geometry': {'encoding': 'WKB'}},
                    }
                ).encode()
            }
        )
        shard = self.raw / 'water.parquet'
        pq.write_table(table, shard)
        water_source = r2_file_pin(shard)
        self.cached_water = cache_fixture_file(self.cache, shard, water_source)
        self.cfg = {
            'schema': 'raw-physical-pipeline-v3',
            'minimum_free_bytes': 0,
            'source_directory': str(self.cache),
            'land_config': land_cfg,
            'grid': self.grid,
            'inland_water': {**water_cfg, 'file_count': 1, 'files': [water_source]},
        }
        self.config = self.config_dir / 'pipeline.json'
        self.config.write_text(json.dumps(self.cfg))

    def tearDown(self):
        self.tmp.cleanup()

    def set_water_sources(self, *paths):
        sources = [r2_file_pin(path) for path in paths]
        cached_paths = [
            cache_fixture_file(self.cache, path, source)
            for path, source in zip(paths, sources, strict=True)
        ]
        self.cfg['inland_water'].update(files=sources, file_count=len(sources))
        return cached_paths

    def interrupt_before_union(self, out):

        def stage(name, *args, **kwargs):
            if name == UNION:
                raise ValueError('simulated interruption')
            return name(*args, **kwargs)

        with intercept_stages(stage):
            with self.assertRaisesRegex(ValueError, 'simulated interruption'):
                b.run(self.config, out)

    def test_resume_reuses_verified_checkpoints_and_preserves_timing(self):
        out = self.root / 'resume'
        self.interrupt_before_union(out)
        seen = []

        def stage(name, *args, **kwargs):
            seen.append(name)
            return name(*args, **kwargs)

        with intercept_stages(stage):
            report = b.run(self.config, out, resume=True)
        self.assertTrue(report['timing_complete'])
        self.assertGreater(report['processing_elapsed_seconds'], 0)
        self.assertNotIn(LAND, seen)
        self.assertNotIn(WATER, seen)
        resumed = b.run(self.config, out, resume=True)
        self.assertEqual(resumed['directory'], str(out / 'physical'))
        self.assertEqual(resumed['physical_output_sha256'], report['physical_output_sha256'])

    def test_concurrent_attempt_is_rejected(self):
        out = self.root / 'locked'
        b.run(self.config, out)
        lock = out / 'run.lock'
        with lock.open('w') as f:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(ValueError, 'another pipeline runner'):
                b.run(self.config, out, resume=True)

    def test_actual_kill_preserves_units_and_marks_timing_incomplete(self):
        out = self.root / 'actual-kill'
        marker = self.root / 'waiting'
        code = """from worldatlas.map_build.execution.runtime import RunFilePins
from worldatlas.map_build.physical import build as b
import pathlib, sys, time
original = b.water_union.run
def stage(*args, **options):
    pathlib.Path(sys.argv[3]).write_text("ready")
    time.sleep(60)
    return original(*args, **options)
b.water_union.run = stage
b.run(sys.argv[1], sys.argv[2])
"""
        env = os.environ.copy()
        proc = subprocess.Popen(
            [sys.executable, '-c', code, str(self.config), str(out), str(marker)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        try:
            deadline = time.monotonic() + 30
            while not marker.exists() and proc.poll() is None and time.monotonic() < deadline:
                time.sleep(0.05)
            if not marker.exists():
                if proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=10)
                self.fail('child did not reach checkpoint: ' + proc.stderr.read().decode())
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.wait(timeout=10)
        report = b.run(self.config, out, resume=True)
        self.assertFalse(report['timing_complete'])
        self.assertIsNone(report['processing_elapsed_seconds'])
        self.assertGreater(report['recorded_processing_elapsed_seconds'], 0)

    def test_resume_rejects_tampered_checkpoint_and_input(self):
        out = self.root / 'tampered'
        self.interrupt_before_union(out)
        (out / 'shards/00000/water.tif').write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError, 'completed stage output changed: physical-shard-00000'):
            b.run(self.config, out, resume=True)
        self.cfg['union_rows_per_block'] = 4
        self.config.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError, 'saved stage request changed'):
            b.run(self.config, out, resume=True)

    def test_resume_trusts_changed_code_and_retains_completed_data(self):
        out = self.root / 'changed-code'
        self.interrupt_before_union(out)
        first_attempt, = (out / 'attempts').iterdir()
        shard_path = out / 'shards/00000/water.tif'
        initial_shard = pin_file(shard_path)
        marker = b'\n# Example code change between attempts.\n'
        source_path = 'src/worldatlas/map_build/physical/union.py'
        capture_source = runtime.capture_source

        def capture_with_edit(package):
            snapshot = capture_source(package)
            content = source_files(snapshot)[source_path]
            snapshot['files'][source_path] = b64encode(content + marker).decode('ascii')
            return snapshot

        with mock.patch.object(runtime, 'capture_source', side_effect=capture_with_edit):
            report = b.run(self.config, out, resume=True)
        self.assertEqual(report['status'], 'candidate-only')
        self.assertEqual(pin_file(shard_path), initial_shard)
        second_attempt, = set((out / 'attempts').iterdir()) - {first_attempt}
        archived = []
        for attempt in (first_attempt, second_attempt):
            archive = attempt / 'source-code.json.gz'
            producer = json.loads((attempt / 'producer.json').read_text())
            self.assertEqual(producer['source_archive'], pin_file(archive))
            archived.append(source_files(read_source(archive))[source_path])
        self.assertEqual(archived[1], archived[0] + marker)

    def test_completed_resume_revalidates_shard_inventory(self):
        out = self.root / 'finished'
        b.run(self.config, out)
        (out / 'shards/00000/water.tif').write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError, 'completed stage output changed: physical-shard-00000|checkpoint/input hash mismatch: .*water.tif'):
            b.run(self.config, out, resume=True)

    def test_completed_resume_validates_the_report_masks_and_final_streams(self):
        out = self.root / 'finished'
        original = b.run(self.config, out)
        for name, message in (
            ('report.json', 'completed stage output changed: physical-report'),
            ('land/land.tif', 'completed stage output changed: physical-land|checkpoint/input hash mismatch: .*land.tif'),
            ('union/water-union.tif', 'completed stage output changed: physical-union|checkpoint/input hash mismatch: .*water-union.tif'),
            ('physical/runs.u32le', 'completed stage output changed: physical-compose|checkpoint/input hash mismatch: .*runs.u32le'),
        ):
            with self.subTest(name=name):
                path = out / name
                content = path.read_bytes()
                path.write_bytes(b'{}')
                try:
                    with self.assertRaisesRegex(ValueError, message):
                        b.run(self.config, out, resume=True)
                finally:
                    path.write_bytes(content)
        resumed = b.run(self.config, out, resume=True)
        self.assertEqual(resumed['physical_output_sha256'], original['physical_output_sha256'])

    def test_resume_rejects_shards_from_different_rasterizer_versions(self):
        first = self.raw / 'water.parquet'
        second = self.raw / 'second.parquet'
        table = pq.read_table(first).replace_schema_metadata(
            pq.read_schema(first).metadata | {b'edition': b'second'}
        )
        pq.write_table(table, second)
        _, cached_second = self.set_water_sources(first, second)
        self.cfg['max_parallel_shards'] = 1
        self.config.write_text(json.dumps(self.cfg))
        output = self.root / 'mixed'

        def interrupt_second_shard(function, *args, **kwargs):
            if function is WATER and args[0] == cached_second:
                raise InterruptedError('second shard interrupted')
            return function(*args, **kwargs)

        with intercept_stages(interrupt_second_shard):
            with self.assertRaisesRegex(InterruptedError, 'second shard interrupted'):
                b.run(self.config, output)
        checkpoints = output / 'checkpoints'
        first_checkpoint = checkpoints / 'physical-shard-00000/complete.json'
        first_receipt = first_checkpoint.read_bytes()
        second_checkpoint = checkpoints / 'physical-shard-00001/complete.json'
        self.assertFalse(second_checkpoint.exists())

        previous_pin = RunFilePins.pin
        rasterizer_path = Path(b.water.__file__).resolve()

        def pin_new_rasterizer(files, path):
            pin = previous_pin(files, path)
            if Path(pin['path']) == rasterizer_path:
                return dict(pin, sha256='f' * 64)
            return pin

        message = 'inconsistent water shard rasterizers or kernels'
        with mock.patch.object(RunFilePins, 'pin', pin_new_rasterizer):
            with self.assertRaisesRegex(ValueError, message):
                b.run(self.config, output, resume=True)
        self.assertEqual(first_checkpoint.read_bytes(), first_receipt)
        self.assertTrue(second_checkpoint.exists())
        self.assertFalse((output / 'union').exists())

        with intercept_stages(AssertionError('unexpected rebuild')):
            with self.assertRaisesRegex(ValueError, message):
                b.run(self.config, output, resume=True)

    def test_completed_resume_revalidates_gdal_kernel_report(self):
        out = self.root / 'finished-gdal'
        b.run(self.config, out)
        path = out / 'shards/00000/report.json'
        report = json.loads(path.read_bytes())
        report['gdal_kernel']['binding_sha256'] = '0' * 64
        path.write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError, 'completed stage output changed: physical-shard-00000|checkpoint/input hash mismatch: .*shards/00000/report.json'):
            b.run(self.config, out, resume=True)

    def test_complete_physical_stage_does_not_start_processes(self):
        with (
            mock.patch.object(runtime, 'repository_identity', return_value=None),
            mock.patch.object(
                subprocess, 'Popen', side_effect=AssertionError('unexpected subprocess')
            ),
        ):
            report = b.run(self.config, self.root / 'in-process')
        self.assertEqual(report['status'], 'candidate-only')
        self.assertFalse(list((self.root / 'in-process').rglob('*.so')))

    def test_resume_quarantines_incomplete_unit(self):
        out = self.root / 'partial'

        def stage(name, *args, **kwargs):
            if name == WATER:
                destination = Path(args[2])
                destination.mkdir()
                (destination / 'partial').write_text('preserve')
                raise ValueError('partial shard')
            return name(*args, **kwargs)

        with intercept_stages(stage):
            with self.assertRaisesRegex(ValueError, 'partial shard'):
                b.run(self.config, out)
        b.run(self.config, out, resume=True)
        self.assertEqual(
            [p.read_text() for p in (out / 'preserved').glob('physical-shard-00000-*/0-00000/partial')], ['preserve']
        )

    def test_resume_reuses_union_after_composition_failure(self):
        out = self.root / 'union-resume'

        def fail_compose(name, *args, **kwargs):
            if name == COMPOSE:
                raise ValueError('composition interrupted')
            return name(*args, **kwargs)

        with intercept_stages(fail_compose):
            with self.assertRaisesRegex(ValueError, 'composition interrupted'):
                b.run(self.config, out)
        seen = []

        def stage(name, *args, **kwargs):
            seen.append(name)
            return name(*args, **kwargs)

        with intercept_stages(stage):
            b.run(self.config, out, resume=True)
        self.assertEqual(seen, [COMPOSE])

    def test_resume_rejects_changed_settings_for_an_unfinished_task(self):
        out = self.root / 'union-settings'
        self.interrupt_before_union(out)
        (out / 'configs/union.json').write_bytes(b'{}')
        with self.assertRaisesRegex(
            ValueError, r'saved build settings differ: .*union\.json'
        ):
            b.run(self.config, out, resume=True)

    def test_resume_after_report_write_failure_reuses_composition(self):
        out = self.root / 'report-resume'

        def fail_report(path, value, *, sort_keys):
            if Path(path) == out / 'report.json':
                raise ValueError('report interrupted')
            return write_json(path, value, sort_keys=sort_keys)

        with mock.patch.object(b, 'write_json', side_effect=fail_report):
            with self.assertRaisesRegex(ValueError, 'report interrupted'):
                b.run(self.config, out)
        with intercept_stages(AssertionError('unexpected rebuild')):
            for name, message in (
                ('configs/land.json', 'checkpoint/input hash mismatch'),
                ('land/report.json', 'completed stage output changed: physical-land'),
                ('configs/union.json', 'checkpoint/input hash mismatch'),
                ('union/report.json', 'completed stage output changed: physical-union'),
                ('physical/runs.u32le', 'completed stage output changed: physical-compose'),
            ):
                with self.subTest(name=name):
                    path = out / name
                    content = path.read_bytes()
                    path.write_bytes(b'{}')
                    with self.assertRaisesRegex(ValueError, message):
                        b.run(self.config, out, resume=True)
                    path.write_bytes(content)
            b.run(self.config, out, resume=True)
        self.assertTrue((out / 'report.json').is_file())

    def test_config_changes_during_processing_leave_run_incomplete(self):
        for path, message in (
            (self.config, 'checkpoint/input hash mismatch'),
            (Path('configs/land.json'), 'checkpoint/input hash mismatch'),
        ):
            with self.subTest(path=path):
                output = self.root / ('changed-' + path.name)
                target = path if path.is_absolute() else output / path
                content = path.read_bytes() if path.is_absolute() else None

                def mutate_after_composing(function, *args, **kwargs):
                    result = function(*args, **kwargs)
                    if function == COMPOSE:
                        target.write_bytes(target.read_bytes() + b'\n')
                    return result
                with intercept_stages(mutate_after_composing):
                    with self.assertRaisesRegex(ValueError, message):
                        b.run(self.config, output)
                self.assertFalse((output / 'report.json').exists())
                if content is not None:
                    path.write_bytes(content)

    def test_r2_download_is_verified_timed_and_reused_by_next_build(self):
        shard = self.raw / 'water.parquet'
        content = shard.read_bytes()
        self.cfg['max_parallel_shards'] = 1
        self.config.write_text(json.dumps(self.cfg))
        self.cached_water.unlink()
        shard.unlink()
        out = self.root / 'staged'
        client = mock.Mock()

        def download(**kwargs):
            self.assertEqual(
                kwargs, {'Bucket': 'test-bucket', 'Key': 'water.parquet'}
            )
            time.sleep(0.05)
            return {'Body': io.BytesIO(content), 'ContentLength': len(content)}

        client.get_object.side_effect = download
        with mock.patch.object(
            r2, 'make_r2_client', return_value=R2Client(client)
        ) as make_client:
            report = b.run(self.config, out)
            make_client.assert_called_once_with()
        client.get_object.assert_called_once()
        client.close.assert_called_once()
        self.assertEqual(report['downloaded_shard_count'], 1)
        self.assertGreaterEqual(report['source_download_elapsed_seconds'], 0.05)
        self.assertGreaterEqual(report['processing_elapsed_seconds'], 0)
        self.assertFalse((out / 'source-staging' / shard.name).exists())
        self.assertFalse(shard.exists())
        self.assertEqual(
            report['physical_output_sha256']['runs.u32le'],
            sha256_file(out / 'physical/runs.u32le'),
        )
        cached = self.cached_water
        self.assertEqual(cached.read_bytes(), content)
        local = self.root / 'warm-cache'
        with mock.patch.object(r2, 'make_r2_client', return_value=R2Client(client)):
            client.get_object.reset_mock()
            b.run(self.config, local)
            client.get_object.assert_not_called()
        self.assertEqual(cached.read_bytes(), content)
        self.assertEqual(
            json.loads((local / 'report.json').read_text())['downloaded_shard_count'], 0
        )
        self.assertEqual(
            sha256_file(local / 'physical/runs.u32le'),
            sha256_file(out / 'physical/runs.u32le'),
        )

    def test_cold_cache_allows_parallel_downloads_and_rasterization(self):
        first = self.raw / 'water.parquet'
        second = self.raw / 'other' / first.name
        second.parent.mkdir()
        table = pq.read_table(first)
        row = {**table.to_pylist()[0], 'id': 'second-lake'}
        pq.write_table(
            pa.Table.from_pylist([row]).replace_schema_metadata(table.schema.metadata),
            second,
        )
        files = [
            r2_file_pin(path, key=path.relative_to(self.raw).as_posix())
            for path in (first, second)
        ]
        payloads = {
            source['r2_key']: path.read_bytes()
            for source, path in zip(files, (first, second), strict=True)
        }
        cached_paths = [
            cache_fixture_file(self.cache, path, source)
            for path, source in zip((first, second), files, strict=True)
        ]
        self.cfg['inland_water'].update(file_count=len(files), files=files)
        self.cfg['max_parallel_shards'] = 1
        self.config.write_text(json.dumps(self.cfg))
        serial = b.run(self.config, self.root / 'serial')
        for path in cached_paths:
            path.unlink()

        self.cfg['max_parallel_shards'] = 2
        self.config.write_text(json.dumps(self.cfg))
        downloads_started = threading.Barrier(2)
        rasterizations_started = threading.Barrier(2)
        first_rasterization_started = threading.Event()

        def get_object(*, Bucket, Key):
            self.assertEqual(Bucket, 'test-bucket')
            downloads_started.wait(timeout=10)
            if Key == files[1]['r2_key']:
                self.assertTrue(first_rasterization_started.wait(timeout=10))
            data = payloads[Key]
            return dict(Body=io.BytesIO(data), ContentLength=len(data))

        def verify_rasterization_order(function, *args, **kwargs):
            if function is WATER:
                shard_index = int(Path(args[2]).name)
                self.assertEqual(args[0].read_bytes(), payloads[files[shard_index]['r2_key']])
                if shard_index == 0:
                    first_rasterization_started.set()
                rasterizations_started.wait(timeout=10)
            return function(*args, **kwargs)

        client = mock.Mock()
        client.get_object.side_effect = get_object
        output = self.root / 'parallel'
        with (
            mock.patch.object(
                r2, 'make_r2_client', return_value=R2Client(client)
            ) as make_client,
            intercept_stages(verify_rasterization_order),
        ):
            parallel = b.run(self.config, output)
        make_client.assert_called_once_with()
        client.close.assert_called_once_with()
        self.assertEqual(parallel['downloaded_shard_count'], 2)
        self.assertEqual(
            parallel['physical_output_sha256'], serial['physical_output_sha256']
        )
        for entry, cached_path in zip(files, cached_paths, strict=True):
            self.assertEqual(
                cached_path.read_bytes(),
                payloads[entry['r2_key']],
            )

    def test_r2_bad_hash_is_discarded_and_retry_can_resume(self):
        shard = self.raw / 'water.parquet'
        content = shard.read_bytes()
        self.cfg['max_parallel_shards'] = 1
        self.config.write_text(json.dumps(self.cfg))
        self.cached_water.unlink()
        out = self.root / 'bad-staged'
        client = mock.Mock()
        client.get_object.return_value = {
            'Body': io.BytesIO(b'X' + content[1:]),
            'ContentLength': len(content),
        }
        with mock.patch.object(r2, 'make_r2_client', return_value=R2Client(client)):
            with self.assertRaisesRegex(ValueError, 'size or hash mismatch'):
                b.run(self.config, out)
        client.close.assert_called_once_with()
        cached = self.cached_water
        self.assertFalse(cached.exists())
        self.assertEqual(list(self.cache.rglob('download-*')), [])
        self.assertFalse((out / 'report.json').exists())
        client.get_object.return_value = {
            'Body': io.BytesIO(content),
            'ContentLength': len(content),
        }
        with mock.patch.object(r2, 'make_r2_client', return_value=R2Client(client)):
            b.run(self.config, out, resume=True)
        self.assertEqual(cached.read_bytes(), content)

    def test_end_to_end_without_reference(self):
        out = self.root / 'out'
        result = subprocess.run(
            [
                sys.executable,
                '-m',
                'worldatlas.map_build.physical.build',
                str(self.config),
                str(out),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        lines = result.stdout.splitlines()
        report = json.loads("\n".join(lines[lines.index("{") :]))
        self.assertEqual(report['status'], 'candidate-only')
        self.assertEqual(report['directory'], str(out / 'physical'))
        self.assertEqual(
            json.loads((out / 'report.json').read_text())['directory'],
            report['directory'],
        )
        self.assertEqual(report['shard_count'], 1)
        self.assertGreaterEqual(report['processing_elapsed_seconds'], 0)
        self.assertEqual(
            report['physical_output_sha256']['rows.u32le'],
            sha256_file(out / 'physical/rows.u32le'),
        )
        expected = np.zeros((4, 8), dtype=np.uint8)
        expected[:2, :3] = 1
        expected[0, 0] = 0
        np.testing.assert_array_equal(
            gdal.Open(str(out / 'physical/physical-dry.tif')).ReadAsArray(), expected
        )
        rows = np.fromfile(out / 'physical/rows.u32le', dtype='<u4')
        runs = np.fromfile(out / 'physical/runs.u32le', dtype='<u4').reshape(-1, 2)
        self.assertEqual(rows.tolist(), [0, 3, 5, 6, 7])
        self.assertEqual(
            runs.tolist(), [[1, 1], [3, 17], [8, 1], [3, 17], [8, 1], [8, 1], [8, 1]]
        )
        self.assertNotIn(
            'historic_dry_cells', json.loads((out / 'physical/report.json').read_text())
        )
        for stage in ('union', 'physical'):
            self.assertFalse((out / stage / 'mismatch-spans.jsonl').exists())

    def test_parallel_shards_match_serial_and_bad_worker_count_fails(self):
        first = self.raw / 'water.parquet'
        table = pq.read_table(first)
        row = table.to_pylist()[0]
        row['id'] = 'second-lake'
        second = self.raw / 'second.parquet'
        pq.write_table(
            pa.Table.from_pylist([row]).replace_schema_metadata(table.schema.metadata), second
        )
        self.set_water_sources(first, second)
        self.cfg['max_parallel_shards'] = 0
        self.config.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError, 'max_parallel_shards'):
            b.run(self.config, self.root / 'bad-workers')
        self.assertFalse((self.root / 'bad-workers').exists())
        self.cfg['max_parallel_shards'] = 1
        self.config.write_text(json.dumps(self.cfg))
        serial = self.root / 'serial'
        b.run(self.config, serial)
        self.cfg['max_parallel_shards'] = 2
        self.config.write_text(json.dumps(self.cfg))
        parallel = self.root / 'parallel'
        b.run(self.config, parallel)
        self.assertEqual(
            sha256_file(serial / 'physical/physical-dry.tif'),
            sha256_file(parallel / 'physical/physical-dry.tif'),
        )
        self.assertEqual(
            sha256_file(serial / 'physical/rows.u32le'), sha256_file(parallel / 'physical/rows.u32le')
        )
        self.assertEqual(
            sha256_file(serial / 'physical/runs.u32le'), sha256_file(parallel / 'physical/runs.u32le')
        )
        self.assertEqual(
            sha256_file(serial / 'union/water-union.tif'), sha256_file(parallel / 'union/water-union.tif')
        )
        self.assertEqual(
            json.loads((parallel / 'report.json').read_text())['max_parallel_shards'], 2
        )
        self.cfg.pop('max_parallel_shards')
        self.config.write_text(json.dumps(self.cfg))
        defaulted = self.root / 'default-parallel'
        b.run(self.config, defaulted)
        self.assertEqual(
            sha256_file(serial / 'physical/physical-dry.tif'),
            sha256_file(defaulted / 'physical/physical-dry.tif'),
        )
        self.assertEqual(
            sha256_file(serial / 'physical/rows.u32le'), sha256_file(defaulted / 'physical/rows.u32le')
        )
        self.assertEqual(
            sha256_file(serial / 'physical/runs.u32le'), sha256_file(defaulted / 'physical/runs.u32le')
        )
        self.assertEqual(
            sha256_file(serial / 'union/water-union.tif'), sha256_file(defaulted / 'union/water-union.tif')
        )
        self.assertEqual(
            json.loads((defaulted / 'report.json').read_text())['max_parallel_shards'], 2
        )
        # No arbitrary worker ceiling: the actual pool is naturally limited by
        # the number of independent shards, even when configuration is larger.
        self.cfg['max_parallel_shards'] = 10000
        self.config.write_text(json.dumps(self.cfg))
        oversized = self.root / 'oversized-worker-setting'
        b.run(self.config, oversized)
        self.assertEqual(
            sha256_file(serial / 'physical/physical-dry.tif'),
            sha256_file(oversized / 'physical/physical-dry.tif'),
        )
        self.assertEqual(
            sha256_file(serial / 'physical/rows.u32le'), sha256_file(oversized / 'physical/rows.u32le')
        )
        self.assertEqual(
            sha256_file(serial / 'physical/runs.u32le'), sha256_file(oversized / 'physical/runs.u32le')
        )
        self.assertEqual(
            sha256_file(serial / 'union/water-union.tif'), sha256_file(oversized / 'union/water-union.tif')
        )
        self.assertEqual(
            json.loads((oversized / 'report.json').read_text())['max_parallel_shards'], 10000
        )

    def test_parallel_incomplete_shard_fails_before_union(self):
        first = self.raw / 'water.parquet'
        table = pq.read_table(first)
        row = table.to_pylist()[0]
        row['id'] = 'bad'
        row['subtype'] = None
        bad = self.raw / 'bad.parquet'
        pq.write_table(
            pa.Table.from_pylist([row]).replace_schema_metadata(table.schema.metadata), bad
        )
        self.set_water_sources(first, bad)
        self.cfg['max_parallel_shards'] = 2
        self.config.write_text(json.dumps(self.cfg))
        out = self.root / 'parallel-incomplete'
        with self.assertRaisesRegex(ValueError, 'incomplete water shard'):
            b.run(self.config, out)
        self.assertFalse((out / 'union').exists())
        self.assertFalse((out / 'report.json').exists())

    def test_worker_failure_cancels_other_worker_between_batches_and_can_resume(self):
        shard = self.raw / 'water.parquet'
        table = pq.read_table(shard)
        pq.write_table(pa.concat_tables([table] * 3), shard)
        second = self.raw / 'second.parquet'
        pq.write_table(table, second)
        _, cached_second = self.set_water_sources(shard, second)
        self.cfg['inland_water']['batch_size'] = 1
        self.cfg['max_parallel_shards'] = 2
        self.config.write_text(json.dumps(self.cfg))
        out = self.root / 'cancelled'
        seen = []
        first_batch = threading.Event()

        with b.control.stage() as cancelled:
            def hold_at_first_batch(message, **_):
                seen.append(json.loads(message)['rows'])
                first_batch.set()
                self.assertTrue(cancelled.wait(timeout=10))

            def fail_second_worker(function, *args, **kwargs):
                if function is WATER:
                    if args[0] == cached_second:
                        self.assertTrue(first_batch.wait(timeout=10))
                        raise ValueError('second water worker failed')
                    kwargs['emit'] = hold_at_first_batch
                return function(*args, **kwargs)

            with intercept_stages(fail_second_worker):
                with self.assertRaisesRegex(ValueError, 'second water worker failed'):
                    b.run(self.config, out)

        self.assertEqual(seen, [1])
        self.assertTrue((out / 'land/report.json').is_file())
        self.assertFalse((out / 'shards/00000/report.json').exists())
        self.assertFalse((out / 'union').exists())
        b.run(self.config, out, resume=True)
        uninterrupted = self.root / 'uninterrupted'
        b.run(self.config, uninterrupted)
        for name in ('rows.u32le', 'runs.u32le'):
            self.assertEqual(
                sha256_file(out / 'physical' / name),
                sha256_file(uninterrupted / 'physical' / name),
            )

    def test_incomplete_water_cannot_publish_pipeline_report(self):
        shard = self.raw / 'water.parquet'
        table = pq.read_table(shard)
        rows = table.to_pylist()
        item = dict(rows[0])
        item['id'] = 'unclassified'
        item['subtype'] = None
        rows.append(item)
        revised = pa.Table.from_pylist(rows).replace_schema_metadata(table.schema.metadata)
        pq.write_table(revised, shard)
        self.set_water_sources(shard)
        self.config.write_text(json.dumps(self.cfg))
        out = self.root / 'incomplete'
        with self.assertRaisesRegex(ValueError, 'incomplete water shard'):
            b.run(self.config, out)
        report = json.loads((out / 'shards/00000/report.json').read_text())
        self.assertEqual(report['status'], 'incomplete-input-issues')
        self.assertEqual(report['counts']['missing_classification'], 1)
        self.assertFalse((out / 'checkpoints/physical-shard-00000/complete.json').exists())
        self.assertFalse((out / 'report.json').exists())
        self.assertFalse((out / 'physical').exists())

    def test_standalone_configuration_rejects_direct_local_inputs(self):
        coastline = self.cfg['land_config']['land'][0]
        inland_water = self.cfg['inland_water']
        for settings, cached_path, section in (
            (coastline, self.cached_coastline, 'land_config.land.0'),
            (inland_water, self.cached_water, 'inland_water'),
        ):
            with self.subTest(section=section):
                original = settings['files']
                settings['files'] = [pin_file(cached_path)]
                self.config.write_text(json.dumps(self.cfg))
                out = self.root / 'direct-input'
                with self.assertRaisesRegex(ValueError, f'{section}.files.0'):
                    b.run(self.config, out)
                self.assertFalse(out.exists())
                settings['files'] = original

    def test_physical_output_cannot_contain_its_configuration(self):
        out = self.root / 'overlap'
        out.mkdir()
        config = write_json(out / 'config.json', self.cfg)
        with self.assertRaisesRegex(
            ValueError, 'physical output must not contain its configuration'
        ):
            b.run(config, out, resume=True)
        self.assertFalse((out / 'land').exists())

    def test_requires_a_valid_output_location_and_current_land_input(self):
        with self.assertRaisesRegex(ValueError, 'output must have an existing parent'):
            b.run(self.config, self.root / 'missing' / 'output')
        for output in (self.cache / 'output', self.root):
            with self.subTest(output=output):
                with self.assertRaisesRegex(ValueError, 'input cache must use separate directories'):
                    b.run(self.config, output)
        self.cached_coastline.write_text('{}')
        out = self.root / 'changed-input'
        with self.assertRaisesRegex(ValueError, 'source file size or hash mismatch'):
            b.run(self.config, out)
        self.assertFalse((out / 'land').exists())

    def test_coastline_dataset_must_name_one_pinned_file(self):
        layer = self.cfg['land_config']['land'][0]
        dataset, files = layer['dataset'], layer['files']
        for i, (name, pins) in enumerate((('missing.geojson', files), (dataset, files * 2))):
            output = self.root / f'invalid-dataset-{i}'
            with self.subTest(name=name, files=pins):
                layer.update(dataset=name, files=pins)
                self.config.write_text(json.dumps(self.cfg))
                with self.assertRaisesRegex(ValueError, 'must name exactly one entry in files'):
                    b.run(self.config, output)
                self.assertFalse((output / 'land').exists())

    def test_physical_preflight_checks_available_disk_and_reports_cli_errors(self):
        self.cfg['minimum_free_bytes'] = 1
        self.config.write_text(json.dumps(self.cfg))
        out = self.root / 'low-disk'
        with mock.patch.object(b.shutil, 'disk_usage', return_value=mock.Mock(free=0)):
            with self.assertRaisesRegex(ValueError, 'free disk below pipeline reserve'):
                b.run(self.config, out)
        self.assertFalse((out / 'land').exists())

        self.config.write_text('{}')
        out = self.root / 'invalid-config'
        result = subprocess.run(
            [
                sys.executable,
                '-m',
                'worldatlas.map_build.physical.build',
                str(self.config),
                str(out),
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('validation errors for PhysicalConfiguration', result.stderr)
        self.assertFalse((out / 'land').exists())

    def test_interrupted_physical_checkpoints_require_their_journal(self):
        out = self.root / 'interrupted'
        self.interrupt_before_union(out)
        (out / 'timing-events.jsonl').unlink()
        with self.assertRaises(FileNotFoundError):
            b.run(self.config, out, resume=True)
        self.assertFalse((out / 'report.json').exists())

    def test_resume_reuses_the_verified_cache_after_interruption(self):
        shard = self.raw / 'water.parquet'
        payload = shard.read_bytes()
        out = self.root / 'restart-r2'
        cached = self.cached_water
        cached.unlink()
        client = mock.Mock()
        client.get_object.return_value = {'Body': io.BytesIO(payload)}

        def interrupt_before_burn(function, *args, **kwargs):
            if function == WATER:
                raise InterruptedError('before burning the shard')
            return function(*args, **kwargs)

        with (
            mock.patch.object(r2, 'make_r2_client', return_value=R2Client(client)),
            intercept_stages(interrupt_before_burn),
        ):
            with self.assertRaisesRegex(InterruptedError, 'before burning'):
                b.run(self.config, out)
        self.assertEqual(cached.read_bytes(), payload)

        with mock.patch.object(r2, 'make_r2_client', return_value=R2Client(client)):
            client.get_object.reset_mock()
            self.assertEqual(
                b.run(self.config, out, resume=True)['status'], 'candidate-only'
            )
            client.get_object.assert_not_called()
        self.assertEqual(cached.read_bytes(), payload)

    def test_preflight_rejects_retired_comparison_fields(self):
        out = self.root / 'bad'
        self.cfg['physical_reference_mask'] = pin_file(self.cached_coastline)
        self.config.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError, 'physical_reference_mask'):
            b.run(self.config, out)
        self.assertFalse(out.exists())

    def test_preflight_rejects_invalid_grid_sources_and_controls(self):
        valid_water = self.cfg['inland_water']
        shard = valid_water['files'][0]
        cases = [
            ('pipeline', {'selection_notes': 'Retired duplicate'}, 'selection_notes'),
            ('water', {'selection_notes': '\t\u00a0\u3000'}, 'selection_notes'),
            ('pipeline', {'minimum_free_bytes': True}, 'minimum_free_bytes'),
            ('pipeline', {'union_rows_per_block': 0}, 'rows_per_block'),
            ('water', {'rasterizer': 'unknown'}, 'inland_water.rasterizer'),
            (
                'water',
                {'policy': {'method': b.water.INLAND_WATER_SUBTYPE_POLICY}},
                r'inland_water\.policy',
            ),
            ('water', {'native_method': 'old'}, 'native_method'),
            (
                'pipeline',
                {'grid': dict(self.grid, width=4)},
                'expected an aligned global',
            ),
            ('water', {'batch_size': 0}, 'batch_size'),
            ('water', {'file_count': 2}, 'must list every raw shard'),
            ('pipeline', {'minimum_free_byte': 1}, 'minimum_free_byte'),
            (
                'water',
                {'files': [dict(shard, sha256='not-a-digest')]},
                'inland_water.files.0',
            ),
            (
                'water',
                {'files': [dict(shard, size_bytes=-1)]},
                r'inland_water.files.0.size_bytes',
            ),
            (
                'water',
                {
                    'file_count': 2,
                    'files': [shard, dict(shard, r2_key='another.parquet')],
                },
                'source hashes must be unique',
            ),
        ]
        for i, (section, changes, error) in enumerate(cases):
            out = self.root / f'invalid-{i}'
            with self.subTest(section=section, changes=changes):
                water = dict(valid_water)
                configuration = dict(self.cfg)
                {'pipeline': configuration, 'water': water}[section].update(changes)
                configuration['inland_water'] = water
                self.config.write_text(json.dumps(configuration))
                with self.assertRaisesRegex(ValueError, error):
                    b.run(self.config, out)
                self.assertFalse((out / 'land').exists())



if __name__ == '__main__':
    unittest.main()
