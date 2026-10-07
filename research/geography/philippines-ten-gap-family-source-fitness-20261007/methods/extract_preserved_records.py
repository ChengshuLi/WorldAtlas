#!/usr/bin/env python3
"""Restore the accepted 22-subject source-fit evidence from pinned repository inputs.

This validates and extracts preserved source/assessment records only; it performs
no GIS operation and generates no new geography comparison.
"""
import argparse, base64, gzip, hashlib, json, pathlib, subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPOSITORY = ROOT.parents[2]
BASE = '9618736b023d041f81496c923e7d0c2154e1491c'
ROUTING_COMMIT = '0198938719a5666b6726fb6a1e45779926eefeb2'
TRANSPORT_PATH = 'coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-PHL-ADM3-000.bin.gz'
SOURCE_SHA = '2ece3d44a5c6a2afb385ffbf3a6b88d83e4d3a3e7eed9a52cb3be1bc59e289fc'
sha = lambda b: hashlib.sha256(b).hexdigest()

def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()

def fail(ok, message):
    if not ok:
        raise ValueError(message)

def require_sha(raw, expected, label):
    fail(sha(raw) == expected, f'{label} SHA-256 mismatch')

def require_exact_ids(expected, observed, label):
    fail(len(observed) == len(set(observed)), f'{label} contains duplicate IDs')
    fail(set(observed) == set(expected) and len(observed) == len(expected), f'{label} membership mismatch')

def require_feature_binding(feature, expected_id, expected_sha, label):
    fail(feature.get('id') == expected_id, f'{label} ID mismatch')
    require_sha(canonical(feature), expected_sha, label)

def git_blob(commit, path):
    return subprocess.check_output(['git', '-C', str(REPOSITORY), 'show', f'{commit}:{path}'])

