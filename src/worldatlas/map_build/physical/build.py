#!/usr/bin/env python3
"""Wire pinned raw land and water sources into a candidate physical grid."""

import argparse
import hashlib
import json
import re
import shutil
import threading
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import closing, nullcontext
from contextvars import copy_context
from functools import partial
from pathlib import Path
from typing import Any

import worldatlas.geodesy.ogr as geometry_io
from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.execution import control
from worldatlas.map_build.execution.runtime import Checkpoints, open_stage_workspace
from worldatlas.map_build.execution.timing import Timing
from worldatlas.map_build.inputs.configuration import (
    PHYSICAL_CONFIGURATION,
    LandLayer,
    LandSettings,
    PhysicalConfiguration,
    land_dataset_index,
    require_separate_cache_and_output,
)
from worldatlas.map_build.physical import composition, land, water
from worldatlas.map_build.physical import union as water_union
from worldatlas.map_build.physical.union import ShardMask
from worldatlas.shared import r2
from worldatlas.shared.files import (
    SHA256_PATTERN,
    FilePin,
    JSONValue,
    json_bytes,
    read_json,
    sha256_file,
    write_bytes_atomic,
    write_json,
)
from worldatlas.source_assets import cache as source_cache
from worldatlas.source_assets.cache import SourceCache
from worldatlas.source_assets.pins import R2ObjectPin, RemoteFile

HERE = Path(__file__).resolve().parent


def plan_land_inputs(
    settings: LandSettings[RemoteFile], cache: SourceCache
) -> tuple[LandSettings[FilePin], list[RemoteFile]]:
    """Prepare local coastline paths without acquiring any R2 files.

    Args:
        settings: Land rasterization settings with R2 file pins.
        cache: Shared cache used to derive each R2 destination.

    Returns:
        Land settings with absolute cache paths and the corresponding R2 requests.
    """
    requests: list[RemoteFile] = []
    layers: list[LandLayer[FilePin]] = []
    for layer in settings["land"]:
        dataset_index = land_dataset_index(layer)
        requests.extend(layer['files'])
        files = [
            FilePin(path=str(cache.path(source)), sha256=source['sha256'])
            for source in layer['files']
        ]
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
    if path.is_relative_to(output):
        raise ValueError('physical output must not contain its configuration')
    with open_stage_workspace(output, request, resume=resume) as (checkpoints, timing):
        with control.stage(), timing.stage('physical'):
            operation = PhysicalBuild(
                settings,
                Grid(**settings['grid']),
                request,
                output,
                checkpoints=checkpoints,
                timing=timing,
            )
            report = operation.run()
        return {**report, **timing.summary()['physical']}


