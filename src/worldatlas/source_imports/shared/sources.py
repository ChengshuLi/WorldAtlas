"""Acquire verified inputs and locate selected datasets for construction methods."""

from pathlib import Path, PurePosixPath
import time
from typing import TypedDict
from zipfile import ZipFile

from worldatlas.source_assets.catalog import assemble_parts, catalog_sources, download_source
from worldatlas.source_imports.shared.contracts import NonEmptyText, SourceId


class MultipartSource(TypedDict):
    """Describe one provider file stored as ordered R2 byte parts."""

    parts: list[SourceId]
    sha256: NonEmptyText
    size_bytes: int
    filename: NonEmptyText


def vector_dataset_path(path, member=None):
    """Find the vector dataset path understood by GDAL.

    Args:
        path: Local vector file or ZIP archive.
        member: Optional dataset path inside the archive.

    Returns:
        A filesystem path or GDAL virtual ZIP path.

    Raises:
        ValueError: The archive selection is invalid, missing, or ambiguous.
    """
    path = Path(path).resolve(strict=True)
    if path.suffix.lower() != ".zip":
        if member is not None:
            raise ValueError("archive member supplied for a non-archive source")
        return str(path)
    with ZipFile(path) as archive:
        names = archive.namelist()
    if member is None:
        # GDAL finds the companion files from the Shapefile entry point.
        candidates = [name for name in names if name.lower().endswith(".shp")]
        if len(candidates) != 1:
            raise ValueError("select one vector dataset archive member")
        member = candidates[0]
    member_path = PurePosixPath(member)
    if member_path.is_absolute() or ".." in member_path.parts:
        raise ValueError("invalid source archive member")
    if names.count(member) != 1:
        raise ValueError("selected vector archive member is missing or duplicated")
    return f"/vsizip/{path}/{member}"


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
