#!/usr/bin/env python3
"""Wire pinned raw land and water sources into a candidate physical grid."""

import argparse
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
from contextlib import ExitStack, closing, nullcontext
from contextvars import copy_context
from pathlib import Path
from typing import Any

import worldatlas.geodesy.ogr as geometry_io
from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.execution import control
from worldatlas.map_build.execution.journal import (
    append_records,
    create_journal,
    preserve_torn_tail,
)
from worldatlas.map_build.execution.runtime import RunFilePins, RunLock, elapsed_union
from worldatlas.map_build.inputs.configuration import (
    PHYSICAL_CONFIGURATION,
    FilePin,
    LandLayer,
    LandSettings,
    LocalFile,
    PhysicalConfiguration,
    ResolvedLandFile,
    land_dataset_index,
    require_separate_cache_and_output,
)
from worldatlas.map_build.physical import composition, land, water
from worldatlas.map_build.physical import union as water_union
from worldatlas.map_build.physical.union import ShardMask
from worldatlas.shared import r2
from worldatlas.shared.files import (
    json_bytes,
    read_json,
    sha256_file,
    sync_directory,
    write_bytes_atomic,
    write_json,
)
from worldatlas.source_assets import cache as source_cache
from worldatlas.source_assets.cache import Download, FileSpec, SourceCache

HERE = Path(__file__).resolve().parent


def plan_land_inputs(
    settings: LandSettings[ResolvedLandFile], cache: SourceCache
) -> tuple[LandSettings[LocalFile], list[FileSpec]]:
    """Prepare local coastline paths without acquiring any R2 files.

    Args:
        settings: Land rasterization settings with local and R2 file pins.
        cache: Shared cache used to derive each R2 destination.

    Returns:
        Land settings with local file paths, and the R2 requests needed to
        populate the cache before rasterization.
    """
    requests: list[FileSpec] = []

    def local_file(spec: ResolvedLandFile) -> LocalFile:
        """Turn a pinned file specification into a pin with a local path.

        Args:
            spec: Local file pin, R2 object, or ZIP member.

        Returns:
            File pin for the land rasterizer. R2 files are queued for acquisition.
        """
        if "path" in spec:
            return spec
        requests.append(spec)
        return {
            "path": str(cache.path(spec)),
            "sha256": spec["sha256"],
            "size_bytes": spec["size_bytes"],
        }

    layers: list[LandLayer[LocalFile]] = []
    for layer in settings["land"]:
        dataset_index = land_dataset_index(layer)
        files = [local_file(spec) for spec in layer["files"]]
        layers.append(
            {**layer, "dataset": files[dataset_index]["path"], "files": files}
        )
    return {**settings, "land": layers}, requests


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
        if self.finished:
            raise ValueError('attempt already ended')
        elapsed = time.monotonic() - self.started
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


def run(
    config_path: Path | str, output: Path | str, *, resume: bool = False
) -> dict[str, Any]:
    """Read the standalone physical configuration and build its grid.

    Args:
        config_path: JSON configuration with the grid, settings and file pins.
        output: Physical build directory.
        resume: Whether to continue a run already started.

    Returns:
        Physical build report with completed outputs and timings.
    """
    path = Path(config_path).resolve()
    data = path.read_bytes()
    settings = PHYSICAL_CONFIGURATION.validate_json(data, strict=True)
    request = FilePin(path=str(path), sha256=hashlib.sha256(data).hexdigest())
    return build(settings, Grid(**settings['grid']), request, output, resume=resume)


def build(
    settings: PhysicalConfiguration,
    grid: Grid,
    request: FilePin,
    output: Path | str,
    *,
    resume: bool = False,
) -> dict[str, Any]:
    """Build or resume the physical grid under an exclusive run lock.

    Args:
        settings: Resolved file pins and physical stage settings.
        grid: The grid shared with the map builder.
        request: Path and checksum of the saved physical configuration.
        output: Directory that holds this physical run.
        resume: Whether to continue a run already started.

    Returns:
        Physical build report with completed outputs and timings.
    """
    started = time.monotonic()
    output = Path(output).resolve()
    if not output.parent.is_dir():
        raise ValueError('output parent must exist')
    lock_path = output.parent / (output.name + '.lock')
    with closing(RunLock(lock_path)), ExitStack() as resources:
        journal: list[ProcessingJournal | None] = [None]
        try:
            return _run(
                settings, grid, request, output, started, resume, journal, resources
            )
        except BaseException:
            if journal[0] is not None and not journal[0].finished:
                journal[0].finish('failed')
            raise


