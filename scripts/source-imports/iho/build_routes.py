"""Build selected IHO S-130 routes from a Neon construction record and raw R2 data."""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path

from psycopg.types.json import Jsonb

from iho.s130 import extract_routes, validate_recipe
from source_io import read_recipe, catalog_source, download_archive


def save_routes(database, revision, result, source, recipe):
    """Save the selected endpoints, routes and ordered point links together."""
    common = {
        'basis': recipe['basis'],
        'source_refs': [dict(source_id=source['source_id'], version=source['version'],
                             sha256=source['sha256'])],
        'construction': dict(processor='iho.s130.extract_routes',
                             recipe_id=recipe['recipe_id'], recipe_version=recipe['recipe_version']),
    }
    with database.transaction():
        for endpoint in result['endpoints']:
            database.execute(
                'INSERT INTO atlas.decision_endpoints '
                '(revision,endpoint_id,name,longitude,latitude,derivation,evidence) '
                'VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (revision,endpoint_id) '
                'DO UPDATE SET name=EXCLUDED.name,longitude=EXCLUDED.longitude,'
                'latitude=EXCLUDED.latitude,derivation=EXCLUDED.derivation,'
                "evidence=(atlas.decision_endpoints.evidence - 'selector' - 'point_id') || EXCLUDED.evidence",
                (revision, endpoint['endpoint_id'], endpoint['name'], endpoint['longitude'],
                 endpoint['latitude'], Jsonb(endpoint['derivation']),
                 Jsonb(dict(endpoint['evidence'], **common))),
            )
        for route in result['routes']:
            database.execute(
                'INSERT INTO atlas.decision_routes '
                '(revision,route_id,route_type,parameters,evidence) VALUES (%s,%s,%s,%s,%s) '
                'ON CONFLICT (revision,route_id) DO UPDATE SET route_type=EXCLUDED.route_type,'
                'parameters=EXCLUDED.parameters,'
                'evidence=atlas.decision_routes.evidence || EXCLUDED.evidence',
                (revision, route['route_id'], route['route_type'], Jsonb(route['parameters']),
                 Jsonb(dict(route['evidence'], **common))),
            )
            database.execute('DELETE FROM atlas.decision_route_points WHERE revision=%s AND route_id=%s',
                             (revision, route['route_id']))
            with database.cursor() as cursor:
                cursor.executemany(
                    'INSERT INTO atlas.decision_route_points VALUES (%s,%s,%s,%s)',
                    [(revision, route['route_id'], point['ordinal'], point['endpoint_id'])
                     for point in route['points']],
                )


def build_routes(database, client, recipe_id, recipe_version, revision, work_dir):
    with database.transaction():
        if database.execute('SELECT 1 FROM atlas.decision_revisions WHERE revision=%s',
                            (revision,)).fetchone() is None:
            raise ValueError('destination decision revision does not exist')
        recipe = read_recipe(database, recipe_id, recipe_version)
        validate_recipe(recipe)
        source = catalog_source(database, recipe['source_id'], recipe['source_version'])
    archive = download_archive(client, source, work_dir)
    result = extract_routes(archive, source['sha256'], recipe)
    save_routes(database, revision, result, source, recipe)
    return dict(revision=revision, route_ids=[route['route_id'] for route in result['routes']],
                endpoint_count=len(result['endpoints']), archive=str(archive))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipe', nargs=2, required=True, metavar=('ID', 'VERSION'))
    parser.add_argument('--revision', required=True)
    parser.add_argument('--r2-endpoint', required=True)
    parser.add_argument('--work-dir', type=Path, required=True)
    args = parser.parse_args()
    connection = os.environ.get('NEON_DATABASE_URL')
    if not connection:
        parser.error('set NEON_DATABASE_URL to the working database')
    import boto3
    import psycopg

    with psycopg.connect(connection) as database, closing(
            boto3.client('s3', endpoint_url=args.r2_endpoint, region_name='auto')) as storage:
        result = build_routes(database, storage, *args.recipe, args.revision, args.work_dir)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
