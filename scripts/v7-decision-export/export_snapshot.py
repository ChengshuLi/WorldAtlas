#!/usr/bin/env python3
"""Review prototype: read one locked build in a repeatable-read read-only transaction.

Requires psycopg 3, a trusted read-only database connection, and an independently
trusted build digest. This file neither accepts reviews nor changes database state.
Not production authority: see README.md.
"""
import argparse
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

HEX = re.compile(r'^[0-9a-f]{64}$')


def decimal_string(value):
    if not value.is_finite():
        raise ValueError('non-finite numeric value')
    s = format(value, 'f')
    if '.' in s:
        s = s.rstrip('0').rstrip('.')
    return '0' if Decimal(s) == 0 else s


def exact(value):
    """Encode JSON fractional numerics as exact normalized strings; keep ints."""
    if isinstance(value, Decimal):
        return decimal_string(value)
    if isinstance(value, float):
        raise ValueError('binary floats are forbidden')
    if isinstance(value, list):
        return [exact(v) for v in value]
    if isinstance(value, dict):
        return {k: exact(v) for k, v in value.items()}
    return value


def parse_json(value):
    # Force PostgreSQL jsonb::text through an exact decimal parser.
    return exact(json.loads(value, parse_float=Decimal,
                            parse_constant=lambda _: (_ for _ in ()).throw(ValueError('invalid number'))))


def canonical_bytes(data):
    return (json.dumps(exact(data), sort_keys=True, ensure_ascii=True,
                       separators=(',', ':'), allow_nan=False) + '\n').encode('ascii')


def query(cur, sql, params):
    cur.execute(sql, params)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, row)) for row in cur.fetchall()]


def one(rows, label):
    if len(rows) != 1:
        raise ValueError(f'{label} must identify exactly one record')
    return rows[0]


def must(condition, message):
    if not condition:
        raise ValueError(message)


