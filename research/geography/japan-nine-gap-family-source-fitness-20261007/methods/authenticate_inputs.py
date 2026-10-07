"""Authenticate #1316 full component, fragment and contact inputs; performs no overlays."""
import gzip, hashlib, json, pathlib, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]
PROPOSAL = json.loads((ROOT / 'inputs/root-proposal-proof.json').read_text())
ISSUE = json.loads((ROOT / 'inputs/issue-snapshot.json').read_text())

def sha(raw): return hashlib.sha256(raw).hexdigest()
def canon(value): return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n').encode()

def exact_section(body, start, end): return body.split(start, 1)[1].split(end, 1)[0]
body = ISSUE['body']
families = __import__('re').findall(r'"(gap-source-batch:[0-9a-f]{24})"', exact_section(body, 'Exact complete family IDs:', 'Exact component IDs'))
components = __import__('re').findall(r'"(physical-component:[0-9a-f]{64})"', exact_section(body, 'Exact component IDs', 'Exact full current Atlas contact subjects'))
contacts = __import__('re').findall(r'"(gb:JPN:ADM2:[A-Z0-9]+)"', exact_section(body, 'Exact full current Atlas contact subjects:', '<!-- worldatlas-work:v1'))
assert len(families) == len(set(families)) == 9
assert len(components) == len(set(components)) == 28
assert len(contacts) == len(set(contacts)) == 21
assert set(families) == set(PROPOSAL['complete_family_ids'])
assert set(components) == set(PROPOSAL['component_ids'])
assert set(contacts) == set(PROPOSAL['contact_ids'])

expected_components = {x['id']: x for x in PROPOSAL['full_candidates']}
expected_fragment_hashes = {}
for feature in expected_components.values():
    for binding in feature['properties']['fragment_bindings']:
        key = binding['id']
        if key in expected_fragment_hashes: raise ValueError('duplicate fragment membership')
        expected_fragment_hashes[key] = binding['feature_sha256']

index_path = REPO / 'coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1/index.json'
index = json.loads(index_path.read_text())
features = {'components': {}, 'fragments': {}}
source_payloads = []
for alias in index['aliases']:
    original = alias['original']; logical = original['path']
    if '/components-v3/components-' not in logical: continue
    encoded = (REPO / alias['payload']).read_bytes()
    if len(encoded) != original['bytes'] or sha(encoded) != original['sha256']: raise ValueError(f'encoded payload differs: {logical}')
    decoded = gzip.decompress(encoded)
    if len(decoded) != original['uncompressed_bytes'] or sha(decoded) != original['uncompressed_sha256']: raise ValueError(f'decoded source differs: {logical}')
    source_payloads.append({'logical_path': logical, 'payload_path': alias['payload'], 'encoded_bytes': len(encoded), 'encoded_sha256': sha(encoded), 'decoded_bytes': len(decoded), 'decoded_sha256': sha(decoded)})
    parsed = json.loads(decoded); rows = parsed if isinstance(parsed, list) else parsed['features']
    for feature in rows:
        identity = feature.get('id')
        if identity in components:
            if identity in features['components']: raise ValueError(f'duplicate full component {identity}')
            features['components'][identity] = feature

# Authenticate the complete component/family report slices, not only routed
# target records. These whole gzip bodies bind the report's 95,173/15,610-row
# source closure before any source comparison is considered.
routing_inputs=[]
routing_dir=REPO/'coordination/engineering/global-actionability-routing-20261007/results'
for descriptor in PROPOSAL['whole_input_body_closure']:
    path=routing_dir/pathlib.Path(descriptor['path']).name
    encoded=path.read_bytes()
    if len(encoded)!=descriptor['bytes'] or sha(encoded)!=descriptor['sha256']:
        raise ValueError(f'whole delivered routing slice differs: {path}')
    decoded=gzip.decompress(encoded)
    if len(decoded)!=descriptor['uncompressed_bytes'] or sha(decoded)!=descriptor['uncompressed_sha256']:
        raise ValueError(f'decoded delivered routing slice differs: {path}')
    routing_inputs.append({'path':str(path.relative_to(REPO)),'bytes':len(encoded),'sha256':sha(encoded),
        'uncompressed_bytes':len(decoded),'uncompressed_sha256':sha(decoded)})

# Restore each complete component/family JSONL body from every exact gzip
# slice, authenticate the concatenated whole raw bytes, and only then decode
# and parse its JSON lines. This proves the 95,173-row and 15,610-row report
# bodies, rather than treating individually verified slices as whole bodies.
report_path=routing_dir/'report.json'; report_raw=report_path.read_bytes()
if sha(report_raw)!=PROPOSAL['routing_report_sha256']:raise ValueError('delivered report SHA differs')
report=json.loads(report_raw)
config_raw=(REPO/'coordination/engineering/global-actionability-routing-20261007/input-config.json').read_bytes()
if sha(config_raw)!='7623fa8a61b72c33a1560f0ab612e70c463e8c25beef930043c985fd6657f173':
    raise ValueError('delivered report input configuration SHA differs')
