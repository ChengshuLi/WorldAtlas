"""Record build-stage timing and report active work across resume attempts."""

from __future__ import annotations

import json
import math
import threading
import time
import uuid
from collections.abc import Generator, Iterable, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NamedTuple, Self, cast

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


class PhysicalDurations(NamedTuple):
    """Seconds spent processing and downloading without other active work."""

    processing: float
    download_only: float


@dataclass
class PhysicalInvocation:
    """Receive the outcome of one call to the physical producer.

    A call may only verify a saved result, or it may start an attempt.
    A started attempt has durations once its end has been written to disk.
    """

    attempt_started: bool = False
    durations: PhysicalDurations | None = None


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


def _valid_seconds(value: JSONValue) -> bool:
    """Check a duration read from the physical producer's report.

    Args:
        value: JSON value expected to hold seconds.

    Returns:
        Whether the value is a finite nonnegative number.
    """
    return (
        (type(value) is int or type(value) is float)
        and math.isfinite(value)
        and value >= 0
    )


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
        physical_reuse: Mapping[str, Any] | None = None,
    ) -> None:
        """Open a timing log and optionally start recording ongoing work.

        Args:
            path: Timing log in JSON Lines format.
            resume: Continue an existing log. Back up an incomplete last line.
            attempt: Attempt ID. Generate one if omitted.
            heartbeat_seconds: Seconds between progress entries for active work.
                Zero disables them.
            earlier_attempts: IDs of existing attempt directories in this run.
            physical_reuse: Receipt for a previously completed physical grid.

        Raises:
            ValueError: A line before the last one is incomplete or invalid.
        """
        self.path = Path(path)
        self.attempt = attempt or uuid.uuid4().hex
        self.earlier_attempts = tuple(sorted(earlier_attempts))
        self._physical_reuse = physical_reuse
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
        physical_reuse: Mapping[str, Any] | None,
    ) -> Self:
        """Open the run's timing log, record setup, and begin heartbeats.

        Args:
            attempt_dir: Directory for this attempt inside the run's attempts folder.
            setup_started: Clock readings captured before input validation.
            resume: Whether this run already has a timing log.
            physical_reuse: Receipt for a reused physical grid, if selected.

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
            physical_reuse=physical_reuse,
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
        report = self._physical_report() if group == "physical" else None
        self.mark_complete(group, physical_report=report)

    @contextmanager
    def physical_invocation(self) -> Generator[PhysicalInvocation]:
        """Measure a physical build call, including cached-output verification.

        Yields:
            A place for the physical producer to report whether it started
            an attempt and how many seconds it processed and downloaded.

        Raises:
            ValueError: The producer reported more time than the call took.
        """
        invocation = PhysicalInvocation()
        interval = None
        try:
            with self.measure(
                "physical", "physical-invocation", kind="command"
            ) as interval:
                yield invocation
        finally:
            if interval is not None and interval.ended is not None:
                self._record_physical_invocation(
                    invocation, interval.ended - interval.started
                )

    def _record_physical_invocation(
        self, invocation: PhysicalInvocation, elapsed: float
    ) -> None:
        """Save verification overhead and any known producer processing time.

        Args:
            invocation: Outcome reported directly by the physical producer.
            elapsed: Total seconds spent on the call.

        Raises:
            ValueError: Producer durations do not fit inside the call.
        """
        durations = invocation.durations
        if durations is None:
            if not invocation.attempt_started:
                self.event(
                    {
                        "event": "physical-command-overhead",
                        "id": "physical",
                        "seconds": elapsed,
                    }
                )
            # Without a durable attempt end, the physical report will carry
            # a lower bound from the completed work when the build resumes.
            return
        processing, download_only = durations
        if (
            any(not _valid_seconds(value) for value in durations)
            or processing + download_only > elapsed
        ):
            raise ValueError("invalid physical invocation timing")
        self.events(
            [
                {
                    "event": "physical-command-overhead",
                    "id": "physical",
                    "seconds": elapsed - processing - download_only,
                },
                {
                    "event": "physical-invocation-processing",
                    "id": "physical",
                    "seconds": processing,
                },
            ]
        )

    def _physical_report(self) -> Mapping[str, Any]:
        """Read the physical stage's saved timing information.

        Returns:
            The producer's report or the receipt for a reused grid.
        """
        return self._physical_reuse or read_json(
            self.path.parent / "physical/report.json"
        )

    def report_fields(self) -> dict[str, Any]:
        """Assemble the timing fields in a successful run's report.

        Returns:
            Stage totals, a timing completeness flag, and the log's checksum.

        Raises:
            ValueError: A stage lacks a record of completed outputs.
        """
        stages = self.summary(self._physical_report())
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

    def failed_stage_summary(self) -> dict[str, dict[str, Any]]:
        """Summarize the timing recorded before a build failed.

        Returns:
            Stage names mapped to timing fields. Missing physical output
            leaves the physical stage with any lower bound we can establish.
        """
        try:
            report = self._physical_report()
        except (ValueError, OSError):
            report = None
        return self.summary(report)

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

    def mark_complete(
        self, group: str, *, physical_report: Mapping[str, Any] | None = None
    ) -> None:
        # Publish the cumulative stage result with completion, rather than
        # making a reader mistake the last resumed interval for the full total.
        """Record that a stage's output files are complete.

        Args:
            group: Stage whose results are ready.
            physical_report: Physical producer timing report or reuse record, when
                needed.
        """
        with self.lock:
            summary = self._stage_summary(group, physical_report)
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
        self, physical_report: Mapping[str, Any] | None
    ) -> dict[str, dict[str, Any]]:
        """Summarize wall-clock time for each stage without counting overlap twice.

        Args:
            physical_report: Physical producer report, reuse record, or None before
                output is ready.

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
                *(r["group"] for r in self.records if "group" in r),
            )
        )
        return {name: self._stage_summary(name, physical_report) for name in names}

    def _stage_summary(
        self, group: str, physical_report: Mapping[str, Any] | None
    ) -> dict[str, Any]:
        """Summarize measured work and output status for one stage.

        Args:
            group: Stage name.
            physical_report: Physical producer report or reuse receipt, if available.

        Returns:
            Timing and completion fields for this stage.
        """
        intervals, missing, interrupted = self.interval_details(group)
        measured = sum(elapsed_union(items) for items in intervals.values())
        complete = not missing
        physical_fields = {}
        if group == "physical":
            measured, complete, physical_fields = self._physical_stage_totals(
                intervals, measured, complete, physical_report or {}
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
            **physical_fields,
        }

    def _physical_stage_totals(
        self,
        intervals: Mapping[str, list[tuple[float, float]]],
        measured: float,
        complete: bool,
        report: Mapping[str, Any],
    ) -> tuple[float, bool, dict[str, Any]]:
        """Combine physical producer timing with time spent around its call.

        Args:
            intervals: Physical-stage intervals keyed by pipeline attempt ID.
            measured: Wall-clock seconds recorded for the physical stage.
            complete: Whether all its measured intervals have known endpoints.
            report: Producer report, reuse receipt, or an empty mapping on failure.

        Returns:
            Processing seconds, whether they cover the entire stage, and
            physical-only fields including source download seconds.
        """
        if report.get("status") == "reused":
            return (
                measured,
                complete,
                {
                    "source_download_elapsed_seconds": 0.0,
                    "producer_processing_elapsed_seconds": None,
                    "timing_error": None,
                    "reused_from": report["source_run"],
                },
            )

        # The full invocation includes processing and transfers. Substitute
        # the producer's split to avoid counting a transfer as processing.
        invocations, _ = self.intervals("physical", kind="command")
        outside_invocations = sum(
            _elapsed_outside(items, invocations.get(attempt, []))
            for attempt, items in intervals.items()
        )
        producer_seconds = report.get(
            "recorded_processing_elapsed_seconds",
            report.get("processing_elapsed_seconds"),
        )
        error = None
        if not _valid_seconds(producer_seconds):
            producer_seconds = self._sum_seconds("physical-invocation-processing")
            complete = False
            error = "physical producer has no valid measured processing total"
        verification_seconds = self._sum_seconds("physical-command-overhead")
        measured = (
            outside_invocations + verification_seconds + cast(float, producer_seconds)
        )
        complete = (
            complete
            and report.get("timing_complete", True)
            and report.get("status") == "candidate-only"
        )
        downloads = report.get("source_download_elapsed_seconds")
        if not _valid_seconds(downloads):
            complete = False
            error = "missing or invalid physical acquisition timing"
        return (
            measured,
            complete,
            {
                "source_download_elapsed_seconds": downloads,
                "producer_processing_elapsed_seconds": report.get(
                    "processing_elapsed_seconds"
                ),
                "timing_error": error,
            },
        )

    def _sum_seconds(self, event: str) -> float:
        """Add the durations of one type of physical invocation event.

        Args:
            event: Event name with a duration recorded in the seconds field.

        Returns:
            Total recorded seconds across attempts.
        """
        return sum(
            record["seconds"] for record in self.records if record["event"] == event
        )
