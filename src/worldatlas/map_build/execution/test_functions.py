from pathlib import Path
import threading
import tempfile
import unittest
from unittest.mock import patch

from worldatlas.map_build.execution.runtime import (
    Checkpoints, Timing, inventory, journal_anchor, repository_identity, verify_anchor,
)
from worldatlas.shared.files import pin_file


class FunctionCheckpointTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / 'source.txt'
        self.source.write_text('input')
        self.output = self.root / 'output'
        self.checkpoints = Checkpoints(self.root / 'checkpoints', 'attempt')
        self.timing = Timing(self.root / 'timing-events.jsonl')
        self.addCleanup(self.timing.close)

    def call(self, action):
        return self.checkpoints.run_function(
            'calculate',
            'water',
            action,
            (),
            timing=self.timing,
            inputs=[pin_file(self.source)],
            outputs=[self.output],
        )

    def calculate(self):
        self.output.mkdir()
        (self.output / 'result').write_text(self.source.read_text())
        return {'result': str(self.output / 'result')}

    def test_resume_trusts_function_changes_and_preserves_the_output_record(self):
        first = self.call(self.calculate)

        def changed_function():
            self.fail('a completed calculation was repeated')

        self.assertEqual(self.call(changed_function), first)
        self.assertEqual(Path(first['result']).read_text(), 'input')

    def test_stage_accepts_explicit_keyword_inputs(self):
        def calculate(*, suffix):
            result = self.calculate()
            result['suffix'] = suffix
            return result

        result = self.checkpoints.run_function(
            'calculate',
            'water',
            calculate,
            (),
            kwargs={'suffix': 'selected'},
            timing=self.timing,
            inputs=[pin_file(self.source)],
            outputs=[self.output],
        )
        self.assertEqual(result['suffix'], 'selected')

    def test_changed_data_or_output_is_rejected(self):
        self.call(self.calculate)
        (self.output / 'result').write_text('tampered')
        with self.assertRaisesRegex(ValueError, 'output changed'):
            self.call(self.calculate)
        (self.output / 'result').write_text('input')
        self.source.write_text('new input')
        with self.assertRaisesRegex(ValueError, 'identity changed'):
            self.call(self.calculate)

    def test_failed_calculation_retains_partial_files_and_can_restart(self):
        def interrupted():
            self.output.mkdir()
            (self.output / 'partial').write_text('partial')
            raise InterruptedError('interrupted')

        with self.assertRaises(InterruptedError):
            self.call(interrupted)
        self.call(self.calculate)
        preserved = list((self.root / 'preserved').glob('calculate-*/0-output/partial'))
        self.assertEqual(len(preserved), 1)
        self.assertEqual(preserved[0].read_text(), 'partial')
        self.assertEqual((self.output / 'result').read_text(), 'input')

    def test_checkpoint_rejects_external_results_and_unsafe_names(self):
        outside = self.root.parent / 'outside'
        for name, output, message in (
            ('../calculate', self.output, 'unsafe checkpoint name'),
            ('calculate', outside, 'stage output outside run'),
            ('calculate', self.root, 'replaces run root'),
        ):
            with self.subTest(name=name, output=output):
                with self.assertRaisesRegex(ValueError, message):
                    self.checkpoints.run_function(
                        name, 'water', self.calculate, (), timing=self.timing,
                        inputs=[pin_file(self.source)], outputs=[output],
                    )
        self.assertFalse(self.output.exists())

    def test_inventory_never_follows_linked_or_missing_outputs(self):
        link = self.root / 'linked'
        link.symlink_to(self.source)
        for path, message in (
            (link, 'symlink checkpoint output'),
            (self.output, 'missing or non-regular checkpoint output'),
        ):
            with self.subTest(path=path):
                with self.assertRaisesRegex(ValueError, message):
                    inventory([path])

    def test_preservation_cannot_move_a_file_outside_the_run(self):
        with tempfile.TemporaryDirectory() as temp:
            outside = Path(temp) / 'unrelated'
            outside.write_text('leave in place')
            with self.assertRaisesRegex(ValueError, 'partial output outside run'):
                self.checkpoints.preserve('restart', [outside])
            self.assertEqual(outside.read_text(), 'leave in place')

    def test_producer_owned_marker_preserves_internal_checkpoints(self):
        marker = self.output / 'resume.json'

        def interrupted():
            self.output.mkdir()
            marker.write_text('completed first unit')
            raise InterruptedError('interrupted')

        with self.assertRaises(InterruptedError):
            self.checkpoints.run_function(
                'calculate',
                'physical',
                interrupted,
                (),
                timing=self.timing,
                inputs=[pin_file(self.source)],
                outputs=[self.output],
                resume_marker=marker,
            )

        def continue_stage():
            self.assertEqual(marker.read_text(), 'completed first unit')
            return {'resumed': True}

        result = self.checkpoints.run_function(
            'calculate',
            'physical',
            continue_stage,
            (),
            timing=self.timing,
            inputs=[pin_file(self.source)],
            outputs=[self.output],
            resume_marker=marker,
        )
        self.assertTrue(result['resumed'])


