from functools import partial
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
from worldatlas.map_build.physical import build as b
from worldatlas.shared.files import sha256_file, write_json


LAND = b.land.run
WATER = b.water.run
UNION = b.water_union.run
COMPOSE = b.composition.main


@contextmanager
def intercept_stages(effect):
    """Observe or interrupt a real stage without changing the production runner."""
    with ExitStack() as stack:
        for module, name, original in (
            (b.land, 'run', LAND), (b.water, 'run', WATER),
            (b.water_union, 'run', UNION), (b.composition, 'main', COMPOSE),
        ):
            side_effect = partial(effect, original) if callable(effect) else effect
            stack.enter_context(mock.patch.object(module, name, side_effect=side_effect))
        yield


class PipelineTests(unittest.TestCase):
    def test_interrupted_parallel_units_use_wall_time_union(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            j = b.ProcessingJournal(root, 20, False)
            j.add({'event': 'attempt_start', 'attempt': 'old'})
            for start, end in ((0, 10), (5, 15)):
                j.add(
                    {
                        'event': 'unit_complete',
                        'attempt': 'old',
                        'unit': 'test',
                        'start_monotonic_seconds': start,
                        'end_monotonic_seconds': end,
                        'processing_elapsed_seconds': end - start,
                    }
                )
            with mock.patch.object(b.time, 'monotonic', return_value=23):
                j.finish('complete')
            r = j.summary()
            self.assertFalse(r['timing_complete'])
            self.assertIsNone(r['processing_elapsed_seconds'])
            self.assertEqual(r['recorded_processing_elapsed_seconds'], 18)

    def test_overlapping_transfers_and_processing_share_wall_time(self):
        with tempfile.TemporaryDirectory() as temp:
            journal = b.ProcessingJournal(Path(temp), time.monotonic(), False)
            for attempt in ('interrupted', 'older'):
                journal.add(dict(event='attempt_start', attempt=attempt))
            for start, end in ((0, 8), (2, 16)):
                journal.add(
                    dict(
                        event='download_complete',
                        attempt='interrupted',
                        seconds=end - start,
                        start_monotonic_seconds=start,
                        end_monotonic_seconds=end,
                    )
                )
            journal.add(dict(event='download_complete', attempt='older', seconds=2))
            for start, end in ((5, 15), (10, 25)):
                journal.add(
                    dict(
                        event='unit_complete',
                        attempt='interrupted',
                        start_monotonic_seconds=start,
                        end_monotonic_seconds=end,
                    )
                )
            journal.finish('complete')
            self.assertEqual(journal.recorded_time('interrupted'), (20, 5))
            self.assertEqual(journal.summary()['source_download_elapsed_seconds'], 7)

    def test_corrupt_processing_journal_is_rejected(self):
        for change, message in (
            (
                [dict(event='unknown', attempt='current')],
                'unknown processing journal event',
            ),
            (
                [dict(event='attempt_start', attempt='current')],
                'invalid processing journal attempts',
            ),
            (
                [dict(event='download_complete', attempt='missing', seconds=1)],
                'event without attempt',
            ),
            (
                [
                    dict(event='attempt_start', attempt='older'),
                    dict(event='download_complete', attempt='older', seconds=-1),
                ],
                'invalid processing journal download duration',
            ),
            (
                [
                    dict(event='attempt_start', attempt='interrupted'),
                    dict(
                        event='unit_complete',
                        attempt='interrupted',
                        start_monotonic_seconds=2,
                        end_monotonic_seconds=1,
                    ),
                ],
                'invalid processing interval',
            ),
        ):
            with self.subTest(message=message), tempfile.TemporaryDirectory() as temp:
                journal = b.ProcessingJournal(Path(temp), time.monotonic(), False)
                for record in change:
                    journal.add(
                        dict(
                            record,
                            attempt=journal.attempt
                            if record['attempt'] == 'current'
                            else record['attempt'],
                        )
                    )
                journal.finish('complete')
                with self.assertRaisesRegex(ValueError, message):
                    journal.summary()

    def test_closing_attempt_twice_or_with_bad_duration_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            journal = b.ProcessingJournal(
                Path(temp), time.monotonic() + 1_000_000, False
            )
            with self.assertRaisesRegex(ValueError, 'invalid attempt timing'):
                journal.finish('complete')
            journal.started = time.monotonic()
            journal.finish('complete')
            with self.assertRaisesRegex(ValueError, 'attempt already ended'):
                journal.finish('failed')

    def test_invalid_attempt_end_record_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            journal = b.ProcessingJournal(Path(temp), time.monotonic(), False)
            journal.finish('complete')
            entry = journal.events[-1]
            entry['status'] = 'unknown'
            with self.assertRaisesRegex(
                ValueError, 'invalid processing journal status'
            ):
                journal.summary()
            entry['status'] = 'complete'
            entry['processing_elapsed_seconds'] = -1
            with self.assertRaisesRegex(
                ValueError, 'invalid processing journal duration'
            ):
                journal.summary()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.config_dir = self.root / 'configs'
        self.config_dir.mkdir()
        self.land_dir = self.root / 'land-input'
        self.land_dir.mkdir()
        self.raw = self.root / 'raw'
        self.raw.mkdir()
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
        land_cfg = {
            'schema': 'land-raster-candidate-v1',
            'selection_notes': 'synthetic',
            'strip_rows': 2,
            'land': [
                {
                    'dataset': str(land),
                    'where': None,
                    'files': [{'path': str(land), 'sha256': sha256_file(land)}],
                }
            ],
        }
        self.land_cfg = self.config_dir / 'land.json'
        self.land_cfg.write_text(json.dumps(land_cfg))
        water_cfg = {
            'schema': 'water-shard-candidate-v2',
            'tile_size': 4,
            'selection_notes': 'synthetic',
            'policy': {'method': 'overture-inland-subtype-v1'},
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
        source = self.source_manifest = self.raw / 'manifest.json'
        source.write_text(
            json.dumps(
                {
                    'file_count': 1,
                    'files': [{'path': 'water.parquet', 'sha256': sha256_file(shard)}],
                }
            )
        )
        self.cfg = {
            'schema': 'raw-physical-pipeline-v3',
            'selection_notes': 'synthetic',
            'minimum_free_bytes': 0,
            'source_directory': str(self.raw),
            'land_config': land_cfg,
            'grid': self.grid,
            'inland_water': {**water_cfg, **json.loads(source.read_text())},
        }
        self.config = self.config_dir / 'pipeline.json'
        self.config.write_text(json.dumps(self.cfg))

    def tearDown(self):
        self.tmp.cleanup()

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
            b.run(self.config, out, resume=True)
        report = json.loads((out / 'report.json').read_text())
        self.assertTrue(report['timing_complete'])
        self.assertGreater(report['processing_elapsed_seconds'], 0)
        self.assertNotIn(LAND, seen)
        self.assertNotIn(WATER, seen)
        self.assertEqual(b.run(self.config, out, resume=True), report)

    def test_concurrent_attempt_is_rejected(self):
        out = self.root / 'locked'
        lock = self.root / 'locked.lock'
        with lock.open('w') as f:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(ValueError, 'another pipeline runner'):
                b.run(self.config, out)
        self.assertFalse(out.exists())

    def test_resume_before_journal_creation_marks_timing_incomplete(self):
        out = self.root / 'early-interruption'
        with mock.patch.object(b, 'ProcessingJournal', side_effect=OSError('journal interrupted')):
            with self.assertRaisesRegex(OSError, 'journal interrupted'):
                b.run(self.config, out)
        report = b.run(self.config, out, resume=True)
        self.assertFalse(report['timing_complete'])
        self.assertIsNone(report['processing_elapsed_seconds'])

    def test_resume_hard_interruption_reports_unknown_total(self):
        out = self.root / 'crashed'
        self.interrupt_before_union(out)
        journal = out / 'processing-events.jsonl'
        lines = journal.read_text().splitlines()
        self.assertEqual(json.loads(lines[-1])['event'], 'attempt_end')
        journal.write_text('\n'.join(lines[:-1]) + '\n{"event":')
        b.run(self.config, out, resume=True)
        report = json.loads((out / 'report.json').read_text())
        self.assertFalse(report['timing_complete'])
        self.assertIsNone(report['processing_elapsed_seconds'])
        self.assertGreater(report['recorded_processing_elapsed_seconds'], 0)
        self.assertEqual(
            [p.read_text() for p in (out / 'interrupted').glob('journal-tail-*')], ['{"event":']
        )

    def test_actual_kill_preserves_units_and_marks_timing_incomplete(self):
        out = self.root / 'actual-kill'
        marker = self.root / 'waiting'
        code = """from worldatlas.map_build.physical import build as b
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
        b.run(self.config, out, resume=True)
        report = json.loads((out / 'report.json').read_text())
        self.assertFalse(report['timing_complete'])
        self.assertIsNone(report['processing_elapsed_seconds'])
        self.assertGreater(report['recorded_processing_elapsed_seconds'], 0)

    def test_resume_rejects_tampered_checkpoint_and_input(self):
        out = self.root / 'tampered'
        self.interrupt_before_union(out)
        (out / 'shards/00000/water.tif').write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError, 'shard checkpoint mismatch'):
            b.run(self.config, out, resume=True)
        self.cfg['selection_notes'] = 'changed'
        self.config.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError, 'resume identity mismatch'):
            b.run(self.config, out, resume=True)

    def test_resume_trusts_changed_code_and_retains_completed_data(self):
        out = self.root / 'changed-code'
        self.interrupt_before_union(out)
        original = sha256_file

        def changed(path):
            path = Path(path)
            if path == Path(b.geometry_io.__file__):
                return 'd' * 64
            return (
                'c' * 64
                if path in {Path(r2.__file__), Path(b.source_cache.__file__)} or (path.is_relative_to(b.HERE.parent) and path.suffix == '.py')
                else original(path)
            )

        with mock.patch.object(b, 'sha256_file', side_effect=changed):
            report = b.run(self.config, out, resume=True)
        self.assertEqual(report['status'], 'candidate-only')
        scripts = report['script_sha256']
        self.assertEqual(scripts['geodesy/ogr.py'], 'd' * 64)
        self.assertTrue(all(value == 'c' * 64 for name, value in scripts.items() if name != 'geodesy/ogr.py'))

    def test_completed_resume_revalidates_shard_inventory(self):
        out = self.root / 'finished'
        b.run(self.config, out)
        (out / 'shards/00000/water.tif').write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError, 'water shard checkpoint mismatch'):
            b.run(self.config, out, resume=True)

    def test_completed_resume_validates_the_report_masks_and_final_streams(self):
        out = self.root / 'finished'
        original = b.run(self.config, out)
        for name, message in (
            ('report.json', 'completed physical report mismatch'),
            ('land/land.tif', 'completed stage output mismatch: land'),
            ('union/water-union.tif', 'completed stage output mismatch: union'),
            ('physical/runs.u32le', 'completed physical output mismatch'),
        ):
            with self.subTest(name=name):
                path = out / name
                content = path.read_bytes()
                path.write_bytes(b'{}')
                with self.assertRaisesRegex(ValueError, message):
                    b.run(self.config, out, resume=True)
                path.write_bytes(content)
        self.assertEqual(b.run(self.config, out, resume=True), original)

    def test_completed_resume_requires_shard_reports_for_the_actual_settings(self):
        out = self.root / 'finished'
        b.run(self.config, out)
        pipeline_path = out / 'report.json'
        union_path = out / 'union' / 'report.json'
        pipeline = json.loads(pipeline_path.read_bytes())
        union = json.loads(union_path.read_bytes())

        def save_union(report):
            union_path.write_text(json.dumps(report))
            pipeline['stage_reports']['union']['sha256'] = sha256_file(union_path)
            pipeline_path.write_text(json.dumps(pipeline))

        save_union(dict(union, shards=[]))
        with self.assertRaisesRegex(ValueError, 'completed shard inventory mismatch'):
            b.run(self.config, out, resume=True)

        pin = union['shards'][0]['report']
        path = Path(pin['path'])
        shard = json.loads(path.read_bytes())
        path.write_text(json.dumps(dict(shard, policy={'method': 'unexpected'})))
        pin['sha256'] = sha256_file(path)
        save_union(union)
        with self.assertRaisesRegex(ValueError, 'mismatched report: 0'):
            b.run(self.config, out, resume=True)

    def test_completed_resume_revalidates_gdal_kernel_report(self):
        out = self.root / 'finished-gdal'
        b.run(self.config, out)
        path = out / 'shards/00000/report.json'
        report = json.loads(path.read_bytes())
        report['gdal_kernel']['binding_sha256'] = '0' * 64
        path.write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError, 'water shard checkpoint mismatch'):
            b.run(self.config, out, resume=True)

    def test_complete_physical_stage_does_not_start_processes(self):
        with mock.patch.object(
            subprocess, 'Popen', side_effect=AssertionError('unexpected subprocess')
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
            [p.read_text() for p in (out / 'interrupted').glob('00000-*/partial')], ['preserve']
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
                ('configs/land.json', 'resumed stage config mismatch'),
                ('land/report.json', 'land checkpoint mismatch'),
                ('configs/union.json', 'resumed stage config mismatch'),
                ('union/report.json', 'union checkpoint mismatch'),
                ('physical/runs.u32le', 'physical checkpoint mismatch'),
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

    def test_config_or_coastline_changes_during_processing_leave_run_incomplete(self):
        coast = Path(json.loads(self.land_cfg.read_text())['land'][0]['dataset'])
        for path, message in (
            (self.config, 'pipeline input changed during processing'),
            (coast, 'land source changed during processing'),
        ):
            with self.subTest(path=path):
                content = path.read_bytes()

                def mutate_after_composing(function, *args, **kwargs):
                    result = function(*args, **kwargs)
                    if function == COMPOSE:
                        path.write_bytes(content + b'\n')
                    return result

                output = self.root / ('changed-' + path.name)
                with intercept_stages(mutate_after_composing):
                    with self.assertRaisesRegex(ValueError, message):
                        b.run(self.config, output)
                self.assertFalse((output / 'report.json').exists())
                path.write_bytes(content)

    def test_r2_download_is_verified_timed_and_reused_by_next_build(self):
        shard = self.raw / 'water.parquet'
        content = shard.read_bytes()
        digest = sha256_file(shard)
        source = self.source_manifest
        source.write_text(
            json.dumps(
                {
                    'file_count': 1,
                    'files': [
                        {
                            'sha256': digest,
                            'size_bytes': len(content),
                            'r2_bucket': 'test-bucket',
                            'r2_key': 'source/water.parquet',
                        }
                    ],
                }
            )
        )
        self.cfg['inland_water'].update(json.loads(source.read_text()))
        self.cfg['max_parallel_shards'] = 1
        self.config.write_text(json.dumps(self.cfg))
        shard.unlink()
        out = self.root / 'staged'
        client = mock.Mock()

        def download(**kwargs):
            self.assertEqual(
                kwargs, {'Bucket': 'test-bucket', 'Key': 'source/water.parquet'}
            )
            time.sleep(0.05)
            return {'Body': io.BytesIO(content), 'ContentLength': len(content)}

        client.get_object.side_effect = download
        with mock.patch.object(
            r2, 'make_r2_client', return_value=R2Client(client)
        ) as make_client:
            b.run(self.config, out)
            make_client.assert_called_once_with()
        client.get_object.assert_called_once()
        client.close.assert_called_once()
        report = json.loads((out / 'report.json').read_text())
        self.assertEqual(report['downloaded_shard_count'], 1)
        self.assertGreaterEqual(report['source_download_elapsed_seconds'], 0.05)
        self.assertGreaterEqual(report['processing_elapsed_seconds'], 0)
        self.assertFalse((out / 'source-staging' / shard.name).exists())
        self.assertFalse(shard.exists())
        self.assertEqual(
            report['physical_output_sha256']['runs.u32le'],
            sha256_file(out / 'physical/runs.u32le'),
        )
        cached = self.raw / digest / shard.name
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

    def test_r2_overlaps_download_and_rasterization_and_matches_serial(self):
        first = self.raw / 'water.parquet'
        second = self.raw / 'other' / first.name
        second.parent.mkdir()
        table = pq.read_table(first)
        row = {**table.to_pylist()[0], 'id': 'second-lake'}
        pq.write_table(
            pa.Table.from_pylist([row]).replace_schema_metadata(table.schema.metadata),
            second,
        )
        payloads = {
            p.relative_to(self.raw).as_posix(): p.read_bytes() for p in (first, second)
        }
        files = [
            dict(
                sha256=sha256_file(self.raw / key),
                size_bytes=len(data),
                r2_bucket='atlas',
                r2_key=key,
            )
            for key, data in payloads.items()
        ]
        source = self.source_manifest
        source.write_text(json.dumps(dict(file_count=len(files), files=files)))
        self.cfg['inland_water'].update(
            file_count=len(files),
            files=[
                dict(path=key, sha256=sha256_file(self.raw / key)) for key in payloads
            ],
        )
        self.cfg['max_parallel_shards'] = 1
        self.config.write_text(json.dumps(self.cfg))
        serial = b.run(self.config, self.root / 'serial')
        self.cfg['inland_water'].update(json.loads(source.read_text()))
        for path in (first, second):
            path.unlink()

        self.cfg['max_parallel_shards'] = 2
        self.config.write_text(json.dumps(self.cfg))
        first_downloading = threading.Event()
        second_downloading = threading.Event()
        first_rasterized = threading.Event()

        def get_object(*, Bucket, Key):
            self.assertEqual(Bucket, 'atlas')
            if first_downloading.is_set():
                second_downloading.set()
                self.assertTrue(first_rasterized.wait(timeout=10))
            else:
                first_downloading.set()
            data = payloads[Key]
            return dict(Body=io.BytesIO(data), ContentLength=len(data))

        def notify_after_first_raster(function, *args, **kwargs):
            if function is WATER and not first_rasterized.is_set():
                self.assertTrue(second_downloading.wait(timeout=10))
                result = function(*args, **kwargs)
                first_rasterized.set()
                return result
            return function(*args, **kwargs)

        client = mock.Mock()
        client.get_object.side_effect = get_object
        output = self.root / 'parallel'
        with (
            mock.patch.object(
                r2, 'make_r2_client', return_value=R2Client(client)
            ) as make_client,
            intercept_stages(notify_after_first_raster),
        ):
            parallel = b.run(self.config, output)
        make_client.assert_called_once_with()
        client.close.assert_called_once_with()
        self.assertEqual(parallel['downloaded_shard_count'], 2)
        self.assertEqual(
            parallel['physical_output_sha256'], serial['physical_output_sha256']
        )
        for entry in files:
            self.assertEqual(
                (self.raw / entry['sha256'] / Path(entry['r2_key']).name).read_bytes(),
                payloads[entry['r2_key']],
            )

    def test_r2_bad_hash_is_discarded_and_retry_can_resume(self):
        shard = self.raw / 'water.parquet'
        content = shard.read_bytes()
        source = self.source_manifest
        source.write_text(
            json.dumps(
                {
                    'file_count': 1,
                    'files': [
                        {
                            'sha256': sha256_file(shard),
                            'size_bytes': len(content),
                            'r2_bucket': 'test-bucket',
                            'r2_key': 'source/water.parquet',
                        }
                    ],
                }
            )
        )
        self.cfg['inland_water'].update(json.loads(source.read_text()))
        self.cfg['max_parallel_shards'] = 1
        self.config.write_text(json.dumps(self.cfg))
        shard.unlink()
        out = self.root / 'bad-staged'
        client = mock.Mock()
        client.get_object.return_value = {
            'Body': io.BytesIO(b'X' + content[1:]),
            'ContentLength': len(content),
        }
        with mock.patch.object(r2, 'make_r2_client', return_value=R2Client(client)):
            with self.assertRaisesRegex(ValueError, 'size or hash mismatch'):
                b.run(self.config, out)
        cached = self.raw / self.cfg['inland_water']['files'][0]['sha256'] / shard.name
        self.assertFalse(cached.exists())
        self.assertEqual(list(self.raw.rglob('download-*')), [])
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
        subprocess.run(
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
        report = json.loads((out / 'report.json').read_text())
        self.assertEqual(report['status'], 'candidate-only')
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
        source = self.source_manifest
        source.write_text(
            json.dumps(
                {
                    'file_count': 2,
                    'files': [
                        {'path': first.name, 'sha256': sha256_file(first)},
                        {'path': second.name, 'sha256': sha256_file(second)},
                    ],
                }
            )
        )
        self.cfg['inland_water'].update(json.loads(source.read_text()))
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
        source = self.source_manifest
        source.write_text(
            json.dumps(
                {
                    'file_count': 2,
                    'files': [
                        {'path': first.name, 'sha256': sha256_file(first)},
                        {'path': bad.name, 'sha256': sha256_file(bad)},
                    ],
                }
            )
        )
        self.cfg['inland_water'].update(json.loads(source.read_text()))
        self.cfg['max_parallel_shards'] = 2
        self.config.write_text(json.dumps(self.cfg))
        out = self.root / 'parallel-incomplete'
        with self.assertRaisesRegex(ValueError, 'incomplete water shard'):
            b.run(self.config, out)
        self.assertFalse((out / 'union').exists())
        self.assertFalse((out / 'report.json').exists())

    def test_cancel_after_first_water_batch_and_resume_to_identical_grid(self):
        shard = self.raw / 'water.parquet'
        table = pq.read_table(shard)
        pq.write_table(pa.concat_tables([table] * 3), shard)
        self.cfg['inland_water']['files'][0]['sha256'] = sha256_file(shard)
        self.cfg['inland_water']['batch_size'] = 1
        self.config.write_text(json.dumps(self.cfg))
        out = self.root / 'cancelled'
        batches = []

        with b.control.stage() as cancelled:

            def cancel_on_water_progress(message, **_):
                if message.startswith('{"rows":'):
                    batches.append(json.loads(message)['rows'])
                    cancelled.set()

            with mock.patch.object(
                b.control, 'emit', side_effect=cancel_on_water_progress
            ):
                with self.assertRaisesRegex(InterruptedError, 'pipeline cancelled'):
                    b.run(self.config, out)

        self.assertEqual(batches, [1])
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
        source = self.source_manifest
        source.write_text(
            json.dumps(
                {'file_count': 1, 'files': [{'path': 'water.parquet', 'sha256': sha256_file(shard)}]}
            )
        )
        self.cfg['inland_water'].update(json.loads(source.read_text()))
        self.config.write_text(json.dumps(self.cfg))
        out = self.root / 'incomplete'
        with self.assertRaisesRegex(ValueError, 'incomplete water shard'):
            b.run(self.config, out)
        self.assertTrue((out / 'shards/00000/report.json').exists())
        self.assertFalse((out / 'report.json').exists())
        self.assertFalse((out / 'physical').exists())

    def test_rejects_source_path_traversal_before_output(self):
        source = self.source_manifest
        source.write_text(
            json.dumps({'file_count': 1, 'files': [{'path': '../bad.parquet', 'sha256': '1' * 64}]})
        )
        self.cfg['inland_water'].update(json.loads(source.read_text()))
        self.config.write_text(json.dumps(self.cfg))
        out = self.root / 'traversal'
        with self.assertRaisesRegex(ValueError, 'relative to the source directory'):
            b.run(self.config, out)
        self.assertFalse(out.exists())

    def test_rejects_a_raw_file_symlink_to_outside_the_manifest_directory(self):
        source = self.raw / 'water.parquet'
        relocated = self.root / source.name
        source.rename(relocated)
        source.symlink_to(relocated)
        out = self.root / 'escaped-source'
        with self.assertRaisesRegex(ValueError, 'raw source escapes the source directory'):
            b.run(self.config, out)
        self.assertFalse(out.exists())

    def test_requires_a_valid_output_location_and_current_land_input(self):
        with self.assertRaisesRegex(ValueError, 'output parent must exist'):
            b.run(self.config, self.root / 'missing' / 'output')
        for output in (self.raw / 'output', self.root):
            with self.subTest(output=output):
                with self.assertRaisesRegex(ValueError, 'input cache must use separate directories'):
                    b.run(self.config, output)
        with self.assertRaisesRegex(ValueError, 'output must be outside all input directories'):
            b.run(self.config, self.land_dir / 'output')
        land = Path(json.loads(self.land_cfg.read_text())['land'][0]['dataset'])
        land.write_text('{}')
        out = self.root / 'changed-input'
        with self.assertRaisesRegex(ValueError, 'land source hash mismatch'):
            b.run(self.config, out)
        self.assertFalse(out.exists())

    def test_physical_preflight_checks_available_disk_and_reports_cli_errors(self):
        self.cfg['minimum_free_bytes'] = 1
        self.config.write_text(json.dumps(self.cfg))
        out = self.root / 'low-disk'
        with mock.patch.object(b.shutil, 'disk_usage', return_value=mock.Mock(free=0)):
            with self.assertRaisesRegex(ValueError, 'free disk below pipeline reserve'):
                b.run(self.config, out)
        self.assertFalse(out.exists())

        self.config.write_text('{}')
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
        self.assertFalse(out.exists())

    def test_interrupted_physical_checkpoints_require_their_journal(self):
        out = self.root / 'interrupted'
        self.interrupt_before_union(out)
        (out / 'processing-events.jsonl').unlink()
        with self.assertRaisesRegex(ValueError, 'missing processing journal for existing checkpoints'):
            b.run(self.config, out, resume=True)
        self.assertFalse((out / 'report.json').exists())

    def test_stage_with_incomplete_report_never_publishes_physical_result(self):
        for stage, message in (
            (LAND, 'land raster is incomplete'),
            (UNION, 'water union is incomplete'),
            (COMPOSE, 'physical composition is incomplete'),
        ):
            with self.subTest(message=message):
                out = self.root / stage.__module__.split('.')[-1]

                def call(function, *args, **kwargs):
                    result = function(*args, **kwargs)
                    if function == stage:
                        report = Path(args[1]) / 'report.json'
                        data = json.loads(report.read_bytes())
                        report.write_text(json.dumps(dict(data, status='incomplete')))
                    return result

                with intercept_stages(call):
                    with self.assertRaisesRegex(ValueError, message):
                        b.run(self.config, out)
                self.assertFalse((out / 'report.json').exists())

    def test_resume_reuses_the_verified_cache_after_interruption(self):
        shard = self.raw / 'water.parquet'
        payload = shard.read_bytes()
        entry = self.cfg['inland_water']['files'][0]
        del entry['path']
        entry.update(r2_bucket='atlas', r2_key=shard.name, size_bytes=len(payload))
        self.config.write_text(json.dumps(self.cfg))
        shard.unlink()
        out = self.root / 'restart-r2'
        cached = self.raw / entry['sha256'] / shard.name
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
        self.cfg['physical_reference_mask'] = {
            'path': str(self.land_cfg),
            'sha256': sha256_file(self.land_cfg),
        }
        self.config.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError, 'physical_reference_mask'):
            b.run(self.config, out)
        self.assertFalse(out.exists())

    def test_preflight_rejects_invalid_grid_sources_and_controls(self):
        valid_water = self.cfg['inland_water']
        shard = valid_water['files'][0]
        cases = [
            ('pipeline', {'selection_notes': ''}, 'selection_notes'),
            ('pipeline', {'minimum_free_bytes': True}, 'minimum_free_bytes'),
            ('pipeline', {'union_rows_per_block': 0}, 'rows_per_block'),
            ('water', {'rasterizer': 'unknown'}, 'inland_water.rasterizer'),
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
                {
                    'file_count': 2,
                    'files': [shard, dict(shard, path='another.parquet')],
                },
                'paths and hashes must be unique',
            ),
        ]
        out = self.root / 'invalid'
        for section, changes, error in cases:
            with self.subTest(section=section, changes=changes):
                water = dict(valid_water)
                configuration = dict(self.cfg)
                {'pipeline': configuration, 'water': water}[section].update(changes)
                configuration['inland_water'] = water
                self.config.write_text(json.dumps(configuration))
                with self.assertRaisesRegex(ValueError, error):
                    b.run(self.config, out)
                self.assertFalse(out.exists())

        with self.assertRaisesRegex(ValueError, 'must match the build grid'):
            self.config.write_text(json.dumps(self.cfg))
            b.run(self.config, out, grid=b.Grid(8, 3, 45))
        self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
