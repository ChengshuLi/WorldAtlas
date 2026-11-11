"""Build an editable Neon boundary from an OSM way archive cataloged in Neon."""
import argparse
import json
from contextlib import closing
import os
from pathlib import Path

from osm.ways import assemble_archive
from source_io import read_recipe, catalog_source, download_source, save_boundary as save_mainland_boundary


def save_boundary(database, revision, geometry, source, recipe):
    """Save geometry and its construction source together, retaining other evidence."""
    provenance = {
        'basis': recipe['basis'],
        'lineage_status': 'complete',
        'construction': {
            'processor': 'osm.ways.assemble',
            'recipe_id': recipe['recipe_id'],
            'recipe_version': recipe['recipe_version'],
            'source_id': source['source_id'],
            'source_version': source['version'],
            'archive_sha256': source['sha256'],
        },
    }
    return save_mainland_boundary(database, revision, recipe['boundary_id'], geometry,
                                  provenance, [source])


def build_boundary(database, client, recipe_id, recipe_version, revision,
                   work_dir, expected_geometry_sha256=None):
    """Look up, download, assemble, and save one boundary in the requested revision."""
    with database.transaction():
        if database.execute('SELECT 1 FROM atlas.decision_revisions WHERE revision=%s',
                            (revision,)).fetchone() is None:
            raise ValueError('destination decision revision does not exist')
        recipe = read_recipe(database, recipe_id, recipe_version)
        fields = {'method', 'source_id', 'source_version', 'boundary_id', 'basis',
                  'recipe_id', 'recipe_version'}
        if (set(recipe) != fields
                or any(not isinstance(value, str) or not value.strip() for value in recipe.values())):
            raise ValueError('invalid OSM construction record')
        if recipe['method'] != 'osm_way_chain':
            raise ValueError('unsupported construction method')
        source = catalog_source(database, recipe['source_id'], recipe['source_version'])
    archive = download_source(client, source, work_dir)
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
