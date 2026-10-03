#!/usr/bin/env python3
"""Fail-closed whole-scope checks for issue #594; no writes outside this packet."""
import gzip
import hashlib
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PARENT = ROOT / 'data/regional-review/regional-review-2d6fa291e9384c2f'

def load(path):
    return json.loads(path.read_text())

def digest(data):
    return hashlib.sha256(data).hexdigest()

def check(ok, message):
    if not ok:
        raise SystemExit('FAIL: ' + message)

scope = load(HERE / 'scope.json')
check(scope['issue'] == 594 and scope['assigned_count'] == 9, 'issue scope/count mismatch')
check(len(set(scope['assigned_ids'])) == 9, 'assigned IDs must be unique')
check(scope['baseline_commit'] == 'f004b8b59bd64353826f952e90f6741d42380b6a', 'unexpected pinned main baseline')
check(scope['owned_paths'] == ['data/regional-review/regional-supplement-bolivia-ecoregion-roles-2026/'], 'ownership differs from actual issue declaration')
for item in scope['inputs']:
    path = ROOT / item['path']
    check(path.is_file(), f"missing pinned input {item['path']}")
    raw = path.read_bytes()
    check(len(raw) == item['bytes'] and digest(raw) == item['sha256'], f"pinned input changed: {item['path']}")

# The parent verifier checks its entire 211-ID scope and retained source archive, read-only.
parent_check = subprocess.run(['python3', str(PARENT / 'verify.py')], check=True, capture_output=True, text=True)
check(parent_check.stdout.startswith('PASS: 211/211 IDs'), 'parent source/scope validation failed')

issue = load(HERE / 'issue-594-snapshot.json')
check(issue['number'] == 594 and issue['state'] == 'open', 'issue snapshot is not the actual open work item')
body = issue['body']
for sid in scope['assigned_ids']:
    check(body.count(sid) == 1, f'assigned subject is absent/duplicated in issue: {sid}')

idx = load(ROOT / 'data/world-index.json')
check('geography/part-2.json' in idx['parts'], 'pinned feature container is not indexed')
fc = load(ROOT / 'data/geography/part-2.json')
features = {f['properties']['id']: f for f in fc['features'] if f['properties'].get('id') in scope['assigned_ids']}
check(set(features) == set(scope['assigned_ids']), 'not every assigned ID was found in current indexed geography')
parent_assessment = load(PARENT / 'assessment.json')
parent_rows = {r['location_id']: r for r in parent_assessment['locations']}
check(set(scope['assigned_ids']) <= set(parent_rows), 'parent evidence does not cover all assigned subjects')
hierarchy = {row['id']: row for row in load(ROOT / 'data/hierarchy.json')}
expected_parent_chain = [
    'framework:province:santa-cruz:ee00377a6395',
    'framework:area:bolivia:590653070fd8',
    'framework:region:western-south-america:7fe9d26228d5',
    'framework:subcontinent:andean-south-america:9579d3e91c2b',
    'framework:continent:south-america:bbda637e3435',
]
report = load(HERE / 'assessment.json')
rows = report['rows']
metrics = load(HERE / 'derived-portion-audit.json')
chain_names = []
for sid in scope['assigned_ids']:
    feature = features[sid]['properties']
    check(feature['parent_id'] == expected_parent_chain[0], f'current parent changed for {sid}')
    chain = []
    cur = hierarchy[feature['parent_id']]
    while True:
        chain.append(cur['id'])
        if cur.get('parent_id') is None:
            break
        check(cur['parent_id'] in hierarchy, f'broken hierarchy link for {sid}: {cur["parent_id"]}')
        cur = hierarchy[cur['parent_id']]
        check(len(chain) < 8, 'hierarchy cycle')
    check(chain == expected_parent_chain, f'incomplete or changed parent chain for {sid}: {chain}')
    row = parent_rows[sid]
    check([p['id'] for p in row['full_parent_chain']] == expected_parent_chain, f'parent evidence disagrees for {sid}')
    meta = feature.get('metadata', {})
    check(meta.get('source_id') == 'resolve:' + str(row['physical_source_identity']['eco_id']), f'ecoregion source mapping changed for {sid}')
    check(meta.get('original_id') == row['physical_source_identity']['admin_predecessor_id'].split(':')[-1], f'predecessor mapping changed for {sid}')
    check(meta.get('source_role') == 'Province', f'current role no longer matches recorded issue finding for {sid}')
    packet_row = next(x for x in rows if x['id'] == sid)
    check(packet_row['source_role_current'] == meta.get('source_role'), f'packet/current source role mismatch: {sid}')
    check(packet_row['administrative_level_current'] == meta.get('administrative_level'), f'packet/current administrative level mismatch: {sid}')
    check(packet_row['location_basis_current'] == meta.get('location_basis'), f'packet/current location basis mismatch: {sid}')
    check(packet_row['selection_reason_current'] == meta.get('selection_reason'), f'packet/current selection reason mismatch: {sid}')
    check(packet_row['current_geometry'] == {'type':row['current_atlas_geometry']['type'],'components':row['current_atlas_geometry']['components'],'rings':row['current_atlas_geometry']['rings'],'holes':row['current_atlas_geometry']['interior_rings'],'vertices':row['current_atlas_geometry']['vertices']}, f'current geometry summary mismatch: {sid}')
    check(packet_row['physical_land_screen']['representative_point_in_level1_land'] == row['physical_source_screen']['representative_point_in_level1_land'] and packet_row['physical_land_screen']['level1_centroid_hits'] == row['physical_source_screen']['level1_centroid_hits'], f'land-screen finding mismatch: {sid}')
    check(packet_row['settlements'].startswith('unresolved:'), f'packet settlement finding missing: {sid}')
    check(packet_row['remainders_islands_inland_water'].startswith('unresolved:'), f'packet remainder finding missing: {sid}')
    check('Named local administrative territories' in meta.get('selection_reason', ''), f'current administrative selection claim not found for {sid}')
    check(row['settlement_review'].startswith('unresolved:'), f'settlement status missing for {sid}')
    check(row['remainders_and_disconnected_land_review'].startswith('unresolved'), f'remainder/island/water status missing for {sid}')

