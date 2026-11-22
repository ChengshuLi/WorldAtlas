#!/usr/bin/env python3
"""Wire pinned raw land and water sources into a candidate physical grid."""

import argparse
import fcntl
import hashlib
import json
import math
import os
import re
import shutil
import sys
import threading
import time
import uuid
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import closing, nullcontext
from contextvars import copy_context
from pathlib import Path
from typing import Any

import boto3
from botocore.client import BaseClient

import worldatlas.geodesy.ogr as geometry_io
from worldatlas.map_build.execution import control
from worldatlas.map_build.execution.runtime import elapsed_union
from worldatlas.map_build.physical import composition, land, water
from worldatlas.map_build.physical import union as water_union
from worldatlas.shared.files import read_json, sha256_file, sync_directory, write_json
from worldatlas.source_assets.catalog import stream_source

HERE = Path(__file__).resolve().parent


def read_pin(spec: dict[str, str]) -> tuple[Path, bytes, dict[str, Any]]:
    """Verify and read a pinned JSON file.

    Args:
        spec: Record containing "path" and expected "sha256".

    Returns:
        (resolved_path, original_bytes, decoded_settings).

    Raises:
        ValueError: The file differs from the expected hash or is invalid JSON.
    """
    path = Path(spec['path']).resolve()
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != spec['sha256']:
        raise ValueError(f'input hash mismatch: {path}')
    return path, data, json.loads(data)


def run_stage(function: Callable[..., Any], *args: Any) -> Any:
    """Call a physical build stage using the current progress logger.

    Args:
        function: Stage that takes an emit callback.
        args: Other positional arguments to the stage.

    Returns:
        The stage's result, typically a report dictionary.
    """
    return function(*args, emit=control.emit)


def validate_r2_endpoint(endpoint: object) -> None:
    """Require an HTTPS account endpoint for an R2 download.

    Args:
        endpoint: Candidate account URL.

    Raises:
        ValueError: The URL is absent or is not a valid R2 account endpoint.
    """
    if not isinstance(endpoint, str) or not re.fullmatch(
        r'https://[0-9a-f]{32}(?:\.(?:eu|us|fedramp))?\.r2\.cloudflarestorage\.com',
        endpoint,
    ):
        raise ValueError(
            'R2 endpoint must be an HTTPS Cloudflare R2 S3 account endpoint'
        )


def make_r2_client(endpoint: str | None) -> BaseClient:
    """Create an S3-compatible client for the R2 account.

    Args:
        endpoint: HTTPS account URL.

    Returns:
        Open client using the caller's configured credentials.
    """
    validate_r2_endpoint(endpoint)
    return boto3.client('s3', endpoint_url=endpoint, region_name='auto')


def validate_shard_staging(
    configuration: dict[str, Any], *, require_r2: bool = False
) -> tuple[int, dict[str, str] | None]:
    """Check the water-shard worker count and how the shards are supplied.

    Args:
        configuration: Physical settings with optional ``max_parallel_shards``
            and ``source_staging`` fields.
        require_r2: Require R2 staging for a replay that starts with an empty cache.

    Returns:
        The worker count and the R2 settings. The settings are None when the
        build reads local shards.

    Raises:
        ValueError: The worker count or R2 staging configuration is invalid.
    """
    workers = configuration.get('max_parallel_shards', 2)
    if type(workers) is not int or workers < 1:
        raise ValueError('max_parallel_shards must be a positive integer')
    staging = configuration.get('source_staging')
    if staging is None:
        if require_r2:
            raise ValueError('release replay requires R2 staging for raw-water shards')
    else:
        if (
            not isinstance(staging, dict)
            or set(staging) != {'mode', 'endpoint_url'}
            or staging['mode'] != 'r2-s3'
        ):
            raise ValueError('R2 staging requires r2-s3 mode and endpoint_url')
        validate_r2_endpoint(staging['endpoint_url'])
    return workers, staging


