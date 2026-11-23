"""Acquire verified inputs and locate selected datasets for construction methods."""

import time
from collections.abc import Sequence
from contextlib import closing
from pathlib import Path
from typing import Any
from zipfile import ZipFile, is_zipfile

from worldatlas.source_assets.archives import archive_member
from worldatlas.source_assets.cache import SourceCache
from worldatlas.source_assets.catalog import catalog_sources
from worldatlas.source_imports.shared.recipe_types import SourceId
from worldatlas.source_imports.shared.runtime import Runtime


def gdal_dataset_path(path: Path | str, member: str | None = None) -> str:
    """Resolve a local dataset or an archive member for GDAL.

    Args:
        path: Local dataset or ZIP archive.
        member: Dataset path inside the archive. An omitted ZIP member selects
            the sole Shapefile in the archive.

    Returns:
        A filesystem path or GDAL virtual ZIP path.

    Raises:
        ValueError: The archive selection is invalid, missing, or ambiguous.
    """
    path = Path(path).resolve(strict=True)
    if path.suffix.lower() != ".zip":
        if member is None:
            return str(path)
        if not is_zipfile(path):
            raise ValueError("archive member supplied for a non-archive source")
    with ZipFile(path) as archive:
        if member is None:
            # GDAL finds the companion files from the Shapefile entry point.
            candidates = [
                name for name in archive.namelist() if name.lower().endswith(".shp")
            ]
            if len(candidates) != 1:
                raise ValueError("select one vector dataset archive member")
            member = candidates[0]
        selected = archive_member(archive, member)
    return f"/vsizip/{{{path}}}/{selected.filename}"


def acquire_sources(
    runtime: Runtime,
    requests: Sequence[SourceId],
    *,
    timing: dict[str, Any] | None = None,
) -> list[Path]:
    """Resolve every source together and stage the files needed for calculation.

    Release the database connection before downloading. A saved recipe's
    database links already validate any evidence IDs that do not name inputs.

    Args:
        runtime: The import's database connection factory and cache directory.
        requests: Source IDs for the files to acquire, in caller order.
        timing: Optional dictionary for catalog, staging, and transfer times.

    Returns:
        Verified local paths in request order.

    Raises:
        ValueError: Required download settings are missing, a source is
            missing from Neon, or a file fails verification.
    """
    if runtime.work_dir is None:
        raise ValueError('this method requires --work-dir for the source cache')

    started = time.monotonic()
    with runtime.connect() as database:
        sources = catalog_sources(database, requests)
    if timing is not None:
        timing['catalog_seconds'] = time.monotonic() - started

    started = time.monotonic()
    with closing(SourceCache(runtime.work_dir)) as cache:
        paths = [cache.acquire(sources[source_id]) for source_id in requests]
    if timing is not None and cache.downloads:
        intervals = [(transfer.started, transfer.ended) for transfer in cache.downloads]
        timing['download_intervals'] = intervals
        timing['download_seconds'] = sum(end - start for start, end in intervals)
    if timing is not None:
        timing['source_staging_seconds'] = time.monotonic() - started
    return paths
