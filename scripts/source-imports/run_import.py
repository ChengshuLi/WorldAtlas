"""Select a source constructor from a versioned Neon record's method."""
import argparse
import hashlib
from contextlib import ExitStack, closing
import json
import logging
import os
from pathlib import Path

from atlas_sources.catalog import read_recipe


def _trace(connect, storage, recipe_id, version, revision, work_dir, expected):
    from traces.build_boundary import build_boundary
    with connect() as database:
        return build_boundary(database, recipe_id, version, expected)


def _osm(connect, storage, recipe_id, version, revision, work_dir, expected):
    from osm.build_boundary import build_boundary
    with connect() as database:
        return build_boundary(database, storage, recipe_id, version, revision, work_dir, expected)


def _iho(connect, storage, recipe_id, version, revision, work_dir, expected):
    from iho.build_routes import build_routes
    with connect() as database:
        return build_routes(database, storage, recipe_id, version, revision, work_dir)


def _watershed(connect, storage, recipe_id, version, revision, work_dir, expected):
    from watersheds.build_boundary import build_boundary
    return build_boundary(connect, storage, recipe_id, version, revision, work_dir)


def _features(connect, storage, recipe_id, version, revision, work_dir, expected):
    from features.build_features import build_features
    with connect() as database:
        return build_features(database, storage, recipe_id, version, revision, work_dir)


IMPORTERS = {
    'smooth_latitude_trace': _trace,
    'osm_way_chain': _osm,
    's130_rhumb_routes': _iho,
    'watershed_boundary': _watershed,
    'selected_vector_features': _features,
    'selected_table_points': _features,
    'selected_osm_features': _features,
    's130_areas': _features,
}


def selected_constructions(database, revisions):
    """List the exact constructors contributing to the selected editable revisions."""
    known = {row[0] for row in database.execute('SELECT revision FROM atlas.decision_revisions WHERE revision=ANY(%s)', (list(revisions),))}
    if set(revisions) - known:
        raise ValueError('unknown decision revisions: ' + str(sorted(set(revisions) - known)))
    rows = database.execute(
        'SELECT DISTINCT construction_id,construction_version,revision FROM ('
        'SELECT construction_id,construction_version,revision FROM atlas.decision_features '
        'UNION ALL SELECT construction_id,construction_version,revision FROM atlas.decision_mainland_boundaries '
        'UNION ALL SELECT construction_id,construction_version,revision FROM atlas.decision_routes '
        'UNION ALL SELECT construction_id,construction_version,revision FROM atlas.decision_endpoints '
        'UNION ALL SELECT l.construction_id,l.construction_version,r.revision '
        'FROM atlas.regional_island_rule_sets r JOIN atlas.geographic_line_observations l USING(line_id) '
        'WHERE r.enabled) c WHERE revision=ANY(%s) AND construction_id IS NOT NULL '
        'ORDER BY revision,construction_id,construction_version', (list(revisions),),
    ).fetchall()
    return rows


def run_import(connect, recipe_id, version, *, storage=None, revision=None,
               work_dir=None, expected_geometry_sha256=None):
    """Read the method, check required inputs, and call its Python constructor."""
    with connect() as database:
        method = read_recipe(database, recipe_id, version).get('method')
    importer = IMPORTERS.get(method) if isinstance(method, str) else None
    if importer is None:
        raise ValueError(f'unsupported source construction method: {method!r}')
    if method != 'smooth_latitude_trace' and (storage is None or not revision or work_dir is None):
        raise ValueError('this method requires --revision, --r2-endpoint and --work-dir')
    if (expected_geometry_sha256 is not None and
            method not in ('smooth_latitude_trace', 'osm_way_chain')):
        raise ValueError('an expected geometry checksum applies to traced and OSM boundaries')
    return importer(connect, storage, recipe_id, version, revision, work_dir,
                    expected_geometry_sha256)


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument('--recipe', nargs=2, metavar=('ID', 'VERSION'))
    selection.add_argument('--revisions', nargs='+', help='regenerate constructions selected by these revisions')
    parser.add_argument('--revision', help='existing decision revision for OSM, IHO and watersheds')
    parser.add_argument('--r2-endpoint', help='R2 endpoint for methods that download raw files')
    parser.add_argument('--work-dir', type=Path, help='verified source cache and local receipts')
    parser.add_argument('--expected-geometry-sha256', help='optional traced/OSM boundary check before saving')
    args = parser.parse_args()
    if not (connection := os.environ.get('NEON_DATABASE_URL')):
        parser.error('set NEON_DATABASE_URL to the working database')
    import psycopg

    connect = lambda: psycopg.connect(connection, connect_timeout=15)
    with ExitStack() as stack:
        storage = None
        if args.r2_endpoint:
            import boto3
            storage = stack.enter_context(closing(boto3.client(
                's3', endpoint_url=args.r2_endpoint, region_name='auto')))
        if args.revisions:
            if args.revision or args.expected_geometry_sha256:
                parser.error('--revisions cannot be combined with --revision or an expected checksum')
            with connect() as database:
                database.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
                constructions = selected_constructions(database, args.revisions)
        else:
            constructions = [(*args.recipe, args.revision)]
        results = []
        for ident, version, revision in constructions:
            result = run_import(connect, ident, version, storage=storage, revision=revision,
                                work_dir=args.work_dir,
                                expected_geometry_sha256=args.expected_geometry_sha256)
            results.append(result)
            if args.work_dir is not None:
                identity = {'construction_id': ident, 'version': version, 'revision': revision}
                name = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
                receipt = args.work_dir / 'receipts' / (name + '.json')
                receipt.parent.mkdir(parents=True, exist_ok=True)
                receipt.write_text(json.dumps(dict(identity, result=result), indent=2) + '\n')
        result = results if args.revisions else results[0]
    print(json.dumps(result))


if __name__ == '__main__':
    main()