if sha((REPO/'data/world-index.json').read_bytes())!=PROPOSAL['world_index_sha256']:
    raise ValueError('audited world index SHA differs')
expected_route={x['component']:x for x in PROPOSAL['routing_rows']}
expected_family={x['id']:x for x in PROPOSAL['families']}
whole_body_receipts=[]
for name,expected_rows,identity_field in [('components',expected_route,'component'),('families',expected_family,'id')]:
    whole=next(x for x in report['complete_whole_raw_bodies'] if x['name']==name)
    desc_by_path={pathlib.Path(x['path']).name:x for x in whole['parts']}
    scope_parts=[x for x in PROPOSAL['whole_input_body_closure'] if x['body']==name]
    if len(scope_parts)!=len(whole['parts']) or set(desc_by_path)!={pathlib.Path(x['path']).name for x in scope_parts}:
        raise ValueError(f'complete {name} whole-body part roster differs')
    aggregate=hashlib.sha256(); aggregate_bytes=0; seen=set(); matched={}
    with tempfile.TemporaryFile(mode='w+b') as restored:
        for descriptor in sorted(scope_parts,key=lambda x:pathlib.Path(x['path']).name):
            leaf=pathlib.Path(descriptor['path']).name; part=desc_by_path[leaf]
            if any(descriptor[k]!=part[k] for k in ('bytes','sha256','uncompressed_bytes','uncompressed_sha256')):
                raise ValueError(f'{name} declared whole-body part differs: {leaf}')
            source=routing_dir/leaf; encoded=source.read_bytes()
            if len(encoded)!=descriptor['bytes'] or sha(encoded)!=descriptor['sha256']:
                raise ValueError(f'{name} encoded part differs: {leaf}')
            decoded=gzip.decompress(encoded)
            if len(decoded)!=descriptor['uncompressed_bytes'] or sha(decoded)!=descriptor['uncompressed_sha256']:
                raise ValueError(f'{name} decoded part differs: {leaf}')
            restored.write(decoded);aggregate.update(decoded);aggregate_bytes+=len(decoded)
        if aggregate_bytes!=whole['bytes'] or aggregate.hexdigest()!=whole['sha256']:
            raise ValueError(f'{name} concatenated whole raw body differs')
        restored.seek(0)
        for raw_line in restored:
            if not raw_line.strip():continue
            item=json.loads(raw_line.decode('utf-8'))
            identity=item.get(identity_field)
            if not isinstance(identity,str) or identity in seen:raise ValueError(f'{name} whole body has duplicate/missing identities')
            seen.add(identity)
            if identity in expected_rows:matched[identity]=item
    if len(seen)!=report['counts'][name] or matched.keys()!=expected_rows.keys():
        raise ValueError(f'{name} full row count or scoped row closure differs')
    if any(canon(matched[k])!=canon(expected_rows[k]) for k in expected_rows):
        raise ValueError(f'{name} scoped full source rows differ from proposal')
    whole_body_receipts.append({'name':name,'bytes':aggregate_bytes,'sha256':aggregate.hexdigest(),
        'complete_rows':len(seen),'scoped_rows':len(matched),'parts':len(scope_parts),
        'parse_after_whole_body_hash':True})

# Original detector fragments are retained as complete GeoJSON feature records.
detection = json.loads((REPO / 'coordination/engineering/physical-gap-audit-1005-20261005-local18/detection-v4/report.json').read_text())
for descriptor in detection['outputs']:
    if '/candidates-' not in descriptor['path']: continue
    encoded = (REPO / descriptor['path']).read_bytes()
    if len(encoded) != descriptor['bytes'] or sha(encoded) != descriptor['sha256']: raise ValueError(f'encoded original fragment shard differs: {descriptor["path"]}')
    decoded = gzip.decompress(encoded)
    if len(decoded) != descriptor['uncompressed_bytes'] or sha(decoded) != descriptor['uncompressed_sha256']: raise ValueError(f'decoded original fragment shard differs: {descriptor["path"]}')
    source_payloads.append({'logical_path': descriptor['path'], 'encoded_bytes': len(encoded), 'encoded_sha256': sha(encoded), 'decoded_bytes': len(decoded), 'decoded_sha256': sha(decoded)})
    for feature in json.loads(decoded)['features']:
        identity = feature.get('id')
        if identity in expected_fragment_hashes:
            if identity in features['fragments']: raise ValueError(f'duplicate original fragment {identity}')
            features['fragments'][identity] = feature
