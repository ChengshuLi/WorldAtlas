"""Freeze working geographic decisions in one short, read-only transaction."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from map_build.inputs.features import selected_basins


HERE = Path(__file__).resolve().parent
QUERIES = {name: HERE / (name + '.sql') for name in ('mainland', 'regional')}
QUERIES.update(water=HERE / 'geography.sql', ocean=HERE / 'geography.sql')


def canonical_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=False, allow_nan=False) + '\n').encode()


def read_selection(database, revisions, *, raw_sources=(), documents=()):
    """Return the selected domains, catalogs and colors, then end the transaction.

    Call with an idle connection. Computation and downloads happen after this
    function returns. Resume reads the saved result instead of querying again.
    """
    if (not revisions or set(revisions) - QUERIES.keys()
            or any(not isinstance(value, str) or not value.strip() for value in revisions.values())):
        raise ValueError('select named mainland, regional, water or ocean revisions')
    result = {'schema': 'worldatlas-input-selection-v1', 'revisions': revisions,
              'selected_at': datetime.now(timezone.utc).isoformat(), 'domains': {}}
    with database.transaction():
        database.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        references = set(raw_sources)
        registries = set()
        for domain, revision in revisions.items():
            row = database.execute(QUERIES[domain].read_text(), {'revision': revision}).fetchone()
            data = json.loads(row[0]) if row else {}
            features = {feature['feature_id']: feature for feature in data.get('features', [])}
            # Geometry can be large. Read records directly instead of asking
            # PostgreSQL to construct one enormous JSON aggregate in memory.
            with database.cursor(name='selected_features_' + domain) as cursor:
                cursor.execute('SELECT feature_id,geometry::text FROM atlas.decision_features '
                               'WHERE revision=%s AND geometry IS NOT NULL ORDER BY feature_id', (revision,))
                for feature_id, geometry in cursor:
                    features[feature_id]['geometry'] = json.loads(geometry)
            identity = data.get('decision_revision') or {}
            if identity.get('id') != revision:
                raise ValueError('selected geographic revision is missing: ' + revision)
            if domain == 'water':
                selected_basins(data)
            result['domains'][domain] = data
            registries.add(identity['entity_revision'])
            references.update((source['source_id'], source['version']) for source in data['sources'])
        if 'regional' in revisions:
            rows = database.execute(
                'SELECT rule_set_id,line_id,definition FROM atlas.regional_island_rule_sets '
                "WHERE revision=%s AND selection_status <> 'withdrawn' ORDER BY rule_set_id",
                (revisions['regional'],)).fetchall()
            result['regional_partitions'] = []
            for rule_set_id, line_id, definition in rows:
                line = database.execute(
                    "SELECT to_jsonb(l)-'created_at' FROM atlas.geographic_line_observations l WHERE line_id=%s",
                    (line_id,)).fetchone()
                if line is None:
                    raise ValueError('selected geographic line is missing')
                result['regional_partitions'].append({'rule_set_id': rule_set_id, 'line': line[0], 'policy': definition})
                references.add((line[0]['source_id'], line[0]['source_version']))
                references.update((source['source_id'], source['version'])
                                  for source in definition.get('sources', []))
        requested = sorted(references)
        rows = database.execute(
            "SELECT to_jsonb(a)-'created_at' FROM atlas.source_assets a WHERE kind='raw' "
            'AND (source_id,version) IN (SELECT * FROM unnest(%s::text[],%s::text[])) '
            'ORDER BY source_id,version',
            ([key[0] for key in requested], [key[1] for key in requested])).fetchall()
        result['raw_sources'] = [row[0] for row in rows]
        missing = references - {(row['source_id'], row['version']) for row in result['raw_sources']}
        if missing:
            raise ValueError('selected raw source is missing: ' + str(sorted(missing)))
        result['documents'] = []
        for source_id, version in sorted(set(documents)):
            row = database.execute(
                'SELECT document::text,sha256,size_bytes FROM atlas.structured_documents '
                'WHERE source_id=%s AND version=%s', (source_id, version)).fetchone()
            if row is None:
                raise ValueError('selected document is missing: ' + source_id)
            text, checksum, size = row
            raw = text.encode()
            if len(raw) != size or hashlib.sha256(raw).hexdigest() != checksum:
                raise ValueError('selected document checksum or size differs: ' + source_id)
            result['documents'].append({'source_id': source_id, 'version': version,
                                        'document_text': text, 'sha256': checksum, 'size_bytes': size})
        rows = database.execute(
            'SELECT e.revision,jsonb_agg(jsonb_build_object('
            "'entity_id',e.id,'color_rgb',i.color_rgb) ORDER BY e.id) "
            'FROM atlas.geographic_entities e JOIN atlas.geographic_entity_ids i USING(id) '
            'WHERE e.revision=ANY(%s) GROUP BY e.revision ORDER BY e.revision',
            (sorted(registries),)).fetchall()
        result['registry_colors'] = dict(rows)
    return result


def read_saved(path, expected_revisions=None):
    result = json.loads(Path(path).read_bytes())
    if result.get('schema') != 'worldatlas-input-selection-v1':
        raise ValueError('unsupported saved input selection')
    if expected_revisions is not None and result['revisions'] != expected_revisions:
        raise ValueError('saved selection uses different geographic revisions')
    if 'water' in result['domains']:
        selected_basins(result['domains']['water'])
    return result
