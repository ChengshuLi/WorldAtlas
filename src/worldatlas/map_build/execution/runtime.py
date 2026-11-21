"""Durable pipeline identities, output checkpoints and attempt-local active timing."""

from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import subprocess
import threading
import time
import traceback
import uuid
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast

from worldatlas.shared.files import (
    pin_file,
    read_json,
    sha256_file,
    sync_directory,
    verify_pins,
    write_json,
)


def journal_anchor(path: Path | str) -> dict[str, str | int]:
    """Record the current bytes of an append-only timing log.

    Args:
        path: Timing log file.

    Returns:
        Dictionary with its absolute "path", byte count "bytes", and "sha256".
        Future writes can append bytes without invalidating this record.

    Raises:
        ValueError: The file shrank while it was being read.
    """
    path = Path(path).resolve(strict=True)
    size = path.stat().st_size
    h = hashlib.sha256()
    with path.open("rb") as stream:
        remaining = size
        while remaining:
            block = stream.read(min(1 << 20, remaining))
            if not block:
                raise ValueError("timing journal shortened while sealing prefix")
            h.update(block)
            remaining -= len(block)
    return {"path": str(path), "bytes": size, "sha256": h.hexdigest()}


def verify_anchor(anchor: dict[str, Any], expected_path: Path | str) -> None:
    """Check that the recorded start of a timing log is unchanged.

    Args:
        anchor: Path, byte count and SHA-256 from journal_anchor.
        expected_path: Timing log path for this run.

    Raises:
        ValueError: The recorded prefix changed or the record is invalid.
    """
    if (
        set(anchor) != {"path", "bytes", "sha256"}
        or Path(anchor["path"]).resolve() != Path(expected_path).resolve()
        or type(anchor["bytes"]) is not int
        or anchor["bytes"] < 0
    ):
        raise ValueError("invalid timing journal anchor")
    remaining = anchor["bytes"]
    h = hashlib.sha256()
    with Path(expected_path).open("rb") as stream:
        while remaining:
            block = stream.read(min(1 << 20, remaining))
            if not block:
                raise ValueError("timing journal lost a checkpointed prefix")
            h.update(block)
            remaining -= len(block)
    if h.hexdigest() != anchor["sha256"]:
        raise ValueError("timing journal checkpoint prefix changed")


def inventory(paths: Iterable[Path | str]) -> list[dict[str, str]]:
    """List and hash the regular files in the supplied outputs.

    Args:
        paths: Files or directories to scan in order.

    Returns:
        File pins in traversal order, with each directory sorted by filename.

    Raises:
        ValueError: A path is missing, a symlink, or not a regular file or directory.
    """
    result = []

    def visit(path: Path) -> None:
        """Collect file pins beneath one path.

        Args:
            path: File or directory to visit.
        """
        if path.is_symlink():
            raise ValueError("symlink checkpoint output: " + str(path))
        elif path.is_file():
            result.append(pin_file(path))
        elif path.is_dir():
            for child in sorted(path.iterdir()):
                visit(child)
        else:
            raise ValueError("missing or non-regular checkpoint output: " + str(path))

    for value in paths:
        visit(Path(value))
    return result


def code_identity(scripts: Path | str) -> dict[str, str]:
    """Hash Python and native source files under a package.

    Args:
        scripts: Directory holding source files.

    Returns:
        Relative path strings mapped to lowercase SHA-256 digests.
    """
    return {
        str(path.relative_to(scripts)): sha256_file(path)
        for path in sorted(Path(scripts).rglob("*"))
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix in {".py", ".cpp", ".c", ".h", ".hpp", ".sh"}
    }