if set(features['components']) != set(components): raise ValueError('incomplete full component geometry closure')
if any(canon(features['components'][k]) != canon(expected_components[k]) for k in components): raise ValueError('component differs from routed full feature')
route_by_id = {r['component']: r for r in PROPOSAL['routing_rows']}
if set(route_by_id) != set(components): raise ValueError('routing row roster differs')
for identity in components:
    feature = expected_components[identity]
    if sha(canon(feature)) != route_by_id[identity]['current_feature_sha256'] or sha(canon(feature['geometry'])) != route_by_id[identity]['current_geometry_sha256']:
        raise ValueError(f'full candidate does not match routed feature and geometry hashes: {identity}')
family_by_id = {}
for family in PROPOSAL['families']:
    if family['numeric_closure_component_count'] != 0 or family['numeric_closure_component_ids']:
        raise ValueError(f'numeric-first member present in family {family["id"]}')
    for identity in family['complete_component_ids']:
        if identity in family_by_id: raise ValueError('component belongs to multiple complete families')
        family_by_id[identity] = family['id']
if set(family_by_id) != set(components): raise ValueError('complete family closure differs from all 28 subjects')
if set(features['fragments']) != set(expected_fragment_hashes): raise ValueError('incomplete original fragment geometry closure')
for identity, expected in expected_fragment_hashes.items():
    if sha(canon(features['fragments'][identity])) != expected: raise ValueError(f'whole fragment binding differs: {identity}')

contacts_full = {}
world_pins = {
 'data/geography/part-11.json': 'd1b2fb15c9427497de740eb33a529ef382b58cb319028f2aa38f5878de4c9b02',
 'data/geography/part-12.json': '24b44617b0164913f598c94c2c1b36e1a2321f0456644cc20e7f2856955b03f7',
}
for logical, digest in world_pins.items():
    raw = (REPO / logical).read_bytes()
    if sha(raw) != digest: raise ValueError(f'complete world partition differs: {logical}')
    for feature in json.loads(raw)['features']:
        if feature.get('id') in contacts:
            if feature['id'] in contacts_full: raise ValueError(f'duplicate contact {feature["id"]}')
            contacts_full[feature['id']] = feature
expected_contacts = {k: v['full_feature'] for k, v in PROPOSAL['full_current_contacts'].items()}
if set(contacts_full) != set(contacts): raise ValueError('incomplete full contact geometry closure')
if any(canon(contacts_full[k]) != canon(expected_contacts[k]) for k in contacts): raise ValueError('contact differs from complete current feature')

contract = body.split('<!-- worldatlas-work:v1', 1)[1].split('-->', 1)[0].strip()
scope = {
 'issue': {'number': 1316, 'url': ISSUE['url'], 'updated_at': ISSUE['updatedAt'], 'body_sha256': sha(body.encode()), 'contract_sha256': sha(contract.encode())},
 'proposal_sha256': sha((ROOT / 'inputs/root-proposal-proof.json').read_bytes()),
 'actual_routing_merge': PROPOSAL['actual_routing_merge'],
 'routing_report_sha256': PROPOSAL['routing_report_sha256'],
 'world_index_sha256': PROPOSAL['world_index_sha256'],
 'families': families, 'components': components, 'contacts': contacts,
 'category_counts': PROPOSAL['category_counts'],
 'whole_input_body_closure': PROPOSAL['whole_input_body_closure'],
 'complete_world_parts': PROPOSAL['complete_world_parts'],
 'families_full_records': PROPOSAL['families'], 'routing_rows': PROPOSAL['routing_rows'],
 'full_candidate_features': list(expected_components.values()),
 'full_original_fragment_features': list(features['fragments'].values()),
 'full_current_contact_features': list(contacts_full.values()),
 'source_payloads': source_payloads,
 'complete_routing_body_slices': routing_inputs,
 'complete_raw_routing_bodies': whole_body_receipts,
 'limits': PROPOSAL['limits'],
}
output = ROOT / 'inputs/immutable-scope-and-inputs.json'
output.write_text(json.dumps(scope, ensure_ascii=False, separators=(',', ':')) + '\n')
receipt = {
 'status': 'PASS', 'comparison_performed': False,
 'families': len(families), 'whole_components': len(components),
 'whole_original_fragments': len(features['fragments']), 'full_contacts': len(contacts),
 'candidate_feature_differences': 0, 'fragment_hash_binding_differences': 0,
 'contact_feature_differences': 0, 'component_source_shards': sum('/components-v3/components-' in x['logical_path'] for x in source_payloads),
 'fragment_source_shards': sum('/detection-v4/candidates-' in x['logical_path'] for x in source_payloads),
 'scope_sha256': sha(output.read_bytes()), 'source_payloads': source_payloads,
 'complete_routing_body_slices': routing_inputs,
 'source_scope_only': 'This authenticates complete routed and current Atlas records; it does not measure geographic or source overlap.'
}
(ROOT / 'receipts/input-authentication.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({k: receipt[k] for k in ('status','families','whole_components','whole_original_fragments','full_contacts','candidate_feature_differences','fragment_hash_binding_differences','contact_feature_differences','scope_sha256')}))
