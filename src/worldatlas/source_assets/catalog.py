"""Resolve source catalog entries and cache verified R2 files."""

import hashlib
import os
import shutil
import time
from collections.abc import Callable, Iterable, Sequence
from contextlib import closing
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import IO, Any

from botocore.client import BaseClient
from psycopg import Connection


def catalog_sources(
    database: Connection, source_ids: Iterable[str]
) -> dict[str, dict[str, Any]]:
    """Resolve raw source IDs in one catalog query.

    Args:
        database: The caller's PostgreSQL connection.
        source_ids: Iterable of raw source IDs to look up.

    Returns:
        A dictionary keyed by source ID. Each entry contains its R2 bucket,
        object key, expected byte size, and SHA-256.

    Raises:
        ValueError: A requested catalog entry is missing.
    """
    ids = list(dict.fromkeys(source_ids))
    rows = database.execute(
        "SELECT id,r2_bucket,r2_key,sha256,size_bytes FROM atlas.source_assets "
        "WHERE id=ANY(%s)",
        (ids,),
    )
    sources = {
        ident: dict(
            source_id=ident,
            r2_bucket=bucket,
            r2_key=key,
            sha256=digest,
            size_bytes=size,
        )
        for ident, bucket, key, digest, size in rows
    }
    missing = next((ident for ident in ids if ident not in sources), None)
    if missing is not None:
        raise ValueError(f'raw source {missing!r} is missing from the Neon catalog')
    return sources


def check_source(path: Path, source: dict[str, Any]) -> None:
    """Check a local file against the expected byte size and SHA-256.

    Check the size of the open file before reading it for the hash.

    Args:
        path: Local file path.
        source: Metadata containing the expected ``size_bytes`` and ``sha256``.

    Raises:
        ValueError: The file's size or hash differs from the expected value.
    """
    with path.open('rb') as stream:
        size = os.fstat(stream.fileno()).st_size
        if (
            size != source['size_bytes']
            or hashlib.file_digest(stream, 'sha256').hexdigest() != source['sha256']
        ):
            raise ValueError('source file size or hash differs from the Neon catalog')


def stream_source(
    client: BaseClient,
    source: dict[str, Any],
    output: IO[bytes],
    *,
    check_cancelled: Callable[[], None] = lambda: None,
) -> None:
    """Copy an R2 object to the caller's open binary output in chunks.

    Close the R2 response body after reading it. The caller owns the
    output and performs SHA-256 verification separately.

    Args:
        client: R2 client with an S3-compatible ``get_object`` method.
        source: Catalog entry with bucket, object key, and expected byte size.
        output: Open binary output that receives the object's bytes.
        check_cancelled: Optional callback before the request and each chunk.

    Raises:
        ValueError: The response length differs from the expected size.
    """
    check_cancelled()
    response = client.get_object(Bucket=source['r2_bucket'], Key=source['r2_key'])
    expected = source['size_bytes']
    with closing(response['Body']) as body:
        if response.get('ContentLength', expected) != expected:
            raise ValueError('source file size or hash differs from the Neon catalog')
        remaining = expected
        while remaining:
            check_cancelled()
            chunk = body.read(min(4 << 20, remaining))
            if not chunk:
                break
            output.write(chunk)
            remaining -= len(chunk)
        if remaining or body.read(1):
            raise ValueError('source file size or hash differs from the Neon catalog')


