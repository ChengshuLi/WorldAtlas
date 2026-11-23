"""Record build-stage timing and report active work across resume attempts."""

from __future__ import annotations

import json
import math
import threading
import time
import uuid
from collections.abc import Callable, Generator, Iterable, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NamedTuple, Self

from worldatlas.map_build.execution.journal import (
    append_records,
    create_journal,
    journal_anchor,
    preserve_torn_tail,
    verify_anchor,
)
from worldatlas.shared.files import JSONValue, read_json, write_json

TIMING_LOG = "timing-events.jsonl"


class SetupStart(NamedTuple):
    """Keep the setup start for elapsed-time calculation and the event log."""

    monotonic_seconds: float
    utc: str

    @classmethod
    def now(cls) -> Self:
        """Capture when build setup starts.

        Returns:
            Monotonic seconds for measurement and an ISO 8601 UTC timestamp.
        """
        return cls(time.monotonic(), datetime.now(timezone.utc).isoformat())


class ProducerDurations(NamedTuple):
    """Seconds spent processing and downloading without other active work."""

    processing: float
    download_only: float


@dataclass
class ProducerInvocation:
    """Receive the outcome of one call to a separately timed producer.

    A call may only verify a saved result, or it may start an attempt.
    A started attempt has durations once its end has been written to disk.
    """

    attempt_started: bool = False
    durations: ProducerDurations | None = None


@dataclass(frozen=True)
class ProducerTotals:
    """Summarize work from the producer's own journal across its attempts."""

    processing_seconds: float | None = None
    recorded_processing_seconds: float | None = None
    download_only_seconds: float | None = None
    complete: bool = False
    reused_from: str | None = None


@dataclass
class _Interval:
    """Track the monotonic seconds at both ends of one measured operation."""

    started: float
    ended: float | None = None


def verify_setup_timing(run: Path) -> None:
    """Verify the timing log prefixes sealed by the run's earlier attempts.

    Args:
        run: Directory containing the timing log and attempt directories.
    """
    for marker in (run / "attempts").glob("*/setup-timing.json"):
        verify_anchor(read_json(marker), run / TIMING_LOG)


def duration_seconds(value: JSONValue) -> float | None:
    """Read a duration from a producer report.

    Args:
        value: JSON value expected to hold seconds.

    Returns:
        The finite nonnegative duration, or None if the value is invalid.
    """
    if (
        (type(value) is int or type(value) is float)
        and math.isfinite(value)
        and value >= 0
    ):
        return value
    return None


def elapsed_union(intervals: Iterable[tuple[float, float]]) -> float:
    """Count seconds covered by one or more time intervals.

    Args:
        intervals: (start, end) pairs from the same clock.

    Returns:
        Elapsed seconds, counting overlaps once. For example, (0, 5) and
        (3, 8) cover eight seconds.

    Raises:
        ValueError: An interval is reversed or contains nonfinite times.
    """
    merged = []
    for start, end in sorted(intervals):
        if not (math.isfinite(start) and math.isfinite(end) and end >= start):
            raise ValueError("invalid processing interval")
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(end, merged[-1][1])
        else:
            merged.append([start, end])
    return sum(end - start for start, end in merged)


def _elapsed_outside(
    intervals: Iterable[tuple[float, float]], excluded: Iterable[tuple[float, float]]
) -> float:
    """Count seconds in the first set of intervals outside the second.

    Args:
        intervals: Time intervals to count.
        excluded: Time intervals to subtract from the first set.

    Returns:
        Elapsed seconds. For example, (0, 10) excluding (2, 8) gives 4.
    """
    events = []
    for start, end in intervals:
        events.extend([(start, 1, 0), (end, -1, 0)])
    for start, end in excluded:
        events.extend([(start, 0, 1), (end, 0, -1)])
    active = removed = 0
    previous_time = None
    total = 0.0
    for point, da, dr in sorted(events):
        if previous_time is not None and active and not removed:
            total += point - previous_time
        active += da
        removed += dr
        previous_time = point
    return total


