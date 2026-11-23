#!/usr/bin/env python3
"""Wire pinned raw land and water sources into a candidate physical grid."""

import argparse
import hashlib
import json
import re
import shutil
import sys
import threading
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import closing, nullcontext
from contextvars import copy_context
from pathlib import Path
from typing import Any

import worldatlas.geodesy.ogr as geometry_io
from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.execution import control
from worldatlas.map_build.execution.runtime import Checkpoints, open_stage_workspace
from worldatlas.map_build.execution.timing import Timing
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
    JSONValue,
    json_bytes,
    read_json,
    sha256_file,
    write_bytes_atomic,
    write_json,
)
from worldatlas.source_assets import cache as source_cache
from worldatlas.source_assets.cache import FileSpec, SourceCache

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
    output = Path(output).resolve()
    require_separate_cache_and_output(
        Path(settings['source_directory']).resolve(), output
    )
    with open_stage_workspace(output, request, resume=resume) as (checkpoints, timing):
        with control.stage(), timing.stage('physical'):
            report = build(
                settings,
                Grid(**settings['grid']),
                request,
                output,
                checkpoints=checkpoints,
                timing=timing,
            )
        return {**report, **timing.summary()['physical']}


def build(
    cfg: PhysicalConfiguration,
    grid: Grid,
    request: FilePin,
    output: Path,
    *,
    checkpoints: Checkpoints,
    timing: Timing,
) -> dict[str, Any]:
    """Rasterize land and water through the shared run's checkpoints.

    Args:
        cfg: Resolved raster settings and source pins.
        grid: Grid shared with later map stages.
        request: Path and SHA-256 of the saved physical configuration.
        output: Directory for physical tasks and their reports.
        checkpoints: Saved work that can be verified and reused.
        timing: Run timer shared with other stages.

    Returns:
        The physical output report with verified grid files.
    """
    source_directory = Path(cfg['source_directory']).resolve()
    with closing(
        SourceCache(
            source_directory,
            check_cancelled=control.check_cancelled,
            measure_download=lambda key: timing.measure(
                'physical', f'download/{key}', kind='download'
            ),
        )
    ) as cache:
        return _build(
            cfg,
            grid,
            request,
            output,
            checkpoints=checkpoints,
            timing=timing,
            cache=cache,
        )