def repository_identity(package: Path | str) -> dict[str, Any] | None:
    """Record the Git checkout and setup files used for this build.

    Args:
        package: Package directory in a possible Git checkout.

    Returns:
        Dictionary with commit, local diff, and setup file text, or None
        when the package is outside a Git checkout.
    """
    root = next(
        (p for p in Path(package).resolve().parents if (p / ".git").exists()), None
    )
    if root is None:
        return None

    def git(*args: str) -> str | None:
        """Run Git in the source checkout without printing.

        Args:
            args: Git subcommand and its arguments.

        Returns:
            Command output text, or None if Git returns an error status.
        """
        result = subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, text=True
        )
        return result.stdout if result.returncode == 0 else None

    result = {
        "commit": (git("rev-parse", "HEAD") or "").strip(),
        "working_changes": git("diff", "--binary", "HEAD"),
    }
    result["setup"] = {
        name: (root / name).read_text()
        for name in ("environment.yml", "pyproject.toml")
        if (root / name).is_file()
    }
    return result


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


def outside(
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
    previous = None
    total = 0.0
    for point, da, dr in sorted(events):
        if previous is not None and active and not removed:
            total += point - previous
        active += da
        removed += dr
        previous = point
    return total


class RunLock:
    """Keep two processes from writing to the same build run."""

    def __init__(self, path: Path | str) -> None:
        """Take an exclusive lock on the run's local lock file.

        Args:
            path: Lock file to open or create.

        Raises:
            ValueError: Another runner holds the lock.
        """
        self.stream = Path(path).open("a+b")
        try:
            fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.stream.close()
            raise ValueError("another pipeline runner still owns this run") from None

    def close(self) -> None:
        """Close the lock file and release the lock."""
        if not self.stream.closed:
            self.stream.close()

    def __del__(self) -> None:
        """Release the lock when the runner is collected."""
        self.close()


class Checkpoints:
    """Save and verify a build stage's completed outputs."""

    def __init__(self, root: Path | str, attempt: str) -> None:
        """Prepare the run's checkpoint directory.

        Args:
            root: Directory for stage checkpoint files.
            attempt: Identifier of the current build attempt.
        """
        self.root, self.attempt = Path(root).resolve(), attempt
        self.root.mkdir(exist_ok=True)
        self.preserved = self.root.parent / "preserved"

    def stage(self, name: str) -> Path:
        """Create or open a named stage's checkpoint directory.

        Args:
            name: Stage ID using lowercase letters, digits, hyphens or underscores.

        Returns:
            Directory for the stage.

        Raises:
            ValueError: The stage name is invalid.
        """
        if not name or any(
            c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in name
        ):
            raise ValueError("unsafe checkpoint name")
        path = self.root / name
        path.mkdir(exist_ok=True)
        return path

    def completed(
        self, name: str, invocation: dict[str, Any], outputs: Iterable[Path | str]
    ) -> bool:
        """Verify the inputs and output files of a completed stage.

        Args:
            name: Stage ID.
            invocation: Current stage inputs and expected output paths.
            outputs: Files or directories the stage should have written.

        Returns:
            True after successful verification, or False if no receipt exists.

        Raises:
            ValueError: Timing, input, or output records do not match.
        """
        path = self.stage(name) / "complete.json"
        if not path.exists():
            return False
        receipt = read_json(path)
        verify_anchor(
            receipt["timing_anchor"], self.root.parent / "timing-events.jsonl"
        )
        request = lambda value: {k: v for k, v in value.items() if k != "code"}
        if receipt.get("schema") != "worldatlas-command-checkpoint-v1" or request(
            receipt["invocation"]
        ) != request(invocation):
            raise ValueError("completed command identity changed: " + name)
        verify_pins(self.data_pins(receipt))
        if inventory(outputs) != receipt["outputs"]:
            raise ValueError("completed stage output changed: " + name)
        return True

    @staticmethod
    def data_pins(receipt: dict[str, Any]) -> list[dict[str, str]]:
        # Earlier checkpoints also included the executable Python file among
        # their inputs. Preserve the receipt and verify its data inputs only.
        """Find the input file pins that must still match on resume.

        Args:
            receipt: Completed stage record.

        Returns:
            Path and SHA-256 dictionaries for the stage's data files.
        """
        code_path = receipt["invocation"].get("code", {}).get("path")
        return [pin for pin in receipt["inputs"] if pin["path"] != code_path]

    def preserve(
        self, name: str, paths: Iterable[Path | str]
    ) -> list[tuple[Path, Path]]:
        """Move incomplete outputs aside for debugging.

        Args:
            name: Stage ID used to name the preserved directory.
            paths: Output paths to move if present.

        Returns:
            List of (original_path, preserved_path) pairs.

        Raises:
            ValueError: A path is outside the current run.
        """
        existing = list(
            dict.fromkeys(
                Path(path)
                for path in paths
                if Path(path).exists() or Path(path).is_symlink()
            )
        )
        if not existing:
            return []
        destination = self.preserved / (name + "-" + uuid.uuid4().hex)
        destination.mkdir(parents=True)
        moved = []
        for index, path in enumerate(existing):
            if (
                not path.resolve().is_relative_to(self.root.parent)
                or path.resolve() == self.root.parent
            ):
                raise ValueError("partial output outside run cannot be moved")
            target = destination / f"{index}-{path.name}"
            path.rename(target)
            moved.append((path, target))
            sync_directory(path.parent)
        sync_directory(destination)
        sync_directory(destination.parent)
        return moved

    def verify_all(self) -> None:
        """Verify the timing log and saved files for every completed stage.

        Raises:
            ValueError: A log prefix or file differs from its saved record.
        """
        for path in self.root.glob("*/attempt-*/admitted.json"):
            admission = read_json(path)
            verify_anchor(
                admission["timing_anchor"], self.root.parent / "timing-events.jsonl"
            )
        for path in self.root.glob("*/complete.json"):
            receipt = read_json(path)
            verify_anchor(
                receipt["timing_anchor"], self.root.parent / "timing-events.jsonl"
            )
            verify_pins(self.data_pins(receipt))
            if inventory(receipt["output_roots"]) != receipt["outputs"]:
                raise ValueError("completed stage output changed: " + path.parent.name)

    def begin(self, name: str) -> Path:
        """Create a directory for one stage attempt.

        Args:
            name: Stage ID.

        Returns:
            Path to the new attempt directory.
        """
        path = self.stage(name) / ("attempt-" + uuid.uuid4().hex)
        path.mkdir()
        sync_directory(path.parent)
        return path

    def complete(
        self,
        name: str,
        invocation: dict[str, Any],
        outputs: list[Path],
        inputs: list[dict[str, str]],
        timing_anchor: dict[str, str | int],
    ) -> None:
        """Write a stage's completion record after verifying its saved outputs.

        Args:
            name: Stage ID.
            invocation: Stage request used to check resume compatibility.
            outputs: Directories and files to hash as completed outputs.
            inputs: Expected path and SHA-256 pins for the inputs.
            timing_anchor: Timing log path, prefix length and digest.
        """
        verify_pins(inputs)
        write_json(
            self.stage(name) / "complete.json",
            {
                "schema": "worldatlas-command-checkpoint-v1",
                "attempt": self.attempt,
                "timing_anchor": timing_anchor,
                "invocation": invocation,
                "inputs": inputs,
                "output_roots": [os.path.abspath(p) for p in outputs],
                "outputs": inventory(outputs),
            },
        )

    def run_function(
        self,
        name: str,
        group: str,
        function: Callable[..., Any],
        args: tuple[Any, ...],
        *,
        timing: Timing,
        inputs: list[dict[str, str]],
        outputs: Iterable[Path | str],
        kwargs: dict[str, Any] | None = None,
        resume_marker: Path | str | None = None,
    ) -> Any:
        """Run a stage or load its verified result from a previous attempt.

        Args:
            name: Stage ID for the checkpoint.
            group: Timing group that contains this stage.
            function: Stage function returning JSON-compatible data.
            args: Positional arguments to the stage function.
            timing: Timing journal for the run.
            inputs: Input file pins.
            outputs: Output files and directories to verify.
            kwargs: Additional keyword arguments to the function.
            resume_marker: If present, keep partial outputs for a producer that can
                resume its own work.

        Returns:
            The stage result decoded from its saved JSON file.

        Raises:
            ValueError: An output path escapes the run or saved data no longer matches.
        """
        outputs = [Path(path).absolute() for path in outputs]
        run = self.root.parent
        if any(
            not path.resolve().is_relative_to(run.resolve())
            or path.resolve() == run.resolve()
            for path in outputs
        ):
            raise ValueError("stage output outside run or replaces run root")
        result_path = self.stage(name) / "result.json"
        invocation = {
            "stage": name,
            "inputs": inputs,
            "outputs": list(map(str, outputs)),
            "code": {"module": function.__module__, "function": function.__qualname__},
        }
        sealed = [*outputs, result_path]
        if self.completed(name, invocation, sealed):
            return read_json(result_path)
        if resume_marker is not None and Path(resume_marker).is_file():
            # The producer owns its validated internal checkpoints. Preserve
            # those outputs so it can continue completed shards or tiles.
            self.preserve(name, [result_path])
        else:
            self.preserve(name, sealed)
        attempt = self.begin(name)
        verify_pins(inputs)
        write_json(
            attempt / "admitted.json",
            {
                "invocation": invocation,
                "inputs": inputs,
                "timing_anchor": timing.anchor(),
            },
        )
        try:
            with timing.measure(group, name):
                result = function(*args, **(kwargs or {}))
            write_json(result_path, result)
        except BaseException:
            (attempt / "error.log").write_text(traceback.format_exc(), encoding="utf-8")
            raise
        self.complete(name, invocation, sealed, inputs, timing.anchor())
        return read_json(result_path)


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
    ) -> None:
        """Open a timing log and optionally start recording ongoing work.

        Args:
            path: Timing log in JSON Lines format.
            resume: Continue an existing log. Back up an incomplete last line.
            attempt: Attempt ID. Generate one if omitted.
            heartbeat_seconds: Seconds between progress entries for active work.
                Zero disables them.

        Raises:
            ValueError: A line before the last one is incomplete or invalid.
        """
        self.path = Path(path)
        self.attempt = attempt or uuid.uuid4().hex
        self.lock = threading.RLock()
        self.records = []
        self.active = {}
        self.open = set()
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
                    with backup.open("xb") as stream:
                        stream.write(raw)
                        stream.flush()
                        os.fsync(stream.fileno())
                    sync_directory(backup.parent)
                    with self.path.open("r+b") as stream:
                        stream.truncate(valid)
                        stream.flush()
                        os.fsync(stream.fileno())
                    break
                self.records.append(record)
                if record["event"] == "group-complete":
                    self.completed_groups.add(record["group"])
                valid += len(line)
        else:
            with self.path.open("x") as stream:
                stream.flush()
                os.fsync(stream.fileno())
            sync_directory(self.path.parent)
        self.event({"event": "attempt", "id": self.attempt})
        if heartbeat_seconds:
            self.thread = threading.Thread(
                target=self._heartbeat, args=(heartbeat_seconds,), daemon=True
            )
            self.thread.start()

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
            with self.path.open("a") as stream:
                for value in values:
                    stream.write(
                        json.dumps(value, sort_keys=True, allow_nan=False) + "\n"
                    )
                stream.flush()
                os.fsync(stream.fileno())
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
    ) -> Iterator[dict[str, Any]]:
        """Record when a piece of work starts and stops.

        Args:
            group: Parent stage to which this work contributes.
            name: Name of the work within the stage.
            kind: Timing category such as processing or command.

        Yields:
            The start-event dictionary. When the block ends, it also includes
            "end_monotonic_seconds", even if the work failed.
        """
        started = time.monotonic()
        token = uuid.uuid4().hex
        record = {
            "event": "start",
            "token": token,
            "id": f"{group}/{name}",
            "group": group,
            "kind": kind,
            "monotonic_seconds": started,
        }
        with self.lock:
            self.event(record)
            self.active[token] = record
            self.open.add(token)
        try:
            yield record
        except BaseException:
            self._finish(token, record, started, "failed")
            raise
        else:
            self._finish(token, record, started, "complete")

    def _finish(
        self, token: str, record: dict[str, Any], started: float, event: str
    ) -> None:
        """Record an interval's end and remove it from active work.

        Args:
            token: Unique interval ID.
            record: Start-event dictionary to update with the end time.
            started: Monotonic clock reading at the start.
            event: Outcome, either "complete" or "failed".
        """
        with self.lock:
            ended = time.monotonic()
            record["end_monotonic_seconds"] = ended
            self.event(
                {
                    "event": event,
                    "token": token,
                    "id": record["id"],
                    "group": record["group"],
                    "start_monotonic_seconds": started,
                    "monotonic_seconds": ended,
                }
            )
            self.active.pop(token, None)
            self.open.discard(token)

    def anchor(self) -> dict[str, str | int]:
        """Hash the current timing log while writes are locked.

        Returns:
            Dictionary with the path, saved prefix length and SHA-256.
        """
        with self.lock:
            return journal_anchor(self.path)

    def mark_complete(
        self, group: str, *, physical_report: dict[str, Any] | None = None
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
            summary = self.summary(physical_report)[group]
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
        incomplete = [
            {"attempt": record.get("attempt"), "id": record["id"]}
            for record in self.records
            if record["event"] == "unmeasured-initialization"
            and record.get("group") == group
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
        self, physical_report: dict[str, Any] | None
    ) -> dict[str, dict[str, Any]]:
        """Summarize wall-clock time for each stage without counting overlap twice.

        Args:
            physical_report: Physical producer report, reuse record, or None before
                output is ready.

        Returns:
            Stage names mapped to report dictionaries with processing seconds,
            output readiness, and details of any intervals with unknown ends.
        """
        groups = {}
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
        for group in names:
            intervals, missing, interrupted = self.interval_details(group)
            measured = sum(elapsed_union(items) for items in intervals.values())
            complete = not missing
            error = None
            downloads = None
            reused = (
                group == "physical"
                and physical_report
                and physical_report.get("status") == "reused"
            )
            if reused:
                downloads = 0.0
            elif group == "physical":
                report = physical_report or {}
                commands, _ = self.intervals(group, kind="command")
                overhead = sum(
                    outside(items, commands.get(attempt, []))
                    for attempt, items in intervals.items()
                )
                child = report.get(
                    "recorded_processing_elapsed_seconds",
                    report.get("processing_elapsed_seconds"),
                )
                if (
                    type(child) not in (int, float)
                    or not math.isfinite(cast(float, child))
                    or cast(float, child) < 0
                ):
                    child = sum(
                        record["seconds"]
                        for record in self.records
                        if record["event"] == "physical-invocation-processing"
                    )
                    complete = False
                    error = "physical producer has no valid measured processing total"
                command_overhead = sum(
                    record["seconds"]
                    for record in self.records
                    if record["event"] == "physical-command-overhead"
                )
                measured = overhead + command_overhead + cast(float, child)
                complete = (
                    complete
                    and report.get("timing_complete", True)
                    and report.get("status") == "candidate-only"
                )
                downloads = report.get("source_download_elapsed_seconds")
                if (
                    type(downloads) not in (int, float)
                    or not math.isfinite(cast(float, downloads))
                    or cast(float, downloads) < 0
                ):
                    complete = False
                    error = "missing or invalid physical acquisition timing"
            outputs_complete = group in self.completed_groups
            groups[group] = {
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
            }
            if group == "physical":
                groups[group].update(
                    {
                        "source_download_elapsed_seconds": downloads,
                        "producer_processing_elapsed_seconds": (
                            physical_report.get("processing_elapsed_seconds")
                            if physical_report and not reused
                            else None
                        ),
                        "timing_error": error,
                    }
                )
                if reused and physical_report is not None:
                    groups[group]["reused_from"] = physical_report["source_run"]
        return groups