def _run(
    cfg: PhysicalConfiguration,
    grid: Grid,
    request: FilePin,
    output: Path,
    processing_started: float,
    resume: bool,
    journal_slot: list[ProcessingJournal | None],
    resources: ExitStack,
) -> dict[str, Any]:
    """Rasterize the sources, union water masks, and compose the physical grid.

    Args:
        cfg: Resolved physical settings used by this run.
        grid: Shared physical grid.
        request: File pin for the saved physical configuration.
        output: Locked physical run directory.
        processing_started: Clock reading from the start of the attempt.
        resume: Whether to look for completed outputs before rasterizing.
        journal_slot: Single slot for the active journal so the caller can
            record failures.
        resources: Closes the source cache as the run exits.

    Returns:
        Physical build report, including the completed output file pins.
    """
    config_path = Path(request['path'])
    config_digest = request['sha256']
    grid_settings = vars(grid)
    reserve = cfg.get('minimum_free_bytes', 2 * (1 << 30))
    workers = cfg.get('max_parallel_shards', 2)
    source_directory = Path(cfg['source_directory']).resolve()
    require_separate_cache_and_output(source_directory, output)
    cache = resources.enter_context(
        closing(SourceCache(source_directory, check_cancelled=control.check_cancelled))
    )
    land_cfg, land_downloads = plan_land_inputs(cfg['land_config'], cache)
    land_document = dict(
        land_cfg, schema='land-raster-candidate-v1', minimum_free_bytes=reserve
    )
    water_cfg: dict[str, Any] = dict(
        cfg['inland_water'],
        schema='water-shard-candidate-v2',
        minimum_free_bytes=reserve,
    )
    water_cfg.setdefault('policy', {'method': 'overture-inland-subtype-v1'})
    batch_size = water_cfg.get('batch_size', 8192)
    union_rows_per_block = cfg.get('union_rows_per_block', 128)
    physical_rows_per_block = cfg.get('physical_rows_per_block', 128)
    raw: list[tuple[Path, str, FileSpec | None]] = []
    for entry in cfg['inland_water']['files']:
        if 'r2_bucket' in entry:
            raw.append((cache.path(entry), entry['sha256'], entry))
            continue
        relative = Path(entry['path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError(
                'raw source paths must be relative to the source directory'
            )
        path = (source_directory / relative).resolve()
        if not path.is_relative_to(source_directory):
            raise ValueError('raw source escapes the source directory')
        raw.append((path, entry['sha256'], None))
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
    scripts['source_assets/cache.py'] = sha256_file(source_cache.__file__)
    scripts['shared/r2.py'] = sha256_file(r2.__file__)
    files = RunFilePins()

    def checksum(path: Path | str) -> str:
        """Read or reuse a verified file digest within this physical attempt.

        Args:
            path: File to check.

        Returns:
            The lowercase SHA-256 for its current bytes.
        """
        return files.pin(path)['sha256']

    output = Path(output).resolve()
    inputs = [path for path, _, _ in raw]
    inputs += [
        Path(item['path']).resolve()
        for spec in land_cfg['land']
        for item in spec['files']
    ]
    # The build configuration can sit beside the output directory.
    if config_path.is_relative_to(output) or any(
        p.is_relative_to(output) or output.is_relative_to(p.parent) for p in inputs
    ):
        raise ValueError(
            'output must be outside all input directories and must not contain inputs'
        )
    if shutil.disk_usage(output.parent).free < reserve:
        raise ValueError('free disk below pipeline reserve')
    source_pins = [item for spec in land_cfg['land'] for item in spec['files']]
    if not land_downloads and any(
        checksum(p['path']) != p['sha256'] for p in source_pins
    ):
        raise ValueError('land source hash mismatch')
    config_dir = output / 'configs'
    stage_documents = {
        'land_config': (config_dir / 'land.json', json_bytes(land_document)),
        'inland_water': (config_dir / 'inland-water.json', json_bytes(water_cfg)),
    }
    stage_pins: dict[str, FilePin] = {
        key: {'path': str(path), 'sha256': hashlib.sha256(content).hexdigest()}
        for key, (path, content) in stage_documents.items()
    }
    identity = {
        'schema': 'raw-physical-resume-identity-v1',
        'configuration_sha256': config_digest,
        **stage_pins,
        'script_sha256': scripts,
        'land_source_pins': source_pins,
    }
    identity_path = output / 'pipeline-identity.json'

    def verify_shard(
        index: int, source_digest: str, saved: ShardMask | None = None
    ) -> tuple[ShardMask, tuple[str, ...]]:
        """Read one shard's verified output pins and validate its reported inputs.

        Args:
            index: Zero-based position in the pinned source list.
            source_digest: Expected SHA-256 of the source GeoParquet file.
            saved: Verified receipt from an earlier attempt, if applicable.

        Returns:
            Verified mask and report pins, followed by the rasterizer identity.

        Raises:
            ValueError: The saved pins, actual bytes, or report disagree.
        """
        directory = output / 'shards' / f'{index:05d}'
        report_path = directory / 'report.json'
        mask_path = directory / 'water.tif'
        receipt = ShardMask(
            path=str(mask_path),
            sha256=checksum(mask_path),
            status='candidate-only',
            report=FilePin(path=str(report_path), sha256=checksum(report_path)),
        )
        if saved is not None and saved != receipt:
            raise ValueError(f'water shard checkpoint mismatch: {index}')
        item = read_json(report_path)
        row_count = item.get('rows_in_source')
        counts = item.get('counts', {})
        script = item.get('script_sha256')
        if (
            item.get('status') != 'candidate-only'
            or item.get('source_sha256') != source_digest
            or item.get('configuration_sha256') != stage_pins['inland_water']['sha256']
            or item.get('grid') != grid_settings
            or item.get('policy') != water_cfg['policy']
            or item.get('batch_size') != batch_size
            or item.get('output_sha256') != receipt['sha256']
            or item.get('invalid_feature_ids')
            or counts.get('missing_classification', 0)
            or counts.get('invalid_polygon', 0)
            or type(row_count) is not int
            or row_count < 0
            or row_count != counts.get('rows')
            or not isinstance(script, str)
            or not re.fullmatch('[0-9a-f]{64}', script)
        ):
            raise ValueError(f'incomplete water shard or mismatched report: {index}')
        rasterizer = item.get('rasterizer')
        if rasterizer == 'python':
            return receipt, (script, rasterizer)
        if rasterizer != 'gdal':
            raise ValueError(f'unknown water rasterizer for shard: {index}')
        kernel = item.get('gdal_kernel')
        if (
            not isinstance(kernel, dict)
            or kernel.get('implementation') != 'python-gdal-api-v2'
            or kernel.get('method') not in ('hybrid', 'tiled')
            or not isinstance(kernel.get('binding_sha256'), str)
            or not re.fullmatch('[0-9a-f]{64}', kernel['binding_sha256'])
        ):
            raise ValueError(f'invalid in-process GDAL water kernel for shard: {index}')
        return receipt, (
            script,
            rasterizer,
            kernel['method'],
            kernel['binding_sha256'],
            kernel['gdal'],
        )

    if resume:
        previous = read_json(identity_path) if identity_path.is_file() else {}
        data_identity = lambda value: {
            k: v for k, v in value.items() if k != 'script_sha256'
        }
        if not output.is_dir() or data_identity(previous) != data_identity(identity):
            raise ValueError('physical resume identity mismatch')
        if (output / 'report.json').exists():
            files.verify(stage_pins.values())
            report = read_json(output / 'report.json')
            stages = report.get('stage_reports', {})
            if (
                report.get('status') != 'candidate-only'
                or report['configuration']['sha256'] != config_digest
                or report.get('pipeline_identity_sha256') != checksum(identity_path)
                or report.get('processing_journal_sha256')
                != checksum(output / 'processing-events.jsonl')
                or set(stages) != {'land', 'union', 'physical'}
                or any(
                    Path(stages[k]['path']).resolve() != output / k / 'report.json'
                    or checksum(stages[k]['path']) != stages[k]['sha256']
                    for k in stages
                )
            ):
                raise ValueError('completed physical report mismatch')
            union = read_json(output / 'union/report.json')
            for key, name, stage in (
                ('land', 'land.tif', read_json(output / 'land/report.json')),
                ('union', 'water-union.tif', union),
            ):
                digest = stage['land_sha256' if key == 'land' else 'union_sha256']
                if checksum(output / key / name) != digest:
                    raise ValueError('completed stage output mismatch: ' + key)
            saved_shards = union.get('shards')
            if not isinstance(saved_shards, list) or len(saved_shards) != len(raw):
                raise ValueError('completed shard inventory mismatch')
            for i, (entry, (_, digest, _)) in enumerate(zip(saved_shards, raw)):
                verify_shard(i, digest, entry)
            physical = read_json(output / 'physical/report.json')
            files.verify(
                [
                    FilePin(
                        path=str(config_dir / 'union.json'),
                        sha256=union['configuration_sha256'],
                    ),
                    FilePin(
                        path=str(config_dir / 'compose.json'),
                        sha256=physical['configuration_sha256'],
                    ),
                ]
            )
            outputs = physical.get('output_sha256', {})
            if outputs != report.get('physical_output_sha256') or any(
                checksum(output / 'physical' / name) != outputs.get(name)
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

    for path, content in stage_documents.values():
        if path.exists():
            if path.read_bytes() != content:
                raise ValueError('resumed stage config mismatch')
        else:
            write_bytes_atomic(path, content)

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
            checksum(land_dir / 'report.json') != land_checkpoint['report_sha256']
            or checksum(land_dir / 'land.tif') != land_checkpoint['output_sha256']
            or land_report.get('status') != 'candidate-only'
            or land_report.get('configuration_sha256')
            != stage_pins['land_config']['sha256']
            or land_report.get('grid') != grid_settings
            or land_report.get('land_sha256') != land_checkpoint['output_sha256']
        ):
            raise ValueError('land checkpoint mismatch')
    else:
        if resume:
            quarantine(land_dir)
        try:
            for spec in land_downloads:
                control.check_cancelled()
                cache.acquire(spec)
        finally:
            for transfer in cache.downloads:
                journal.record_download(transfer, 'land')
        unit_start = time.monotonic()
        land.run(
            stage_pins['land_config']['sha256'],
            land_dir,
            grid,
            settings=land_cfg,
            minimum_free_bytes=reserve,
            files=files,
            emit=control.emit,
        )
        land_report = read_json(land_dir / 'report.json')
        if land_report.get('status') != 'candidate-only' or land_report.get(
            'land_sha256'
        ) != checksum(land_dir / 'land.tif'):
            raise ValueError('land raster is incomplete')
        journal.unit(
            'land',
            unit_start,
            checksum(land_dir / 'report.json'),
            land_report['land_sha256'],
        )

    download_slot = threading.Lock()
    cold_cache = any(pin is not None and not path.is_file() for path, _, pin in raw)
    raster_slot = threading.Lock() if cold_cache else nullcontext()

    def build_shard(
        item: tuple[int, tuple[Path, str, FileSpec | None]],
    ) -> tuple[ShardMask, tuple[str, ...]]:
        """Validate or build a single water shard's raster.

        Args:
            item: Shard index and its (local path, SHA-256, optional R2 pin).

        Returns:
            Verified mask and report pins, followed by the rasterizer identity.
        """
        control.check_cancelled()
        i, (path, digest, remote) = item
        destination = output / 'shards' / f'{i:05d}'
        checkpoint = prior(f'shard-{i:05d}') if resume else None
        if checkpoint:
            return verify_shard(
                i,
                digest,
                ShardMask(
                    path=str(destination / 'water.tif'),
                    sha256=checkpoint['output_sha256'],
                    status='candidate-only',
                    report=FilePin(
                        path=str(destination / 'report.json'),
                        sha256=checkpoint['report_sha256'],
                    ),
                ),
            )
        if resume:
            quarantine(destination)
        if remote is not None:
            with download_slot:
                before = len(cache.downloads)
                try:
                    path = cache.acquire(remote)
                finally:
                    for transfer in cache.downloads[before:]:
                        journal.record_download(transfer, 'water')
        with raster_slot:
            control.check_cancelled()
            unit_start = time.monotonic()
            water.run(
                path,
                digest,
                destination,
                stage_pins['inland_water']['sha256'],
                grid,
                settings=cfg['inland_water'],
                minimum_free_bytes=reserve,
                files=files,
                emit=control.emit,
            )
        receipt, producer = verify_shard(i, digest)
        journal.unit(
            f'shard-{i:05d}', unit_start, receipt['report']['sha256'], receipt['sha256']
        )
        return receipt, producer

    # With an empty cache, overlap one R2 download with one rasterization.
    # When all files are local, workers can rasterize concurrently.
    # Keep masks in manifest order regardless of when each worker finishes.
    completed_shards: dict[int, tuple[ShardMask, tuple[str, ...]]] = {}
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
                completed_shards[futures[future]] = future.result()
        except BaseException:
            cancelled.set()
            for future in futures:
                future.cancel()
            raise
    if len({producer for _, producer in completed_shards.values()}) != 1:
        raise ValueError('inconsistent water shard rasterizers or kernels')
    shards = [completed_shards[i][0] for i in range(len(raw))]
    water_manifest: FilePin = stage_pins['inland_water']
    union_cfg: dict[str, Any] = {
        'schema': 'water-union-v1',
        'grid': grid_settings,
        **(
            {'selection_notes': cfg['selection_notes']}
            if 'selection_notes' in cfg
            else {}
        ),
        'minimum_free_bytes': reserve,
        'source_manifest': water_manifest,
        'shard_count': len(shards),
        'rows_per_block': union_rows_per_block,
        'shards': shards,
    }

    def bind_config(path: Path, value: dict[str, Any]) -> FilePin:
        """Save the generated settings or check they match the previous attempt.

        Args:
            path: Configuration file in the current run.
            value: Expected JSON settings.

        Returns:
            File pin for the saved stage settings.

        Raises:
            ValueError: An existing file differs or belongs to a fresh run.
        """
        data = json_bytes(value, sort_keys=False)
        if path.exists():
            if not resume or path.read_bytes() != data:
                raise ValueError('resumed stage config mismatch')
        else:
            write_bytes_atomic(path, data)
        return FilePin(path=str(path), sha256=hashlib.sha256(data).hexdigest())

    union_config = bind_config(config_dir / 'union.json', union_cfg)
    union_dir = output / 'union'
    union_checkpoint = prior('union') if resume else None
    if union_checkpoint:
        union_report = read_json(union_dir / 'report.json')
        if (
            checksum(union_dir / 'report.json') != union_checkpoint['report_sha256']
            or checksum(union_dir / 'water-union.tif')
            != union_checkpoint['output_sha256']
            or union_report.get('status') != 'candidate-only'
            or union_report.get('configuration_sha256') != union_config['sha256']
            or union_report.get('grid') != grid_settings
            or union_report.get('union_sha256') != union_checkpoint['output_sha256']
        ):
            raise ValueError('union checkpoint mismatch')
    else:
        if resume:
            quarantine(union_dir)
        unit_start = time.monotonic()
        water_union.run(
            union_config['sha256'],
            union_dir,
            grid,
            source_manifest=water_manifest,
            shards=shards,
            minimum_free_bytes=reserve,
            rows_per_block=union_rows_per_block,
            files=files,
            emit=control.emit,
        )
        union_report = read_json(union_dir / 'report.json')
        if union_report.get('status') != 'candidate-only' or union_report.get(
            'union_sha256'
        ) != checksum(union_dir / 'water-union.tif'):
            raise ValueError('water union is incomplete')
        journal.unit(
            'union',
            unit_start,
            checksum(union_dir / 'report.json'),
            union_report['union_sha256'],
        )
    land_mask = FilePin(
        path=str(land_dir / 'land.tif'), sha256=land_report['land_sha256']
    )
    water_mask = FilePin(
        path=str(union_dir / 'water-union.tif'), sha256=union_report['union_sha256']
    )
    compose_cfg = {
        'schema': 'candidate-physical-composition-v1',
        'grid': grid_settings,
        **(
            {'selection_notes': cfg['selection_notes']}
            if 'selection_notes' in cfg
            else {}
        ),
        'minimum_free_bytes': reserve,
        'rows_per_block': physical_rows_per_block,
        'land': land_mask,
        'water': water_mask,
    }
    compose_config = bind_config(config_dir / 'compose.json', compose_cfg)
    physical_dir = output / 'physical'
    physical_checkpoint = prior('physical') if resume else None
    if physical_checkpoint:
        physical = read_json(physical_dir / 'report.json')
        outputs = physical.get('output_sha256', {})
        if (
            checksum(physical_dir / 'report.json')
            != physical_checkpoint['report_sha256']
            or checksum(physical_dir / 'rows.u32le')
            != physical_checkpoint['output_sha256']
            or physical.get('status') != 'candidate-only'
            or physical.get('configuration_sha256') != compose_config['sha256']
            or physical.get('grid') != grid_settings
            or any(
                checksum(physical_dir / name) != outputs.get(name)
                for name in ('physical-dry.tif', 'rows.u32le', 'runs.u32le')
            )
        ):
            raise ValueError('physical checkpoint mismatch')
    else:
        if resume:
            quarantine(physical_dir)
        unit_start = time.monotonic()
        composition.main(
            compose_config['sha256'],
            physical_dir,
            grid,
            land=land_mask,
            water=water_mask,
            minimum_free_bytes=reserve,
            rows_per_block=physical_rows_per_block,
            files=files,
            emit=control.emit,
        )
        physical = read_json(physical_dir / 'report.json')
        if physical.get('status') != 'candidate-only' or any(
            checksum(physical_dir / name) != physical.get('output_sha256', {}).get(name)
            for name in ('physical-dry.tif', 'rows.u32le', 'runs.u32le')
        ):
            raise ValueError('physical composition is incomplete')
        journal.unit(
            'physical',
            unit_start,
            checksum(physical_dir / 'report.json'),
            physical['output_sha256']['rows.u32le'],
        )
    files.verify([request, *stage_pins.values(), union_config, compose_config])
    if (not land_downloads or land_checkpoint is None) and any(
        checksum(p['path']) != p['sha256'] for p in source_pins
    ):
        raise ValueError('land source changed during processing')
    report = {
        'status': 'candidate-only',
        'configuration': request,
        'grid': grid_settings,
        **stage_pins,
        'water_batch_size': batch_size,
        'union_rows_per_block': union_rows_per_block,
        'physical_rows_per_block': physical_rows_per_block,
        'shard_count': len(shards),
        'max_parallel_shards': workers,
        'script_sha256': scripts,
        'stage_reports': {
            key: {
                'path': str(output / key / 'report.json'),
                'sha256': checksum(output / key / 'report.json'),
            }
            for key in ('land', 'union', 'physical')
        },
        'physical_output_sha256': physical['output_sha256'],
        'limitations': 'Candidate physical land/water only; not historical source reproduction or continent labels.',
    }
    report['downloaded_shard_count'] = sum(
        event['event'] == 'download_complete'
        and event['attempt'] == journal.attempt
        and event['source'] == 'water'
        for event in journal.events
    )
    report['downloaded_shard_count_scope'] = 'current invocation'
    journal.finish('complete')
    report.update(journal.summary())
    report['pipeline_identity_sha256'] = checksum(identity_path)
    report['processing_journal_sha256'] = checksum(journal.path)
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
    parser.add_argument('physical_config')
    parser.add_argument('output')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args(argv)
    emit(
        json.dumps(
            run(args.physical_config, args.output, resume=args.resume), indent=2
        ),
        flush=True,
    )


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as e:
        sys.exit(f'failed: {e}')