def download_source(
    client: BaseClient,
    source: dict[str, Any],
    work_dir: Path | str,
    *,
    timing: dict[str, Any] | None = None,
    filename: str | None = None,
) -> Path:
    """Return a verified local path for a cataloged R2 object.

    Verify cached content before reuse. Share the bytes by hard link when
    the cache has them under the default or provider filename. Verify a
    new download before making the final cache path available.

    Args:
        client: R2 client with an S3-compatible ``get_object`` method.
        source: Catalog entry with R2 location, byte size, and SHA-256.
        work_dir: Local cache root.
        timing: Optional dictionary that accumulates transfer durations and
            intervals, excluding verification and cached reuse.
        filename: Optional plain filename. Defaults to ``source`` with the
            object's suffix, or ``source.bin`` when it has no suffix.

    Returns:
        The cached ``Path`` under ``work_dir / sha256``.

    Raises:
        ValueError: The filename is invalid or the file fails verification.
    """
    directory = Path(work_dir) / source['sha256']
    directory.mkdir(parents=True, exist_ok=True)
    standard = 'source' + (Path(source['r2_key']).suffix or '.bin')
    filename = standard if filename is None else filename
    if not filename or Path(filename).name != filename or filename in ('.', '..'):
        raise ValueError('source cache needs a plain filename')
    destination = directory / filename
    if destination.exists():
        check_source(destination, source)
        return destination
    # A map build may have cached the same bytes under the provider filename.
    for name in dict.fromkeys((standard, Path(source['r2_key']).name)):
        existing = directory / name
        if existing != destination and existing.is_file():
            check_source(existing, source)
            try:
                os.link(existing, destination)
            except FileExistsError:
                check_source(destination, source)
            return destination
    output = NamedTemporaryFile(dir=directory, prefix='download-', delete=False)
    partial = Path(output.name)
    try:
        with output:
            started = time.monotonic()
            try:
                stream_source(client, source, output.file)
            finally:
                if timing is not None:
                    ended = time.monotonic()
                    timing['download_seconds'] = (
                        timing.get('download_seconds', 0.0) + ended - started
                    )
                    timing.setdefault('download_intervals', []).append((started, ended))
        check_source(partial, source)
        try:
            os.link(partial, destination)
        except FileExistsError:
            check_source(destination, source)
    finally:
        partial.unlink(missing_ok=True)
    return destination


def assemble_parts(
    client: BaseClient,
    parts: Sequence[dict[str, Any]],
    sha256: str,
    size_bytes: int,
    filename: str,
    work_dir: Path | str,
    *,
    timing: dict[str, Any] | None = None,
) -> Path:
    """Reassemble and verify a provider file stored as multiple R2 objects.

    Reuse a verified assembly when present. Otherwise concatenate the
    verified parts in byte order and check the complete file before caching it.

    Args:
        client: R2 client with an S3-compatible ``get_object`` method.
        parts: Catalog entries in the order of their bytes in the full file.
        sha256: Expected SHA-256 of the complete file.
        size_bytes: Expected size of the complete file in bytes.
        filename: Plain local filename for the assembled file.
        work_dir: Local cache root for the parts and complete file.
        timing: Optional dictionary that accumulates part transfer timings.

    Returns:
        The cached ``Path`` at ``work_dir / sha256 / filename``.

    Raises:
        ValueError: No parts were supplied, the filename is invalid, or the
            part sizes or file contents fail verification.
    """
    if (
        not parts
        or not filename
        or Path(filename).name != filename
        or filename in ('.', '..')
    ):
        raise ValueError('ordered source parts and a plain filename are required')
    if sum(part['size_bytes'] for part in parts) != size_bytes:
        raise ValueError('source part sizes do not match the complete file')
    source = {'sha256': sha256, 'size_bytes': size_bytes}
    directory = Path(work_dir) / sha256
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / filename
    if destination.exists():
        check_source(destination, source)
        return destination
    output = NamedTemporaryFile(dir=directory, prefix='assembly-', delete=False)
    partial = Path(output.name)
    try:
        with output:
            for part in parts:
                with download_source(client, part, work_dir, timing=timing).open(
                    'rb'
                ) as stream:
                    shutil.copyfileobj(stream, output, 1 << 20)
        check_source(partial, source)
        try:
            os.link(partial, destination)
        except FileExistsError:
            check_source(destination, source)
    finally:
        partial.unlink(missing_ok=True)
    return destination
