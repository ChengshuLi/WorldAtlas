#!/usr/bin/env python3
"""Reproduce issue #917's pinned-source and Atlas geometry lineage ledger.

Read-only over the issue snapshot, #449 originals, and baseline geography parts;
all outputs are confined to this issue's declared owned directory.
"""
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
ISSUE = json.loads((ROOT / 'source/issue-contract-917.json').read_text())
matches = list(re.finditer(r'<!-- worldatlas-work:v1\s*\n([\s\S]*?)\n-->', ISSUE['body']))
assert len(matches) == 1
SPEC = json.loads(matches[0].group(1))
QUALITY = SPEC['evidence_quality']
IDS = QUALITY['subject_ids']
assert len(IDS) == 228
assert QUALITY['manifest_path'] == 'data/regional-review/southwest-china-adm2-lineage-449/evidence-quality.json'
scope_digest = hashlib.sha256(json.dumps(sorted(IDS), separators=(',', ':')).encode()).hexdigest()

def assert_exact_scope(actual, expected):
    if len(actual) != len(set(actual)) or len(expected) != len(set(expected)):
        raise ValueError('duplicate expected subject or feature identity')
    if set(actual) != set(expected):
        raise ValueError('missing or foreign subject identity')

def run_scope_controls():
    method_id = 'scope-and-source-lineage'
    assert_exact_scope(['a', 'b'], ['a', 'b'])
    checks = ['positive exact-coverage fixture accepted']
    for actual, expected, label in [
        (['a', 'a'], ['a', 'b'], 'duplicate scope fixture'),
        (['a', 'b'], ['a', 'a'], 'duplicate expected-subject fixture'),
        (['a'], ['a', 'b'], 'missing subject fixture'),
        (['a', 'b', 'c'], ['a', 'b'], 'foreign subject fixture'),
    ]:
        try:
            assert_exact_scope(actual, expected)
        except ValueError:
            checks.append(f'{label} rejected')
        else:
            raise AssertionError(f'{label} was accepted')
    positive = {'method_id': method_id, 'kind': 'positive-control', 'outcome': 'passed', 'checks': checks}
    negative = {'method_id': method_id, 'kind': 'negative-control', 'outcome': 'passed', 'checks': checks[1:]}
    return positive, negative

assert_exact_scope(IDS, IDS)

if '--self-test' in __import__('sys').argv:
    positive, negative = run_scope_controls()
    (ROOT / 'findings/scope-control-positive.json').write_text(json.dumps(positive, indent=2) + '\n')
    (ROOT / 'findings/scope-control-negative.json').write_text(json.dumps(negative, indent=2) + '\n')
    print(json.dumps({'positive': positive, 'negative': negative}, indent=2))
    raise SystemExit(0)

def read_json(path):
    return json.loads(path.read_text())

atlas = {}
atlas_file = {}
for rel in ('data/geography/part-3.json', 'data/geography/part-4.json'):
    for feature in read_json(REPO / rel)['features']:
        ident = feature.get('id') or feature['properties'].get('id')
        if ident in IDS:
            assert ident not in atlas
            atlas[ident] = feature
            atlas_file[ident] = rel
assert_exact_scope(list(atlas), IDS)

source_path = REPO / 'data/regional-review/regional-review-365cbd6478904888/source/geoBoundaries-CHN-ADM2.geojson'
source_doc = read_json(source_path)
meta = read_json(source_path.with_name('geoBoundaries-CHN-ADM2-metaData.json'))
source_by_shape = {f['properties']['shapeID']: f for f in source_doc['features']}
assert len(source_by_shape) == len(source_doc['features']) == 2391
assert meta['boundaryID'] == 'CHN-ADM2-17275852' and meta['boundaryYear'] == '2017'

def vertices(value):
    if isinstance(value, list) and len(value) >= 2 and all(isinstance(x, (float, int)) for x in value[:2]):
        return 1
    return sum(vertices(x) for x in value) if isinstance(value, list) else 0

def round4(value):
    if isinstance(value, dict): return {k: round4(v) for k, v in value.items()}
    if isinstance(value, list): return [round4(v) for v in value]
    if isinstance(value, float): return round(value, 4)
    return value

def coords(value):
    if isinstance(value, list) and len(value) >= 2 and all(isinstance(x, (int, float)) for x in value[:2]):
        return [value]
    if isinstance(value, list):
        return sum((coords(x) for x in value), [])
    return []

