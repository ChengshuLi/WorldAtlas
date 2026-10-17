"""Metadata preparation from whole retained originals; no spatial predicates.

Reads exact accepted Git objects without lazy fetching. Outputs preserve complete
consumed source and selected owner features for later stock physical execution.
"""
import collections
import gzip
import hashlib
import json
import os
import pathlib
import subprocess
import sys

REPO = pathlib.Path(sys.argv[1]).resolve(strict=True)
OUT = pathlib.Path(sys.argv[2]).absolute()
BASE = 'b7ca15f8d88241b088699396d3df0ca58a9e0803'
INPUT = sys.argv[3]
assert len(INPUT) == 40
PREFIX = 'coordination/engineering/mozambique-original-repair-20261017/'
QUEUE = 'coordination/engineering/global-current-cell-work-queue-20261014/'
ENV = dict(os.environ, GIT_NO_LAZY_FETCH='1', GIT_NO_REPLACE_OBJECTS='1', GIT_OPTIONAL_LOCKS='0')
assert not OUT.exists() and OUT.parent.is_dir()
assert all(not p.is_symlink() for root in (REPO, OUT) for p in (root, *root.parents))
inputs = {}
def sha(body):
    return hashlib.sha256(body).hexdigest()
def git(*args):
    return subprocess.check_output(['git', '-c', 'protocol.allow=never', '-C', str(REPO), *args], env=ENV)
def read(name, commit=BASE):
    row = git('ls-tree', '-z', commit, '--', name).rstrip(b'\0')
    metadata, member = row.split(b'\t')
    mode, kind, oid = metadata.decode().split()
    assert mode == '100644' and kind == 'blob' and member.decode() == name
    body = git('cat-file', 'blob', oid)
    assert hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\0' + body).hexdigest() == oid
    pin = dict(commit=commit, path=name, mode=mode, git_blob_oid=oid, bytes=len(body), sha256=sha(body))
    if name.endswith('.gz'):
        body = gzip.decompress(body)
        pin.update(decoded_bytes=len(body), decoded_sha256=sha(body))
    inputs[commit, name] = pin
    return body
def js(name, commit=BASE):
    return json.loads(read(name, commit))