def validate_r2_shard_location(entry: dict[str, Any]) -> None:
    """Check whether a frozen raw-water shard can be downloaded from R2.

    Args:
        entry: Raw manifest entry after any catalog reference has been resolved.

    Raises:
        ValueError: The R2 bucket, object key, or byte size is missing or invalid.
    """
    if (
        not isinstance(entry.get('r2_bucket'), str)
        or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,62}', entry['r2_bucket'])
        or not isinstance(entry.get('r2_key'), str)
        or not entry['r2_key']
        or type(entry.get('size_bytes')) is not int
        or entry['size_bytes'] < 0
    ):
        raise ValueError('missing or invalid pinned R2 source metadata')


def download_r2(endpoint: str, entry: dict[str, Any], destination: Path) -> None:
    """Download one water shard to a new local file.

    Keep an interrupted file for inspection.

    Args:
        endpoint: R2 account URL.
        entry: Shard's bucket, key and byte count.
        destination: Local path that must not exist.

    Raises:
        ValueError: The transfer size or object location is invalid.
        InterruptedError: The stage was cancelled.
    """
    control.check_cancelled()
    with closing(make_r2_client(endpoint)) as client, destination.open('xb') as stream:
        try:
            stream_source(
                client,
                entry,
                stream,
                check_cancelled=control.check_cancelled,
            )
        except ValueError as exc:
            raise ValueError(
                'staged source size/hash mismatch: ' + str(destination)
            ) from exc


