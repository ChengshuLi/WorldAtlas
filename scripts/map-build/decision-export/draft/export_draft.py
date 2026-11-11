#!/usr/bin/env python3
"""Export draft evidence, never an accepted revision or a build authorization.

Use a TLS-verified, least-privilege SELECT-only Postgres connection. No data is
written to the database. R2 bytes and the authority of decisions are not verified.
"""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
HEX = re.compile(r'^[0-9a-f]{64}$')
SCHEMA = 'worldatlas-geography-decision-draft-evidence-v1'


def exact(value):
    if isinstance(value, Decimal):
        if not value.is_finite(): raise ValueError('non-finite numeric value')
        text = format(value, 'f')
        if '.' in text: text = text.rstrip('0').rstrip('.')
        return '0' if value == 0 else text
    if isinstance(value, float): raise ValueError('binary floats are forbidden')
    if isinstance(value, list): return [exact(x) for x in value]
    if isinstance(value, dict): return {k: exact(v) for k, v in value.items()}
    return value


def canonical_bytes(doc):
    return (json.dumps(exact(doc), sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False)+'\n').encode('ascii')


def parse_snapshot(raw):
    doc = json.loads(raw, parse_float=Decimal, parse_constant=lambda x: (_ for _ in ()).throw(ValueError('invalid number')))
    if doc.get('schema') != SCHEMA or doc.get('source') != 'neon-export': raise ValueError('invalid draft export schema')
    d, e = doc.get('decision_revision'), doc.get('entity_revision')
    if not isinstance(d, dict) or not isinstance(e, dict) or d.get('status') != 'draft' or e.get('status') != 'draft' or d.get('entity_revision') != e.get('id') or not d.get('id'):
        raise ValueError('only matching draft decision and entity revisions can be exported')
    # Defensive referential checks do not claim completeness or geographic validity.
    def unique(rows, fields):
        keys = [tuple(row[k] for k in fields) for row in rows]
        if len(keys) != len(set(keys)): raise ValueError('duplicate ' + '/'.join(fields))
        return set(keys)
    features = doc['features']; sources = doc['sources']; assets = doc['source_lineage_assets']
    fk = unique(features, ('feature_id',)); sk = unique(sources, ('source_id','version')); ak = unique(assets, ('source_id','version'))
    if not sk.issubset(ak): raise ValueError('missing source lineage')
    by_asset = {(a['source_id'],a['version']): a for a in assets}
    if any(any(s[k] != by_asset[(s['source_id'],s['version'])][k] for k in ('sha256','size_bytes','r2_bucket','r2_key')) for s in sources): raise ValueError('source lineage mismatch')
    if any(not HEX.fullmatch(s['sha256']) for s in assets): raise ValueError('invalid source digest')
    source_by_id = {(s['source_id'], s['version']): s for s in sources}
    for record in doc['endpoints'] + doc['routes']:
        for ref in record.get('evidence', {}).get('source_refs', []):
            source = source_by_id.get((ref['source_id'], ref['version']))
            if source is None or ('sha256' in ref and ref['sha256'] != source['sha256']):
                raise ValueError('invalid route or endpoint source reference')
    if any((f['source_id'],f['source_version']) not in sk or not HEX.fullmatch(f['geometry_sha256']) for f in features): raise ValueError('invalid feature source')
    feature_by_id = {f['feature_id']: f for f in features}
    entity_ids = {row['id'] for row in doc['entities']}; unique(doc['entities'], ('id',)); unique(doc['category_bindings'], ('code',))
    if any(x['entity_id'] not in entity_ids for x in doc['category_bindings']): raise ValueError('orphan category binding')
    unique(doc['basins'], ('id',)); unique(doc['affiliations'], ('affiliation_id',)); unique(doc['ocean_seeds'], ('seed_id',)); unique(doc['policies'], ('id',))
    if any(p.get('kind') in ('coastline_assignment','closed_water_assignment','ocean_fill') and (not isinstance(p.get('evidence'),dict) or p['evidence'].get('execution_status') not in ('selected_for_research','research_only_not_selected')) for p in doc['policies']): raise ValueError('invalid draft water policy selection')
    for basin in doc['basins']:
        f = feature_by_id.get(basin['feature_id'])
        if f is None or any(basin[k] != f[k] for k in ('source_id','source_version','source_feature_id','geometry_sha256')) or not set(basin['participant_entity_ids']).issubset(entity_ids): raise ValueError('invalid basin reference')
    if any((a['feature_id'],) not in fk or a['entity_id'] not in entity_ids for a in doc['affiliations']): raise ValueError('orphan affiliation')
    if any(a.get('scope') == 'land' and (not isinstance(a.get('evidence'),dict) or a['evidence'].get('execution_status') not in ('selected_for_research','research_only_not_selected')) for a in doc['affiliations']): raise ValueError('invalid draft land affiliation selection')
    unique(doc['land_component_witness_rules'], ('rule_id',))
    if any(w['entity_id'] not in entity_ids or w['method'] != 'component_witness_list_v1' or not isinstance(w['selector'], dict) or not isinstance(w['evidence'], dict) or w['evidence'].get('execution_status') not in ('selected_for_research','research_only_not_selected') for w in doc['land_component_witness_rules']): raise ValueError('invalid land witness rule')
    endpoints = {x['endpoint_id'] for x in doc['endpoints']}; unique(doc['endpoints'], ('endpoint_id',)); unique(doc['routes'], ('route_id',))
    if any(p['endpoint_id'] not in endpoints for r in doc['routes'] for p in r['points']): raise ValueError('orphan route point')
    if any(s['endpoint_id'] not in endpoints or s['entity_id'] not in entity_ids for s in doc['ocean_seeds']): raise ValueError('orphan ocean seed')
    parents = {a: set() for a in ak}
    unique(doc['source_lineage_dependencies'], ('source_id','version','parent_source_id','parent_version'))
    for dep in doc['source_lineage_dependencies']:
        child = dep['source_id'], dep['version']; parent = dep['parent_source_id'], dep['parent_version']
        if child not in ak or parent not in ak or child == parent: raise ValueError('orphan or self-referential source dependency')
        parents[child].add(parent)
    active, visited = set(), set()
    def visit(node):
        if node in active: raise ValueError('source dependency cycle')
        if node in visited: return
        active.add(node)
        for parent in parents[node]: visit(parent)
        active.remove(node); visited.add(node)
    for source in sk: visit(source)
    if visited != ak: raise ValueError('unreachable source lineage')
    for endpoint in doc['endpoints']:
        for field in ('longitude','latitude'):
            value = endpoint[field]
            if type(value) not in (int, Decimal, str): raise ValueError('invalid endpoint coordinate')
            try:
                number = Decimal(value)
                if not number.is_finite() or abs(number) > (180 if field == 'longitude' else 90): raise ValueError('invalid endpoint coordinate')
                endpoint[field] = exact(number)
            except ArithmeticError:
                raise ValueError('invalid endpoint coordinate') from None
    # Sort outside the server locale so a repeated equivalent export is stable.
    for key, fields in (('sources',('source_id','version')),('source_lineage_assets',('source_id','version')),
        ('source_lineage_dependencies',('source_id','version','parent_source_id','parent_version')),
        ('entities',('id',)),('category_bindings',('code',)),('features',('feature_id',)),
        ('endpoints',('endpoint_id',)),('routes',('route_id',)),('basins',('id',)),
        ('affiliations',('affiliation_id',)),('land_component_witness_rules',('rule_id',)),('ocean_seeds',('seed_id',)),('policies',('id',))):
        doc[key].sort(key=lambda row: tuple(row[k] for k in fields))
    for route in doc['routes']: route['points'].sort(key=lambda point: point['ordinal'])
    for basin in doc['basins']: basin['participant_entity_ids'].sort()
    return exact(doc)


def export(conn, revision):
    if conn.autocommit is not True: raise ValueError('autocommit required')
    if not revision or not revision.strip(): raise ValueError('revision required')
    cur = conn.cursor(); began = False
    try:
        cur.execute('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY'); began = True
        cur.execute((HERE/'query.sql').read_text(), {'revision': revision})
        rows = cur.fetchall()
        if len(rows) != 1: raise ValueError('expected one snapshot')
        doc = parse_snapshot(rows[0][0])
        if doc['decision_revision']['id'] != revision: raise ValueError('wrong revision')
        return canonical_bytes(doc)
    finally:
        try:
            if began: cur.execute('ROLLBACK')
        finally: cur.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--revision', required=True); ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    import psycopg
    with psycopg.connect(autocommit=True, sslmode='verify-full') as conn: payload = export(conn, args.revision)
    with args.out.open('xb') as f: f.write(payload)
    print('DRAFT EVIDENCE ONLY; not authorized for publication. SHA-256:', hashlib.sha256(payload).hexdigest())

if __name__ == '__main__': main()
