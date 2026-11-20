"""Acquire verified inputs and locate selected datasets for construction methods."""

from pathlib import Path, PurePosixPath
import time
from typing import TypedDict
from zipfile import ZipFile, is_zipfile

from worldatlas.source_assets.catalog import assemble_parts, catalog_sources, download_source
from worldatlas.source_imports.shared.contracts import NonEmptyText, SourceId


class MultipartSource(TypedDict):
    """Describe one provider file stored as ordered R2 byte parts."""

    parts: list[SourceId]
    sha256: NonEmptyText
    size_bytes: int
    filename: NonEmptyText


def archive_member(archive, name):
    """Select one relative file path in an open ZIP archive.

    Args:
        archive: Open ``ZipFile`` containing the cataloged source.
        name: Path inside the ZIP.

    Returns:
        The matching ZIP member.

    Raises:
        ValueError: The path is invalid, missing, or duplicated.
    """
    member_path = PurePosixPath(name or "")
    if not name or member_path.is_absolute() or ".." in member_path.parts:
        raise ValueError("invalid source archive member")
    matches = [item for item in archive.infolist() if item.filename == name and not item.is_dir()]
    if len(matches) != 1:
        raise ValueError("selected archive member is missing or duplicated")
    return matches[0]


def gdal_dataset_path(path, member=None):
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
            candidates = [name for name in archive.namelist() if name.lower().endswith(".shp")]
            if len(candidates) != 1:
                raise ValueError("select one vector dataset archive member")
            member = candidates[0]
        selected = archive_member(archive, member)
    return f"/vsizip/{{{path}}}/{selected.filename}"


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
