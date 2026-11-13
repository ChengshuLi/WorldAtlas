"""Freeze working geographic decisions in one short, read-only transaction."""

from datetime import datetime, timezone
import json
from pathlib import Path

from worldatlas.map_build.inputs.features import affiliation_selection, selected_basins

HERE = Path(__file__).resolve().parent
DOMAINS = {'mainland', 'regional', 'water', 'ocean'}
QUERY = HERE / 'geography.sql'


def validate_bindings(domains):
    """Require every selected stage to give each map code the same meaning.

    Row order and descriptive metadata do not affect a binding. Registry
    revision names may differ when their entity/code meanings are identical.
    """
    expected = None
    for name, domain in domains.items():
        rows = domain.get('category_bindings')
        if not isinstance(rows, list):
            raise ValueError(f'{name} selection needs category bindings')
        bindings, entities = {}, set()
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError(f'{name} selection has an invalid category binding')
            code, entity, kind = (row.get(key) for key in ('code', 'entity_id', 'physical_class'))
            if (
                type(code) is not int
                or not 0 < code < 2**32
                or type(entity) is not int
                or entity <= 0
                or kind not in ('land', 'water')
                or code in bindings
                or (entity, kind) in entities
            ):
                raise ValueError(f'{name} selection has invalid or duplicate category bindings')
            bindings[code] = (entity, kind)
            entities.add((entity, kind))
        if expected is not None and bindings != expected:
            raise ValueError(f'{name} category bindings differ from {first}')
        if expected is None:
            first, expected = name, bindings


def canonical_bytes(value):
    return (
        json.dumps(
            value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False
        )
        + '\n'
    ).encode()


def read_selection(database, revisions, *, raw_sources=(), documents=()):
    """Return the selected domains, catalogs and colors, then end the transaction.

    Call with an idle connection. Computation and downloads happen after this
    function returns. Resume reads the saved result instead of querying again.
    """
    if (
        not revisions
        or set(revisions) - DOMAINS
        or any(not isinstance(value, str) or not value.strip() for value in revisions.values())
    ):
        raise ValueError('select named mainland, regional, water or ocean revisions')
    result = {
        'schema': 'worldatlas-input-selection-v2',
        'revisions': revisions,
        'selected_at': datetime.now(timezone.utc).isoformat(),
        'domains': {},
    }
    with database.transaction():
        database.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        references = set(raw_sources)
        document_refs = set(documents)
        registries = set()
        for domain, revision in revisions.items():
            row = database.execute(QUERY.read_text(), {'revision': revision}).fetchone()
            data = json.loads(row[0]) if row else {}
            features = {feature['feature_id']: feature for feature in data.get('features', [])}
            # Geometry can be large. Read records directly instead of asking
            # PostgreSQL to construct one enormous JSON aggregate in memory.
            with database.cursor(name='selected_features_' + domain) as cursor:
                cursor.execute(
                    'SELECT feature_id,geometry::text FROM atlas.decision_features '
                    'WHERE revision=%s AND geometry IS NOT NULL ORDER BY feature_id',
                    (revision,),
                )
                for feature_id, geometry in cursor:
                    features[feature_id]['geometry'] = json.loads(geometry)
            identity = data.get('decision_revision') or {}
            if identity.get('id') != revision:
                raise ValueError('selected geographic revision is missing: ' + revision)
            if domain == 'water':
                selected_basins(data)
            validate_feature_references(data)
            result['domains'][domain] = data
            for key in ('features', 'mainland_boundaries', 'endpoints', 'routes'):
                document_refs.update(
                    (item['construction_id'], item['construction_version'])
                    for item in data.get(key, []) if item.get('construction_id') is not None
                )
            registries.add(identity['entity_revision'])
            references.update(
                (source['source_id'], source['version']) for source in data['sources']
            )
        validate_bindings(result['domains'])
        if 'regional' in revisions:
            rows = database.execute(
                'SELECT rule_set_id,line_id,definition FROM atlas.regional_island_rule_sets '
                'WHERE revision=%s AND enabled ORDER BY rule_set_id',
                (revisions['regional'],),
            ).fetchall()
            result['regional_partitions'] = []
            for rule_set_id, line_id, definition in rows:
                line = database.execute(
                    "SELECT to_jsonb(l)-'created_at' FROM atlas.geographic_line_observations l WHERE line_id=%s",
                    (line_id,),
                ).fetchone()
                if line is None:
                    raise ValueError('selected geographic line is missing')
                result['regional_partitions'].append(
                    {'rule_set_id': rule_set_id, 'line': line[0], 'policy': definition}
                )
                references.add((line[0]['source_id'], line[0]['source_version']))
                if line[0].get('construction_id') is not None:
                    document_refs.add((line[0]['construction_id'], line[0]['construction_version']))
                references.update(
                    (source['source_id'], source['version'])
                    for source in definition.get('sources', [])
                )
        requested = sorted(references)
        rows = database.execute(
            "SELECT to_jsonb(a)-'created_at' FROM atlas.source_assets a "
            'WHERE (source_id,version) IN (SELECT * FROM unnest(%s::text[],%s::text[])) '
            'ORDER BY source_id,version',
            ([key[0] for key in requested], [key[1] for key in requested]),
        ).fetchall()
        result['raw_sources'] = [row[0] for row in rows]
        missing = references - {(row['source_id'], row['version']) for row in result['raw_sources']}
        if missing:
            raise ValueError('selected raw source is missing: ' + str(sorted(missing)))
        requested_documents = sorted(document_refs)
        rows = database.execute(
            'SELECT source_id,version,document '
            'FROM atlas.structured_documents WHERE (source_id,version) IN '
            '(SELECT * FROM unnest(%s::text[],%s::text[])) ORDER BY source_id,version',
            ([key[0] for key in requested_documents], [key[1] for key in requested_documents]),
        ).fetchall()
        missing = document_refs - {(row[0], row[1]) for row in rows}
        if missing:
            raise ValueError('selected document is missing: ' + str(sorted(missing)))
        result['documents'] = [dict(source_id=source_id, version=version, document=document)
                               for source_id, version, document in rows]
        rows = database.execute(
            'SELECT e.revision,jsonb_agg(jsonb_build_object('
            "'entity_id',e.id,'color_rgb',i.color_rgb) ORDER BY e.id) "
            'FROM atlas.geographic_entities e JOIN atlas.geographic_entity_ids i USING(id) '
            'WHERE e.revision=ANY(%s) GROUP BY e.revision ORDER BY e.revision',
            (sorted(registries),),
        ).fetchall()
        result['registry_colors'] = dict(rows)
    return result


def validate_feature_references(domain):
    """Check every executable affiliation reference before lengthy processing."""
    features = {feature['feature_id'] for feature in domain.get('features', [])}
    for rule in domain.get('affiliations', []):
        affiliation_selection(rule, features)


def read_saved(path, expected_revisions=None):
    result = json.loads(Path(path).read_bytes())
    if result.get('schema') not in ('worldatlas-input-selection-v1', 'worldatlas-input-selection-v2'):
        raise ValueError('unsupported saved input selection')
    if expected_revisions is not None and result['revisions'] != expected_revisions:
        raise ValueError('saved selection uses different geographic revisions')
    validate_bindings(result['domains'])
    for domain in result['domains'].values():
        validate_feature_references(domain)
    if 'water' in result['domains']:
        selected_basins(result['domains']['water'])
    return result