def validate(doc):
    rev = doc['decision_revision']
    must(rev['status'] == 'accepted' and doc['entity_revision']['status'] == 'accepted'
         and rev['entity_revision'] == doc['entity_revision']['id'], 'revision mismatch or not accepted')
    sources = {(s['source_id'], s['version']): s for s in doc['sources']}
    must(len(sources) == len(doc['sources']) and bool(sources), 'source identities must be unique and nonempty')
    must(all(HEX.fullmatch(s['sha256']) for s in doc['sources']), 'invalid source digest')
    must(all((f['source_id'], f['source_version']) in sources and HEX.fullmatch(f['geometry_sha256'])
             for f in doc['features']), 'feature source not selected or invalid geometry digest')
    basins = doc['basins']; ids = [b['id'] for b in basins]
    must(bool(ids) and len(ids) == len(set(ids)), 'nonempty unique basin decisions required')
    bindings = doc['category_bindings']
    for basin in basins:
        participants = basin['participant_entity_ids']
        method = basin['assignment_method']
        must(method in ('single_continent_named_basin', 'shared_nearest_assigned_shore'), 'unsupported basin method')
        must((len(participants) == 1 if method == 'single_continent_named_basin' else len(participants) >= 2)
             and len(participants) == len(set(participants)), 'invalid basin participants')
        for entity in participants:
            found = [b for b in bindings if b['entity_id'] == entity and b['physical_class'] == 'water']
            must(len(found) == 1 and type(found[0]['code']) is int and found[0]['code'] in range(1, 7), 'invalid participant binding for v7')
    must(all((i['source_id'],i['version']) in sources for i in doc['source_inputs']), 'missing selected source')
    features = {f['feature_id']: f for f in doc['features']}
    must(len(features) == len(doc['features']), 'duplicate feature')
    for basin in basins:
        f = features.get(basin['feature_id'])
        must(f is not None and all(basin[k] == f[k] for k in ('source_id','source_version','source_feature_id','geometry_sha256')), 'basin feature mismatch')
    endpoint_ids = {x['endpoint_id'] for x in doc['endpoints']}
    must(len(endpoint_ids) == len(doc['endpoints']), 'duplicate endpoint')
    entity_ids = {x['id'] for x in doc['entities']}
    # IDs and references must exist even if a privileged writer bypassed constraints.
    must(all(b['entity_id'] in entity_ids for b in bindings), 'orphan binding')
    must(all(p in entity_ids for b in basins for p in b['participant_entity_ids']), 'orphan participant')
    must(all(a['feature_id'] in features and a['entity_id'] in entity_ids for a in doc['affiliations']), 'orphan affiliation')
    must(all(x['endpoint_id'] in endpoint_ids and x['entity_id'] in entity_ids for x in doc['ocean_seeds']), 'orphan seed')
    must(all(p['endpoint_id'] in endpoint_ids for r in doc['routes'] for p in r['points']), 'orphan route point')
    policies = doc['policies']
    must(len({p['id'] for p in policies}) == len(policies), 'duplicate policy identity')
    must(all(p['kind'] in ('layer_precedence', 'coastline_assignment', 'ocean_fill') for p in policies), 'unsupported policy kind')
    prec = one([p for p in policies if p['kind'] == 'layer_precedence'], 'layer precedence')
    coast = one([p for p in policies if p['kind'] == 'coastline_assignment'], 'coastline assignment')
    c = coast['definition']
    must(isinstance(c, dict) and (c.get('source_id'), c.get('source_version')) in sources and
         isinstance(c.get('method'), str) and bool(c['method'].strip()) and isinstance(c.get('parameters'), dict), 'invalid coastline policy')
    definition = prec['definition']; must(isinstance(definition, dict), 'invalid precedence')
    priorities = definition.get('priorities'); rules = definition.get('allowed_overrides')
    layers = {'coastal-band'} | {f'named-{i}' for i in ids}
    must(isinstance(priorities, dict) and set(priorities) == layers and
         all(type(v) is int for v in priorities.values()) and isinstance(rules, list), 'invalid precedence layers')
    seen = set()
    for rule in rules:
        must(isinstance(rule, dict) and set(rule) == {'winner', 'loser'}, 'invalid override')
        w, l = rule['winner'], rule['loser']
        must(isinstance(w, str) and isinstance(l, str) and w in priorities and l in priorities and
             priorities[w] > priorities[l] and (w, l) not in seen, 'invalid override')
        seen.add((w, l))
    oceans = [p for p in policies if p['kind'] == 'ocean_fill']
    must(len(oceans) <= 1, 'ambiguous ocean fill policy')
    if oceans:
        ocean = oceans[0]['definition']
        must(isinstance(ocean, dict) and ocean.get('connectivity') == 4 and type(ocean.get('connectivity')) is int
             and type(ocean.get('wrap_longitude')) is bool and ocean.get('barrier_tie_rule') == 'left-of-oriented-route'
             and ocean.get('unseeded_policy') == 'report-only', 'unsupported ocean fill policy')
        for name, collection, key in (('route_ids', doc['routes'], 'route_id'), ('seed_ids', doc['ocean_seeds'], 'seed_id')):
            ids_ = ocean.get(name)
            must(isinstance(ids_, list) and bool(ids_) and all(isinstance(x, str) for x in ids_)
                 and len(ids_) == len(set(ids_)) and set(ids_).issubset({x[key] for x in collection}), 'invalid ocean fill references')
        must(all(x['route_type'] in ('lonlat_polyline', 'meridian', 'wgs84_geodesic') for x in doc['routes'] if x['route_id'] in ocean['route_ids']), 'unsupported ocean route type')
    for route in doc['routes']:
        if route['route_type'] == 'wgs84_geodesic':
            versions = doc['build']['software_versions']
            must(isinstance(versions, dict) and all(isinstance(versions.get(k), str) and versions[k].strip() for k in ('pyproj', 'proj')), 'missing geodesic software pins')
            value = route['parameters'].get('max_step_km') if isinstance(route['parameters'], dict) else None
            must(type(value) in (int, str), 'invalid geodesic step')
            try:
                step = Decimal(value)
                must(step.is_finite() and 0 < step <= 1, 'invalid geodesic step')
            except (ArithmeticError, ValueError):
                raise ValueError('invalid geodesic step') from None
        points = route['points']; must(len(points) >= 2 and [p['ordinal'] for p in points] == list(range(len(points))), 'invalid route points')
    for name in ('physical_grid_sha256',):
        must(bool(HEX.fullmatch(doc['build'][name])), 'invalid grid hash')


