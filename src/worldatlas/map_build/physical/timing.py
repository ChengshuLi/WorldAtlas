"""Record physical checkpoints, processing time, and source transfers."""

import json
import math
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from worldatlas.map_build.execution.journal import (
    append_records,
    create_journal,
    preserve_torn_tail,
)
from worldatlas.map_build.execution.timing import PhysicalDurations, elapsed_union
from worldatlas.shared.files import sync_directory
from worldatlas.source_assets.cache import Download

PROCESSING_LOG = "processing-events.jsonl"


class ProcessingJournal:
    """Record physical work that survives a restart."""

    def __init__(self, output: Path, started: float, resume: bool) -> None:
        """Open the journal and record the start of this attempt.

        Args:
            output: Physical run directory.
            started: Start time from the monotonic performance clock.
            resume: Continue an existing journal, saving any partial final entry.
        """
        self.path = output / PROCESSING_LOG
        self.started = started
        self.attempt = uuid.uuid4().hex
        self.lock = threading.Lock()
        self.durations: PhysicalDurations | None = None
        self.events = []
        if resume:
            raw = self.path.read_bytes()
            end = raw.rfind(b'\n') + 1
            if end < len(raw):
                interrupted = output / 'interrupted'
                interrupted.mkdir(mode=0o700, exist_ok=True)
                sync_directory(output)
                tail = interrupted / ('journal-tail-' + uuid.uuid4().hex)
                preserve_torn_tail(self.path, end, tail, raw[end:])
            self.events = [json.loads(line) for line in raw[:end].splitlines()]
        else:
            create_journal(self.path)
        self.add({'event': 'attempt_start', 'attempt': self.attempt})

    def add(self, event: dict[str, Any]) -> None:
        """Append an event to disk and the in-memory journal.

        Args:
            event: JSON-compatible event fields.
        """
        with self.lock:
            append_records(self.path, [event])
            self.events.append(event)

    def unit(
        self, name: str, started: float, report_sha256: str, output_sha256: str
    ) -> None:
        """Record one completed output and its measured work.

        Args:
            name: Name of the task that produced the files.
            started: Clock reading when the task began.
            report_sha256: Verified checksum of the producer report.
            output_sha256: Verified checksum of the primary output.
        """
        ended = time.monotonic()
        self.add(
            {
                'event': 'unit_complete',
                'attempt': self.attempt,
                'unit': name,
                'start_monotonic_seconds': started,
                'end_monotonic_seconds': ended,
                'processing_elapsed_seconds': ended - started,
                'report_sha256': report_sha256,
                'output_sha256': output_sha256,
            }
        )

    def record_download(self, transfer: Download, source: str) -> None:
        """Record the time spent transferring one coastline ZIP or water shard.

        Args:
            transfer: Transfer time interval with its outcome.
            source: Input type, either "land" or "water".
        """
        self.add(
            {
                'event': 'download_complete'
                if transfer.completed
                else 'download_failed',
                'attempt': self.attempt,
                'source': source,
                'start_monotonic_seconds': transfer.started,
                'end_monotonic_seconds': transfer.ended,
                'seconds': transfer.ended - transfer.started,
            }
        )

    def recorded_time(self, attempt: str) -> tuple[float, float]:
        """Count recorded processing and download-only time for one attempt.

        Args:
            attempt: ID of the physical build attempt.

        Returns:
            (processing_seconds, download_only_seconds). Concurrent transfers
            count once, and time spent rasterizing counts as processing.
        """
        processing = []
        downloads = []
        serial_downloads = 0.0
        for event in self.events:
            if event['attempt'] != attempt:
                continue
            if event['event'] == 'unit_complete':
                intervals = processing
            elif event['event'] in ('download_complete', 'download_failed'):
                # Older journals measured serial transfers by duration alone.
                if 'start_monotonic_seconds' not in event:
                    serial_downloads += event['seconds']
                    continue
                intervals = downloads
            else:
                continue
            intervals.append(
                (event['start_monotonic_seconds'], event['end_monotonic_seconds'])
            )
        active = elapsed_union(processing)
        return active, elapsed_union(processing + downloads) - active + serial_downloads

    def finish(self, status: str) -> None:
        """Record the attempt's final duration and status.

        Args:
            status: Outcome such as complete or failed.
        """
        if self.durations is not None:
            raise ValueError('attempt already ended')
        elapsed = time.monotonic() - self.started
        _, download_only = self.recorded_time(self.attempt)
        if not math.isfinite(elapsed) or elapsed < download_only:
            raise ValueError('invalid attempt timing')
        durations = PhysicalDurations(elapsed - download_only, download_only)
        self.add(
            {
                'event': 'attempt_end',
                'attempt': self.attempt,
                'status': status,
                'processing_elapsed_seconds': durations.processing,
                'source_download_elapsed_seconds': durations.download_only,
            }
        )
        self.durations = durations

    def summary(self) -> dict[str, Any]:
        """Summarize work across physical build attempts.

        Returns:
            Dictionary with known processing and download seconds. A missing
            end time leaves processing as a lower bound.
        """
        if any(
            e.get('event')
            not in (
                'attempt_start',
                'attempt_end',
                'unit_complete',
                'download_complete',
                'download_failed',
            )
            for e in self.events
        ):
            raise ValueError('unknown processing journal event')
        starts = {
            e['attempt'] for e in self.events if e.get('event') == 'attempt_start'
        }
        ends = {e['attempt']: e for e in self.events if e.get('event') == 'attempt_end'}
        if (
            len(starts) != sum(e.get('event') == 'attempt_start' for e in self.events)
            or len(ends) != sum(e.get('event') == 'attempt_end' for e in self.events)
            or not set(ends) <= starts
        ):
            raise ValueError('invalid processing journal attempts')
        if any(e.get('status') not in ('complete', 'failed') for e in ends.values()):
            raise ValueError('invalid processing journal status')
        if any(e.get('attempt') not in starts for e in self.events):
            raise ValueError('processing journal event without attempt')
        if any(
            type(e.get(k)) not in (int, float) or not math.isfinite(e[k]) or e[k] < 0
            for e in ends.values()
            for k in ('processing_elapsed_seconds', 'source_download_elapsed_seconds')
        ):
            raise ValueError('invalid processing journal duration')
        if any(
            type(e.get('seconds')) not in (int, float)
            or not math.isfinite(e['seconds'])
            or e['seconds'] < 0
            for e in self.events
            if e.get('event') in ('download_complete', 'download_failed')
        ):
            raise ValueError('invalid processing journal download duration')
        missing = starts - set(ends)
        lower = sum(e['processing_elapsed_seconds'] for e in ends.values())
        download = sum(e['source_download_elapsed_seconds'] for e in ends.values())
        for attempt in missing:
            processing, download_only = self.recorded_time(attempt)
            lower += processing
            download += download_only
        return {
            'timing_complete': not missing,
            'processing_elapsed_seconds': lower if not missing else None,
            'recorded_processing_elapsed_seconds': lower,
            'source_download_elapsed_seconds': download,
            'source_download_elapsed_scope': 'complete'
            if not missing
            else 'recorded-lower-bound',
            'invocation_processing_elapsed_seconds': ends[self.attempt][
                'processing_elapsed_seconds'
            ],
            'invocation_source_download_elapsed_seconds': ends[self.attempt][
                'source_download_elapsed_seconds'
            ],
        }

    def checkpoint(self, name: str) -> dict[str, Any] | None:
        """Look up the latest saved completion for a physical task.

        Args:
            name: Physical task or water shard name.

        Returns:
            The event with output hashes and timings, or None if the task is unfinished.
        """
        for event in reversed(self.events):
            if event.get('event') == 'unit_complete' and event.get('unit') == name:
                return event
        return None

    def downloaded_water_shards(self) -> int:
        """Count successful water shard transfers for this attempt.

        Returns:
            Number of water files transferred, excluding cache hits.
        """
        return sum(
            event['event'] == 'download_complete'
            and event['attempt'] == self.attempt
            and event['source'] == 'water'
            for event in self.events
        )