class Timing:
    """Record wall-clock durations within each build attempt.

    Durations are added across attempts. Gaps between attempts do not count.
    """

    def __init__(
        self,
        path: Path | str,
        *,
        resume: bool = False,
        attempt: str | None = None,
        heartbeat_seconds: float = 0,
        earlier_attempts: Iterable[str] = (),
        producer_reports: Mapping[str, Callable[[], ProducerTotals]] | None = None,
    ) -> None:
        """Open a timing log and optionally start recording ongoing work.

        Args:
            path: Timing log in JSON Lines format.
            resume: Continue an existing log. Back up an incomplete last line.
            attempt: Attempt ID. Generate one if omitted.
            heartbeat_seconds: Seconds between progress entries for active work.
                Zero disables them.
            earlier_attempts: IDs of existing attempt directories in this run.
            producer_reports: Readers for stages that keep their own timing totals.

        Raises:
            ValueError: A line before the last one is incomplete or invalid.
        """
        self.path = Path(path)
        self.attempt = attempt or uuid.uuid4().hex
        self.earlier_attempts = tuple(sorted(earlier_attempts))
        self._producer_reports = dict(producer_reports or {})
        self.lock = threading.RLock()
        self.records = []
        self.active = {}
        self.completed_groups = set()
        self.stopped = threading.Event()
        self.thread = None
        if resume:
            raw = self.path.read_bytes()
            lines = raw.splitlines(keepends=True)
            valid = 0
            for index, line in enumerate(lines):
                try:
                    if not line.endswith(b"\n"):
                        raise ValueError("torn journal tail")
                    record = json.loads(line)
                except (ValueError, UnicodeDecodeError):
                    if index != len(lines) - 1:
                        raise ValueError(
                            "invalid timing journal before final line"
                        ) from None
                    backup = self.path.with_name(
                        self.path.name + ".torn-" + uuid.uuid4().hex
                    )
                    preserve_torn_tail(self.path, valid, backup, raw)
                    break
                self.records.append(record)
                if record["event"] == "group-complete":
                    self.completed_groups.add(record["group"])
                valid += len(line)
        else:
            create_journal(self.path)
        self.event({"event": "attempt", "id": self.attempt})
        if heartbeat_seconds:
            self._start_heartbeat(heartbeat_seconds)

    @classmethod
    def open_run(
        cls,
        attempt_dir: Path,
        setup_started: SetupStart,
        *,
        resume: bool,
        producer_reports: Mapping[str, Callable[[], ProducerTotals]],
    ) -> Self:
        """Open the run's timing log, record setup, and begin heartbeats.

        Args:
            attempt_dir: Directory for this attempt inside the run's attempts folder.
            setup_started: Clock readings captured before input validation.
            resume: Whether this run already has a timing log.
            producer_reports: Readers for stages that keep their own timing totals.

        Returns:
            The open timing recorder. Call close when the run ends.
        """
        attempts = attempt_dir.parent
        log_path = attempts.parent / TIMING_LOG
        # Setup can stop after creating the attempt directory but before
        # the first timing event exists. Resume can start the log then.
        timer = cls(
            log_path,
            resume=resume and log_path.exists(),
            attempt=attempt_dir.name,
            earlier_attempts=(
                path.name
                for path in attempts.iterdir()
                if path.is_dir() and path != attempt_dir
            ),
            producer_reports=producer_reports,
        )
        token = uuid.uuid4().hex
        ended = time.monotonic()
        timer.events(
            [
                {
                    "event": "start",
                    "token": token,
                    "id": "setup/source-validation",
                    "group": "setup",
                    "monotonic_seconds": setup_started.monotonic_seconds,
                    "utc": setup_started.utc,
                },
                {
                    "event": "complete",
                    "token": token,
                    "id": "setup/source-validation",
                    "group": "setup",
                    "start_monotonic_seconds": setup_started.monotonic_seconds,
                    "monotonic_seconds": ended,
                },
            ]
        )
        timer.mark_complete("setup")
        write_json(attempt_dir / "setup-timing.json", timer.anchor())
        timer._start_heartbeat(1.0)
        return timer

    def _start_heartbeat(self, seconds: float) -> None:
        """Start a thread that periodically saves progress for active intervals.

        Args:
            seconds: Interval between progress entries.
        """
        self.thread = threading.Thread(
            target=self._heartbeat, args=(seconds,), daemon=True
        )
        self.thread.start()

    @contextmanager
    def stage(self, group: str) -> Generator[None]:
        """Time a top-level stage and mark its outputs complete on success.

        Args:
            group: Stage name used in the run report.

        Yields:
            Control to the stage's work.
        """
        with self.measure(group, "stage-total"):
            yield
        self.mark_complete(group)

    @contextmanager
    def measure_producer(self, group: str) -> Generator[ProducerInvocation]:
        """Measure a call to a producer that reports its own work time.

        Args:
            group: Stage timing group that contains the producer call.

        Yields:
            A place for the producer to report whether it started
            an attempt and how many seconds it processed and downloaded.

        Raises:
            ValueError: The producer reported more time than the call took.
        """
        invocation = ProducerInvocation()
        interval = None
        try:
            with self.measure(group, f"{group}-invocation", kind="command") as interval:
                yield invocation
        finally:
            if interval is not None and interval.ended is not None:
                self._record_producer_invocation(
                    group, invocation, interval.ended - interval.started
                )

    def _record_producer_invocation(
        self, group: str, invocation: ProducerInvocation, elapsed: float
    ) -> None:
        """Save verification overhead and any known producer processing time.

        Args:
            group: Stage that ran the producer.
            invocation: Outcome reported directly by the producer.
            elapsed: Total seconds spent on the call.

        Raises:
            ValueError: Producer durations do not fit inside the call.
        """
        durations = invocation.durations
        if durations is None:
            if not invocation.attempt_started:
                self.event(
                    {
                        "event": f"{group}-command-overhead",
                        "id": group,
                        "seconds": elapsed,
                    }
                )
            # Without a durable attempt end, the producer's report will carry
            # a lower bound from the completed work when the build resumes.
            return
        processing, download_only = durations
        if (
            any(duration_seconds(value) is None for value in durations)
            or processing + download_only > elapsed
        ):
            raise ValueError(f"invalid {group} invocation timing")
        self.events(
            [
                {
                    "event": f"{group}-command-overhead",
                    "id": group,
                    "seconds": elapsed - processing - download_only,
                },
                {
                    "event": f"{group}-invocation-processing",
                    "id": group,
                    "seconds": processing,
                },
            ]
        )

    def report_fields(self) -> dict[str, Any]:
        """Assemble the timing fields in a successful run's report.

        Returns:
            Stage totals, a timing completeness flag, and the log's checksum.

        Raises:
            ValueError: A stage lacks a record of completed outputs.
        """
        stages = self.summary(require_producer_reports=True)
        if not all(stage["outputs_complete"] for stage in stages.values()):
            raise ValueError("all stage outputs must be complete")
        return {
            "stages": stages,
            "timing_complete": all(
                stage["timing_complete"] for stage in stages.values()
            ),
            "timing_anchor": self.anchor(),
        }

    def verify_report(self, report: Mapping[str, Any]) -> None:
        """Verify the saved report's timing log prefix before reuse.

        Args:
            report: Completed map build report.
        """
        verify_anchor(report["timing_anchor"], self.path)

    def event(self, value: dict[str, Any]) -> None:
        """Append one event to the timing log.

        Args:
            value: JSON-compatible event fields.
        """
        self.events([value])

    def events(self, values: Iterable[dict[str, Any]]) -> None:
        """Append a batch of events and flush them to disk.

        Args:
            values: Events to label with the current attempt ID.
        """
        values = [{"attempt": self.attempt, **value} for value in values]
        if not values:
            return
        with self.lock:
            append_records(self.path, values)
            self.records.extend(values)

    def _heartbeat(self, seconds: float) -> None:
        """Periodically record how far each active interval has progressed.

        Args:
            seconds: Time between progress entries.
        """
        while not self.stopped.wait(seconds):
            with self.lock:
                now = time.monotonic()
                self.events(
                    [
                        {
                            "event": "heartbeat",
                            "token": token,
                            "id": record["id"],
                            "group": record["group"],
                            "monotonic_seconds": now,
                        }
                        for token, record in self.active.items()
                    ]
                )

    def close(self) -> None:
        """Stop and join the timing thread."""
        self.stopped.set()
        if self.thread is not None:
            self.thread.join()
            self.thread = None

    @contextmanager
    def measure(
        self, group: str, name: str, *, kind: str = "processing"
    ) -> Generator[_Interval]:
        """Record when a piece of work starts and stops.

        Args:
            group: Parent stage to which this work contributes.
            name: Name of the work within the stage.
            kind: Timing category such as processing or command.

        Yields:
            The interval with its start in monotonic seconds. Its end time
            is filled in when the block exits, including when the work failed.
        """
        interval = _Interval(time.monotonic())
        token = uuid.uuid4().hex
        record = {
            "event": "start",
            "token": token,
            "id": f"{group}/{name}",
            "group": group,
            "kind": kind,
            "monotonic_seconds": interval.started,
        }
        with self.lock:
            self.event(record)
            self.active[token] = record
        try:
            yield interval
        except BaseException:
            self._finish(token, record, interval, "failed")
            raise
        else:
            self._finish(token, record, interval, "complete")

    def _finish(
        self, token: str, record: dict[str, Any], interval: _Interval, event: str
    ) -> None:
        """Record an interval's end and remove it from active work.

        Args:
            token: Unique interval ID.
            record: Start-event fields that identify this work.
            interval: Clock readings. The end is set here.
            event: Outcome, either "complete" or "failed".
        """
        with self.lock:
            interval.ended = time.monotonic()
            self.event(
                {
                    "event": event,
                    "token": token,
                    "id": record["id"],
                    "group": record["group"],
                    "start_monotonic_seconds": interval.started,
                    "monotonic_seconds": interval.ended,
                }
            )
            self.active.pop(token, None)

    def anchor(self) -> dict[str, str | int]:
        """Hash the current timing log while writes are locked.

        Returns:
            Dictionary with the path, saved prefix length and SHA-256.
        """
        with self.lock:
            return journal_anchor(self.path)

    def mark_complete(self, group: str) -> None:
        # Publish the cumulative stage result with completion, rather than
        # making a reader mistake the last resumed interval for the full total.
        """Record that a stage's output files are complete.

        Args:
            group: Stage whose results are ready.
        """
        with self.lock:
            summary = self._stage_summary(group, require_producer_report=True)
            summary.update(outputs_complete=True, complete=summary["timing_complete"])
            self.event(
                {
                    "event": "group-complete",
                    "id": group,
                    "group": group,
                    "timing_summary": summary,
                }
            )
            self.completed_groups.add(group)

    def intervals(
        self, group: str, *, kind: str | None = None
    ) -> tuple[dict[str, list[tuple[float, float]]], list[dict[str, Any]]]:
        """Read a stage's recorded active intervals.

        Args:
            group: Stage to summarize.
            kind: Optional timing category filter.

        Returns:
            (intervals_by_attempt, incomplete_events). Each interval is a
            (start, end) pair from its attempt's clock.
        """
        intervals, missing, _ = self.interval_details(group, kind=kind)
        return intervals, missing

    def interval_details(
        self, group: str, *, kind: str | None = None
    ) -> tuple[
        dict[str, list[tuple[float, float]]], list[dict[str, Any]], list[dict[str, Any]]
    ]:
        """Read active times and explain which intervals lack a known end.

        Args:
            group: Stage to summarize.
            kind: Optional timing category filter.

        Returns:
            (intervals_by_attempt, incomplete_events, interrupted_details).
            A heartbeat gives an interrupted interval's last recorded time.
            Its actual end remains unknown.

        Raises:
            ValueError: An interval ends before it starts.
        """
        starts, ends, beats = {}, {}, {}
        for record in self.records:
            token = (record.get("attempt"), record.get("token"))
            if record.get("group") != group or not token[1]:
                continue
            if record["event"] == "start":
                starts[token] = record
            elif record["event"] in ("complete", "failed"):
                ends[token] = record["monotonic_seconds"]
            elif record["event"] == "heartbeat":
                beats[token] = max(
                    beats.get(token, float("-inf")), record["monotonic_seconds"]
                )
        by_attempt = {}
        incomplete = []
        if group == "setup":
            measured_attempts = {attempt for attempt, _ in starts}
            incomplete = [
                {"attempt": attempt, "id": "setup/interrupted-initialization"}
                for attempt in self.earlier_attempts
                if attempt not in measured_attempts
            ]
        details = [
            {
                **record,
                "start_monotonic_seconds": None,
                "last_recorded_monotonic_seconds": None,
                "last_recorded_event": None,
                "recorded_elapsed_seconds": None,
                "unrecorded_tail_seconds": None,
                "reason": "initialization has no durable start/end interval",
            }
            for record in incomplete
        ]
        for token, start in starts.items():
            if kind is not None and start.get("kind", "processing") != kind:
                continue
            a = start["monotonic_seconds"]
            b = ends.get(token, beats.get(token, a))
            if token not in ends:
                incomplete.append({"attempt": token[0], "id": start["id"]})
                details.append(
                    {
                        "attempt": token[0],
                        "id": start["id"],
                        "start_monotonic_seconds": a,
                        "last_recorded_monotonic_seconds": b,
                        "last_recorded_event": "heartbeat"
                        if token in beats
                        else "start",
                        "recorded_elapsed_seconds": b - a,
                        "unrecorded_tail_seconds": None,
                        "reason": "no durable completion or failure endpoint",
                    }
                )
            if b < a:
                raise ValueError("non-monotonic processing interval")
            by_attempt.setdefault(token[0], []).append((a, b))
        return by_attempt, incomplete, details

    def summary(
        self, *, require_producer_reports: bool = False
    ) -> dict[str, dict[str, Any]]:
        """Summarize wall-clock time for each stage without counting overlap twice.

        Args:
            require_producer_reports: Require readable reports for stages with
                their own recorder. A failure summary can use partial timing.

        Returns:
            Stage names mapped to report dictionaries with processing seconds,
            output readiness, and details of any intervals with unknown ends.
        """
        names = dict.fromkeys(
            (
                "setup",
                "physical",
                "division",
                "package",
                "verification",
                *self._producer_reports,
                *(r["group"] for r in self.records if "group" in r),
            )
        )
        return {
            name: self._stage_summary(
                name, require_producer_report=require_producer_reports
            )
            for name in names
        }

    def _stage_summary(
        self, group: str, *, require_producer_report: bool
    ) -> dict[str, Any]:
        """Summarize measured work and output status for one stage.

        Args:
            group: Stage name.
            require_producer_report: Raise if the producer report is unavailable.

        Returns:
            Timing and completion fields for this stage.
        """
        intervals, missing, interrupted = self.interval_details(group)
        measured = sum(elapsed_union(items) for items in intervals.values())
        complete = not missing
        producer_fields = {}
        if reader := self._producer_reports.get(group):
            try:
                totals = reader()
            except (ValueError, OSError):
                if require_producer_report:
                    raise
                totals = ProducerTotals()
            measured, complete, producer_fields = self._producer_stage_totals(
                group, intervals, measured, complete, totals
            )
        outputs_complete = group in self.completed_groups
        return {
            "processing_elapsed_seconds": measured if complete else None,
            "recorded_processing_elapsed_seconds": measured,
            "recorded_processing_is_lower_bound": not complete,
            "complete": outputs_complete and complete,
            "outputs_complete": outputs_complete,
            "timing_complete": complete,
            "unmeasured_interrupted_attempts": missing,
            "interrupted_interval_details": interrupted,
            "unrecorded_interruption_tail_seconds": None if not complete else 0.0,
            "semantics": "sum of attempt-local active interval unions; no restart gap is counted",
            **producer_fields,
        }

    def _producer_stage_totals(
        self,
        group: str,
        intervals: Mapping[str, list[tuple[float, float]]],
        measured: float,
        complete: bool,
        totals: ProducerTotals,
    ) -> tuple[float, bool, dict[str, Any]]:
        """Combine a producer's timing with time spent around its calls.

        Args:
            group: Stage that calls the producer.
            intervals: Stage intervals keyed by pipeline attempt ID.
            measured: Wall-clock seconds recorded for the stage.
            complete: Whether all stage intervals have known endpoints.
            totals: Processing and download totals from the producer.

        Returns:
            Processing seconds, whether they cover all the work, and timing
            fields for the producer.
        """
        if totals.reused_from is not None:
            return (
                measured,
                complete,
                {
                    "source_download_elapsed_seconds": 0.0,
                    "producer_processing_elapsed_seconds": None,
                    "timing_error": None,
                    "reused_from": totals.reused_from,
                },
            )

        # Substitute the producer's split so downloads do not count as processing.
        invocations, _ = self.intervals(group, kind="command")
        outside_invocations = sum(
            _elapsed_outside(items, invocations.get(attempt, []))
            for attempt, items in intervals.items()
        )
        producer_seconds = totals.recorded_processing_seconds
        error = None
        if producer_seconds is None:
            producer_seconds = self._sum_seconds(f"{group}-invocation-processing")
            complete = False
            error = f"{group} producer has no valid measured processing total"
        verification_seconds = self._sum_seconds(f"{group}-command-overhead")
        measured = outside_invocations + verification_seconds + producer_seconds
        complete = complete and totals.complete
        downloads = totals.download_only_seconds
        if downloads is None:
            complete = False
            error = f"missing or invalid {group} acquisition timing"
        return (
            measured,
            complete,
            {
                "source_download_elapsed_seconds": downloads,
                "producer_processing_elapsed_seconds": totals.processing_seconds,
                "timing_error": error,
            },
        )

    def _sum_seconds(self, event: str) -> float:
        """Add the durations of one type of invocation event.

        Args:
            event: Event name with a duration recorded in the seconds field.

        Returns:
            Total recorded seconds across attempts.
        """
        return sum(
            record["seconds"] for record in self.records if record["event"] == event
        )