def export(conn, build_id, expected_sha256=None, *, prepare_candidate=False):
    """Read a single MVCC snapshot, validate it, compare both trusted and DB pins.

    The connection must be fresh, with TLS and a least-privilege SELECT-only role.
    Caller is responsible for authenticating the server and the independent pin.
    """
    must(prepare_candidate or (isinstance(expected_sha256, str) and bool(HEX.fullmatch(expected_sha256))), 'trusted SHA-256 required')
    must(not prepare_candidate or expected_sha256 is None, 'candidate mode does not verify a pin')
    must(conn.autocommit is True, 'connection must use autocommit for an explicit read-only transaction')
    cur = conn.cursor()
    began = False
    try:
        cur.execute('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY')
        began = True
        b = one(query(cur, '''SELECT b.build_id,b.status,b.entity_revision,b.decision_revision,b.decision_snapshot_sha256,
 b.physical_grid_revision,b.physical_grid_sha256,b.code_revision,b.git_paths::text,b.software_versions::text,
 d.status AS decision_status,d.evidence::text AS decision_evidence,d.reviewed_by AS decision_reviewer,
 to_char(d.reviewed_at AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"') AS decision_reviewed_at,
 e.status AS entity_status,e.reviewed_by AS entity_reviewer,
 to_char(e.reviewed_at AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"') AS entity_reviewed_at
 FROM atlas.source_builds b JOIN atlas.decision_revisions d ON d.revision=b.decision_revision AND d.entity_revision=b.entity_revision
 JOIN atlas.entity_registry_revisions e ON e.revision=b.entity_revision WHERE b.build_id=%s''', (build_id,)), 'build')
        must(b['status'] == ('draft' if prepare_candidate else 'locked') and b['decision_status'] == 'accepted' and b['entity_status'] == 'accepted', 'build status or accepted revisions invalid')
        must(all(b[k] for k in ('decision_reviewer','decision_reviewed_at','entity_reviewer','entity_reviewed_at','physical_grid_revision','physical_grid_sha256','code_revision')), 'missing review or build pins')
        if not prepare_candidate:
            must(b['decision_snapshot_sha256'] == expected_sha256, 'database build pin differs from trusted pin')
        d, e = b['decision_revision'], b['entity_revision']
        sources = query(cur, '''SELECT DISTINCT a.source_id,a.version,a.sha256,a.size_bytes,a.r2_bucket,a.r2_key
 FROM atlas.source_build_inputs i JOIN atlas.source_assets a ON a.source_id=i.source_id AND a.version=i.version
 WHERE i.build_id=%s ORDER BY a.source_id,a.version''', (build_id,))
        inputs = query(cur, '''SELECT source_id,version,stage,role FROM atlas.source_build_inputs WHERE build_id=%s ORDER BY source_id,version,stage,role''', (build_id,))
        entities = query(cur, '''SELECT id,name,level,parent_id,physical_class FROM atlas.geographic_entities WHERE revision=%s ORDER BY id''', (e,))
        bindings = query(cur, '''SELECT code,entity_id,physical_class FROM atlas.review_category_bindings WHERE revision=%s ORDER BY code''', (e,))
        features = query(cur, '''SELECT feature_id,source_id,source_version,source_feature_id,geometry_sha256,evidence::text FROM atlas.decision_features WHERE revision=%s ORDER BY feature_id''', (d,))
        endpoints = query(cur, '''SELECT endpoint_id,name,longitude::text,latitude::text,derivation::text,evidence::text FROM atlas.decision_endpoints WHERE revision=%s ORDER BY endpoint_id''', (d,))
        routes = query(cur, '''SELECT route_id,route_type,parameters::text,evidence::text FROM atlas.decision_routes WHERE revision=%s ORDER BY route_id''', (d,))
        route_points = query(cur, '''SELECT route_id,ordinal,endpoint_id FROM atlas.decision_route_points WHERE revision=%s ORDER BY route_id,ordinal''', (d,))
        basins = query(cur, '''SELECT b.basin_id AS id,b.feature_id,f.source_id,f.source_version,f.source_feature_id,f.geometry_sha256,b.method AS assignment_method,b.tie_rules::text,b.evidence::text
 FROM atlas.decision_basins b LEFT JOIN atlas.decision_features f ON f.revision=b.revision AND f.feature_id=b.feature_id
 WHERE b.revision=%s ORDER BY b.basin_id''', (d,))
        parts = query(cur, '''SELECT basin_id,entity_id FROM atlas.decision_basin_participants WHERE revision=%s ORDER BY basin_id,entity_id''', (d,))
        affiliations = query(cur, '''SELECT affiliation_id,feature_id,entity_id,relationship,scope,method,rationale,evidence::text FROM atlas.decision_affiliations WHERE revision=%s ORDER BY affiliation_id''', (d,))
        seeds = query(cur, '''SELECT seed_id,endpoint_id,entity_id,evidence::text FROM atlas.decision_ocean_seeds WHERE revision=%s ORDER BY seed_id''', (d,))
        policies = query(cur, '''SELECT policy_id AS id,kind,definition::text,evidence::text FROM atlas.decision_policies WHERE revision=%s ORDER BY policy_id''', (d,))
        ocean_policies = query(cur, """SELECT policy_id AS id,'ocean_fill' AS kind,definition::text,evidence::text FROM atlas.decision_ocean_fill_policies WHERE revision=%s ORDER BY policy_id""", (d,))
        policies += ocean_policies
        # Do not rely on the database's locale-dependent text ordering.
        for rows, keys in ((sources,('source_id','version')), (inputs,('source_id','version','stage','role')),
                           (entities,('id',)), (bindings,('code',)), (features,('feature_id',)),
                           (endpoints,('endpoint_id',)), (routes,('route_id',)), (route_points,('route_id','ordinal')),
                           (basins,('id',)), (parts,('basin_id','entity_id')), (affiliations,('affiliation_id',)),
                           (seeds,('seed_id',)), (policies,('id',))):
            rows.sort(key=lambda row: tuple(row[k] for k in keys))
        for rows, fields in ((features,['evidence']), (endpoints,['derivation','evidence']), (routes,['parameters','evidence']), (basins,['tie_rules','evidence']), (affiliations,['evidence']), (seeds,['evidence']), (policies,['definition','evidence'])):
            for row in rows:
                for field in fields: row[field] = parse_json(row[field])
        for endpoint in endpoints:
            for field in ('longitude', 'latitude'): endpoint[field] = decimal_string(Decimal(endpoint[field]))
        must(all(x['route_id'] in {r['route_id'] for r in routes} for x in route_points), 'orphan route points')
        must(all(x['basin_id'] in {r['id'] for r in basins} for x in parts), 'orphan basin participants')
        for route in routes: route['points'] = [{k:v for k,v in x.items() if k != 'route_id'} for x in route_points if x['route_id'] == route['route_id']]
        for basin in basins: basin['participant_entity_ids'] = [x['entity_id'] for x in parts if x['basin_id'] == basin['id']]
        doc = {'schema':'worldatlas-geography-decision-export-v1','serialization':'worldatlas-canonical-json-v1','source':'neon-export',
               'decision_revision':{'id':d,'status':b['decision_status'],'entity_revision':e,'reviewed_by':b['decision_reviewer'],'reviewed_at':b['decision_reviewed_at'],'evidence':parse_json(b['decision_evidence'])},
               'entity_revision':{'id':e,'status':b['entity_status'],'reviewed_by':b['entity_reviewer'],'reviewed_at':b['entity_reviewed_at']},
               'build':{'id':build_id,'physical_grid_revision':b['physical_grid_revision'],'physical_grid_sha256':b['physical_grid_sha256'],
                        'code_revision':b['code_revision'],'git_paths':parse_json(b['git_paths']),'software_versions':parse_json(b['software_versions'])},
               'sources':sources,'source_inputs':inputs,'entities':entities,'category_bindings':bindings,'features':features,
               'endpoints':endpoints,'routes':routes,'basins':basins,'affiliations':affiliations,'ocean_seeds':seeds,'policies':policies}
        validate(doc)
        payload = canonical_bytes(doc)
        if not prepare_candidate:
            must(hashlib.sha256(payload).hexdigest() == expected_sha256, 'canonical snapshot digest mismatch')
        return payload
    finally:
        try:
            if began:
                cur.execute('ROLLBACK')  # No database writes or commit.
        finally:
            cur.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--build-id', required=True)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--expected-sha256', help='independently trusted digest for a locked build')
    mode.add_argument('--prepare-candidate', action='store_true', help='compute an unverified digest for an accepted revision and draft build')
    ap.add_argument('--out', required=True, type=Path)
    args = ap.parse_args()
    # libpq reads standard connection variables; never print or persist credentials.
    import psycopg
    with psycopg.connect(autocommit=True, sslmode='verify-full') as conn:
        payload = export(conn, args.build_id, args.expected_sha256, prepare_candidate=args.prepare_candidate)
    with args.out.open('xb') as f: f.write(payload)
    label = 'UNVERIFIED candidate' if args.prepare_candidate else 'Verified snapshot'
    print(f'{label}: {hashlib.sha256(payload).hexdigest()}')

if __name__ == '__main__': main()
