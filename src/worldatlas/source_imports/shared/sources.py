"""Acquire verified files and check cited sources for construction methods."""

import time
from typing import TypedDict

from worldatlas.source_assets.catalog import assemble_parts, catalog_sources, download_source
from worldatlas.source_imports.shared.contracts import NonEmptyText, SourceId


class MultipartSource(TypedDict):
    """Describe one provider file stored as ordered R2 byte parts."""

    parts: list[SourceId]
    sha256: NonEmptyText
    size_bytes: int
    filename: NonEmptyText


def acquire_sources(runtime, requests, *, evidence_source_ids=(), timing=None):
    """Resolve every source together and stage the files needed for calculation.

    Release the database connection before downloading. Evidence IDs are
    checked in the catalog and don't need local files.

    Args:
        runtime: The import's database connection factory and R2 settings.
        requests: Ordered list of source IDs or multipart specifications.
        evidence_source_ids: Source IDs cited as supporting evidence.
        timing: Optional dictionary for catalog, staging, and transfer times.

    Returns:
        Verified local paths in request order.

    Raises:
        ValueError: Required download settings are missing, a source is
            missing from Neon, or a file fails verification.
    """
    if requests and (runtime.storage is None or runtime.work_dir is None):
        raise ValueError('this method requires --r2-endpoint and --work-dir')

    started = time.monotonic()
    ids = list(evidence_source_ids)
    for request in requests:
        ids.extend(request['parts'] if isinstance(request, dict) else [request])
    sources = {}
    if ids:
        with runtime.connect() as database:
            sources = catalog_sources(database, ids)
    if timing is not None:
        timing['catalog_seconds'] = time.monotonic() - started

    started = time.monotonic()
    paths = []
    for request in requests:
        if isinstance(request, dict):
            path = assemble_parts(
                runtime.storage, [sources[ident] for ident in request['parts']],
                request['sha256'], request['size_bytes'], request['filename'],
                runtime.work_dir, timing=timing,
            )
        else:
            path = download_source(runtime.storage, sources[request], runtime.work_dir,
                                   timing=timing)
        paths.append(path)
    if timing is not None:
        timing['source_staging_seconds'] = time.monotonic() - started
    return paths