check(report['issue'] == 594 and report['assigned_count'] == report['assessed_count'] == 9, 'assessment completeness counts differ')
check(len(rows) == 9 and {r['id'] for r in rows} == set(scope['assigned_ids']), 'assessment must contain each assigned subject once')
for r in rows:
    check(r['status'].startswith('correction_needed') and 'unresolved' in report['evidence_disposition'], f'unsupported finding/tier for {r["id"]}')
    check(r['parent_chain_ids'] == expected_parent_chain, f'packet parent chain incomplete for {r["id"]}')
    check(r['settlements'].startswith('unresolved:'), f'packet settlement disposition missing for {r["id"]}')

expected_ecos = {476, 504, 523, 529, 567, 569, 584}
actual_ecos = {r['resolve_eco_id'] for r in rows}
check(actual_ecos == expected_ecos, f'mapped ecoregion source IDs differ: {actual_ecos}')
check(sorted({f['eco_id'] for f in report['mapped_resolve_features']}) == sorted(expected_ecos), 'seven-feature source roster incomplete')
check(sorted(f['id'] for f in report['source_accounting']['predecessors']) == sorted('gb:BOL:ADM2:'+sid for sid in scope['predecessor_adm2_ids']), 'predecessor set differs')
check(report['source_accounting']['unaccounted_source_adm2_features'] == 0, 'predecessor source roster not fully accounted')

source_admin = json.loads(gzip.decompress((PARENT / 'sources/geoboundaries-BOL-ADM2-2015.geojson.gz').read_bytes()))
admin = {f['properties']['shapeID'] for f in source_admin['features']}
check(len(admin) == 110 and set(scope['predecessor_adm2_ids']) <= admin, 'complete two predecessor source polygons not present')
admin_by_id = {f['properties']['shapeID']: f['properties']['shapeName'] for f in source_admin['features']}
check(admin_by_id['80513517B19404624083023'] == 'Cordillera' and admin_by_id['80513517B10383084964738'] == 'Velasco', 'predecessor source names/IDs disagree')
resolve = json.loads(gzip.decompress((PARENT / 'sources/resolve-bolivia-ecoregions-7.geojson.gz').read_bytes()))
eco = {str(f['properties']['ECO_ID']): f for f in resolve['features']}
check(set(map(str, expected_ecos)) <= set(eco), 'a mapped RESOLVE feature is missing')
for r in rows:
    f = eco[str(r['resolve_eco_id'])]
    check(f['properties'].get('ECO_NAME') == r['resolve_eco_name'], f'ECO_ID/name mismatch for {r["id"]}')
    check(r['overlay'] == {k: next(x for x in metrics['fragments'] if x['location_id'] == r['id'])[k] for k in ('expected_intersection_area_km2_equal_area','current_area_km2_equal_area','overlap_area_km2_equal_area','expected_area_covered_by_current_fraction','current_area_inside_expected_fraction','symmetric_difference_area_km2_equal_area','raw_geometry_validity')}, f'overlay row mismatch: {r["id"]}')
for sid, feature in eco.items():
    if int(sid) in expected_ecos:
        check(feature['properties'].get('LICENSE') == 'CC-BY 4.0', f'feature license missing for ECO_ID {sid}')

parent_metrics = load(PARENT / 'derived-portion-audit.json')
check(metrics['fragment_count'] == 9, 'reproduced geometry audit is incomplete')
check(metrics['source_hashes'] == parent_metrics['source_hashes'], 'source archive hashes differ from parent audit')
check(metrics['parent_unions'] == parent_metrics['parent_unions'], 'predecessor union metrics differ from pinned parent audit')
check(metrics['neighbor_pair_graph_differences'] == parent_metrics['neighbor_pair_graph_differences'], 'fragment source/current neighbor graph changed')
check(len(metrics['fragment_pairs']) == 36, 'all 36 assigned-subject pairs must be checked')
check(not metrics['neighbor_pair_graph_differences']['expected_missing_current'] and not metrics['neighbor_pair_graph_differences']['current_missing_expected'], 'source/current internal fragment neighbor graph has a difference')

neighbors = load(PARENT / 'neighbor-screen-bolivia.json')
for r in rows:
    check(next(x for x in load(HERE / 'neighbor-reconciliation.json')['records'] if x['id'] == r['id'])['current_exact_segment_contacts'] == neighbors['per_location'][r['id']]['current_exact_segment_neighbors'], f'current neighbor screen mismatch: {r["id"]}')
print('PASS: issue #594 9/9 IDs, 2 predecessor polygons, 7 RESOLVE features, role findings, parent chains, whole-scope overlay and neighbors, retained source hashes and explicit unresolved physical/settlement limits')