def decode_jsonl(raw):
    return [json.loads(line) for line in gzip.decompress(raw).splitlines() if line]

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode() + b'\n')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=pathlib.Path, default=ROOT / 'records')
    args = ap.parse_args()

    proposal_raw = (ROOT / 'inputs/root-philippines-ten-full-family-source-fit-proposal.json').read_bytes()
    proposal = json.loads(proposal_raw)

    # Full source identity is tied to the accepted whole gzip transport, not a
    # similarly named or unsimplified source. Candidate raw bytes must match.
    source_raw = (ROOT / 'inputs/gb-PHL-ADM3.original').read_bytes()
    transport = git_blob(BASE, TRANSPORT_PATH)
    decoded = gzip.decompress(transport)
    require_sha(transport, '0b7b241fd977a792eca3101f31f0d02fba79d75b6ea463e33dec937b6c5ed72c', 'source transport')
    require_sha(decoded, SOURCE_SHA, 'decoded consumed source')
    require_sha(source_raw, SOURCE_SHA, 'retained consumed source')
    fail(source_raw == decoded, 'retained consumed source differs from decoded baseline transport')
    source = json.loads(source_raw)
    fail(len(source.get('features', [])) == 1647, 'Consumed source feature count mismatch')

    ids = sorted(proposal['contact_ids'])
    require_exact_ids(ids, proposal['contact_ids'], 'contact scope')
    native = {value.rsplit(':', 1)[-1] for value in ids}
    originals = [f for f in source['features'] if f.get('properties', {}).get('shapeID') in native]
    require_exact_ids(native, [f.get('properties', {}).get('shapeID') for f in originals], 'original source features')
    fail(len(originals) == 22, 'Expected 22 original source features')

    # Rebuild current complete features from the two exact pinned world parts.
    current_map = {}
    for part in ('data/geography/part-18.json', 'data/geography/part-19.json'):
        body = json.loads(git_blob(BASE, part))
        for feature in body['features']:
            feature_id = feature.get('id') or feature.get('properties', {}).get('id')
            if feature_id in ids:
                fail(feature_id not in current_map, 'Current contact duplicated between pinned full parts')
                current_map[feature_id] = feature
    require_exact_ids(ids, list(current_map), 'current contact features in pinned whole parts')
    current = [current_map[i] for i in ids]
    proposal_current = proposal['full_current_contacts']
    require_exact_ids(ids, list(proposal_current), 'proposal contact registry')
    for feature_id in ids:
        expected = proposal_current[feature_id]
        require_feature_binding(current_map[feature_id], feature_id, expected['full_feature_sha256'], f'current full feature {feature_id}')

    # Preserve accepted candidate pointsets unchanged and bind each full body.
    candidates = proposal['full_candidates']
    component_ids = sorted(proposal['component_ids'])
    require_exact_ids(component_ids, [f.get('id') for f in candidates], 'complete candidate pointsets')
    candidate_records = []
    for feature in sorted(candidates, key=lambda f: f['id']):
        candidate_records.append({'component_id': feature['id'], 'feature': feature,
                                  'canonical_feature_sha256': sha(canonical(feature).rstrip(b'\n')),
                                  'canonical_geometry_sha256': sha(canonical(feature['geometry']).rstrip(b'\n'))})

    # Reopen and authenticate all complete original routing body partitions
    # declared by the predecessor proposal, then cross-check selected rows.
    closure = proposal['whole_input_body_closure']
    fail(len(closure) == 39, 'Original routing body closure must have all 39 partitions')
    closure_bytes = {}
    for descriptor in closure:
        path = 'coordination/engineering/global-actionability-routing-20261007/results/' + descriptor['path']
        raw = git_blob(BASE, path)
        require_sha(raw, descriptor['sha256'], f'routing input {path}')
        unpacked = gzip.decompress(raw)
        require_sha(unpacked, descriptor['uncompressed_sha256'], f'decoded routing input {path}')
        fail(len(raw) == descriptor['bytes'] and len(unpacked) == descriptor['uncompressed_bytes'], f'routing input length mismatch: {path}')
        closure_bytes[path] = unpacked
    component_stream = b''.join(closure_bytes['coordination/engineering/global-actionability-routing-20261007/results/' + d['path']]
                                for d in sorted(closure, key=lambda x: x['path']) if d['body'] == 'components')
    family_stream = b''.join(closure_bytes['coordination/engineering/global-actionability-routing-20261007/results/' + d['path']]
                             for d in sorted(closure, key=lambda x: x['path']) if d['body'] == 'families')
    component_tokens = [('"component":"' + value + '"').encode() for value in component_ids]
    family_tokens = [('"id":"' + value + '"').encode() for value in proposal['complete_family_ids']]
    component_stream_rows = [json.loads(line) for line in component_stream.splitlines()
                             if line and any(token in line for token in component_tokens)]
    family_stream_rows = [json.loads(line) for line in family_stream.splitlines()
                          if line and any(token in line for token in family_tokens)]
    component_rows = {}
    family_rows = {}
    for row in component_stream_rows:
        if row.get('component') in component_ids:
            fail(row['component'] not in component_rows, 'Duplicate selected original routing component')
            component_rows[row['component']] = row
    for row in family_stream_rows:
        if row.get('id') in proposal['complete_family_ids']:
            fail(row['id'] not in family_rows, 'Duplicate selected original routing family')
            family_rows[row['id']] = row
    require_exact_ids(component_ids, list(component_rows), 'selected original routing components')
    require_exact_ids(proposal['complete_family_ids'], list(family_rows), 'complete original routing families')
    for row in proposal['routing_rows']:
        fail(component_rows[row['component']] == row, f'Original routing component row changed: {row["component"]}')
    proposal_families = {row['id']: row for row in proposal['families']}
    require_exact_ids(proposal['complete_family_ids'], list(proposal_families), 'proposal complete family rows')
    for family_id, row in proposal_families.items():
        fail(family_rows[family_id] == row, f'Original routing family row changed: {family_id}')

    # Reopen all 18 source result bodies at both the original routing merge and
    # the pinned baseline, prove byte identity, and retain the selected rows.
    expected = {r['component']: r for r in proposal['routing_rows']}
    paths = sorted({r['whole_physical_containing_file'] for r in proposal['routing_rows']})
    fail(len(paths) == 18, 'Physical comparison source closure must include all 18 whole bodies')
    selected = {}
    physical_closure = []
    for path in paths:
        original_body = git_blob(ROUTING_COMMIT, path)
        baseline_body = git_blob(BASE, path)
        fail(original_body == baseline_body, f'Physical result body differs between routing merge and pinned baseline: {path}')
        rows = decode_jsonl(original_body)
        physical_closure.append({'path': path, 'bytes': len(original_body), 'sha256': sha(original_body),
                                 'uncompressed_bytes': len(gzip.decompress(original_body)),
                                 'uncompressed_sha256': sha(gzip.decompress(original_body)),
                                 'routing_commit_sha256': sha(git_blob(ROUTING_COMMIT, path)),
                                 'baseline_equals_routing_commit': True})
        for line in gzip.decompress(original_body).splitlines():
            if not line:
                continue
            row = json.loads(line)
            component = row.get('component_id')
            if component in expected:
                fail(component not in selected, f'Duplicate archived physical row: {component}')
                digest = sha(canonical(row))
                require_sha(canonical(row), expected[component]['whole_physical_row_sha256'], f'archived physical row {component}')
                selected[component] = {'record': row, 'canonical_sha256': digest,
                                       'raw_line_sha256': sha(line),
                                       'raw_line_bytes_base64': base64.b64encode(line).decode('ascii'),
                                       'source_file': path}
    require_exact_ids(list(expected), list(selected), 'selected archived physical rows')
    package = {'source_commit': ROUTING_COMMIT, 'source_files': paths,
               'records': [{'component': i, **selected[i]} for i in sorted(selected)]}

    write_json(args.output / 'original-source-features-22.json', {'type': 'FeatureCollection', 'features': originals})
    write_json(args.output / 'current-contact-features-22.json', {'type': 'FeatureCollection', 'features': current})
    write_json(args.output / 'candidate-pointsets-22.json', {'features': candidate_records, 'count': len(candidate_records),
               'source_proposal_sha256': sha(proposal_raw), 'science_status': 'unchanged accepted predecessor pointsets; no new geometry analysis'})
    write_json(args.output / 'physical-comparison-rows-22.json', package)
    write_json(args.output / 'accepted-predecessor-source-closure.json', {
        'baseline_commit': BASE, 'routing_merge_commit': ROUTING_COMMIT,
        'proposal_sha256': sha(proposal_raw), 'original_source_transport_path': TRANSPORT_PATH,
        'original_source_transport_sha256': sha(transport), 'original_source_decoded_sha256': sha(decoded),
        'original_source_retained_equals_decoded': True, 'routing_body_count': len(closure_bytes),
        'routing_component_row_count': len(component_rows), 'routing_family_row_count': len(family_rows),
        'physical_result_body_count': len(physical_closure), 'physical_result_bodies': physical_closure,
        'current_contact_parts': ['data/geography/part-18.json', 'data/geography/part-19.json'],
        'candidate_pointset_feature_sha256': {x['component_id']: x['canonical_feature_sha256'] for x in candidate_records},
        'candidate_pointset_geometry_sha256': {x['component_id']: x['canonical_geometry_sha256'] for x in candidate_records},
        'family_ids': sorted(family_rows), 'component_ids': sorted(component_rows), 'contact_ids': ids,
        'science_disposition': 'The 22 component/family source-relative findings and candidate pointsets are preserved accepted predecessor outputs; no source authority or new physical comparison is inferred.'})
    print(json.dumps({'result': 'PASS', 'original_contacts': len(originals), 'current_contacts': len(current),
                      'candidate_pointsets': len(candidate_records), 'families': len(family_rows),
                      'routing_component_rows': len(component_rows), 'physical_rows': len(selected),
                      'routing_bodies': len(closure_bytes), 'physical_bodies': len(physical_closure),
                      'source_sha256': sha(source_raw)}, sort_keys=True))

if __name__ == '__main__':
    main()
