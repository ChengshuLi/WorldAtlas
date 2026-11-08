"""Restart safety: active-time arithmetic, real leaf processes and pinned outputs."""
import json
import os
from pathlib import Path
import tempfile
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

import run_pipeline as pipeline
from execution_state import Checkpoints, Timing, RunLock, process_identity, write


class ActiveTimingTests(unittest.TestCase):
    def test_downtime_and_changed_monotonic_origin_are_never_counted(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'timing.jsonl'
            first = Timing(path, attempt='first')
            with patch.object(pipeline.time, 'monotonic', side_effect=[100, 104]):
                with first.measure('water', 'sea'):
                    pass
            first.close()
            second = Timing(path, resume=True, attempt='second')
            # This represents a different boot with a smaller monotonic clock.
            with patch.object(pipeline.time, 'monotonic', side_effect=[1, 4]):
                with second.measure('water', 'coast'):
                    pass
            second.mark_complete('water')
            result = second.summary(None)['water']
            self.assertEqual(result['processing_elapsed_seconds'], 7)
            self.assertTrue(result['timing_complete'])
            self.assertTrue(result['outputs_complete'])
            self.assertFalse(result['recorded_processing_is_lower_bound'])
            self.assertEqual(result['interrupted_interval_details'], [])
            self.assertEqual(result['unrecorded_interruption_tail_seconds'], 0)
            completion = [r for r in second.records if r['event'] == 'group-complete'][-1]
            self.assertEqual(completion['timing_summary'], result)
            second.close()

    def test_hard_interruption_has_only_durable_active_prefix_and_unknown_tail(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'timing.jsonl'
            first = Timing(path, attempt='first')
            first.event({'event': 'start', 'token': 'lost', 'id': 'water/sea',
                         'group': 'water', 'monotonic_seconds': 10})
            first.event({'event': 'heartbeat', 'token': 'lost', 'id': 'water/sea',
                         'group': 'water', 'monotonic_seconds': 12})
            first.close()
            second = Timing(path, resume=True, attempt='second')
            with patch.object(pipeline.time, 'monotonic', side_effect=[10000, 10003]):
                with second.measure('water', 'sea'):
                    pass
            second.mark_complete('water')
            result = second.summary(None)['water']
            self.assertIsNone(result['processing_elapsed_seconds'])
            self.assertEqual(result['recorded_processing_elapsed_seconds'], 5)
            self.assertFalse(result['timing_complete'])
            self.assertTrue(result['outputs_complete'])
            self.assertEqual(result['unmeasured_interrupted_attempts'], [{'attempt': 'first', 'id': 'water/sea'}])
            self.assertTrue(result['recorded_processing_is_lower_bound'])
            self.assertIsNone(result['unrecorded_interruption_tail_seconds'])
            self.assertEqual(result['interrupted_interval_details'], [{
                'attempt': 'first', 'id': 'water/sea', 'start_monotonic_seconds': 10,
                'last_recorded_monotonic_seconds': 12, 'last_recorded_event': 'heartbeat',
                'recorded_elapsed_seconds': 2, 'unrecorded_tail_seconds': None,
                'reason': 'no durable completion or failure endpoint'}])
            completion = [r for r in second.records if r['event'] == 'group-complete'][-1]
            self.assertEqual(completion['timing_summary'], result)
            self.assertEqual(completion['timing_summary']['recorded_processing_elapsed_seconds'], 5)
            second.close()

    def test_physical_completion_uses_the_download_excluding_producer_total(self):
        with tempfile.TemporaryDirectory() as td:
            timing = Timing(Path(td) / 'timing.jsonl', attempt='first')
            for token, start, end, kind in [('parent', 10, 25, 'processing'),
                                            ('child', 12, 24, 'command')]:
                timing.event({'event': 'start', 'token': token, 'id': 'physical/' + token,
                              'group': 'physical', 'kind': kind, 'monotonic_seconds': start})
                timing.event({'event': 'complete', 'token': token, 'id': 'physical/' + token,
                              'group': 'physical', 'monotonic_seconds': end})
            producer = {'status': 'candidate-only', 'processing_elapsed_seconds': 7,
                        'source_download_elapsed_seconds': 5, 'timing_complete': True}
            timing.mark_complete('physical', physical_report=producer)
            snapshot = timing.records[-1]['timing_summary']
            self.assertEqual(snapshot['processing_elapsed_seconds'], 10)
            self.assertEqual(snapshot['source_download_elapsed_seconds'], 5)
            self.assertFalse(snapshot['recorded_processing_is_lower_bound'])
            self.assertTrue(snapshot['complete'])
            timing.close()

    def test_interrupted_parent_and_child_prefixes_are_not_double_counted(self):
        with tempfile.TemporaryDirectory() as td:
            timing = Timing(Path(td) / 'timing.jsonl', attempt='first')
            for token, start, cutoff in [('parent', 10, 18), ('child', 12, 17)]:
                timing.event({'event': 'start', 'token': token, 'id': 'water/' + token,
                              'group': 'water', 'monotonic_seconds': start})
                timing.event({'event': 'heartbeat', 'token': token, 'id': 'water/' + token,
                              'group': 'water', 'monotonic_seconds': cutoff})
            result = timing.summary(None)['water']
            self.assertEqual(result['recorded_processing_elapsed_seconds'], 8)
            self.assertEqual([d['recorded_elapsed_seconds'] for d in
                              result['interrupted_interval_details']], [8, 5])
            self.assertTrue(result['recorded_processing_is_lower_bound'])
            timing.close()

    def test_interruption_before_first_heartbeat_has_an_explicit_unknown_tail(self):
        with tempfile.TemporaryDirectory() as td:
            timing = Timing(Path(td) / 'timing.jsonl', attempt='first')
            timing.event({'event': 'start', 'token': 'lost', 'id': 'mainland/stage-total',
                          'group': 'mainland', 'monotonic_seconds': 20})
            result = timing.summary(None)['mainland']
            self.assertIsNone(result['processing_elapsed_seconds'])
            self.assertEqual(result['recorded_processing_elapsed_seconds'], 0)
            detail, = result['interrupted_interval_details']
            self.assertEqual(detail['last_recorded_event'], 'start')
            self.assertEqual(detail['last_recorded_monotonic_seconds'], 20)
            self.assertIsNone(detail['unrecorded_tail_seconds'])
            timing.close()

    def test_missing_initialization_does_not_invent_a_zero_length_interval(self):
        with tempfile.TemporaryDirectory() as td:
            timing = Timing(Path(td) / 'timing.jsonl', attempt='first')
            timing.event({'event': 'unmeasured-initialization', 'id': 'setup/interrupted',
                          'group': 'setup'})
            result = timing.summary(None)['setup']
            detail, = result['interrupted_interval_details']
            self.assertIsNone(detail['start_monotonic_seconds'])
            self.assertIsNone(detail['recorded_elapsed_seconds'])
            self.assertIsNone(result['unrecorded_interruption_tail_seconds'])
            timing.close()

    def test_graceful_failed_work_is_measured_without_downtime(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'timing.jsonl'
            first = Timing(path, attempt='first')
            with patch.object(pipeline.time, 'monotonic', side_effect=[10, 13]):
                with self.assertRaises(KeyboardInterrupt):
                    with first.measure('mainland', 'stage2'):
                        raise KeyboardInterrupt()
            first.close()
            second = Timing(path, resume=True, attempt='second')
            with patch.object(pipeline.time, 'monotonic', side_effect=[10000, 10002]):
                with second.measure('mainland', 'stage2'):
                    pass
            second.mark_complete('mainland')
            self.assertEqual(second.summary(None)['mainland']['processing_elapsed_seconds'], 5)
            second.close()

    def test_torn_final_journal_line_is_preserved_and_not_invented(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'timing.jsonl'
            first = Timing(path, attempt='first')
            first.event({'event': 'start', 'token': 'lost', 'id': 'water/sea',
                         'group': 'water', 'monotonic_seconds': 10})
            first.close()
            with path.open('ab') as stream:
                stream.write(b'{"event":"compl')
            second = Timing(path, resume=True, attempt='second')
            self.assertEqual(len(list(Path(td).glob('timing.jsonl.torn-*'))), 1)
            self.assertFalse(second.summary(None)['water']['timing_complete'])
            self.assertTrue(path.read_bytes().endswith(b'\n'))
            second.close()

    def test_parallel_intervals_union_only_within_their_attempt(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'timing.jsonl'
            first = Timing(path, attempt='first')
            for token, start, end in [('a', 1, 5), ('b', 2, 7)]:
                first.event({'event': 'start', 'token': token, 'id': 'water/' + token,
                             'group': 'water', 'monotonic_seconds': start})
                first.event({'event': 'complete', 'token': token, 'id': 'water/' + token,
                             'group': 'water', 'monotonic_seconds': end})
            first.close()
            second = Timing(path, resume=True, attempt='second')
            with patch.object(pipeline.time, 'monotonic', side_effect=[1, 3]):
                with second.measure('water', 'c'):
                    pass
            second.mark_complete('water')
            self.assertEqual(second.summary(None)['water']['processing_elapsed_seconds'], 8)
            second.close()


class ExecutorResumeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        inputs = self.root / 'inputs'
        inputs.mkdir()
        sentinel = pipeline.write(inputs / 'sentinel.json', {})
        required = ('land_config water_config raw_manifest land_snapshot resolution_template '
                    'regional_template water_snapshot seavox_archive coastal_plan neon_selection osm_receipt').split()
        cfg = {'schema': 'worldatlas-end-to-end-pipeline-v1',
               'input_root': str(self.root), 'sources': {key: pipeline.pin(sentinel) for key in required}}
        self.config = pipeline.write(inputs / 'request.json', cfg)
        self.out = self.root / 'run'
        self.source = inputs / 'source.bin'
        self.source.write_bytes(b'final-output\x00\x01\x02')

    def runner(self, resume=False, confirm_no_writers=False):
        runner = pipeline.Pipeline(self.config, self.out, resume=resume,
                                   confirm_no_writers=confirm_no_writers)
        self.addCleanup(runner.close)
        return runner

    def execute(self, runner, **kwargs):
        return runner.command('water', 'fixture-stage', 'v7-pipeline/fixtures/partial_stage.py',
            self.source, self.out / 'result', _outputs=[self.out / 'result'], **kwargs)

    def test_completed_stage_is_verified_and_not_run_again(self):
        first = self.runner()
        self.assertTrue(self.execute(first))
        receipt = pipeline.pin(self.out / 'checkpoints/fixture-stage/complete.json')
        first.close()
        second = self.runner(resume=True)
        with patch.object(pipeline.subprocess, 'Popen', side_effect=AssertionError('completed process restarted')):
            self.assertFalse(self.execute(second))
        self.assertEqual(receipt, pipeline.pin(receipt['path']))
        self.assertEqual((self.out / 'result/result.bin').read_bytes(), self.source.read_bytes())

    def test_interrupted_leaf_is_preserved_then_rebuilt_and_checkpoints_resumed(self):
        first = self.runner()
        once = self.out / 'work/interrupt-marker'
        with self.assertRaisesRegex(RuntimeError, 'failed'):
            self.execute(first, interrupt_once=once)
        self.assertEqual((self.out / 'result/result.bin').read_bytes(), b'partial')
        first.close()
        with self.assertRaisesRegex(ValueError, 'no normal exit record'):
            self.runner(resume=True)
        second = self.runner(resume=True, confirm_no_writers=True)
        self.assertTrue(self.execute(second, interrupt_once=once))
        self.assertEqual((self.out / 'result/result.bin').read_bytes(), self.source.read_bytes())
        saved = list((self.out / 'preserved').glob('fixture-stage-*/0-result/result.bin'))
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0].read_bytes(), b'partial')
        second.close()
        third = self.runner(resume=True)
        self.assertFalse(self.execute(third, interrupt_once=once))
        self.assertEqual((self.out / 'result/result.bin').read_bytes(), self.source.read_bytes())

    def test_changed_completed_output_fails_before_reuse(self):
        first = self.runner()
        self.execute(first)
        first.close()
        (self.out / 'result/result.bin').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'output changed'):
            self.runner(resume=True)

    def test_changed_input_pin_fails_before_reuse(self):
        first = self.runner()
        self.execute(first)
        first.close()
        self.source.write_bytes(b'changed input')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            self.runner(resume=True)

    def test_lost_timing_prefix_is_rejected_before_checkpoint_reuse(self):
        first = self.runner()
        self.execute(first)
        first.close()
        (self.out / 'timing-events.jsonl').write_bytes(b'')
        with self.assertRaisesRegex(ValueError, 'timing journal lost'):
            self.runner(resume=True)

    def test_changed_code_identity_fails_before_reuse(self):
        first = self.runner()
        first.close()
        with patch.object(pipeline, 'code_identity', return_value={'changed.py': '0' * 64}):
            with self.assertRaisesRegex(ValueError, 'identity changed'):
                self.runner(resume=True)

    def test_two_live_runners_cannot_resume_same_run(self):
        self.runner()
        with self.assertRaisesRegex(ValueError, 'another pipeline runner'):
            self.runner(resume=True)

    def test_verified_unfinished_stage_process_blocks_resume_without_killing_it(self):
        first = self.runner()
        attempt = first.checkpoints.begin('orphan')
        write(attempt / 'admitted.json', {'timing_anchor': first.timing.anchor()})
        write(attempt / 'started.json', {'process': process_identity(os.getpid()),
                                              'timing_anchor': first.timing.anchor()})
        first.close()
        with self.assertRaisesRegex(ValueError, 'previous stage process is still alive'):
            self.runner(resume=True)
        self.assertIsNotNone(process_identity(os.getpid()))

    def test_direct_stage_retains_lease_after_parent_is_killed(self):
        release = self.root / 'release'
        log = self.root / 'parent.log'
        with log.open('wb') as stream:
            parent = subprocess.Popen([sys.executable, str(pipeline.HERE / 'fixtures/runner_process.py'),
                str(self.config), str(self.out), str(self.source), str(release)],
                stdout=stream, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 10
                while not (self.out / 'result/waiting').exists():
                    if parent.poll() is not None:
                        self.fail('fixture parent exited: ' + log.read_text())
                    if time.monotonic() > deadline:
                        self.fail('fixture did not reach direct stage')
                    time.sleep(.01)
                parent.kill()
                parent.wait()
                # Even if /proc cannot see the old namespace, the filesystem
                # lease remains held by the admitted ordinary stage process.
                with patch.object(pipeline, 'process_identity', return_value=None):
                    with self.assertRaisesRegex(ValueError, 'another pipeline runner'):
                        self.runner(resume=True)
            finally:
                release.write_bytes(b'continue')
                if parent.poll() is None:
                    parent.kill()
                    parent.wait()
        deadline = time.monotonic() + 10
        while True:
            try:
                lease = RunLock(self.out / 'run.lock')
            except ValueError:
                if time.monotonic() > deadline:
                    self.fail('direct stage did not release lease')
                time.sleep(.01)
            else:
                lease.close()
                break
        # A lease becoming free is not evidence about invisible grandchildren.
        # Without a normal exit record, only explicit quiescence confirmation
        # permits preserving/restarting the incomplete command.
        with self.assertRaisesRegex(ValueError, 'no normal exit record'):
            self.runner(resume=True)
        resumed = self.runner(resume=True, confirm_no_writers=True)
        self.assertTrue(self.execute(resumed, wait_for=release))
        self.assertEqual((self.out / 'result/result.bin').read_bytes(), self.source.read_bytes())
        self.assertFalse(resumed.timing.summary(None)['water']['timing_complete'])

    def test_generated_document_must_match_on_resume(self):
        first = self.runner()
        path = first.document('handoff', {'input': 'fixed'})
        first.close()
        second = self.runner(resume=True)
        self.assertEqual(second.document('handoff', {'input': 'fixed'}), path)
        with self.assertRaisesRegex(ValueError, 'generated request changed'):
            second.document('handoff', {'input': 'different'})


if __name__ == '__main__':
    unittest.main()
