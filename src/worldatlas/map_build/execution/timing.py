"""Record build-stage timing and report active work across resume attempts."""

from __future__ import annotations

import json
import math
import threading
import time
import uuid
from collections.abc import Generator, Iterable, Mapping
from contextlib import contextmanager
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
from worldatlas.shared.files import read_json, write_json

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


def verify_setup_timing(run: Path) -> None:
    """Verify the timing log prefixes sealed by the run's earlier attempts.

    Args:
        run: Directory containing the timing log and attempt directories.
    """
    for marker in (run / "attempts").glob("*/setup-timing.json"):
        verify_anchor(read_json(marker), run / TIMING_LOG)


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
        groups: Iterable[str] = (),
    ) -> None:
        """Open a timing log and optionally start recording ongoing work.

        Args:
            path: Timing log in JSON Lines format.
            resume: Continue an existing log. Back up an incomplete last line.
            attempt: Attempt ID. Generate one if omitted.
            heartbeat_seconds: Seconds between progress entries for active work.
                Zero disables them.
            earlier_attempts: IDs of existing attempt directories in this run.
            groups: Stage names to include even before work starts.

        Raises:
            ValueError: A line before the last one is incomplete or invalid.
        """
        self.path = Path(path)
        self.attempt = attempt or uuid.uuid4().hex
        self.earlier_attempts = tuple(sorted(earlier_attempts))
        self.groups = tuple(groups)
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
        groups: Iterable[str] = (),
    ) -> Self:
        """Open the run's timing log, record setup, and begin heartbeats.

        Args:
            attempt_dir: Directory for this attempt inside the run's attempts folder.
            setup_started: Clock readings captured before input validation.
            resume: Whether this run already has a timing log.
            groups: Stage names to show as pending before they run.

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
            groups=groups,
            earlier_attempts=(
                path.name
                for path in attempts.iterdir()
                if path.is_dir() and path != attempt_dir
            ),
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
        with self.measure(group, "stage-total", kind="wall"):
            yield
        self.mark_complete(group)

    def report_fields(self) -> dict[str, Any]:
        """Assemble the timing fields in a successful run's report.

        Returns:
            Stage totals, a timing completeness flag, and the log's checksum.

        Raises:
            ValueError: A stage lacks a record of completed outputs.
        """
        stages = self.summary()
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
    ) -> Generator[None]:
        """Record when a piece of work starts and stops.

        Args:
            group: Parent stage to which this work contributes.
            name: Name of the work within the stage.
            kind: Timing category such as processing, download, or inclusive wall time.

        """
        token = uuid.uuid4().hex
        record = {
            "event": "start",
            "token": token,
            "id": f"{group}/{name}",
            "group": group,
            "kind": kind,
            "monotonic_seconds": time.monotonic(),
        }
        with self.lock:
            self.event(record)
            self.active[token] = record
        try:
            yield
        except BaseException:
            self._finish(token, record, "failed")
            raise
        else:
            self._finish(token, record, "complete")

    def _finish(self, token: str, record: dict[str, Any], event: str) -> None:
        """Record an interval's end and remove it from active work.

        Args:
            token: Unique interval ID.
            record: Start-event fields that identify this work.
            event: Outcome, either "complete" or "failed".
        """
        with self.lock:
            self.event(
                {
                    "event": event,
                    "token": token,
                    "id": record["id"],
                    "group": record["group"],
                    "start_monotonic_seconds": record["monotonic_seconds"],
                    "monotonic_seconds": time.monotonic(),
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
            summary = self._stage_summary(group)
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

    def summary(self) -> dict[str, dict[str, Any]]:
        """Summarize wall-clock time for each stage without counting overlap twice.

        Returns:
            Stage names mapped to report dictionaries with processing and
            download seconds, output readiness, and any interrupted intervals.
        """
        names = dict.fromkeys(
            (*self.groups, *(r["group"] for r in self.records if "group" in r))
        )
        return {name: self._stage_summary(name) for name in names}

    def _stage_summary(self, group: str) -> dict[str, Any]:
        """Summarize measured work and output status for one stage.

        Args:
            group: Stage name.

        Returns:
            Timing and completion fields for this stage.
        """
        intervals, missing, interrupted = self.interval_details(group)
        downloads, _ = self.intervals(group, kind="download")
        processing, _ = (
            self.intervals(group, kind="processing") if downloads else ({}, [])
        )
        # Count overlapping downloads only once, and count time shared with
        # actual processing as processing. Wall-clock spans include both.
        download_only = sum(
            _elapsed_outside(items, processing.get(attempt, []))
            for attempt, items in downloads.items()
        )
        measured = (
            sum(elapsed_union(items) for items in intervals.values()) - download_only
        )
        complete = not missing
        outputs_complete = group in self.completed_groups
        return {
            "processing_elapsed_seconds": measured if complete else None,
            "recorded_processing_elapsed_seconds": measured,
            "source_download_elapsed_seconds": download_only,
            "recorded_processing_is_lower_bound": not complete,
            "complete": outputs_complete and complete,
            "outputs_complete": outputs_complete,
            "timing_complete": complete,
            "unmeasured_interrupted_attempts": missing,
            "interrupted_interval_details": interrupted,
            "unrecorded_interruption_tail_seconds": None if not complete else 0.0,
            "semantics": "sum of attempt-local active interval unions; no restart gap is counted",
        }
