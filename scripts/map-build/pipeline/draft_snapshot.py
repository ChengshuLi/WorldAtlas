"""Read and prepare the mainland decisions selected for a preview."""

import copy
import hashlib
import json
import os
from decimal import Decimal
from pathlib import Path


LAND_EXPORT = (
    Path(__file__).resolve().parents[1]
    / 'land/mainland-l2-draft/query-stage2-selected.sql'
)
REGIONAL_EXPORT = (Path(__file__).resolve().parents[1]
                   / 'land/research-mixed-runtime/stage3-mixed-leeward-full-20261105/export_regional.sql')


def read_regional_decisions(revision):
    """Read the working regional records, selected rule, and its current boundary together."""
    import psycopg

    connection = os.environ.get('NEON_DATABASE_URL')
    if not connection:
        raise ValueError('set NEON_DATABASE_URL to the working database')
    with psycopg.connect(connection) as database:
        database.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        snapshot = json.loads(database.execute(REGIONAL_EXPORT.read_text(), {'revision': revision}).fetchone()[0])
        rows = database.execute(
            'SELECT line_id,definition FROM atlas.regional_island_rule_sets '
            "WHERE revision=%s AND selection_status='selected_for_research'", (revision,)).fetchall()
        if len(rows) != 1:
            raise ValueError('the regional builder requires one selected island rule')
        line_id, policy = rows[0]
        row = database.execute(
            "SELECT (to_jsonb(l)-'created_at')::text FROM atlas.geographic_line_observations l "
            'WHERE line_id=%s', (line_id,)).fetchone()
        if row is None:
            raise ValueError('selected regional boundary is missing')
        line = json.loads(row[0])
        policy['line'] = {'line_id': line_id, 'geometry_sha256': line['geometry_sha256']}
    return {'snapshot': snapshot, 'policy': policy, 'line': line}


def read_land_draft(revision):
    """Export a single, consistent view of working mainland decisions."""
    if not isinstance(revision, str) or not revision.strip():
        raise ValueError('a mainland revision is required')
    connection = os.environ.get('NEON_DATABASE_URL')
    if not connection:
        raise ValueError('set NEON_DATABASE_URL to the database containing the mainland revision')

    import psycopg

    try:
        with psycopg.connect(connection) as database:
            database.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            row = database.execute(LAND_EXPORT.read_text(), {'revision': revision}).fetchone()
    except psycopg.Error:
        raise ValueError('Neon mainland export failed; check working database access') from None
    draft = json.loads(row[0]) if row is not None else {}
    identity = draft.get('decision_revision') or {}
    if (identity.get('id') != revision
            or draft.get('source') != 'neon-export'
            or not draft.get('land_baseline_policy')
            or not draft.get('seed_regions')):
        raise ValueError(f'no selected mainland decisions found for {revision}')
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


def assembled_region_hash(decision, records):
    """Mirror the region builder's ordered, exact-join ring serialization."""
    ring = []
    for segment in decision['segments']:
        record = records[(segment['kind'], segment['id'])]
        coordinates = record['geometry']['coordinates']
        start, end = segment['start'], segment['end']
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(coordinates) or end - start < 2:
            raise ValueError('invalid region slice')
        pts = [tuple(Decimal(str(v)) for v in p) for p in coordinates[start:end]]
        if any(len(p) != 2 or any(not v.is_finite() for v in p) for p in pts):
            raise ValueError('invalid region coordinate')
        if type(segment['reverse']) is not bool:
            raise ValueError('invalid region direction')
        if segment['reverse']:
            pts.reverse()
        if ring and ring[-1] != pts[0]:
            raise ValueError('region does not join exactly')
        ring.extend(pts if not ring else pts[1:])
    if len(ring) < 4 or ring[0] != ring[-1]:
        raise ValueError('region is not explicitly closed')
    geom = {'type': 'Polygon', 'coordinates': [[[float(x), float(y)] for x, y in ring]]}
    return hashlib.sha256(json.dumps(geom, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def prepare_land_draft(draft, published):
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
        region['geometry_sha256'] = assembled_region_hash(region, lines)
    return prepared
