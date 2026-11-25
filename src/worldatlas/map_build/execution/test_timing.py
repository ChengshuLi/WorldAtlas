"""Restart safety: active-time arithmetic, checkpoints and pinned outputs."""

from contextlib import ExitStack
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from worldatlas.map_build.execution.timing import Timing


class ActiveTimingTests(unittest.TestCase):
    def test_stage_totals_separate_only_download_time_outside_processing(self):
        with tempfile.TemporaryDirectory() as td:
            timing = Timing(Path(td) / "timing.jsonl", groups=("tiles", "publish"))
            with patch.object(time, "monotonic", side_effect=[0, 0, 2, 5, 8, 15, 16, 20]):
                with timing.stage("tiles"), timing.measure("tiles", "file", kind="download"):
                    # Rasterization starts during the failed download and ends after it.
                    with ExitStack() as rasterize:
                        with self.assertRaises(InterruptedError), timing.measure(
                            "tiles", "failed-file", kind="download"
                        ):
                            rasterize.enter_context(timing.measure("tiles", "rasterize"))
                            raise InterruptedError("transfer stopped")
            stages = timing.summary()
            self.assertEqual(set(stages), {"tiles", "publish"})
            self.assertEqual(stages["tiles"]["processing_elapsed_seconds"], 14)
            self.assertEqual(stages["tiles"]["source_download_elapsed_seconds"], 6)
            self.assertTrue(stages["tiles"]["complete"])
            self.assertFalse(stages["publish"]["outputs_complete"])
            timing.close()

    def test_downtime_and_changed_monotonic_origin_are_never_counted(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "timing.jsonl"
            first = Timing(path, attempt="first")
            with patch.object(time, "monotonic", side_effect=[100, 104]):
                with first.measure("water", "sea"):
                    pass
            first.close()
            second = Timing(path, resume=True, attempt="second")
            # This represents a different boot with a smaller monotonic clock.
            with patch.object(time, "monotonic", side_effect=[1, 4]):
                with second.measure("water", "coast"):
                    pass
            second.mark_complete("water")
            result = second.summary()["water"]
            self.assertEqual(result["processing_elapsed_seconds"], 7)
            self.assertTrue(result["timing_complete"])
            self.assertTrue(result["outputs_complete"])
            self.assertFalse(result["recorded_processing_is_lower_bound"])
            self.assertEqual(result["interrupted_interval_details"], [])
            self.assertEqual(result["unrecorded_interruption_tail_seconds"], 0)
            completion = [r for r in second.records if r["event"] == "group-complete"][
                -1
            ]
            self.assertEqual(completion["timing_summary"], result)
            second.close()

    def test_hard_interruption_has_only_durable_active_prefix_and_unknown_tail(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "timing.jsonl"
            first = Timing(path, attempt="first")
            first.event(
                {
                    "event": "start",
                    "token": "lost",
                    "id": "water/sea",
                    "group": "water",
                    "monotonic_seconds": 10,
                }
            )
            first.event(
                {
                    "event": "heartbeat",
                    "token": "lost",
                    "id": "water/sea",
                    "group": "water",
                    "monotonic_seconds": 12,
                }
            )
            first.close()
            second = Timing(path, resume=True, attempt="second")
            with patch.object(time, "monotonic", side_effect=[10000, 10003]):
                with second.measure("water", "sea"):
                    pass
            second.mark_complete("water")
            result = second.summary()["water"]
            self.assertIsNone(result["processing_elapsed_seconds"])
            self.assertEqual(result["recorded_processing_elapsed_seconds"], 5)
            self.assertFalse(result["timing_complete"])
            self.assertTrue(result["outputs_complete"])
            self.assertEqual(
                result["unmeasured_interrupted_attempts"],
                [{"attempt": "first", "id": "water/sea"}],
            )
            self.assertTrue(result["recorded_processing_is_lower_bound"])
            self.assertIsNone(result["unrecorded_interruption_tail_seconds"])
            self.assertEqual(
                result["interrupted_interval_details"],
                [
                    {
                        "attempt": "first",
                        "id": "water/sea",
                        "start_monotonic_seconds": 10,
                        "last_recorded_monotonic_seconds": 12,
                        "last_recorded_event": "heartbeat",
                        "recorded_elapsed_seconds": 2,
                        "unrecorded_tail_seconds": None,
                    }
                ],
            )
            completion = [r for r in second.records if r["event"] == "group-complete"][
                -1
            ]
            self.assertEqual(completion["timing_summary"], result)
            self.assertEqual(
                completion["timing_summary"]["recorded_processing_elapsed_seconds"], 5
            )
            second.close()

    def test_interrupted_parent_and_child_prefixes_are_not_double_counted(self):
        with tempfile.TemporaryDirectory() as td:
            timing = Timing(Path(td) / "timing.jsonl", attempt="first")
            for token, start, cutoff in [("parent", 10, 18), ("child", 12, 17)]:
                timing.event(
                    {
                        "event": "start",
                        "token": token,
                        "id": "water/" + token,
                        "group": "water",
                        "monotonic_seconds": start,
                    }
                )
                timing.event(
                    {
                        "event": "heartbeat",
                        "token": token,
                        "id": "water/" + token,
                        "group": "water",
                        "monotonic_seconds": cutoff,
                    }
                )
            result = timing.summary()["water"]
            self.assertEqual(result["recorded_processing_elapsed_seconds"], 8)
            self.assertEqual(
                [
                    d["recorded_elapsed_seconds"]
                    for d in result["interrupted_interval_details"]
                ],
                [8, 5],
            )
            self.assertTrue(result["recorded_processing_is_lower_bound"])
            timing.close()

    def test_interruption_before_first_heartbeat_has_an_explicit_unknown_tail(self):
        with tempfile.TemporaryDirectory() as td:
            timing = Timing(Path(td) / "timing.jsonl", attempt="first")
            timing.event(
                {
                    "event": "start",
                    "token": "lost",
                    "id": "land/stage-total",
                    "group": "land",
                    "monotonic_seconds": 20,
                }
            )
            result = timing.summary()["land"]
            self.assertIsNone(result["processing_elapsed_seconds"])
            self.assertEqual(result["recorded_processing_elapsed_seconds"], 0)
            (detail,) = result["interrupted_interval_details"]
            self.assertEqual(detail["last_recorded_event"], "start")
            self.assertEqual(detail["last_recorded_monotonic_seconds"], 20)
            self.assertIsNone(detail["unrecorded_tail_seconds"])
            timing.close()

    def test_missing_initialization_does_not_invent_a_zero_length_interval(self):
        with tempfile.TemporaryDirectory() as td:
            timing = Timing(
                Path(td) / "timing.jsonl", attempt="second", groups=("setup",), earlier_attempts=["first"]
            )
            result = timing.summary()["setup"]
            (detail,) = result["interrupted_interval_details"]
            self.assertIsNone(detail["start_monotonic_seconds"])
            self.assertIsNone(detail["recorded_elapsed_seconds"])
            self.assertIsNone(result["unrecorded_interruption_tail_seconds"])
            timing.close()

    def test_graceful_failed_work_is_measured_without_downtime(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "timing.jsonl"
            first = Timing(path, attempt="first")
            with patch.object(time, "monotonic", side_effect=[10, 13]):
                with self.assertRaises(KeyboardInterrupt):
                    with first.measure("land", "stage2"):
                        raise KeyboardInterrupt()
            first.close()
            second = Timing(path, resume=True, attempt="second")
            with patch.object(time, "monotonic", side_effect=[10000, 10002]):
                with second.measure("land", "stage2"):
                    pass
            second.mark_complete("land")
            self.assertEqual(
                second.summary()["land"]["processing_elapsed_seconds"], 5
            )
            second.close()

    def test_torn_final_journal_line_is_preserved_and_not_invented(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "timing.jsonl"
            first = Timing(path, attempt="first")
            first.event(
                {
                    "event": "start",
                    "token": "lost",
                    "id": "water/sea",
                    "group": "water",
                    "monotonic_seconds": 10,
                }
            )
            first.close()
            with path.open("ab") as stream:
                stream.write(b'{"event":"compl')
            second = Timing(path, resume=True, attempt="second")
            self.assertEqual(len(list(Path(td).glob("timing.jsonl.torn-*"))), 1)
            self.assertFalse(second.summary()["water"]["timing_complete"])
            self.assertTrue(path.read_bytes().endswith(b"\n"))
            second.close()

    def test_parallel_intervals_union_only_within_their_attempt(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "timing.jsonl"
            first = Timing(path, attempt="first")
            for token, start, end in [("a", 1, 5), ("b", 2, 7)]:
                first.event(
                    {
                        "event": "start",
                        "token": token,
                        "id": "water/" + token,
                        "group": "water",
                        "monotonic_seconds": start,
                    }
                )
                first.event(
                    {
                        "event": "complete",
                        "token": token,
                        "id": "water/" + token,
                        "group": "water",
                        "monotonic_seconds": end,
                    }
                )
            first.close()
            second = Timing(path, resume=True, attempt="second")
            with patch.object(time, "monotonic", side_effect=[1, 3]):
                with second.measure("water", "c"):
                    pass
            second.mark_complete("water")
            self.assertEqual(
                second.summary()["water"]["processing_elapsed_seconds"], 8
            )
            second.close()


if __name__ == "__main__":
    unittest.main()