def _build(
    cfg: PhysicalConfiguration,
    grid: Grid,
    request: FilePin,
    output: Path,
    *,
    checkpoints: Checkpoints,
    timing: Timing,
    cache: SourceCache,
) -> dict[str, Any]:
    """Run physical tasks with one source cache for all of their inputs.

    Args:
        cfg: Resolved raster settings and source pins.
        grid: Grid shared with later map stages.
        request: Path and SHA-256 of the saved physical configuration.
        output: Directory for physical tasks and their reports.
        checkpoints: Saved work that can be verified and reused.
        timing: Run timer for rasterization and downloads.
        cache: Open R2 source cache for this build.

    Returns:
        The physical output report with verified grid files.
    """
    config_path = Path(request['path'])
    grid_settings = vars(grid)
    reserve = cfg.get('minimum_free_bytes', 2 * (1 << 30))
    workers = cfg.get('max_parallel_shards', 2)
    source_directory = Path(cfg['source_directory']).resolve()
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
    files = checkpoints.files

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

    def bind_config(path: Path, data: bytes) -> FilePin:
        """Save the generated settings or check they match the previous attempt.

        Args:
            path: Configuration file in the current run.
            data: Expected JSON bytes.

        Returns:
            File pin for the saved stage settings.

        Raises:
            ValueError: An existing settings file differs.
        """
        if path.exists():
            if path.read_bytes() != data:
                raise ValueError('resumed stage config mismatch')
        else:
            write_bytes_atomic(path, data)
        return FilePin(path=str(path), sha256=hashlib.sha256(data).hexdigest())

    config_dir = output / 'configs'
    stage_documents = {
        'land_config': (config_dir / 'land.json', json_bytes(land_document)),
        'inland_water': (config_dir / 'inland-water.json', json_bytes(water_cfg)),
    }
    config_dir.mkdir(parents=True, exist_ok=True)
    (output / 'shards').mkdir(exist_ok=True)
    stage_pins = {
        key: bind_config(path, data) for key, (path, data) in stage_documents.items()
    }

    def task[Result: JSONValue](
        name: str,
        operation: Callable[[], Result],
        destination: Path,
        *,
        inputs: Sequence[Mapping[str, str] | FilePin],
        includes_downloads: bool = False,
    ) -> Result:
        """Run one physical operation through the shared checkpoint runner.

        Args:
            name: Name of the work within the physical stage.
            operation: Function with its arguments supplied.
            destination: File or directory written by the operation.
            inputs: Pinned settings and input files.
            includes_downloads: Whether this span includes a separate download.

        Returns:
            The new result, or the verified saved result on resume.
        """
        return checkpoints.run_function(
            f'physical-{name}',
            'physical',
            operation,
            timing=timing,
            inputs=[request, *inputs],
            outputs=[destination],
            timing_kind='wall' if includes_downloads else 'processing',
        )

    def verify_shard(
        index: int, source_digest: str
    ) -> tuple[ShardMask, tuple[str, ...]]:
        """Read one shard's verified output pins and validate its reported inputs.

        Args:
            index: Zero-based position in the pinned source list.
            source_digest: Expected SHA-256 of the source GeoParquet file.

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

    land_dir = output / 'land'

    def rasterize_land() -> dict[str, Any]:
        """Acquire coastline inputs and return the verified land raster report.

        Returns:
            Coastline raster report, including the checksum of its output.
        """
        for spec in land_downloads:
            control.check_cancelled()
            cache.acquire(spec)
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
        return land_report

    land_report = task(
        'land',
        rasterize_land,
        land_dir,
        includes_downloads=bool(land_downloads),
        inputs=[
            stage_pins['land_config'],
            *[
                {'path': pin['path'], 'sha256': pin['sha256']}
                for pin in source_pins
                if not land_downloads
            ],
        ],
    )
    land_transfer_count = len(cache.downloads)

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
        name = f'shard-{i:05d}'

        def rasterize_shard() -> tuple[ShardMask, tuple[str, ...]]:
            """Read one water source and produce a verified mask for it.

            Returns:
                Mask and report pins, followed by the rasterizer identity.
            """
            source_path = path
            if remote is not None:
                with download_slot:
                    source_path = cache.acquire(remote)
            with raster_slot:
                control.check_cancelled()
                with timing.measure('physical', f'rasterize-{name}'):
                    water.run(
                        source_path,
                        digest,
                        destination,
                        stage_pins['inland_water']['sha256'],
                        grid,
                        settings=cfg['inland_water'],
                        minimum_free_bytes=reserve,
                        files=files,
                        emit=control.emit,
                    )
                    return verify_shard(i, digest)

        source_pin = [{'path': str(path), 'sha256': digest}] if remote is None else []
        receipt, rasterizer = task(
            name,
            rasterize_shard,
            destination,
            includes_downloads=True,
            inputs=[stage_pins['inland_water'], *source_pin],
        )
        return receipt, tuple(rasterizer)

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

    union_config = bind_config(
        config_dir / 'union.json', json_bytes(union_cfg, sort_keys=False)
    )
    union_dir = output / 'union'

    def merge_water() -> dict[str, Any]:
        """Merge the verified water masks in manifest order.

        Returns:
            Water union report, including its output checksum.
        """
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
        return union_report

    union_report = task(
        'union',
        merge_water,
        union_dir,
        inputs=[
            union_config,
            water_manifest,
            *(
                pin
                for shard in shards
                for pin in (
                    {'path': shard['path'], 'sha256': shard['sha256']},
                    shard['report'],
                )
            ),
        ],
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
    compose_config = bind_config(
        config_dir / 'compose.json', json_bytes(compose_cfg, sort_keys=False)
    )
    physical_dir = output / 'physical'

    def compose_grid() -> dict[str, Any]:
        """Combine the land and water masks into the finished physical grid.

        Returns:
            Physical grid report with checksums of the TIFF and row-run files.
        """
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
        return physical

    physical = task(
        'compose',
        compose_grid,
        physical_dir,
        inputs=[compose_config, land_mask, water_mask],
    )
    files.verify([request, *stage_pins.values(), union_config, compose_config])
    if not land_downloads and any(
        checksum(pin['path']) != pin['sha256'] for pin in source_pins
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
    report_path = output / 'report.json'

    def save_report() -> dict[str, Any]:
        """Write the stage report after the physical files are verified.

        Returns:
            The saved physical output report.
        """
        report['downloaded_shard_count'] = sum(
            transfer.completed for transfer in cache.downloads[land_transfer_count:]
        )
        report['downloaded_shard_count_scope'] = 'current invocation'
        write_json(report_path, report, sort_keys=False)
        return report

    return task(
        'report',
        save_report,
        report_path,
        inputs=[
            *stage_pins.values(),
            *(
                files.pin(output / name / 'report.json')
                for name in ('land', 'union', 'physical')
            ),
            *files.row_streams(physical_dir),
        ],
    )


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
