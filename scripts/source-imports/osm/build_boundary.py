"""Build an editable Neon boundary from an OSM way archive cataloged in Neon."""
import argparse
import hashlib
import json
from contextlib import closing
import os
from pathlib import Path

from psycopg.types.json import Jsonb

from osm.ways import assemble_archive
from source_io import read_recipe, catalog_source, download_archive


def save_boundary(database, revision, geometry, source, recipe):
    """Save geometry and its construction source together, retaining other evidence."""
    raw = json.dumps(geometry, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    digest = hashlib.sha256(raw).hexdigest()
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
            "WHERE revision=%s AND boundary_id=%s AND relationship='construction_input' "
            "AND (source_id,source_version)<>(%s,%s)",
            (revision, recipe['boundary_id'], source['source_id'], source['version']),
        )
        database.execute(
            "INSERT INTO atlas.decision_mainland_boundary_sources "
            "(revision,boundary_id,source_id,source_version,relationship) "
            "VALUES (%s,%s,%s,%s,'construction_input') "
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
        fields = {'method', 'source_id', 'source_version', 'boundary_id', 'basis',
                  'recipe_id', 'recipe_version'}
        if (set(recipe) != fields
                or any(not isinstance(value, str) or not value.strip() for value in recipe.values())):
            raise ValueError('invalid OSM construction record')
        if recipe['method'] != 'osm_way_chain':
            raise ValueError('unsupported construction method')
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
