"""Select a source constructor from a versioned Neon record's method."""
import argparse
import hashlib
from contextlib import ExitStack, closing
import json
import logging
import os
from pathlib import Path

from worldatlas.source_imports.atlas_sources.catalog import read_recipe


from worldatlas.source_imports.contracts import Runtime, bind_document
from worldatlas.source_imports.traces.build_boundary import smooth_latitude_trace
from worldatlas.source_imports.osm.build_boundary import osm_way_chain
from worldatlas.source_imports.iho.build_routes import s130_rhumb_routes
from worldatlas.source_imports.watersheds.build_boundary import watershed_boundary
from worldatlas.source_imports.features.build_features import (
    selected_vector_features, selected_table_points, selected_osm_features, s130_areas,
)

IMPORTERS = {constructor.__name__: constructor for constructor in (
    smooth_latitude_trace, osm_way_chain, s130_rhumb_routes, watershed_boundary,
    selected_vector_features, selected_table_points, selected_osm_features, s130_areas,
)}


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
        document = read_recipe(database, recipe_id, version)
    method = document.get('method')
    importer = IMPORTERS.get(method) if isinstance(method, str) else None
    if importer is None:
        raise ValueError(f'unsupported source construction method: {method!r}')
    if method != 'smooth_latitude_trace' and (storage is None or not revision or work_dir is None):
        raise ValueError('this method requires --revision, --r2-endpoint and --work-dir')
    if (expected_geometry_sha256 is not None and
            method not in ('smooth_latitude_trace', 'osm_way_chain')):
        raise ValueError('an expected geometry checksum applies to traced and OSM boundaries')
    arguments = bind_document(importer, document)
    runtime = Runtime(connect, storage, recipe_id, version, method, revision, work_dir,
                      expected_geometry_sha256)
    return importer(runtime, **arguments)


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