class TimingJournalTests(unittest.TestCase):
    def test_timing_prefix_cannot_be_sealed_if_the_file_shrinks_while_reading(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'timing-events.jsonl'
            path.write_text('original output')
            normal_open = Path.open

            def opening(file, mode='r', *args, **kwargs):
                if file == path.resolve() and mode == 'rb':
                    with normal_open(path, 'wb'):
                        pass
                return normal_open(file, mode, *args, **kwargs)

            with patch.object(Path, 'open', new=opening), self.assertRaisesRegex(
                ValueError, 'timing journal shortened while sealing prefix',
            ):
                journal_anchor(path)

    def test_empty_timing_write_has_no_effect(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'timing-events.jsonl'
            timing = Timing(path)
            self.addCleanup(timing.close)
            old_data = path.read_bytes()
            timing.events([])
            self.assertEqual(path.read_bytes(), old_data)
            self.assertIsNone(repository_identity(Path(temp)))

    def test_report_rejects_an_end_event_before_its_start(self):
        with tempfile.TemporaryDirectory() as temp:
            timing = Timing(Path(temp) / 'timing-events.jsonl')
            self.addCleanup(timing.close)
            for name, stamp in (('start', 2), ('complete', 1)):
                timing.event(
                    dict(event=name, group='land', id='work', token='unit', monotonic_seconds=stamp)
                )
            with self.assertRaisesRegex(ValueError, 'non-monotonic processing interval'):
                timing.interval_details('land')
    def test_checkpoint_pin_checks_prefix_and_allows_ordinary_appends(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'timing-events.jsonl'
            path.write_bytes(b'{"event":"attempt"}\n')
            pinned = journal_anchor(path)
            with path.open('ab') as stream:
                stream.write(b'{"event":"complete"}\n')
            verify_anchor(pinned, path)
            with self.assertRaisesRegex(ValueError, 'invalid timing journal anchor'):
                verify_anchor(dict(pinned, bytes=-1), path)
            path.write_bytes(b'{"event":"altered"}\n')
            with self.assertRaisesRegex(ValueError, 'checkpoint prefix changed'):
                verify_anchor(pinned, path)

    def test_resume_rejects_corruption_before_last_entry(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'timing-events.jsonl'
            raw = b'not JSON\n{"event":"attempt"}\n'
            path.write_bytes(raw)
            with self.assertRaisesRegex(ValueError, 'invalid timing journal before final line'):
                Timing(path, resume=True)
            self.assertEqual(path.read_bytes(), raw)

    def test_heartbeat_preserves_a_lower_bound_for_interrupted_work(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'timing-events.jsonl'
            heartbeat = threading.Event()
            timing = Timing(path, heartbeat_seconds=0.01)
            original = timing.events

            def observed(events):
                original(events)
                if any(event['event'] == 'heartbeat' for event in events):
                    heartbeat.set()

            try:
                with patch.object(timing, 'events', side_effect=observed):
                    started = {'event': 'start', 'id': 'work', 'group': 'physical',
                               'token': 'unit', 'monotonic_seconds': 0.0}
                    timing.event(started)
                    timing.event(dict(started, event='progress'))
                    with timing.lock:
                        timing.active['unit'] = started
                    self.assertTrue(heartbeat.wait(timeout=3))
                intervals, incomplete, details = timing.interval_details('physical')
                self.assertEqual(incomplete[0]['id'], 'work')
                self.assertEqual(details[0]['last_recorded_event'], 'heartbeat')
                self.assertGreater(intervals[timing.attempt][0][1], 0)
            finally:
                timing.close()



if __name__ == '__main__':
    unittest.main()
