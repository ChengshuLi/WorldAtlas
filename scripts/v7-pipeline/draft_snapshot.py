"""Read and prepare the mainland decisions selected for a preview."""

import copy
import hashlib
import json
import os
from pathlib import Path


LAND_EXPORT = (
    Path(__file__).resolve().parents[1]
    / 'v7-land/mainland-l2-draft/query-stage2-selected.sql'
)


def read_land_draft(revision):
    """Export a single, consistent view of a named Neon draft."""
    if not isinstance(revision, str) or not revision.strip():
        raise ValueError('a mainland draft revision is required')
    connection = os.environ.get('NEON_DATABASE_URL')
    if not connection:
        raise ValueError('set NEON_DATABASE_URL to the database containing the draft')

    import psycopg

    try:
        with psycopg.connect(connection) as database:
            database.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            row = database.execute(LAND_EXPORT.read_text(), {'revision': revision}).fetchone()
    except psycopg.Error:
        raise ValueError('Neon mainland export failed; check draft database access') from None
    draft = json.loads(row[0]) if row is not None else {}
    identity = draft.get('decision_revision') or {}
    if (identity.get('id') != revision or identity.get('status') != 'draft'
            or draft.get('source') != 'neon-export'
            or not draft.get('land_baseline_policy')
            or not draft.get('seed_regions')):
        raise ValueError(f'no selected mainland draft found for {revision}')
    return draft


def read_release_streams(version):
    """Resolve the two published streams without embedding object paths in a preview."""
    connection = os.environ.get('NEON_DATABASE_URL')
    if not connection:
        raise ValueError('set NEON_DATABASE_URL to the database containing the map release')

    import psycopg

    try:
        with psycopg.connect(connection) as database:
            database.execute('SET TRANSACTION READ ONLY')
            rows = database.execute(
                'SELECT stream,r2_bucket,r2_key,size_bytes,stored_sha256,decoded_sha256 '
                'FROM atlas.map_release_objects WHERE map_version=%s ORDER BY stream',
                (version,),
            ).fetchall()
    except psycopg.Error:
        raise ValueError('Neon release lookup failed; check release database access') from None
    if [row[0] for row in rows] != ['rows', 'runs']:
        raise ValueError(f'missing row or run stream for map release {version}')
    return rows


def draft_physical_selection(draft, published):
    """Record the draft's physical sources and require the published selection."""
    revision = draft['decision_revision']['id']
    sources = {(row['source_id'], row['version']): row for row in draft['sources']}
    rows = []
    for selection in draft['stage1_source_inputs']:
        if selection['decision_revision'] != revision:
            raise ValueError('physical source selection belongs to another draft')
        source = sources.get((selection['source_id'], selection['source_version']))
        if source is None:
            raise ValueError('draft physical source is missing from the catalog export')
        rows.append({
            **source,
            'size_bytes': str(source['size_bytes']),
            'revision': revision,
            'role': selection['role'],
            'ordinal': selection['ordinal'],
            'execution_status': selection['execution_status'],
        })
    expected = [{**row, 'revision': revision, 'size_bytes': str(row['size_bytes'])}
                for row in published['rows']]

    def by_role(row):
        return row['role'], row['ordinal']

    if sorted(rows, key=by_role) != sorted(expected, key=by_role):
        raise ValueError('preview physical sources differ from the published selection')
    return {'schema': published['schema'], 'revision': revision, 'rows': rows}


def prepare_land_draft(draft, published, assemble_region_hash):
    """Recalculate geometry pins for a preview of the editable draft."""
    prepared = copy.deepcopy(draft)
    for section, key in (('mainland_boundaries', 'boundary_id'), ('routes', 'route_id')):
        baseline = {row[key] for row in published[section]}
        if {row[key] for row in prepared[section]} != baseline:
            raise ValueError(f'preview requires the published set of {section}')
        for row in prepared[section]:
            geometry = row['geometry']
            canonical = {'type': geometry['type'],
                         'coordinates': [[float(x), float(y)] for x, y in geometry['coordinates']]}
            geometry_bytes = json.dumps(canonical, sort_keys=True, separators=(',', ':'),
                                        allow_nan=False).encode()
            row['geometry_sha256'] = hashlib.sha256(geometry_bytes).hexdigest()

    lines = {('boundary', row['boundary_id']): row for row in prepared['mainland_boundaries']}
    lines.update({('route', row['route_id']): row for row in prepared['routes']})
    for region in prepared['seed_regions']:
        region['geometry_sha256'] = assemble_region_hash(region, lines)
    return prepared