class PhysicalBuild:
    """Coordinate the checkpointed tasks that produce one physical grid."""

    def __init__(
        self,
        configuration: PhysicalConfiguration,
        grid: Grid,
        request: FilePin,
        output: Path,
        *,
        checkpoints: Checkpoints,
        timing: Timing,
    ) -> None:
        """Keep the inputs and services shared by the physical tasks.

        Args:
            configuration: Resolved raster settings and R2 source pins.
            grid: Grid shared with later map stages.
            request: Path and SHA-256 of the saved physical configuration.
            output: Directory for physical task outputs and reports.
            checkpoints: Shared task runner and checkpoint store.
            timing: Shared timer for rasterization and downloads.
        """
        self.configuration = configuration
        self.grid = grid
        self.request = request
        self.output = output.resolve()
        self.config_directory = self.output / 'configs'
        self.checkpoints = checkpoints
        self.files = checkpoints.files
        self.timing = timing
        self.minimum_free_bytes = configuration.get('minimum_free_bytes', 2 * (1 << 30))
        self.water_workers = configuration.get('max_parallel_shards', 2)
        self.water_batch_size = configuration['inland_water'].get('batch_size', 8192)
        self.union_rows_per_block = configuration.get('union_rows_per_block', 128)
        self.physical_rows_per_block = configuration.get('physical_rows_per_block', 128)

    def run(self) -> dict[str, Any]:
        """Build land, draw and merge inland water, then save the physical grid.

        Returns:
            Physical build report with output paths and checksums.
        """
        water_sources = self.configuration['inland_water']['files']
        if len({source['sha256'] for source in water_sources}) != len(water_sources):
            raise ValueError('inland-water source hashes must be unique')
        script_checksums = _physical_script_checksums()
        if shutil.disk_usage(self.output.parent).free < self.minimum_free_bytes:
            raise ValueError('free disk below pipeline reserve')

        with closing(
            SourceCache(
                Path(self.configuration['source_directory']),
                check_cancelled=control.check_cancelled,
                measure_download=lambda key: self.timing.measure(
                    'physical', f'download/{key}', kind='download'
                ),
            )
        ) as cache:
            land_settings, coastline_sources = plan_land_inputs(
                self.configuration['land_config'], cache
            )
            self.config_directory.mkdir(parents=True, exist_ok=True)
            (self.output / 'shards').mkdir(exist_ok=True)
            land_config = self._save_task_configuration(
                'land.json',
                dict(
                    land_settings,
                    schema='land-raster-candidate-v1',
                    minimum_free_bytes=self.minimum_free_bytes,
                ),
            )
            water_config = self._save_task_configuration(
                'inland-water.json',
                dict(
                    self.configuration['inland_water'],
                    schema='water-shard-candidate-v2',
                    minimum_free_bytes=self.minimum_free_bytes,
                ),
            )

            land_mask = self._rasterize_land(
                land_settings, coastline_sources, land_config, cache=cache
            )
            water_download_start = len(cache.downloads)
            shards = self._rasterize_water_shards(
                water_config, water_sources, cache=cache
            )
            downloaded_shard_count = sum(
                transfer.completed
                for transfer in cache.downloads[water_download_start:]
            )

        union_config, water_mask = self._merge_water(water_config, shards)
        compose_config, output_checksums = self._compose_grid(land_mask, water_mask)

        self.files.verify(
            [self.request, land_config, water_config, union_config, compose_config]
        )
        return self._write_report(
            land_config,
            water_config,
            output_checksums,
            script_checksums,
            downloaded_shard_count=downloaded_shard_count,
        )

    def _checksum(self, path: Path) -> str:
        """Read or reuse the SHA-256 digest of a file in this build attempt.

        Args:
            path: File to check.

        Returns:
            The file's lowercase hexadecimal SHA-256.
        """
        return self.files.pin(path)['sha256']

    def _save_task_configuration(
        self, filename: str, settings: JSONValue, *, sort_keys: bool = True
    ) -> FilePin:
        """Save a task's settings or check the settings already saved for resume.

        Args:
            filename: JSON filename under this build's configs directory.
            settings: JSON-compatible settings used by the task.
            sort_keys: Whether to sort object keys when writing.

        Returns:
            Path and SHA-256 of the settings file.

        Raises:
            ValueError: The existing settings differ from the current settings.
        """
        path = self.config_directory / filename
        data = json_bytes(settings, sort_keys=sort_keys)
        if path.exists():
            if path.read_bytes() != data:
                raise ValueError('resumed stage config mismatch')
        else:
            write_bytes_atomic(path, data)
        return FilePin(path=str(path), sha256=hashlib.sha256(data).hexdigest())

    def _run_task[Result: JSONValue](
        self,
        name: str,
        operation: Callable[[], Result],
        destination: Path,
        *,
        inputs: Sequence[FilePin],
        includes_downloads: bool = False,
    ) -> Result:
        """Run a physical task through the shared checkpoint and timing tools.

        Args:
            name: Task name, prefixed with 'physical-' in the checkpoint store.
            operation: Function that produces the task's output and result.
            destination: File or directory written by the operation.
            inputs: Task-specific settings and input file pins.
            includes_downloads: Whether this span includes separately timed downloads.

        Returns:
            The new result, or the verified saved result on resume.
        """
        return self.checkpoints.run_function(
            f'physical-{name}',
            'physical',
            operation,
            timing=self.timing,
            inputs=[self.request, *inputs],
            outputs=[destination],
            timing_kind='wall' if includes_downloads else 'processing',
        )

    def _rasterize_land(
        self,
        land_settings: LandSettings[FilePin],
        coastline_sources: Sequence[RemoteFile],
        land_config: FilePin,
        *,
        cache: SourceCache,
    ) -> FilePin:
        """Acquire the coastline inputs and build the land mask.

        Args:
            land_settings: Rasterization settings with cache paths.
            coastline_sources: R2 objects and ZIP members needed by the rasterizer.
            land_config: Path and checksum of the saved coastline settings.
            cache: Shared cache for coastline and inland-water inputs.

        Returns:
            Path and SHA-256 of the completed land mask.
        """
        land_directory = self.output / 'land'

        def rasterize_land() -> dict[str, Any]:
            """Rasterize the coastline and verify its saved report.

            Returns:
                The land raster report, including the checksum of its output.
            """
            for source in coastline_sources:
                control.check_cancelled()
                cache.acquire(source)
            land.run(
                land_config['sha256'],
                land_directory,
                self.grid,
                settings=land_settings,
                minimum_free_bytes=self.minimum_free_bytes,
                files=self.files,
                emit=control.emit,
            )
            report = read_json(land_directory / 'report.json')
            if report.get('status') != 'candidate-only' or report.get(
                'land_sha256'
            ) != self._checksum(land_directory / 'land.tif'):
                raise ValueError('land raster is incomplete')
            return report

        report = self._run_task(
            'land',
            rasterize_land,
            land_directory,
            inputs=[land_config],
            includes_downloads=True,
        )
        return FilePin(
            path=str(land_directory / 'land.tif'), sha256=report['land_sha256']
        )

    def _rasterize_water_shards(
        self,
        water_config: FilePin,
        water_sources: Sequence[R2ObjectPin],
        *,
        cache: SourceCache,
    ) -> list[ShardMask]:
        """Rasterize the water files in parallel and return masks in source order.

        Args:
            water_config: Path and checksum of the saved water settings.
            water_sources: R2 pins for all inland-water files.
            cache: Shared cache for coastline and inland-water inputs.

        Returns:
            Verified mask and report pins in the order of the input files.
        """
        download_slot = threading.Lock()
        # Overlap one R2 download with one rasterization when files are missing.
        # When the cache is warm, workers can rasterize concurrently.
        cold_cache = any(not cache.path(source).is_file() for source in water_sources)
        raster_slot = threading.Lock() if cold_cache else nullcontext()

        rasterize_shard = partial(
            self._rasterize_water_shard,
            water_config=water_config,
            cache=cache,
            download_slot=download_slot,
            raster_slot=raster_slot,
        )
        completed_shards: dict[int, tuple[ShardMask, tuple[str, ...]]] = {}
        with (
            control.stage() as cancelled,
            ThreadPoolExecutor(
                max_workers=min(self.water_workers, len(water_sources))
            ) as pool,
        ):
            futures = {
                pool.submit(copy_context().run, rasterize_shard, index, source): index
                for index, source in enumerate(water_sources)
            }
            try:
                for future in as_completed(futures):
                    completed_shards[futures[future]] = future.result()
            except BaseException:
                cancelled.set()
                for future in futures:
                    future.cancel()
                raise
        if len({rasterizer for _, rasterizer in completed_shards.values()}) != 1:
            raise ValueError('inconsistent water shard rasterizers or kernels')
        return [completed_shards[index][0] for index in range(len(water_sources))]

    def _rasterize_water_shard(
        self,
        index: int,
        source: R2ObjectPin,
        *,
        water_config: FilePin,
        cache: SourceCache,
        download_slot: threading.Lock,
        raster_slot: threading.Lock | nullcontext[None],
    ) -> tuple[ShardMask, tuple[str, ...]]:
        """Run one water file through the cache, rasterizer and checkpoint store.

        Args:
            index: Zero-based position of the file in the source list.
            source: Pinned inland-water GeoParquet file in R2.
            water_config: Path and SHA-256 of the shared water settings.
            cache: Open source cache shared by the raster workers.
            download_slot: Lock shared by workers acquiring files.
            raster_slot: Lock for a cold cache, or an empty context for a warm cache.

        Returns:
            The verified mask and report pins, followed by the rasterizer identity.
        """
        control.check_cancelled()
        directory = self.output / 'shards' / f'{index:05d}'
        name = f'shard-{index:05d}'

        def rasterize_shard() -> tuple[ShardMask, tuple[str, ...]]:
            """Download if needed, rasterize, then check the saved shard report.

            Returns:
                The verified mask and report pins, and the rasterizer identity.
            """
            with download_slot:
                source_path = cache.acquire(source)
            with raster_slot:
                control.check_cancelled()
                with self.timing.measure('physical', f'rasterize-{name}'):
                    water.run(
                        source_path,
                        source['sha256'],
                        directory,
                        water_config['sha256'],
                        self.grid,
                        settings=self.configuration['inland_water'],
                        minimum_free_bytes=self.minimum_free_bytes,
                        files=self.files,
                        emit=control.emit,
                    )
                    return self._verify_water_shard(
                        directory, water_config, index, source['sha256']
                    )

        receipt, rasterizer = self._run_task(
            name,
            rasterize_shard,
            directory,
            includes_downloads=True,
            inputs=[water_config],
        )
        return receipt, tuple(rasterizer)

    def _verify_water_shard(
        self, directory: Path, water_config: FilePin, index: int, source_digest: str
    ) -> tuple[ShardMask, tuple[str, ...]]:
        """Read one shard's verified output pins and validate its reported inputs.

        Args:
            directory: Directory containing this shard's mask and report.
            water_config: Pin of the settings used to rasterize the shard.
            index: Zero-based position in the pinned source list.
            source_digest: Expected SHA-256 of the source GeoParquet file.

        Returns:
            Verified mask and report pins, followed by the rasterizer identity.

        Raises:
            ValueError: The saved pins, actual bytes, or report disagree.
        """
        report_path = directory / 'report.json'
        mask_path = directory / 'water.tif'
        receipt = ShardMask(
            path=str(mask_path),
            sha256=self._checksum(mask_path),
            status='candidate-only',
            report=FilePin(path=str(report_path), sha256=self._checksum(report_path)),
        )
        item = read_json(report_path)
        row_count = item.get('rows_in_source')
        counts = item.get('counts', {})
        script = item.get('script_sha256')
        if (
            item.get('status') != 'candidate-only'
            or item.get('source_sha256') != source_digest
            or item.get('configuration_sha256') != water_config['sha256']
            or item.get('grid') != vars(self.grid)
            or item.get('batch_size') != self.water_batch_size
            or item.get('output_sha256') != receipt['sha256']
            or item.get('invalid_feature_ids')
            or counts.get('missing_classification', 0)
            or counts.get('invalid_polygon', 0)
            or type(row_count) is not int
            or row_count < 0
            or row_count != counts.get('rows')
            or not isinstance(script, str)
            or not re.fullmatch(SHA256_PATTERN, script)
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
            or not re.fullmatch(SHA256_PATTERN, kernel['binding_sha256'])
        ):
            raise ValueError(f'invalid in-process GDAL water kernel for shard: {index}')
        return receipt, (
            script,
            rasterizer,
            kernel['method'],
            kernel['binding_sha256'],
            kernel['gdal'],
        )

    def _merge_water(
        self, water_config: FilePin, shards: Sequence[ShardMask]
    ) -> tuple[FilePin, FilePin]:
        """Combine all inland-water masks into one mask.

        Args:
            water_config: Pin of the saved water source list and settings.
            shards: Verified water shard masks in source order.

        Returns:
            File pins for the union settings and the combined water mask, in that order.
        """
        union_config = self._save_task_configuration(
            'union.json',
            {
                'schema': 'water-union-v1',
                'grid': vars(self.grid),
                **self._selection_notes(),
                'minimum_free_bytes': self.minimum_free_bytes,
                'source_manifest': water_config,
                'shard_count': len(shards),
                'rows_per_block': self.union_rows_per_block,
                'shards': list(shards),
            },
            sort_keys=False,
        )
        union_directory = self.output / 'union'

        def merge_water() -> dict[str, Any]:
            """Merge the shard masks and verify the saved union report.

            Returns:
                The water union report, including the checksum of its output.
            """
            water_union.run(
                union_config['sha256'],
                union_directory,
                self.grid,
                source_manifest=water_config,
                shards=shards,
                minimum_free_bytes=self.minimum_free_bytes,
                rows_per_block=self.union_rows_per_block,
                files=self.files,
                emit=control.emit,
            )
            report = read_json(union_directory / 'report.json')
            if report.get('status') != 'candidate-only' or report.get(
                'union_sha256'
            ) != self._checksum(union_directory / 'water-union.tif'):
                raise ValueError('water union is incomplete')
            return report

        shard_inputs: list[FilePin] = []
        for shard in shards:
            shard_inputs.extend(
                (FilePin(path=shard['path'], sha256=shard['sha256']), shard['report'])
            )
        report = self._run_task(
            'union',
            merge_water,
            union_directory,
            inputs=[union_config, water_config, *shard_inputs],
        )
        mask = FilePin(
            path=str(union_directory / 'water-union.tif'), sha256=report['union_sha256']
        )
        return union_config, mask

    def _compose_grid(
        self, land_mask: FilePin, water_mask: FilePin
    ) -> tuple[FilePin, dict[str, str]]:
        """Subtract the inland-water mask from the land mask.

        Args:
            land_mask: Path and SHA-256 of the coastline raster.
            water_mask: Path and SHA-256 of the combined inland-water raster.

        Returns:
            The composition settings pin and the grid checksums by filename.
        """
        compose_config = self._save_task_configuration(
            'compose.json',
            {
                'schema': 'candidate-physical-composition-v1',
                'grid': vars(self.grid),
                **self._selection_notes(),
                'minimum_free_bytes': self.minimum_free_bytes,
                'rows_per_block': self.physical_rows_per_block,
                'land': land_mask,
                'water': water_mask,
            },
            sort_keys=False,
        )
        physical_directory = self.output / 'physical'

        def compose_grid() -> dict[str, Any]:
            """Write the finished physical grid and verify its saved report.

            Returns:
                The physical grid report, including the checksum of each output.
            """
            composition.main(
                compose_config['sha256'],
                physical_directory,
                self.grid,
                land=land_mask,
                water=water_mask,
                minimum_free_bytes=self.minimum_free_bytes,
                rows_per_block=self.physical_rows_per_block,
                files=self.files,
                emit=control.emit,
            )
            report = read_json(physical_directory / 'report.json')
            if report.get('status') != 'candidate-only' or any(
                self._checksum(physical_directory / filename)
                != report.get('output_sha256', {}).get(filename)
                for filename in ('physical-dry.tif', 'rows.u32le', 'runs.u32le')
            ):
                raise ValueError('physical composition is incomplete')
            return report

        report = self._run_task(
            'compose',
            compose_grid,
            physical_directory,
            inputs=[compose_config, land_mask, water_mask],
        )
        return compose_config, report['output_sha256']

    def _selection_notes(self) -> dict[str, str]:
        """Return the optional selection notes to include in task settings.

        Returns:
            An empty dictionary or the configured notes under 'selection_notes'.
        """
        if 'selection_notes' in self.configuration:
            return {'selection_notes': self.configuration['selection_notes']}
        return {}

    def _write_report(
        self,
        land_config: FilePin,
        water_config: FilePin,
        output_checksums: dict[str, str],
        script_checksums: dict[str, str],
        *,
        downloaded_shard_count: int,
    ) -> dict[str, Any]:
        """Write the physical stage report with the verified grid files.

        Args:
            land_config: Path and SHA-256 of the saved coastline settings.
            water_config: Path and SHA-256 of the saved inland-water settings.
            output_checksums: SHA-256 by output filename for the finished grid.
            script_checksums: SHA-256 of the implementation files, by relative path.
            downloaded_shard_count: Number of water files downloaded in this attempt.

        Returns:
            The saved physical build report.
        """
        physical_directory = self.output / 'physical'
        stage_reports = {
            stage: self.files.pin(self.output / stage / 'report.json')
            for stage in ('land', 'union', 'physical')
        }
        report_path = self.output / 'report.json'

        def save_report() -> dict[str, Any]:
            """Save the report after the checkpoint runner verifies its inputs.

            Returns:
                The saved physical build report.
            """
            report = {
                'status': 'candidate-only',
                'directory': str(physical_directory),
                'configuration': self.request,
                'grid': vars(self.grid),
                'land_config': land_config,
                'inland_water': water_config,
                'water_batch_size': self.water_batch_size,
                'union_rows_per_block': self.union_rows_per_block,
                'physical_rows_per_block': self.physical_rows_per_block,
                'shard_count': len(self.configuration['inland_water']['files']),
                'max_parallel_shards': self.water_workers,
                'script_sha256': script_checksums,
                'stage_reports': stage_reports,
                'physical_output_sha256': output_checksums,
                'limitations': 'Candidate physical land/water only; not historical source reproduction or continent labels.',
                'downloaded_shard_count': downloaded_shard_count,
                'downloaded_shard_count_scope': 'current invocation',
            }
            write_json(report_path, report, sort_keys=False)
            return report

        saved_report = self._run_task(
            'report',
            save_report,
            report_path,
            inputs=[
                land_config,
                water_config,
                *stage_reports.values(),
                *self.files.row_streams(physical_directory),
            ],
        )
        return {**saved_report, 'directory': str(physical_directory)}


def _physical_script_checksums() -> dict[str, str]:
    """Record the physical builder implementation used for this attempt.

    Returns:
        SHA-256 digests keyed by the implementation files' relative names.
    """
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
    return scripts


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
    with control.stage() as cancelled, control.cancel_on_stop_signals(cancelled.set):
        report = run(args.physical_config, args.output, resume=args.resume)
    emit(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
