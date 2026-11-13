"""Resolve cataloged inputs and stage verified files for importers and map builds."""

import hashlib
import json
import os
from contextlib import closing
from pathlib import Path
import shutil
from tempfile import NamedTemporaryFile
import time


def read_recipe(database, recipe_id, version):
    """Read a versioned construction record from the existing document table."""
    row = database.execute(
        'SELECT document::text,sha256,size_bytes FROM atlas.structured_documents '
        'WHERE source_id=%s AND version=%s',
        (recipe_id, version),
    ).fetchone()
    if row is None:
        raise ValueError('construction record is missing from Neon')
    text, digest, size = row
    raw = text.encode()
    if len(raw) != size or hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('construction record size or hash mismatch')
    recipe = json.loads(text)
    if not isinstance(recipe, dict):
        raise ValueError('invalid construction record')
    return dict(recipe, recipe_id=recipe_id, recipe_version=version)


def catalog_source(database, source_id, version):
    """Look up an exact raw source version and its R2 location."""
    row = database.execute(
        "SELECT r2_bucket,r2_key,sha256,size_bytes FROM atlas.source_assets "
        "WHERE kind='raw' AND source_id=%s AND version=%s",
        (source_id, version),
    ).fetchone()
    if row is None:
        raise ValueError('raw source version is missing from the Neon catalog')
    return dict(
        zip(('r2_bucket', 'r2_key', 'sha256', 'size_bytes'), row),
        source_id=source_id,
        version=version,
    )


def check_source(path, source):
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if (path.stat().st_size, digest) != (source['size_bytes'], source['sha256']):
        raise ValueError('source file size or hash differs from the Neon catalog')


def stream_source(client, source, output, *, check_cancelled=lambda: None):
    """Copy a complete R2 object and enforce its cataloged byte length."""
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
    """Download and check a cataloged R2 file, or reuse a verified local copy."""
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

    Each physical R2 object has its own catalog record. The construction records
    their order and the complete provider file's size and checksum.
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
