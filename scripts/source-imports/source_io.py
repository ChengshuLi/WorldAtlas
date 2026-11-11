"""Read construction records and raw catalogs from Neon; stage checked R2 archives."""
import hashlib
import json
from contextlib import closing
from pathlib import Path
import shutil
from tempfile import NamedTemporaryFile


def read_recipe(database, recipe_id, version):
    """Read a versioned construction record from the existing document table."""
    row = database.execute(
        'SELECT document::text,sha256,size_bytes FROM atlas.structured_documents '
        'WHERE source_id=%s AND version=%s', (recipe_id, version),
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
    return dict(zip(('r2_bucket', 'r2_key', 'sha256', 'size_bytes'), row),
                source_id=source_id, version=version)


def check_archive(path, source):
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if (path.stat().st_size, digest) != (source['size_bytes'], source['sha256']):
        raise ValueError('source archive size or hash differs from the Neon catalog')


def download_archive(client, source, work_dir):
    """Download and check the cataloged R2 object, or reuse a checked local copy."""
    directory = Path(work_dir) / source['sha256']
    directory.mkdir(parents=True, exist_ok=True)
    archive = directory / 'source.zip'
    if archive.exists():
        check_archive(archive, source)
        return archive
    output = NamedTemporaryFile(dir=directory, prefix='download-', delete=False)
    partial = Path(output.name)
    try:
        with output:
            response = client.get_object(Bucket=source['r2_bucket'], Key=source['r2_key'])
            with closing(response['Body']) as stream:
                shutil.copyfileobj(stream, output, 1 << 20)
        check_archive(partial, source)
        partial.replace(archive)
    finally:
        partial.unlink(missing_ok=True)
    return archive
