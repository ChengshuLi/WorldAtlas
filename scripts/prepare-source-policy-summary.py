#!/usr/bin/env python3
"""Bounded runtime projection of the retained, sourced role-correction bundle."""
import argparse, collections, gzip, hashlib, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/source-policy-corrections/europe-v1.json.gz'
TARGET = ROOT / 'data/source-policy-corrections/summary.json'

def build_summary():
    raw = SOURCE.read_bytes()
    bundle = json.loads(gzip.decompress(raw))
    policies = [{key: row[key] for key in (
        'id', 'profile_iso', 'before_policy', 'after_policy', 'role_counts',
        'continent_counts', 'evidence_ids', 'effective_from', 'temporal_meaning',
        'semantic_complete')} for row in bundle['policy_corrections']]
    grouped = collections.defaultdict(list)
    roles = {}
    for row in bundle['location_annotations']:
        key = row['classification']
        role = {key: row['after_annotation'][key] for key in (
            'effective_source_role', 'effective_source_level', 'effective_role_type')}
        role['profile_iso'] = row['profile_iso']
        if key in roles and roles[key] != role:
            raise ValueError('Classification has inconsistent source roles: ' + key)
        roles[key] = role
        grouped[key].append(row['location_id'])
    if len({id for ids in grouped.values() for id in ids}) != bundle['counts']['locations']:
        raise ValueError('Compact role inventory is not unique or complete')
    evidence = []
    for id, row in bundle['source_evidence'].items():
        receipts = row.get('request_receipts', {})
        urls = list(dict.fromkeys([url for url in [row.get('url'), row.get('source', {}).get('url')]
            + [receipt['url'] for receipt in receipts.values()] if url]))
        fact = row.get('inspected_fact')
        if not fact and id == 'spain-municipality-source-metadata':
            fact = 'Retained municipality metadata identifies MUNICIPIOS; these remain distinct from agricultural comarca adaptations.'
        if not fact and id == 'kosovo-source-metadata-contradiction':
            fact = 'API metadata says Municipalities and 48 units; the pinned original geometry has seven named district features. The contradiction remains retained.'
        evidence.append({'id': id, 'urls': urls, 'fact': fact,
            'original_sha256': row.get('sha256') or row.get('source', {}).get('sha256') or row.get('manifest_sha256')})
    return {'version': 1, 'id': bundle['id'], 'reviewed_at': bundle['reviewed_at'],
        'source_bundle': {'path': 'data/source-policy-corrections/europe-v1.json.gz',
            'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)},
        'policy_corrections': policies,
        'role_groups': [{'classification': key, **roles[key], 'location_ids': sorted(grouped[key])}
            for key in sorted(grouped)],
        'source_evidence': evidence, 'counts': bundle['counts'],
        'semantic_complete': False, 'geography_changed': False,
        'context': 'Source-role corrections update reference descriptions. Frozen review notes remain original context; location granularity and boundaries are not approved.'}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    raw = (json.dumps(build_summary(), ensure_ascii=False, separators=(',', ':')) + '\n').encode()
    if len(raw) > 80000:
        raise ValueError('Bounded policy summary exceeds its 80 KB budget')
    if args.check:
        if not TARGET.exists() or TARGET.read_bytes() != raw:
            raise ValueError('Source-policy summary is stale; regenerate explicitly')
    else:
        TARGET.parent.mkdir(parents=True, exist_ok=True)
        TARGET.write_bytes(raw)
    print(json.dumps({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
        'policies': 3, 'locations': 1001, 'semantic_complete': False}))

if __name__ == '__main__':
    main()
