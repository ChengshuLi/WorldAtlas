"""Restart safety: active-time arithmetic, checkpoints and pinned outputs."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from worldatlas.map_build.execution import runtime as pipeline
from worldatlas.map_build.execution.runtime import Timing


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
            first.event(
                {
                    'event': 'start',
                    'token': 'lost',
                    'id': 'water/sea',
                    'group': 'water',
                    'monotonic_seconds': 10,
                }
            )
            first.event(
                {
                    'event': 'heartbeat',
                    'token': 'lost',
                    'id': 'water/sea',
                    'group': 'water',
                    'monotonic_seconds': 12,
                }
            )
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
            self.assertEqual(
                result['unmeasured_interrupted_attempts'], [{'attempt': 'first', 'id': 'water/sea'}]
            )
            self.assertTrue(result['recorded_processing_is_lower_bound'])
            self.assertIsNone(result['unrecorded_interruption_tail_seconds'])
            self.assertEqual(
                result['interrupted_interval_details'],
                [
                    {
                        'attempt': 'first',
                        'id': 'water/sea',
                        'start_monotonic_seconds': 10,
                        'last_recorded_monotonic_seconds': 12,
                        'last_recorded_event': 'heartbeat',
                        'recorded_elapsed_seconds': 2,
                        'unrecorded_tail_seconds': None,
                        'reason': 'no durable completion or failure endpoint',
                    }
                ],
            )
            completion = [r for r in second.records if r['event'] == 'group-complete'][-1]
            self.assertEqual(completion['timing_summary'], result)
            self.assertEqual(completion['timing_summary']['recorded_processing_elapsed_seconds'], 5)
            second.close()

    def test_physical_completion_uses_the_download_excluding_producer_total(self):
        with tempfile.TemporaryDirectory() as td:
            timing = Timing(Path(td) / 'timing.jsonl', attempt='first')
            for token, start, end, kind in [
                ('parent', 10, 25, 'processing'),
                ('child', 12, 24, 'command'),
            ]:
                timing.event(
                    {
                        'event': 'start',
                        'token': token,
                        'id': 'physical/' + token,
                        'group': 'physical',
                        'kind': kind,
                        'monotonic_seconds': start,
                    }
                )
                timing.event(
                    {
                        'event': 'complete',
                        'token': token,
                        'id': 'physical/' + token,
                        'group': 'physical',
                        'monotonic_seconds': end,
                    }
                )
            producer = {
                'status': 'candidate-only',
                'processing_elapsed_seconds': 7,
                'source_download_elapsed_seconds': 5,
                'timing_complete': True,
            }
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
                timing.event(
                    {
                        'event': 'start',
                        'token': token,
                        'id': 'water/' + token,
                        'group': 'water',
                        'monotonic_seconds': start,
                    }
                )
                timing.event(
                    {
                        'event': 'heartbeat',
                        'token': token,
                        'id': 'water/' + token,
                        'group': 'water',
                        'monotonic_seconds': cutoff,
                    }
                )
            result = timing.summary(None)['water']
            self.assertEqual(result['recorded_processing_elapsed_seconds'], 8)
            self.assertEqual(
                [d['recorded_elapsed_seconds'] for d in result['interrupted_interval_details']],
                [8, 5],
            )
            self.assertTrue(result['recorded_processing_is_lower_bound'])
            timing.close()

    def test_interruption_before_first_heartbeat_has_an_explicit_unknown_tail(self):
        with tempfile.TemporaryDirectory() as td:
            timing = Timing(Path(td) / 'timing.jsonl', attempt='first')
            timing.event(
                {
                    'event': 'start',
                    'token': 'lost',
                    'id': 'mainland/stage-total',
                    'group': 'mainland',
                    'monotonic_seconds': 20,
                }
            )
            result = timing.summary(None)['mainland']
            self.assertIsNone(result['processing_elapsed_seconds'])
            self.assertEqual(result['recorded_processing_elapsed_seconds'], 0)
            (detail,) = result['interrupted_interval_details']
            self.assertEqual(detail['last_recorded_event'], 'start')
            self.assertEqual(detail['last_recorded_monotonic_seconds'], 20)
            self.assertIsNone(detail['unrecorded_tail_seconds'])
            timing.close()

    def test_missing_initialization_does_not_invent_a_zero_length_interval(self):
        with tempfile.TemporaryDirectory() as td:
            timing = Timing(Path(td) / 'timing.jsonl', attempt='first')
            timing.event(
                {'event': 'unmeasured-initialization', 'id': 'setup/interrupted', 'group': 'setup'}
            )
            result = timing.summary(None)['setup']
            (detail,) = result['interrupted_interval_details']
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
            first.event(
                {
                    'event': 'start',
                    'token': 'lost',
                    'id': 'water/sea',
                    'group': 'water',
                    'monotonic_seconds': 10,
                }
            )
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
                first.event(
                    {
                        'event': 'start',
                        'token': token,
                        'id': 'water/' + token,
                        'group': 'water',
                        'monotonic_seconds': start,
                    }
                )
                first.event(
                    {
                        'event': 'complete',
                        'token': token,
                        'id': 'water/' + token,
                        'group': 'water',
                        'monotonic_seconds': end,
                    }
                )
            first.close()
            second = Timing(path, resume=True, attempt='second')
            with patch.object(pipeline.time, 'monotonic', side_effect=[1, 3]):
                with second.measure('water', 'c'):
                    pass
            second.mark_complete('water')
            self.assertEqual(second.summary(None)['water']['processing_elapsed_seconds'], 8)
            second.close()


if __name__ == "__main__":
    unittest.main()
