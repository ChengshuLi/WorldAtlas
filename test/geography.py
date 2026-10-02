"""Validate prepared source identities and display polygon geometry."""
import json, pathlib
from shapely.geometry import shape
from shapely import STRtree
parts = json.loads(pathlib.Path('data/world-index.json').read_text())['parts']
locations = [f for part in parts for f in json.loads((pathlib.Path('data') / part).read_text())['features']]
assert len({f['id'] for f in locations}) == len(locations)
for feature in locations:
    geometry = shape(feature['geometry'])
    assert geometry.is_valid and not geometry.is_empty, feature['id']
    p = feature['properties']; metadata = p['metadata']
    assert 'base_location' not in p and 'generated' not in p
    assert metadata['source_name'] and metadata.get('source_url')
    assert metadata.get('reference_version')==3
    if metadata['source_name'] == 'geoBoundaries gbOpen':
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