class ProcessingJournal:
    """Record physical work that survives a restart."""

    def __init__(self, output: Path, started: float, resume: bool) -> None:
        """Open the journal and record the start of this attempt.

        Args:
            output: Physical run directory.
            started: Start time from the monotonic performance clock.
            resume: Continue an existing journal, saving any partial final entry.
        """
        self.path = output / 'processing-events.jsonl'
        self.started = started
        self.attempt = uuid.uuid4().hex
        self.lock = threading.Lock()
        self.finished = False
        self.events = []
        if resume:
            raw = self.path.read_bytes()
            end = raw.rfind(b'\n') + 1
            if end < len(raw):
                interrupted = output / 'interrupted'
                interrupted.mkdir(mode=0o700, exist_ok=True)
                sync_directory(output)
                tail = interrupted / ('journal-tail-' + uuid.uuid4().hex)
                with tail.open('xb') as f:
                    f.write(raw[end:])
                    f.flush()
                    os.fsync(f.fileno())
                fd = os.open(interrupted, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
                with self.path.open('r+b') as f:
                    f.truncate(end)
                    f.flush()
                    os.fsync(f.fileno())
            self.events = [json.loads(line) for line in raw[:end].splitlines()]
        else:
            with self.path.open('x') as f:
                f.flush()
                os.fsync(f.fileno())
            sync_directory(output)
        self.add({'event': 'attempt_start', 'attempt': self.attempt})

    def add(self, event: dict[str, Any]) -> None:
        """Append an event to disk and the in-memory journal.

        Args:
            event: JSON-compatible event fields.
        """
        with self.lock:
            with self.path.open('a') as f:
                f.write(json.dumps(event, sort_keys=True, allow_nan=False) + '\n')
                f.flush()
                os.fsync(f.fileno())
            self.events.append(event)

    def unit(self, name: str, started: float, report: Path, output: Path) -> None:
        """Record one completed output and its measured work.

        Args:
            name: Name of the task that produced the files.
            started: Clock reading when the task began.
            report: Saved report to hash.
            output: Produced file to hash.
        """
        ended = time.perf_counter()
        self.add(
            {
                'event': 'unit_complete',
                'attempt': self.attempt,
                'unit': name,
                'start_monotonic_seconds': started,
                'end_monotonic_seconds': ended,
                'processing_elapsed_seconds': ended - started,
                'report_sha256': sha256_file(report),
                'output_sha256': sha256_file(output),
            }
        )

    def download_done(self, started: float) -> None:
        """Record when a shard download began and ended.

        Args:
            started: Clock reading before the transfer.
        """
        ended = time.perf_counter()
        self.add(
            {
                'event': 'download_complete',
                'attempt': self.attempt,
                'start_monotonic_seconds': started,
                'end_monotonic_seconds': ended,
                'seconds': ended - started,
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
            elif event['event'] == 'download_complete':
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
        if self.finished:
            raise ValueError('attempt already ended')
        elapsed = time.perf_counter() - self.started
        _, download_only = self.recorded_time(self.attempt)
        if not math.isfinite(elapsed) or elapsed < download_only:
            raise ValueError('invalid attempt timing')
        self.add(
            {
                'event': 'attempt_end',
                'attempt': self.attempt,
                'status': status,
                'processing_elapsed_seconds': elapsed - download_only,
                'source_download_elapsed_seconds': download_only,
            }
        )
        self.finished = True

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
            if e.get('event') == 'download_complete'
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


def run(
    manifest_path: Path | str, output: Path | str, *, resume: bool = False
) -> dict[str, Any]:
    """Build or resume the physical grid under an exclusive run lock.

    Args:
        manifest_path: JSON configuration with pins for land and water sources.
        output: Directory that holds this physical run.
        resume: Whether to continue a run already started.

    Returns:
        Report dictionary with the land, water and physical layer outputs
        and recorded processing and download times.

    Raises:
        ValueError: Settings, saved files, or the run lock are incompatible.
    """
    started = time.perf_counter()
    output = Path(output).resolve()
    if not output.parent.is_dir():
        raise ValueError('output parent must exist')
    lock_path = output.parent / (output.name + '.lock')
    with lock_path.open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('physical pipeline already running') from None
        journal: list[ProcessingJournal | None] = [None]
        try:
            return _run(manifest_path, output, started, resume, journal)
        except BaseException:
            if journal[0] is not None and not journal[0].finished:
                journal[0].finish('failed')
            raise


def _run(
    manifest_path: Path | str,
    output: Path,
    processing_started: float,
    resume: bool,
    journal_slot: list[ProcessingJournal | None],
) -> dict[str, Any]:
    """Rasterize the sources, union water masks, and compose the physical grid.

    Args:
        manifest_path: Physical build settings.
        output: Locked physical run directory.
        processing_started: Clock reading from the start of the attempt.
        resume: Whether to look for completed outputs before rasterizing.
        journal_slot: Single slot for the active journal so the caller can
            record failures.

    Returns:
        Physical build report, including the completed output file pins.
    """
    manifest_path = Path(manifest_path).resolve()
    data = manifest_path.read_bytes()
    cfg = json.loads(data)
    if cfg.get('schema') != 'raw-physical-pipeline-v1' or not cfg.get(
        'selection_notes'
    ):
        raise ValueError('explicit pipeline schema and selection notes required')
    reserve = cfg.get('minimum_free_bytes', 2 * (1 << 30))
    # Keep the worker count configurable; use complete-source profiles to
    # balance CPU throughput against disk headroom for on-demand shard staging.
    workers, staging = validate_shard_staging(cfg)
    if not isinstance(reserve, int) or isinstance(reserve, bool) or reserve < 0:
        raise ValueError('invalid free-space reserve')
    land_path, land_bytes, land_cfg = read_pin(cfg['land_config'])
    water_path, water_bytes, water_cfg = read_pin(cfg['water_config'])
    if water_cfg.get('rasterizer', 'gdal') not in ('gdal', 'python'):
        raise ValueError(
            'water rasterizer must be gdal or python; runtime native compilation is retired'
        )
    if 'native_method' in water_cfg:
        raise ValueError('retired native_method; use batch_method')
    source_path, source_bytes, source = read_pin(cfg['source_manifest'])
    grid = land_cfg['grid']
    if grid != water_cfg['grid']:
        raise ValueError('land and water grids differ')
    batch_size = water_cfg.get('batch_size', 8192)
    if type(batch_size) is not int or batch_size < 1:
        raise ValueError('water batch_size must be a positive integer')
    union_rows_per_block = cfg.get('union_rows_per_block', 128)
    physical_rows_per_block = cfg.get('physical_rows_per_block', 128)
    for value in (union_rows_per_block, physical_rows_per_block):
        if type(value) is not int or value < 1:
            raise ValueError('rows_per_block must be a positive integer')
    for stage in (land_cfg, water_cfg):
        if stage.get('minimum_free_bytes', 2 * (1 << 30)) < reserve:
            raise ValueError('stage free-space reserve is below pipeline reserve')
    files = source.get('files')
    if (
        not isinstance(files, list)
        or not files
        or source.get('file_count') != len(files)
    ):
        raise ValueError('source manifest must list every raw shard')
    raw = []
    for entry in files:
        rel = Path(entry['path'])
        if rel.is_absolute() or '..' in rel.parts:
            raise ValueError('raw source paths must be relative to manifest directory')
        path = (source_path.parent / rel).resolve()
        if not path.is_relative_to(source_path.parent):
            raise ValueError('raw source escapes manifest directory')
        digest = entry['sha256']
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(c not in '0123456789abcdef' for c in digest)
        ):
            raise ValueError('invalid raw source digest')
        if staging is not None and not path.is_file():
            validate_r2_shard_location(entry)
        raw.append((path, digest, entry))
    if len({x[0] for x in raw}) != len(raw) or len({x[1] for x in raw}) != len(raw):
        raise ValueError('raw source paths and hashes must be unique')
    scripts = {
        name: sha256_file(HERE / name)
        for name in (
            'build.py',
            'sources.py',
            'land.py',
            'water.py',
            'water_batch.py',
            'union.py',
            'composition.py',
        )
    }
    scripts['geodesy/ogr.py'] = sha256_file(geometry_io.__file__)
    output = Path(output).resolve()
    inputs = [land_path, water_path, source_path] + [x[0] for x in raw]
    inputs += [
        Path(item['path']).resolve()
        for spec in land_cfg['land']
        for item in spec['files']
    ]
    for key in ('water_reference', 'physical_reference_mask'):
        if cfg.get(key):
            inputs.append(Path(cfg[key]['path']).resolve())
    if cfg.get('physical_reference_streams'):
        inputs += [
            Path(cfg['physical_reference_streams'][k]['path']).resolve()
            for k in ('rows', 'runs')
        ]
    if bool(cfg.get('physical_reference_mask')) != bool(
        cfg.get('physical_reference_streams')
    ):
        raise ValueError(
            'physical reference mask and streams must be supplied together'
        )
    # The build configuration can sit beside the output directory.
    if manifest_path.is_relative_to(output) or any(
        p.is_relative_to(output) or output.is_relative_to(p.parent) for p in inputs
    ):
        raise ValueError(
            'output must be outside all input directories and must not contain inputs'
        )
    if shutil.disk_usage(output.parent).free < reserve:
        raise ValueError('free disk below pipeline reserve')
    source_pins = [item for spec in land_cfg['land'] for item in spec['files']]
    if any(sha256_file(p['path']) != p['sha256'] for p in source_pins):
        raise ValueError('land source hash mismatch')
    identity = {
        'schema': 'raw-physical-resume-identity-v1',
        'configuration_sha256': hashlib.sha256(data).hexdigest(),
        'land_config': cfg['land_config'],
        'water_config': cfg['water_config'],
        'source_manifest': cfg['source_manifest'],
        'script_sha256': scripts,
        'land_source_pins': source_pins,
    }
    identity_path = output / 'pipeline-identity.json'
    if resume:
        previous = read_json(identity_path) if identity_path.is_file() else {}
        data_identity = lambda value: {
            k: v for k, v in value.items() if k != 'script_sha256'
        }
        if not output.is_dir() or data_identity(previous) != data_identity(identity):
            raise ValueError('physical resume identity mismatch')
        if (output / 'report.json').exists():
            report = read_json(output / 'report.json')
            stages = report.get('stage_reports', {})
            if (
                report.get('status') != 'candidate-only'
                or report.get('configuration_sha256')
                != identity['configuration_sha256']
                or report.get('pipeline_identity_sha256') != sha256_file(identity_path)
                or report.get('processing_journal_sha256')
                != sha256_file(output / 'processing-events.jsonl')
                or set(stages) != {'land', 'union', 'physical'}
                or any(
                    Path(stages[k]['path']).resolve() != output / k / 'report.json'
                    or sha256_file(stages[k]['path']) != stages[k]['sha256']
                    for k in stages
                )
            ):
                raise ValueError('completed physical report mismatch')
            for key, name in (('land', 'land.tif'), ('union', 'water-union.tif')):
                stage = read_json(output / key / 'report.json')
                digest = stage['land_sha256' if key == 'land' else 'union_sha256']
                if sha256_file(output / key / name) != digest:
                    raise ValueError('completed stage output mismatch: ' + key)
            union = read_json(output / 'union/report.json')
            saved_shards = union.get('shards')
            if not isinstance(saved_shards, list) or len(saved_shards) != len(raw):
                raise ValueError('completed shard inventory mismatch')
            for i, (entry, (source, digest, _)) in enumerate(zip(saved_shards, raw)):
                directory = output / 'shards' / f'{i:05d}'
                rp = directory / 'report.json'
                tif = directory / 'water.tif'
                sp = entry.get('report', {})
                if (
                    Path(entry.get('path', '')).resolve() != tif
                    or Path(sp.get('path', '')).resolve() != rp
                    or sha256_file(rp) != sp.get('sha256')
                    or sha256_file(tif) != entry.get('sha256')
                    or entry.get('status') != 'candidate-only'
                ):
                    raise ValueError(f'completed shard checkpoint mismatch: {i}')
                item = read_json(rp)
                if (
                    item.get('source_sha256') != digest
                    or Path(item.get('source', '')).name != source.name
                    or item.get('configuration_sha256') != cfg['water_config']['sha256']
                    or item.get('grid') != grid
                    or item.get('policy') != water_cfg.get('policy')
                    or item.get('batch_size') != batch_size
                    or item.get('output_sha256') != entry['sha256']
                ):
                    raise ValueError(f'completed shard report mismatch: {i}')
            physical = read_json(output / 'physical/report.json')
            outputs = physical.get('output_sha256', {})
            if outputs != report.get('physical_output_sha256') or any(
                sha256_file(output / 'physical' / name) != outputs.get(name)
                for name in ('physical-dry.tif', 'rows.u32le', 'runs.u32le')
            ):
                raise ValueError('completed physical output mismatch')
            return report
    else:
        os.mkdir(output)
        sync_directory(output.parent)
        (output / 'configs').mkdir()
        (output / 'shards').mkdir()
        write_json(identity_path, identity, sort_keys=False)
    journal_exists = (output / 'processing-events.jsonl').exists()
    if resume and not journal_exists:
        if (
            (output / 'land').exists()
            or (output / 'union').exists()
            or (output / 'physical').exists()
            or any((output / 'shards').iterdir())
            or any((output / 'configs').iterdir())
        ):
            raise ValueError('missing processing journal for existing checkpoints')
    journal = ProcessingJournal(output, processing_started, resume and journal_exists)
    journal_slot[0] = journal
    if resume and not journal_exists:
        journal.add(
            {
                'event': 'attempt_start',
                'attempt': 'unrecorded-before-journal-' + uuid.uuid4().hex,
            }
        )

    def prior(name: str) -> dict[str, Any] | None:
        """Find the last completed checkpoint for a named task.

        Args:
            name: Physical task or shard name.

        Returns:
            Saved event dictionary, or None if the task has not completed.
        """
        matches = [
            e
            for e in journal.events
            if e.get('event') == 'unit_complete' and e.get('unit') == name
        ]
        return matches[-1] if matches else None

    def quarantine(path: Path) -> None:
        """Move existing partial output aside for inspection.

        Args:
            path: Output to move when present.
        """
        if path.exists():
            target = output / 'interrupted'
            target.mkdir(mode=0o700, exist_ok=True)
            sync_directory(output)
            os.rename(path, target / (path.name + '-' + uuid.uuid4().hex))
            sync_directory(path.parent)
            sync_directory(target)

    land_dir = output / 'land'
    land_checkpoint = prior('land') if resume else None
    if land_checkpoint:
        land_report = read_json(land_dir / 'report.json')
        if (
            sha256_file(land_dir / 'report.json') != land_checkpoint['report_sha256']
            or sha256_file(land_dir / 'land.tif') != land_checkpoint['output_sha256']
            or land_report.get('status') != 'candidate-only'
            or land_report.get('configuration_sha256') != cfg['land_config']['sha256']
            or land_report.get('grid') != grid
            or land_report.get('land_sha256') != land_checkpoint['output_sha256']
        ):
            raise ValueError('land checkpoint mismatch')
    else:
        if resume:
            quarantine(land_dir)
        unit_start = time.perf_counter()
        run_stage(land.run, land_path, land_dir)
        land_report = read_json(land_dir / 'report.json')
        if land_report.get('status') != 'candidate-only' or land_report.get(
            'land_sha256'
        ) != sha256_file(land_dir / 'land.tif'):
            raise ValueError('land raster is incomplete')
        journal.unit(
            'land', unit_start, land_dir / 'report.json', land_dir / 'land.tif'
        )

    download_slot = threading.Lock()
    raster_slot = threading.Lock() if staging is not None else nullcontext()

    def build_shard(
        item: tuple[int, tuple[Path, str, dict[str, Any]]],
    ) -> dict[str, Any]:
        """Validate or build a single water shard's raster.

        Args:
            item: Shard index and its (path, expected_hash, source_record).

        Returns:
            Dictionary with verified raster and report paths and digests.
        """
        control.check_cancelled()
        i, (path, digest, entry) = item
        destination = output / 'shards' / f'{i:05d}'
        # Keep the manifest's directory structure so equal basenames can run together.
        staged = output / 'source-staging' / path.relative_to(source_path.parent)
        checkpoint = prior(f'shard-{i:05d}') if resume else None
        if checkpoint:
            report_path = destination / 'report.json'
            report = read_json(report_path)
            if (
                sha256_file(report_path) != checkpoint['report_sha256']
                or sha256_file(destination / 'water.tif') != checkpoint['output_sha256']
                or report.get('status') != 'candidate-only'
                or report.get('source_sha256') != digest
                or Path(report.get('source', '')).name != path.name
                or report.get('configuration_sha256') != cfg['water_config']['sha256']
                or report.get('grid') != grid
                or report.get('policy') != water_cfg.get('policy')
                or report.get('batch_size') != batch_size
                or report.get('output_sha256') != checkpoint['output_sha256']
            ):
                raise ValueError(f'shard checkpoint mismatch: {i}')
            if (
                staged.is_file()
                and staged.stat().st_size == entry.get('size_bytes')
                and sha256_file(staged) == digest
            ):
                staged.unlink()
            return {
                'path': str(destination / 'water.tif'),
                'sha256': checkpoint['output_sha256'],
                'status': 'candidate-only',
                'report': {
                    'path': str(report_path),
                    'sha256': checkpoint['report_sha256'],
                },
            }
        if resume:
            quarantine(destination)
        owned = False
        if not path.is_file() and staging is not None:
            staged.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            if staged.exists() and (
                not staged.is_file()
                or staged.stat().st_size != entry['size_bytes']
                or sha256_file(staged) != digest
            ):
                quarantine(staged)
            if not staged.exists():
                with download_slot:
                    started = time.perf_counter()
                    try:
                        download_r2(staging['endpoint_url'], entry, staged)
                    finally:
                        journal.download_done(started)
            if (
                not staged.is_file()
                or staged.stat().st_size != entry['size_bytes']
                or sha256_file(staged) != digest
            ):
                raise ValueError(f'staged source size/hash mismatch: {path}')
            path = staged
            owned = True
        with raster_slot:
            control.check_cancelled()
            unit_start = time.perf_counter()
            run_stage(water.run, path, digest, destination, water_path, batch_size)
        report_path = destination / 'report.json'
        report = read_json(report_path)
        if (
            report.get('status') != 'candidate-only'
            or report.get('source_sha256') != digest
            or report.get('configuration_sha256') != cfg['water_config']['sha256']
            or report.get('output_sha256') != sha256_file(destination / 'water.tif')
        ):
            raise ValueError(f'incomplete water shard: {path}')
        journal.unit(
            f'shard-{i:05d}', unit_start, report_path, destination / 'water.tif'
        )
        if owned:
            path.unlink()
        return {
            'path': str(destination / 'water.tif'),
            'sha256': report['output_sha256'],
            'status': report['status'],
            'report': {'path': str(report_path), 'sha256': sha256_file(report_path)},
        }

    # R2 staging overlaps one download with one rasterization. Local shards
    # can rasterize concurrently without a download slot.
    # Keep masks in manifest order regardless of when each worker finishes.
    shards: list[dict[str, Any] | None] = [None] * len(raw)
    with (
        control.stage() as cancelled,
        ThreadPoolExecutor(max_workers=min(workers, len(raw))) as pool,
    ):
        futures = {
            pool.submit(copy_context().run, build_shard, item): item[0]
            for item in enumerate(raw)
        }
        try:
            for future in as_completed(futures):
                shards[futures[future]] = future.result()
        except BaseException:
            cancelled.set()
            for future in futures:
                future.cancel()
            raise
    union_cfg: dict[str, Any] = {
        'schema': 'water-union-comparison-v1',
        'grid': grid,
        'selection_notes': cfg['selection_notes'],
        'minimum_free_bytes': reserve,
        'source_manifest': cfg['source_manifest'],
        'shard_count': len(shards),
        'rows_per_block': union_rows_per_block,
        'shards': shards,
    }
    if cfg.get('water_reference'):
        union_cfg['reference'] = cfg['water_reference']

    def bind_config(path: Path, value: dict[str, Any]) -> None:
        """Save the generated settings or check they match the previous attempt.

        Args:
            path: Configuration file in the current run.
            value: Expected JSON settings.

        Raises:
            ValueError: An existing file differs or belongs to a fresh run.
        """
        if path.exists():
            if not resume or read_json(path) != value:
                raise ValueError('resumed stage config mismatch')
        else:
            write_json(path, value, sort_keys=False)

    union_config = output / 'configs/union.json'
    bind_config(union_config, union_cfg)
    union_dir = output / 'union'
    union_checkpoint = prior('union') if resume else None
    if union_checkpoint:
        union_report = read_json(union_dir / 'report.json')
        if (
            sha256_file(union_dir / 'report.json') != union_checkpoint['report_sha256']
            or sha256_file(union_dir / 'water-union.tif')
            != union_checkpoint['output_sha256']
            or union_report.get('status') != 'candidate-only'
            or union_report.get('configuration_sha256') != sha256_file(union_config)
            or union_report.get('grid') != grid
            or union_report.get('union_sha256') != union_checkpoint['output_sha256']
        ):
            raise ValueError('union checkpoint mismatch')
    else:
        if resume:
            quarantine(union_dir)
        unit_start = time.perf_counter()
        run_stage(water_union.run, union_config, union_dir)
        union_report = read_json(union_dir / 'report.json')
        if union_report.get('status') != 'candidate-only' or union_report.get(
            'union_sha256'
        ) != sha256_file(union_dir / 'water-union.tif'):
            raise ValueError('water union is incomplete')
        journal.unit(
            'union',
            unit_start,
            union_dir / 'report.json',
            union_dir / 'water-union.tif',
        )
    compose_cfg = {
        'schema': 'candidate-physical-composition-v1',
        'grid': grid,
        'selection_notes': cfg['selection_notes'],
        'minimum_free_bytes': reserve,
        'rows_per_block': physical_rows_per_block,
        'land': {
            'path': str(output / 'land/land.tif'),
            'sha256': land_report['land_sha256'],
        },
        'water': {
            'path': str(output / 'union/water-union.tif'),
            'sha256': union_report['union_sha256'],
        },
    }
    if cfg.get('physical_reference_mask'):
        compose_cfg['reference_mask'] = cfg['physical_reference_mask']
        compose_cfg['reference_streams'] = cfg['physical_reference_streams']
    compose_config = output / 'configs/compose.json'
    bind_config(compose_config, compose_cfg)
    physical_dir = output / 'physical'
    physical_checkpoint = prior('physical') if resume else None
    if physical_checkpoint:
        physical = read_json(physical_dir / 'report.json')
        outputs = physical.get('output_sha256', {})
        if (
            sha256_file(physical_dir / 'report.json')
            != physical_checkpoint['report_sha256']
            or sha256_file(physical_dir / 'rows.u32le')
            != physical_checkpoint['output_sha256']
            or physical.get('status') != 'candidate-only'
            or physical.get('configuration_sha256') != sha256_file(compose_config)
            or physical.get('grid') != grid
            or any(
                sha256_file(physical_dir / name) != outputs.get(name)
                for name in ('physical-dry.tif', 'rows.u32le', 'runs.u32le')
            )
        ):
            raise ValueError('physical checkpoint mismatch')
    else:
        if resume:
            quarantine(physical_dir)
        unit_start = time.perf_counter()
        run_stage(composition.main, compose_config, physical_dir)
        physical = read_json(physical_dir / 'report.json')
        if physical.get('status') != 'candidate-only' or any(
            sha256_file(physical_dir / name)
            != physical.get('output_sha256', {}).get(name)
            for name in ('physical-dry.tif', 'rows.u32le', 'runs.u32le')
        ):
            raise ValueError('physical composition is incomplete')
        journal.unit(
            'physical',
            unit_start,
            physical_dir / 'report.json',
            physical_dir / 'rows.u32le',
        )
    for p, original in (
        (manifest_path, data),
        (land_path, land_bytes),
        (water_path, water_bytes),
        (source_path, source_bytes),
    ):
        if p.read_bytes() != original:
            raise ValueError(f'pipeline input changed during processing: {p}')
    if any(sha256_file(p['path']) != p['sha256'] for p in source_pins):
        raise ValueError('land source changed during processing')
    report = {
        'status': 'candidate-only',
        'configuration_sha256': hashlib.sha256(data).hexdigest(),
        'grid': grid,
        'source_manifest': cfg['source_manifest'],
        'land_config': cfg['land_config'],
        'water_config': cfg['water_config'],
        'water_batch_size': batch_size,
        'union_rows_per_block': union_rows_per_block,
        'physical_rows_per_block': physical_rows_per_block,
        'shard_count': len(shards),
        'max_parallel_shards': workers,
        'script_sha256': scripts,
        'stage_reports': {
            key: {
                'path': str(output / key / 'report.json'),
                'sha256': sha256_file(output / key / 'report.json'),
            }
            for key in ('land', 'union', 'physical')
        },
        'physical_output_sha256': physical['output_sha256'],
        'limitations': 'Candidate physical land/water only; not historical source reproduction or continent labels.',
    }
    report['staged_shard_count'] = sum(
        event['event'] == 'download_complete' and event['attempt'] == journal.attempt
        for event in journal.events
    )
    report['staged_shard_count_scope'] = 'current invocation'
    journal.finish('complete')
    report.update(journal.summary())
    report['pipeline_identity_sha256'] = sha256_file(identity_path)
    report['processing_journal_sha256'] = sha256_file(journal.path)
    write_json(output / 'report.json', report, sort_keys=False)
    return report


def main(
    argv: Sequence[str] | None = None, *, emit: Callable[..., None] = print
) -> None:
    """Run the physical build command and print its report.

    Args:
        argv: Command arguments, or None to read them from the process.
        emit: Function that prints the resulting report.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pipeline_config')
    parser.add_argument('output')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args(argv)
    emit(
        json.dumps(
            run(args.pipeline_config, args.output, resume=args.resume), indent=2
        ),
        flush=True,
    )


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as e:
        sys.exit(f'failed: {e}')
