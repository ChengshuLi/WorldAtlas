#!/usr/bin/env python3
"""Fail-closed integrity and exhaustive-scope checks for issue #490 evidence."""
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def load(name):
    return json.loads((ROOT / name).read_text())

def digest(data):
    return hashlib.sha256(data).hexdigest()

def check(condition, message):
    if not condition:
        raise SystemExit(f"FAIL: {message}")

scope = load('scope.json')
assessment = load('assessment.json')
ids = scope['member_location_ids']
rows = assessment['locations']
row_ids = [r['location_id'] for r in rows]
check(len(ids) == 211 and len(set(ids)) == 211, 'scope must contain 211 unique IDs')
check(set(row_ids) == set(ids) and len(row_ids) == 211, 'assessment does not account for each exact scope ID once')
check(scope['location_count'] == 211, 'scope count mismatch')
check(len(scope['province_scopes']) == 11, 'province/dept cohort count mismatch')
check(sum(x['owned_member_location_count'] for x in scope['area_scopes']) == 211, 'area membership total mismatch')
check(all(r['full_parent_chain'] and r['full_parent_chain'][-1]['level'] == 'continent' for r in rows), 'incomplete ancestry chain')
check(all(r['settlement_review'].startswith('unresolved:') for r in rows), 'settlement evidence disposition missing')
check(all(r['remainders_and_disconnected_land_review'].startswith('unresolved') for r in rows), 'remainder/disconnected-land disposition missing')
check(all(r['political_historical_distinction'] for r in rows), 'political/historical distinction missing')
counts = Counter(r['decision'] for r in rows)
check(counts == {'insufficient_evidence': 202, 'correction_needed': 9}, f'unexpected decisions {counts}')
check(sum(r['location_id'].startswith('atlas:physical:') for r in rows) == 9, 'physical fragment identity crosswalk incomplete')
check(all('inconsistent' in r['source_role_metadata_review']['finding'] for r in rows if r['location_id'].startswith('atlas:physical:')), 'physical source-role discrepancy not recorded for every fragment')

accounting = assessment['source_accounting']
check(accounting['bolivia_ADM2_source_units'] == 110 and accounting['bolivia_direct_admin_location_matches'] == 108, 'Bolivia ADM2 accounting mismatch')
check(accounting['bolivia_original_admin_units_represented_as_physical_fragments'] == 2 and accounting['bolivia_fragment_count'] == 9 and accounting['bolivia_unaccounted_ADM2_source_units'] == 0, 'Bolivia predecessor accounting mismatch')
check(accounting['bolivia_ADM3_source_units'] == 339 and accounting['colombia_whole_ADM2_source_units'] == 1122 and accounting['colombia_assigned_direct_location_matches'] == 94, 'secondary source cohort accounting mismatch')

# Validate every retained source object, both compressed and canonical uncompressed hashes.
registry = load('sources.json')
for source in registry['sources']:
    for field in ('retained_metadata', 'item_metadata', 'service_metadata', 'layer_metadata', 'retained_features', 'retained_data'):
        obj = source.get(field)
        if not isinstance(obj, dict) or 'path' not in obj:
            continue
        path = Path(obj['path'])
        path = (ROOT / path) if not path.is_absolute() else path
        check(path.is_file(), f"missing retained source {path}")
        raw = path.read_bytes()
        if 'bytes' in obj:
            check(len(raw) == obj['bytes'] and digest(raw) == obj['sha256'], f"metadata hash mismatch: {path}")
        if 'compressed_bytes' in obj:
            check(len(raw) == obj['compressed_bytes'] and digest(raw) == obj['compressed_sha256'], f"compressed source mismatch: {path}")
            uncompressed = gzip.decompress(raw)
            check(len(uncompressed) == obj['uncompressed_bytes'] and digest(uncompressed) == obj['uncompressed_sha256'], f"uncompressed source mismatch: {path}")

bol = load('neighbor-screen-bolivia.json')
col = load('neighbor-screen-colombia.json')
portions = load('derived-portion-audit.json')
check(bol['assigned_count'] == 117 and bol['source_admin_count'] == 110 and bol['coarse_graph_difference_count'] == 0, 'Bolivia neighbor/member screen mismatch')
check(col['assigned_count'] == 94 and col['whole_colombia_source_count'] == 1122 and col['assigned_internal_pair_graph_differences'] == 0, 'Colombia neighbor/member screen mismatch')
check(portions['fragment_count'] == 9 and portions['source_expected_neighbor_pair_count'] == portions['current_exact_neighbor_pair_count'] == 9, 'fragment graph mismatch')
check(not portions['neighbor_pair_graph_differences']['expected_missing_current'] and not portions['neighbor_pair_graph_differences']['current_missing_expected'], 'fragment neighbor graph differs')

land = load('gshhg-colombia-screen.json')
check(land['scope_count'] == 211 and set(land['per_location']) == set(ids), 'physical land screen does not cover exact scope')
check(sum(bool(x['representative_point_in_level1_land']) for x in land['per_location'].values()) == 210, 'physical land point count mismatch')
check(len(land['matched_source_records']) == 72, 'retained GSHHG selection count mismatch')
check(len(assessment['locations']) == 211 and assessment['counts']['assessed'] == 211, 'final assessment count mismatch')
print('PASS: 211/211 IDs, full parent and unresolved coverage, 9 corrections + 202 explicit gaps, source hashes, source rosters, physical and neighbor screens')