def encode(value):
    return (json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n').encode()

assert read(PREFIX + 'method/prepare-source-members.py', INPUT) == pathlib.Path(__file__).read_bytes()
scope = js(PREFIX + 'original-claim-scope.json', INPUT)
owners = {r['index']: r for r in scope['owners']}
assert len(owners) == 81 and len(set(scope['complete_source_atoms'])) == 81
roster = js(QUEUE + 'source-feature-roster.json.gz')
by_source = {r['source_id']: r for r in roster}
assert len(by_source) == len(roster) == 73567
semantic = js('data/semantic-report.json')
changes = collections.defaultdict(list)
for row in semantic['changes']:
    changes[row['id']].append(row)
selected = {}
whole_country = []
for name in ('data/geography/part-16.json',):
    product = js(name)
    assert product['type'] == 'FeatureCollection'
    for feature in product['features']:
        if feature['properties']['reference_owner'] == 'Mozambique':
            whole_country.append(feature)
        if feature['id'] in {r['id'] for r in owners.values()}:
            assert feature['id'] not in selected
            selected[feature['id']] = feature
assert len(selected) == len(owners)

catalogue = js('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json')
metadata = js('data/administrative-sources.json')
products, product_inventory = {}, []
for family in ('gb:MOZ:ADM1', 'gb:MOZ:ADM2', 'gb:MWI:ADM1', 'gb:TZA:ADM1'):
    record, = [r for r in catalogue['products'] if r['key'] == family]
    chunks, offset = [], 0
    for ordinal, part in enumerate(record['parts']):
        assert part['ordinal'] == ordinal and part['offset'] == offset
        decoded = read(part['path'])
        pin = inputs[BASE, part['path']]
        assert pin['bytes'] == part['bytes'] and pin['sha256'] == part['sha256']
        assert len(decoded) == part['uncompressed_bytes'] and sha(decoded) == part['uncompressed_sha256']
        chunks.append(decoded)
        offset += len(decoded)
    body = b''.join(chunks)
    assert len(body) == record['original_bytes'] and sha(body) == record['original_sha256']
    product = json.loads(body)
    assert product['type'] == 'FeatureCollection'
    assert product['crs']['properties']['name'] == 'urn:ogc:def:crs:OGC:1.3:CRS84'
    originals = {family + ':' + f['properties']['shapeID']: f for f in product['features']}
    assert len(originals) == len(product['features']) == record['feature_count'] == record['advertised_feature_count']
    assert set(originals) == {r['source_id'] for r in roster if r['source_id'].startswith(family + ':')}
    assert metadata[family]['sha256'] == record['original_sha256']
    products[family] = originals
    product_inventory.append(dict(source_family=family, original_bytes=len(body), original_sha256=sha(body),
                                  features=len(originals), crs=product['crs'], metadata=metadata[family]))

stages, membership, owner_associations = [], [], []
for index, owner in sorted(owners.items()):
    feature = selected[owner['id']]
    properties = feature['properties']
    assert feature['id'] == properties['id'] == owner['id']
    assert properties['reference_owner'] == 'Mozambique' and properties['parent_id'] == owner['province_id']
    atoms = owner['source_atoms']
    assert len(atoms) == len(set(atoms))
    if atoms == [owner['id']]:
        assert owner['id'] in products['gb:MOZ:ADM2']
        assert not properties['metadata'].get('source_member_ids')
        association = 'direct-original-district'
    else:
        members = properties['metadata']['source_member_ids']
        change, = changes[owner['id']]
        assert sorted(members) == sorted(change['replaces']) == sorted(atoms)
        assert properties['metadata']['location_basis'] == change['basis']
        assert properties['metadata']['source_url'] == change['source']
        association = 'accepted-complete-aggregation'
    for atom in atoms:
        row = by_source[atom]
        assert row['family_index'] == 224 and row['owners'] == [index]
        original = products['gb:MOZ:ADM2'][atom]
        stages.append(dict(target=atom, consumed=original, selected=feature))
        membership.append(dict(source_id=atom, target_id=owner['id'], pixelIndex=index,
                               source_ordinal=row['ordinal'], source_index=row['source_index']))
    owner_associations.append(dict(id=owner['id'], pixelIndex=index, name=properties['name'],
                                   association=association, source_atoms=atoms,
                                   location_basis=properties['metadata'].get('location_basis'),
                                   source_url=properties['metadata'].get('source_url')))
assert len(stages) == len({s['target'] for s in stages}) == 81
assert set(s['target'] for s in stages) == set(scope['complete_source_atoms'])
stage_bytes = encode(stages)
assessment = dict(version=1, kind='mozambique-original-source-owner-preparation', accepted_commit=BASE,
                  whole_physical_stage_targets=len(stages), whole_intended_owners=len(owners),
                  complete_selected_country_owners_in_one_part=len(whole_country),
                  whole_stage_serialized_bytes=len(stage_bytes),
                  whole_products=product_inventory, owner_associations=owner_associations,
                  inputs=list(inputs.values()),
                  limits=['Metadata association is not independent semantic approval, physical support, native qualification or owner-zero proof.',
                          'Every original source atom and complete selected owner geometry is preserved. No polygon union, clipping, snapping or spatial predicate ran.',
                          'Complete foreign applicability, geometric validity and whole physical execution remain pending.'])
OUT.mkdir()
outputs = {'source-target-membership.json': membership, 'source-owner-assessment.json': assessment}
(OUT / 'original-stage-inputs.json').write_bytes(stage_bytes)
for name, value in outputs.items():
    (OUT / name).write_bytes(encode(value))
print(json.dumps({k: assessment[k] for k in ['whole_physical_stage_targets', 'whole_intended_owners',
                'complete_selected_country_owners_in_one_part', 'whole_stage_serialized_bytes',
                'accepted_commit']}))
