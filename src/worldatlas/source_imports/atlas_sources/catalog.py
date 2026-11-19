"""Resolve cataloged inputs and stage verified files for importers and map builds."""

import hashlib
import os
from contextlib import closing
from pathlib import Path
import shutil
from tempfile import NamedTemporaryFile
import time


def read_recipe(database, recipe_id):
    """Return the stored method and arguments for a construction ID.

    Use the caller's PostgreSQL connection and transaction. Raise
    ``ValueError`` if the construction record is missing.
    """
    row = database.execute(
        'SELECT method,arguments FROM atlas.construction_records '
        'WHERE id=%s',
        (recipe_id,),
    ).fetchone()
    if row is None:
        raise ValueError('construction record is missing from Neon')
    return row


def catalog_source(database, source_id):
    """Resolve a raw source ID into its R2 location and expected file identity.

    Return a dictionary with the source ID, bucket, object key, byte size,
    and SHA-256. Raise ``ValueError`` if the catalog entry is missing.
    """
    row = database.execute(
        "SELECT r2_bucket,r2_key,sha256,size_bytes FROM atlas.source_assets "
        "WHERE id=%s",
        (source_id,),
    ).fetchone()
    if row is None:
        raise ValueError('raw source is missing from the Neon catalog')
    return dict(
        zip(('r2_bucket', 'r2_key', 'sha256', 'size_bytes'), row),
        source_id=source_id,
    )


def check_source(path, source):
    """Check a local file against the expected byte size and SHA-256.

    Check the size of the open file before reading it for the hash. Raise
    ``ValueError`` when either value differs from the source record.
    """
    with path.open('rb') as stream:
        size = os.fstat(stream.fileno()).st_size
        if (
            size != source['size_bytes']
            or hashlib.file_digest(stream, 'sha256').hexdigest() != source['sha256']
        ):
            raise ValueError('source file size or hash differs from the Neon catalog')


def stream_source(client, source, output, *, check_cancelled=lambda: None):
    """Copy an R2 object to the caller's open binary output in chunks.

    ``source`` supplies the R2 bucket, object key, and expected byte size.
    Check cancellation before the request and before each chunk. Close
    the response body and reject any byte-length mismatch. The caller
    owns the output and performs SHA-256 verification separately.
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


def download_source(client, source, work_dir, *, timing=None, filename=None):
    """Return a verified local path for a cataloged R2 object.

    Cache the file under ``work_dir / sha256`` using the supplied plain
    filename or a default such as ``source.zip``. Reuse verified cached
    content, sharing it by hard link when the two callers use different
    names. A corrupt cache entry raises an error. On a cache miss, verify
    the temporary download before linking it into the cache.

    If supplied, ``timing`` accumulates transfer durations and intervals.
    Verification and cached reuse are outside those measurements.
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
    # Both callers use the same content directory. Preserve their established
    # filenames without downloading or copying bytes already cached by the other.
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
                stream_source(client, source, output)
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


def assemble_parts(client, parts, sha256, size_bytes, filename, work_dir, *, timing=None):
    """Reassemble a provider file from cataloged byte parts and verify the whole.

    ``parts`` contains the catalog entries in byte order. Their sizes
    must sum to ``size_bytes``. Reuse a verified assembly if present.
    Otherwise download or reuse each part, concatenate them, and verify
    the complete file before caching it. Return the path under the
    complete file's SHA-256. Report only part transfers in ``timing``.
    """
    if not parts or not filename or Path(filename).name != filename or filename in ('.', '..'):
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
                with download_source(client, part, work_dir, timing=timing).open('rb') as stream:
                    shutil.copyfileobj(stream, output, 1 << 20)
        check_source(partial, source)
        try:
            os.link(partial, destination)
        except FileExistsError:
            check_source(destination, source)
    finally:
        partial.unlink(missing_ok=True)
    return destination
