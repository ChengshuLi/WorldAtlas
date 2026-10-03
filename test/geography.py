"""Validate prepared source identities and display polygon geometry."""
import gzip, hashlib, json, pathlib, tarfile
from shapely.geometry import shape
from shapely import STRtree
def read(path): return json.loads(path.read_text())
def validated_source_creations(features,data):
 """Accept new source land only through the installed, byte-pinned proof chain."""
 new={f['id']:f for f in features if f['properties']['metadata'].get('reference_version')!=3}
 if not new:return set()
 bundle=data/'macro-improvements/combined-restoration'
 installed=read(data/'publication-geography-receipt.json')
 raw=gzip.decompress((bundle/'aggregate-source-receipt.json.gz').read_bytes());receipt=json.loads(raw)
 assert hashlib.sha256(raw).hexdigest()==installed['sources']['sourceReceipt']['sha256'],'Creation receipt differs from installed proof'
 assert receipt['geometry_stage_validated'] is True and receipt['historical_claims_transferred'] is False
 assert receipt['after_footprints_sha256']==installed['after_footprints_sha256']
 proofs={p['location_id']:p for p in receipt['creation_proofs']}
 approved={f['id']:f for f in receipt['added_features']}
 assert len(proofs)==len(receipt['creation_proofs']) and len(approved)==len(receipt['added_features'])
 assert set(new)==set(proofs)==set(approved)==set(receipt['added_ids']),'Unreceipted source role'
 index=json.loads(gzip.decompress((bundle/'installation-proof-index.json.gz').read_bytes()))
 archive=bundle/index['archive']['path'];body=archive.read_bytes()
 assert index['history_transfer'] is False and len(body)==index['archive']['bytes'] and hashlib.sha256(body).hexdigest()==index['archive']['sha256']
 with tarfile.open(archive) as sources:
  for identifier,feature in new.items():
   assert feature==approved[identifier],f'Created feature differs from reviewed source record: {identifier}'
   assert feature['properties']['metadata'].get('reference_version') is None,'New source land must not impersonate a legacy version'
   proof=proofs[identifier];source=proof['source'];member=sources.getmember(source['path'])
   assert member.isfile() and not pathlib.PurePosixPath(member.name).is_absolute() and '..' not in pathlib.PurePosixPath(member.name).parts
   raw=sources.extractfile(member).read();assert hashlib.sha256(raw).hexdigest()==source['sha256']
   document=json.loads(raw);matches=[f for f in document.get('features',[document]) if f.get('id')==source['identity']]
   assert len(matches)==1 and matches[0]['geometry']==feature['geometry'],'Created footprint differs from exact named source'
   assert source['license'] and source['attribution'] and source['url'].startswith(('https://','http://'))
   assert source['supported_from']!=0 and source['supported_to']!=0 and source['supported_from']<source['supported_to']
   assert proof['identity_review']['status']=='distinct-new-territory'
 return set(new)

parts = json.loads(pathlib.Path('data/world-index.json').read_text())['parts']
locations = [f for part in parts for f in json.loads((pathlib.Path('data') / part).read_text())['features']]
created_source_ids = validated_source_creations(locations, pathlib.Path('data'))
if created_source_ids:
    created = next(f for f in locations if f['id'] in created_source_ids)
    legacy = next(f for f in locations if f['id'] not in created_source_ids)
    for field in ('name', 'parent_id'):
        changed = {**created, 'properties': {**created['properties'], field: 'unreviewed-change'}}
        try:
            validated_source_creations([changed if f['id'] == changed['id'] else f for f in locations], pathlib.Path('data'))
        except AssertionError:
            pass
        else:
            raise AssertionError(f'Unreviewed creation {field} was accepted')
    metadata = {k:v for k,v in legacy['properties']['metadata'].items() if k != 'reference_version'}
    changed = {**legacy, 'properties': {**legacy['properties'], 'metadata': metadata}}
    try:
        validated_source_creations([changed if f['id'] == changed['id'] else f for f in locations], pathlib.Path('data'))
    except AssertionError:
        pass
    else:
        raise AssertionError('Removing a legacy source version must not bypass the source contract')
assert len({f['id'] for f in locations}) == len(locations)
for feature in locations:
    geometry = shape(feature['geometry'])
    assert geometry.is_valid and not geometry.is_empty, feature['id']
    p = feature['properties']; metadata = p['metadata']
    assert 'base_location' not in p and 'generated' not in p
    assert (metadata.get('source_name') and metadata.get('source_url') and metadata.get('reference_version')==3) or feature['id'] in created_source_ids
    if metadata.get('source_name') == 'geoBoundaries gbOpen':
        assert metadata['original_id'] and metadata['source_id'] and metadata['source_url']
        assert feature['id'].startswith('gb:') or feature['id'] in ('GBR-4809', 'FRA-5333', 'TUR-2265')
count = 0
for path in pathlib.Path('data/cliopatria').glob('part-*.json'):
    for feature in json.loads(path.read_text())['features']:
        geometry = shape(feature['geometry'])
        assert geometry.is_valid and not geometry.is_empty, feature['id']
        assert geometry.bounds[1] >= -60, feature['id']
        assert feature['properties']['valid_to'] > feature['properties']['valid_from']
        count += 1
print(f'PASS: {len(locations)} valid administrative locations; {count} valid historical territories.')

# Valid individual polygons can still overlap. Audit the entire final collection.
geometries = [shape(f['geometry']) for f in locations]
tree = STRtree(geometries)
overlaps = []
for i, geometry in enumerate(geometries):
    for j in tree.query(geometry, predicate='intersects'):
        j = int(j)
        if j > i and geometry.intersection(geometries[j]).area > 1e-10:
            overlaps.append((locations[i]['id'], locations[j]['id']))
assert not overlaps, overlaps[:20]
hong_kong = [i for i,f in enumerate(locations) if f['id']=='atlas:territory:HKG']
assert len(hong_kong) == 1
assert not any(f['properties']['name'] == 'Xianggang' for f in locations)
for i in hong_kong:
    point = geometries[i].representative_point()
    hits = [int(j) for j in tree.query(point, predicate='intersects')]
    assert hits == [i], (locations[i]['id'], hits)
print('PASS: no overlapping location interiors above 1e-10 square degrees; the coherent Hong Kong territory has single coverage.')
