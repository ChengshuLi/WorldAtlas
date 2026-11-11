"""Build an editable Neon boundary from an OSM way archive cataloged in Neon."""
import argparse
import hashlib
import json
from contextlib import closing
import os
from pathlib import Path
import shutil
from tempfile import NamedTemporaryFile

from psycopg.types.json import Jsonb

from osm.ways import assemble_archive


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
    fields = {'method', 'source_id', 'source_version', 'boundary_id', 'basis'}
    if (not isinstance(recipe, dict) or set(recipe) != fields
            or any(not isinstance(value, str) or not value.strip() for value in recipe.values())):
        raise ValueError('invalid OSM construction record')
    if recipe['method'] != 'osm_way_chain':
        raise ValueError('unsupported construction method')
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


def save_boundary(database, revision, geometry, source, recipe):
    """Save geometry and its construction source together, retaining other evidence."""
    raw = json.dumps(geometry, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    digest = hashlib.sha256(raw).hexdigest()
    provenance = {
        'basis': recipe['basis'],
        'construction': {
            'processor': 'osm.ways.assemble',
            'recipe_id': recipe['recipe_id'],
            'recipe_version': recipe['recipe_version'],
            'source_id': source['source_id'],
            'source_version': source['version'],
            'archive_sha256': source['sha256'],
        },
    }
    with database.transaction():
        database.execute(
            "INSERT INTO atlas.decision_mainland_boundaries "
            "(revision,boundary_id,method,execution_status,geometry,geometry_sha256,"
            "geometry_hash_method,coordinate_reference,provenance) "
            "VALUES (%s,%s,'stored_linestring_v1','selected_for_research',%s,%s,"
            "'binary64-sorted-compact-geojson-v1','OGC:CRS84',%s) "
            "ON CONFLICT (revision,boundary_id) DO UPDATE SET "
            "geometry=EXCLUDED.geometry,geometry_sha256=EXCLUDED.geometry_sha256,"
            "provenance=atlas.decision_mainland_boundaries.provenance || EXCLUDED.provenance",
            (revision, recipe['boundary_id'], Jsonb(geometry), digest, Jsonb(provenance)),
        )
        database.execute(
            "DELETE FROM atlas.decision_mainland_boundary_sources "
            "WHERE revision=%s AND boundary_id=%s AND relationship='geometry_source' "
            "AND (source_id,source_version)<>(%s,%s)",
            (revision, recipe['boundary_id'], source['source_id'], source['version']),
        )
        database.execute(
            "INSERT INTO atlas.decision_mainland_boundary_sources "
            "(revision,boundary_id,source_id,source_version,relationship) "
            "VALUES (%s,%s,%s,%s,'geometry_source') "
            "ON CONFLICT (revision,boundary_id,source_id,source_version) "
            "DO UPDATE SET relationship=EXCLUDED.relationship",
            (revision, recipe['boundary_id'], source['source_id'], source['version']),
        )
    return digest


def build_boundary(database, client, recipe_id, recipe_version, revision,
                   work_dir, expected_geometry_sha256=None):
    """Look up, download, assemble, and save one boundary in the requested revision."""
    with database.transaction():
        if database.execute('SELECT 1 FROM atlas.decision_revisions WHERE revision=%s',
                            (revision,)).fetchone() is None:
            raise ValueError('destination decision revision does not exist')
        recipe = read_recipe(database, recipe_id, recipe_version)
        source = catalog_source(database, recipe['source_id'], recipe['source_version'])
    archive = download_archive(client, source, work_dir)
    geometry = assemble_archive(archive, source['sha256'], expected_geometry_sha256)
    digest = save_boundary(database, revision, geometry, source, recipe)
    return {'revision': revision, 'boundary_id': recipe['boundary_id'],
            'vertices': len(geometry['coordinates']), 'sha256': digest,
            'archive': str(archive)}


def main():
    """Build the OSM boundary described by a selected Neon construction record."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipe', nargs=2, required=True, metavar=('ID', 'VERSION'),
                        help='construction record source_id and version in Neon')
    parser.add_argument('--revision', required=True,
                        help='existing decision revision to write in Neon')
    parser.add_argument('--r2-endpoint', required=True)
    parser.add_argument('--work-dir', type=Path, required=True)
    parser.add_argument('--expected-geometry-sha256',
                        help='check an existing boundary before writing, e.g. a release replay')
    args = parser.parse_args()
    connection = os.environ.get('NEON_DATABASE_URL')
    if not connection:
        parser.error('set NEON_DATABASE_URL to the working database')

    import boto3
    import psycopg

    with psycopg.connect(connection) as database, closing(
            boto3.client('s3', endpoint_url=args.r2_endpoint, region_name='auto')) as storage:
        result = build_boundary(database, storage, *args.recipe,
                                args.revision, args.work_dir,
                                args.expected_geometry_sha256)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