rows = []
for ident in sorted(IDS):
    f = atlas[ident]
    p = f['properties']
    original_id = p['metadata']['original_id']
    sf = source_by_shape[original_id]
    sp = sf['properties']
    source_count = vertices(sf['geometry']['coordinates'])
    atlas_count = vertices(f['geometry']['coordinates'])
    source_coords = Counter(tuple(x) for x in coords(round4(sf['geometry']['coordinates'])))
    atlas_coords = Counter(tuple(x) for x in coords(f['geometry']['coordinates']))
    retained = sum((source_coords & atlas_coords).values())
    rows.append({
        'atlas_id': ident,
        'atlas_part': atlas_file[ident],
        'atlas_name': p['name'],
        'atlas_parent_id': p['parent_id'],
        'atlas_parent_source': p['metadata'].get('hierarchy_source'),
        'atlas_parent_method_claim': p['metadata'].get('parent_match'),
        '2017_source_shape_id': original_id,
        '2017_source_name': sp['shapeName'],
        '2017_source_type': sp['shapeType'],
        'name_exact_match': sp['shapeName'] == p['name'],
        'source_geometry_type': sf['geometry']['type'],
        'atlas_geometry_type': f['geometry']['type'],
        'source_ring_count_including_exterior': len(sf['geometry']['coordinates']),
        'atlas_ring_count_including_exterior': len(f['geometry']['coordinates']),
        'source_vertices': source_count,
        'atlas_vertices': atlas_count,
        'vertex_delta_source_minus_atlas': source_count - atlas_count,
        'round_source_to_4dp_equals_atlas': round4(sf['geometry']) == f['geometry'],
        'atlas_vertex_multiset_found_in_source_rounded_4dp': retained,
        'atlas_vertex_multiset_total': sum(atlas_coords.values()),
        'rounded_vertex_retention_fraction': (f'{retained}/{sum(atlas_coords.values())}' if atlas_coords else '0/0'),
        'transformation_origin': 'unresolved: no pinned transformation recipe or original generator identified',
        'current_legal_identity_parent_completeness_boundary': 'unresolved: official current row and authoritative current polygon source not retained/verified',
        'territory_islands_coastline_neighbors_boundary_role': 'unresolved: no suitable authoritative current geometry comparison',
    })

with (ROOT / 'findings/feature-lineage.csv').open('w', newline='') as out:
    writer = csv.DictWriter(out, fieldnames=list(rows[0]), lineterminator='\n')
    writer.writeheader(); writer.writerows(rows)

precision_matches = {}
for dp in range(0, 9):
    def rounded(value):
        if isinstance(value, dict): return {k: rounded(v) for k, v in value.items()}
        if isinstance(value, list): return [rounded(v) for v in value]
        if isinstance(value, float): return round(value, dp)
        return value
    precision_matches[str(dp)] = sum(rounded(source_by_shape[atlas[i]['properties']['metadata']['original_id']]['geometry']) == atlas[i]['geometry'] for i in IDS)

summary = {
    'issue': 917,
    'issue_snapshot_retrieved_at': ISSUE['updated_at'],
    'evaluation_commit': __import__('subprocess').check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], text=True).strip(),
    'subject_count': len(IDS),
    'subject_ids_sorted_json_sha256': scope_digest,
    'area_counts': {'Chongqing': 33, 'Guizhou': 82, 'Sichuan': 113},
    'source': {'boundaryID': meta.get('boundaryID'), 'boundaryYear': meta.get('boundaryYear'), 'boundaryType': meta.get('boundaryType'), 'boundaryCanonical': meta.get('boundaryCanonical'), 'admUnitCount': len(source_doc['features']), 'source_sha256': hashlib.sha256(source_path.read_bytes()).hexdigest(), 'metadata_sha256': hashlib.sha256(source_path.with_name('geoBoundaries-CHN-ADM2-metaData.json').read_bytes()).hexdigest()},
    'matched_unique_source_shapes': len({r['2017_source_shape_id'] for r in rows}),
    'source_name_matches': sum(r['name_exact_match'] for r in rows),
    'source_type_counts': dict(Counter(r['2017_source_type'] for r in rows)),
    'geometry_type_pairs': dict(Counter(f"{r['source_geometry_type']}->{r['atlas_geometry_type']}" for r in rows)),
    'source_vertices_total': sum(r['source_vertices'] for r in rows),
    'atlas_vertices_total': sum(r['atlas_vertices'] for r in rows),
    'net_vertex_reduction': sum(r['vertex_delta_source_minus_atlas'] for r in rows),
    'rows_with_fewer_atlas_vertices': sum(r['vertex_delta_source_minus_atlas'] > 0 for r in rows),
    'rows_matching_after_source_rounding_to_4dp': sum(r['round_source_to_4dp_equals_atlas'] for r in rows),
    'rounding_precision_match_counts': precision_matches,
    'all_per_feature_transform_origins': 'unresolved; individual counts and IDs are in feature-lineage.csv',
    'current_official_row_crosswalk': 'unresolved for all 228; official web discovery snippets are not originals or row evidence',
    'current_legal_boundary_and_completeness': 'unresolved for all 228; no retained suitable authoritative current polygon source',
    'adjacent_granularity': 'pinned source labels each of the 228 as ADM2 / County Level; this historical label is not current legal identity proof',
    'parent_evidence': 'all Atlas parent fields separately cite gbHumanitarian/HDX China ADM2 2020 greatest-overlap matching; the 2017 gbOpen source carries no parent code; current parents remain unresolved',
}
(ROOT / 'findings/reproduction-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(summary, ensure_ascii=False, indent=2))
